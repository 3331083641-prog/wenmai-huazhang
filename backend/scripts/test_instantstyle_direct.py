from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
LOG_PATH = PROJECT_ROOT / "logs" / "test_instantstyle_direct.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("HF_HOME", str(PROJECT_ROOT / ".cache" / "huggingface"))
os.environ.setdefault("HF_HUB_CACHE", str(PROJECT_ROOT / ".cache" / "huggingface" / "hub"))
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(PROJECT_ROOT / ".cache" / "huggingface" / "hub"))
os.environ.setdefault("TRANSFORMERS_CACHE", str(PROJECT_ROOT / ".cache" / "transformers"))
os.environ.setdefault("TORCH_HOME", str(PROJECT_ROOT / ".cache" / "torch"))
os.environ.setdefault("XDG_CACHE_HOME", str(PROJECT_ROOT / ".cache"))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env", override=True)

    print("== Runtime ==")
    import torch
    import diffusers
    print("python=", sys.executable)
    print("torch=", torch.__version__)
    print("cuda=", torch.cuda.is_available())
    print("cudaDevice=", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NO CUDA")
    print("diffusers=", diffusers.__version__)

    from image_analyzer import analyze_image
    from instantstyle_service import generate_with_instantstyle
    from prompt_builder import build_enhanced_prompt, build_negative_prompt
    from style_config import STYLE_REFS_DIR, get_style, missing_style_refs

    missing = missing_style_refs()
    print("styleRefsDir=", STYLE_REFS_DIR)
    print("styleRefsMissing=", missing)
    if missing:
        raise RuntimeError(f"Missing style refs: {missing}")

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
    analysis = analyze_image(None)
    payload["imageAnalysis"] = analysis
    style = get_style(payload["style"])
    enhanced = build_enhanced_prompt(payload, style)
    negative = build_negative_prompt(payload["negativePrompt"])
    print("== Request ==")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("== Generate ==")
    result = generate_with_instantstyle(payload, enhanced, negative, style, image_analysis=analysis)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    with LOG_PATH.open("w", encoding="utf-8") as log, redirect_stdout(log), redirect_stderr(log):
        try:
            code = main()
        except Exception:
            traceback.print_exc()
            code = 1
    print(f"Log written to {LOG_PATH}")
    raise SystemExit(code)