from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
ENV_PATH = BACKEND_DIR / ".env"
OUTPUT_PATH = BACKEND_DIR / "outputs" / "dashscope_self_test.png"
LOG_PATH = PROJECT_ROOT / "logs" / "dashscope_self_test.log"
SUBMIT_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"


def load_env() -> None:
    os.environ.setdefault("PIP_CACHE_DIR", str(PROJECT_ROOT / ".cache" / "pip"))
    os.environ.setdefault("HF_HOME", str(PROJECT_ROOT / ".cache" / "huggingface"))
    os.environ.setdefault("HF_HUB_CACHE", str(PROJECT_ROOT / ".cache" / "huggingface" / "hub"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(PROJECT_ROOT / ".cache" / "transformers"))
    os.environ.setdefault("TORCH_HOME", str(PROJECT_ROOT / ".cache" / "torch"))
    os.environ.setdefault("XDG_CACHE_HOME", str(PROJECT_ROOT / ".cache"))
    os.environ.setdefault("LOCALAPPDATA", str(PROJECT_ROOT / ".cache" / "localappdata"))
    os.environ.setdefault("TEMP", str(PROJECT_ROOT / ".cache" / "temp"))
    os.environ.setdefault("TMP", str(PROJECT_ROOT / ".cache" / "temp"))
    for path in [
        PROJECT_ROOT / ".cache" / "pip",
        PROJECT_ROOT / ".cache" / "npm",
        PROJECT_ROOT / ".cache" / "huggingface" / "hub",
        PROJECT_ROOT / ".cache" / "transformers",
        PROJECT_ROOT / ".cache" / "torch",
        PROJECT_ROOT / ".cache" / "localappdata",
        PROJECT_ROOT / ".cache" / "temp",
        BACKEND_DIR / "outputs",
        PROJECT_ROOT / "logs",
    ]:
        path.mkdir(parents=True, exist_ok=True)
    if load_dotenv is not None:
        load_dotenv(ENV_PATH, override=True, encoding="utf-8-sig")
        return
    if ENV_PATH.exists():
        for raw in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
            if not raw.strip() or raw.lstrip().startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            os.environ[key.strip()] = value.strip().strip('"').strip("'")


def log(record: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    load_env()
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    model = os.getenv("DASHSCOPE_WANX_FALLBACK_MODEL", "wanx-v1").strip() or "wanx-v1"
    size = os.getenv("DASHSCOPE_IMAGE_SIZE", "1024*1024").strip() or "1024*1024"
    poll_interval = float(os.getenv("DASHSCOPE_POLL_INTERVAL", "2") or "2")
    timeout = float(os.getenv("DASHSCOPE_TIMEOUT", "300") or "300")
    verify = os.getenv("DASHSCOPE_VERIFY_SSL", "true").strip().lower() not in {"0", "false", "no", "off"}
    ca_bundle = os.getenv("DASHSCOPE_CA_BUNDLE", "").strip()
    verify_arg: bool | str = ca_bundle or verify

    print(f"hasApiKey={str(bool(api_key)).lower()}")
    record: dict[str, Any] = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "hasApiKey": bool(api_key),
        "model": model,
        "size": size,
        "taskIdExists": False,
        "taskStatus": None,
        "usageImageCount": None,
        "imageSaved": False,
        "error": None,
    }
    if not api_key:
        record["error"] = "DASHSCOPE_API_KEY is empty"
        log(record)
        return 2

    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-DashScope-Async": "enable",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": {
            "prompt": "中国非遗纹样数字艺术海报，精致构图，高质量",
            "negative_prompt": "低质量，模糊，水印，乱码文字，多余文字",
        },
        "parameters": {"size": size, "n": 1},
    }

    try:
        submit = requests.post(SUBMIT_URL, headers=headers, json=payload, timeout=30, verify=verify_arg)
        record["submitHttpStatus"] = submit.status_code
        body = submit.json()
    except Exception as exc:
        record["error"] = f"submit failed: {type(exc).__name__}: {exc}"
        log(record)
        print(f"task_status=FAILED")
        return 3

    record["dashscopeRequestId"] = body.get("request_id") or body.get("requestId")
    record["submitResponseCode"] = body.get("code")
    record["submitResponseMessage"] = str(body.get("message") or "")[:300]
    task_id = (body.get("output") or {}).get("task_id") or body.get("task_id")
    record["taskIdExists"] = bool(task_id)
    if not task_id:
        record["error"] = f"no task_id, http={submit.status_code}, code={body.get('code')}"
        log(record)
        print("task_status=FAILED")
        return 4

    print("task_id 已获取")
    deadline = time.time() + timeout
    result: dict[str, Any] = {}
    poll_count = 0
    while time.time() < deadline:
        poll_count += 1
        poll = requests.get(TASK_URL.format(task_id=task_id), headers={"Authorization": f"Bearer {api_key}"}, timeout=30, verify=verify_arg)
        record["lastPollHttpStatus"] = poll.status_code
        result = poll.json()
        output = result.get("output") or {}
        status = str(output.get("task_status") or output.get("status") or "").upper()
        record["taskStatus"] = status
        record["pollCount"] = poll_count
        record["usageImageCount"] = (result.get("usage") or {}).get("image_count")
        if status in {"SUCCEEDED", "SUCCESS", "FAILED", "UNKNOWN", "CANCELED"}:
            break
        time.sleep(max(0.5, poll_interval))

    status = str(record.get("taskStatus") or "")
    print(f"task_status={status}")
    if status not in {"SUCCEEDED", "SUCCESS"}:
        output = result.get("output") or {}
        record["error"] = f"{output.get('code') or result.get('code')}: {output.get('message') or result.get('message')}"
        log(record)
        return 5

    usage_count = record.get("usageImageCount")
    print(f"usage.image_count={usage_count}")
    results = (result.get("output") or {}).get("results") or []
    image_url = results[0].get("url") if results and isinstance(results[0], dict) else ""
    record["resultUrlExists"] = bool(image_url)
    if not image_url:
        record["error"] = "SUCCEEDED but no output.results[0].url"
        log(record)
        return 6

    image_response = requests.get(image_url, timeout=60, verify=verify_arg)
    record["downloadStatus"] = image_response.status_code
    image_response.raise_for_status()
    OUTPUT_PATH.write_bytes(image_response.content)
    record["imageSaved"] = True
    record["outputPath"] = str(OUTPUT_PATH)
    log(record)
    print(f"图片保存路径={OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
