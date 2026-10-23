from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "logs" / "provider_health.log"
URL = "http://127.0.0.1:8000/health"


def write(line: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line)


def main() -> int:
    write(f"\n[{datetime.now().isoformat(timespec='seconds')}] GET {URL}")
    try:
        response = requests.get(URL, timeout=30)
        write(f"HTTP {response.status_code}")
        data = response.json()
        write(json.dumps(data, ensure_ascii=False, indent=2))
        providers = data.get("providers") or {}
        for name, status in providers.items():
            write(f"- {name}: available={status.get('available')} message={status.get('message')}")
        return 0 if response.ok else 1
    except Exception as exc:
        write(f"ERROR: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())