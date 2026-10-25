"""Bounded official DeepSeek/Bailian vision reviews; no tools or automatic retries.

Transport errors and rejected model output intentionally expose no provider text.
The optimizer, rather than this transport layer, owns the parameter whitelist.
"""
from __future__ import annotations

import base64
import io
import json
import math
import os
from pathlib import Path
import re
import threading
from typing import Any
from urllib.parse import urlsplit

from PIL import Image, ImageOps
import requests


DEFAULT_MODEL = "deepseek-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com"
BAILIAN_DEFAULT_MODEL = "deepseek-v4.1-flash-1017"
_OFFICIAL_MODELS = {"deepseek-flash", "deepseek-v4-flash", "deepseek-v4-flash-vision-exp"}
DIMENSIONS = ("fidelity", "layering", "occlusion", "motion", "interaction")
_PUBLIC_HOSTS = {"dashscope.aliyuncs.com", "dashscope-intl.aliyuncs.com", "dashscope-us.aliyuncs.com"}
_WORKSPACE_HOST = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.maas\.aliyuncs\.com\Z")
_MODEL = re.compile(r"deepseek-[a-z0-9.-]{1,100}\Z")
_IDENTIFIER = re.compile(r"[A-Za-z0-9_.:-]{1,160}\Z")
_TOKEN_FIELDS = ("prompt_tokens", "completion_tokens", "total_tokens", "input_tokens", "output_tokens")
_DETAIL_FIELDS = ("reasoning_tokens", "cached_tokens", "image_tokens", "text_tokens", "audio_tokens",
                  "accepted_prediction_tokens", "rejected_prediction_tokens")

SYSTEM_PROMPT = """你是纹脉华章的云端DeepSeek画境视觉复审员。依据本图原像素、真实浏览器多视角和动态截图、原五件精选参照及给定程序证据审查。
检查风格和可见形态保真、主体完整与内部相对起伏、多层视差、遮挡连续、漏体/重复/拉伸/硬边、克制运动、热点吻合和图文依据。
平面纹样不强造不存在的空间或骨骼动作；补全是推断。无法从证据确认时明确指出，不把主题说明当作已见内容。
遵守上下文中的复审目标、程序检查和输出契约。只建议有限参数，不提供或执行代码、工具、文件修改、路径或密钥操作。
只输出一个 JSON 对象，不输出 Markdown 或思考过程，字段为 overallScore(0至100数值)、dimensions(五项0至100数值：fidelity,layering,occlusion,motion,interaction)、passed(布尔值)、issues(含severity为blocker/major/minor、code、description的对象数组)、suggestedParameters(对象)、summary(简体中文字符串)。
"""


class ReviewError(RuntimeError):
    """Safe to persist; contains only locally chosen diagnostic text."""


class ConfigurationError(ReviewError):
    pass


def _integer(value: Any, minimum: int, maximum: int, name: str) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ConfigurationError(f"invalid {name}")
    return value


def _base_url(value: str) -> str:
    try:
        if not isinstance(value, str) or any(ord(ch) <= 32 for ch in value):
            raise ValueError
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        if (parsed.scheme != "https" or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443) or parsed.query or parsed.fragment):
            raise ValueError
        if host == "api.deepseek.com" and parsed.path in ("", "/", "/v1", "/v1/"):
            return "https://api.deepseek.com" + ("/v1" if parsed.path.startswith("/v1") else "")
        if not (host in _PUBLIC_HOSTS or _WORKSPACE_HOST.fullmatch(host)) or parsed.path not in ("/compatible-mode/v1", "/compatible-mode/v1/"):
            raise ValueError
        # Construct from validated components; never forward userinfo/query/fragment.
        return f"https://{host}/compatible-mode/v1"
    except (ValueError, TypeError):
        raise ConfigurationError("invalid DeepSeek HTTPS base URL") from None


