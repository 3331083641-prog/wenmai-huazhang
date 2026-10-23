from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = PROJECT_ROOT / "logs" / "backend_connectivity_test.log"
API_BASE = "http://127.0.0.1:8000"


def main() -> int:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("LOCALAPPDATA", str(PROJECT_ROOT / ".cache" / "localappdata"))
    os.environ.setdefault("TEMP", str(PROJECT_ROOT / ".cache" / "temp"))
    os.environ.setdefault("TMP", str(PROJECT_ROOT / ".cache" / "temp"))

    result: dict[str, object] = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "apiBase": API_BASE,
    }

    try:
        health = requests.get(f"{API_BASE}/health", timeout=10)
        result["healthStatusCode"] = health.status_code
        health_data = health.json() if health.headers.get("content-type", "").startswith("application/json") else {}
        result["generationProvider"] = health_data.get("generationProvider")
        result["allowMockFallback"] = health_data.get("allowMockFallback")
        result["dashscopeHasApiKey"] = bool(((health_data.get("providers") or {}).get("dashscope_wanx") or {}).get("hasApiKey"))
    except Exception as exc:
        result["healthError"] = f"{type(exc).__name__}: {exc}"

    try:
        docs = requests.get(f"{API_BASE}/docs", timeout=10)
        result["docsStatusCode"] = docs.status_code
    except Exception as exc:
        result["docsError"] = f"{type(exc).__name__}: {exc}"

    payload = {
        "theme": "后端连通性测试：朱仙镇木版年画风格文旅海报",
        "style": "zhuxianzhen",
        "styleName": "朱仙镇木版年画",
        "outputType": "poster",
        "styleStrength": 0.25,
        "compositionMode": "portrait",
        "negativePrompt": "不要水印",
        "uploadedImage": None,
    }
    try:
        generate = requests.post(f"{API_BASE}/generate", json=payload, timeout=300)
        result["generateStatusCode"] = generate.status_code
        data = generate.json()
        result["generateSuccess"] = data.get("success")
        result["mode"] = data.get("mode")
        result["provider"] = data.get("provider")
        result["imageUrl"] = data.get("imageUrl")
        result["realProviderError"] = data.get("realProviderError")
    except Exception as exc:
        result["generateError"] = f"{type(exc).__name__}: {exc}"

    line = json.dumps(result, ensure_ascii=False)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("healthStatusCode") == 200 and result.get("docsStatusCode") == 200 and result.get("generateStatusCode") == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
