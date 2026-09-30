from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Mapping
from uuid import uuid4

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from image_analyzer import analyze_image, get_vision_provider
from dashscope_config import configured_image_model
from prompt_builder import build_culture_card, build_enhanced_prompt, build_negative_prompt, style_strength_text
from providers import DashScopeQwenImageProvider, DashScopeWanxProvider, FastDemoProvider, InstantStyleProvider, MockProvider, OpenAIImageProvider, ProviderError
from services.vision_analysis import VisionAnalysisError, VisionAnalysisService
from style_config import OUTPUT_DIR, PROJECT_ROOT, STYLE_REFS_DIR, get_style, missing_style_refs, style_refs_ready


BACKEND_DIR = Path(__file__).resolve().parent
ENV_PATH = BACKEND_DIR / ".env"


def load_backend_env() -> None:
    if load_dotenv is not None:
        load_dotenv(ENV_PATH, override=True, encoding="utf-8-sig")
        return
    if not ENV_PATH.exists():
        return
    for raw_line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def current_provider_name() -> str:
    provider = os.getenv("GENERATION_PROVIDER", "").strip().lower()
    if provider:
        return provider
    legacy_mock = env_bool("MOCK_MODE", False)
    legacy_fast = env_bool("FAST_DEMO_MODE", False)
    if legacy_fast:
        return "fast_demo"
    if legacy_mock:
        return "mock"
    return "dashscope_qwen_image"


