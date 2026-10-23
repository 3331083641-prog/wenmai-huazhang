from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
from dashscope_direct_client import DashScopeDirectClient
LOG = ROOT / "logs" / "dashscope_minimal_test.log"
OUTPUT = BACKEND / "outputs" / "dashscope_minimal_test.png"
SUBMIT_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
PROMPT = "一张中国传统剪纸风格的红色莲花图案，干净背景，高质量"
NEGATIVE = "low quality, blurry, watermark, text artifacts"


def write(line: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line)


def safe_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)[:2000]


def extract_error(body: Mapping[str, Any]) -> dict[str, object]:
    output = body.get("output") if isinstance(body.get("output"), Mapping) else {}
    return {
        "code": body.get("code") or output.get("code"),
        "message": body.get("message") or output.get("message"),
        "request_id": body.get("request_id") or body.get("requestId") or body.get("requestId"),
        "task_status": output.get("task_status") or output.get("status"),
    }


def classify(text: str) -> str:
    lower = text.lower()
    if "invalid" in lower and "key" in lower or "no api-key" in lower:
        return "B: Key 未读到、Key 错误或格式问题，不是充值问题。"
    if "unauthorized" in lower or "accessdenied" in lower or "forbidden" in lower:
        return "B: 权限/业务空间/模型开通问题，不是充值问题。"
    if "model" in lower and ("not" in lower or "exist" in lower or "invalid" in lower):
        return "B: 模型名或模型权限问题，不是充值问题。"
    if "region" in lower or "workspace" in lower:
        return "B: 地域或业务空间不匹配，不是充值问题。"
    if "insufficient" in lower or "balance" in lower or "quota" in lower or "arrears" in lower or "account balance" in lower:
        return "A: 疑似计费/余额/欠费/额度问题。"
    if "rate" in lower or "qps" in lower or "concurrency" in lower:
        return "B: 频率或并发限制，不是充值问题。"
    if "synchronous" in lower:
        return "B: 异步 header 或调用方式错误，不是充值问题。"
    if "size" in lower and "match" in lower:
        return "B: 图片尺寸参数错误，不是充值问题。"
    if "timeout" in lower or "timed out" in lower:
        return "C: 任务超时，暂时无法判断计费。"
    if "ssl" in lower or "connection" in lower or "network" in lower:
        return "B: 网络/SSL 连接失败，不是充值问题。"
    return "C: 暂时无法判断，需要平台控制台或完整错误码。"


def main() -> int:
    if load_dotenv is not None:
        load_dotenv(BACKEND / ".env", override=True)
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip().strip('"').strip("'")
    model = os.getenv("DASHSCOPE_WANX_FALLBACK_MODEL", "wanx-v1").strip() or "wanx-v1"
    write(f"\n[{datetime.now().isoformat(timespec='seconds')}] DashScope minimal image test")
    write(f"hasApiKey={bool(api_key)}")
    write(f"model={model}")
    if not api_key:
        write("RESULT success=false")
        write("ERROR code=NO_API_KEY message=缺少 DASHSCOPE_API_KEY")
        write("CLASSIFICATION B: .env 未读取或 Key 缺失，不是充值问题。")
        return 1

    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-DashScope-Async": "enable",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": {
            "prompt": PROMPT,
            "negative_prompt": NEGATIVE,
        },
        "parameters": {
            "size": "1024*1024",
            "n": 1,
            "style": "<chinese painting>",
        },
    }

    direct_client = DashScopeDirectClient()
    use_direct = os.getenv("DASHSCOPE_BYPASS_TUN", "true").strip().lower() not in {"0", "false", "no", "off"}

    try:
        if use_direct:
            response = direct_client.request("POST", SUBMIT_URL, headers=headers, json_body=payload, timeout=60)
        else:
            response = requests.post(SUBMIT_URL, headers=headers, json=payload, timeout=30)
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        write("RESULT success=false")
        write("STAGE submit_task")
        write(f"ERROR exception={msg}")
        write("CLASSIFICATION " + classify(msg))
        return 1

    write(f"submit_http_status={response.status_code}")
    try:
        body = response.json()
    except Exception:
        body = {"message": response.text[:1000]}
    if response.status_code >= 400:
        err = extract_error(body)
        write("RESULT success=false")
        write("STAGE submit_task")
        write("ERROR " + safe_json(err))
        write("CLASSIFICATION " + classify(safe_json(err)))
        return 1

    task_id = (body.get("output") or {}).get("task_id") or body.get("task_id")
    write(f"task_id_present={bool(task_id)}")
    if not task_id:
        write("RESULT success=false")
        write("STAGE submit_task")
        write("ERROR code=NO_TASK_ID message=" + safe_json(body))
        write("CLASSIFICATION C: 未返回 task_id，需检查接口返回结构。")
        return 1

    deadline = time.time() + 180
    last_body: dict[str, Any] | None = None
    while time.time() < deadline:
        try:
            poll_url = TASK_URL.format(task_id=task_id)
            if use_direct:
                poll = direct_client.request("GET", poll_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=60)
            else:
                poll = requests.get(poll_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
        except Exception as exc:
            msg = f"{type(exc).__name__}: {exc}"
            write("RESULT success=false")
            write("STAGE poll_task")
            write(f"ERROR exception={msg}")
            write("CLASSIFICATION " + classify(msg))
            return 1
        try:
            last_body = poll.json()
        except Exception:
            last_body = {"message": poll.text[:1000]}
        output = last_body.get("output") or {}
        status = str(output.get("task_status") or output.get("status") or "").upper()
        write(f"poll_status={status or 'UNKNOWN'} http={poll.status_code}")
        if poll.status_code >= 400:
            err = extract_error(last_body)
            write("RESULT success=false")
            write("STAGE poll_task")
            write("ERROR " + safe_json(err))
            write("CLASSIFICATION " + classify(safe_json(err)))
            return 1
        if status == "SUCCEEDED":
            results = output.get("results") or []
            image_url = results[0].get("url") if results and isinstance(results[0], Mapping) else ""
            if not image_url:
                write("RESULT success=false")
                write("STAGE parse_result")
                write("ERROR code=NO_IMAGE_URL message=" + safe_json(last_body))
                write("CLASSIFICATION C: 成功任务未返回图片 URL。")
                return 1
            try:
                image_resp = requests.get(image_url, timeout=60)
                image_resp.raise_for_status()
                OUTPUT.parent.mkdir(parents=True, exist_ok=True)
                OUTPUT.write_bytes(image_resp.content)
            except Exception as exc:
                msg = f"{type(exc).__name__}: {exc}"
                write("RESULT success=false")
                write("STAGE download_image")
                write(f"ERROR exception={msg}")
                write("CLASSIFICATION " + classify(msg))
                return 1
            write("RESULT success=true")
            write(f"output={OUTPUT}")
            return 0
        if status in {"FAILED", "UNKNOWN", "CANCELED"}:
            err = extract_error(last_body)
            write("RESULT success=false")
            write("STAGE poll_task")
            write("ERROR " + safe_json(err))
            write("CLASSIFICATION " + classify(safe_json(err)))
            return 1
        time.sleep(2)

    write("RESULT success=false")
    write("STAGE poll_task")
    write("ERROR code=TIMEOUT message=任务 180 秒内未完成")
    write("CLASSIFICATION C: 任务超时，暂时无法判断计费。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
