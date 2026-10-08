from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

import requests


DEFAULT_MODEL = "qwen3-vl:4b-instruct-q4_K_M"
DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_CONTEXT_TOKENS = 8192
DEFAULT_IMAGE_LIMIT_BYTES = 20 * 1024 * 1024


VISION_SYSTEM_PROMPT = """你是纹脉华章的传统文化视觉解读助手。先仔细观察实际生成图片，再结合用户主题和给定风格资料输出 JSON。
observed_subjects 只列真实可见的实体；visual_features、composition、dominant_colors 只描述实际画面。不得把主题要求当成已经看见的内容。
culture_interpretation 从至少两项可见细节出发写80至180字审美解读。区分画面观察和文化联想，以准确、保守的表述为准，不编造历史出处、年份、民俗寓意、非遗身份或艺术家归属。不必引用诗文；如引用只能使用给定 literaryReferences 的准确原文与篇名。
传统风格是本次 AI 视觉转化的方向，不据此认定作品是历史实物或手工制品。只使用所选风格适用的材质语言，不把青花写成刺绣。看不清的细节不要猜测。
应用建议用“可用于”“适用于”，不声称已落地。全部简体中文，严格按要求的JSON字段返回，不输出Markdown。
"""


VISION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "observed_subjects": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 5,
        },
        "theme_summary": {"type": "string"},
        "dominant_colors": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 4,
        },
        "composition": {"type": "string"},
        "visual_features": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 5,
        },
        "style_interpretation": {"type": "string"},
        "culture_interpretation": {"type": "string", "minLength": 80, "maxLength": 180},
        "recommended_scenes": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 3,
        },
        "theme_alignment": {"type": "string", "enum": ["高", "中", "低"]},
        "style_alignment": {"type": "string", "enum": ["明显", "基本", "较弱"]},
    },
    "required": [
        "title",
        "observed_subjects",
        "theme_summary",
        "dominant_colors",
        "composition",
        "visual_features",
        "style_interpretation",
        "culture_interpretation",
        "recommended_scenes",
        "theme_alignment",
        "style_alignment",
    ],
}


class VisionAnalysisError(RuntimeError):
    pass


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_context(style_library_data: Mapping[str, object]) -> dict[str, object]:
    safe: dict[str, object] = {}
    for key in (
        "id",
        "name",
        "category",
        "shortDescription",
        "cultureSource",
        "cultureInterpretationGuide",
        "literaryReferences",
    ):
        value = style_library_data.get(key)
        if isinstance(value, str):
            safe[key] = value.strip()[:400]

    for key in ("visualFeatures", "recommendedScenes", "literaryReferences"):
        value = style_library_data.get(key)
        if isinstance(value, (list, tuple)):
            safe[key] = [str(item).strip()[:80] for item in value[:5] if str(item).strip()]
        elif isinstance(value, str) and value.strip():
            safe[key] = value.strip()[:400]
    return safe


def _remove_unverified_citation_sentences(
    analysis: dict[str, Any],
    style_library_data: Mapping[str, object],
) -> dict[str, Any]:
    """Keep literary allusions vivid while preventing invented quotations."""
    references = style_library_data.get("literaryReferences") or []
    if isinstance(references, str):
        references = [references]
    reference_texts = [str(item).strip() for item in references if str(item).strip()]
    if not reference_texts:
        reference_texts = []

    result = dict(analysis)
    for field in ("culture_interpretation", "style_interpretation"):
        text = result.get(field)
        if not isinstance(text, str) or not text:
            continue
        sentences = re.split(r"(?<=[。！？])", text)
        kept: list[str] = []
        for sentence in sentences:
            title_match = re.search(r"《([^》]+)》", sentence)
            quoted = re.findall(r"[“‘「]([^”’」]+)[”’」]", sentence)
            vague_attribution = re.search(r"古人所言|古语云|诗云|先贤云|古诗有云", sentence)
            mentions_author = any(
                author and author in sentence
                for author in (str(reference).split("《", 1)[0].strip() for reference in reference_texts)
            )
            if vague_attribution and not title_match and not mentions_author:
                continue
            if not title_match and not mentions_author:
                kept.append(sentence)
                continue
            verified = False
            for reference in reference_texts:
                title = re.search(r"《([^》]+)》", reference)
                title_matches = bool(title and title.group(1) in sentence)
                author = reference.split("《", 1)[0].strip()
                author_matches = bool(author and author in sentence)
                if not title_matches and not author_matches:
                    continue
                tail = re.split(r"[：:]", reference, maxsplit=1)
                canonical_text = tail[1] if len(tail) == 2 else reference
                if quoted and any(quote in canonical_text for quote in quoted):
                    verified = True
                    break
            if verified:
                kept.append(sentence)
        result[field] = "".join(kept).strip()
    return result


