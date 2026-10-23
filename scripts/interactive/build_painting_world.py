"""把一张平面画作加工成「画境」可用的深度资产。

产物（写到 frontend/public/interactive/<slug>/world/）：
  art.webp            画作本体（网格贴图）
  depth-rg.png        16 位深度，打包进 R(高字节) G(低字节)，着色器里还原
  backdrop.webp       边缘外推 + 模糊的兜底背景（挡住网格之外的区域）
  masks.png           RGB 三通道遮罩：R=水面 G=云雾 B=近景植被
  cutout-*.webp       近景抠像（带 alpha），入画时从镜头两侧掠过
  depth-preview.png   伪彩预览，只用于人工/模型复核，不参与渲染
  world.json          前端要用的配置与热点深度

用法（都从项目根运行）：
  python scripts/interactive/build_painting_world.py                  # 默认 songhua
  python scripts/interactive/build_painting_world.py --style bianxiu  # 单件
  python scripts/interactive/build_painting_world.py --all            # 全部配置
  python scripts/interactive/build_painting_world.py --config path/to/art.json
  python scripts/interactive/build_painting_world.py --style qinghua --force-depth

作品参数不再写在 Python 里，唯一事实来源是 scripts/interactive/artworks/<slug>.json
（由 scripts/interactive/export_artwork_configs.mjs 从 frontend/src/data/experiences/*.ts
导出）。配置里的坐标口径与 TS 一致：
  * 矩形热点：x/y 是矩形中心，w/h 是宽高（不是左上角）；
  * 圆形热点：w==0，x/y 是圆心，r 是半径（配置缺 r 时才用 0.05）；
  * 可选 hotspot_depth_overrides: {"crane": 0.42}，按 id 覆盖该热点的最终深度。

设计约束（写进产物与报告，不许含糊）：
  单图深度只能支撑「有限视角」——本管线给的是 2.5D 深度网格，
  不是三维重建；镜头左右 ±18°、上下 ±12°、前后有限推进，不能绕到物体背后。
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import time

import numpy as np
import torch
from PIL import Image, ImageFilter

CONFIG_DIR = os.path.join("scripts", "interactive", "artworks")
PROBE_DIR = os.path.join("scripts", "interactive", "_probe")
DEFAULT_REPORT = os.path.join(PROBE_DIR, "world-build-report.json")
DEFAULT_STYLE = "songhua"   # 什么都没给时的默认作品

DEPTH_REPO = "depth-anything/Depth-Anything-V2-Small-hf"

DEPTH_TEX_W = 768          # 深度贴图宽度（着色器里线性采样，够用）
MASK_TEX_W = 768

DEFAULT_HOTSPOT_R = 0.05   # 圆形热点未给 r 时的窗口半径（老实现里写死的值）
DEPTH_CLAMP = (0.14, 0.88)  # 热点深度的统一夹取区间

# 画境清单里各部件的目标覆盖率：低分辩排名用，最终 >0.5 的可动面积约为
# water 13% / mist 9% / 植被 30%
DEFAULT_MASK_TARGETS = {"water": 0.11, "mist": 0.09, "foliage": 0.24}

REQUIRED_FILES = ("art.webp", "depth-rg.png", "masks.png", "backdrop.webp", "world.json")


# --------------------------------------------------------------------------- #
# 配置
# --------------------------------------------------------------------------- #
def artwork_config_path(slug: str) -> str:
    return os.path.join(CONFIG_DIR, f"{slug}.json")


def known_slugs() -> list[str]:
    return sorted(
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(os.path.join(CONFIG_DIR, "*.json"))
    )


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    cfg["_config_path"] = path
    return cfg


def normalise_config(cfg: dict) -> dict:
    """把配置整理成构建器内部用的形状，同时做最必要的校验。

    坐标口径（与 export_artwork_configs.mjs 导出的口径一致）：
      * w>0：矩形，(x, y) 是矩形中心，w/h 是宽高；
      * w==0：圆形，(x, y) 是圆心，r 是半径，缺省 0.05。
    cutout 既接受配置里的 seed/half 嵌套写法，也接受 seed_x/half_w 平铺写法。
    """
    path = cfg.get("_config_path", "<inline>")
    for key in ("slug", "title", "source", "hotspots"):
        if key not in cfg:
            raise SystemExit(f"配置缺少必填字段 {key}: {path}")
    if not cfg["hotspots"]:
        raise SystemExit(f"配置里没有任何热点: {path}")

    hotspots = []
    for sp in cfg["hotspots"]:
        if "id" not in sp:
            raise SystemExit(f"热点缺少 id: {path}")
        w = float(sp.get("w") or 0.0)
        h = float(sp.get("h") or 0.0)
        r = sp.get("r")
        if w > 0:
            r_val = 0.0
        else:
            r_val = DEFAULT_HOTSPOT_R if r in (None, 0, 0.0) else float(r)
        hotspots.append({
            "id": sp["id"],
            "label": sp.get("label", sp["id"]),
            "x": float(sp["x"]),
            "y": float(sp["y"]),
            "w": w,
            "h": h,
            "r": r_val,
        })

    overrides_raw = cfg.get("hotspot_depth_overrides") or {}
    if not isinstance(overrides_raw, dict):
        raise SystemExit(f"hotspot_depth_overrides 必须是对象: {path}")
    ids = {sp["id"] for sp in hotspots}
    unknown = [k for k in overrides_raw if k not in ids]
    if unknown:
        print(f"config: hotspot_depth_overrides 里这些 id 没有对应热点，将忽略 {unknown}")

    cutouts = []
    for spec in cfg.get("cutouts") or []:
        seed = spec.get("seed") or {}
        half = spec.get("half") or {}
        cutouts.append({
            "id": spec["id"],
            "label": spec.get("label", spec["id"]),
            "depth_min": float(spec.get("depth_min", 0.6)),
            "seed_x": float(seed.get("x", spec.get("seed_x"))),
            "seed_y": float(seed.get("y", spec.get("seed_y"))),
            "half_w": float(half.get("w", spec.get("half_w", 0.2))),
            "half_h": float(half.get("h", spec.get("half_h", 0.24))),
        })

    targets = dict(DEFAULT_MASK_TARGETS)
    if cfg.get("mask_targets"):
        targets.update({k: float(v) for k, v in cfg["mask_targets"].items()})

    return {
        "config_path": path,
        "slug": cfg["slug"],
        "title": cfg["title"],
        "style_name": cfg.get("styleName", ""),
        "source": cfg["source"],
        "hotspots": hotspots,
        "hotspot_depth_overrides": {k: float(v) for k, v in overrides_raw.items()},
        "cutouts": cutouts,
        "mask_targets": targets,
        "gamma": cfg.get("gamma"),
        "depth_smooth": cfg.get("depth_smooth"),
        "depth_repo": cfg.get("depth_repo") or DEPTH_REPO,
    }


def select_configs(args) -> list[dict]:
    """决定这次要构建什么，优先级：--config > --all > --style > 默认 songhua。

    注意 --style 的 argparse 默认值是 None 而不是 "songhua"：若默认成 "songhua"，
    `--config x.json` 也会被当成「同时给了 --style」而误报冲突（流水线踩过）。
    """
    if args.config and (args.all or args.style):
        raise SystemExit("--config 不能与 --style/--all 同时使用")
    if args.config:
        return [load_config(args.config)]
    if args.all:
        slugs = known_slugs()
        if not slugs:
            raise SystemExit(f"{CONFIG_DIR} 下没有找到任何配置")
        return [load_config(artwork_config_path(s)) for s in slugs]
    slug = args.style or DEFAULT_STYLE
    path = artwork_config_path(slug)
    if not os.path.exists(path):
        raise SystemExit(f"找不到配置 {path}（可用：{', '.join(known_slugs())}）")
    return [load_config(path)]


# --------------------------------------------------------------------------- #
# 深度
# --------------------------------------------------------------------------- #
def run_depth(art_path: str, repo: str, cache: str, force: bool) -> np.ndarray:
    """返回原始深度（float32, 全图分辨率, 值越大越近）。"""
    if os.path.exists(cache) and not force:
        print(f"depth: 复用缓存 {cache}")
        return np.load(cache).astype(np.float32)

    from transformers import AutoImageProcessor, DepthAnythingForDepthEstimation

    device = "cuda" if torch.cuda.is_available() else "cpu"
    img = Image.open(art_path).convert("RGB")
    t0 = time.time()
    processor = AutoImageProcessor.from_pretrained(repo)
    model = DepthAnythingForDepthEstimation.from_pretrained(repo).to(device).eval()
    print(f"depth: model ready in {time.time() - t0:.1f}s on {device}")

    inputs = processor(images=img, return_tensors="pt").to(device)
    with torch.inference_mode():
        outputs = model(**inputs)
    depth = processor.post_process_depth_estimation(
        outputs, target_sizes=[(img.height, img.width)]
    )[0]["predicted_depth"].detach().float().cpu().numpy()

    os.makedirs(os.path.dirname(cache), exist_ok=True)
    np.save(cache, depth.astype(np.float32))
    print(f"depth: {depth.shape} in {time.time() - t0:.1f}s")
    return depth.astype(np.float32)


def normalise_depth(raw: np.ndarray, gamma: float = 0.72) -> np.ndarray:
    """裁剪百分位 -> 0..1（1=最近），再用 gamma 把中景拉开。

    为什么需要 gamma：青绿山水 71% 的像素落在远景，直接线性映射会让中景
    （楼阁、山腰）几乎不动，画面看起来仍是「放大一张图」。gamma<1 抬高
    中远景，让中景也有可见的相对位移。
    """
    lo, hi = np.percentile(raw, [2, 98])
    n = np.clip((raw - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    return np.power(n, gamma)


def smooth_depth(depth: np.ndarray, radius: float) -> np.ndarray:
    """对深度做一次轻微高斯平滑（半径以原图像素计）。

    不平滑时深度边界是硬阶跃，网格在那里立起近乎垂直的「墙」，
    斜看会被拉成长条；平滑后落差摊开，位移连贯，也不改变远近次序。
    """
    if radius <= 0:
        return depth
    # PIL 的 GaussianBlur 不支持 F 模式，这里自己做可分离高斯卷积
    r = int(max(1, round(radius)))
    sigma = max(radius / 2.0, 0.6)
    x = np.arange(-r, r + 1, dtype=np.float32)
    w = np.exp(-(x ** 2) / (2 * sigma * sigma))
    w /= w.sum()
    a = depth.astype(np.float32)
    p = np.pad(a, ((0, 0), (r, r)), mode="edge")
    a = sum(w[i] * p[:, i:i + a.shape[1]] for i in range(2 * r + 1))
    p = np.pad(a, ((r, r), (0, 0)), mode="edge")
    a = sum(w[i] * p[i:i + a.shape[0], :] for i in range(2 * r + 1))
    return np.clip(a, 0.0, 1.0)


def pack_depth_rg(depth: np.ndarray, out: str, width: int) -> np.ndarray:
    """16 位深度打进 RG 两通道（PNG 是 8 位/channel，别无选择）。"""
    h = round(depth.shape[0] * width / depth.shape[1])
    small = np.asarray(
        Image.fromarray((depth * 65535).astype(np.uint16).astype(np.float32), mode="F")
        .resize((width, h), Image.BICUBIC),
        dtype=np.float32,
    )
    v = np.clip(small / 65535.0, 0, 1)
    q = np.round(v * 65535).astype(np.uint16)
    rg = np.stack([(q >> 8).astype(np.uint8), (q & 0xFF).astype(np.uint8),
                   np.zeros_like(q, dtype=np.uint8)], axis=-1)
    Image.fromarray(rg, mode="RGB").save(out, optimize=True)
    err = np.abs((rg[..., 0].astype(np.int32) << 8 | rg[..., 1]) / 65535.0 - v)
    print(f"depth-rg: {width}x{h}  quantise err max={err.max():.5f} mean={err.mean():.6f}")
    return v


def turbo(t: np.ndarray) -> np.ndarray:
    """不依赖 matplotlib 的turbo近似，只用于出预览图。"""
    stops = np.array([
        [0.19, 0.07, 0.23], [0.10, 0.50, 0.72], [0.13, 0.79, 0.58],
        [0.63, 0.87, 0.20], [0.98, 0.66, 0.10], [0.79, 0.21, 0.06],
    ], dtype=np.float32)
    pos = np.linspace(0, 1, len(stops))
    flat = t.reshape(-1)
    rgb = np.stack([np.interp(flat, pos, stops[:, c]) for c in range(3)], axis=-1)
    return (rgb.reshape(t.shape + (3,)) * 255).astype(np.uint8)


# --------------------------------------------------------------------------- #
# 边缘外推 + 遮罩
# --------------------------------------------------------------------------- #
def edge_extend(img: np.ndarray, passes: int = 6, ring: int = 4) -> np.ndarray:
    """兜底背景：画面本身轻微外推 + 中等模糊。

    第一版用了 26 轮大半径扩散，结果整张图被抹成一块纯色（产物只有 8 KB），
    已经看不出是同一幅画。改成少轮次小半径：保留纸张与设色的走向，
    只把边缘「续」出去一点，模糊到不会和主网格抢细节。
    """
    out = img.astype(np.float32).copy()
    for _ in range(passes):
        padded = np.pad(out, ((ring, ring), (ring, ring), (0, 0)), mode="edge")
        # 4 邻域均值 + 自身加权：边缘信息缓慢向内/外扩散
        blur = (
            padded[:-2 * ring, ring:-ring] + padded[2 * ring:, ring:-ring]
            + padded[ring:-ring, :-2 * ring] + padded[ring:-ring, 2 * ring:]
            + padded[ring:-ring, ring:-ring] * 4.0
        ) / 8.0
        out = out * 0.72 + blur * 0.28
    out = np.asarray(
        Image.fromarray(out.clip(0, 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(radius=5)
        )
    )
    # 轻微去饱和 + 抬亮：让它在网格后面读作「更远的一层」，而不是另一张画
    gray = out.mean(axis=-1, keepdims=True)
    out = out * 0.82 + gray * 0.18
    return np.clip(out * 0.90 + 20.0, 0, 255).astype(np.uint8)


def _rank_mask(score: np.ndarray, coverage: float, feather: float = 0.5) -> np.ndarray:
    """按名次分配权重：最高的 k 个像素为 1，再往下按名次线性衰减到 0。

    为什么不按分数阈值做软边：分数常常在大片区域饱和（云雾这一路在「偏远 + 亮 +
    低饱和」的区域会整片顶到 1.0），任何「阈值 × 系数」的软边都会把整片饱和区
    一起拉进来，覆盖率与目标值脱钩（实测目标 5.5% 出来 22%）。
    按名次分配则只依赖排序：覆盖率 = k / n，与分数分布无关。
    """
    s = score.astype(np.float32)
    if not np.any(s > 0):
        return np.zeros_like(s)
    n = s.size
    k = max(1, int(round(n * coverage)))
    # 并列拆分：加一个按像素序号的极小扰动，避免 argsort 把同分像素随意排序
    s_ord = s.astype(np.float64) + np.arange(n, dtype=np.float64).reshape(s.shape) * (1e-9 / n)
    flat = s_ord.ravel()
    order = np.argsort(-flat, kind="stable")
    rank = np.empty(n, dtype=np.float32)
    rank[order] = np.arange(n, dtype=np.float32)

    k_edge = k * (1.0 + feather)
    margin = max(k_edge - k, 1.0)
    m = np.clip((k_edge - rank) / margin, 0.0, 1.0).reshape(s.shape)
    m[s <= 0] = 0.0
    return (m * m * (3.0 - 2.0 * m)).astype(np.float32)


def build_masks(
    img: np.ndarray,
    depth: np.ndarray,
    width: int,
    targets: dict | None = None,
) -> tuple[np.ndarray, dict]:
    """R=水面 G=云雾 B=近景植被。全部羽化，不要在着色器里出现硬边。

    做法：先在低分辨率网格上算「像不像」的连续分数，再按目标覆盖率取前若干比例，
    然后双三次上采样到贴图尺寸 —— 软边由插值天然得到。

    为什么必须在低分辩上排名：全分辨率下分数是 8 位量化来的，同分像素成片并列；
    而且排名选出的像素是散点，后续闭运算会把散点连成地毯（实测 4.5% 变 20%）。
    低分辨率网格上每个格子代表一片区域，选出来的必然是成块的区域。
    """
    t = dict(DEFAULT_MASK_TARGETS)
    if targets:
        t.update(targets)

    h, w = img.shape[:2]
    grid = 128                                  # 低分辩网格宽度
    gh = max(32, round(grid * h / w))
    small = np.asarray(
        Image.fromarray(img).resize((grid, gh), Image.LANCZOS), dtype=np.float32
    ) / 255.0
    dsmall = np.asarray(
        Image.fromarray((depth * 255).astype(np.uint8)).resize((grid, gh), Image.BILINEAR),
        dtype=np.float32,
    ) / 255.0

    r, g, b = small[..., 0], small[..., 1], small[..., 2]
    mx = small.max(axis=-1)
    mn = small.min(axis=-1)
    sat = np.where(mx > 1e-5, (mx - mn) / np.maximum(mx, 1e-5), 0.0)
    yy = np.linspace(0, 1, gh, dtype=np.float32)[:, None]

    # 水面：下半幅、偏青蓝、中低饱和、亮度不塌
    yterm = np.clip((yy - 0.40) / 0.30, 0.0, 1.0)
    blue = np.clip((b - r + 0.10) / 0.20, 0.0, 1.0)
    midlight = np.clip((mx - 0.30) / 0.30, 0.0, 1.0) * np.clip((0.95 - mx) / 0.15, 0.0, 1.0)
    water_s = yterm * blue * midlight * np.clip((0.45 - sat) / 0.45, 0.0, 1.0)

    # 云雾：偏远 + 亮 + 低饱和（青绿山水的云气偏淡青灰，不是纯白）
    far = np.clip((0.55 - dsmall) / 0.55, 0.0, 1.0)
    light = np.clip((mx - 0.42) / 0.40, 0.0, 1.0)
    mist_s = (far ** 1.2) * light * np.clip((0.55 - sat) / 0.55, 0.0, 1.0)

    # 近景植被：偏绿的黄绿相、且靠前
    greenish = np.clip((g - np.maximum(r, b) + 0.035) / 0.09, 0.0, 1.0)
    foliage_s = greenish * np.clip((dsmall - 0.20) / 0.50, 0.0, 1.0)

    water = _rank_mask(water_s, t["water"], feather=0.35)
    mist = _rank_mask(mist_s, t["mist"], feather=0.30)
    foliage = _rank_mask(foliage_s, t["foliage"], feather=0.35)

    def up(m: np.ndarray, radius: float = 1.2) -> np.ndarray:
        """低分辩 → 目标尺寸：双三次插值得到软边，再轻微模糊抹掉格子感。"""
        upscaled = np.asarray(
            Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).resize(
                (width, hh), Image.BICUBIC
            ),
            dtype=np.float32,
        ) / 255.0
        im = Image.fromarray((upscaled * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(radius=radius * width / 512.0)
        )
        return np.asarray(im, dtype=np.float32) / 255.0

    hh = round(h * width / w)
    rgbf = np.stack([up(water), up(mist), up(foliage)], axis=-1)
    resized = np.clip(rgbf, 0, 1)

    stats = {
        "water": round(float(resized[..., 0].mean()), 4),
        "mist": round(float(resized[..., 1].mean()), 4),
        "foliage": round(float(resized[..., 2].mean()), 4),
    }
    return (resized * 255).astype(np.uint8), stats


def flood_region(cand: np.ndarray, sx: int, sy: int, iters: int = 400) -> np.ndarray:
    """从种子点做四邻域漫水，只保留与种子连通的那一块。

    为什么不用「全局深度阈值」：第一版直接阈值化，结果把水面、岸石、松枝
    全算成一块，bbox 横跨大半张画、羽化后 alpha 覆盖率归零。近景抠像必须
    是「某一棵树」，所以要从种子点长出来。
    """
    h, w = cand.shape
    if not cand[sy, sx]:
        # 种子落在阈值外时，在附近 7% 范围找最近的候选像素
        rr = max(6, int(h * 0.07))
        y0, y1 = max(0, sy - rr), min(h, sy + rr)
        x0, x1 = max(0, sx - rr), min(w, sx + rr)
        sub = cand[y0:y1, x0:x1]
        if not sub.any():
            return np.zeros_like(cand, dtype=bool)
        ys, xs = np.nonzero(sub)
        d = (ys - (sy - y0)) ** 2 + (xs - (sx - x0)) ** 2
        i = int(np.argmin(d))
        sy, sx = y0 + int(ys[i]), x0 + int(xs[i])

    reach = np.zeros_like(cand, dtype=bool)
    reach[sy, sx] = True
    for _ in range(iters):
        prev_sum = int(reach.sum())
        grown = reach.copy()
        grown[1:, :] |= reach[:-1, :]
        grown[:-1, :] |= reach[1:, :]
        grown[:, 1:] |= reach[:, :-1]
        grown[:, :-1] |= reach[:, 1:]
        reach = grown & cand
        if int(reach.sum()) == prev_sum:
            break
    return reach


def make_cutout(img: np.ndarray, depth: np.ndarray, spec: dict) -> tuple[Image.Image, dict] | None:
    """按深度阈值 + 种子漫水 + 局部窗口裁出一个近景元素，带羽化 alpha。

    踩过的坑：单靠漫水会把「松石+坡岸+水面」这一整片连通的近景都吃进去
    （实测 10.7% 面积）；再叠一层 MaxFilter→MinFilter 的开运算，细枝被
    彻底抹掉，alpha 里几乎没有像素 >128。所以：
      1) 用 seed 附近的归一化窗口把结果限制在一棵树的范围；
      2) 软边用「高斯模糊 + 增益」做，不用形态学，细枝才留得住。
    """
    h, w = depth.shape
    yy, xx = np.mgrid[0:h, 0:w]
    nx, ny = xx / w, yy / h
    sx, sy = float(spec["seed_x"]), float(spec["seed_y"])
    hw, hh = float(spec["half_w"]), float(spec["half_h"])

    window = (np.abs(nx - sx) <= hw) & (np.abs(ny - sy) <= hh)
    cand = (depth > spec["depth_min"]) & window
    if cand.sum() < w * h * 0.004:
        print(f"cutout {spec['id']}: 候选区域太小，跳过")
        return None

    seed = flood_region(cand, int(sx * w), int(sy * h))
    cov = float(seed.mean())
    if cov < 0.002:
        print(f"cutout {spec['id']}: 连通域 {cov:.3%} 太小，跳过")
        return None

    # 软边：模糊后拉增益，保证内部到 255、边缘平滑归零
    soft = Image.fromarray((seed * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(radius=9)
    )
    a = np.clip(np.asarray(soft, dtype=np.float32) * 2.6 - 44.0, 0, 255)
    if (a > 128).sum() < 500:
        print(f"cutout {spec['id']}: 羽化后有效像素过少，跳过")
        return None

    ys, xs = np.where(a > 10)
    pad = 6
    x0, x1 = max(0, xs.min() - pad), min(w, xs.max() + pad)
    y0, y1 = max(0, ys.min() - pad), min(h, ys.max() + pad)
    crop_img = img[y0:y1, x0:x1]
    crop_a = a[y0:y1, x0:x1]
    rgba = np.dstack([crop_img, crop_a]).astype(np.uint8)
    info = {
        "bbox_px": [int(x0), int(y0), int(x1 - x0), int(y1 - y0)],
        "bbox_norm": [round(x0 / w, 4), round(y0 / h, 4),
                      round((x1 - x0) / w, 4), round((y1 - y0) / h, 4)],
        "alpha_coverage": round(float((crop_a > 128).mean()), 4),
        "region_share": round(cov, 4),
        "size": [int(x1 - x0), int(y1 - y0)],
    }
    return Image.fromarray(rgba), info


# --------------------------------------------------------------------------- #
# 抠像参数兜底：命中太少 / 抠得过头时换一组参数重试（最多 3 组）
# --------------------------------------------------------------------------- #
ALPHA_MAX_OK = 0.85     # > 0.85 基本等于没抠（整块不透明）
ALPHA_MIN_OK = 0.05     # < 0.05 基本没内容


def _variant(spec: dict, direction: str) -> dict:
    """按失败方向调整一组参数：放宽/收紧深度阈值，同时放大/缩小窗口。"""
    out = dict(spec)
    dm = float(spec["depth_min"])
    if direction == "loosen":
        out["depth_min"] = round(max(0.30, dm - 0.08), 4)
        out["half_w"] = round(min(0.40, float(spec["half_w"]) * 1.30), 4)
        out["half_h"] = round(min(0.40, float(spec["half_h"]) * 1.30), 4)
    else:
        out["depth_min"] = round(min(0.92, dm + 0.08), 4)
        out["half_w"] = round(max(0.10, float(spec["half_w"]) * 0.72), 4)
        out["half_h"] = round(max(0.10, float(spec["half_h"]) * 0.72), 4)
    return out


def build_cutout_with_retry(img: np.ndarray, depth: np.ndarray, spec: dict,
                            max_attempts: int = 3) -> dict:
    """最多试 max_attempts 组参数，返回 {} 表示最终放弃（作品可以没有 cutout）。"""
    attempts: list[dict] = []
    cur = dict(spec)
    got = None
    for i in range(max_attempts):
        result = make_cutout(img, depth, cur)
        if result is None:
            attempts.append({"attempt": i + 1, "params": _params_of(cur),
                             "result": "none", "alpha_coverage": None})
            nxt = "loosen"
        else:
            im, info = result
            alpha = float(info["alpha_coverage"])
            attempts.append({"attempt": i + 1, "params": _params_of(cur),
                             "result": "ok" if ALPHA_MIN_OK <= alpha <= ALPHA_MAX_OK else
                             ("too_opaque" if alpha > ALPHA_MAX_OK else "too_sparse"),
                             "alpha_coverage": alpha})
            if ALPHA_MIN_OK <= alpha <= ALPHA_MAX_OK:
                got = (im, info, cur)
                break
            nxt = "tighten" if alpha > ALPHA_MAX_OK else "loosen"
        if i + 1 < max_attempts:
            cur = _variant(cur, nxt)
    if got is None:
        return {"ok": False, "attempts": attempts}
    im, info, used = got
    return {"ok": True, "attempts": attempts, "image": im, "info": info,
            "params_used": _params_of(used),
            "retried": len(attempts) > 1}


def _params_of(spec: dict) -> dict:
    return {
        "depth_min": round(float(spec["depth_min"]), 4),
        "seed": {"x": round(float(spec["seed_x"]), 4), "y": round(float(spec["seed_y"]), 4)},
        "half": {"w": round(float(spec["half_w"]), 4), "h": round(float(spec["half_h"]), 4)},
    }


# --------------------------------------------------------------------------- #
# 热点取深度
# --------------------------------------------------------------------------- #
def measure_hotspots(depth: np.ndarray, cfg: dict) -> list[dict]:
    """按配置量每个热点的深度。

    矩形热点（w>0）的 x/y 是矩形中心 —— 与 export_artwork_configs.mjs 的导出
    口径、以及 frontend/src/data/experiences/*.ts 的 geometry 中心一致；
    圆形热点（w==0）的 x/y 是圆心，半径取配置里的 r（缺省 0.05）。
    """
    H, W = depth.shape
    spots = []
    for sp in cfg["hotspots"]:
        if sp["w"] > 0:
            x0 = int((sp["x"] - sp["w"] / 2) * W)
            x1 = int(min(1.0, sp["x"] + sp["w"] / 2) * W)
            y0 = int((sp["y"] - sp["h"] / 2) * H)
            y1 = int(min(1.0, sp["y"] + sp["h"] / 2) * H)
        else:
            r = sp["r"]
            x0 = int(max(0.0, sp["x"] - r) * W)
            x1 = int(min(1.0, sp["x"] + r) * W)
            y0 = int(max(0.0, sp["y"] - r) * H)
            y1 = int(min(1.0, sp["y"] + r) * H)
        x0, x1 = max(0, min(W, x0)), max(1, min(W, x1))
        y0, y1 = max(0, min(H, y0)), max(1, min(H, y1))
        patch = depth[y0:y1, x0:x1]
        if patch.size == 0:
            patch = depth[max(0, y0 - 1):y0 + 1, max(0, x0 - 1):x0 + 1]
        cx = round(((x0 + x1) / 2) / W, 4) if sp["w"] > 0 else round(sp["x"], 4)
        cy = round(((y0 + y1) / 2) / H, 4) if sp["w"] > 0 else round(sp["y"], 4)
        measured = round(float(np.median(patch)), 4)
        # 深度图在天空/云气处会贴到 0，在个别近景边缘会贴到 1。
        # 热点若落在极值上，点它时镜头会被推到网格的最远端或最近端（观感像瞬移），
        # 而且气泡会贴着网格面片飞出去。统一夹在 [0.14, 0.88]。
        clamped = round(min(DEPTH_CLAMP[1], max(DEPTH_CLAMP[0], measured)), 4)
        override = cfg["hotspot_depth_overrides"].get(sp["id"])
        final = clamped if override is None else float(override)
        spots.append({
            "id": sp["id"], "x": cx, "y": cy,
            "depth": round(float(final), 4),
            "depth_measured": measured,
            "depth_overridden": override is not None,
        })
    return spots


# --------------------------------------------------------------------------- #
# 质量统计（写报告用；不改变任何产物）
# --------------------------------------------------------------------------- #
def _corr(a: np.ndarray, b: np.ndarray) -> float:
    a = a.ravel().astype(np.float64)
    b = b.ravel().astype(np.float64)
    if a.size < 4 or a.std() < 1e-9 or b.std() < 1e-9:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def depth_quality(img: np.ndarray, depth: np.ndarray) -> dict:
    """深度图的可复核统计：与亮度/饱和度相关性 + 直方图是否单峰塌缩。

    伪彩预览（depth-preview.png）靠人眼判断，这里给出可量化的替代指标：
      * corr_luma：正常山水约 -0.2~-0.6（越亮往往越远），|corr| 过小说明深度
        与画面结构脱节；
      * corr_sat：弱相关正常，强正相关说明深度在跟「色彩浓淡」走；
      * share_mid：落在 0.40~0.60 的像素占比，>0.85 即直方图塌缩成一条线，
        视差几乎没有区分度，属于不合格。
    """
    h, w = depth.shape
    small = np.asarray(Image.fromarray(img).resize((256, 256), Image.LANCZOS),
                       dtype=np.float32) / 255.0
    d = np.asarray(Image.fromarray((depth * 255).astype(np.uint8)).resize(
        (256, 256), Image.BILINEAR), dtype=np.float32) / 255.0
    mx, mn = small.max(axis=-1), small.min(axis=-1)
    luma = (0.299 * small[..., 0] + 0.587 * small[..., 1] + 0.114 * small[..., 2])
    sat = np.where(mx > 1e-5, (mx - mn) / np.maximum(mx, 1e-5), 0.0)
    share_mid = float(((d >= 0.40) & (d <= 0.60)).mean())
    return {
        "corr_luma": round(_corr(d, luma), 4),
        "corr_sat": round(_corr(d, sat), 4),
        "share_0.40_0.60": round(share_mid, 4),
        "std": round(float(d.std()), 4),
    }


# --------------------------------------------------------------------------- #
# 单件构建
# --------------------------------------------------------------------------- #
def build_artwork(cfg: dict, args) -> dict:
    slug = cfg["slug"]
    art_path = cfg["source"]
    out_dir = os.path.join("frontend", "public", "interactive", slug, "world")
    os.makedirs(out_dir, exist_ok=True)
    cache = os.path.join(PROBE_DIR, f"{slug}-depth.npy")

    gamma = cfg["gamma"] if cfg["gamma"] is not None else args.gamma
    smooth = cfg["depth_smooth"] if cfg["depth_smooth"] is not None else args.depth_smooth
    print(f"\n=== {slug} ({cfg['title']}) ===")

    img = np.asarray(Image.open(art_path).convert("RGB"))
    H, W = img.shape[:2]
    print(f"artwork: {art_path} {W}x{H}  aspect={W / H:.4f}")

    raw = run_depth(art_path, cfg["depth_repo"], cache, args.force_depth)
    depth = normalise_depth(raw, gamma)
    # 轻平滑：未经平滑的深度在边界处落差很陡，做成网格后那些地方是近乎垂直的
    # 「墙」，斜看时被拉成细长条纹（试看时被读成「画被撕裂」）。模糊 3px 后
    # 落差摊开，位移更连贯；代价是最锐的边稍微变软，这与设色画的观感是一致的。
    depth = smooth_depth(depth, smooth)
    dec = np.percentile(depth, [2, 10, 25, 50, 75, 90, 98])
    near_share = float((depth > 0.8).mean())
    far_share = float((depth < 0.35).mean())
    print("depth percentiles (1=near): " + " ".join(f"{v:.3f}" for v in dec))
    print("depth mean=%.3f  near(>0.8)=%.1f%%  far(<0.35)=%.1f%%"
          % (depth.mean(), near_share * 100, far_share * 100))

    # 1) 画作贴图
    art_out = os.path.join(out_dir, "art.webp")
    Image.fromarray(img).save(art_out, quality=92, method=6)
    print(f"art.webp: {os.path.getsize(art_out) / 1024:.0f} KB")

    # 2) 深度
    depth_out = os.path.join(out_dir, "depth-rg.png")
    pack_depth_rg(depth, depth_out, DEPTH_TEX_W)
    print(f"depth-rg.png: {os.path.getsize(depth_out) / 1024:.0f} KB")

    # 3) 兜底背景
    backdrop = edge_extend(img)
    bd_out = os.path.join(out_dir, "backdrop.webp")
    Image.fromarray(backdrop).resize(
        (max(512, W // 2), max(342, H // 2)), Image.LANCZOS
    ).save(bd_out, quality=86, method=6)
    print(f"backdrop.webp: {os.path.getsize(bd_out) / 1024:.0f} KB")

    # 4) 遮罩
    masks, mstats = build_masks(img, depth, MASK_TEX_W, cfg["mask_targets"])
    mk_out = os.path.join(out_dir, "masks.png")
    Image.fromarray(masks, mode="RGB").save(mk_out, optimize=True)
    print(f"masks.png: {os.path.getsize(mk_out) / 1024:.0f} KB  coverage={mstats}")

    # 5) 近景抠像（失败会换参数重试，最终仍失败就允许没有 cutout）
    cut_meta = []
    cut_report = []
    for spec in cfg["cutouts"]:
        got = build_cutout_with_retry(img, depth, spec)
        if not got["ok"]:
            print(f"cutout {spec['id']}: 3 组参数都没抠出来，跳过（不硬抠）")
            cut_report.append({"id": spec["id"], "label": spec["label"], "ok": False,
                               "attempts": got["attempts"]})
            continue
        im, info = got["image"], got["info"]
        p = os.path.join(out_dir, f"cutout-{spec['id']}.webp")
        im.save(p, quality=90, method=6)
        info.update({"id": spec["id"], "label": spec["label"], "file": f"cutout-{spec['id']}.webp",
                     "bytes": os.path.getsize(p)})
        cut_meta.append(info)
        cut_report.append({"id": spec["id"], "label": spec["label"], "ok": True,
                           "file": info["file"], "params_used": got["params_used"],
                           "retried": got["retried"], "attempts": got["attempts"],
                           "alpha_coverage": info["alpha_coverage"],
                           "region_share": info["region_share"],
                           "bbox_norm": info["bbox_norm"], "size": info["size"],
                           "bytes": info["bytes"]})
        print(f"cutout {spec['id']}: {info['size']} bbox_norm={info['bbox_norm']} "
              f"alpha={info['alpha_coverage']} {info['bytes'] / 1024:.0f} KB"
              + ("  (重试过)" if got["retried"] else ""))

    # 6) 伪彩预览（人工/模型复核用）
    prev = turbo(depth)
    Image.fromarray(prev).resize((W // 2, H // 2), Image.BILINEAR).save(
        os.path.join(out_dir, "depth-preview.png")
    )

    # 7) 热点取深度，给前端定位用
    spots = measure_hotspots(depth, cfg)

    # 8) 相机参数：按画面长宽比推一个「看得完」的入场终点
    aspect = W / H
    vert_fov = 34.0
    dist_to_fill = 0.5 / math.tan(math.radians(vert_fov / 2))
    world = {
        "version": 1,
        "slug": slug,
        "title": cfg["title"],
        "art": {"file": "art.webp", "width": W, "height": H, "aspect": round(aspect, 4)},
        "depth": {"file": "depth-rg.png", "width": DEPTH_TEX_W,
                  "height": round(H * DEPTH_TEX_W / W), "gamma": gamma},
        "backdrop": {"file": "backdrop.webp"},
        "masks": {"file": "masks.png", "width": MASK_TEX_W,
                  "height": round(H * MASK_TEX_W / W), "coverage": mstats},
        "cutouts": cut_meta,
        "hotspots": spots,
        "camera": {
            "fov": vert_fov,
            "plane_height": 1.0,
            "plane_width": round(aspect, 4),
            "distance_fill": round(dist_to_fill, 4),
            "depth_amplitude": 0.30,
            "yaw_limit_deg": 18.0,
            "pitch_limit_deg": 12.0,
            "dolly_near": 0.62,
            "dolly_far": 1.55,
            "entry": {"from_scale": 1.74, "duration_ms": 2600},
        },
        "provenance": {
            "depth_model": cfg["depth_repo"],
            "depth_generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "note": "单图深度估计，2.5D 深度网格；有限视角，不是三维重建，"
                    "不能绕视到物体背后。",
        },
    }
    wj = os.path.join(out_dir, "world.json")
    with open(wj, "w", encoding="utf-8") as fh:
        json.dump(world, fh, ensure_ascii=False, indent=2)
    print(f"world.json: {os.path.getsize(wj) / 1024:.1f} KB")
    print("hotspot depth: " + ", ".join(f"{s['id']}={s['depth']}" for s in spots))

    files = {}
    for f in sorted(os.listdir(out_dir)):
        p = os.path.join(out_dir, f)
        if os.path.isfile(p):
            files[f] = os.path.getsize(p)
    total = sum(files.values())
    print("total bytes: %.1f KB" % (total / 1024))

    # 9) 机器可读报告
    quality = depth_quality(img, depth)
    anomalies = _collect_anomalies(files, near_share, far_share, mstats, cut_report,
                                   quality, len(cfg["cutouts"]))
    print("anomalies: " + ("none" if not anomalies else "; ".join(anomalies)))
    return {
        "slug": slug,
        "title": cfg["title"],
        "styleName": cfg["style_name"],
        "config_path": cfg["config_path"].replace("\\", "/"),
        "source": cfg["source"].replace("\\", "/"),
        "source_size": {"width": W, "height": H, "bytes": os.path.getsize(art_path)},
        "out_dir": out_dir.replace("\\", "/"),
        "depth": {
            "model": cfg["depth_repo"],
            "gamma": gamma,
            "smooth_radius": smooth,
            "percentiles": {
                "p2": round(float(dec[0]), 4), "p10": round(float(dec[1]), 4),
                "p25": round(float(dec[2]), 4), "p50": round(float(dec[3]), 4),
                "p75": round(float(dec[4]), 4), "p90": round(float(dec[5]), 4),
                "p98": round(float(dec[6]), 4),
            },
            "mean": round(float(depth.mean()), 4),
            "near_share_gt_0.8": round(near_share, 4),
            "far_share_lt_0.35": round(far_share, 4),
            "quality": quality,
        },
        "masks": {"coverage": mstats, "targets": cfg["mask_targets"]},
        "cutouts": cut_report,
        "hotspots": [{"id": s["id"], "x": s["x"], "y": s["y"], "depth": s["depth"],
                      "depth_measured": s["depth_measured"],
                      "depth_overridden": s["depth_overridden"]} for s in spots],
        "hotspot_depth_overrides": cfg["hotspot_depth_overrides"],
        "files": files,
        "total_bytes": total,
        "anomalies": anomalies,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def _collect_anomalies(files: dict, near_share: float, far_share: float,
                       mstats: dict, cut_report: list, quality: dict,
                       cutout_specs: int) -> list[str]:
    """把「数值越界」翻译成人能读的异常串。空数组 = 全部在范围内。"""
    out: list[str] = []
    for f in REQUIRED_FILES:
        if f not in files:
            out.append(f"缺少必需文件 {f}")
        elif files[f] <= 0:
            out.append(f"必需文件 {f} 为空")
    if near_share > 0.40:
        out.append(f"near(>0.8) 占比 {near_share:.1%} > 40%，近景区域过大")
    if far_share <= 0.0:
        out.append("far(<0.35) 占比为 0，画面没有远景层")
    for k in ("water", "mist", "foliage"):
        v = mstats.get(k, 0.0)
        if not (0.02 <= v <= 0.45):
            out.append(f"mask coverage {k}={v:.1%} 超出 2%–45%")
    if quality["share_0.40_0.60"] > 0.85:
        out.append(f"深度直方图单峰塌缩：{quality['share_0.40_0.60']:.1%} 像素落在 0.40–0.60")
    if abs(quality["corr_luma"]) < 0.15:
        out.append(f"深度与亮度几乎无关（corr_luma={quality['corr_luma']}）")
    for c in cut_report:
        if not c["ok"]:
            out.append(f"cutout {c['id']} 三组参数都没抠出来，该作品无此抠像")
        elif c["retried"]:
            out.append(f"cutout {c['id']} 换过参数才成功（用了 "
                       f"depth_min={c['params_used']['depth_min']}）")
    if cutout_specs and not any(c["ok"] for c in cut_report):
        out.append("world.json 的 cutouts 为空数组")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default=None,
                    help="作品 slug（配置在 scripts/interactive/artworks/<slug>.json）；"
                         "不给时默认为 songhua")
    ap.add_argument("--all", action="store_true", help="构建 artworks/ 下全部配置")
    ap.add_argument("--config", default=None, help="直接读一个自定义 JSON 配置")
    ap.add_argument("--force-depth", action="store_true", help="忽略深度缓存，重跑模型")
    ap.add_argument("--gamma", type=float, default=0.72)
    ap.add_argument("--depth-smooth", type=float, default=3.0,
                    help="深度平滑半径（原图像素），0 表示不平滑")
    ap.add_argument("--report", default=DEFAULT_REPORT, help="机器可读构建报告路径")
    args = ap.parse_args()

    configs = select_configs(args)
    report = {}
    if os.path.exists(args.report):
        try:
            with open(args.report, "r", encoding="utf-8") as fh:
                report = json.load(fh)
        except (json.JSONDecodeError, OSError):
            report = {}

    failures = 0
    for raw_cfg in configs:
        cfg = normalise_config(raw_cfg)
        try:
            entry = build_artwork(cfg, args)
        except SystemExit:
            raise
        except Exception as exc:  # 单件失败不拖垮 --all
            failures += 1
            print(f"[失败] {cfg['slug']}: {type(exc).__name__}: {exc}")
            report[cfg["slug"]] = {
                "slug": cfg["slug"], "title": cfg["title"], "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "anomalies": [f"构建抛异常：{type(exc).__name__}: {exc}"],
                "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            continue
        entry["ok"] = True
        report[cfg["slug"]] = entry
        os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)

    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print(f"\nreport: {args.report}（{len(report)} 件）")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())