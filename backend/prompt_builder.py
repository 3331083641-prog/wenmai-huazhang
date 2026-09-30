from __future__ import annotations

import re
from typing import Mapping, Optional

from style_config import StyleConfig, get_composition_preset, get_output_preset


DEFAULT_NEGATIVE_PROMPT = (
    "低质量，模糊，水印，乱码文字，多余文字，畸形结构，噪点，过曝，低分辨率，画面破碎，主体缺失"
)


def _clean_text(value: Optional[str], fallback: str = "") -> str:
    value = (value or fallback).strip()
    return re.sub(r"\s+", " ", value)


def _coerce_image_analysis(value: object) -> Mapping[str, str] | None:
    if not isinstance(value, Mapping):
        return None
    keys = [
        "hasUploadedImage",
        "subject",
        "scene",
        "colors",
        "composition",
        "transferableElements",
        "savedPath",
        "width",
        "height",
        "brightness",
        "dominantColor",
    ]
    return {key: _clean_text(str(value.get(key) or "")) for key in keys}


def style_strength_text(raw_strength: object) -> tuple[float, str]:
    try:
        strength = float(raw_strength)
    except Exception:
        strength = 0.65
    strength = max(0.0, min(1.5, strength))
    if strength < 0.35:
        return strength, "提示词以主题和主体要求为主，仅轻度强调所选视觉风格。"
    if strength < 0.7:
        return strength, "提示词中等程度强调所选视觉风格的色彩、构图和纹样描述。"
    return strength, "提示词较强强调所选视觉风格描述；实际画面效果受生成模型影响。"


def build_enhanced_prompt(payload: Mapping[str, object], style: StyleConfig) -> str:
    theme = _clean_text(str(payload.get("theme") or ""), "传统文化主题创作")
    style_name = _clean_text(str(payload.get("styleName") or ""), style.name)
    output = get_output_preset(str(payload.get("outputType") or "poster"))
    composition = get_composition_preset(str(payload.get("compositionMode") or "portrait"))
    strength, strength_text = style_strength_text(payload.get("styleStrength"))
    image_analysis = _coerce_image_analysis(payload.get("imageAnalysis"))
    user_exclusions = _clean_text(str(payload.get("negativePrompt") or ""))[:320]
    exclusion_instruction = ""
    if user_exclusions:
        exclusion_instruction = (
            f"用户排除清单：{user_exclusions}。清单是需要避开的画面元素，不是创作题材，不能把清单词语绘制到作品中。"
        )
        if any(term in user_exclusions.lower() for term in ("文字", "标题", "水印", "logo", "二维码", "乱码", "text")):
            exclusion_instruction += (
                "画面只呈现图像内容，不生成任何可读文字、数字、标题、署名、印章字符、标识、二维码或水印；"
                "该限制优先于海报、票券等版式提示。"
            )

    image_hint = "未上传参考图，生成主要依据用户主题、所选视觉风格和构图提示。"
    if image_analysis and image_analysis.get("hasUploadedImage") == "true":
        image_hint = (
            "用户上传的参考图将作为图像条件参与本次生成；请将其用于理解主体、主要关系与画面构图，"
            "并在保持创作主题和所选传统风格的前提下进行再创作。"
            "后端另由 Pillow 进行本地基础统计（不识别主体或场景）："
            f"尺寸 {image_analysis.get('width')}x{image_analysis.get('height')}；"
            f"平均色彩与明暗 {image_analysis.get('colors')}；"
            f"画幅方向 {image_analysis.get('composition')}。"
        )

    return (
        f"核心主题：{theme}。"
        f"所选传统文化视觉风格：{style_name}（{style.name}）。"
        f"风格来源：{style.culture_source}。"
        f"视觉特征：{style.visual_features}。"
        f"文化寓意：{style.symbolic_meaning}。"
        f"风格提示强度：{strength:.2f}，{strength_text}"
        f"参考图基础信息：{image_hint}"
        f"输出类型：{output.label}，{output.prompt_hint}。"
        f"构图要求：{composition.label}，{composition.prompt_hint}。"
        f"{exclusion_instruction}"
        "生成要求：主体清晰，层次丰富，传统视觉元素自然融入现代设计，避免无意义文字，画面完整，细节清楚，high quality, detailed texture."
    )


def build_negative_prompt(user_negative_prompt: Optional[str]) -> str:
    user_negative_prompt = _clean_text(user_negative_prompt)
    if not user_negative_prompt:
        return DEFAULT_NEGATIVE_PROMPT
    return f"{DEFAULT_NEGATIVE_PROMPT}，{user_negative_prompt}"


def build_culture_card(payload: Mapping[str, object], style: StyleConfig) -> dict[str, str]:
    theme = _clean_text(str(payload.get("theme") or ""), "传统文化主题创作")
    output = get_output_preset(str(payload.get("outputType") or "poster"))
    strength, strength_label = style_strength_text(payload.get("styleStrength"))
    image_analysis = _coerce_image_analysis(payload.get("imageAnalysis"))
    visual_features = f"{style.visual_features}；风格提示强度 {strength:.2f}：{strength_label}"
    application_scenario = output.label

    if image_analysis and image_analysis.get("hasUploadedImage") == "true":
        visual_features += f"；参考图本地基础统计：{image_analysis.get('colors')}，{image_analysis.get('composition')}"
        application_scenario += f"；提示词参考信息：{image_analysis.get('transferableElements')}"

    return {
        "title": f"{theme} · {style.name}",
        "cultureSource": style.culture_source,
        "visualFeatures": visual_features,
        "symbolicMeaning": style.symbolic_meaning,
        "applicationScenario": application_scenario,
    }
