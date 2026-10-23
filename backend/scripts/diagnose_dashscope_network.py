from __future__ import annotations

import os
import re
import socket
import ssl
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
LOG = ROOT / "logs" / "dashscope_network_diagnosis.log"
HOST = "dashscope.aliyuncs.com"
PORT = 443


def write(line: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line)


def sanitize_proxy(value: str | None) -> str:
    if not value:
        return "present=false"
    try:
        parsed = urlparse(value)
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        scheme = parsed.scheme or "proxy"
        return f"present=true host={scheme}://{host}{port}"
    except Exception:
        redacted = re.sub(r"//.*@", "//***@", value)
        return f"present=true value={redacted[:120]}"


def main() -> int:
    if load_dotenv is not None:
        load_dotenv(BACKEND / ".env", override=True)
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip().strip('"').strip("'")
    write(f"\n[{datetime.now().isoformat(timespec='seconds')}] DashScope network diagnosis")
    write(f"hasApiKey={bool(api_key)}")

    dns_ok = False
    tcp_ok = False
    ssl_ok = False
    requests_root_ok = False
    requests_task_ok = False

    write("\n[A] DNS")
    try:
        infos = socket.getaddrinfo(HOST, PORT, type=socket.SOCK_STREAM)
        ips = sorted({item[4][0] for item in infos})
        dns_ok = bool(ips)
        write("dnsOk=true")
        write("ips=" + ", ".join(ips))
    except Exception as exc:
        write("dnsOk=false")
        write(f"dnsError={type(exc).__name__}: {exc}")

    write("\n[B] TCP 443")
    try:
        with socket.create_connection((HOST, PORT), timeout=15):
            tcp_ok = True
        write("tcp443Ok=true")
    except Exception as exc:
        write("tcp443Ok=false")
        write(f"tcpError={type(exc).__name__}: {exc}")

    write("\n[C] Python SSL handshake")
    try:
        context = ssl.create_default_context()
        with socket.create_connection((HOST, PORT), timeout=15) as sock:
            with context.wrap_socket(sock, server_hostname=HOST) as ssock:
                cert = ssock.getpeercert()
                ssl_ok = True
        write("sslOk=true")
        write("subject=" + str(cert.get("subject")))
        write("issuer=" + str(cert.get("issuer")))
        write("notBefore=" + str(cert.get("notBefore")))
        write("notAfter=" + str(cert.get("notAfter")))
    except Exception as exc:
        write("sslOk=false")
        write(f"sslError={type(exc).__name__}: {exc}")

    write("\n[D] requests root")
    try:
        resp = requests.get(f"https://{HOST}", timeout=15)
        requests_root_ok = True
        write("requestsRootOk=true")
        write(f"rootHttpStatus={resp.status_code}")
    except requests.exceptions.SSLError as exc:
        write("requestsRootOk=false")
        write(f"requestsRootError=SSLError: {exc}")
    except Exception as exc:
        write("requestsRootOk=false")
        write(f"requestsRootError={type(exc).__name__}: {exc}")

    write("\n[E] requests fake task")
    try:
        resp = requests.get(f"https://{HOST}/api/v1/tasks/fake_task_id", timeout=15)
        requests_task_ok = True
        write("requestsTaskOk=true")
        write(f"taskHttpStatus={resp.status_code}")
        write("businessSuccessNotRequired=true")
    except requests.exceptions.SSLError as exc:
        write("requestsTaskOk=false")
        write(f"requestsTaskError=SSLError: {exc}")
    except Exception as exc:
        write("requestsTaskOk=false")
        write(f"requestsTaskError={type(exc).__name__}: {exc}")

    write("\n[F] Proxy environment")
    for name in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy"]:
        write(f"{name}={sanitize_proxy(os.getenv(name))}")

    write("\n[G] certifi")
    try:
        import certifi
        write("certifiPresent=true")
        write("certifiWhere=" + certifi.where())
        write("certifiVersion=" + getattr(certifi, "__version__", "unknown"))
    except Exception as exc:
        write("certifiPresent=false")
        write(f"certifiError={type(exc).__name__}: {exc}")

    write("\n[Advice]")
    proxy_present = any(os.getenv(name) for name in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"])
    if not dns_ok:
        write("advice=DNS 失败：检查 DNS、校园网、公司网、代理或切换热点。")
    elif not tcp_ok:
        write("advice=TCP 443 失败：检查防火墙、校园网限制、代理、杀毒软件、网络出口。")
    elif not ssl_ok:
        write("advice=SSL 握手失败：检查证书链、HTTPS 拦截、杀毒软件 HTTPS 扫描、代理证书；可尝试升级 certifi/requests/urllib3，安装 truststore 或 python-certifi-win32。")
    elif not requests_root_ok or not requests_task_ok:
        write("advice=requests HTTPS 失败：可能是 Python requests 证书链或代理问题；不要在正式 Provider 中关闭 SSL 校验，可临时诊断 verify=False 但不建议正式使用。")
    elif proxy_present:
        write("advice=网络基础诊断通过，但检测到代理变量；确认代理能访问阿里云 DashScope，若代理导致 SSL 问题可临时取消代理重试。")
    else:
        write("advice=DNS/TCP/SSL/requests 均通过；若最小 DashScope API 仍失败，请继续检查请求参数、模型名、地域和权限。")

    write(f"SUMMARY dnsOk={dns_ok} tcp443Ok={tcp_ok} sslOk={ssl_ok} requestsRootOk={requests_root_ok} requestsTaskOk={requests_task_ok} proxyPresent={proxy_present}")
    return 0 if dns_ok and tcp_ok and ssl_ok and requests_root_ok and requests_task_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())