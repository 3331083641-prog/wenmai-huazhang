from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


BASE_URL = os.getenv("BACKEND_HOST", "http://127.0.0.1:8000").rstrip("/")


def request_json(path: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    data = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method="POST" if payload else "GET")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{path} failed with HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach {BASE_URL}{path}: {exc.reason}") from exc


def main() -> int:
    health = request_json("/health")
    print("GET /health")
    print(json.dumps(health, ensure_ascii=False, indent=2))

    payload = {
        "theme": "开封古城墙与祥云纹样",
        "style": "zhuxianzhen",
        "styleName": "朱仙镇木版年画",
        "outputType": "poster",
        "styleStrength": 0.65,
        "compositionMode": "portrait",
        "negativePrompt": None,
        "uploadedImage": None,
    }
    generated = request_json("/generate", payload)
    print("POST /generate")
    print(json.dumps(generated, ensure_ascii=False, indent=2))

    if not generated.get("imageUrl"):
        raise RuntimeError("POST /generate returned an empty imageUrl")

    print(f"imageUrl OK: {generated['imageUrl']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"check_mock_api failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
