from __future__ import annotations

import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Mapping

from image_provider import output_url
from style_config import OUTPUT_DIR, StyleConfig, ensure_runtime_dirs

from .base import ImageProvider, ProviderError


class OpenAIImageProvider(ImageProvider):
    name = "openai_image"

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1").strip() or "gpt-image-1"
        self.size = os.getenv("OPENAI_IMAGE_SIZE", "1024x1024").strip() or "1024x1024"

    def is_available(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "缺少 API Key"
        try:
            import openai  # noqa: F401
        except Exception:
            return False, "缺少 openai Python SDK，请运行 pip install -r requirements.txt"
        return True, f"OpenAI 图像生成可用，模型 {self.model}"

    def generate(
        self,
        request_data: Mapping[str, object],
        enhanced_prompt: str,
        negative_prompt: str,
        style_config: StyleConfig,
        image_analysis: Mapping[str, str],
        culture_card: Mapping[str, str],
        *,
        base_url: str,
    ) -> dict[str, object]:
        available, message = self.is_available()
        if not available:
            raise ProviderError(self.name, "config", message, "在 backend/.env 填写 OPENAI_API_KEY，或切换其他 Provider。")

        try:
            from openai import OpenAI
        except Exception as exc:
            raise ProviderError(self.name, "import", str(exc), "安装 openai Python SDK。") from exc

        prompt = enhanced_prompt if not negative_prompt else f"{enhanced_prompt}\nAvoid: {negative_prompt}"
        try:
            client = OpenAI(api_key=self.api_key)
            response = client.images.generate(model=self.model, prompt=prompt, size=self.size, n=1)
        except Exception as exc:
            raise ProviderError(self.name, "generate", str(exc), _openai_suggestion(str(exc))) from exc

        try:
            item = response.data[0]
            b64_json = getattr(item, "b64_json", None)
            url = getattr(item, "url", None)
            if b64_json:
                content = base64.b64decode(b64_json)
            elif url:
                import requests
                image_response = requests.get(url, timeout=60)
                image_response.raise_for_status()
                content = image_response.content
            else:
                raise ValueError("OpenAI image response contains neither b64_json nor url")
            local_path = _save_openai_bytes(content, style_config.id)
        except Exception as exc:
            raise ProviderError(self.name, "save_output", str(exc), "OpenAI 生成成功但本地保存失败。") from exc

        return {
            "success": True,
            "imageUrl": output_url(base_url, local_path),
            "mode": self.name,
            "provider": self.name,
            "engine": self.model,
            "localPath": str(local_path),
            "usedStyleRef": style_config.refImagePath,
            "debug": {"provider": self.name, "stage": "done", "size": self.size},
        }


def _save_openai_bytes(content: bytes, style_id: str) -> Path:
    ensure_runtime_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"openai_{stamp}_{style_id}.png"
    output_path.write_bytes(content)
    return output_path


def _openai_suggestion(error_text: str) -> str:
    lower = error_text.lower()
    if "api key" in lower or "authentication" in lower or "unauthorized" in lower:
        return "OPENAI_API_KEY 鉴权失败；确认后端 .env 中 Key 存在且有效。"
    if "billing" in lower or "quota" in lower or "insufficient" in lower:
        return "OpenAI 额度或账单状态不可用；检查账户额度和付款设置。"
    if "organization" in lower or "verified" in lower:
        return "可能需要组织验证或模型权限开通。"
    if "model" in lower and ("not" in lower or "invalid" in lower):
        return "模型不可用或参数不兼容；尝试调整 OPENAI_IMAGE_MODEL 或 OPENAI_IMAGE_SIZE。"
    return "检查 OPENAI_API_KEY、网络、模型权限和请求参数。"