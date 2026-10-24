"""把一张新生成的图，变成一件「可互动」的真实案例。

一次调用做完全部步骤：
  1. 落盘成标准案例目录 docs/examples/<slug>/（generated.png + metadata.json）
  2. 用单目深度估计找画面前后关系，自动选 4–6 处热点（标 approximate，待人工复核）
  3. 按风格知识包写 3 折叙事（chapter 的镜头参数由热点几何算出）
  4. 写出 experience.json（前端自动加载，无需改代码）
  5. 调 build_painting_world.py 生成画境资产（深度网格 / 遮罩 / 抠像 / world.json）
  6. 回写 metadata.json 的 experienceId，并写一份 ingest-report.json

设计边界（必须诚实写在报告与 UI 里）：
  * 热点坐标是**自动估计**的，不是逐点裁切复核过的；因此 locationStatus=approximate、
    reviewStatus=pending，前端会把它们显示为「待复核」。
  * 文化解读沿用该风格的知识包与来源编号（SRC-*），不凭空生成新的文化说法。
  * 深度是单图估计，只能给前后关系，不是三维重建。

用法：
  python scripts/interactive/ingest_case.py \
      --image D:\\out\\new.png --slug zx-20261021-a --style-id zhuxianzhen \
      --title "瑞猫迎春·新作" [--no-vlm] [--skip-world] [--force]

  # 已有案例重新生成互动内容
  python scripts/interactive/ingest_case.py --refresh zhuxianzhen-20261021-153012-ab12
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "docs" / "examples"
BUILDER = PROJECT_ROOT / "scripts" / "interactive" / "build_painting_world.py"
PUBLIC_WORLD = PROJECT_ROOT / "frontend" / "public" / "interactive"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("QWEN_VL_MODEL", "qwen3-vl:4b-instruct-q4_K_M")

# --------------------------------------------------------------------------- #
# 风格知识包：新图沿用同风格的来源编号与解读，不编造文化事实
# --------------------------------------------------------------------------- #
STYLES: dict[str, dict] = {
    "zhuxianzhen": {
        "name": "朱仙镇木版年画",
        "accent": "#9E241B", "accentSoft": "#E8C9A0", "paper": "#F6EFE3",
        "ink": "#3F2B1F", "gold": "#B98B4E",
        "sources": ["SRC-ZXZ-NIANHUA-001", "SRC-ZXZ-CRAFT-002"],
        "kicker": "线刻转译",
        "chapters": [
            ("第一折 · 线", "线先立骨", "年画先刻线版，墨线定下轮廓与主要结构；颜色是后来一块块套上去的，所以线的走向决定了整幅画的骨架。"),
            ("第二折 · 色", "一色一块", "每换一种颜色就要多一块版，色块之间的错位靠手工对版控制。看画面里不同颜色交界处，能读到套色留下的位置关系。"),
            ("第三折 · 形", "圆里带方", "年画造型讲究饱满、对称、边界清楚，形象要在一眼之内认得出。这种「看得懂」的夸张，是为年节张贴的观看距离准备的。"),
        ],
        "explain": "朱仙镇木版年画以线版立形、多版套色，造型饱满、色彩浓烈，2006 年列入第一批国家级非物质文化遗产名录。",
    },
    "bianxiu": {
        "name": "汴绣",
        "accent": "#7B4B8A", "accentSoft": "#E7D3EA", "paper": "#F7F2F4",
        "ink": "#3A2A33", "gold": "#B08A5E",
        "sources": ["SRC-BX-KAIFENG-001"],
        "kicker": "针法特征",
        "chapters": [
            ("第一折 · 线", "一根线就是一笔", "刺绣没有填色这一步，同一片花瓣上不同深浅的丝线被并排放置，针脚方向随形体转折。"),
            ("第二折 · 色", "色阶不是调出来的", "想得到更深的红，就换一支更深的线；想让它变浅，就少叠一层。色是一支一支选出来的。"),
            ("第三折 · 名", "为什么叫宋绣", "汴绣也称宋绣，因产生于北宋都城汴京（开封）而得名，以针法细密、摹画入绣见长。"),
        ],
        "explain": "汴绣以针代笔、以线晕色，讲究针脚走向随形体转折；2008 年列入国家级非物质文化遗产名录。",
    },
    "songhua": {
        "name": "宋画青绿山水",
        "accent": "#2F6B5E", "accentSoft": "#CBDCC8", "paper": "#F4F1E6",
        "ink": "#2A3630", "gold": "#A8894F",
        "sources": ["SRC-SH-QINGLU-001"],
        "kicker": "设色层次",
        "chapters": [
            ("第一折 · 势", "先看山势", "青绿山水先立主峰与坡脚的关系：高处石骨用墨线勾出，再以石青石绿层层罩染，山体因此有厚度。"),
            ("第二折 · 色", "青绿从哪来", "石青、石绿是矿物色，覆盖力强、不易褪。它们在绢或纸上反复罩染，才会出现上重下轻的通透感。"),
            ("第三折 · 点", "楼与鹤：画面里最小的人", "楼台、舟桥、禽鸟都是点景，比例极小，却给山水定下尺度。"),
        ],
        "explain": "青绿山水以石青、石绿为主色，先墨骨后重彩，山体层层罩染，是宋画里最具装饰性的一路。",
    },
    "qinghua": {
        "name": "青花瓷纹样",
        "accent": "#22508F", "accentSoft": "#CBD9EC", "paper": "#F3F5F8",
        "ink": "#243040", "gold": "#9C8556",
        "sources": ["SRC-QH-JINGDEZHEN-001"],
        "kicker": "青料特征",
        "chapters": [
            ("第一折 · 料", "颜色被烧在釉下面", "先在素坯上用钴料描画，再罩透明釉入窑高温一次烧成，蓝色被封在釉层里。"),
            ("第二折 · 白", "白也是一种颜色", "青花靠留白成形：纹样之间留出的空白是釉本身的颜色，浓淡对比才让蓝色立起来。"),
            ("第三折 · 纹", "缠枝为什么绕", "缠枝纹以连续卷曲的枝条串起花叶，可以无始无终地铺满器身，适合转着看的圆器。"),
        ],
        "explain": "青花属釉下彩，以钴料在坯上绘纹、罩釉高温烧成；青花瓷是瓷器品种，本项目不将其表述为非物质文化遗产项目。",
    },
    "jianzhi": {
        "name": "中国剪纸",
        "accent": "#B03A2E", "accentSoft": "#F0CFC6", "paper": "#FBF3EF",
        "ink": "#3A2622", "gold": "#B98B4E",
        "sources": ["SRC-JZ-PAPER-001"],
        "kicker": "镂空语言",
        "chapters": [
            ("第一折 · 空", "留下的才是画", "剪纸靠剪掉的部分成形，图案之间的连接处是纸筋，也是构图必须留出的通道。"),
            ("第二折 · 折", "对称是折出来的", "把纸对折再剪，展开就得到镜像；对称不是画出来的，是折叠顺序带来的。"),
            ("第三折 · 意", "图必有意", "花、鸟、鱼、兽各有约定俗成的吉祥含义，剪纸把祝愿压缩成可张贴的形状。"),
        ],
        "explain": "剪纸以镂空成形、讲究纸筋相连；2006 年列入第一批国家级非物质文化遗产名录（Ⅶ-16），2009 年入选联合国教科文组织人类非遗代表作名录。",
    },
}


# --------------------------------------------------------------------------- #
# 小工具
# --------------------------------------------------------------------------- #
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9-]+", "-", text.strip().lower()).strip("-")
    return cleaned or f"case-{int(time.time())}"


def log(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------- #
# 深度（复用画境构建器的实现，保证两边口径一致）
# --------------------------------------------------------------------------- #
def load_depth_functions():
    sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "interactive"))
    import build_painting_world as bpw  # noqa: E402

    return bpw


def estimate_depth(image_path: Path, slug: str, gamma: float = 0.72):
    """优先用 Depth Anything V2；模型/权重不可用时退回可解释的近似深度。

    降级不是假数据：近似深度只由这张图自身的亮度、中心权重与垂直梯度构成，
    明确标记 depthSource=fallback_luminance，画境仍可打开但只提供有限视差。
    这样「深度模型缺失」不会让整条互动流水线失败。
    """
    global DEPTH_SOURCE
    cache = PROJECT_ROOT / "scripts" / "interactive" / "_probe" / f"{slug}-depth.npy"
    source_file = cache.with_name(cache.stem + "-source.txt")

    try:
        bpw = load_depth_functions()
        if cache.is_file() and source_file.is_file():
            DEPTH_SOURCE = source_file.read_text(encoding="utf-8-sig").strip() or "depth-anything-v2-small"
        else:
            DEPTH_SOURCE = "depth-anything-v2-small"
        raw = bpw.run_depth(str(image_path), "depth-anything/Depth-Anything-V2-Small-hf", str(cache), False)
        cache.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text(DEPTH_SOURCE, encoding="utf-8")
        depth = bpw.normalise_depth(raw, gamma)
        depth = bpw.smooth_depth(depth, 3.0)
        return depth
    except Exception as exc:  # noqa: BLE001 - 缺模型时必须还能产出降级体验
        log(f"    ! 深度模型不可用（{type(exc).__name__}: {str(exc)[:120]}），改用近似深度")
        DEPTH_SOURCE = "fallback_luminance"
        raw = fallback_depth(image_path)
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.save(cache, raw.astype(np.float32))
        source_file.write_text(DEPTH_SOURCE, encoding="utf-8")
        depth = _normalise_depth(raw, gamma)
        depth = _smooth_depth(depth, 3.0)
        return depth


DEPTH_SOURCE = "depth-anything-v2-small"


def fallback_depth(image_path: Path) -> np.ndarray:
    """模型不可用时的近似深度：亮度 + 中心权重 + 垂直梯度，只描述本图。"""
    with Image.open(image_path) as im:
        small = im.convert("RGB").resize((512, 512))
    arr = np.asarray(small, dtype=np.float32) / 255.0
    lum = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
    blur = Image.fromarray((lum * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(8))
    lum_blur = np.asarray(blur, dtype=np.float32) / 255.0

    h, w = lum.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    radial = np.clip(1.0 - np.sqrt(((xx - cx) / (w * 0.62)) ** 2 + ((yy - cy) / (h * 0.62)) ** 2), 0.0, 1.0)
    vertical = 1.0 - yy / max(h - 1, 1)

    depth = 0.55 * lum_blur + 0.30 * radial + 0.15 * vertical
    lo, hi = np.percentile(depth, [3, 97])
    return np.clip((depth - lo) / max(float(hi - lo), 1e-6), 0.0, 1.0).astype(np.float32)


def _normalise_depth(raw: np.ndarray, gamma: float) -> np.ndarray:
    lo, hi = np.percentile(raw, [2, 98])
    n = np.clip((raw - lo) / max(float(hi - lo), 1e-6), 0.0, 1.0)
    return np.power(n, gamma)


def _smooth_depth(depth: np.ndarray, radius: float = 3.0) -> np.ndarray:
    if radius <= 0:
        return depth
    img = Image.fromarray((np.clip(depth, 0.0, 1.0) * 255).astype(np.uint8))
    blur = img.filter(ImageFilter.GaussianBlur(radius))
    return np.asarray(blur, dtype=np.float32) / 255.0


def dominant_palette(image: Image.Image, k: int = 3) -> list[str]:
    """取画面的主色（十六进制）。

    schema 要求 `visualAnalysis.dominantColors` 至少一项，之前这里写的是空数组，
    结果是新案例一加载就校验失败、整个展厅白屏。用中位切分量化取前 k 个颜色，
    按占比排序，顺带把几乎相同的颜色合并掉。
    """
    small = image.convert("RGB")
    small.thumbnail((160, 160))
    quantized = small.quantize(colors=max(2, k), method=Image.MEDIANCUT)
    palette = quantized.getpalette() or []
    counts = sorted(quantized.getcolors() or [], key=lambda item: item[0], reverse=True)
    total = sum(count for count, _ in counts) or 1
    colors: list[str] = []
    for count, index in counts:
        rgb = tuple(palette[index * 3 : index * 3 + 3])
        if len(rgb) < 3:
            continue
        if count / total < 0.05:  # 零星像素不算主色
            continue
        hex_color = "#{:02x}{:02x}{:02x}".format(*rgb)
        if all(hex_color != existing for existing in colors):
            colors.append(hex_color)
        if len(colors) >= k:
            break
    return colors or ["#808080"]


# --------------------------------------------------------------------------- #
# 自动热点：画面「前、彩、密」三处得分高的地方
# --------------------------------------------------------------------------- #
def pick_hotspots(image: np.ndarray, depth: np.ndarray, count: int, min_dist: float = 0.17):
    """在粗网格上打分并做非极大值抑制，返回 [(x, y, score, radius)]。"""
    h, w = depth.shape
    grid = 48
    ys = np.linspace(0, h - 1, grid + 1).astype(int)
    xs = np.linspace(0, w - 1, grid + 1).astype(int)

    rgb = image.astype(np.float32) / 255.0
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    lum = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)

    def downsample(arr):
        out = np.zeros((grid, grid), dtype=np.float32)
        for i in range(grid):
            for j in range(grid):
                patch = arr[ys[i] : ys[i + 1] or ys[i] + 1, xs[j] : xs[j + 1] or xs[j] + 1]
                out[i, j] = float(np.mean(patch)) if patch.size else 0.0
        return out

    d = downsample(depth)
    s = downsample(sat)
    l = downsample(lum)

    def z(arr):
        return (arr - arr.mean()) / (arr.std() + 1e-6)

    # 近景（depth 大）与彩色密集处更容易成为「可点的地方」；
    # 亮度只用来避开大片空白纸底。
    score = 0.55 * z(d) + 0.30 * z(s) + 0.15 * z(np.abs(l - np.median(l)))
    # 边框 6% 内不选：那里通常只是画边，点了没有内容
    margin = int(grid * 0.06)
    score[:margin, :] = -9
    score[-margin:, :] = -9
    score[:, :margin] = -9
    score[:, -margin:] = -9

    picks = []
    work = score.copy()
    # 深度分带：只按得分取点会全部落在最近的前景（实测 5 个点全在 0.68–0.81，
    # 于是「点哪儿都贴到脸上」）。强制先各取一个远景 / 中景点，剩下的再按分数补，
    # 这样一次漫游里既有远处可点的空景，也有近处可推的细节。
    bands = [(0.0, 0.42), (0.42, 0.66), (0.66, 1.01)]
    for lo, hi in bands:
        mask = (d >= lo) & (d < hi) & (work > -5)
        if mask.any():
            work[~mask] = -9
            flat = int(np.argmax(work))
            i, j = divmod(flat, grid)
            picks.append({
                "x": round(float((xs[j] + xs[min(j + 1, grid)]) / 2 / w), 4),
                "y": round(float((ys[i] + ys[min(i + 1, grid)]) / 2 / h), 4),
                "score": round(float(score[i, j]), 3), "r": 0.09,
            })
        work = score.copy()
        for pick in picks:
            for ii in range(grid):
                for jj in range(grid):
                    gy = (ys[ii] + ys[min(ii + 1, grid)]) / 2 / h
                    gx = (xs[jj] + xs[min(jj + 1, grid)]) / 2 / w
                    if math.hypot(gx - pick["x"], gy - pick["y"]) < min_dist:
                        work[ii, jj] = -9

    while len(picks) < count:
        flat = int(np.argmax(work))
        i, j = divmod(flat, grid)
        if work[i, j] < -5:
            break
        cx = (xs[j] + xs[min(j + 1, grid)]) / 2 / w
        cy = (ys[i] + ys[min(i + 1, grid)]) / 2 / h
        picks.append({"x": round(float(cx), 4), "y": round(float(cy), 4),
                      "score": round(float(work[i, j]), 3), "r": 0.09})
        # 抑制邻域
        for ii in range(grid):
            for jj in range(grid):
                gy = (ys[ii] + ys[min(ii + 1, grid)]) / 2 / h
                gx = (xs[jj] + xs[min(jj + 1, grid)]) / 2 / w
                if math.hypot(gx - cx, gy - cy) < min_dist:
                    work[ii, jj] = -9
    return picks


def vlm_label(image: Image.Image, box: tuple[int, int, int, int], style_name: str,
              vocab: list[str]) -> str:
    """让本地 Qwen3-VL 看这一小块，从给定词表里挑一个词。失败返回空串。"""
    import base64
    import urllib.request

    crop = image.crop(box).convert("RGB")
    crop.thumbnail((512, 512))
    from io import BytesIO

    raw = BytesIO()
    crop.save(raw, format="JPEG", quality=88)
    b64 = base64.b64encode(raw.getvalue()).decode()

    # 给词表而不是开放提问：4b 模型开放提问时会编出画面里没有的东西
    # （实测把青花的一个局部说成「云海波涛」）。词表之外一律回退成方位描述。
    prompt = (
        f"这是{style_name}画面里的一个局部。请从下面这些词里挑一个最接近的，只输出这个词本身：\n"
        + "、".join(vocab)
        + "\n如果都不接近，只输出：不确定"
    )
    payload = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "images": [b64],
                          "stream": False, "options": {"temperature": 0, "num_predict": 12}}).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=payload,
                                headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            text = json.loads(resp.read().decode())["response"].strip()
    except Exception as exc:  # 本地模型没起、超时、显存不够都走到这里
        log(f"  vlm: 跳过（{type(exc).__name__}）")
        return ""
    return text[:24]


def position_word(x: float, y: float) -> str:
    horiz = "左" if x < 0.38 else ("右" if x > 0.62 else "中")
    vert = "上" if y < 0.38 else ("下" if y > 0.62 else "中")
    if vert == "中":
        return "画面中央" if horiz == "中" else f"画面{horiz}侧"
    if horiz == "中":
        return f"画面{vert}方"
    return f"画面{vert}{horiz}"


def resolve_titles(style_id: str, spots: list[dict], raw_labels: list[str]) -> list[str]:
    """把模型输出收敛成「方位 + 画里确实有的东西」的短语，并保证互不重复。"""
    vocab = VOCAB.get(style_id, [])
    used: set[str] = set()
    titles: list[str] = []
    for idx, spot in enumerate(spots):
        raw = raw_labels[idx] if idx < len(raw_labels) else ""
        hit = ""
        for word in vocab:
            if word and (word in raw or (raw and raw in word)):
                hit = word
                break
        pos = position_word(spot["x"], spot["y"])
        title = f"{pos}的{hit}" if hit else f"{pos}局部"
        suffix = 2
        base = title
        while title in used:
            title = f"{base}·{suffix}"
            suffix += 1
        used.add(title)
        titles.append(title)
    return titles


# --------------------------------------------------------------------------- #
# 命名词表：只允许从画里真实存在的元素里选，避免 4b 模型编出画面没有的东西
# --------------------------------------------------------------------------- #
VOCAB: dict[str, list[str]] = {
    "zhuxianzhen": ["猫脸", "猫耳", "猫须", "虎斑", "牡丹花", "花瓣", "叶片", "海水纹", "云纹", "题字"],
    "bianxiu": ["兔头", "兔耳", "兔身", "绣线", "牡丹花", "花瓣", "叶片", "枝干", "底料"],
    "songhua": ["主峰", "远山", "云气", "楼阁", "仙鹤", "松枝", "坡石", "水面"],
    "qinghua": ["蝶翼", "蝶身", "蝶须", "缠枝", "花瓣", "叶片", "器口", "弦纹"],
    "jianzhi": ["狐头", "狐耳", "狐身", "尾巴", "花朵", "花瓣", "枝叶", "月牙镂空"],
}

# --------------------------------------------------------------------------- #
# 生成 experience.json
# --------------------------------------------------------------------------- #
def build_experience(*, slug: str, title: str, style_id: str, image: Image.Image,
                     hotspots_raw: list[dict], titles: list[str], raw_labels: list[str],
                     vlm_used: bool, subjects: list[str] | None = None) -> dict:
    style = STYLES[style_id]
    w, h = image.size
    known_subjects = [str(item).strip() for item in (subjects or []) if str(item).strip()]
    subject_text = "、".join(known_subjects[:3])

    kinds = ["主体", "纹样", "局部"]
    hotspots = []
    for idx, spot in enumerate(hotspots_raw):
        label = titles[idx]
        hx, hy, r = spot["x"], spot["y"], spot["r"]
        hotspots.append({
            "id": f"auto-{idx + 1}",
            "title": label,
            "kicker": style["kicker"],
            "shape": "circle",
            "geometry": {"cx": hx, "cy": hy, "r": r},
            "shortDescription": f"{label}：这一处在画面里的位置与前后关系。",
            "visualObservation": f"{label}，位于画面横向 {hx:.0%}、纵向 {hy:.0%} 附近，"
                                 f"周围有{'较强的明暗对比' if spot['score'] > 0 else '较弱的明暗起伏'}。",
            "culturalExplanation": f"{style['explain']}这一处是该风格里常见的观察点，"
                                   f"它承担说明{kinds[idx % len(kinds)]}的角色。",
            "sourceIds": style["sources"],
            "locationStatus": "approximate",
            "reviewStatus": "pending",
            "relatedChapterId": f"fold-{min(3, idx // 2 + 1)}",
        })

    chapters = []
    for ci, (eyebrow, ctitle, body) in enumerate(style["chapters"], start=1):
        group = [s for s in hotspots if s["relatedChapterId"] == f"fold-{ci}"] or hotspots[:1]
        if not group:
            group = hotspots[:1]
        cx = float(np.mean([s["geometry"]["cx"] for s in group]))
        cy = float(np.mean([s["geometry"]["cy"] for s in group]))
        # 镜头放大倍数：焦点越靠边，放大后越容易露出画外，收着用
        edge = max(abs(cx - 0.5), abs(cy - 0.5))
        scale = float(np.clip(1.85 - 0.8 * edge * 2, 1.15, 1.85))
        # 第一折把「这张画自己可见的主体」带进叙事，而不是只讲通用风格知识。
        body_text = body
        if ci == 1 and subject_text:
            body_text = (
                f"{body} 回到《{title}》这张画：画面可见{subject_text}，"
                f"可先看它们与背景的明暗和前后关系，再读画法。"
            )
        chapters.append({
            "id": f"fold-{ci}",
            "index": ci,
            "eyebrow": eyebrow,
            "title": ctitle,
            "body": body_text,
            "focusHotspotIds": [s["id"] for s in group],
            "frame": {"scale": round(scale, 2), "focusX": round(cx, 4), "focusY": round(cy, 4)},
            "sourceIds": style["sources"],
        })

    return {
        "id": slug,
        "styleId": style_id,
        "styleName": style["name"],
        "title": title,
        "subtitle": "自动生成的三重互动",
        "lead": (
            f"这一张《{title}》是用{style['name']}的视觉语言生成的。"
            + (f"画面可见{subject_text}。" if subject_text else "")
            + "下面三折讲的是这套画法的读法，热点位置由画面自动估计。"
        ),
        "artworkSize": {"width": w, "height": h},
        "theme": {"accent": style["accent"], "accentSoft": style["accentSoft"],
                  "paper": style["paper"], "ink": style["ink"], "gold": style["gold"]},
        "visualAnalysis": {
            "source": "auto_ingest",
            "model": OLLAMA_MODEL if vlm_used else "",
            "observedSubjects": known_subjects[:6] or [t for t in titles if t][:6] or [title],
            "visualFeatures": [h["title"] for h in hotspots][:6],
            "dominantColors": dominant_palette(image),
        },
        "hotspots": hotspots,
        "chapters": chapters,
        "animation": {
            "mode": "world",
            "world": {"url": f"interactive/{slug}/world/world.json",
                      "depthNote": "单图深度估计（Depth Anything V2 Small）驱动的 2.5D 深度网格"},
            "capabilityNote": "画境由这张图做单目深度估计后生成深度网格：可以推近、小幅转头、"
                              "在前后有限范围里移动；深度是模型对画面前后关系的估计，"
                              "不能绕到主体背后，也不是三维重建。低性能设备会自动降级为静止画面。",
            "layerSource": "Depth Anything V2 Small（单目深度估计）+ 逐像素深度网格；"
                           "遮罩按明暗与色彩密度划分水面 / 云雾 / 植被三类微动区域。",
        },
        "provenance": {
            "sourceCaseId": slug,
            "knowledgeVersion": "1.0.0",
            "authoredAt": datetime.now().strftime("%Y-%m-%d"),
            "hotspotMethod": "深度显著性 + 色彩密度自动打分，非极大值抑制选点；"
                             + ("热点名称由本地 Qwen3-VL 判读；" if vlm_used else "")
                             + "坐标未经逐点裁切复核，标记为 approximate。",
            "designNote": "由 scripts/interactive/ingest_case.py 自动生成；"
                          "文化解读沿用该风格知识包与来源编号，未凭空生成文化事实。",
        },
    }


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def ingest(args) -> int:
    started = time.time()
    t0 = time.time()

    if args.refresh:
        folder = EXAMPLES_DIR / args.refresh
        if not folder.is_dir():
            log(f"✖ 找不到案例目录 {folder}")
            return 2
        slug = folder.name
        meta_path = folder / "metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8-sig")) if meta_path.exists() else {}
        style_id = str(args.style_id or meta.get("styleId") or "zhuxianzhen")
        title = str(args.title or meta.get("artworkTitle") or slug)
        image_path = folder / "generated.png"
        if not image_path.is_file():
            log(f"✖ {folder} 里没有 generated.png")
            return 2
    else:
        if not args.image:
            log("✖ 需要 --image 或 --refresh")
            return 2
        src = Path(args.image).expanduser().resolve()
        if not src.is_file():
            log(f"✖ 图片不存在：{src}")
            return 2
        style_id = str(args.style_id or "")
        if style_id not in STYLES:
            log(f"✖ --style-id 必须是 {', '.join(STYLES)} 之一")
            return 2
        slug = slugify(args.slug or src.stem)
        folder = EXAMPLES_DIR / slug
        if folder.exists() and not args.force:
            log(f"✖ 案例已存在：{folder}（加 --force 覆盖）")
            return 2
        folder.mkdir(parents=True, exist_ok=True)
        image_path = folder / "generated.png"
        with Image.open(src) as im:
            im.convert("RGB").save(image_path, format="PNG", optimize=True)
        title = str(args.title or slug)
        meta = {}
        log(f"1/6 落盘 {image_path.relative_to(PROJECT_ROOT)}  {image_path.stat().st_size / 1024:.0f} KB")

    with Image.open(image_path) as im:
        image = im.convert("RGB")
    W, H = image.size
    arr = np.asarray(image)
    log(f"    尺寸 {W}x{H}  风格 {style_id} / {STYLES[style_id]['name']}")

    # 2) 深度
    depth = estimate_depth(image_path, slug, args.gamma)
    log(f"2/6 深度完成（{DEPTH_SOURCE}）  近景占比 {(depth > 0.8).mean() * 100:.1f}%  远景占比 {(depth < 0.35).mean() * 100:.1f}%")

    # 3) 热点候选 + 命名
    spots = pick_hotspots(arr, depth, args.hotspots)
    if not spots:
        log("✖ 没选出任何热点，画面可能过于均匀")
        return 3
    labels: list[str] = []
    vlm_used = False
    if not args.no_vlm:
        for spot in spots:
            r_px = spot["r"] * min(W, H)
            cx, cy = spot["x"] * W, spot["y"] * H
            box = (int(max(0, cx - r_px)), int(max(0, cy - r_px)),
                   int(min(W, cx + r_px)), int(min(H, cy + r_px)))
            labels.append(vlm_label(image, box, STYLES[style_id]["name"], VOCAB.get(style_id, [])))
            vlm_used = vlm_used or bool(labels[-1])
    labels += [""] * (len(spots) - len(labels))
    titles = resolve_titles(style_id, spots, labels)
    # 本作品生成时由 Qwen3-VL 得到的画面主体（属于这张图自己的元数据），
    # 用来让叙事对得上这张图；没有就退化为通用占位，不跨作品借用。
    meta_subjects = [
        str(item).strip()
        for item in (((meta.get("visionAnalysis") or {}).get("observed_subjects")) or [])
        if str(item).strip()
    ][:6]
    log("3/6 热点 " + ", ".join(
        f"({s['x']:.2f},{s['y']:.2f})→{t}" for s, t in zip(spots, titles)))

    # 4) experience.json
    draft = build_experience(slug=slug, title=title, style_id=style_id, image=image,
                             hotspots_raw=spots, titles=titles, raw_labels=labels,
                             vlm_used=vlm_used, subjects=meta_subjects)
    if DEPTH_SOURCE != "depth-anything-v2-small":
        # 降级必须对用户可见：仍然能打开画境，但明确说明只有近似深度。
        draft["animation"]["world"]["depthNote"] = (
            "单图近似深度（本机深度模型不可用时的降级），仅支持有限视差；"
            "不是三维重建，可稍后重新构建以获得更准确的画境。"
        )
    exp_path = folder / "experience.json"
    exp_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"4/6 experience.json  {exp_path.stat().st_size / 1024:.1f} KB  "
        f"{len(draft['hotspots'])} 热点 / {len(draft['chapters'])} 折")

    # 5) 画境资产
    world_ok = False
    if not args.skip_world:
        cfg = {
            "slug": slug,
            "title": title,
            "styleName": STYLES[style_id]["name"],
            "source": str(image_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "hotspots": [{"id": h["id"], "label": h["title"],
                          "x": h["geometry"]["cx"], "y": h["geometry"]["cy"],
                          "w": 0, "h": 0, "r": h["geometry"]["r"]} for h in draft["hotspots"]],
            "cutouts": [{
                "id": "subject", "label": draft["hotspots"][0]["title"], "depth_min": 0.58,
                "seed": {"x": draft["hotspots"][0]["geometry"]["cx"],
                         "y": draft["hotspots"][0]["geometry"]["cy"]},
                "half": {"w": 0.2, "h": 0.2},
            }],
        }
        cfg_path = PROJECT_ROOT / "scripts" / "interactive" / "_probe" / f"{slug}-config.json"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        cmd = [sys.executable, "-X", "utf8", str(BUILDER), "--config", str(cfg_path)]
        log("5/6 生成画境资产 …")
        proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding="utf-8")
        tail = (proc.stdout or "").strip().splitlines()
        for line in tail[-6:]:
            log("    " + line)
        if proc.returncode != 0:
            log("    ✖ 画境构建失败：\n" + (proc.stderr or "")[-800:])
        else:
            world_ok = (PUBLIC_WORLD / slug / "world" / "world.json").is_file()

    # 6) 回写 metadata
    meta.update({
        "caseId": slug,
        "caseOrigin": "runtime",
        "experienceId": slug,
        "styleId": style_id,
        "styleName": STYLES[style_id]["name"],
        "artworkTitle": title,
        "generatedAt": meta.get("generatedAt") or datetime.now().astimezone().isoformat(),
        "generatedSha256": sha256(image_path),
        "generatedBytes": image_path.stat().st_size,
        "artworkSize": {"width": W, "height": H},
        "interactive": {
            "status": "ready" if world_ok else "partial",
            "experience": "experience.json",
            "world": f"frontend/public/interactive/{slug}/world/world.json" if world_ok else "",
            "hotspots": len(draft["hotspots"]),
            "hotspotMethod": "auto-approximate",
            "depthSource": DEPTH_SOURCE,
            "builtAt": datetime.now().astimezone().isoformat(),
        },
    })
    (folder / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    world_dir = PUBLIC_WORLD / slug / "world"
    files = sorted(p.name for p in world_dir.glob("*")) if world_dir.is_dir() else []
    report = {
        "slug": slug,
        "styleId": style_id,
        "title": title,
        "image": {"width": W, "height": H, "bytes": image_path.stat().st_size},
        "depth": {
            "source": DEPTH_SOURCE,
            "nearShare": round(float((depth > 0.8).mean()), 4),
            "farShare": round(float((depth < 0.35).mean()), 4),
            "percentiles": [round(float(v), 4) for v in np.percentile(depth, [2, 10, 50, 90, 98])],
            "gamma": args.gamma,
        },
        "hotspots": [{"id": h["id"], "title": h["title"], "x": h["geometry"]["cx"],
                      "y": h["geometry"]["cy"], "status": h["locationStatus"]} for h in draft["hotspots"]],
        "chapters": [{"id": c["id"], "scale": c["frame"]["scale"]} for c in draft["chapters"]],
        "world": {"built": world_ok, "files": files,
                  "bytes": sum((world_dir / f).stat().st_size for f in files) if files else 0},
        "vlm": {"used": vlm_used, "model": OLLAMA_MODEL if vlm_used else ""},
        "warnings": ([w for w in [
            "热点为自动估计，未逐点裁切复核，请人工确认后再对外展示。",
            "热点名称由 4b 视觉模型判读，可能有偏差。" if vlm_used else "未使用视觉模型，热点标题为占位名。",
            "本机深度模型不可用，画境使用近似深度，只提供有限视差。" if DEPTH_SOURCE.startswith("fallback") else "",
        ] if w]),
        "elapsedSec": round(time.time() - started, 1),
    }
    (folder / "ingest-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    log(f"6/6 完成  {slug}  用时 {report['elapsedSec']}s")
    log(f"    三入口：/experience/{slug} · /story/{slug} · /wander/{slug}")
    for warn in report["warnings"]:
        log("    ! " + warn)
    if not world_ok and not args.skip_world:
        log("    ✖ 画境资产未生成，画境漫游入口不会出现（本次按失败返回）")
        return 4
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="把新生成的图变成带三重互动的真实案例")
    ap.add_argument("--image", help="新生成的图片路径")
    ap.add_argument("--slug", help="案例目录名（默认取文件名）")
    ap.add_argument("--title", help="作品标题")
    ap.add_argument("--style-id", choices=sorted(STYLES), help="风格（决定文案口径与来源编号）")
    ap.add_argument("--hotspots", type=int, default=5, help="自动热点数量（4–6）")
    ap.add_argument("--gamma", type=float, default=0.72)
    ap.add_argument("--no-vlm", action="store_true", help="不调用本地视觉模型命名热点")
    ap.add_argument("--skip-world", action="store_true", help="只生成 experience.json，不建画境资产")
    ap.add_argument("--refresh", help="对已有案例目录重新生成互动内容")
    ap.add_argument("--force", action="store_true", help="覆盖已有案例目录")
    args = ap.parse_args()
    args.hotspots = int(np.clip(args.hotspots, 4, 6))
    return ingest(args)


if __name__ == "__main__":
    raise SystemExit(main())