class GenerationService:
    def _providers(self) -> dict[str, object]:
        load_backend_env()
        return {
            "mock": MockProvider(),
            "fast_demo": FastDemoProvider(),
            "dashscope_qwen_image": DashScopeQwenImageProvider(),
            "dashscope_wanx": DashScopeWanxProvider(),
            "openai_image": OpenAIImageProvider(),
            "instantstyle": InstantStyleProvider(),
        }

    def health(self) -> dict[str, object]:
        load_backend_env()
        providers = self._providers()
        selected = current_provider_name()
        provider_status: dict[str, dict[str, object]] = {}
        for name, provider in providers.items():
            try:
                available, message = provider.is_available()
            except Exception as exc:
                available, message = False, f"Provider 状态检查失败: {exc}"
            item: dict[str, object] = {"available": bool(available), "message": message}
            if name in {"dashscope_qwen_image", "dashscope_wanx", "openai_image"}:
                item["hasApiKey"] = bool(getattr(provider, "api_key", ""))
            if name == "dashscope_qwen_image":
                item["hasBaseUrl"] = bool(os.getenv("DASHSCOPE_BASE_URL", "").strip())
                item["model"] = getattr(provider, "model", None)
            if name == "dashscope_wanx" and selected == "dashscope_wanx":
                net = _dashscope_network_status()
                item.update(net)
                if item.get("hasApiKey") and (net.get("networkReachable") is False or net.get("sslOk") is False):
                    item["available"] = False
                    item["message"] = "DashScope API Key 已读取，但当前本机网络/SSL 诊断未通过。"
            if name == "openai_image":
                blocked, detail = _openai_billing_blocked()
                item["billingBlocked"] = blocked
                if blocked:
                    item["available"] = False
                    item["message"] = "OpenAI API billing hard limit reached，需要到 OpenAI Platform Billing 调整额度或补充 credits。"
            if name == "instantstyle":
                try:
                    from instantstyle_service import inspect_runtime, reload_settings
                    settings = reload_settings()
                    settings.mock_mode = False
                    settings.fast_demo_mode = False
                    settings.generation_provider = "instantstyle"
                    diagnostics = inspect_runtime(settings)
                    item.update({
                        "torchAvailable": diagnostics.get("torchAvailable"),
                        "cudaAvailable": diagnostics.get("cudaAvailable"),
                        "cudaDevice": diagnostics.get("cudaDevice"),
                        "diffusersAvailable": diagnostics.get("diffusersAvailable"),
                        "transformersAvailable": diagnostics.get("transformersAvailable"),
                        "ipAdapterImageEncoderReady": diagnostics.get("ipAdapterImageEncoderReady"),
                        "systemMemoryAvailableGiB": diagnostics.get("systemMemoryAvailableGiB"),
                        "requiredFreeMemoryGiB": diagnostics.get("requiredFreeMemoryGiB"),
                        "systemMemoryReady": diagnostics.get("systemMemoryReady"),
                    })
                except Exception as exc:
                    item.update({"torchAvailable": False, "cudaAvailable": False, "diffusersAvailable": False, "message": f"InstantStyle 检查失败: {exc}"})
            provider_status[name] = item

        allow_fallback = env_bool("ALLOW_MOCK_FALLBACK", False)
        selected_status = provider_status.get(selected, {"available": False, "message": "未知 Provider"})
        if selected_status.get("available"):
            message = f"当前主 Provider {selected} 可用。"
        elif allow_fallback:
            message = f"当前主 Provider {selected} 不可用，将回退到 fast_demo/mock。原因：{selected_status.get('message')}"
        else:
            message = f"当前主 Provider {selected} 不可用，且未开启回退。原因：{selected_status.get('message')}"

        return {
            "status": "ok",
            "provider": selected,
            "generationProvider": selected,
            "model": getattr(providers.get(selected), "model", configured_image_model() if selected == "dashscope_qwen_image" else None),
            "allowMockFallback": allow_fallback,
            "providers": provider_status,
            "styleRefsReady": style_refs_ready(),
            "styleRefsMissing": missing_style_refs(),
            "outputsDir": str(OUTPUT_DIR),
            "styleRefsDir": str(STYLE_REFS_DIR),
            "visionProvider": get_vision_provider(),
            "localVisionAnalysis": VisionAnalysisService().health(),
            "message": message,
        }

    def generate(self, payload: Mapping[str, object], *, base_url: str) -> dict[str, object]:
        request_id = uuid4().hex[:12]
        providers = self._providers()
        requested_provider = str(payload.get("generationProvider") or "").strip().lower()
        provider_name = requested_provider or current_provider_name()
        provider = providers.get(provider_name)
        allow_fallback = env_bool("ALLOW_MOCK_FALLBACK", False)

        enriched_payload = dict(payload)
        image_analysis = analyze_image(str(enriched_payload.get("uploadedImage") or "") or None)
        enriched_payload["imageAnalysis"] = image_analysis
        style = get_style(str(enriched_payload.get("style") or "zhuxianzhen"))
        enhanced_prompt = build_enhanced_prompt(enriched_payload, style)
        negative_prompt = build_negative_prompt(str(enriched_payload.get("negativePrompt") or ""))
        culture_card = build_culture_card(enriched_payload, style)
        _, strength_text = style_strength_text(enriched_payload.get("styleStrength"))

        def response_from_provider(result: dict[str, object], real_provider_error: str | None = None) -> dict[str, object]:
            analysis_source = "template_fallback"
            vision_analysis: dict[str, object] | None = None
            vision_analysis_error: str | None = None
            result_mode = str(result.get("mode") or "")
            local_path = str(result.get("localPath") or "")
            # Keep the generation and visual interpretation stages independent:
            # a local VL failure must never discard a successfully generated image.
            if (
                result.get("provider") in {"dashscope_qwen_image", "instantstyle"}
                and result_mode not in {"mock", "fast_demo", "mock_fallback", "fast_demo_fallback"}
                and local_path
            ):
                try:
                    style_library_data = {
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
                    vision_result = VisionAnalysisService().analyze(
                        generated_image_path=local_path,
                        theme=str(enriched_payload.get("theme") or ""),
                        style_id=style.id,
                        style_name=style.name,
                        style_library_data=style_library_data,
                    )
                    vision_analysis = vision_result.get("analysis")  # normalized, safe JSON for UI
                    if isinstance(vision_analysis, dict):
                        analysis_source = "qwen3_vl"
                        culture_card.update({
                            "title": str(vision_analysis.get("title") or culture_card.get("title") or ""),
                            "cultureSource": style.culture_source,
                            "visualFeatures": "、".join(str(item) for item in vision_analysis.get("visual_features", [])),
                            "symbolicMeaning": str(vision_analysis.get("culture_interpretation") or culture_card.get("symbolicMeaning") or ""),
                            "applicationScenario": "、".join(str(item) for item in vision_analysis.get("recommended_scenes", [])),
                        })
                except Exception as exc:
                    # No exception text from a local runtime is exposed to the UI;
                    # keep the image result and mark the documented template fallback.
                    vision_analysis_error = f"{type(exc).__name__}: {str(exc)[:180]}"

            debug = dict(result.get("debug") or {})
            result_provider = str(result.get("provider") or provider_name)
            result_model = result.get("model") or getattr(providers.get(result_provider), "model", None)
            debug.update({
                "requestId": request_id,
                "selectedProvider": provider_name,
                "allowMockFallback": allow_fallback,
                "styleStrengthApplied": True,
                "styleStrengthText": strength_text,
                "negativePromptPreview": negative_prompt[:120],
                "analysisSource": analysis_source,
            })
            response = {
                "success": True,
                "imageUrl": result.get("imageUrl", ""),
                "enhancedPrompt": enhanced_prompt,
                "mode": result.get("mode") or result.get("provider") or provider_name,
                "provider": result_provider,
                "model": result_model,
                "referenceImageUsed": bool(result.get("referenceImageUsed", False)),
                "styleReferenceUsed": result_provider == "instantstyle" and bool(result.get("usedStyleRef")),
                "engine": result.get("engine"),
                "localPath": result.get("localPath"),
                "usedStyleRef": result.get("usedStyleRef"),
                "cultureCard": culture_card,
                "analysisSource": analysis_source,
                "visionAnalysis": vision_analysis,
                "visionAnalysisError": vision_analysis_error,
                "imageAnalysis": image_analysis,
                "realProviderError": real_provider_error,
                "error": None,
                "debug": debug,
            }
            _trace_generate(request_id, enriched_payload, image_analysis, enhanced_prompt, negative_prompt, provider_name, allow_fallback, response)
            return response

        if provider is None:
            error = ProviderError(provider_name, "config", f"未知 GENERATION_PROVIDER={provider_name}", "可选值：dashscope_qwen_image、dashscope_wanx、openai_image、instantstyle、fast_demo、mock。")
        else:
            try:
                available, message = provider.is_available()
                if not available:
                    suggestion = (
                        "填写并校验华北2（北京）业务空间专属 DASHSCOPE_BASE_URL；沿用当前 DASHSCOPE_API_KEY。"
                        if provider_name == "dashscope_qwen_image"
                        else "配置 API Key、依赖或切换 Provider。"
                    )
                    raise ProviderError(provider_name, "availability", message, suggestion)
                result = provider.generate(enriched_payload, enhanced_prompt, negative_prompt, style, image_analysis, culture_card, base_url=base_url)
                return response_from_provider(result)
            except ProviderError as exc:
                error = exc
            except Exception as exc:
                error = ProviderError(provider_name, "generate", str(exc), "查看后端日志并检查 Provider 配置。")

        if allow_fallback:
            fallback_name = "fast_demo" if provider_name != "fast_demo" else "mock"
            fallback = providers[fallback_name]
            fallback_result = fallback.generate(enriched_payload, enhanced_prompt, negative_prompt, style, image_analysis, culture_card, base_url=base_url)
            fallback_result["mode"] = f"{fallback_name}_fallback"
            return response_from_provider(fallback_result, real_provider_error=str(error))

        response = {
            "success": False,
            "imageUrl": "",
            "enhancedPrompt": enhanced_prompt,
            "mode": "error",
            "provider": provider_name,
            "engine": None,
            "localPath": None,
            "usedStyleRef": style.refImagePath,
            "cultureCard": culture_card,
            "imageAnalysis": image_analysis,
            "realProviderError": str(error),
            "error": "AI生成服务暂时不可用，请稍后重试。",
            "model": getattr(provider, "model", configured_image_model() if provider_name == "dashscope_qwen_image" else "SDXL + InstantStyle / IP-Adapter" if provider_name == "instantstyle" else None),
            "referenceImageUsed": False,
            "debug": {
                **error.to_debug(),
                "requestId": request_id,
                "providerRequestId": error.request_id,
                "selectedProvider": provider_name,
                "allowMockFallback": allow_fallback,
                "styleStrengthApplied": True,
                "styleStrengthText": strength_text,
                "negativePromptPreview": negative_prompt[:120],
            },
        }
        _trace_generate(request_id, enriched_payload, image_analysis, enhanced_prompt, negative_prompt, provider_name, allow_fallback, response)
        return response

def _dashscope_network_status() -> dict[str, object]:
    if env_bool("DASHSCOPE_BYPASS_TUN", False):
        try:
            from dashscope_direct_client import DashScopeDirectClient
            client = DashScopeDirectClient()
            response = client.request("GET", "https://dashscope.aliyuncs.com/api/v1/tasks/fake_task_id", headers={}, timeout=15)
            return {
                "networkReachable": True,
                "sslOk": True,
                "bypassTun": True,
                "sourceIp": client.source_ip,
                "directIps": client.direct_ips,
                "probeStatus": response.status_code,
            }
        except Exception as exc:
            return {
                "networkReachable": False,
                "sslOk": False,
                "bypassTun": True,
                "message": f"DashScope direct probe failed: {type(exc).__name__}: {exc}",
            }

    try:
        import requests
        response = requests.get("https://dashscope.aliyuncs.com/api/v1/tasks/fake_task_id", timeout=15)
        return {
            "networkReachable": True,
            "sslOk": True,
            "bypassTun": False,
            "probeStatus": response.status_code,
        }
    except Exception as exc:
        return {
            "networkReachable": False,
            "sslOk": False,
            "bypassTun": False,
            "message": f"DashScope domain probe failed: {type(exc).__name__}: {exc}",
        }


def _trace_generate(
    request_id: str,
    payload: Mapping[str, object],
    image_analysis: Mapping[str, str],
    enhanced_prompt: str,
    negative_prompt: str,
    selected_provider: str,
    allow_fallback: bool,
    response: Mapping[str, object],
) -> None:
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    saved_path = str(image_analysis.get("savedPath") or "")
    record = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "requestId": request_id,
        "theme": str(payload.get("theme") or "")[:80],
        "style": payload.get("style"),
        "styleName": payload.get("styleName"),
        "styleStrength": payload.get("styleStrength"),
        "compositionMode": payload.get("compositionMode"),
        "hasNegativePrompt": bool(str(payload.get("negativePrompt") or "").strip()),
        "hasUploadedImage": bool(str(payload.get("uploadedImage") or "").strip()),
        "uploadedImageSavedPathExists": bool(saved_path and Path(saved_path).exists()),
        "enhancedPrompt": enhanced_prompt[:200],
        "negativePrompt": negative_prompt[:120],
        "selectedProvider": selected_provider,
        "allowMockFallback": allow_fallback,
        "providerResultMode": response.get("mode"),
        "providerResultProvider": response.get("provider"),
        "imageUrl": response.get("imageUrl"),
        "hasRealProviderError": bool(response.get("realProviderError")),
    }
    with (log_dir / "generate_payload_trace.log").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _openai_billing_blocked() -> tuple[bool, str]:
    log_path = PROJECT_ROOT / "logs" / "openai_image_minimal_test.log"
    if not log_path.exists():
        return False, ""
    try:
        text = log_path.read_text(encoding="utf-8", errors="ignore").lower()
    except Exception:
        return False, ""
    blocked = "billing_hard_limit_reached" in text or "billing hard limit" in text
    return blocked, "billing_hard_limit_reached" if blocked else ""