def _normalise_analysis(
    value: object,
    style_library_data: Mapping[str, object],
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise VisionAnalysisError("Qwen3-VL 返回内容不是 JSON 对象。")

    required = VISION_JSON_SCHEMA["required"]
    missing = [key for key in required if key not in value]
    if missing:
        raise VisionAnalysisError("Qwen3-VL 返回字段不完整。")

    string_fields = (
        "title",
        "theme_summary",
        "composition",
        "style_interpretation",
        "culture_interpretation",
    )
    result: dict[str, object] = {}
    for key in string_fields:
        item = value.get(key)
        if not isinstance(item, str) or not item.strip():
            raise VisionAnalysisError(f"Qwen3-VL 返回字段 {key} 为空。")
        clean_text = item.strip()
        if key == "culture_interpretation" and len(clean_text) < 60:
            raise VisionAnalysisError("Qwen3-VL 文化解读过短，无法形成完整题画短评。")
        result[key] = clean_text[:400]

    array_fields = ("observed_subjects", "dominant_colors", "visual_features", "recommended_scenes")
    style_id = str(style_library_data.get("id") or "").strip()
    style_incompatible_terms = {
        "zhuxianzhen": ("青花瓷", "釉下", "丝线", "针脚", "刺绣", "剪纸镂空"),
        "bianxiu": ("青花瓷", "釉下", "瓷器质感", "木版套色", "剪纸镂空"),
        "songhua": ("青花瓷", "釉下", "丝线", "针脚", "木版套色", "剪纸镂空"),
        "qinghua": ("丝线", "针脚", "针法", "刺绣", "剪纸镂空", "木版套色"),
        "jianzhi": ("青花瓷", "釉下", "丝线", "针脚", "刺绣", "木版套色"),
    }.get(style_id, ())
    limits = {
        "observed_subjects": (2, 5),
        "dominant_colors": (2, 4),
        "visual_features": (3, 5),
        "recommended_scenes": (2, 3),
    }
    for key in array_fields:
        items = value.get(key)
        if not isinstance(items, list):
            raise VisionAnalysisError(f"Qwen3-VL 返回字段 {key} 不是列表。")
        clean_items = [str(item).strip()[:80] for item in items if str(item).strip()]
        if key == "observed_subjects":
            non_subject_markers = (
                "质感", "纹理", "风格", "构图", "色彩", "线条", "效果", "针法", "针脚",
            )
            clean_items = [
                item for item in clean_items
                if not any(marker in item for marker in non_subject_markers)
            ]
        if key == "visual_features":
            clean_items = [
                item for item in clean_items
                if not any(term in item for term in style_incompatible_terms)
            ]
        minimum, maximum = limits[key]
        if len(clean_items) < minimum:
            raise VisionAnalysisError(f"Qwen3-VL 返回字段 {key} 项数不足。")
        result[key] = clean_items[:maximum]

    alignments = {
        "theme_alignment": {"高", "中", "低"},
        "style_alignment": {"明显", "基本", "较弱"},
    }
    for key, allowed in alignments.items():
        item = value.get(key)
        if item not in allowed:
            raise VisionAnalysisError(f"Qwen3-VL 返回字段 {key} 不符合约定枚举。")
        result[key] = item

    return result


class VisionAnalysisService:
    """Local Ollama-backed Qwen3-VL image understanding service."""

    def __init__(self) -> None:
        configured_base = os.getenv("QWEN_VL_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
        self.base_url = configured_base or DEFAULT_BASE_URL
        self.chat_url = (
            self.base_url
            if self.base_url.endswith("/api/chat")
            else f"{self.base_url}/api/chat"
        )
        self.tags_url = self.chat_url[: -len("/api/chat")] + "/api/tags"
        self.model = os.getenv("QWEN_VL_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        self.enabled = _env_bool("QWEN_VL_ENABLED", False)
        self.timeout = max(
            10,
            min(
                600,
                int(float(os.getenv("QWEN_VL_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS)))),
            ),
        )
        self.context_tokens = max(
            2048,
            min(32768, int(os.getenv("QWEN_VL_CONTEXT_TOKENS", str(DEFAULT_CONTEXT_TOKENS)))),
        )
        try:
            configured_temperature = float(os.getenv("QWEN_VL_TEMPERATURE", "0.65"))
        except ValueError:
            configured_temperature = 0.65
        self.temperature = max(0.0, min(1.0, configured_temperature))
        self.max_image_bytes = max(
            1024 * 1024,
            int(os.getenv("QWEN_VL_MAX_IMAGE_BYTES", str(DEFAULT_IMAGE_LIMIT_BYTES))),
        )
        self.session = requests.Session()

    def health(self) -> dict[str, object]:
        if not self.enabled:
            return {
                "enabled": False,
                "available": False,
                "provider": "ollama_local",
                "model": self.model,
                "message": "本地视觉解读未启用。",
            }

        try:
            response = self.session.get(self.tags_url, timeout=3)
            response.raise_for_status()
            body = response.json()
            models = body.get("models") or []
            available = any(
                str(item.get("name") or item.get("model") or "") == self.model
                for item in models
                if isinstance(item, dict)
            )
            return {
                "enabled": True,
                "available": available,
                "provider": "ollama_local",
                "model": self.model,
                "message": "本地 Qwen3-VL 已就绪。" if available else "本地服务可连接，但未找到配置的 Qwen3-VL 模型。",
            }
        except Exception as exc:
            return {
                "enabled": True,
                "available": False,
                "provider": "ollama_local",
                "model": self.model,
                "message": f"本地视觉服务暂不可用：{type(exc).__name__}",
            }

    def analyze(
        self,
        *,
        generated_image_path: str | Path,
        theme: str,
        style_id: str,
        style_name: str,
        style_library_data: Mapping[str, object],
    ) -> dict[str, object]:
        if not self.enabled:
            raise VisionAnalysisError("本地 Qwen3-VL 未启用。")

        image_path = Path(generated_image_path)
        if not image_path.is_file():
            raise VisionAnalysisError("生成图片文件不存在，无法进行本地视觉解读。")

        image_bytes = image_path.read_bytes()
        if not image_bytes:
            raise VisionAnalysisError("生成图片文件为空。")
        if len(image_bytes) > self.max_image_bytes:
            raise VisionAnalysisError("生成图片超过本地视觉分析的大小限制。")

        context = {
            "theme": str(theme or "").strip()[:1200],
            "selected_style_id": str(style_id or "").strip()[:80],
            "selected_style_name": str(style_name or "").strip()[:100],
            "project_style_library_data": _safe_context(style_library_data),
            "literaryReferences": _safe_context(style_library_data).get("literaryReferences", []),
            "output_requirements": {
                "title": "6至14个汉字，概括画面主体",
                "observed_subjects": "2至5项，只列图片中可见主体",
                "theme_summary": "20至40字，概括图片实际呈现的主题",
                "dominant_colors": "2至4项",
                "composition": "20至40字，描述实际构图",
                "visual_features": "3至5条，每条不超过10字，描述实际视觉效果",
                "style_interpretation": "50至90字，从真实画面细节说明气质与风格，不写模板话",
                "culture_interpretation": "90至150字，写成有画面、有情绪的题画短评；至少两项实际可见细节及其关系先行，再由细节引出文化联想与情绪余韵，避免抽象口号和说明书口吻",
                "recommended_scenes": "2至3项，从给定推荐场景中选择或概括",
                "theme_alignment": "高、中、低之一",
                "style_alignment": "明显、基本、较弱之一",
            },
        }
        encoded_image = base64.b64encode(image_bytes).decode("ascii")
        user_content = json.dumps(context, ensure_ascii=False)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": VISION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": user_content,
                    "images": [encoded_image],
                },
            ],
            "format": VISION_JSON_SCHEMA,
            "stream": False,
            "keep_alive": "2m",
            "options": {
                "num_ctx": self.context_tokens,
                "num_predict": 900,
                "temperature": self.temperature,
            },
        }

        try:
            for attempt in range(2):
                retry_instruction = (
                    "\n补充要求：culture_interpretation 请写成 90 至 150 个汉字的完整题画短评，"
                    "以至少两项可见细节及其关系开篇，再写文化联想和情绪余韵；不要用套语凑字数。"
                    if attempt else ""
                )
                payload["messages"][1]["content"] = user_content + retry_instruction
                response = self.session.post(self.chat_url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                body = response.json()
                content = ((body.get("message") or {}).get("content") or "").strip()
                if not content:
                    raise VisionAnalysisError("本地 Qwen3-VL 没有返回解读内容。")
                raw_analysis = json.loads(content)
                if isinstance(raw_analysis, dict):
                    raw_analysis = _remove_unverified_citation_sentences(raw_analysis, style_library_data)
                culture_text = raw_analysis.get("culture_interpretation") if isinstance(raw_analysis, dict) else None
                if attempt == 0 and isinstance(culture_text, str) and len(culture_text.strip()) < 90:
                    continue
                analysis = _normalise_analysis(raw_analysis, style_library_data)
                break
        except VisionAnalysisError:
            raise
        except requests.RequestException as exc:
            raise VisionAnalysisError(f"本地 Qwen3-VL 请求失败：{type(exc).__name__}") from exc
        except (ValueError, TypeError, KeyError) as exc:
            raise VisionAnalysisError("本地 Qwen3-VL 返回的 JSON 无法解析或字段不符合约定。") from exc

        return {
            "analysis": analysis,
            "raw_analysis": raw_analysis,
            "metadata": {
                "provider": "ollama_local",
                "model": body.get("model") or self.model,
                "input_image_count": 1,
                "input_image_bytes": len(image_bytes),
                "total_duration_ns": body.get("total_duration"),
                "load_duration_ns": body.get("load_duration"),
                "prompt_eval_count": body.get("prompt_eval_count"),
                "eval_count": body.get("eval_count"),
            },
        }
