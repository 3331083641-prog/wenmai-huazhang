from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BACKEND_DIR / ".env"
STYLE_REFS_DIR = BACKEND_DIR / "style_refs"
STYLE_REF_FILES = [
    "zhuxianzhen.png",
    "bianxiu.png",
    "songhua.png",
    "qinghua.png",
    "jianzhi.png",
]


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def print_check(label: str, ok: bool, detail: str = "") -> None:
    status = "OK" if ok else "MISSING"
    suffix = f" - {detail}" if detail else ""
    print(f"- {label}: {status}{suffix}")


def main() -> int:
    load_env_file(ENV_PATH)

    mock_mode = env_bool("MOCK_MODE", True)
    provider = os.getenv("GENERATION_PROVIDER", "mock").strip().lower()

    print("InstantStyle readiness check")
    print("=" * 32)
    print(f"backend/.env: {ENV_PATH if ENV_PATH.exists() else 'MISSING'}")
    print(f"MOCK_MODE={str(mock_mode).lower()}")
    print(f"GENERATION_PROVIDER={provider}")
    print()

    can_enter_real_mode = (not mock_mode) and provider == "instantstyle"
    print_check("real mode config", can_enter_real_mode, "requires MOCK_MODE=false and GENERATION_PROVIDER=instantstyle")

    torch_ok = module_available("torch")
    print_check("torch", torch_ok)
    cuda_ok = False
    if torch_ok:
        try:
            import torch

            cuda_ok = bool(torch.cuda.is_available())
        except Exception as exc:
            print(f"  torch import error: {exc}")
    print_check("CUDA", cuda_ok)

    diffusers_ok = module_available("diffusers")
    print_check("diffusers", diffusers_ok)

    refs_ok = True
    print()
    print("style_refs")
    for filename in STYLE_REF_FILES:
        path = STYLE_REFS_DIR / filename
        exists = path.exists()
        refs_ok = refs_ok and exists
        print_check(filename, exists, str(path))

    ready = can_enter_real_mode and torch_ok and cuda_ok and diffusers_ok and refs_ok
    print()
    if ready:
        print("Result: READY - backend can enter real InstantStyle mode.")
        return 0

    print("Result: NOT READY - fix the missing items above before real generation.")
    if not cuda_ok:
        print("Hint: 当前环境没有可用 CUDA，无法运行 InstantStyle 真实推理，请使用 MOCK_MODE=true 或部署到 GPU 服务器。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
