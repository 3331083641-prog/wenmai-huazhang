from __future__ import annotations

from typing import Mapping

from instantstyle_service import InstantStyleGenerationError, generate_with_instantstyle, inspect_runtime, reload_settings
from style_config import StyleConfig

from .base import ImageProvider, ProviderError


class InstantStyleProvider(ImageProvider):
    name = "instantstyle"

    def is_available(self) -> tuple[bool, str]:
        try:
            settings = reload_settings()
            settings.mock_mode = False
            settings.fast_demo_mode = False
            settings.generation_provider = "instantstyle"
            diagnostics = inspect_runtime(settings)
            if not diagnostics.get("torchAvailable"):
                return False, "torch 未安装"
            if settings.device.strip().lower().startswith("cuda") and not diagnostics.get("cudaAvailable"):
                return False, "CUDA 不可用，无法运行本地 SDXL / InstantStyle"
            if not diagnostics.get("diffusersAvailable"):
                return False, "diffusers 未安装"
            if not diagnostics.get("transformersAvailable"):
                return False, "transformers 未安装"
            if not diagnostics.get("styleRefsReady"):
                return False, "风格参考图缺失: " + ", ".join(diagnostics.get("styleRefsMissing") or [])
            if not diagnostics.get("ipAdapterImageEncoderReady", True):
                return False, "IP-Adapter image_encoder 权重缺失: " + str(diagnostics.get("ipAdapterImageEncoderDetail", ""))
            memory_available = diagnostics.get("systemMemoryAvailableGiB")
            required_memory = diagnostics.get("requiredFreeMemoryGiB", 5.0)
            if isinstance(memory_available, (int, float)) and not diagnostics.get("systemMemoryReady", True):
                return False, f"当前系统可用内存约 {memory_available:.2f} GiB；本项目为首次加载设置的预检值为 {required_memory} GiB。释放内存后刷新页面重试。"
            return True, "InstantStyle 本地环境初步可用，模型将在首次生成时懒加载"
        except Exception as exc:
            return False, f"InstantStyle 环境检查失败: {exc}"

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
        try:
            settings = reload_settings()
            settings.mock_mode = False
            settings.fast_demo_mode = False
            settings.generation_provider = "instantstyle"
            result = generate_with_instantstyle(
                request_data,
                enhanced_prompt,
                negative_prompt,
                style_config,
                image_analysis=image_analysis,
                settings=settings,
            )
            image_url = str(result.get("imageUrl") or "")
            if image_url.startswith("http://127.0.0.1:8000"):
                image_url = image_url.replace("http://127.0.0.1:8000", base_url.rstrip("/"), 1)
            result.update({
                "success": True,
                "imageUrl": image_url,
                "mode": self.name,
                "provider": self.name,
                "model": "SDXL + InstantStyle / IP-Adapter",
                "debug": {"provider": self.name, "stage": "generate", "engine": result.get("engine")},
                "localPath": result.get("outputPath") or result.get("localPath"),
            })
            return result
        except InstantStyleGenerationError as exc:
            raise ProviderError(self.name, exc.stage, str(exc), exc.suggestion) from exc
        except Exception as exc:
            raise ProviderError(self.name, "generate", str(exc), "检查本地 SDXL、IP-Adapter、显存与内存；也可切回阿里云百炼 Qwen Image 3.0。") from exc
