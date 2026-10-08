from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from dashscope_config import configured_image_model, configured_workspace_base_url, workspace_endpoint
from dashscope_direct_client import DashScopeDirectClient
from image_provider import output_url
from style_config import OUTPUT_DIR, PROJECT_ROOT, StyleConfig, ensure_runtime_dirs

from .base import ImageProvider, ProviderError


TRACE_LOG = PROJECT_ROOT / "logs" / "dashscope_qwen_image_trace.log"


class DashScopeQwenImageProvider(ImageProvider):
    name = "dashscope_qwen_image"

    def __init__(self) -> None:
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        self.model = configured_image_model()
        self.size = os.getenv("DASHSCOPE_IMAGE_SIZE", "1024*1024").strip() or "1024*1024"
        self.poll_interval = _env_float("DASHSCOPE_POLL_INTERVAL", 2.0)
        self.timeout = _env_float("DASHSCOPE_TIMEOUT", 240.0)
        self.verify_ssl = os.getenv("DASHSCOPE_VERIFY_SSL", "true").strip().lower() not in {"0", "false", "no", "off"}
        self.ca_bundle = os.getenv("DASHSCOPE_CA_BUNDLE", "").strip()
        self.bypass_tun = os.getenv("DASHSCOPE_BYPASS_TUN", "true").strip().lower() not in {"0", "false", "no", "off"}
        self.direct_client = DashScopeDirectClient()

    def is_available(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "缺少 DASHSCOPE_API_KEY。"
        base_url, base_error = configured_workspace_base_url()
        if not base_url:
            return False, base_error
        if self.model not in {"qwen-image-3.0", "qwen-image-3.0-pro"}:
            return False, "DASHSCOPE_IMAGE_MODEL 不是当前接口支持的 Qwen Image 3.0 模型名。"
        if not re.fullmatch(r"\d{3,4}\*\d{3,4}", self.size):
            return False, "DASHSCOPE_IMAGE_SIZE 格式应为宽*高，例如 1024*1024。"
        try:
            import requests  # noqa: F401
        except Exception:
            return False, "缺少 requests 依赖，请运行 pip install -r requirements.txt。"
        return True, f"DashScope Qwen Image 云端生成可用，模型 {self.model}。"

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
            raise ProviderError(self.name, "config", message, "检查后端 backend/.env 中的 DASHSCOPE_API_KEY、DASHSCOPE_BASE_URL 和 DASHSCOPE_IMAGE_MODEL。")

        workspace_base, base_error = configured_workspace_base_url()
        if not workspace_base:
            raise ProviderError(self.name, "config", base_error)

        request_id = str(request_data.get("requestId") or uuid4().hex[:12])
        uploaded_image = str(request_data.get("uploadedImage") or "").strip()
        mode = "image_to_image" if uploaded_image else "text_to_image"
        content: list[dict[str, str]] = []
        if uploaded_image:
            # analyze_image() has already validated the image data URL and decoded its bytes.
            # The same Base64 data URL is sent as a real DashScope image condition.
            content.append({"image": uploaded_image})
        content.append({"text": enhanced_prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "input": {
                "messages": [{"role": "user", "content": content}],
            },
            "parameters": {
                "size": self.size,
                "n": 1,
                "negative_prompt": negative_prompt,
                "prompt_extend": True,
                "prompt_extend_mode": "direct",
                "watermark": False,
            },
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        trace: dict[str, Any] = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "requestId": request_id,
            "model": self.model,
            "mode": mode,
            "inputImageCount": 1 if uploaded_image else 0,
            "outputImageCount": 0,
            "promptLength": len(enhanced_prompt),
            "success": False,
            "dashscopeRequestId": None,
        }
        poll_count = 0
        dashscope_request_id: str | None = None
        generation_deadline = time.time() + self.timeout
        submit_timeout = max(1, min(120, int(self.timeout)))

        try:
            import requests

            submit_url = workspace_endpoint(workspace_base, "services/aigc/image-generation/generation")
            # Keep submission one-shot, but allow a slower dedicated workspace to
            # respond without resubmitting a potentially billable generation.
            submit = self._request("POST", submit_url, headers=headers, json_body=payload, timeout=submit_timeout, single_attempt=True)
            body = _response_json(submit)
            dashscope_request_id = _dashscope_request_id(body)
            trace["dashscopeRequestId"] = dashscope_request_id
            if submit.status_code >= 400:
                raise _api_error("submit_task", body, submit.status_code, _qwen_suggestion(body))

            task_id = str((body.get("output") or {}).get("task_id") or body.get("task_id") or "")
            if not task_id:
                error = ProviderError(self.name, "submit_task", "DashScope 已响应，但没有返回任务编号。", "确认工作空间 URL、模型权限和 API 响应格式。")
                error.request_id = dashscope_request_id
                error.http_status = submit.status_code
                raise error

            result_body: dict[str, Any] | None = None
            while time.time() < generation_deadline:
                poll_count += 1
                task_url = workspace_endpoint(workspace_base, f"tasks/{task_id}")
                poll = self._request("GET", task_url, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=60)
                result_body = _response_json(poll)
                dashscope_request_id = _dashscope_request_id(result_body) or dashscope_request_id
                trace["dashscopeRequestId"] = dashscope_request_id
                if poll.status_code >= 400:
                    raise _api_error("poll_task", result_body, poll.status_code, _qwen_suggestion(result_body))

                output = result_body.get("output") or {}
                task_status = str(output.get("task_status") or output.get("status") or "").upper()
                if task_status in {"SUCCEEDED", "SUCCESS"}:
                    break
                if task_status in {"FAILED", "UNKNOWN", "CANCELED"}:
                    raise _api_error("poll_task", result_body, 200, _qwen_suggestion(result_body))
                time.sleep(max(0.5, self.poll_interval))
            else:
                raise ProviderError(self.name, "poll_task", f"Qwen Image 任务超过 {int(self.timeout)} 秒仍未完成。", "稍后重试；本次请求不会自动再次提交。")

            image_url = _extract_image_url(result_body or {})
            if not image_url:
                error = ProviderError(self.name, "parse_result", "Qwen Image 任务成功，但响应中没有图片地址。", "检查 DashScope 任务结果中的图片字段。")
                error.request_id = dashscope_request_id
                raise error

            usage = (result_body or {}).get("usage") or {}
            trace["outputImageCount"] = int(usage.get("output_image_count") or 1)
            trace["modelInputImageCount"] = int(usage.get("input_image_count") or 0)
            trace["requestTraceIdExists"] = bool(dashscope_request_id)
            reference_used = bool(uploaded_image) and trace["modelInputImageCount"] > 0
            if uploaded_image and not reference_used:
                error = ProviderError(self.name, "confirm_reference_image", "模型任务成功，但服务响应未确认参考图已参与推理。", "请查看 Qwen Image usage.input_image_count；本次不会标记为参考图创作。")
                error.request_id = dashscope_request_id
                raise error
            image_response = requests.get(image_url, timeout=60, verify=self._verify_arg())
            image_response.raise_for_status()
            local_path = _save_image_bytes(image_response.content, style_config.id)
            trace["success"] = True
            trace["taskPollCount"] = poll_count
            _write_trace(trace)

            return {
                "success": True,
                "imageUrl": output_url(base_url, local_path),
                "mode": mode,
                "provider": self.name,
                "model": self.model,
                "engine": f"DashScope {self.model}",
                "localPath": str(local_path),
                "usedStyleRef": style_config.refImagePath,
                "referenceImageUsed": reference_used,
                "debug": {
                    "provider": self.name,
                    "model": self.model,
                    "mode": mode,
                    "referenceImageUsed": reference_used,
                    "inputImageCount": 1 if uploaded_image else 0,
                    "outputImageCount": trace["outputImageCount"],
                    "modelInputImageCount": trace["modelInputImageCount"],
                    "dashscopeRequestId": dashscope_request_id,
                    "size": self.size,
                },
            }
        except ProviderError as exc:
            trace["errorStage"] = exc.stage
            trace["errorCode"] = exc.error_code or _safe_error_code(str(exc))
            if not exc.request_id:
                exc.request_id = dashscope_request_id
            _write_trace(trace)
            if self.api_key and self.api_key in exc.error:
                sanitized = ProviderError(self.name, exc.stage, exc.error.replace(self.api_key, "[REDACTED]"), exc.suggestion)
                sanitized.error_code = exc.error_code
                sanitized.http_status = exc.http_status
                sanitized.request_id = exc.request_id
                raise sanitized from exc
            raise
        except Exception as exc:
            trace["errorStage"] = "network_or_download"
            trace["errorCode"] = type(exc).__name__
            trace["dashscopeRequestId"] = dashscope_request_id
            _write_trace(trace)
            error = ProviderError(
                self.name,
                "generate",
                f"{type(exc).__name__}: {_redact_secret(str(exc), self.api_key)[:400]}",
                "检查业务空间 Base URL、网络、证书、模型权限和百炼额度。",
            )
            error.request_id = dashscope_request_id
            raise error from exc

    def _request(self, method: str, url: str, *, headers: Mapping[str, str], json_body: Any = None, timeout: int = 60, single_attempt: bool = False) -> Any:
        if self.bypass_tun:
            return self.direct_client.request(method, url, headers=headers, json_body=json_body, timeout=timeout, single_attempt=single_attempt)
        import requests
        return requests.request(method, url, headers=dict(headers), json=json_body, timeout=timeout, verify=self._verify_arg())

    def _verify_arg(self) -> bool | str:
        return self.ca_bundle if self.ca_bundle else self.verify_ssl


def _response_json(response: Any) -> dict[str, Any]:
    try:
        value = response.json()
        return value if isinstance(value, dict) else {"message": "DashScope 返回了非对象 JSON。"}
    except Exception:
        return {"message": f"DashScope 返回非 JSON 响应（HTTP {getattr(response, 'status_code', 'unknown')}）。"}


def _response_error(body: Mapping[str, Any], status_code: int) -> str:
    output = body.get("output") if isinstance(body.get("output"), Mapping) else {}
    code = str(body.get("code") or output.get("code") or "")
    message = str(body.get("message") or output.get("message") or "请求失败")
    return f"HTTP {status_code}{f' {code}' if code else ''}: {message[:600]}"


def _dashscope_request_id(body: Mapping[str, Any]) -> str | None:
    """Read a DashScope trace ID without exposing request headers or credentials."""
    for key in ("request_id", "requestId", "RequestId", "request-id"):
        value = body.get(key)
        if value:
            return str(value)[:160]
    output = body.get("output")
    if isinstance(output, Mapping):
        for key in ("request_id", "requestId", "RequestId", "request-id"):
            value = output.get(key)
            if value:
                return str(value)[:160]
    return None


def _api_error(stage: str, body: Mapping[str, Any], status_code: int, suggestion: str) -> ProviderError:
    output = body.get("output") if isinstance(body.get("output"), Mapping) else {}
    error_code = str(body.get("code") or output.get("code") or "")[:120] or None
    error = ProviderError("dashscope_qwen_image", stage, _response_error(body, status_code), suggestion)
    error.error_code = error_code or "dashscope_request_failed"
    error.http_status = status_code
    error.request_id = _dashscope_request_id(body)
    return error


def _extract_image_url(body: Mapping[str, Any]) -> str:
    output = body.get("output") or {}
    results = output.get("results") or []
    if results:
        first = results[0]
        if isinstance(first, Mapping):
            candidate = first.get("url") or first.get("image_url") or first.get("image")
            if candidate:
                return str(candidate)
    choices = output.get("choices") or []
    for choice in choices:
        message = choice.get("message") if isinstance(choice, Mapping) else None
        content = message.get("content") if isinstance(message, Mapping) else None
        if isinstance(content, list):
            for item in content:
                if isinstance(item, Mapping) and item.get("image"):
                    return str(item["image"])
    return str(output.get("url") or output.get("image_url") or "")


def _qwen_suggestion(body: Mapping[str, Any]) -> str:
    output = body.get("output") if isinstance(body.get("output"), Mapping) else {}
    message = str(body.get("message") or output.get("message") or "").lower()
    code = str(body.get("code") or "").lower()
    if "model" in message and ("not" in message or "invalid" in message or "exist" in message):
        return "检查 DASHSCOPE_IMAGE_MODEL 和该业务空间中的模型权限。"
    if "region" in message or "workspace" in message or "permission" in message or "forbidden" in code:
        return "确认 DASHSCOPE_BASE_URL、API Key 和模型属于同一华北2（北京）业务空间。"
    if "quota" in message or "balance" in message or "insufficient" in message:
        return "请检查百炼控制台的模型额度和付费状态。"
    return "检查 DashScope 响应、业务空间 URL、模型权限、网络和额度。"


def _safe_error_code(error_text: str) -> str:
    match = re.search(r"(?:HTTP \d{3}\s+)?([A-Za-z][A-Za-z0-9_-]{2,})", error_text)
    return match.group(1) if match else "provider_error"


def _redact_secret(value: str, api_key: str) -> str:
    return value.replace(api_key, "[REDACTED]") if api_key else value


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _save_image_bytes(content: bytes, style_id: str) -> Path:
    from io import BytesIO
    from PIL import Image
    try:
        with Image.open(BytesIO(content)) as image:
            if image.format != 'PNG':
                raise ValueError('Expected a PNG generation result')
            image.verify()
    except Exception as exc:
        raise ProviderError('dashscope_qwen_image', 'validate_image', '生成服务返回的图片文件无效；未保存替代图片。') from exc
    ensure_runtime_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"qwen_image_{stamp}_{style_id}.png"
    suffix = 1
    while output_path.exists():
        output_path = OUTPUT_DIR / f"qwen_image_{stamp}_{style_id}_{suffix}.png"
        suffix += 1
    output_path.write_bytes(content)
    return output_path


def _write_trace(record: Mapping[str, Any]) -> None:
    TRACE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TRACE_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
