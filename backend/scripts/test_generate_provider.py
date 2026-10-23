from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

import requests

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
LOG = ROOT / "logs" / "generate_provider.log"
URL = "http://127.0.0.1:8000/generate"


def write(line: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line)


def main() -> int:
    if load_dotenv is not None:
        load_dotenv(BACKEND / ".env", override=True)
    provider = os.getenv("GENERATION_PROVIDER", "")
    payload = {
        "theme": "开封古城墙与朱仙镇木版年画风格融合的非遗文旅海报",
        "style": "zhuxianzhen",
        "styleName": "朱仙镇木版年画",
        "outputType": "poster",
        "styleStrength": 0.65,
        "compositionMode": "portrait",
        "negativePrompt": "low quality, blurry, watermark, text artifacts",
        "uploadedImage": None,
    }
    write(f"\n[{datetime.now().isoformat(timespec='seconds')}] provider={provider} POST {URL}")
    try:
        response = requests.post(URL, json=payload, timeout=300)
        write(f"HTTP {response.status_code}")
        data = response.json()
        summary = {
            "success": data.get("success"),
            "mode": data.get("mode"),
            "provider": data.get("provider"),
            "imageUrl": data.get("imageUrl"),
            "error": data.get("error"),
            "realProviderError": data.get("realProviderError"),
            "debug": data.get("debug"),
            "cultureCard": bool(data.get("cultureCard")),
            "imageAnalysis": bool(data.get("imageAnalysis")),
        }
        write(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if response.ok and data.get("success") else 1
    except Exception as exc:
        write(f"ERROR: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())