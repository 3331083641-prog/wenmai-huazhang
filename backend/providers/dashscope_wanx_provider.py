from __future__ import annotations

import os
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from dashscope_direct_client import DashScopeDirectClient
from image_provider import output_url
from style_config import OUTPUT_DIR, PROJECT_ROOT, StyleConfig, ensure_runtime_dirs

from .base import ImageProvider, ProviderError


DASHSCOPE_SUBMIT_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
DASHSCOPE_TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
TRACE_LOG = PROJECT_ROOT / "logs" / "dashscope_real_call_trace.log"


class DashScopeWanxProvider(ImageProvider):
    name = "dashscope_wanx"

    def __init__(self) -> None:
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        self.model = os.getenv("DASHSCOPE_WANX_FALLBACK_MODEL", "wanx-v1").strip() or "wanx-v1"
        self.size = os.getenv("DASHSCOPE_IMAGE_SIZE", "1024*1024").strip() or "1024*1024"
        self.poll_interval = _env_float("DASHSCOPE_POLL_INTERVAL", 2.0)
        self.timeout = _env_float("DASHSCOPE_TIMEOUT", 180.0)
        self.verify_ssl = os.getenv("DASHSCOPE_VERIFY_SSL", "true").strip().lower() not in {"0", "false", "no", "off"}
        self.ca_bundle = os.getenv("DASHSCOPE_CA_BUNDLE", "").strip()
        self.bypass_tun = os.getenv("DASHSCOPE_BYPASS_TUN", "true").strip().lower() not in {"0", "false", "no", "off"}
        self.direct_client = DashScopeDirectClient()

    def is_available(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "缺少 API Key"
        try:
            import requests  # noqa: F401
        except Exception:
            return False, "缺少 requests 依赖，请运行 pip install -r requirements.txt"
        return True, f"通义万相云端生成可用，模型 {self.model}"

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
        request_id = str(request_data.get("requestId") or uuid4().hex[:12])
        trace: dict[str, Any] = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "requestId": request_id,
            "stage": "init",
            "model": self.model,
            "size": self.size,
            "promptLength": len(enhanced_prompt or ""),
            "negativePromptLength": len(negative_prompt or ""),
            "submitHttpStatus": None,
            "submitResponseCode": None,
            "submitResponseMessage": None,
            "dashscopeRequestId": None,
            "taskIdExists": False,
            "pollCount": 0,
            "taskStatus": None,
            "resultUrlExists": False,
            "usageImageCount": None,
            "downloadStatus": None,
            "localPath": None,
            "finalMode": None,
            "finalProvider": self.name,
            "errorType": None,
            "errorMessage": None,
        }

        def fail(stage: str, error: ProviderError) -> ProviderError:
            trace["stage"] = stage
            trace["finalMode"] = "error"
            trace["errorType"] = error.stage
            trace["errorMessage"] = str(error.error)[:500]
            _write_trace(trace)
            return error

        if not available:
            raise fail("config", ProviderError(self.name, "config", message, "在 backend/.env 填写 DASHSCOPE_API_KEY，或切换 GENERATION_PROVIDER=fast_demo。"))

        try:
            import requests
        except Exception as exc:
            raise fail("import", ProviderError(self.name, "import", str(exc), "安装 requests 依赖。")) from exc

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "input": {
                "prompt": enhanced_prompt,
                "negative_prompt": negative_prompt,
            },
            "parameters": {
                "size": self.size,
                "n": 1,
            },
        }

        try:
            trace["stage"] = "submit_task"
            if self.bypass_tun:
                submit = self.direct_client.request("POST", DASHSCOPE_SUBMIT_URL, headers=headers, json_body=payload, timeout=60)
            else:
                submit = requests.post(DASHSCOPE_SUBMIT_URL, headers=headers, json=payload, timeout=30, verify=self._verify_arg())
        except Exception as exc:
            raise fail("submit_task", self._network_error("submit_task", exc)) from exc
        trace["submitHttpStatus"] = getattr(submit, "status_code", None)
        if submit.status_code >= 400:
            raise fail("submit_task", ProviderError(self.name, "submit_task", _safe_response_text(submit), _dashscope_suggestion(_safe_response_text(submit))))

        try:
            body = submit.json()
        except Exception as exc:
            raise fail("submit_task", ProviderError(self.name, "submit_task", f"DashScope 返回非 JSON 响应，HTTP {submit.status_code}", "检查 DashScope 服务状态。")) from exc

        trace["submitResponseCode"] = body.get("code")
        trace["submitResponseMessage"] = str(body.get("message") or "")[:300]
        trace["dashscopeRequestId"] = body.get("request_id") or body.get("requestId")
        task_id = (body.get("output") or {}).get("task_id") or body.get("task_id")
        trace["taskIdExists"] = bool(task_id)
        if not task_id:
            raise fail("submit_task", ProviderError(self.name, "submit_task", f"DashScope 未返回 task_id: {_redact_large(body)}", "确认模型名称和异步接口是否匹配。"))

        result_body: dict[str, Any] | None = None
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            try:
                trace["stage"] = "poll_task"
                trace["pollCount"] = int(trace.get("pollCount") or 0) + 1
                poll_url = DASHSCOPE_TASK_URL.format(task_id=task_id)
                if self.bypass_tun:
                    poll = self.direct_client.request("GET", poll_url, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=60)
                else:
                    poll = requests.get(poll_url, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=30, verify=self._verify_arg())
            except Exception as exc:
                raise fail("poll_task", self._network_error("poll_task", exc)) from exc
            if poll.status_code >= 400:
                raise fail("poll_task", ProviderError(self.name, "poll_task", _safe_response_text(poll), _dashscope_suggestion(_safe_response_text(poll))))
            try:
                result_body = poll.json()
            except Exception as exc:
                raise fail("poll_task", ProviderError(self.name, "poll_task", f"任务查询返回非 JSON 响应，HTTP {poll.status_code}", "检查 DashScope 任务查询接口。")) from exc

            output = result_body.get("output") or {}
            status = str(output.get("task_status") or output.get("status") or "").upper()
            trace["dashscopeRequestId"] = result_body.get("request_id") or result_body.get("requestId") or trace.get("dashscopeRequestId")
            trace["taskStatus"] = status
            trace["usageImageCount"] = (result_body.get("usage") or {}).get("image_count")
            if status in {"SUCCEEDED", "SUCCESS"}:
                break
            if status in {"FAILED", "UNKNOWN", "CANCELED"}:
                code = output.get("code") or result_body.get("code") or "UNKNOWN"
                msg = output.get("message") or result_body.get("message") or str(_redact_large(result_body))
                raise fail("poll_task", ProviderError(self.name, "poll_task", f"{code}: {msg}", _dashscope_suggestion(f"{code}: {msg}")))
            time.sleep(max(0.5, self.poll_interval))
        else:
            raise fail("poll_task", ProviderError(self.name, "poll_task", f"DashScope task {task_id} timed out after {int(self.timeout)}s", "将 DASHSCOPE_TIMEOUT 调高到 300，或稍后重试。"))

        image_url = _extract_image_url(result_body or {})
        trace["resultUrlExists"] = bool(image_url)
        if not image_url:
            raise fail("parse_result", ProviderError(self.name, "parse_result", f"DashScope 成功返回但未找到图片 URL: {_redact_large(result_body)}", "检查 output.results[0].url 字段是否变化。"))

        try:
            trace["stage"] = "download_image"
            image_response = requests.get(image_url, timeout=60, verify=self._verify_arg())
            trace["downloadStatus"] = image_response.status_code
            image_response.raise_for_status()
            local_path = _save_dashscope_bytes(image_response.content, style_config.id)
        except Exception as exc:
            raise fail("download_image", self._network_error("download_image", exc)) from exc

        trace["stage"] = "done"
        trace["localPath"] = str(local_path)
        trace["finalMode"] = self.name
        trace["finalProvider"] = self.name
        _write_trace(trace)
        return {
            "success": True,
            "imageUrl": output_url(base_url, local_path),
            "mode": self.name,
            "provider": self.name,
            "engine": f"DashScope {self.model}",
            "localPath": str(local_path),
            "usedStyleRef": style_config.refImagePath,
            "debug": {"provider": self.name, "stage": "done", "taskId": task_id, "size": self.size},
        }

    def _verify_arg(self) -> bool | str:
        if self.ca_bundle:
            return self.ca_bundle
        return self.verify_ssl

    def _network_error(self, stage: str, exc: Exception) -> ProviderError:
        try:
            import requests
            if isinstance(exc, requests.exceptions.SSLError):
                return ProviderError(
                    self.name,
                    stage,
                    f"SSLError: {exc}",
                    "本机到 dashscope.aliyuncs.com 的 HTTPS/SSL 握手失败，通常与证书链、代理、HTTPS 拦截、防火墙或 Python certifi 证书包有关，不是 API Key 或余额问题。",
                )
            if isinstance(exc, requests.exceptions.ProxyError):
                return ProviderError(
                    self.name,
                    stage,
                    f"ProxyError: {exc}",
                    "当前代理无法正常转发 DashScope HTTPS 请求，请检查 HTTP_PROXY/HTTPS_PROXY 或关闭代理后重试。",
                )
            if isinstance(exc, requests.exceptions.ConnectTimeout):
                return ProviderError(self.name, stage, f"ConnectTimeout: {exc}", "连接 DashScope 超时，检查网络出口、防火墙或代理。")
            if isinstance(exc, requests.exceptions.ReadTimeout):
                return ProviderError(self.name, stage, f"ReadTimeout: {exc}", "DashScope 响应超时，可调高 DASHSCOPE_TIMEOUT 或稍后重试。")
            if isinstance(exc, requests.exceptions.ConnectionError):
                return ProviderError(self.name, stage, f"ConnectionError: {exc}", "本机无法稳定连接 DashScope，检查 DNS、网络、代理、防火墙或证书链。")
            if isinstance(exc, requests.exceptions.HTTPError):
                return ProviderError(self.name, stage, f"HTTPError: {exc}", "DashScope HTTP 请求失败，检查状态码和返回体。")
        except Exception:
            pass
        return ProviderError(self.name, stage, f"{type(exc).__name__}: {exc}", "检查 DashScope 网络、代理、证书链、模型名和账号权限。")

