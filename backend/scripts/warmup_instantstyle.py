from __future__ import annotations

import os
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv
except ImportError as exc:
    raise SystemExit("缺少 python-dotenv，请先执行：pip install -r requirements.txt") from exc


load_dotenv(BACKEND_DIR / ".env")


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def main() -> int:
    if env_bool("MOCK_MODE", True):
        print("MOCK_MODE 当前不是 false，跳过 InstantStyle 真实模型预热。")
        print("如需预热真实模型，请在 backend/.env 中设置 MOCK_MODE=false。")
        return 1

    try:
        import torch
    except ImportError as exc:
        raise SystemExit("缺少 torch，请先执行：pip install -r requirements-instantstyle.txt") from exc

    device = os.getenv("INSTANTSTYLE_DEVICE", "cuda").strip().lower()
    print(f"MOCK_MODE=false")
    print(f"INSTANTSTYLE_DEVICE={device}")
    print(f"CUDA available={torch.cuda.is_available()}")

    if device.startswith("cuda") and not torch.cuda.is_available():
        print("当前环境没有可用 CUDA，无法运行 InstantStyle 真实推理，请使用 MOCK_MODE=true 或部署到 GPU 服务器。")
        return 1

    from instantstyle_service import InstantStyleService

    service = InstantStyleService()
    print("开始加载 StableDiffusionXLPipeline 与 IP-Adapter...")
    service._load_pipeline()
    print("模型加载完成，pipeline 已缓存，可启动 FastAPI 真实推理服务。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
