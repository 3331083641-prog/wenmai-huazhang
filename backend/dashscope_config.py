from __future__ import annotations

import os
from urllib.parse import urlparse


DEFAULT_IMAGE_MODEL = "qwen-image-3.0"
BEIJING_WORKSPACE_SUFFIX = ".cn-beijing.maas.aliyuncs.com"


def configured_image_model() -> str:
    return os.getenv("DASHSCOPE_IMAGE_MODEL", DEFAULT_IMAGE_MODEL).strip() or DEFAULT_IMAGE_MODEL


def configured_workspace_base_url() -> tuple[str | None, str]:
    raw = os.getenv("DASHSCOPE_BASE_URL", "").strip()
    if not raw:
        return None, "DASHSCOPE_BASE_URL 未配置，请填写百炼控制台显示的华北2（北京）业务空间专属 Base URL。"

    try:
        parsed = urlparse(raw)
        host = (parsed.hostname or "").lower()
        port = parsed.port
    except ValueError:
        return None, "DASHSCOPE_BASE_URL 格式无效；需要 HTTPS 华北2（北京）业务空间专属域名。"
    valid_host = host.endswith(BEIJING_WORKSPACE_SUFFIX) and host != BEIJING_WORKSPACE_SUFFIX.lstrip(".")
    valid_path = parsed.path.rstrip("/") in {"", "/api/v1", "/compatible-mode/v1"}
    if (
        parsed.scheme != "https"
        or not valid_host
        or port not in (None, 443)
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or not valid_path
    ):
        return None, "DASHSCOPE_BASE_URL 格式无效；需要 HTTPS 华北2（北京）业务空间专属域名，不能使用公共域名。"

    return f"https://{host}", ""


def workspace_endpoint(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/api/v1/{path.lstrip('/')}"