def _bounded_text(value: Any, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ReviewError("invalid review schema")
    return value


def _score(value: Any) -> float | int:
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100:
        raise ReviewError("invalid review score")
    return value


def _json_tree(value: Any, depth: int = 0) -> None:
    """Reject non-JSON/nonfinite/oversized parameter structures, without policy filtering."""
    if depth > 8:
        raise ReviewError("invalid review parameter structure")
    if value is None or type(value) in (bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if isinstance(value, str) and len(value) <= 4000:
        return
    if isinstance(value, list) and len(value) <= 100:
        for item in value:
            _json_tree(item, depth + 1)
        return
    if isinstance(value, dict) and len(value) <= 100:
        for key, item in value.items():
            _bounded_text(key, 100)
            _json_tree(item, depth + 1)
        return
    raise ReviewError("invalid review parameter structure")


def _validate_review(value: Any) -> dict:
    try:
        if not isinstance(value, dict):
            raise ReviewError("invalid review schema")
        dimensions = value["dimensions"]
        if not isinstance(dimensions, dict) or set(dimensions) != set(DIMENSIONS):
            raise ReviewError("invalid review dimensions")
        if type(value["passed"]) is not bool:
            raise ReviewError("invalid review schema")
        issues = value["issues"]
        if not isinstance(issues, list) or len(issues) > 50:
            raise ReviewError("invalid review issues")
        clean_issues = []
        for issue in issues:
            if not isinstance(issue, dict) or issue.get("severity") not in ("blocker", "major", "minor"):
                raise ReviewError("invalid review issues")
            clean_issues.append({"severity": issue["severity"], "code": _bounded_text(issue["code"], 100),
                                 "description": _bounded_text(issue["description"], 2000)})
        parameters = value["suggestedParameters"]
        if not isinstance(parameters, dict):
            raise ReviewError("invalid review parameters")
        _json_tree(parameters)
        if len(json.dumps(parameters, allow_nan=False)) > 32000:
            raise ReviewError("review parameters too large")
        return {"overallScore": _score(value["overallScore"]),
                "dimensions": {name: _score(dimensions[name]) for name in DIMENSIONS},
                "passed": value["passed"], "issues": clean_issues,
                "suggestedParameters": parameters, "summary": _bounded_text(value["summary"], 4000)}
    except (KeyError, TypeError, ValueError, OverflowError):
        raise ReviewError("invalid review schema") from None


def _usage(value: Any) -> dict:
    if not isinstance(value, dict):
        return {}
    clean = {key: item for key in _TOKEN_FIELDS
             if type(item := value.get(key)) is int and 0 <= item <= 10**12}
    for field in ("prompt_tokens_details", "completion_tokens_details", "input_tokens_details", "output_tokens_details"):
        details = value.get(field)
        if isinstance(details, dict):
            clean[field] = {key: item for key in _DETAIL_FIELDS
                            if type(item := details.get(key)) is int and 0 <= item <= 10**12}
    return clean


def _image_data(path: Path) -> str:
    try:
        # Actual decoded pixels, never remote URLs; EXIF and other metadata are removed.
        if not isinstance(path, Path) or not path.is_file() or path.stat().st_size > 40 * 1024 * 1024:
            raise ReviewError("invalid review image")
        with Image.open(path) as source:
            if source.width * source.height > 40_000_000:
                raise ReviewError("review image too large")
            image = ImageOps.exif_transpose(source)
            image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            if image.mode in ("RGBA", "LA") or "transparency" in image.info:
                rgba = image.convert("RGBA")
                rgb = Image.new("RGB", rgba.size, "white")
                rgb.paste(rgba, mask=rgba.getchannel("A"))
            else:
                rgb = image.convert("RGB")
            output = io.BytesIO()
            rgb.save(output, format="JPEG", quality=85)
        return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii")
    except ReviewError:
        raise
    except (OSError, ValueError, Image.DecompressionBombError):
        raise ReviewError("invalid review image") from None


class ReviewClient:
    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL, model: str | None = None,
                 *, max_calls: int = 3, max_tokens: int = 4096, timeout: float = 180,
                 session: requests.Session | None = None, provider: str | None = None):
        if (not isinstance(api_key, str) or not api_key.strip() or len(api_key) > 512
                or any(ch.isspace() for ch in api_key)
                or api_key.lower().startswith(("http://", "https://", "bearer"))):
            raise ConfigurationError("missing or invalid review API key")
        self._api_key = api_key
        self.base_url = _base_url(base_url)
        self.provider = "official" if urlsplit(self.base_url).hostname == "api.deepseek.com" else "bailian"
        if provider is not None and provider != self.provider:
            raise ConfigurationError("review provider does not match endpoint")
        if model is None:
            model = DEFAULT_MODEL if self.provider == "official" else BAILIAN_DEFAULT_MODEL
        if not isinstance(model, str) or not _MODEL.fullmatch(model):
            raise ConfigurationError("invalid review model")
        if self.provider == "official" and model not in _OFFICIAL_MODELS:
            raise ConfigurationError("unsupported official vision review model")
        self.model = model
        self.max_calls = _integer(max_calls, 1, 3, "review call limit")
        self.max_tokens = _integer(max_tokens, 128, 4096, "review output token limit")
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 1 <= timeout <= 180:
            raise ConfigurationError("invalid review timeout")
        self.timeout = timeout
        self.session = session if session is not None else requests.Session()
        if session is None:
            self.session.trust_env = False
        self.call_count = 0
        self.usage: dict[str, int] = {}
        self._lock = threading.Lock()

    @classmethod
    def from_env(cls) -> ReviewClient:
        try:
            max_calls = int(os.getenv("DEEPSEEK_MAX_REVIEW_CALLS", "3"))
            max_tokens = int(os.getenv("DEEPSEEK_MAX_TOKENS", "4096"))
            timeout = float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "180"))
        except (ValueError, TypeError):
            raise ConfigurationError("invalid review numeric configuration") from None
        return cls(os.getenv("DEEPSEEK_API_KEY", ""), os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
                   os.getenv("DEEPSEEK_MODEL"), max_calls=max_calls,
                   max_tokens=max_tokens, timeout=timeout, provider=os.getenv("DEEPSEEK_PROVIDER"))

    def review(self, context: dict, images: list[dict]) -> dict:
        try:
            if not isinstance(context, dict) or not isinstance(images, list) or not 1 <= len(images) <= 64:
                raise ReviewError("invalid review input")
            context_json = json.dumps(context, ensure_ascii=False, allow_nan=False)
            if len(context_json) > 200000 or self._api_key in context_json:
                raise ReviewError("invalid review context")
            content = [{"type": "text", "text": context_json}]
            for item in images:
                if not isinstance(item, dict):
                    raise ReviewError("invalid review image")
                label = _bounded_text(item.get("label"), 200)
                if self._api_key in label:
                    raise ReviewError("invalid review image label")
                content.append({"type": "text", "text": label})
                content.append({"type": "image_url", "image_url": {"url": _image_data(item.get("path"))}})
        except (ValueError, TypeError, OverflowError, RecursionError):
            raise ReviewError("invalid review input") from None

        payload = {"model": self.model, "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                   {"role": "user", "content": content}], "stream": False,
                   "max_tokens": self.max_tokens, "response_format": {"type": "json_object"}}
        if self.provider == "official":
            payload["thinking"] = {"type": "disabled"}
        else:
            payload["enable_thinking"] = False
        with self._lock:
            if self.call_count >= self.max_calls:
                raise ReviewError("review call budget exhausted")
            self.call_count += 1
        try:
            response = self.session.post(self.base_url + "/chat/completions", json=payload,
                                         headers={"Authorization": "Bearer " + self._api_key,
                                                  "Content-Type": "application/json"},
                                         timeout=self.timeout, allow_redirects=False)
        except requests.RequestException as exc:
            name = "Timeout" if isinstance(exc, requests.Timeout) else "RequestException"
            raise ReviewError("review transport failure: " + name) from None
        if response.status_code != 200:
            # Never read, retain or include HTTP error bodies, URLs, or auth headers.
            raise ReviewError(f"review HTTP status {int(response.status_code)}")
        try:
            envelope = response.json()
            if not isinstance(envelope, dict):
                raise ValueError
            usage = _usage(envelope.get("usage"))
            with self._lock:
                for key in _TOKEN_FIELDS:
                    if key in usage:
                        self.usage[key] = self.usage.get(key, 0) + usage[key]
            raw = envelope["choices"][0]["message"]["content"]
            if not isinstance(raw, str) or len(raw) > 64000 or self._api_key in raw:
                raise ValueError
            result = _validate_review(json.loads(raw))
            if self._api_key in json.dumps(result, ensure_ascii=False, allow_nan=False):
                raise ReviewError("invalid review JSON response")
            request_id = response.headers.get("x-request-id") or response.headers.get("x-dashscope-request-id") or envelope.get("id", "")
            result["_requestId"] = request_id if isinstance(request_id, str) and _IDENTIFIER.fullmatch(request_id) and self._api_key not in request_id else ""
            result["_usage"] = usage
            model = envelope.get("model", self.model)
            result["_model"] = model if isinstance(model, str) and _MODEL.fullmatch(model) and self._api_key not in model else self.model
            return result
        except ReviewError:
            raise
        except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError):
            raise ReviewError("invalid review JSON response") from None
