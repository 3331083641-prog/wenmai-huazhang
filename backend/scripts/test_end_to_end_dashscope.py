from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

ROOT = Path(r"D:\wenmai-huazhang")
LOG = ROOT / "logs" / "end_to_end_dashscope.log"
API = "http://127.0.0.1:8000"


def write(line: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def safe_provider_error(value: Any) -> str | None:
    if not value:
        return None
    text = str(value)
    return text[:1200]


def main() -> int:
    write(f"\n[{datetime.now().isoformat(timespec='seconds')}] End-to-end DashScope provider check")

    health_resp = requests.get(f"{API}/health", timeout=20)
    write(f"healthStatus={health_resp.status_code}")
    health_resp.raise_for_status()
    health = health_resp.json()
    providers = health.get("providers") or {}
    dashscope = providers.get("dashscope_wanx") or {}
    write("healthSummary=" + json.dumps({
        "status": health.get("status"),
        "generationProvider": health.get("generationProvider"),
        "allowMockFallback": health.get("allowMockFallback"),
        "dashscopeHasApiKey": dashscope.get("hasApiKey"),
        "dashscopeAvailable": dashscope.get("available"),
        "dashscopeNetworkReachable": dashscope.get("networkReachable"),
        "dashscopeSslOk": dashscope.get("sslOk"),
    }, ensure_ascii=False))

    payload = {
        "theme": "开封古城墙与朱仙镇木版年画风格融合的非遗文旅海报",
        "style": "zhuxianzhen",
        "styleName": "朱仙镇木版年画",
        "outputType": "poster",
        "styleStrength": 0.65,
        "compositionMode": "portrait",
        "negativePrompt": "低质量，模糊，水印，乱码文字，多余文字，畸形结构，噪点",
        "uploadedImage": None,
    }
    gen_resp = requests.post(f"{API}/generate", json=payload, timeout=360)
    write(f"generateStatus={gen_resp.status_code}")
    try:
        data = gen_resp.json()
    except Exception as exc:
        write(f"RESULT success=false stage=parse_generate error={type(exc).__name__}: {exc}")
        return 2

    image_url = data.get("imageUrl") or ""
    summary = {
        "success": data.get("success"),
        "mode": data.get("mode"),
        "provider": data.get("provider"),
        "imageUrl": image_url,
        "realProviderError": safe_provider_error(data.get("realProviderError")),
        "hasCultureCard": bool(data.get("cultureCard")),
        "hasImageAnalysis": bool(data.get("imageAnalysis")),
        "hasEnhancedPrompt": bool(data.get("enhancedPrompt")),
    }
    write("generateSummary=" + json.dumps(summary, ensure_ascii=False))

    if not data.get("success") or not image_url:
        write("RESULT success=false stage=generate error=missing successful imageUrl")
        return 3

    img_resp = requests.get(image_url, timeout=60)
    content_type = img_resp.headers.get("Content-Type", "")
    byte_count = len(img_resp.content)
    write("imageCheck=" + json.dumps({
        "status": img_resp.status_code,
        "contentType": content_type,
        "bytes": byte_count,
    }, ensure_ascii=False))

    ok_type = content_type.startswith("image/png") or content_type.startswith("image/jpeg")
    ok_size = byte_count > 10 * 1024
    if img_resp.status_code == 200 and ok_type and ok_size:
        write("RESULT success=true")
        return 0

    write("RESULT success=false stage=image_url_check error=imageUrl did not return a png/jpeg larger than 10KB")
    return 4


if __name__ == "__main__":
    raise SystemExit(main())