from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
LOG_PATH = PROJECT_ROOT / "logs" / "generate_parameters_effective.log"

sys.path.insert(0, str(BACKEND_DIR))

from provider_service import GenerationService  # noqa: E402


CASES = [
    {
        "name": "A",
        "theme": "开封古城墙与朱仙镇木版年画风格融合的非遗文旅海报",
        "style": "zhuxianzhen",
        "styleName": "朱仙镇木版年画",
        "outputType": "poster",
        "styleStrength": 0.25,
        "compositionMode": "portrait",
        "negativePrompt": None,
        "uploadedImage": None,
    },
    {
        "name": "B",
        "theme": "青花瓷纹样与现代校园文创杯垫设计",
        "style": "qinghua",
        "styleName": "青花瓷纹样",
        "outputType": "coaster",
        "styleStrength": 0.85,
        "compositionMode": "object",
        "negativePrompt": None,
        "uploadedImage": None,
    },
    {
        "name": "C",
        "theme": "剪纸风格的黄河文化宣传海报",
        "style": "jianzhi",
        "styleName": "中国剪纸",
        "outputType": "poster",
        "styleStrength": 0.65,
        "compositionMode": "portrait",
        "negativePrompt": "不要现代建筑，不要英文文字，不要水印",
        "uploadedImage": None,
    },
]


def main() -> int:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    service = GenerationService()
    results: list[dict[str, object]] = []
    with LOG_PATH.open("a", encoding="utf-8") as log:
        log.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] parameter effectiveness test\n")
        for case in CASES:
            payload = {key: value for key, value in case.items() if key != "name"}
            response = service.generate(payload, base_url="http://127.0.0.1:8000/")
            record = {
                "case": case["name"],
                "success": response.get("success"),
                "mode": response.get("mode"),
                "provider": response.get("provider"),
                "imageUrl": response.get("imageUrl"),
                "enhancedPrompt": response.get("enhancedPrompt"),
                "negativePromptContainsUserInput": "不要现代建筑" in str((response.get("debug") or {}).get("negativePromptPreview", "")),
                "styleStrengthText": (response.get("debug") or {}).get("styleStrengthText") if isinstance(response.get("debug"), dict) else None,
                "realProviderErrorExists": bool(response.get("realProviderError")),
            }
            results.append(record)
            log.write(json.dumps(record, ensure_ascii=False) + "\n")

        prompts = [str(item.get("enhancedPrompt") or "") for item in results]
        strength_texts = [str(item.get("styleStrengthText") or "") for item in results]
        summary = {
            "enhancedPromptsDifferent": len(set(prompts)) == len(prompts),
            "styleStrengthTextsDifferent": len(set(strength_texts)) >= 3,
            "modes": [item.get("mode") for item in results],
            "providers": [item.get("provider") for item in results],
        }
        log.write("SUMMARY " + json.dumps(summary, ensure_ascii=False) + "\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if not summary["enhancedPromptsDifferent"]:
            return 2
        if not summary["styleStrengthTextsDifferent"]:
            return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
