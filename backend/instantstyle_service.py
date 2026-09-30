from __future__ import annotations

import importlib.util
import os
import re
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Mapping, Optional

from image_analyzer import analyze_image, get_vision_provider
from image_provider import output_url, save_mock_svg, save_uploaded_image
from prompt_builder import build_culture_card, build_enhanced_prompt, build_negative_prompt
from style_config import (
    OUTPUT_DIR,
    PROJECT_ROOT,
    STYLE_REFS_DIR,
    StyleConfig,
    ensure_runtime_dirs,
    get_style,
    missing_style_refs,
    resolve_style_ref_path,
    style_refs_ready,
)

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def _configure_project_caches() -> None:
    cache_root = PROJECT_ROOT / ".cache"
    os.environ.setdefault("HF_HOME", str(cache_root / "huggingface"))
    os.environ.setdefault("HF_HUB_CACHE", str(cache_root / "huggingface" / "hub"))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(cache_root / "huggingface" / "hub"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(cache_root / "transformers"))
    os.environ.setdefault("TORCH_HOME", str(cache_root / "torch"))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_root))
    os.environ.setdefault("PIP_CACHE_DIR", str(cache_root / "pip"))
    for path in [
        cache_root,
        cache_root / "huggingface" / "hub",
        cache_root / "transformers",
        cache_root / "torch",
        cache_root / "pip",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def _load_local_env(env_path: Path) -> None:
    _configure_project_caches()
    if load_dotenv is not None:
        load_dotenv(env_path, override=True)
        _configure_project_caches()
        return
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")
    _configure_project_caches()


_load_local_env(Path(__file__).resolve().parent / ".env")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip():
            return value.strip()
    return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    try:
        return int(value) if value is not None and value.strip() else default
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    try:
        return float(value) if value is not None and value.strip() else default
    except ValueError:
        return default


def _available_system_memory_gib() -> float | None:
    """Return available physical memory without adding a runtime dependency."""
    try:
        if os.name == "nt":
            import ctypes

            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatusEx()
            status.dwLength = ctypes.sizeof(MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return round(status.ullAvailPhys / (1024 ** 3), 2)
        else:
            page_size = os.sysconf("SC_PAGE_SIZE")
            available_pages = os.sysconf("SC_AVPHYS_PAGES")
            return round((page_size * available_pages) / (1024 ** 3), 2)
    except (AttributeError, OSError, ValueError):
        return None
    return None


def _resolve_generation_provider() -> str:
    provider = os.getenv("GENERATION_PROVIDER")
    if provider:
        return provider.strip().lower()
    return "mock" if _env_bool("MOCK_MODE", True) else "instantstyle"


class InstantStyleSettings:
    def __init__(self) -> None:
        self.mock_mode = _env_bool("MOCK_MODE", True)
        self.fast_demo_mode = _env_bool("FAST_DEMO_MODE", False)
        self.generation_provider = _resolve_generation_provider()
        self.enable_openai_image = _env_bool("ENABLE_OPENAI_IMAGE", False)
        self.fallback_to_mock = _env_bool("ALLOW_MOCK_FALLBACK", False)
        self.backend_host = os.getenv("BACKEND_HOST", "http://127.0.0.1:8000")
        self.base_model_path = _env_first("MODEL_ID", "INSTANTSTYLE_BASE_MODEL", default="stabilityai/stable-diffusion-xl-base-1.0")
        self.model_variant = _env_first("MODEL_VARIANT", "INSTANTSTYLE_MODEL_VARIANT", default="")
        self.ip_adapter_repo = _env_first("IP_ADAPTER_REPO", "INSTANTSTYLE_IP_ADAPTER_REPO", default="h94/IP-Adapter")
        self.ip_adapter_subfolder = _env_first("IP_ADAPTER_SUBFOLDER", "INSTANTSTYLE_IP_ADAPTER_SUBFOLDER", default="sdxl_models")
        self.ip_adapter_weight_name = _env_first("IP_ADAPTER_WEIGHT", "INSTANTSTYLE_IP_ADAPTER_WEIGHT", default="ip-adapter_sdxl.bin")
        self.device = os.getenv("INSTANTSTYLE_DEVICE", "cuda")
        self.image_width = _env_int("IMAGE_WIDTH", 768)
        self.image_height = _env_int("IMAGE_HEIGHT", 768)
        self.guidance_scale = _env_float("GUIDANCE_SCALE", _env_float("INSTANTSTYLE_GUIDANCE_SCALE", 5.0))
        self.num_inference_steps = _env_int("NUM_INFERENCE_STEPS", _env_int("INSTANTSTYLE_STEPS", 20))
        seed = os.getenv("INSTANTSTYLE_SEED", "42")
        self.seed = int(seed) if seed else None
        self.low_vram = _env_bool("LOW_VRAM", True)

class InstantStyleGenerationError(RuntimeError):
    def __init__(self, stage: str, message: str, suggestion: str, exc: BaseException | None = None) -> None:
        self.stage = stage
        self.exception_type = type(exc).__name__ if exc else "RuntimeError"
        self.original_message = str(exc) if exc else message
        self.suggestion = suggestion
        self.traceback = traceback.format_exc() if exc else ""
        super().__init__(f"[{stage}] {message}: {self.original_message}. Suggestion: {suggestion}")

    def to_debug(self, settings: InstantStyleSettings) -> dict[str, object]:
        return {
            "stage": self.stage,
            "provider": "instantstyle",
            "mockMode": settings.mock_mode,
            "fastDemoMode": settings.fast_demo_mode,
            "exceptionType": self.exception_type,
            "message": self.original_message,
            "suggestion": self.suggestion,
        }


_PIPELINE_CACHE: dict[str, object] = {}
_PIPELINE_LOCK = Lock()


def reload_settings() -> InstantStyleSettings:
    _load_local_env(Path(__file__).resolve().parent / ".env")
    return InstantStyleSettings()


class InstantStyleService:
    def __init__(self, settings: Optional[InstantStyleSettings] = None) -> None:
        self.settings = settings or InstantStyleSettings()

    def refresh_settings(self) -> None:
        self.settings = reload_settings()

    @property
    def mode(self) -> str:
        if self.settings.fast_demo_mode:
            return "fast_demo"
        if self.settings.mock_mode:
            return "mock"
        return self.settings.generation_provider

    def generate(self, payload: Mapping[str, object], *, base_url: str) -> dict[str, object]:
        self.refresh_settings()
        enriched_payload = dict(payload)
        image_analysis = analyze_image(str(enriched_payload.get("uploadedImage") or "") or None)
        enriched_payload["imageAnalysis"] = image_analysis
        style = get_style(str(enriched_payload.get("style") or "zhuxianzhen"))
        enhanced_prompt = build_enhanced_prompt(enriched_payload, style)
        negative_prompt = build_negative_prompt(str(enriched_payload.get("negativePrompt") or ""))
        culture_card = build_culture_card(enriched_payload, style)

        if self.settings.fast_demo_mode:
            return self._generate_mock_response(enriched_payload, base_url, enhanced_prompt, culture_card, "fast_demo", image_analysis, None)
        if self.settings.mock_mode or self.settings.generation_provider == "mock":
            return self._generate_mock_response(enriched_payload, base_url, enhanced_prompt, culture_card, "mock", image_analysis, None)
        if self.settings.generation_provider != "instantstyle":
            error = f"Unsupported GENERATION_PROVIDER={self.settings.generation_provider!r}."
            return self._error_response(enhanced_prompt, culture_card, image_analysis, error, "config", "Use GENERATION_PROVIDER=instantstyle or mock.")

        try:
            result = generate_with_instantstyle(enriched_payload, enhanced_prompt, negative_prompt, style, image_analysis=image_analysis)
            if result.get("imageUrl", "").startswith(self.settings.backend_host):
                result["imageUrl"] = result["imageUrl"].replace(self.settings.backend_host.rstrip("/"), base_url.rstrip("/"), 1)
            return {
                "success": True,
                "imageUrl": result["imageUrl"],
                "enhancedPrompt": enhanced_prompt,
                "mode": "instantstyle",
                "cultureCard": culture_card,
                "imageAnalysis": image_analysis,
                "error": None,
                "usedStyleRef": result.get("usedStyleRef"),
                "engine": result.get("engine"),
                "device": result.get("device"),
                "steps": result.get("steps"),
                "width": result.get("width"),
                "height": result.get("height"),
            }
        except InstantStyleGenerationError as exc:
            if self.settings.fallback_to_mock:
                return self._generate_mock_response(enriched_payload, base_url, enhanced_prompt, culture_card, "mock_fallback", image_analysis, str(exc))
            return {
                "success": False,
                "imageUrl": "",
                "enhancedPrompt": enhanced_prompt,
                "mode": "error",
                "cultureCard": culture_card,
                "imageAnalysis": image_analysis,
                "error": str(exc),
                "debug": exc.to_debug(self.settings),
            }
        except Exception as exc:
            wrapped = InstantStyleGenerationError("unknown", "InstantStyle unexpected failure", "Check backend logs for traceback.", exc)
            if self.settings.fallback_to_mock:
                return self._generate_mock_response(enriched_payload, base_url, enhanced_prompt, culture_card, "mock_fallback", image_analysis, str(wrapped))
            return {
                "success": False,
                "imageUrl": "",
                "enhancedPrompt": enhanced_prompt,
                "mode": "error",
                "cultureCard": culture_card,
                "imageAnalysis": image_analysis,
                "error": str(wrapped),
                "debug": wrapped.to_debug(self.settings),
            }

    def _generate_mock_response(self, payload: Mapping[str, object], base_url: str, enhanced_prompt: str, culture_card: Mapping[str, str], mode: str, image_analysis: Mapping[str, str], error: Optional[str]) -> dict[str, object]:
        style = get_style(str(payload.get("style") or "zhuxianzhen"))
        if payload.get("uploadedImage"):
            save_uploaded_image(str(payload.get("uploadedImage") or ""))
        output_path = save_mock_svg(style=style, payload=payload, enhanced_prompt=enhanced_prompt, culture_card=culture_card)
        return {
            "success": True,
            "imageUrl": output_url(base_url, output_path),
            "enhancedPrompt": enhanced_prompt,
            "mode": mode,
            "cultureCard": culture_card,
            "imageAnalysis": image_analysis,
            "error": error,
        }

    def _error_response(self, enhanced_prompt: str, culture_card: Mapping[str, str], image_analysis: Mapping[str, str], error: str, stage: str, suggestion: str) -> dict[str, object]:
        return {
            "success": False,
            "imageUrl": "",
            "enhancedPrompt": enhanced_prompt,
            "mode": "error",
            "cultureCard": culture_card,
            "imageAnalysis": image_analysis,
            "error": error,
            "debug": {
                "stage": stage,
                "provider": self.settings.generation_provider,
                "mockMode": self.settings.mock_mode,
                "fastDemoMode": self.settings.fast_demo_mode,
                "suggestion": suggestion,
            },
        }

    def health(self) -> dict[str, object]:
        self.refresh_settings()
        diagnostics = inspect_runtime(self.settings)
        return {
            "status": "ok",
            "mode": self.mode,
            "mockMode": self.settings.mock_mode,
            "fastDemoMode": self.settings.fast_demo_mode,
            "generationProvider": self.settings.generation_provider,
            "torchAvailable": diagnostics["torchAvailable"],
            "cudaAvailable": diagnostics["cudaAvailable"],
            "cudaDevice": diagnostics["cudaDevice"],
            "diffusersAvailable": diagnostics["diffusersAvailable"],
            "transformersAvailable": diagnostics["transformersAvailable"],
            "accelerateAvailable": diagnostics["accelerateAvailable"],
            "styleRefsReady": diagnostics["styleRefsReady"],
            "styleRefsMissing": diagnostics["styleRefsMissing"],
            "instantStyleReady": diagnostics["instantStyleReady"],
            "visionProvider": get_vision_provider(),
            "message": _health_message(self.settings, diagnostics),
        }

    def _load_pipeline(self) -> tuple[object, object]:
        return load_instantstyle_pipeline(self.settings)


def generate_with_instantstyle(
    request_data: Mapping[str, object],
    enhanced_prompt: str,
    negative_prompt: str,
    style_config: StyleConfig,
    image_analysis: Optional[Mapping[str, str]] = None,
    settings: Optional[InstantStyleSettings] = None,
) -> dict[str, object]:
    settings = settings or reload_settings()
    if settings.mock_mode or settings.fast_demo_mode or settings.generation_provider != "instantstyle":
        raise InstantStyleGenerationError(
            "config",
            "Real InstantStyle mode is not enabled",
            "Set MOCK_MODE=false, FAST_DEMO_MODE=false, GENERATION_PROVIDER=instantstyle.",
        )

    style_ref_path = resolve_style_ref_path(style_config)
    if style_ref_path is None:
        raise InstantStyleGenerationError("load_style_ref", f"Missing style reference image {style_config.filename}", f"Put {style_config.filename} into {STYLE_REFS_DIR}.")

    try:
        from PIL import Image
        style_image = Image.open(style_ref_path).convert("RGB")
    except Exception as exc:
        raise InstantStyleGenerationError("load_style_ref", f"Cannot read style reference image {style_ref_path}", "Verify the PNG file is valid.", exc) from exc

    pipe, torch = load_instantstyle_pipeline(settings)
    style_strength = _coerce_strength(request_data.get("styleStrength"))
    scale = {"up": {"block_0": [0.0, style_strength, 0.0]}}
    try:
        pipe.set_ip_adapter_scale(scale)
    except Exception as exc:
        _append_runtime_log(f"set_ip_adapter_scale dict failed, falling back to scalar {style_strength}: {type(exc).__name__}: {exc}")
        try:
            pipe.set_ip_adapter_scale(style_strength)
        except Exception as inner:
            raise InstantStyleGenerationError("set_ip_adapter_scale", "IP-Adapter scale configuration failed", "Upgrade diffusers or use a compatible IP-Adapter weight.", inner) from inner

    width = settings.image_width
    height = settings.image_height
    steps = settings.num_inference_steps
    if settings.low_vram:
        width = min(width, 768)
        height = min(height, 768)
        steps = min(steps, 20)

    generator = None
    if settings.seed is not None:
        try:
            generator = torch.Generator(device=settings.device).manual_seed(settings.seed)
        except Exception:
            generator = torch.Generator(device="cpu").manual_seed(settings.seed)

    try:
        result = pipe(
            prompt=enhanced_prompt,
            negative_prompt=negative_prompt,
            ip_adapter_image=style_image,
            num_inference_steps=steps,
            guidance_scale=settings.guidance_scale,
            width=width,
            height=height,
            generator=generator,
        ).images[0]
    except Exception as exc:
        raise InstantStyleGenerationError("generate", "StableDiffusionXLPipeline generation failed", "If this is CUDA OOM, set IMAGE_WIDTH=512, IMAGE_HEIGHT=512, INSTANTSTYLE_STEPS=10, LOW_VRAM=true.", exc) from exc

    try:
        ensure_runtime_dirs()
        theme = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]+", "-", str(request_data.get("theme") or "theme")).strip("-")[:32] or "theme"
        filename = f"instantstyle_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{style_config.id}_{theme}.png"
        output_path = OUTPUT_DIR / filename
        result.save(output_path)
    except Exception as exc:
        raise InstantStyleGenerationError("save_output", "Saving generated image failed", f"Verify backend outputs directory is writable: {OUTPUT_DIR}", exc) from exc

    return {
        "success": True,
        "imageUrl": output_url(settings.backend_host, output_path),
        "mode": "instantstyle",
        "usedStyleRef": str(style_ref_path),
        "engine": "StableDiffusionXLPipeline + IP-Adapter",
        "device": settings.device,
        "steps": steps,
        "width": width,
        "height": height,
        "outputPath": str(output_path),
        "imageAnalysis": image_analysis,
    }


def load_instantstyle_pipeline(settings: Optional[InstantStyleSettings] = None) -> tuple[object, object]:
    settings = settings or reload_settings()
    cache_key = "|".join([
        settings.base_model_path,
        settings.ip_adapter_repo,
        settings.ip_adapter_subfolder,
        settings.ip_adapter_weight_name,
        settings.model_variant or "no_variant",
        str(settings.low_vram),
        settings.device,
    ])
    with _PIPELINE_LOCK:
        cached_pipe = _PIPELINE_CACHE.get(cache_key)
        cached_torch = _PIPELINE_CACHE.get(f"{cache_key}:torch")
        if cached_pipe is not None and cached_torch is not None:
            return cached_pipe, cached_torch

        try:
            import torch
            from diffusers import StableDiffusionXLPipeline
        except Exception as exc:
            raise InstantStyleGenerationError("load_pipeline", "Missing torch or diffusers runtime", "Install torch, diffusers, transformers, accelerate and safetensors in backend venv.", exc) from exc

        device = settings.device.strip().lower()
        if device.startswith("cuda") and not torch.cuda.is_available():
            raise InstantStyleGenerationError("load_pipeline", "CUDA is not available", "Use MOCK_MODE=true or deploy to a CUDA GPU server.")

        ready, detail = _ip_adapter_image_encoder_ready(settings)
        if not ready:
            raise InstantStyleGenerationError("load_ip_adapter", "IP-Adapter image_encoder weights are missing", "Download h94/IP-Adapter sdxl_models/image_encoder/* into D:\\wenmai-huazhang\\.cache\\huggingface before real generation.", RuntimeError(detail))

        try:
            kwargs: dict[str, object] = {
                "torch_dtype": torch.float16 if device.startswith("cuda") else torch.float32,
                "add_watermarker": False,
                "use_safetensors": True,
            }
            if settings.model_variant:
                kwargs["variant"] = settings.model_variant
            pipe = StableDiffusionXLPipeline.from_pretrained(settings.base_model_path, **kwargs)
        except Exception as exc:
            raise InstantStyleGenerationError("load_pipeline", f"SDXL model load/download failed for {settings.base_model_path}", "Check Hugging Face network/cache. For local cache, keep files under D:\\wenmai-huazhang\\.cache\\huggingface.", exc) from exc

        try:
            if hasattr(pipe, "enable_vae_tiling"):
                pipe.enable_vae_tiling()
            if settings.low_vram and hasattr(pipe, "enable_attention_slicing"):
                pipe.enable_attention_slicing()
            if settings.low_vram and hasattr(pipe, "enable_model_cpu_offload") and device.startswith("cuda"):
                pipe.enable_model_cpu_offload()
            else:
                pipe.to(device)
        except Exception as exc:
            raise InstantStyleGenerationError("load_pipeline", "Pipeline device/offload setup failed", "Check accelerate installation and GPU memory.", exc) from exc
        try:
            pipe.load_ip_adapter(settings.ip_adapter_repo, subfolder=settings.ip_adapter_subfolder, weight_name=settings.ip_adapter_weight_name)
        except Exception as exc:
            raise InstantStyleGenerationError("load_ip_adapter", "IP-Adapter weight load failed", "Check IP_ADAPTER_REPO, IP_ADAPTER_SUBFOLDER, IP_ADAPTER_WEIGHT and Hugging Face cache/network.", exc) from exc

        if not hasattr(pipe, "set_ip_adapter_scale"):
            raise InstantStyleGenerationError("load_ip_adapter", "Current diffusers pipeline does not support set_ip_adapter_scale", "Upgrade diffusers to a version supporting IP-Adapter scale control.")

        _PIPELINE_CACHE[cache_key] = pipe
        _PIPELINE_CACHE[f"{cache_key}:torch"] = torch
        return pipe, torch


def _ip_adapter_image_encoder_ready(settings: InstantStyleSettings) -> tuple[bool, str]:
    hub_value = os.environ.get("HF_HUB_CACHE") or os.environ.get("HUGGINGFACE_HUB_CACHE")
    hub = Path(hub_value.strip()) if hub_value else (PROJECT_ROOT / ".cache" / "huggingface" / "hub")
    repo_dir = hub / "models--h94--IP-Adapter"
    if settings.ip_adapter_repo != "h94/IP-Adapter":
        return True, "custom repo; skip local preflight"
    if not repo_dir.exists():
        return False, f"IP-Adapter cache directory not found: {repo_dir}"
    candidates = list(repo_dir.glob("snapshots/*/sdxl_models/image_encoder/*"))
    weight_files = [p for p in candidates if p.is_file() and p.suffix in {".bin", ".safetensors"} and p.stat().st_size > 1024 * 1024]
    if not weight_files:
        return False, f"Missing h94/IP-Adapter sdxl_models/image_encoder weight file under {repo_dir}. Only config.json/incomplete blobs are present."
    return True, str(weight_files[0])

def inspect_runtime(settings: Optional[InstantStyleSettings] = None) -> dict[str, object]:
    settings = settings or reload_settings()
    torch_available = _module_available("torch")
    diffusers_available = _module_available("diffusers")
    transformers_available = _module_available("transformers")
    accelerate_available = _module_available("accelerate")
    cuda_available = False
    cuda_device = ""
    if torch_available:
        try:
            import torch
            cuda_available = bool(torch.cuda.is_available())
            cuda_device = torch.cuda.get_device_name(0) if cuda_available else "NO CUDA"
        except Exception as exc:
            cuda_device = f"torch import/check failed: {exc}"
    missing_refs = missing_style_refs()
    refs_ready = not missing_refs
    ip_encoder_ready, ip_encoder_detail = _ip_adapter_image_encoder_ready(settings)
    memory_available_gib = _available_system_memory_gib()
    # Conservative project preflight for the first SDXL/IP-Adapter load when
    # CPU offload is enabled. This is a local safety threshold, not a vendor
    # minimum specification.
    required_free_memory_gib = 5.0
    system_memory_ready = memory_available_gib is None or memory_available_gib >= required_free_memory_gib
    instant_ready = torch_available and diffusers_available and transformers_available and refs_ready and ip_encoder_ready
    instant_ready = instant_ready and system_memory_ready
    if settings.device.strip().lower().startswith("cuda"):
        instant_ready = instant_ready and cuda_available
    return {
        "torchAvailable": torch_available,
        "cudaAvailable": cuda_available,
        "cudaDevice": cuda_device,
        "diffusersAvailable": diffusers_available,
        "transformersAvailable": transformers_available,
        "accelerateAvailable": accelerate_available,
        "styleRefsReady": refs_ready,
        "styleRefsMissing": missing_refs,
        "ipAdapterImageEncoderReady": ip_encoder_ready,
        "ipAdapterImageEncoderDetail": ip_encoder_detail,
        "systemMemoryAvailableGiB": memory_available_gib,
        "requiredFreeMemoryGiB": required_free_memory_gib,
        "systemMemoryReady": system_memory_ready,
        "instantStyleReady": bool(instant_ready),
    }


def _health_message(settings: InstantStyleSettings, diagnostics: Mapping[str, object]) -> str:
    if settings.fast_demo_mode:
        return "Fast Demo mode is active; real InstantStyle will not be called."
    if settings.mock_mode or settings.generation_provider == "mock":
        return "Mock mode is active; real InstantStyle will not be called."
    if settings.generation_provider != "instantstyle":
        return f"Unsupported GENERATION_PROVIDER={settings.generation_provider!r}."
    if not diagnostics["torchAvailable"]:
        return "Real mode unavailable: torch is not installed."
    if settings.device.strip().lower().startswith("cuda") and not diagnostics["cudaAvailable"]:
        return "Real mode unavailable: CUDA is not available for SDXL / InstantStyle."
    if not diagnostics["diffusersAvailable"]:
        return "Real mode unavailable: diffusers is not installed."
    if not diagnostics["transformersAvailable"]:
        return "Real mode unavailable: transformers is not installed."
    if not diagnostics["styleRefsReady"]:
        return "Real mode unavailable: missing style_refs " + ", ".join(diagnostics["styleRefsMissing"])
    if not diagnostics.get("ipAdapterImageEncoderReady", False):
        return "Real mode unavailable: IP-Adapter image_encoder weights are missing. " + str(diagnostics.get("ipAdapterImageEncoderDetail", ""))
    memory_available = diagnostics.get("systemMemoryAvailableGiB")
    if isinstance(memory_available, (int, float)) and not diagnostics.get("systemMemoryReady", True):
        return f"Real mode unavailable: 当前可用内存约 {memory_available:.2f} GiB；本项目首次加载预检要求至少 5 GiB 可用内存。"
    return "InstantStyle real generation environment is preliminarily available."

def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _coerce_strength(value: object) -> float:
    try:
        strength = float(value)
    except (TypeError, ValueError):
        strength = 0.65
    if strength > 1:
        strength = strength / 100.0
    return max(0.0, min(strength, 1.5))


def _append_runtime_log(message: str) -> None:
    log_path = PROJECT_ROOT / "logs" / "instantstyle_runtime.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")
