"""把一次成功的生成落盘为一个「真实案例」。

设计原则
--------
1. **绝不覆盖已有案例**：新案例目录名带时间戳与短请求号，内置五件永远是只读的。
2. **不伪造溯源字段**：sha256 / 字节数 / 尺寸都现算，拿不到就留空，不编。
3. **只沉淀真图**：mock / fast_demo 这类演示产物默认不写入案例库（可用
   ``AUTO_SAVE_DEMO=true`` 打开，仅供本机验证链路）。
4. **失败不影响出图**：保存是副作用，出错只记录，不改变 /generate 的响应。

目录结构（与 docs/examples/zhuxianzhen 同构）::

    docs/examples/<styleId>-<YYYYMMDD-HHMMSS>-<rid4>/
        generated.png      必选
        reference.png      有上传图时才有
        culture_card.png   必选（Pillow 绘制，1080x1440）
        metadata.json      必选
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from PIL import Image, ImageDraw, ImageFont

from style_config import PROJECT_ROOT, get_style

EXAMPLES_DIR = PROJECT_ROOT / "docs" / "examples"
CARD_SIZE = (1080, 1440)
# 与现有五件真实案例保持同一套视觉
PAPER = (248, 238, 220)
INK = (63, 43, 31)
PRIMARY = (158, 36, 27)
GOLD = (210, 161, 74)
MUTED = (110, 92, 78)

REAL_PROVIDERS = {"dashscope_qwen_image", "instantstyle"}

FONT_CANDIDATES = (
    ("bold", ("C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/simhei.ttf")),
    ("regular", ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simsun.ttc", "C:/Windows/Fonts/Deng.ttf")),
)


def auto_save_enabled() -> bool:
    return os.getenv("AUTO_SAVE_CASES", "true").strip().lower() in {"1", "true", "yes", "on"}


def demo_save_enabled() -> bool:
    return os.getenv("AUTO_SAVE_DEMO", "false").strip().lower() in {"1", "true", "yes", "on"}


def _max_cases() -> int:
    try:
        return max(5, int(os.getenv("AUTO_SAVE_MAX_CASES", "200")))
    except ValueError:
        return 200


# --------------------------------------------------------------------------- 工具

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean(text: object, limit: int = 400) -> str:
    value = " ".join(str(text or "").split())
    return value[:limit]


def _split_features(text: object) -> list[str]:
    raw = str(text or "")
    parts: list[str] = []
    for chunk in raw.replace("；", "、").replace(";", "、").split("、"):
        item = chunk.strip(" ，,。")
        if item and item not in parts:
            parts.append(item)
    return parts[:8]


def _font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name, candidates in FONT_CANDIDATES:
        if name != weight:
            continue
        for path in candidates:
            if Path(path).exists():
                try:
                    return ImageFont.truetype(path, size=size)
                except OSError:
                    continue
    return ImageFont.load_default()


def _has_cjk_font() -> bool:
    return any(Path(path).exists() for _, paths in FONT_CANDIDATES for path in paths)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    """按像素宽度折行；中文逐字、英文按词，尽量不切断单词。"""
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = char if char != " " else ""
    if current:
        lines.append(current)
    return lines


# --------------------------------------------------------------------------- 文化卡

def _render_culture_card(*, image_path: Path, art_title: str, style_name: str,
                         theme: str, features: list[str], culture_text: str,
                         colors: list[str], scenes: list[str], footer_left: str,
                         footer_right: str, out_path: Path) -> str:
    """按现有五张文化卡的版式绘制 1080x1440 卡片。"""
    canvas = Image.new("RGB", CARD_SIZE, PAPER)
    draw = ImageDraw.Draw(canvas)
    width, height = CARD_SIZE

    # 双线金框
    draw.rectangle([(28, 28), (width - 28, height - 28)], outline=GOLD, width=3)
    draw.rectangle([(40, 40), (width - 40, height - 40)], outline=(226, 205, 168), width=1)

    f_brand = _font(40, "bold")
    f_small = _font(20, "regular")
    f_style = _font(26, "bold")
    f_h2 = _font(28, "bold")
    f_body = _font(23, "regular")

    margin = 80
    # 页首
    draw.text((margin, 68), "纹脉华章", font=f_brand, fill=PRIMARY)
    draw.text((margin, 122), "文化解读 · 作品卡", font=f_small, fill=MUTED)
    style_w = draw.textlength(style_name, font=f_style)
    draw.text((width - margin - style_w, 76), style_name, font=f_style, fill=PRIMARY)

    # 作品图：白底圆角卡片，保持原图比例，宽度 80%
    art_w = int(width * 0.78)
    with Image.open(image_path) as source:
        art = source.convert("RGB")
        ratio = art.height / art.width
        art_h = int(art_w * ratio)
        max_h = int(height * 0.52)
        if art_h > max_h:
            art_h = max_h
            art_w = int(art_h / ratio)
        art = art.resize((art_w, art_h), Image.LANCZOS)

    pad = 14
    card_w, card_h = art_w + pad * 2, art_h + pad * 2
    card_x = (width - card_w) // 2
    card_y = 168
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)],
                           radius=18, fill=(255, 253, 248), outline=(228, 210, 178), width=2)
    canvas.paste(art, (card_x + pad, card_y + pad))

    # 正文区
    y = card_y + card_h + 34
    content_w = width - margin * 2

    def section(title: str, body: str, max_lines: int = 4) -> None:
        nonlocal y
        if y > height - 190:
            return
        draw.text((margin, y), title, font=f_h2, fill=INK)
        y += 40
        draw.line([(margin, y), (margin + 42, y)], fill=GOLD, width=2)
        y += 12
        for line in _wrap(draw, body, f_body, content_w)[:max_lines]:
            draw.text((margin, y), line, font=f_body, fill=(78, 62, 50))
            y += 36
        y += 16

    draw.text((margin, y), art_title, font=_font(46, "bold"), fill=INK)
    y += 62
    section("画面主题", theme, 2)
    section("风格特征", "、".join(features[:6]) or style_name, 3)
    section("文化解读", culture_text, 5)
    if colors:
        section("主要色彩", "、".join(colors[:6]), 1)
    if scenes:
        section("推荐应用", "、".join(scenes[:4]), 1)

    # 页脚
    draw.line([(margin, height - 108), (width - margin, height - 108)], fill=(226, 205, 168), width=1)
    draw.text((margin, height - 88), footer_left, font=f_small, fill=MUTED)
    right_w = draw.textlength(footer_right, font=f_small)
    draw.text((width - margin - right_w, height - 88), footer_right, font=f_small, fill=MUTED)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="PNG", optimize=True)
    return "pillow_png"


# --------------------------------------------------------------------------- 保存

def _fallback_vision_analysis(*, title: str, culture_card: Mapping[str, Any],
                              style, image_analysis: Mapping[str, Any]) -> dict[str, Any]:
    """视觉解读缺失时，用文化卡与风格库信息拼一个**可解释来源**的最小结构。

    这不是伪造模型输出：metadata 里 analysisSource 会标 template_fallback，
    前端也会显示「模板兜底」。
    """
    features = _split_features(culture_card.get("visualFeatures"))
    colors = _split_features(image_analysis.get("colors"))
    return {
        "title": title,
        "theme_summary": _clean(culture_card.get("title") or title, 200),
        "composition": _clean(image_analysis.get("composition") or "未做构图识别", 120),
        "style_interpretation": _clean(f"{style.name}：{style.visual_features}", 240),
        "culture_interpretation": _clean(culture_card.get("symbolicMeaning") or style.symbolic_meaning, 300),
        "observed_subjects": [str(style.name)],
        "dominant_colors": colors[:6],
        "visual_features": features[:6],
        "recommended_scenes": _split_features(culture_card.get("applicationScenario"))[:4],
        "theme_alignment": "未评估",
        "style_alignment": "未评估",
    }


def save_case(*, payload: Mapping[str, Any], response: Mapping[str, Any], base_url: str) -> dict[str, Any] | None:
    """把一次成功生成写成 docs/examples 下的标准案例。失败返回 None，不抛。"""
    provider = str(response.get("provider") or "")
    if provider not in REAL_PROVIDERS and not demo_save_enabled():
        return None
    if not response.get("success"):
        return None

    local_raw = str(response.get("localPath") or "").strip()
    if not local_raw:
        return None
    local_path = Path(local_raw)
    # 注意：Path("") 会变成当前目录，is_file() 才能挡住这种空路径
    if not local_path.is_file() or local_path.stat().st_size == 0:
        return None

    style = get_style(str(payload.get("style") or "zhuxianzhen"))
    now = datetime.now().astimezone()
    request_id = str((response.get("debug") or {}).get("requestId") or "")[:6] or "000000"
    case_id = f"{style.id}-{now.strftime('%Y%m%d-%H%M%S')}-{request_id[:4]}"
    target = EXAMPLES_DIR / case_id
    suffix = 1
    while target.exists():
        suffix += 1
        target = EXAMPLES_DIR / f"{case_id}-{suffix}"
        case_id = target.name

    target.mkdir(parents=True, exist_ok=False)

    generated = target / "generated.png"
    try:
        with Image.open(local_path) as image:
            image.convert("RGB").save(generated, format="PNG", optimize=True)
    except Exception:
        shutil.copyfile(local_path, generated)

    with Image.open(generated) as image:
        art_size = {"width": image.width, "height": image.height}

    # 参考图（用户上传时才有）
    image_analysis = dict(response.get("imageAnalysis") or {})
    saved_path_raw = str(image_analysis.get("savedPath") or "").strip()
    reference_path = Path(saved_path_raw) if saved_path_raw else None
    reference_name = ""
    reference_sha = ""
    reference_source = "none"
    if reference_path is not None and reference_path.is_file() and reference_path.stat().st_size > 0:
        reference_name = "reference.png"
        try:
            with Image.open(reference_path) as image:
                image.convert("RGB").save(target / reference_name, format="PNG", optimize=True)
        except Exception:
            shutil.copyfile(reference_path, target / reference_name)
        reference_sha = _sha256(target / reference_name)
        reference_source = "user_upload"

    vision = response.get("visionAnalysis")
    culture_card = dict(response.get("cultureCard") or {})
    analysis_source = str(response.get("analysisSource") or "template_fallback")
    art_title = _clean((vision or {}).get("title") or culture_card.get("title") or payload.get("theme") or style.name, 60)
    theme_text = _clean(payload.get("theme") or art_title, 200)

    if not isinstance(vision, dict) or not vision:
        vision = _fallback_vision_analysis(title=art_title, culture_card=culture_card,
                                           style=style, image_analysis=image_analysis)
        analysis_source = "template_fallback"

    features = [str(item) for item in (vision.get("visual_features") or [])][:8]
    culture_text = _clean(vision.get("culture_interpretation") or culture_card.get("symbolicMeaning") or style.symbolic_meaning, 400)
    colors = [str(item) for item in (vision.get("dominant_colors") or [])][:6]
    scenes = [str(item) for item in (vision.get("recommended_scenes") or [])][:4]

    card_path = target / "culture_card.png"
    if _has_cjk_font():
        card_export = _render_culture_card(
            image_path=generated,
            art_title=art_title,
            style_name=style.name,
            theme=theme_text,
            features=features,
            culture_text=culture_text,
            colors=colors,
            scenes=scenes,
            footer_left=f"生成于 {now.strftime('%Y/%m/%d %H:%M:%S')}",
            footer_right=f"{provider} · {analysis_source}",
            out_path=card_path,
        )
    else:
        # 没有中文字体时不画错字卡片，退化为「成图 + 说明存储」，并在 metadata 标明
        shutil.copyfile(generated, card_path)
        card_export = "image_only_fallback"

    generated_sha = _sha256(generated)
    card_sha = _sha256(card_path)

    metadata = {
        "caseId": case_id,
        "caseOrigin": "runtime",
        # 互动解读（热点/章节）需要人工标注，运行期案例默认没有，前端据此不显示互动入口
        "experienceId": "",
        "styleId": style.id,
        "styleName": style.name,
        "referenceSubject": _clean(payload.get("subjectLock") or art_title, 60),
        "artworkTitle": art_title,
        "theme": theme_text,
        "referenceSource": reference_source,
        "sourceFilename": reference_name,
        "referenceFilename": reference_name,
        "referenceSha256": reference_sha,
        "provider": provider,
        "model": str(response.get("model") or ""),
        "styleStrength": float(payload.get("styleStrength") or 0.65),
        "compositionMode": str(payload.get("compositionMode") or "portrait"),
        "outputType": str(payload.get("outputType") or "poster"),
        "negativePrompt": str(payload.get("negativePrompt") or ""),
        "inputImageCount": 1 if reference_name else 0,
        "generatedAt": now.isoformat(),
        "generationAttempt": "runtime_auto_save",
        "generationSucceeded": True,
        "referenceImageUsed": bool(response.get("referenceImageUsed")),
        "modelInputImageCount": 1 if response.get("referenceImageUsed") else 0,
        "analysisSource": analysis_source,
        "visionProvider": "ollama_local" if analysis_source == "qwen3_vl" else "",
        "visionModel": "",
        "cultureCardAnalysisSource": analysis_source,
        "generationHistory": [{
            "generation": "runtime_auto_save",
            "generatedAt": now.isoformat(),
            "model": str(response.get("model") or ""),
            "styleStrength": float(payload.get("styleStrength") or 0.65),
            "referenceImageUsed": bool(response.get("referenceImageUsed")),
            "modelInputImageCount": 1 if response.get("referenceImageUsed") else 0,
            "generatedSha256": generated_sha,
            "analysisSource": analysis_source,
        }],
        "outputImageCount": 1,
        "generatedSha256": generated_sha,
        "generatedBytes": generated.stat().st_size,
        "artworkSize": art_size,
        "visionAnalysis": vision,
        "visionAnalysisRuntime": response.get("visionAnalysisRuntime") or {},
        "cultureCard": culture_card,
        "enhancedPrompt": str(response.get("enhancedPrompt") or ""),
        "cultureCardGeneratedSha256": card_sha,
        "cultureCardSha256": card_sha,
        "cultureCardExport": card_export,
        "caseFiles": {
            "generated": "generated.png",
            "reference": reference_name,
            "cultureCard": "culture_card.png",
        },
    }

    (target / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    _prune_cases()

    return {
        "caseId": case_id,
        "artworkTitle": art_title,
        "styleId": style.id,
        "styleName": style.name,
        "generatedAt": metadata["generatedAt"],
        "images": {
            "generated": f"{base_url.rstrip('/')}/examples/{case_id}/generated.png",
            "reference": f"{base_url.rstrip('/')}/examples/{case_id}/reference.png" if reference_name else "",
            "cultureCard": f"{base_url.rstrip('/')}/examples/{case_id}/culture_card.png",
        },
    }


# --------------------------------------------------------------------------- 列表 / 清理

def list_cases(*, base_url: str) -> list[dict[str, Any]]:
    """扫描 docs/examples，返回可展示的案例（内置 + 运行时）。"""
    if not EXAMPLES_DIR.exists():
        return []
    root = base_url.rstrip("/")
    items: list[dict[str, Any]] = []
    for folder in EXAMPLES_DIR.iterdir():
        if not folder.is_dir():
            continue
        meta_path = folder / "metadata.json"
        if not meta_path.exists():
            continue
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        case_id = str(metadata.get("caseId") or folder.name)
        files = metadata.get("caseFiles") or {}
        generated_name = files.get("generated") or "generated.png"
        card_name = files.get("cultureCard") or "culture_card.png"
        reference_name = files.get("reference") or metadata.get("referenceFilename") or ""

        generated_url = f"{root}/examples/{folder.name}/{generated_name}"
        card_url = f"{root}/examples/{folder.name}/{card_name}" if (folder / card_name).exists() else ""
        reference_url = f"{root}/examples/{folder.name}/{reference_name}" if reference_name and (folder / reference_name).exists() else ""

        if not (folder / generated_name).exists():
            continue

        metadata.setdefault("caseId", case_id)
        metadata.setdefault("caseOrigin", "curated")
        items.append({
            **metadata,
            "caseId": case_id,
            "folder": folder.name,
            "referenceUrl": reference_url,
            "imageUrl": generated_url,
            "cardUrl": card_url,
            "experienceId": metadata.get("experienceId") or "",
        })

    items.sort(key=lambda item: str(item.get("generatedAt") or ""), reverse=True)
    return items


def _prune_cases() -> None:
    """超过上限时只清理运行时案例，内置五件永不删除。"""
    if not EXAMPLES_DIR.exists():
        return
    runtime: list[tuple[str, Path]] = []
    for folder in EXAMPLES_DIR.iterdir():
        if not folder.is_dir():
            continue
        meta_path = folder / "metadata.json"
        if not meta_path.exists():
            continue
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if metadata.get("caseOrigin") == "runtime":
            runtime.append((str(metadata.get("generatedAt") or ""), folder))

    limit = _max_cases()
    if len(runtime) <= limit:
        return
    runtime.sort(key=lambda item: item[0])
    for _, folder in runtime[: len(runtime) - limit]:
        shutil.rmtree(folder, ignore_errors=True)


def delete_case(case_id: str) -> bool:
    """仅允许删除运行时案例（内置案例受保护）。"""
    if not case_id or "/" in case_id or "\\" in case_id or ".." in case_id:
        return False
    folder = EXAMPLES_DIR / case_id
    if not folder.is_dir():
        return False
    meta_path = folder / "metadata.json"
    if not meta_path.exists():
        return False
    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if metadata.get("caseOrigin") != "runtime":
        return False
    shutil.rmtree(folder, ignore_errors=True)
    return True