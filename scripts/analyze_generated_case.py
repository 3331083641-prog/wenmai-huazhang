"""Run the project's local Qwen3-VL analyzer for a saved gallery case."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / 'backend/.env', override=True)
sys.path.insert(0, str(ROOT / "backend"))

from services.vision_analysis import VisionAnalysisService  # noqa: E402
from style_config import STYLE_LIBRARY  # noqa: E402


def main(style_id: str) -> int:
    if style_id not in STYLE_LIBRARY:
        print("unknown_style")
        return 2

    case_dir = ROOT / "docs" / "examples" / style_id
    metadata_path = case_dir / "metadata.json"
    image_path = case_dir / "generated.png"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    style = STYLE_LIBRARY[style_id]
    theme = metadata.get('theme') or (
        f"{metadata['artworkTitle']}：{metadata['referenceSubject']}。"
        f"将该主体转化为{style.name}视觉作品，保持主体清晰完整，主体身份高于装饰题材。"
    )
    style_data = {
        "id": style.id,
        "name": style.name,
        "category": style.tag,
        "shortDescription": style.description,
        "visualFeatures": [part.strip() for part in style.visual_features.split("、") if part.strip()],
        "cultureSource": style.culture_source,
        "symbolicMeaning": style.symbolic_meaning,
        "cultureInterpretationGuide": style.culture_interpretation_guide,
        "recommendedScenes": list(style.recommended_scenes),
        "literaryReferences": list(style.literary_references),
    }

    try:
        result = VisionAnalysisService().analyze(
            generated_image_path=image_path,
            theme=theme,
            style_id=style.id,
            style_name=style.name,
            style_library_data=style_data,
        )
        analysis = result["analysis"]
        details = result.get("metadata") or {}
        metadata["analysisSource"] = "qwen3_vl"
        metadata["cultureCardAnalysisSource"] = "qwen3_vl_on_generated_image"
        metadata["visionAnalysis"] = analysis
        metadata["visionAnalysisRuntime"] = {
            "provider": details.get("provider"),
            "model": details.get("model"),
            "input_image_count": details.get("input_image_count"),
            "input_image_bytes": details.get("input_image_bytes"),
            "prompt_eval_count": details.get("prompt_eval_count"),
            "eval_count": details.get("eval_count"),
        }
        metadata.pop("visionAnalysisErrorType", None)
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"style": style_id, "success": True, "provider": details.get("provider"), "model": details.get("model"), "title": analysis.get("title"), "subjects": analysis.get("observed_subjects")}, ensure_ascii=False))
        return 0
    except Exception as exc:  # never substitute the template card for a failed model analysis
        metadata["analysisSource"] = "unavailable"
        metadata["cultureCardAnalysisSource"] = "unavailable"
        metadata["visionAnalysisErrorType"] = type(exc).__name__
        metadata.pop("visionAnalysis", None)
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"style": style_id, "success": False, "errorType": type(exc).__name__}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: analyze_generated_case.py STYLE_ID")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
