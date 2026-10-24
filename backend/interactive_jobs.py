"""Persistent background jobs for the three interactive experiences.

One generation should end with a case that has:
  - 画中有话  (hotspots + culture notes)      -> experience.json
  - 一图一境  (chapter story)                 -> experience.json
  - 画境漫游  (2.5D depth world)              -> public/interactive/<case>/world/

The HTTP response of /generate must not wait for this work, so it runs in a
thread.  Unlike the previous in-memory version, every state transition is
written to ``backend/outputs/interactive_jobs.json`` atomically.  A backend
restart therefore keeps history; jobs that were mid-flight are marked failed
with an explicit "interrupted" reason and can be retried.

States (the contract used by the frontend):
    queued      - accepted, waiting for the worker
    processing  - worker is running
    ready       - experience.json + world.json available
    partial     - experience.json available, world missing/failed
    failed      - nothing usable; retry allowed
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = PROJECT_ROOT / "docs" / "examples"
PUBLIC_WORLD = PROJECT_ROOT / "frontend" / "public" / "interactive"
INGEST_SCRIPT = PROJECT_ROOT / "scripts" / "interactive" / "ingest_case.py"
JOBS_FILE = PROJECT_ROOT / "backend" / "outputs" / "interactive_jobs.json"

CASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
ACTIVE_STATES = {"queued", "processing"}

_LOCK = threading.RLock()
_JOBS: dict[str, dict[str, Any]] = {}
_LOADED = False


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def interactive_build_enabled() -> bool:
    return os.getenv("AUTO_BUILD_INTERACTIVE", "true").strip().lower() in {"1", "true", "yes", "on"}


def _safe_case_id(case_id: str) -> bool:
    return bool(case_id and CASE_ID_RE.match(case_id))


# --------------------------------------------------------------------------- #
# persistence
# --------------------------------------------------------------------------- #
def _save_locked() -> None:
    JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = JOBS_FILE.with_name(JOBS_FILE.name + ".tmp")
    tmp.write_text(json.dumps(_JOBS, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, JOBS_FILE)


def _load() -> None:
    global _LOADED
    with _LOCK:
        if _LOADED:
            return
        _LOADED = True
        if JOBS_FILE.is_file():
            try:
                data = json.loads(JOBS_FILE.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                data = {}
            if isinstance(data, dict):
                _JOBS.update({
                    str(key): value
                    for key, value in data.items()
                    if isinstance(value, dict) and _safe_case_id(str(key))
                })
        # A restart cannot resume an in-process thread.  Be explicit instead of
        # leaving a permanent "processing" spinner in the UI.
        recovered = False
        for record in _JOBS.values():
            if str(record.get("status")) in ACTIVE_STATES:
                record.update({
                    "status": "failed",
                    "error": "后端重启，任务被中断；可点击“重新构建”。",
                    "finishedAt": _now(),
                    "updatedAt": _now(),
                })
                recovered = True
        if recovered:
            _save_locked()


def _update(case_id: str, **fields: Any) -> dict[str, Any]:
    with _LOCK:
        record = _JOBS.setdefault(case_id, {"caseId": case_id, "attempts": 0})
        record.update(fields)
        record["updatedAt"] = _now()
        _save_locked()
        return dict(record)


# --------------------------------------------------------------------------- #
# artefact inspection
# --------------------------------------------------------------------------- #
def _read_artifacts(case_id: str) -> dict[str, Any]:
    """Derive the real, on-disk state instead of trusting a subprocess exit code."""
    folder = EXAMPLES_DIR / case_id
    experience_path = folder / "experience.json"
    world_path = PUBLIC_WORLD / case_id / "world" / "world.json"
    report_path = folder / "ingest-report.json"
    metadata_path = folder / "metadata.json"

    metadata: dict[str, Any] = {}
    if metadata_path.is_file():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            metadata = {}

    experience: dict[str, Any] = {}
    if experience_path.is_file():
        try:
            experience = json.loads(experience_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            experience = {}

    report: dict[str, Any] = {}
    if report_path.is_file():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            report = {}

    hotspots = experience.get("hotspots") if isinstance(experience.get("hotspots"), list) else []
    chapters = experience.get("chapters") if isinstance(experience.get("chapters"), list) else []
    has_experience = bool(hotspots and chapters)
    has_world = world_path.is_file()

    return {
        "hasExperience": has_experience,
        "hasWorld": has_world,
        "hotspots": len(hotspots),
        "chapters": len(chapters),
        "experiencePath": str(experience_path.relative_to(PROJECT_ROOT)) if experience_path.is_file() else "",
        "worldPath": str(world_path.relative_to(PROJECT_ROOT)) if has_world else "",
        "worldFiles": sorted(p.name for p in world_path.parent.glob("*")) if has_world else [],
        "depthSource": str(report.get("depthSource") or (report.get("depth") or {}).get("source") or ""),
        "vlmUsed": bool((report.get("vlm") or {}).get("used")),
        "warnings": report.get("warnings") if isinstance(report.get("warnings"), list) else [],
        "metadataStatus": str((metadata.get("interactive") or {}).get("status") or ""),
        "experienceId": str(metadata.get("experienceId") or ""),
        "artworkTitle": str(metadata.get("artworkTitle") or case_id),
    }


def _status_from_artifacts(state: dict[str, Any]) -> str:
    if state.get("hasExperience") and state.get("hasWorld"):
        return "ready"
    if state.get("hasExperience"):
        return "partial"
    return "failed"


# --------------------------------------------------------------------------- #
# worker
# --------------------------------------------------------------------------- #
def _run(case_id: str, timeout: int) -> None:
    started = time.time()
    _update(
        case_id,
        status="processing",
        beganAt=_now(),
        error="",
        message="正在生成文化热点、章节叙事与画境资产……",
    )
    cmd = [sys.executable, "-X", "utf8", str(INGEST_SCRIPT), "--refresh", case_id]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
        state = _read_artifacts(case_id)
        status = _status_from_artifacts(state)
        tail = (proc.stdout or "").strip().splitlines()[-12:]
        stderr = (proc.stderr or "").strip()
        if proc.returncode != 0 and not state.get("hasExperience"):
            status = "failed"
        _update(
            case_id,
            status=status,
            finishedAt=_now(),
            elapsedSec=round(time.time() - started, 1),
            exitCode=proc.returncode,
            stages={
                "hotspots": bool(state.get("hasExperience")),
                "story": bool(state.get("hasExperience")),
                "world": bool(state.get("hasWorld")),
            },
            assets={
                "experience": state.get("experiencePath", ""),
                "world": state.get("worldPath", ""),
                "worldFiles": state.get("worldFiles", []),
            },
            detail=state,
            tail=tail,
            error="" if status in {"ready", "partial"} else (stderr or (tail[-1] if tail else "构建失败"))[-600:],
            message=(
                "三种互动已就绪。"
                if status == "ready"
                else "画中有话与一图一境已就绪，画境资产未完成，可重试。"
                if status == "partial"
                else "互动构建失败，可重试。"
            ),
        )
    except subprocess.TimeoutExpired:
        state = _read_artifacts(case_id)
        _update(
            case_id,
            status=_status_from_artifacts(state) if state.get("hasExperience") else "failed",
            finishedAt=_now(),
            elapsedSec=round(time.time() - started, 1),
            error=f"超过 {timeout}s 未完成；可重试。",
            message="构建超时，可重试。",
        )
    except Exception as exc:  # noqa: BLE001 - background failure must be recorded, never raised
        _update(
            case_id,
            status="failed",
            finishedAt=_now(),
            elapsedSec=round(time.time() - started, 1),
            error=f"{type(exc).__name__}: {exc}"[:600],
            message="互动构建失败，可重试。",
        )


def start_interactive_build(case_id: str, timeout: int = 900, *, force: bool = False) -> dict[str, Any]:
    """Queue (or reuse) the interactive build for one case.

    ``force=True`` is the explicit retry path: finished jobs are rebuilt, but
    the case directory itself is never duplicated - the worker refreshes the
    same caseId in place.
    """
    _load()
    if not interactive_build_enabled():
        return {"enabled": False, "status": "disabled", "caseId": case_id}
    if not INGEST_SCRIPT.is_file():
        return {"enabled": False, "status": "missing_script", "caseId": case_id}
    if not _safe_case_id(case_id):
        return {"enabled": False, "status": "invalid_case_id", "caseId": case_id}
    if not (EXAMPLES_DIR / case_id).is_dir():
        return {"enabled": False, "status": "case_not_found", "caseId": case_id}

    with _LOCK:
        existing = _JOBS.get(case_id)
        if existing and str(existing.get("status")) in ACTIVE_STATES and not force:
            return {"enabled": True, "status": existing["status"], "reused": True, "job": dict(existing)}
        if existing and str(existing.get("status")) in {"ready", "partial"} and not force:
            return {"enabled": True, "status": existing["status"], "reused": True, "job": dict(existing)}

        previous_attempts = int(existing.get("attempts") or 0) if existing else 0
        _JOBS[case_id] = {
            "caseId": case_id,
            "status": "queued",
            "attempts": previous_attempts + 1,
            "queuedAt": _now(),
            "startedAt": (existing or {}).get("startedAt") or "",
            "finishedAt": "",
            "error": "",
            "message": "已进入队列，等待构建……",
            "stages": {"hotspots": False, "story": False, "world": False},
            "assets": {},
            "updatedAt": _now(),
        }
        _save_locked()
        thread = threading.Thread(
            target=_run,
            args=(case_id, timeout),
            daemon=True,
            name=f"interactive-{case_id}",
        )
        thread.start()
        return {"enabled": True, "status": "queued", "reused": False, "job": dict(_JOBS[case_id])}


def get_job(case_id: str) -> dict[str, Any] | None:
    _load()
    with _LOCK:
        record = _JOBS.get(case_id)
        return dict(record) if record else None


def list_jobs() -> list[dict[str, Any]]:
    _load()
    with _LOCK:
        items = [dict(item) for item in _JOBS.values()]
    items.sort(key=lambda item: str(item.get("updatedAt") or ""), reverse=True)
    return items