from __future__ import annotations

import importlib.util
import os
import platform
import sys
from pathlib import Path


STYLE_REF_FILES = [
    "zhuxianzhen.png",
    "bianxiu.png",
    "songhua.png",
    "qinghua.png",
    "jianzhi.png",
]

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BACKEND_DIR / ".env"
STYLE_REFS_DIR = BACKEND_DIR / "style_refs"
OUTPUTS_DIR = BACKEND_DIR / "outputs"


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def env_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def module_installed(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def status(ok: bool) -> str:
    return "OK" if ok else "MISSING"


def main() -> int:
    env_values = load_env_file(ENV_PATH)
    mock_mode_value = os.getenv("MOCK_MODE", env_values.get("MOCK_MODE", "true"))
    mock_mode = env_bool(mock_mode_value, True)
    generation_provider = os.getenv("GENERATION_PROVIDER", env_values.get("GENERATION_PROVIDER", "")).strip().lower()
    enable_instantstyle = env_bool(os.getenv("ENABLE_INSTANTSTYLE", env_values.get("ENABLE_INSTANTSTYLE")), False)
    if not generation_provider:
        generation_provider = "instantstyle" if enable_instantstyle or not mock_mode else "mock"

    checks_ok = True

    print("纹脉华章 backend 环境检查")
    print("=" * 36)
    print(f"Python: {platform.python_version()} ({sys.executable})")
    print(f"backend/.env: {status(ENV_PATH.exists())} - {ENV_PATH}")
    if not ENV_PATH.exists():
        checks_ok = False
    print(f"MOCK_MODE: {mock_mode_value}")
    print(f"GENERATION_PROVIDER: {generation_provider}")
    print(f"ENABLE_INSTANTSTYLE: {enable_instantstyle}")
    print()

    print("目录检查")
    print(f"- backend/outputs: {status(OUTPUTS_DIR.exists())} - {OUTPUTS_DIR}")
    if not OUTPUTS_DIR.exists():
        checks_ok = False
    print(f"- backend/style_refs: {status(STYLE_REFS_DIR.exists())} - {STYLE_REFS_DIR}")
    if not STYLE_REFS_DIR.exists():
        checks_ok = False
    print()

    print("风格参考图检查")
    for filename in STYLE_REF_FILES:
        path = STYLE_REFS_DIR / filename
        exists = path.exists()
        print(f"- {filename}: {status(exists)}")
        if not exists:
            checks_ok = False
    print()

    if generation_provider == "mock":
        print("真实推理依赖检查: 跳过，当前 GENERATION_PROVIDER=mock")
    else:
        print("真实推理依赖检查")
        torch_installed = module_installed("torch")
        print(f"- torch: {status(torch_installed)}")
        if not torch_installed:
            checks_ok = False
        else:
            try:
                import torch

                print(f"- CUDA available: {torch.cuda.is_available()}")
                if not torch.cuda.is_available():
                    checks_ok = False
            except Exception as exc:
                checks_ok = False
                print(f"- CUDA available: ERROR ({exc})")

        for module_name in ["diffusers", "transformers", "accelerate", "safetensors"]:
            installed = module_installed(module_name)
            print(f"- {module_name}: {status(installed)}")
            if not installed:
                checks_ok = False

    print()
    if checks_ok:
        print("检查完成: 环境看起来可用。")
        return 0

    print("检查完成: 存在缺失项，请根据上方提示补齐。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
