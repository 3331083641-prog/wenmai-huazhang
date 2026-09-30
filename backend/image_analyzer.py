from __future__ import annotations

import base64
import colorsys
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image, ImageStat

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from style_config import UPLOAD_DIR, ensure_runtime_dirs


if load_dotenv is not None:
    load_dotenv(Path(__file__).resolve().parent / ".env", override=True, encoding="utf-8-sig")

DATA_URL_RE = re.compile(r"^data:(?P<mime>image/[a-zA-Z0-9.+-]+);base64,(?P<data>.+)$", re.DOTALL)
MAX_REFERENCE_IMAGE_BYTES = 10 * 1024 * 1024


def get_vision_provider() -> str:
    return "local_basic"


def get_analysis_mode() -> str:
    return "local_basic"


def analyze_image(uploaded_image: Optional[str]) -> dict[str, str]:
    if uploaded_image:
        return _analyze_uploaded_image(uploaded_image)

    return {
        "hasUploadedImage": "false",
        "subject": "未进行主体识别",
        "scene": "未进行场景识别",
        "colors": "由所选非遗风格决定",
        "composition": "由构图模式决定",
        "transferableElements": "无上传图；仅使用主题文本与所选风格提示",
        "savedPath": "",
        "width": "",
        "height": "",
        "brightness": "未分析",
        "dominantColor": "",
    }


def _decode_data_url(data_url: str) -> tuple[str, bytes]:
    normalized = (data_url or "").strip()
    if len(normalized) > 14_000_000:
        raise RuntimeError("参考图编码后超过接口允许的 10 MB 图片上限。")
    match = DATA_URL_RE.match(normalized)
    if not match:
        raise RuntimeError("uploadedImage 不是有效的 image/* base64 data URL。")
    try:
        mime = match.group("mime").lower()
        content = base64.b64decode(match.group("data"), validate=True)
        if mime not in {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/bmp", "image/tiff", "image/gif"}:
            raise RuntimeError("参考图格式不受支持，请使用 PNG、JPG 或 WEBP。")
        if len(content) > MAX_REFERENCE_IMAGE_BYTES:
            raise RuntimeError("参考图超过接口允许的 10 MB 图片上限。")
        return mime, content
    except Exception as exc:
        raise RuntimeError("uploadedImage base64 解码失败。") from exc


def _save_upload(mime: str, content: bytes) -> Path:
    ensure_runtime_dirs()
    suffix = "png" if mime.endswith("png") else "jpg"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = UPLOAD_DIR / f"upload_{stamp}.{suffix}"
    counter = 1
    while path.exists():
        path = UPLOAD_DIR / f"upload_{stamp}_{counter}.{suffix}"
        counter += 1
    path.write_bytes(content)
    return path


def _analyze_uploaded_image(uploaded_image: str) -> dict[str, str]:
    mime, content = _decode_data_url(uploaded_image)
    saved_path = _save_upload(mime, content)

    with Image.open(BytesIO(content)) as raw:
        image = raw.convert("RGB")
        width, height = image.size
        small = image.resize((1, 1))
        r, g, b = small.getpixel((0, 0))
        stat = ImageStat.Stat(image.resize((64, 64)))
        avg_r, avg_g, avg_b = [int(v) for v in stat.mean[:3]]
        brightness_value = int((avg_r * 0.299) + (avg_g * 0.587) + (avg_b * 0.114))
        hue, saturation, _ = colorsys.rgb_to_hsv(avg_r / 255, avg_g / 255, avg_b / 255)

    brightness = "偏亮" if brightness_value >= 170 else "偏暗" if brightness_value <= 90 else "明暗适中"
    orientation = "竖向画幅" if height > width * 1.15 else "横向画幅" if width > height * 1.15 else "接近方形画幅"
    color_name = _describe_color(hue, saturation, brightness_value)
    dominant_hex = f"#{r:02X}{g:02X}{b:02X}"

    return {
        "hasUploadedImage": "true",
        "subject": "当前未进行主体识别",
        "scene": "当前未进行场景识别",
        "colors": f"主色调约为 {color_name}（{dominant_hex}），整体{brightness}",
        "composition": f"{orientation}，尺寸 {width}x{height}",
        "transferableElements": "画幅方向、宽高比例、平均色彩和整体明暗；仅作为文字提示信息",
        "savedPath": str(saved_path),
        "width": str(width),
        "height": str(height),
        "brightness": brightness,
        "dominantColor": dominant_hex,
    }


def _describe_color(hue: float, saturation: float, brightness: int) -> str:
    if saturation < 0.12:
        return "低饱和灰白色系" if brightness > 150 else "低饱和深灰色系"
    degree = hue * 360
    if degree < 20 or degree >= 340:
        return "红色系"
    if degree < 45:
        return "橙黄色系"
    if degree < 75:
        return "黄色系"
    if degree < 160:
        return "绿色系"
    if degree < 210:
        return "青绿色系"
    if degree < 260:
        return "蓝色系"
    if degree < 310:
        return "紫色系"
    return "品红色系"
