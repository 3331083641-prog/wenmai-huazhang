"""出图之后把「三重互动」也自动做出来。

为什么要单独一个模块：`/generate` 的响应时间不能被深度推理拖累。这里只负责
起一个后台线程去跑 `scripts/interactive/ingest_case.py --refresh <case>`，
任务状态记在内存里，可通过 `/interactive-jobs` 查询。

它做的事（全部在 ingest_case.py 里）：
  1. 对案例目录里的 generated.png 做单目深度估计；
  2. 自动选 4–6 处热点（标 approximate / pending）；
  3. 按风格知识包写三折叙事（来源编号沿用该风格已核验的来源）；
  4. 生成画境资产（frontend/public/interactive/<case>/world/）；
  5. 把 experienceId 写回 metadata.json —— 前端下次构建/重启就会自动出现三个入口。

关闭方式：`AUTO_BUILD_INTERACTIVE=false`。
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INGEST_SCRIPT = PROJECT_ROOT / "scripts" / "interactive" / "ingest_case.py"

_LOCK = threading.Lock()
_JOBS: dict[str, dict[str, Any]] = {}


def interactive_build_enabled() -> bool:
    return os.getenv("AUTO_BUILD_INTERACTIVE", "true").strip().lower() in {"1", "true", "yes", "on"}


def _run(case_id: str, timeout: int) -> None:
    started = time.time()
    record = _JOBS[case_id]
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
        ok = proc.returncode == 0
        with _LOCK:
            record.update({
                "status": "ready" if ok else "failed",
                "elapsedSec": round(time.time() - started, 1),
                "exitCode": proc.returncode,
                "tail": (proc.stdout or "").strip().splitlines()[-8:],
                "error": None if ok else (proc.stderr or "")[-400:],
            })
    except subprocess.TimeoutExpired:
        with _LOCK:
            record.update({"status": "timeout", "elapsedSec": round(time.time() - started, 1),
                           "error": f"超过 {timeout}s 未完成"})
    except Exception as exc:  # noqa: BLE001 - 后台任务失败只记录
        with _LOCK:
            record.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"[:400]})


def start_interactive_build(case_id: str, timeout: int = 900) -> dict[str, Any]:
    """起一个后台线程给该案例生成互动内容；同一案例重复触发会复用已有任务。"""
    if not interactive_build_enabled():
        return {"enabled": False, "status": "disabled"}
    if not INGEST_SCRIPT.is_file():
        return {"enabled": False, "status": "missing_script"}

    with _LOCK:
        existing = _JOBS.get(case_id)
        if existing and existing.get("status") == "running":
            return {"enabled": True, "status": "running", "reused": True}
        _JOBS[case_id] = {
            "caseId": case_id,
            "status": "running",
            "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        thread = threading.Thread(target=_run, args=(case_id, timeout), daemon=True,
                                  name=f"interactive-{case_id}")
        thread.start()
    return {"enabled": True, "status": "running", "reused": False}


def list_jobs() -> list[dict[str, Any]]:
    with _LOCK:
        return [dict(item) for item in _JOBS.values()]