def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _save_dashscope_bytes(content: bytes, style_id: str) -> Path:
    ensure_runtime_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"dashscope_{stamp}_{style_id}.png"
    output_path.write_bytes(content)
    return output_path


def _safe_response_text(response: object) -> str:
    text = getattr(response, "text", "") or ""
    return text[:1200]


def _extract_image_url(body: Mapping[str, Any]) -> str:
    output = body.get("output") or {}
    results = output.get("results") or []
    if results:
        first = results[0]
        if isinstance(first, Mapping):
            return str(first.get("url") or first.get("image_url") or first.get("image") or "")
    return str(output.get("url") or output.get("image_url") or "")


def _redact_large(value: object) -> str:
    return str(value)[:1200]


def _dashscope_suggestion(error_text: str) -> str:
    lower = error_text.lower()
    if "invalid" in lower and "key" in lower:
        return "DASHSCOPE_API_KEY 可能无效；确认后端已读取到 Key，但不要在前端或日志中暴露。"
    if "model" in lower and ("not" in lower or "invalid" in lower or "exist" in lower):
        return "模型可能不存在或无权限；可检查 DASHSCOPE_WANX_FALLBACK_MODEL 和账号权限。"
    if "quota" in lower or "balance" in lower or "insufficient" in lower:
        return "账号额度或余额不足；请检查阿里云百炼控制台。"
    if "thrott" in lower or "qps" in lower or "rate" in lower:
        return "触发 QPS 或并发限制；降低频率后重试。"
    if "region" in lower or "permission" in lower or "forbidden" in lower:
        return "可能是地域、权限或模型开通问题；请在阿里云百炼控制台确认。"
    return "检查 DashScope API Key、模型名、账号权限、网络和额度。"


def _write_trace(record: Mapping[str, Any]) -> None:
    TRACE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TRACE_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
