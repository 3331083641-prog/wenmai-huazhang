from __future__ import annotations

import base64
import html
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Mapping, Optional, Tuple

from style_config import OUTPUT_DIR, UPLOAD_DIR, StyleConfig, ensure_runtime_dirs


DATA_URL_RE = re.compile(r"^data:(?P<mime>image/[a-zA-Z0-9.+-]+);base64,(?P<data>.+)$", re.DOTALL)


def make_output_filename(prefix: str, suffix: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    token = uuid.uuid4().hex[:8]
    clean_prefix = re.sub(r"[^a-zA-Z0-9_-]+", "-", prefix).strip("-") or "image"
    clean_suffix = suffix.lstrip(".")
    return f"{clean_prefix}_{timestamp}_{token}.{clean_suffix}"


def output_url(base_url: str, output_path: Path) -> str:
    return f"{base_url.rstrip('/')}/outputs/{output_path.name}"


def save_mock_svg(
    *,
    style: StyleConfig,
    payload: Mapping[str, object],
    enhanced_prompt: str,
    culture_card: Mapping[str, str],
) -> Path:
    ensure_runtime_dirs()

    title = html.escape(str(culture_card.get("title", style.name)))
    theme = html.escape(str(payload.get("theme") or "纹脉华章"))
    visual_features = html.escape(style.visual_features)
    symbolic = html.escape(style.symbolic_meaning)
    prompt = html.escape(enhanced_prompt[:180] + ("..." if len(enhanced_prompt) > 180 else ""))
    primary, paper, accent = style.palette

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{paper}"/>
      <stop offset="55%" stop-color="#F8F1E3"/>
      <stop offset="100%" stop-color="{primary}"/>
    </linearGradient>
    <pattern id="grid" width="64" height="64" patternUnits="userSpaceOnUse">
      <path d="M 64 0 L 0 0 0 64" fill="none" stroke="{accent}" stroke-opacity="0.16" stroke-width="2"/>
    </pattern>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="18" stdDeviation="18" flood-color="#211814" flood-opacity="0.18"/>
    </filter>
  </defs>
  <rect width="1024" height="1024" fill="url(#bg)"/>
  <rect width="1024" height="1024" fill="url(#grid)" opacity="0.85"/>
  <circle cx="166" cy="176" r="86" fill="{primary}" opacity="0.18"/>
  <circle cx="870" cy="842" r="146" fill="{paper}" opacity="0.32"/>
  <rect x="92" y="92" width="840" height="840" rx="34" fill="#FFFDF7" opacity="0.9" filter="url(#shadow)"/>
  <rect x="124" y="124" width="776" height="776" rx="20" fill="none" stroke="{primary}" stroke-width="7"/>
  <rect x="154" y="154" width="716" height="716" rx="14" fill="none" stroke="{accent}" stroke-width="2" stroke-dasharray="14 14" opacity="0.62"/>

  <g transform="translate(512 412)">
    <circle r="188" fill="{primary}" opacity="0.10"/>
    <path d="M0,-224 C62,-118 182,-108 224,0 C118,62 108,182 0,224 C-62,118 -182,108 -224,0 C-118,-62 -108,-182 0,-224Z" fill="{primary}" opacity="0.88"/>
    <path d="M0,-154 C42,-74 116,-70 154,0 C74,42 70,116 0,154 C-42,74 -116,70 -154,0 C-74,-42 -70,-116 0,-154Z" fill="{paper}" opacity="0.92"/>
    <path d="M-118,0 C-66,-76 66,-76 118,0 C66,76 -66,76 -118,0Z" fill="{accent}" opacity="0.78"/>
    <circle cx="0" cy="0" r="42" fill="{primary}" opacity="0.95"/>
  </g>

  <text x="512" y="742" text-anchor="middle" font-family="Noto Serif CJK SC, SimSun, serif" font-size="44" fill="#2B211D" font-weight="700">{html.escape(style.name)}</text>
  <text x="512" y="792" text-anchor="middle" font-family="Noto Sans CJK SC, Microsoft YaHei, sans-serif" font-size="24" fill="#5E4A40">{title}</text>
  <text x="512" y="834" text-anchor="middle" font-family="Noto Sans CJK SC, Microsoft YaHei, sans-serif" font-size="18" fill="#7A6358">MOCK_MODE=true · FastAPI 联调占位图</text>

  <foreignObject x="160" y="860" width="704" height="96">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-family: 'Microsoft YaHei', sans-serif; font-size: 18px; line-height: 1.45; color: #4B3B34; text-align: center;">
      <div>{theme}</div>
      <div style="font-size: 14px; opacity: .78; margin-top: 8px;">{visual_features}</div>
    </div>
  </foreignObject>

  <metadata>{symbolic} | {prompt}</metadata>
</svg>
"""
    output_path = OUTPUT_DIR / make_output_filename(f"mock_{style.id}", "svg")
    output_path.write_text(svg, encoding="utf-8")
    return output_path


def decode_data_url_image(data_url: Optional[str]) -> Optional[Tuple[str, bytes]]:
    if not data_url:
        return None
    match = DATA_URL_RE.match(data_url.strip())
    if not match:
        return None
    try:
        return match.group("mime"), base64.b64decode(match.group("data"), validate=True)
    except ValueError:
        return None


def save_uploaded_image(data_url: Optional[str]) -> Optional[Path]:
    decoded = decode_data_url_image(data_url)
    if decoded is None:
        return None

    mime, content = decoded
    suffix = "png" if mime.endswith("png") else "jpg"
    ensure_runtime_dirs()
    output_path = UPLOAD_DIR / make_output_filename("upload", suffix)
    output_path.write_bytes(content)
    return output_path


def save_pil_image(image: object, *, prefix: str = "instantstyle") -> Path:
    ensure_runtime_dirs()
    output_path = OUTPUT_DIR / make_output_filename(prefix, "png")
    image.save(output_path)
    return output_path


def save_image_bytes(content: bytes, *, prefix: str = "provider", suffix: str = "png") -> Path:
    ensure_runtime_dirs()
    output_path = OUTPUT_DIR / make_output_filename(prefix, suffix)
    output_path.write_bytes(content)
    return output_path

def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = (value or "#CCCCCC").strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except Exception:
        return (204, 204, 204)


def _load_font(size: int, *, bold: bool = False):
    from PIL import ImageFont

    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap_text(draw, text: str, font, max_width: int, max_lines: int) -> list[str]:
    text = str(text or "").replace("\r", " ").replace("\n", " ").strip()
    if not text:
        return []
    lines: list[str] = []
    current = ""
    for char in text:
        trial = current + char
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = char
            if len(lines) >= max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and len("".join(lines)) < len(text):
        lines[-1] = lines[-1].rstrip("，。,. ") + "..."
    return lines


def save_demo_png(
    *,
    style: StyleConfig,
    payload: Mapping[str, object],
    enhanced_prompt: str,
    culture_card: Mapping[str, str],
    prefix: str = "fast_demo",
) -> Path:
    """Render a local PNG demo image for fallback flows.

    The file is intentionally a real PNG rather than an SVG so browser/image
    checks can verify /outputs static serving with normal image MIME types.
    """
    from PIL import Image, ImageDraw

    ensure_runtime_dirs()
    width, height = 1024, 1024
    primary, paper, accent = style.palette
    primary_rgb = _hex_to_rgb(primary)
    paper_rgb = _hex_to_rgb(paper)
    accent_rgb = _hex_to_rgb(accent)
    ink = (43, 33, 29)

    image = Image.new("RGB", (width, height), paper_rgb)
    draw = ImageDraw.Draw(image, "RGBA")

    for y in range(height):
        blend = y / max(1, height - 1)
        r = int(paper_rgb[0] * (1 - blend) + primary_rgb[0] * blend * 0.45)
        g = int(paper_rgb[1] * (1 - blend) + primary_rgb[1] * blend * 0.45)
        b = int(paper_rgb[2] * (1 - blend) + primary_rgb[2] * blend * 0.45)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    for x in range(0, width, 64):
        draw.line([(x, 0), (x, height)], fill=(*accent_rgb, 32), width=2)
    for y in range(0, height, 64):
        draw.line([(0, y), (width, y)], fill=(*accent_rgb, 32), width=2)

    draw.rounded_rectangle((88, 88, 936, 936), radius=34, fill=(255, 253, 247, 235), outline=(*primary_rgb, 255), width=6)
    draw.rounded_rectangle((126, 126, 898, 898), radius=20, outline=(*accent_rgb, 150), width=3)

    cx, cy = 512, 404
    draw.ellipse((cx - 190, cy - 190, cx + 190, cy + 190), fill=(*primary_rgb, 28))
    diamond = [(cx, cy - 228), (cx + 228, cy), (cx, cy + 228), (cx - 228, cy)]
    draw.polygon(diamond, fill=(*primary_rgb, 224))
    inner = [(cx, cy - 154), (cx + 154, cy), (cx, cy + 154), (cx - 154, cy)]
    draw.polygon(inner, fill=(*paper_rgb, 238))
    eye = [(cx - 126, cy), (cx - 74, cy - 66), (cx, cy - 82), (cx + 74, cy - 66), (cx + 126, cy), (cx + 74, cy + 66), (cx, cy + 82), (cx - 74, cy + 66)]
    draw.polygon(eye, fill=(*accent_rgb, 210))
    draw.ellipse((cx - 42, cy - 42, cx + 42, cy + 42), fill=(*primary_rgb, 245))

    title_font = _load_font(48, bold=True)
    sub_font = _load_font(26)
    small_font = _load_font(20)
    tiny_font = _load_font(16)

    style_name = str(style.name or "非遗风格")
    title = str(culture_card.get("title") or payload.get("theme") or "纹脉华章")
    theme = str(payload.get("theme") or "非遗文旅海报")

    def center_text(y: int, text: str, font, fill=ink):
        bbox = draw.textbbox((0, 0), text, font=font)
        draw.text(((width - (bbox[2] - bbox[0])) / 2, y), text, font=font, fill=fill)

    center_text(690, style_name, title_font)
    for i, line in enumerate(_wrap_text(draw, title, sub_font, 760, 2)):
        center_text(754 + i * 34, line, sub_font, fill=primary_rgb)

    draw.text((160, 842), "演示生成 / FAST DEMO FALLBACK", font=tiny_font, fill=(*primary_rgb, 255))
    strength_text = f"风格强度: {float(payload.get('styleStrength') or 0):.2f}"
    analysis = payload.get("imageAnalysis") if isinstance(payload.get("imageAnalysis"), dict) else {}
    upload_text = "已接收参考图" if analysis.get("hasUploadedImage") == "true" or payload.get("uploadedImage") else "未上传参考图"
    neg_text = "含负面提示词" if payload.get("negativePrompt") else "无负面提示词"
    draw.text((160, 818), f"{strength_text} · {upload_text} · {neg_text}", font=tiny_font, fill=(*primary_rgb, 255))
    for i, line in enumerate(_wrap_text(draw, theme, small_font, 704, 2)):
        center_text(870 + i * 28, line, small_font, fill=(75, 59, 52))

    output_path = OUTPUT_DIR / make_output_filename(f"{prefix}_{style.id}", "png")
    image.save(output_path, format="PNG", optimize=False)
    return output_path


