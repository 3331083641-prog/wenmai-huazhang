from __future__ import annotations

import json
import ipaddress
import os
import socket
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlparse

import urllib3
import certifi

DEFAULT_DASHSCOPE_IPS = ["8.140.217.18", "39.96.213.166", "8.152.159.24", "39.96.198.249"]


@dataclass
class DirectResponse:
    status_code: int
    text: str
    content: bytes
    headers: Mapping[str, str]

    def json(self) -> Any:
        return json.loads(self.text or self.content.decode("utf-8", errors="replace"))

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}: {self.text[:500]}")


class DashScopeDirectClient:
    """HTTP client that bypasses local fake-IP/TUN for DashScope.

    It connects to resolved DashScope IPs while preserving Host/SNI. API keys
    are only passed in headers by callers and are never logged here.
    """

    def __init__(self) -> None:
        self.enabled = os.getenv("DASHSCOPE_BYPASS_TUN", "true").strip().lower() not in {"0", "false", "no", "off"}
        self.source_ip = os.getenv("DASHSCOPE_SOURCE_IP", "").strip() or _guess_lan_source_ip()
        raw_ips = os.getenv("DASHSCOPE_DIRECT_IPS", "").strip()
        self.direct_ips = [ip.strip() for ip in raw_ips.split(",") if ip.strip()] or DEFAULT_DASHSCOPE_IPS
        self.timeout = urllib3.Timeout(connect=30, read=60)
        self.ca_certs = certifi.where()

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Any = None,
        timeout: int = 60,
        single_attempt: bool = False,
    ) -> DirectResponse:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        is_public_endpoint = host == "dashscope.aliyuncs.com"
        is_beijing_workspace = host.endswith(".cn-beijing.maas.aliyuncs.com") and host != "cn-beijing.maas.aliyuncs.com"
        if not self.enabled or parsed.scheme != "https" or parsed.port not in (None, 443) or not (is_public_endpoint or is_beijing_workspace):
            raise RuntimeError("DashScope direct client only accepts HTTPS DashScope Beijing endpoints")

        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        body: bytes | None = None
        req_headers = dict(headers or {})
        req_headers["Host"] = host
        if json_body is not None:
            body = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            req_headers.setdefault("Content-Type", "application/json")

        ips = self.direct_ips if is_public_endpoint else _resolve_public_ipv4(host)
        if single_attempt:
            ips = ips[:1]
        if not ips:
            raise RuntimeError("DashScope endpoint DNS did not resolve to a public IPv4 address")

        last_error: Exception | None = None
        attempted = 0
        for ip in ips:
            try:
                attempted += 1
                pool = urllib3.HTTPSConnectionPool(
                    ip,
                    port=443,
                    server_hostname=host,
                    assert_hostname=host,
                    source_address=(self.source_ip, 0) if self.source_ip else None,
                    timeout=urllib3.Timeout(connect=30, read=timeout),
                    cert_reqs="CERT_REQUIRED",
                    ca_certs=self.ca_certs,
                )
                resp = pool.request(method.upper(), path, body=body, headers=req_headers, retries=False)
                content = bytes(resp.data or b"")
                text = content.decode("utf-8", errors="replace")
                return DirectResponse(status_code=int(resp.status), text=text, content=content, headers=dict(resp.headers))
            except Exception as exc:
                last_error = exc
                continue
        raise RuntimeError(f"DashScope direct connection failed via {attempted} IPs; last_error={type(last_error).__name__}: {last_error}")


def _resolve_public_ipv4(host: str) -> list[str]:
    resolved: list[str] = []
    for item in socket.getaddrinfo(host, 443, family=socket.AF_INET, type=socket.SOCK_STREAM):
        address = item[4][0]
        try:
            if ipaddress.ip_address(address).is_global and address not in resolved:
                resolved.append(address)
        except ValueError:
            continue
    return resolved


def _guess_lan_source_ip() -> str:
    candidates: list[str] = []
    try:
        hostname = socket.gethostname()
        for item in socket.getaddrinfo(hostname, None, family=socket.AF_INET):
            ip = item[4][0]
            if ip.startswith(("10.", "172.", "192.168.")) and not ip.startswith("198.18."):
                candidates.append(ip)
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("223.5.5.5", 53))
        ip = s.getsockname()[0]
        s.close()
        if ip.startswith(("10.", "172.", "192.168.")) and not ip.startswith("198.18."):
            candidates.insert(0, ip)
    except Exception:
        pass
    return candidates[0] if candidates else ""
