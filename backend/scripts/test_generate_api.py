from __future__ import annotations

import json
import sys
import traceback
import urllib.error
import urllib.request
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = PROJECT_ROOT / "logs" / "test_generate_api.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def main() -> int:
    payload = {
        "theme": "开封古城墙",
        "style": "zhuxianzhen",
        "styleName": "朱仙镇木版年画",
        "outputType": "poster",
        "styleStrength": 0.65,
        "compositionMode": "portrait",
        "negativePrompt": "low quality, blurry, watermark, text artifacts",
        "uploadedImage": None,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:8000/generate",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        status = exc.code
    print("HTTP status:", status)
    print("Raw response:")
    print(raw)
    try:
        data = json.loads(raw)
    except Exception:
        print("Response is not JSON")
        return 1
    print("Summary:")
    print("success=", data.get("success"))
    print("mode=", data.get("mode"))
    print("imageUrl=", data.get("imageUrl"))
    print("error=", data.get("error"))
    print("debug=", json.dumps(data.get("debug"), ensure_ascii=False, indent=2))
    print("cultureCard exists=", bool(data.get("cultureCard")))
    print("imageAnalysis exists=", bool(data.get("imageAnalysis")))
    return 0 if data.get("success") else 1


if __name__ == "__main__":
    with LOG_PATH.open("w", encoding="utf-8") as log, redirect_stdout(log), redirect_stderr(log):
        try:
            code = main()
        except Exception:
            traceback.print_exc()
            code = 1
    print(f"Log written to {LOG_PATH}")
    raise SystemExit(code)