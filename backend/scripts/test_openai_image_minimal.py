from __future__ import annotations

import base64
import os
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
LOG = ROOT / "logs" / "openai_image_minimal_test.log"
OUTPUT = BACKEND / "outputs" / "openai_minimal_test.png"
PROMPT = "A clean poster-style illustration of Chinese intangible cultural heritage paper-cut lotus pattern, red and gold, high quality"


def write(line: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line)


def classify(error_type: str, message: str) -> str:
    lower = f"{error_type} {message}".lower()
    if "invalid_api_key" in lower or "api key" in lower and ("incorrect" in lower or "invalid" in lower):
        return "B: Key 错误或未正确读取，不是充值问题。"
    if "insufficient_quota" in lower or "billing" in lower or "credits" in lower or "quota" in lower or "hard limit" in lower:
        return "A: API billing/credits/额度问题。"
    if "model_not_found" in lower or "model" in lower and "not" in lower:
        return "B: 模型名不可用，不是充值问题。"
    if "permission" in lower or "denied" in lower or "forbidden" in lower:
        return "B: 组织/项目没有模型权限，不是充值问题。"
    if "rate_limit" in lower or "rate limit" in lower:
        return "B: 请求过快或速率限制，不是充值问题。"
    if "content_policy" in lower or "policy" in lower:
        return "B: 内容策略拦截，不是充值问题。"
    if "timeout" in lower or "connection" in lower or "network" in lower:
        return "B: 网络/超时问题，不是充值问题。"
    return "C: 暂时无法判断，需要平台错误码或控制台信息。"


def error_code(exc: Exception) -> str:
    code = getattr(exc, "code", None)
    if code:
        return str(code)
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        err = body.get("error") or body
        if isinstance(err, dict) and err.get("code"):
            return str(err.get("code"))
    return type(exc).__name__


def error_message(exc: Exception) -> str:
    return str(exc)[:2000]


def run_model(client, model: str) -> tuple[bool, str]:
    try:
        response = client.images.generate(model=model, prompt=PROMPT, size="1024x1024", n=1)
        item = response.data[0]
        b64_json = getattr(item, "b64_json", None)
        url = getattr(item, "url", None)
        if b64_json:
            content = base64.b64decode(b64_json)
        elif url:
            import requests
            image_resp = requests.get(url, timeout=60)
            image_resp.raise_for_status()
            content = image_resp.content
        else:
            raise RuntimeError("Image response has neither b64_json nor url")
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(content)
        write("RESULT success=true")
        write(f"model={model}")
        write(f"output={OUTPUT}")
        return True, ""
    except Exception as exc:
        code = error_code(exc)
        msg = error_message(exc)
        write(f"MODEL_ATTEMPT model={model} success=false")
        write(f"ERROR type={code}")
        write(f"ERROR message={msg}")
        write("CLASSIFICATION " + classify(code, msg))
        return False, code


def main() -> int:
    if load_dotenv is not None:
        load_dotenv(BACKEND / ".env", override=True)
    api_key = os.getenv("OPENAI_API_KEY", "").strip().strip('"').strip("'")
    configured_model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1").strip() or "gpt-image-1"
    write(f"\n[{datetime.now().isoformat(timespec='seconds')}] OpenAI image minimal test")
    write(f"hasApiKey={bool(api_key)}")
    write(f"configuredModel={configured_model}")
    if not api_key:
        write("RESULT success=false")
        write("ERROR type=NO_API_KEY")
        write("ERROR message=缺少 OPENAI_API_KEY")
        write("CLASSIFICATION B: .env 未读取或 Key 缺失，不是充值问题。")
        return 1
    try:
        from openai import OpenAI
    except Exception as exc:
        write("RESULT success=false")
        write("ERROR type=SDK_IMPORT_ERROR")
        write(f"ERROR message={exc}")
        write("CLASSIFICATION B: 本地 SDK 依赖问题，不是充值问题。")
        return 1
    client = OpenAI(api_key=api_key)
    models = [configured_model]
    for candidate in ["gpt-image-1.5", "gpt-image-1-mini"]:
        if candidate not in models:
            models.append(candidate)
    for index, model in enumerate(models):
        ok, code = run_model(client, model)
        if ok:
            return 0
        if "model" not in code.lower() and "not" not in code.lower():
            break
    write("RESULT success=false")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())