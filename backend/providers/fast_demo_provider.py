from __future__ import annotations

from typing import Mapping

from image_provider import output_url, save_demo_png, save_uploaded_image
from style_config import StyleConfig

from .base import ImageProvider


class FastDemoProvider(ImageProvider):
    name = "fast_demo"

    def is_available(self) -> tuple[bool, str]:
        return True, "快速演示可用"

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
        if request_data.get("uploadedImage"):
            save_uploaded_image(str(request_data.get("uploadedImage") or ""))
        local_path = save_demo_png(style=style_config, payload=request_data, enhanced_prompt=enhanced_prompt, culture_card=culture_card, prefix="fast_demo")
        return {
            "success": True,
            "imageUrl": output_url(base_url, local_path),
            "mode": self.name,
            "provider": self.name,
            "engine": "Fast local demo renderer",
            "localPath": str(local_path),
            "usedStyleRef": style_config.refImagePath,
            "debug": {"provider": self.name, "stage": "generate", "fallbackSafe": True},
        }