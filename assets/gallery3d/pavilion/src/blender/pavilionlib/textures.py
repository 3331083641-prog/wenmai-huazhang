"""程序化 PBR 贴图生成 —— 纯 numpy 算法，不依赖任何外部图片素材。

消费端约定（`materials.py` / `finalize.py`）：
* 每个材质 key 输出三张 PNG，放在 ``<tex_dir>``：
    ``{key}_basecolor.png``  sRGB   (RGB)
    ``{key}_orm.png``        Non-Color，R=AO / G=Roughness / B=Metallic
    ``{key}_normal.png``     Non-Color，切线空间法线（绿色 +Y 向上）
* 尺寸取 ``MAT_META[key][4]``（2048 / 1024 / 512），不在这里写死。
* AO 由 ``finalize.bake_ao()`` 先产出 ``ao_{key}.png``，这里只把它读进 ORM 的 R 通道；
  **不**把 AO 乘进 basecolor（Three.js 用 aoMap 自己乘）。

实现要点
--------
* **无缝平铺**：所有噪声都是周期化实现 —— 值噪声用整数周期的环形栅格（`_vnoise_raw`），
  分形叠加时周期按 2 倍递增（`_fbm`），白噪声天然周期，板缝/瓦垄用「到最近整数格
  线的像素距离」构造，因此四周边缘天然对齐、大屋面上不会看到接缝。
* **Blender 写图**：实测 ``Image.pixels`` 是「直接字节值 / 255」，``save()`` 不做
  线性→sRGB 转换，所以 sRGB 贴图必须自己编码（``_srgb_encode``）；ORM / normal
  保持线性直接写。
"""
from __future__ import annotations

import os
import time

import numpy as np

# 相对导入；直接用 Blender -P 跑本文件时（__name__ == "__main__"）退化为绝对导入
try:
    from .materials import MAT_META, MAT_ORDER
except ImportError:  # pragma: no cover
    import sys as _sys

    _sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from pavilionlib.materials import MAT_META, MAT_ORDER

try:
    import bpy
except ImportError:  # 允许在纯 python 下 import 本模块做单元检查
    bpy = None


# ============================================================ 色彩工具
def _srgb_encode(x):
    """线性 → sRGB（0..1）。"""
    x = np.clip(x, 0.0, 1.0).astype(np.float32)
    return np.where(x <= 0.0031308, x * 12.92,
                    1.055 * np.power(np.maximum(x, 1e-8), 1.0 / 2.4) - 0.055).astype(np.float32)


def _hex_lin(hexc: str):
    """'#RRGGBB' → 线性 RGB（与 materials._hex 同口径）。"""
    h = hexc.lstrip("#")
    s = np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)
    return np.where(s <= 0.04045, s / 12.92,
                    ((s + 0.055) / 1.055) ** 2.4).astype(np.float32)


def _srgb_decode(x):
    """sRGB（0..1）→ 线性。"""
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92,
                    np.power((x + 0.055) / 1.055, 2.4)).astype(np.float32)


def _shade(base_lin, shade, amount=1.0):
    """在 sRGB（感知）域里乘纹理明暗因子，再回到线性。

    为什么不直接 base*shade：深色材质在线性域乘 ±10%，落到 sRGB 只差 2 个 8bit 级
    （#2B211B 的 0.023 线性 ×1.10 → 41 级变 43 级），年轮、矿物颗粒、板缝全被压成
    一片纯色。美术意义上的「色差、纹理」本来就是感知域定义的，所以先编码再乘。
    amount 用来整体收放对比度（1.0 = 按传入 shade 的原幅度）。
    """
    b = _srgb_encode(np.asarray(base_lin, np.float32))
    s = 1.0 + float(amount) * (np.asarray(shade, np.float32) - 1.0)
    return _srgb_decode(np.clip(b[None, None, :] * s[..., None], 0.0, 1.0))


# ============================================================ 噪声原语（全部周期化）
def _quintic(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _uv(size):
    """返回 U (1,size)、V (size,1) 两个 0..1 采样坐标。"""
    t = ((np.arange(size, dtype=np.float32) + 0.5) / size).astype(np.float32)
    return t[None, :], t[:, None]


# 噪声计算分辨率上限：2048 贴图上的有机细节在 1024 上算完再平滑放大，
# 肉眼看不出差别（1 UV 单位 = 1m 时 1024 已是 1mm 级），但快 4 倍。
_CAP = 1024


def _vnoise_raw(n, pu, pv, seed):
    """在 n×n 栅格上算周期值噪声：U 方向 pu 个周期、V 方向 pv 个周期（整数）。"""
    pu, pv = max(int(pu), 1), max(int(pv), 1)
    rng = np.random.default_rng(seed)
    g = rng.random((pv, pu)).astype(np.float32)          # 行 = v，列 = u
    xs = (np.arange(n, dtype=np.float32) + 0.5) * (pu / n)
    ys = (np.arange(n, dtype=np.float32) + 0.5) * (pv / n)
    x0 = np.floor(xs).astype(np.int32)
    y0 = np.floor(ys).astype(np.int32)
    tx = _quintic((xs - x0).astype(np.float32))          # 五次插值，比线性更顺
    ty = _quintic((ys - y0).astype(np.float32))
    tx = tx[None, :]
    ty = ty[:, None]
    x0 %= pu
    y0 %= pv
    x1 = (x0 + 1) % pu
    y1 = (y0 + 1) % pv
    a = g[np.ix_(y0, x0)]
    b = g[np.ix_(y0, x1)]
    c = g[np.ix_(y1, x0)]
    d = g[np.ix_(y1, x1)]
    return ((a * (1.0 - tx) + b * tx) * (1.0 - ty) +
            (c * (1.0 - tx) + d * tx) * ty).astype(np.float32)


def _resample_periodic(a, size):
    """周期性平滑缩放（低频层先在小尺寸算，再放大，省时间）。"""
    n = a.shape[0]
    if n == size:
        return a.astype(np.float32)
    idx = (np.arange(size, dtype=np.float32) + 0.5) * (n / size) - 0.5
    i0 = np.floor(idx).astype(np.int32)
    t = _quintic((idx - i0).astype(np.float32))
    i0 %= n
    i1 = (i0 + 1) % n
    rows = a[i0] * (1.0 - t)[:, None] + a[i1] * t[:, None]
    return (rows[:, i0] * (1.0 - t)[None, :] + rows[:, i1] * t[None, :]).astype(np.float32)


def _vnoise(size, pu, pv, seed):
    """周期值噪声（自动按 _CAP 降分辨率计算再放大）。"""
    n = min(int(size), _CAP)
    v = _vnoise_raw(n, pu, pv, seed)
    return _resample_periodic(v, size) if n != size else v


def _fbm(size, pu, pv, octaves, seed, gain=0.5):
    """周期化分形噪声，返回 0..1（均值约 0.5）。"""
    n = min(int(size), _CAP)
    acc = np.zeros((n, n), np.float32)
    amp, norm = 1.0, 0.0
    for i in range(int(octaves)):
        acc += amp * _vnoise_raw(n, pu * (2 ** i), pv * (2 ** i), seed + 7919 * i)
        norm += amp
        amp *= gain
    acc /= norm
    lo, hi = float(acc.min()), float(acc.max())
    acc = ((acc - lo) / max(hi - lo, 1e-6)).astype(np.float32)
    return _resample_periodic(acc, size) if n != size else acc


def _aniso(size, pu, pv, octaves, seed):
    """各向异性 fbm：pu 小 / pv 大 → 沿 U 拉长的细条纹（木纹、拉丝、抹刀痕）。"""
    return _fbm(size, pu, pv, octaves, seed)


def _white(size, seed):
    """白噪声（iid，天然无缝），0..1。"""
    return np.random.default_rng(seed).random((size, size), dtype=np.float32)


def _worley(n, cells, seed):
    """可平铺 Worley F1 距离场（向量化：一次算全部特征点）。

    返回 0..1 归一化后的 F1：值大 = 离团簇中心远 = 簇间缝隙。
    """
    cells = max(int(cells), 1)
    rng = np.random.default_rng(seed)
    jx = rng.random((cells, cells)).astype(np.float32)
    jy = rng.random((cells, cells)).astype(np.float32)
    gx = (np.arange(cells, dtype=np.float32)[None, :] + 0.5 + 0.8 * (jx - 0.5)) / cells
    gy = (np.arange(cells, dtype=np.float32)[:, None] + 0.5 + 0.8 * (jy - 0.5)) / cells
    fx = np.repeat(gx, cells, axis=0).ravel()      # 特征点 x（0..1）
    fy = np.repeat(gy, cells, axis=1).ravel()      # 特征点 y（0..1）
    p = ((np.arange(n, dtype=np.float32) + 0.5) / n).astype(np.float32)
    X, Y = p[None, :], p[:, None]
    f1 = np.full((n, n), 9.0, np.float32)
    # 周期边界：特征点整体平移 ±1 个周期各算一次，逐点取最小
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            for k in range(fx.size):
                ddx = (fx[k] + dx) - X
                ddy = (fy[k] + dy) - Y
                np.minimum(f1, np.sqrt(ddx * ddx + ddy * ddy), out=f1)
    lo, hi = float(f1.min()), float(f1.max())
    return ((f1 - lo) / max(hi - lo, 1e-6)).astype(np.float32)


def _lines(size, count, width_px, axis, feather=0.5):
    """周期等距格线（板缝）：返回 0..1，1 = 线心。带亚像素抗锯齿。

    axis=0 → 缝沿 V 方向等距排布（线是水平的）；axis=1 → 缝沿 U 方向排布（竖缝）。
    """
    n = (np.arange(size, dtype=np.float32) + 0.5) / size * count
    # 缝放在「格心」(n = k + 0.5) 而不是格线 (n = k) 上：否则缝心正好压在贴图边界，
    # 只有一半宽度落在瓦片内，拼缝看起来只有一半宽且左右不对称。
    d = np.abs((n + 0.5) - np.round(n + 0.5)) / count * size        # 到最近缝心的像素距离
    half = max(float(width_px) * 0.5, 1e-3)
    m = np.clip((half + feather - d) / (feather + 1e-6), 0.0, 1.0).astype(np.float32)
    return m[:, None] if axis == 0 else m[None, :]


def _slab_tone(size, count, seed):
    """大板之间的轻微色差（块状，非渐变）。"""
    rng = np.random.default_rng(seed)
    g = rng.random((count, count)).astype(np.float32)
    step = max(size // count, 1)
    up = np.repeat(np.repeat(g, step, axis=0), step, axis=1)
    for ax in (0, 1):
        if up.shape[ax] < size:
            pad = [(0, 0), (0, 0)]
            pad[ax] = (0, size - up.shape[ax])
            up = np.pad(up, pad, mode="wrap")
    # 色块边界与 _lines 的缝心对齐（缝在格心 → 色块也整体滚半个 cell）
    up = np.roll(up, (step // 2, step // 2), axis=(0, 1))
    return np.ascontiguousarray(up[:size, :size], dtype=np.float32)


def _normal_from_height(h, slope=0.35, floor=0.004):
    """高度场 → 切线空间法线 (nx, ny, nz)。像素行号向上（Blender 像素左下为原点）。

    两个关键点：
    1) 用「前向差分」而不是中心差分：中心差分要 roll ±1 相减，在周期边界处两个窗口
       不对称，会沿接缝拉出一条假的高光/暗线（平铺后肉眼可见）。前向差分只比较本像素
       与下一个像素（跨边界时正是绕回的那一个），天然无缝。
    2) 不把「相邻像素差」直接当斜率：差值随贴图分辨率缩小（2048 的细纹只有 0.002），
       直接写出来就是一整张平坦法线，等于没做。这里按材质自身的梯度做相对标定 ——
       取 99.5 分位梯度当 1，再乘 slope（0.35 ≈ 19°）：宽结构（瓦垄、年轮、团簇缝）
       都能得到同一量级、看得见又不过火的起伏；而没有起伏的材质（玉墙、玻璃）梯度
       极小，最多只放大 slope/floor 倍，所以依然是平的。
    """
    du = (np.roll(h, -1, axis=1) - h).astype(np.float32)
    dv = (np.roll(h, -1, axis=0) - h).astype(np.float32)
    g = np.sqrt(du * du + dv * dv)
    p = float(np.percentile(g, 99.5))
    k = float(slope) / max(p, float(floor))
    nx = (-du * k).astype(np.float32)
    ny = (-dv * k).astype(np.float32)
    nz = np.ones_like(nx)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / l, ny / l, nz / l], axis=-1).astype(np.float32)


def _flat_normal(size):
    n = np.zeros((size, size, 3), np.float32)
    n[..., 2] = 1.0
    return n


def _fill(size, v):
    return np.full((size, size), float(v), np.float32)


def _clip01(x):
    return np.clip(x, 0.0, 1.0).astype(np.float32)


def _smoothstep(e0, e1, x):
    """软边阶跃：x<=e0 → 0，x>=e1 → 1，中间三次平滑。

    用来把连续剖面切成「明度带」（筒瓦 / 板瓦 / 沟槽），硬阈值会在带上留下锯齿线。
    """
    t = np.clip((np.asarray(x, np.float32) - float(e0)) / max(float(e1 - e0), 1e-6),
                0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _srgb_mean(hexc):
    """声明色的 sRGB 通道均值（0..255），作为 _match_mean 的目标值。"""
    h = hexc.lstrip("#")
    v = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float64)
    return float(v.mean())


def _match_mean(out_lin, target):
    """把 basecolor 的 sRGB 均值整体缩放到 target（0..255），只缩放不改色相。

    相乘式纹理的均值恒小于「均值的相乘」，而且对比度越大压得越狠（wood_dark 加对比
    后均值会掉十几个 8bit 级）。这里统一乘一个常数把均值拉回声明色，改多少次对比度
    都不会跑出 lead 的 ±15 验收；缩放是在 sRGB 域做，所以色相不变。
    """
    s = _srgb_encode(np.clip(np.asarray(out_lin, np.float32), 0.0, 1.0))
    cur = float(s.mean()) * 255.0
    if target is None or cur < 1e-6:
        return np.clip(out_lin, 0.0, 1.0).astype(np.float32)
    k = float(target) / cur
    return _srgb_decode(np.clip(s * k, 0.0, 1.0))


# ============================================================ 各材质生成器
# 约定：f(size, hexc, rough0, metal0) -> (base_lin(H,W,3), rough(H,W), metal(H,W), normal(H,W,3))
# 粗糙度/金属度以 MAT_META 的声明值为中心做小幅起伏 —— ORM 的 G/B 通道会覆盖材质
# 的 socket 值，硬编码一套区间会让交付观感与声明值打架。
def _mk_wood_dark(size, hexc, rough0, metal0):
    """温润金丝栗壳楠木：沿 U 的细密年轮 + 板缝 + 低频色斑。

    基色从 #382A22 提到 #4A3528 后（亮 +32），年轮/细纹的对比度整体上调约 20%，
    亮面同样的百分比只会换来更少的可见层次，不补的话木纹会「发灰」。
    """
    U, V = _uv(size)
    base = _hex_lin(hexc)
    warp = (_fbm(size, 2, 3, 3, 101) - 0.5) * 0.05                  # 年轮翘曲
    ph = V + warp
    ring = 0.5 + 0.5 * np.cos(2 * np.pi * 11 * ph)                  # 11 条主纹
    fine = 0.5 + 0.5 * np.cos(2 * np.pi * 43 * ph + 1.9 * np.sin(2 * np.pi * 3 * U))
    lf = _fbm(size, 3, 3, 4, 113)                                   # 低频大色斑
    seam = np.maximum(_lines(size, 3, 1.6, 0), 0.55 * _lines(size, 2, 1.1, 1))
    # 第四期补的「纵纹」：U 向密、V 向疏的各向异性噪声 = 沿柱身竖向拉长的木纤维。
    # 原来只有随 V 变化的年轮（绕柱一圈的水平线），30m 外整体被平均成一块均匀深褐；
    # 加上这一层之后，竖向的疏密才会在远景留下「木头」的读感。
    vgrain = _aniso(size, 90, 3, 3, 131)
    vfine = _aniso(size, 260, 4, 2, 137)
    shade = ((1.0 + 0.06 * (lf - 0.5) * 2.0)                        # ±6% 明度
             * (1.0 - 0.120 * ring)                                 # 年轮压暗（远景让位给纵纹）
             * (1.0 - 0.085 * fine)                                 # 高频细纹
             * (1.0 + 0.110 * (vgrain - 0.5) * 2.0)                 # 竖向纵纹（主读感）
             * (1.0 + 0.055 * (vfine - 0.5) * 2.0)                  # 纵纹里的细丝
             * (1.0 - 0.180 * seam))                                # 板缝深 18%
    out = _shade(base, shade)
    out = _match_mean(out, _srgb_mean(hexc))                        # 对比度加大后均值回正
    rough = np.clip(rough0 + 0.04 * (ring - 0.5) + 0.015 * (lf - 0.5)
                    + 0.030 * (vgrain - 0.5) * 2.0,                # 纵纹带 ±0.03 粗糙度差
                    rough0 - 0.06, rough0 + 0.06)
    h = (-0.40 * seam - 0.06 * fine + 0.05 * ring + 0.05 * (vgrain - 0.5)).astype(np.float32)
    return out, rough.astype(np.float32), _fill(size, metal0), _normal_from_height(h, 0.34)


def _mk_wood_lite(size, hexc, rough0, metal0):
    """银杏黄暖木构件：更细更浅的年轮 + 轻微拉丝。"""
    U, V = _uv(size)
    base = _hex_lin(hexc)
    warp = (_fbm(size, 3, 2, 3, 211) - 0.5) * 0.035
    ph = V + warp
    ring = 0.5 + 0.5 * np.cos(2 * np.pi * 21 * ph)
    fine = 0.5 + 0.5 * np.cos(2 * np.pi * 67 * ph + 2.4 * np.sin(2 * np.pi * 5 * U))
    brush = _aniso(size, 6, 260, 2, 223)                            # 沿 U 的拉丝
    lf = _fbm(size, 2, 2, 3, 227)
    seam = np.maximum(_lines(size, 3, 1.4, 0), 0.5 * _lines(size, 2, 1.0, 1))
    shade = ((1.0 + 0.04 * (lf - 0.5) * 2.0)
             * (1.0 - 0.075 * ring)
             * (1.0 - 0.05 * fine)
             * (1.0 + 0.04 * (brush - 0.5) * 2.0)
             * (1.0 - 0.12 * seam))
    out = _shade(base, shade)
    rough = np.clip(rough0 + 0.035 * (ring - 0.5) + 0.015 * (brush - 0.5),
                    rough0 - 0.05, rough0 + 0.05)
    h = (-0.40 * seam - 0.03 * fine + 0.02 * brush).astype(np.float32)
    return out, rough.astype(np.float32), _fill(size, metal0), _normal_from_height(h, 0.26)


def _mk_wall_white(size, hexc, rough0, metal0):
    """羊脂温玉暖白微水泥：极干净。只有极低频色差 + 细砂粒 + 抹刀痕。"""
    U, V = _uv(size)
    base = _hex_lin(hexc)
    lf = _fbm(size, 2, 2, 3, 307)                                   # 极低频
    grain = _white(size, 311)                                       # 细砂粒
    trowel = _aniso(size, 3, 90, 2, 313)                            # 拉长抹刀痕
    seam = 0.35 * _lines(size, 2, 1.0, 1)                           # 极淡模板缝
    shade = ((1.0 + 0.015 * (lf - 0.5) * 2.0)
             * (1.0 + 0.02 * (grain - 0.5) * 2.0)
             * (1.0 + 0.008 * (trowel - 0.5) * 2.0)
             * (1.0 - 0.03 * seam))
    out = _shade(base, shade)
    rough = np.clip(rough0 + 0.03 * (lf - 0.5) * 2.0 + 0.015 * (trowel - 0.5),
                    rough0 - 0.04, rough0 + 0.04)
    h = (0.02 * (trowel - 0.5) + 0.01 * (grain - 0.5)).astype(np.float32)
    return out, rough.astype(np.float32), _fill(size, metal0), _normal_from_height(h, 0.04)


def _mk_roof_dai(size, hexc, rough0, metal0):
    """宋韵青黛琉璃瓦：6 垄筒瓦 + 板瓦 + 沟槽暗线 + 沿 U 的低频窑变。

    第四期加强（集成渲图里屋面读成「光滑青灰塑料壳」）：
    1) ORM 的 G 通道做 ±0.10 的垄沟对比：沟底积灰、挂光 → 更粗糙；瓦背釉厚 → 更光滑。
       太阳掠射时沟里先出暗线，远景读感主要靠这一条（比 basecolor 对比更管用，
       因为远景平均掉的是明度，留下的是粗糙度高光的方向性）。
    2) basecolor 分三条明度带：筒瓦顶 +4.5%、板瓦平伏面 -2%、沟槽 -5.5%，
       再叠沿 U 的低频窑变色差（±2%，只动色相不动明度）—— 宋琉璃瓦不是均匀色；
    3) 法线起伏 +40%（slope 0.34 → 0.476），近景能吃满掠射光。
    """
    U, V = _uv(size)
    base = _hex_lin(hexc)
    warp = (_fbm(size, 2, 4, 2, 401) - 0.5) * 0.02                   # 垄线轻微起伏
    cup = 0.5 + 0.5 * np.cos(2 * np.pi * 6 * (U + warp))             # 1=垄顶 0=沟底
    ridge = cup ** 0.75                                              # 垄面收窄一点，更像筒瓦
    tube = _smoothstep(0.66, 0.92, cup)                              # 筒瓦（圆弧顶）
    ditch = _clip01(1.0 - cup / 0.17) ** 0.8                         # 沟槽（谷底窄带）
    pan = _clip01(1.0 - tube - ditch)                                # 板瓦（平伏面）
    ox = _fbm(size, 3, 3, 3, 409)                                    # 釉面不匀/氧化斑
    kiln = _fbm(size, 5, 1, 2, 421)                                  # 沿 U 的低频窑变
    anis = _aniso(size, 6, 180, 2, 419)                              # 沿垄的油润拉丝
    shade = ((1.0 + 0.045 * tube - 0.020 * pan - 0.055 * ditch)
             * (1.0 + 0.05 * (ox - 0.5) * 2.0))
    shade /= max(float(shade.mean()), 1e-6)                          # 三条带不对称，均值归 1
    out = _shade(base, shade)
    k = (kiln - 0.5) * 2.0                                           # -1..1
    tint = np.stack([1.0 + 0.012 * k, np.ones_like(k), 1.0 - 0.014 * k], axis=-1)
    out = _srgb_decode(np.clip(_srgb_encode(out) * tint, 0.0, 1.0))
    out = _match_mean(out, _srgb_mean(hexc))
    drop = ((0.5 - ridge) * 0.20).astype(np.float32)                 # 垄顶 -0.10 / 沟底 +0.10
    drop -= float(drop.mean())                                       # 均值回正到声明粗糙度
    rough = np.clip(rough0 + drop + 0.02 * (anis - 0.5) * 2.0,
                    rough0 - 0.13, rough0 + 0.13)
    metal = np.clip(metal0 + 0.04 * (anis - 0.5) * 2.0 + 0.03 * (ox - 0.5),
                    metal0 - 0.08, metal0 + 0.07)
    h = (0.85 * cup).astype(np.float32)
    return out, rough.astype(np.float32), metal.astype(np.float32), _normal_from_height(h, 0.476)


def _mk_stone_dark(size, hexc, rough0, metal0):
    """青灰玄武岩铺装：2×2 大板拼缝 + 黑白矿物颗粒 + 极淡石英纹。

    基色从 #1A1C1E 抬到 #3C4449（暗部不再死黑）后，板缝与矿点对比度上调约 20%，
    否则细矿点会被 8bit 量化吃掉，铺装面会显得平板。
    """
    base = _hex_lin(hexc)
    seam = np.maximum(_lines(size, 2, 2.0, 0), _lines(size, 2, 2.0, 1))
    tone = _slab_tone(size, 2, 503)
    grain = _white(size, 509)
    grain2 = _white(size, 510)                                      # 第二层细颗粒
    speck_hi = (grain > 0.94).astype(np.float32)                    # 亮矿点
    speck_lo = (grain < 0.06).astype(np.float32)                    # 暗矿点
    speck = speck_hi * 0.62 - speck_lo * 0.55
    quartz = _fbm(size, 2, 3, 4, 521)
    vein = _clip01(1.0 - np.abs(quartz - 0.5) / 0.018) ** 1.5       # 细白石英纹
    lf = _fbm(size, 2, 2, 3, 523)
    shade = ((1.0 + 0.10 * (tone - 0.5) * 2.0)
             * (1.0 + 0.19 * speck)                                 # 矿物颗粒（+20%）
             * (1.0 + 0.030 * (grain2 - 0.5) * 2.0)
             * (1.0 + 0.05 * (lf - 0.5) * 2.0)
             * (1.0 + 0.30 * vein)
             * (1.0 - 0.24 * seam))                                 # 板缝深 24%（+20%）
    out = _shade(base, shade)
    rough = np.clip(rough0 + 0.02 * (tone - 0.5) * 2.0 + 0.02 * grain
                    + 0.03 * vein + 0.05 * seam, rough0 - 0.05, rough0 + 0.06)
    metal = _fill(size, metal0)                                     # 玄武岩非金属：B 通道恒为声明值
    h = (-0.50 * seam + 0.03 * vein + 0.008 * (grain - 0.5)).astype(np.float32)
    return out, rough.astype(np.float32), metal.astype(np.float32), _normal_from_height(h, 0.30)


def _mk_stone_lite(size, hexc, rough0, metal0):
    """汉白玉暖石铺装：板缝清晰 + 水线云纹 + 0.6~0.9m 浅色斑 + 细颗粒。

    第四期加强（bridge/台阶/台明在成图里是一整片 240+ 的纯白，读成塑料或石膏）：
    1) 均值压到 ~228（原 234.9）。白退一步，石头的重量感才出来；
    2) 低频水线云纹（±3%，暖灰偏色：R 升 B 降，明度基本不动）；
    3) 0.6~0.9m 尺度的浅色斑：1 个 UV ≈ 4m（板缝 2×2 → 每块 2m），5 个周期 ≈ 0.8m/块，
       是石材自身的不均，与板缝无关；
    4) roughness 在 0.45 上做 ±0.05 的斑驳 —— 掠射光下有细腰的漫反射变化，
       不再是均匀的塑料高光。
    """
    base = _hex_lin(hexc)
    seam = np.maximum(_lines(size, 2, 3.0, 0), _lines(size, 2, 3.0, 1))
    tone = _slab_tone(size, 2, 601)
    grain = _white(size, 607)
    grain2 = _white(size, 608)                                      # 第二层细颗粒（满场微起伏）
    speck = (grain > 0.935).astype(np.float32) * 0.55 - (grain < 0.065).astype(np.float32) * 0.45
    cloud = _fbm(size, 2, 3, 4, 619)                                # 水线云纹（低频）
    patch = _fbm(size, 5, 5, 2, 623)                                # 0.6~0.9m 浅色斑
    lf = _fbm(size, 3, 3, 4, 613)
    brush = _aniso(size, 8, 200, 2, 617)
    shade = ((1.0 + 0.030 * (cloud - 0.5) * 2.0)                    # 水线云纹 ±3%
             * (1.0 + 0.030 * np.clip((patch - 0.5) * 2.0, 0.0, 1.0))   # 浅色斑只提亮
             * (1.0 + 0.045 * (tone - 0.5) * 2.0)                   # 每块板的轻微色差
             * (1.0 + 0.14 * speck)                                 # 石材黑白矿点
             * (1.0 + 0.035 * (grain2 - 0.5) * 2.0)                 # 满场细砂
             * (1.0 + 0.03 * (lf - 0.5) * 2.0)
             * (1.0 + 0.02 * (brush - 0.5) * 2.0)
             * (1.0 - 0.22 * seam))
    out = _shade(base, shade)
    c = (cloud - 0.5) * 2.0                                         # 暖灰：R 升 B 降
    tint = np.stack([1.0 + 0.012 * c, np.ones_like(c), 1.0 - 0.016 * c], axis=-1)
    out = _srgb_decode(np.clip(_srgb_encode(out) * tint, 0.0, 1.0))
    out = _match_mean(out, 228.5)                                   # 目标均值 225~232 的中值
    mottle = (patch - 0.5) * 2.0
    rough = np.clip(rough0 + 0.05 * mottle
                    + 0.025 * (tone - 0.5) * 2.0
                    + 0.02 * (cloud - 0.5) * 2.0
                    + 0.03 * seam, rough0 - 0.05, rough0 + 0.05)
    h = (-0.55 * seam + 0.006 * (grain - 0.5)).astype(np.float32)
    return out, rough.astype(np.float32), _fill(size, metal0), _normal_from_height(h, 0.32)


def _mk_water(size, hexc, rough0, metal0):
    """澄澈影青水体：只有极低幅度大波纹 + 极淡涟漪法线（Three.js 会用 Reflector 替换）。"""
    U, V = _uv(size)
    base = _hex_lin(hexc)
    swell = _fbm(size, 1, 2, 3, 701)                                # 大尺度涌浪
    ripple = _fbm(size, 4, 4, 2, 709)                               # 小涟漪
    # 水体本身已是很深的影青，感知域里幅度要压住，否则水面会「脏」
    shade = 1.0 + 0.030 * (swell - 0.5) * 2.0 + 0.008 * (ripple - 0.5) * 2.0
    out = _shade(base, shade)
    rough = np.clip(rough0 + 0.012 * (swell - 0.5) * 2.0, rough0 - 0.02, rough0 + 0.02)
    h = (0.30 * swell + 0.08 * ripple).astype(np.float32)
    return out, rough.astype(np.float32), _fill(size, metal0), _normal_from_height(h, 0.10)


def _mk_glass(size, hexc, rough0, metal0):
    """影青透光玉石屏扇：几乎纯色，只有 1~2% 极淡条纹。"""
    U, V = _uv(size)
    base = _hex_lin(hexc)
    streak = _aniso(size, 2, 60, 2, 801)
    shade = 1.0 + 0.015 * (streak - 0.5) * 2.0
    out = _shade(base, shade)
    rough = np.clip(rough0 + 0.015 * (streak - 0.5) * 2.0, rough0 - 0.02, rough0 + 0.02)
    return out, rough.astype(np.float32), _fill(size, metal0), _flat_normal(size)


def _mk_bronze(size, hexc, rough0, metal0):
    """宋韵鎏金沉香细部：沿 U 的金属拉丝 + 轻微氧化斑。"""
    U, V = _uv(size)
    base = _hex_lin(hexc)
    brush = _aniso(size, 5, 240, 3, 901)                            # 拉丝
    brush2 = _aniso(size, 3, 90, 2, 907)
    lf = _fbm(size, 2, 2, 3, 911)                                   # 氧化/包浆低频
    patina = _clip01((lf - 0.55) * 2.6)                             # 只有偏高处生斑
    teal = np.array([0.055, 0.135, 0.110], np.float32)              # 偏青的氧化色
    shade = 1.0 + 0.09 * (brush - 0.5) * 2.0 + 0.03 * (brush2 - 0.5) * 2.0
    out = _shade(base, shade)                                       # 拉丝在感知域里做，才看得见
    # 氧化是「往青绿方向混色」，属于线性域的物理混合，放在 _shade 之后叠加
    out = (out * (1.0 - 0.03 * patina[..., None])
           + teal[None, None, :] * (0.03 * patina[..., None])).astype(np.float32)
    rough = np.clip(rough0 + 0.03 * (brush2 - 0.5) * 2.0 + 0.02 * (lf - 0.5),
                    rough0 - 0.04, rough0 + 0.04)
    metal = np.clip(metal0 + 0.03 * (brush - 0.5) * 2.0 - 0.05 * patina,
                    metal0 - 0.05, metal0 + 0.03)
    h = (0.25 * brush + 0.10 * brush2).astype(np.float32)
    return out, rough.astype(np.float32), metal.astype(np.float32), _normal_from_height(h, 0.18)


def _mk_lightstrip(size, hexc, rough0, metal0):
    """洗墙光带（自发光）：纯平色 + 极淡暖色渐变。"""
    U, V = _uv(size)
    base = _hex_lin(hexc)
    grad = 1.0 + 0.015 * np.cos(2 * np.pi * V)                        # 沿 V 的极淡暖色渐变
    grad = np.broadcast_to(grad, (size, size))                        # 必须显式展成 (size,size)，
    # 否则与 (1,1,3) 相乘会得到 (size,1,3)，落盘就变成 512×1 的图
    # 注意用 cos 而不是线性梯度：线性梯度在 v=0/1 处有 5% 的台阶，平铺后是一条横缝。
    grad = np.ascontiguousarray(grad, dtype=np.float32)
    out = np.clip((base[None, None, :] * grad[..., None]), 0.0, 1.0).astype(np.float32)
    return out, _fill(size, rough0), _fill(size, metal0), _flat_normal(size)


def _mk_foliage(size, hexc, rough0, metal0):
    """苍翠罗汉松针叶：多尺度团簇 + 深色缝隙（Worley F1 大值处即簇间暗缝）。"""
    base = _hex_lin(hexc)
    n = min(size, 192)                                              # 团簇尺度够用且快
    c1 = _resample_periodic(_worley(n, 4, 1001), size)              # 大团簇
    c2 = _resample_periodic(_worley(n, 9, 1009), size)              # 小团簇
    crevice = _clip01((c1 - 0.42) / 0.40) ** 1.3                    # 大团簇之间的缝
    crevice2 = _clip01((c2 - 0.45) / 0.40) ** 1.3                   # 叶簇碎缝
    clump = _clip01(1.0 - c1)                                       # 1 = 团簇中心
    lf = _fbm(size, 2, 2, 3, 1013)
    fine = _white(size, 1019)
    shade = ((1.0 + 0.16 * (clump - 0.5) * 2.0)
             * (1.0 + 0.08 * (lf - 0.5) * 2.0)
             * (1.0 + 0.06 * (fine - 0.5) * 2.0)
             * (1.0 - 0.45 * crevice)
             * (1.0 - 0.22 * crevice2))
    out = _shade(base, shade)
    out[..., 0] *= (1.0 + 0.12 * clump)                             # 叶面偏亮偏黄
    rough = np.clip(rough0 + 0.03 * (clump - 0.5) * 2.0 + 0.02 * (fine - 0.5),
                    rough0 - 0.04, rough0 + 0.04)
    h = (0.55 * clump - 0.45 * crevice - 0.20 * crevice2 + 0.05 * fine).astype(np.float32)
    return (np.clip(out, 0.0, 1.0), rough.astype(np.float32), _fill(size, metal0),
            _normal_from_height(h, 0.40))


def _mk_crimson(size, hexc, rough0, metal0):
    """故宫典雅朱砂大漆：深红底 + 极细金屑 + 轻微竖向流漆纹。"""
    base = _hex_lin(hexc)
    # 竖向流漆：pu 大 / pv 小 → 沿 U 变化快、沿 V 变化慢，形成细竖条。
    # 只用 64 个周期（不是 96/26）：太密会变成「枕席」，太疏又像幕布褶皱。
    drip = _aniso(size, 64, 5, 3, 1501)
    drip2 = _fbm(size, 3, 6, 3, 1507)                               # 漆面厚薄的大块起伏
    lf = _fbm(size, 2, 3, 3, 1511)
    # 金屑：两张白噪声取交集 → 约 0.4% 覆盖，形状是碎屑而非圆点
    flake = ((_white(size, 1513) > 0.992) & (_white(size, 1517) > 0.55)).astype(np.float32)
    flake *= 0.55 + 0.45 * _white(size, 1519)                       # 每片亮度不一
    shade = ((1.0 + 0.05 * (lf - 0.5) * 2.0)
             * (1.0 + 0.065 * (drip - 0.5) * 2.0)                   # 流漆明暗
             * (1.0 + 0.030 * (drip2 - 0.5) * 2.0))
    out = _shade(base, shade)
    # 金屑是漆面下的反光颗粒：往金色「换色」属于视觉域，不做物理混色
    gold = np.array([0.78, 0.60, 0.26], np.float32)
    s = _srgb_encode(out)
    s = s + (gold[None, None, :] - s) * (0.85 * flake)[..., None]
    out = _srgb_decode(_clip01(s))
    rough = np.clip(rough0 + 0.02 * (drip - 0.5) * 2.0 - 0.06 * flake,
                    rough0 - 0.03, rough0 + 0.03)
    metal = np.clip(metal0 + 0.60 * flake, 0.0, 1.0)                # 金屑处金属度跳高，才会闪
    h = (0.30 * drip + 0.10 * drip2 + 0.06 * flake).astype(np.float32)
    return out, rough.astype(np.float32), metal.astype(np.float32), _normal_from_height(h, 0.16)


def _mk_celadon(size, hexc, rough0, metal0):
    """宋画青绿彩画·远山：石青石绿相间的横向细带，淡、碎、有节奏。

    同一张图既做远山屏障也做彩画大面，所以**不做写实纹样**：只有 6~10px 的细带、
    偶发的浅色缝、以及沿 U 的干笔断续。远看是一层有节奏的青绿，近看是笔触。
    三条反「机械感」的措施：带子随 U 轻微起伏（不直）、缝只出现在约两成的带上、
    颜色由「带 + 大块 wash」两级噪声决定，相邻带之间不会像条形码一样跳变。
    """
    size_i = int(size)
    band_px = max(6, int(round(size_i / 128.0)))     # 1024 → 8px 一带；整数带数保证可平铺
    nb = max(size_i // band_px, 2)
    U, V = _uv(size_i)

    # 带子不是水平的：整条带沿 U 起伏（幅度 < 半个带宽，带号不会错位，仍然可平铺）。
    # 注意 V 是 0..1 的归一化坐标，必须先乘回像素尺寸，否则整张图只落在不到一个带里。
    jit = (_fbm(size_i, 2, 3, 2, 1601) - 0.5) * (band_px * 0.7)
    ph = (V * float(size_i) + jit) / float(band_px)
    k = np.floor(ph).astype(np.int32) % nb
    frac = ph - np.floor(ph)

    rng = np.random.default_rng(1613)
    tone = rng.random(nb).astype(np.float32)         # 每带明度
    hue = rng.random(nb).astype(np.float32)          # 每带偏石青(0)/偏石绿(1)
    seam_b = rng.random(nb).astype(np.float32)       # < 0.22 的带，其下边界有一道浅缝
    tone2, hue2 = tone[k], hue[k]

    # 浅色缝：到带边界的像素距离，1.1px 内渐隐；只在部分带上出现
    dist = np.minimum(frac, 1.0 - frac) * band_px
    gap = _clip01(1.0 - dist / 1.1) * (seam_b[k] < 0.22).astype(np.float32)

    # 干笔：两级笔触噪声叠加，边缘柔和地回到底色（paint=0 = 没画到）
    dry_a = _aniso(size_i, 21, 4, 3, 1621)           # 大笔触走向（沿 U 拉长）
    dry_b = _aniso(size_i, 90, 7, 2, 1627)           # 细分断口
    paint = _clip01((dry_a * 0.65 + dry_b * 0.35 - 0.30) / 0.22)
    wash = _fbm(size_i, 2, 2, 3, 1631)               # 大块色差，压掉整体规律感

    # 偏石绿 → R 升 / B 降；偏石青 → 反之（保持均值仍在声明色附近）
    ch = np.ones((size_i, size_i, 3), np.float32)
    ch[..., 0] *= 1.0 + 0.11 * (hue2 - 0.5) * 2.0
    ch[..., 2] *= 1.0 - 0.10 * (hue2 - 0.5) * 2.0
    s0 = _srgb_encode(_hex_lin(hexc))                               # (3,) 底色
    gain = (1.0 + 0.085 * (tone2 - 0.5) * 2.0
            + 0.060 * (wash - 0.5) * 2.0)[..., None]
    band = s0[None, None, :] * gain * ch
    p = paint[..., None]
    s = s0[None, None, :] * (1.0 - p) + band * p                    # 干笔处回到底色
    s = s * (1.0 + 0.26 * gap)[..., None]                           # 偶发浅缝
    out = _srgb_decode(_clip01(s))
    rough = np.clip(rough0 + 0.03 * (tone2 - 0.5) * 2.0 + 0.05 * (1.0 - paint)
                    + 0.02 * gap, rough0 - 0.04, rough0 + 0.05)
    h = (0.10 * (tone2 - 0.5) - 0.16 * gap + 0.04 * (paint - 0.5)).astype(np.float32)
    return out, rough.astype(np.float32), _fill(size_i, metal0), _normal_from_height(h, 0.18)


def _mk_cloud(size, hexc, rough0, metal0):
    """飘逸层云：只有大幅柔和低频，3~5% 起伏，没有任何高频细节。"""
    base = _hex_lin(hexc)
    lf = _fbm(size, 2, 2, 2, 1701)                                  # 2 个 octave，够软
    # #FFF8E7 的 R 已经顶到 1.0，正向提亮会直接削平（出现大片死白）；
    # 先整体压 4.5% 留出高光余量，再围绕 1.0 做 ±4.5% 起伏，均值仍在声明色 ±15 内。
    shade = 0.955 * (1.0 + 0.045 * (lf - 0.5) * 2.0)
    out = _shade(base, shade)
    h = (0.20 * lf).astype(np.float32)
    return out, _fill(size, rough0), _fill(size, metal0), _normal_from_height(h, 0.05)


def _mk_pond(size, hexc, rough0, metal0):
    """暖青灰池底微晶石：细密晶粒 + 极浅方格缝（4×4 格，约 0.6m 一格）。"""
    base = _hex_lin(hexc)
    grid = np.maximum(_lines(size, 4, 1.2, 0), _lines(size, 4, 1.2, 1))   # 4×4 格缝
    grain = _white(size, 1801)
    grain2 = _white(size, 1807)
    spark = (grain > 0.965).astype(np.float32) * (0.5 + 0.5 * grain2)      # 晶粒反光点
    lf = _fbm(size, 3, 3, 4, 1811)
    shade = ((1.0 + 0.045 * (lf - 0.5) * 2.0)
             * (1.0 + 0.055 * (grain2 - 0.5) * 2.0)
             * (1.0 + 0.20 * spark)
             * (1.0 - 0.09 * grid))                                 # 缝很浅：池底终年被水盖住
    out = _shade(base, shade)
    rough = np.clip(rough0 + 0.03 * (lf - 0.5) * 2.0 - 0.06 * spark,
                    rough0 - 0.05, rough0 + 0.05)
    h = (-0.20 * grid + 0.03 * (grain2 - 0.5)).astype(np.float32)
    return out, rough.astype(np.float32), _fill(size, metal0), _normal_from_height(h, 0.14)


def _mk_silk(size, hexc, rough0, metal0):
    """朱红月白丝光织锦：经纬交织的 2×2 织点 + 低频色差。

    织点是 1px 交替（2×2 循环），属于织物本身的高频丝光；法线只给很低的坡度，
    否则 512 尺寸下会变成一片噪点，mipmap 一缩就脏。
    """
    U, V = _uv(size)
    base = _hex_lin(hexc)
    x = np.arange(size, dtype=np.float32)[None, :]
    y = np.arange(size, dtype=np.float32)[:, None]
    weave = np.cos(np.pi * (x + y)).astype(np.float32)              # 2×2 循环织点：±1/-1
    thread = _aniso(size, 48, 2, 2, 1901)                           # 丝线粗细不匀（要疏，不能成灯芯绒）
    lf = _fbm(size, 2, 2, 3, 1907)                                  # 低频色差
    shade = ((1.0 + 0.05 * (lf - 0.5) * 2.0)
             * (1.0 + 0.050 * weave)                                # 织点明暗
             * (1.0 + 0.020 * (thread - 0.5) * 2.0))
    out = _shade(base, shade)
    rough = np.clip(rough0 + 0.02 * (thread - 0.5) * 2.0 - 0.03 * weave,
                    rough0 - 0.04, rough0 + 0.04)
    h = (0.10 * weave + 0.03 * (thread - 0.5)).astype(np.float32)
    return out, rough.astype(np.float32), _fill(size, metal0), _normal_from_height(h, 0.05)


# ============================================================ 第八期：远山法线 / 泥金
def _fault_lines(size, count, seed, slope=(0.25, 0.40), length=(80.0, 160.0),
                 width=(2.0, 4.0)):
    """随机斜向断层线（凹槽），返回 0..1 高度塌陷量，1 = 缝心。

    每条线用「点到直线距离 + 沿线方向窗口收口」算，而不是逐像素沿线采样：
    1024² 上一次算完一条线只要两个临时数组，40 条也就零点几秒；沿线采样会退化成
    数亿次运算。所有差值都先减去 size 的整数倍（环绕最小差），所以天然可平铺。
    """
    rng = np.random.default_rng(seed)
    U, V = _uv(size)
    X = U * float(size)                   # 像素坐标，方便用像素量级写长度/宽度
    Y = V * float(size)
    groove = np.zeros((size, size), np.float32)
    for _ in range(int(count)):
        s = float(rng.uniform(slope[0], slope[1])) * (1.0 if rng.random() < 0.5 else -1.0)
        L = float(rng.uniform(length[0], length[1]))
        w = float(rng.uniform(width[0], width[1]))
        x0, y0 = float(rng.uniform(0.0, size)), float(rng.uniform(0.0, size))
        nrm = float(np.hypot(1.0, s))
        dx, dy = L / nrm, L * s / nrm      # 线段方向向量（长度 = L）
        rx = X - x0
        rx -= float(size) * np.round(rx / float(size))      # 环绕最小差
        ry = Y - y0
        ry -= float(size) * np.round(ry / float(size))
        dist = np.abs(dx * ry - dy * rx) / max(L, 1e-6)      # 到直线的距离（像素）
        # 沿线位置：点积除 L² 才归一化到 -0.5..0.5（除 L 得到的是像素，会在两端直接判空）
        t = (rx * dx + ry * dy) / max(L * L, 1e-6)
        along = _clip01((0.5 - np.abs(t)) * L / max(w, 1e-6))   # 两端各用 w 像素收口
        # 剖面 = 中间一条平底沟（prof）+ 两侧微微隆起的挤压唇（rim）。
        # 只有 prof 的话在掠射光下读成一根「亮划痕」；有了唇，才看得出是岩体被错断、两盘微翘。
        prof = np.clip(1.0 - dist / (w * 0.55), 0.0, 1.0).astype(np.float32) ** 1.25
        rim = np.exp(-((dist - w * 0.85) / (w * 0.45)) ** 2).astype(np.float32)
        groove = np.maximum(groove, (prof * 1.0 - 0.32 * rim) * along)
    # 不做 clip：两侧的挤压唇是负值（在高度场里表现为隆起），裁掉就只剩一条沟
    return groove.astype(np.float32)


# 远山法线参数：key -> (种子, 层带数, 断层条数, 低频周期, 坡度)
#   层带用「V 坐标域扭曲 + 量化成台阶」生成：横向、微微起伏、平台/陡坎交替，
#   像岩层剖面；各向同性 fbm 直接量化会变成水波状团块，这就是必须做域扭曲的原因。
#   坡度 0.12~0.18：远山是背景，要"看得出骨架"而不是"碎石路面"。
_MOUNT_NORMAL = {
    "mount_near": (8101, 7, 46, 4, 0.18),
    "mount_far": (8201, 5, 30, 3, 0.14),
}


def _mount_normal(size, spec):
    """远山法线高度场：阶梯状横向层理 + 带内细暴 + 斜向断层 + 低频大起伏。"""
    seed, nband, nfault, low_p, slope = spec
    U, V = _uv(size)
    low = _fbm(size, low_p, max(low_p - 1, 1), 4, seed + 23)    # 山体大起伏（多一个 octave 撑中频）
    warp = _fbm(size, 2, 3, 2, seed + 3)                        # 层理倾斜/弯曲
    # 扭曲只给 0.10 + 0.18：再大层理就会像水波一样软，失掉「水平岩层」的读感
    vv = (V + 0.10 * (warp - 0.5) + 0.18 * (low - 0.5)).astype(np.float32)

    b = vv * np.float32(nband)
    fr = (b - np.floor(b)).astype(np.float32)      # 层带内位置 0..1（对 vv 严格周期）
    # 非对称锯齿：长缓坡上行（台地/层面）+ 陡坎下落（崖面）。
    # 对称梯形波读起来像软布褶皱；真岩层是「缓—陡」不对称的，陡坎才是骨架。
    rise = _smoothstep(0.03, 0.70, fr)
    drop = _smoothstep(0.87, 0.96, fr)
    terr = (rise - drop).astype(np.float32)

    sub = fr * np.float32(4.0)                      # 层带内的细层（暴）
    subf = (sub - np.floor(sub)).astype(np.float32)
    scour = (_smoothstep(0.00, 0.35, subf) - _smoothstep(0.55, 0.90, subf))

    # 皴纹：沿层理方向的细密短笔触 + 斜向碎纹，给台地表面一点「皮」
    cun = _aniso(size, int(nband * 7), 3, 2, seed + 51)
    cun2 = _fbm(size, 14, 5, 2, seed + 57)

    fault = _fault_lines(size, nfault, seed + 37)   # 斜向断层（凹槽 + 两侧挤压唇）
    h = (0.62 * (terr - 0.50)
         + 0.30 * (low - 0.5)
         + 0.15 * (scour - 0.35)
         + 0.12 * (cun - 0.5)
         + 0.06 * (cun2 - 0.5)
         - 0.62 * fault).astype(np.float32)
    return _normal_from_height(h, float(slope))


def _mk_mount_gold(size, hexc, rough0, metal0):
    """泥金脊线：暖金底 + 3~5px 金屑团（密度 ~1.5%）+ 极轻的纵向流痕。

    金屑用低分辨率白噪声取阈值再平滑放大成团，比逐点画圆快，且放大插值天然无缝。
    """
    base = _hex_lin(hexc)
    n4 = max(size // 4, 8)
    blk = _white(n4, 7301)
    mask = (blk > 1.0 - 0.015).astype(np.float32)             # ~1.5% 的团心
    flake = _resample_periodic(mask, size) * _resample_periodic(_white(n4, 7307), size)
    flake = _clip01(flake * 2.6)                              # 拉回 0..1，团缘柔化
    streak = _aniso(size, 40, 3, 3, 7311)                     # U 向密 = 竖向流痕
    lf = _fbm(size, 3, 2, 3, 7317)

    shade = ((1.0 + 0.05 * (lf - 0.5) * 2.0) *
             (1.0 + 0.04 * (streak - 0.5) * 2.0))
    s = _srgb_encode(np.clip(base, 0.0, 1.0)[None, None, :]) * shade[..., None]
    gold = np.array([0.92, 0.84, 0.46], np.float32)           # 高光金屑（sRGB 域）
    s = s + (gold[None, None, :] - s) * (0.55 * flake)[..., None]
    out = _match_mean(_srgb_decode(np.clip(s, 0.0, 1.0)), _srgb_mean(hexc))

    rough = np.clip(rough0 + 0.05 * (lf - 0.5) * 2.0 - 0.04 * flake,
                    0.37, 0.47)                               # 0.42 ± 0.05
    metal = np.clip(metal0 + 0.25 * flake, 0.0, 1.0)          # 金屑处更"亮"
    h = (0.06 * (streak - 0.5) + 0.05 * flake).astype(np.float32)
    return (out.astype(np.float32), rough.astype(np.float32),
            metal.astype(np.float32), _normal_from_height(h, 0.06))


# 不在 MAT_META 里的附加键：值写死在这里做兜底（MAT_META 归 lead，不动；
# 若 lead 之后把它并进 MAT_META，这里会自动让位给 MAT_META 的声明）。
_EXTRA_META = {
    "mount_gold": ("远山泥金脊线", "#C9A227", 0.42, 0.55, 512),
}
_EXTRA_BUILDERS = {"mount_gold": _mk_mount_gold}


_BUILDERS = {
    "roof_dai": _mk_roof_dai,
    "wood_dark": _mk_wood_dark,
    "wood_lite": _mk_wood_lite,
    "wall_white": _mk_wall_white,
    "stone_dark": _mk_stone_dark,
    "stone_lite": _mk_stone_lite,
    "water": _mk_water,
    "glass": _mk_glass,
    "bronze": _mk_bronze,
    "crimson": _mk_crimson,
    "celadon": _mk_celadon,
    "foliage": _mk_foliage,
    "cloud": _mk_cloud,
    "pond": _mk_pond,
    "silk": _mk_silk,
    "lightstrip": _mk_lightstrip,
    "mount_gold": _mk_mount_gold,
}


# ============================================================ 落盘 / 读 AO
def _scene_png_settings():
    """把场景的 PNG 设置钉成 8bit RGB（体积小、显存友好）。"""
    if bpy is None:
        return
    ims = bpy.context.scene.render.image_settings
    ims.file_format = "PNG"
    ims.color_mode = "RGB"
    ims.color_depth = "8"
    ims.compression = 15


def _write(name, arr, path, srgb=False):
    """arr: (H,W,3)。srgb=True 时内部做线性→sRGB 编码；否则按线性直接写。"""
    if bpy is None:
        raise RuntimeError("需要 Blender 环境（bpy）才能写 PNG")
    h, w = arr.shape[:2]
    v = _srgb_encode(arr) if srgb else np.clip(arr, 0.0, 1.0).astype(np.float32)
    q = np.empty((h, w, 4), np.float32)
    q[..., :3] = np.round(v * 255.0) / 255.0          # 量化到 8bit 网格，避免截断偏色
    q[..., 3] = 1.0
    old = bpy.data.images.get(name)
    if old is not None:
        bpy.data.images.remove(old)
    img = bpy.data.images.new(name, w, h, alpha=False, float_buffer=False)
    img.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    img.pixels.foreach_set(q.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)                        # 立即释放，避免 reload 命中旧缓存
    return path


def _read_ao(path, size):
    """读 ao_{key}.png → (size,size) 0..1；缺失时返回纯白并提示。"""
    name = os.path.basename(path)
    if bpy is None or not os.path.exists(path):
        print(f"[tex] 警告: 缺少 {name}，AO 通道用 1.0 纯白填充")
        return np.ones((size, size), np.float32)
    img = bpy.data.images.load(path, check_existing=False)
    try:
        img.colorspace_settings.name = "Non-Color"
        w, h = img.size
        buf = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(buf)
        ao = buf.reshape(h, w, 4)[..., 0].copy()
    finally:
        bpy.data.images.remove(img)
    return _resample_periodic(ao, size) if w != size else ao.astype(np.float32)


def _ensure_size(a, size, tag):
    """形状兜底：把 (h,w,...) 广播/校验成 (size,size,...)。

    历史 bug：某个 builder 因为少了一次广播，返回 (size,1,3)，落盘成 size×1 的图，
    管线不报错但贴图整条消失。这里统一在写盘前卡死尺寸。
    """
    a = np.asarray(a, np.float32)
    if a.shape[:2] == (size, size):
        return a
    try:
        b = np.broadcast_to(a, (size, size) + a.shape[2:])
    except ValueError:
        raise ValueError(f"[tex] {tag} 形状 {a.shape} 无法广播到 {size}x{size}")
    print(f"[tex] 警告: {tag} 形状 {a.shape} 已广播到 {b.shape}")
    return np.ascontiguousarray(b)


# ============================================================ 主入口
def _mk_portable_micro(size, hexc, rough0, metal0):
    """Subtle deterministic grain for constant-color craft keys; baked, not procedural at export."""
    base = _hex_lin(hexc)
    grain = _fbm(size, 24, 19, 3, 1515)
    shade = 1.0 + 0.025 * (grain - 0.5)
    color = _shade(base, shade)
    rough = np.clip(rough0 + 0.025 * (grain - 0.5), 0.02, 1.0)
    return color, rough.astype(np.float32), _fill(size, metal0), _normal_from_height(grain, 0.008)


def generate_all(tex_dir, materials=None, only=None, ao_keys=None) -> dict:
    """生成全部材质贴图，返回 {key: {basecolor, orm, normal}}。

    materials：本次场景实际用到的 key 列表（只用于提示，不影响生成范围）。
    only：可选的 key 白名单（逗号分隔字符串或可迭代），调试单材质时用。
    """
    t_all = time.time()
    os.makedirs(tex_dir, exist_ok=True)
    _scene_png_settings()

    if isinstance(only, str):
        only = [s.strip() for s in only.split(",") if s.strip()]

    # 始终出全套（reload_textures 会按 MAT_ORDER 逐个找文件）；materials 只用来
    # 提示本次场景实际用到的 key，未知 key 直接跳过。
    # mount_near / mount_far 只出法线，交给下面的专用分支，这里先排除，免得刷警告。
    allkeys = list(MAT_ORDER) + [k for k in _EXTRA_META if k not in MAT_META]
    keys = [k for k in allkeys
            if k not in _MOUNT_NORMAL and (not only or k in set(only))]
    if materials:
        extra = sorted(set(k for k in materials if k) -
                       set(MAT_ORDER) - set(_EXTRA_META))
        if extra:
            print(f"[tex] 忽略未知材质 key: {extra}")

    out = {}
    for key in keys:
        meta = MAT_META.get(key) or _EXTRA_META.get(key)
        build = _BUILDERS.get(key, _mk_portable_micro)
        if meta is None:
            raise KeyError(f"Texture material metadata missing: {key}")
        size = int(meta[4])
        t0 = time.time()
        # 粗糙度/金属度以 MAT_META 为准（ORM 的 G/B 通道会覆盖材质的 socket 值）；
        # 生成器只在声明值附近做一点起伏，别自己另写一套区间。
        base, rough, metal, nrm = build(size, meta[1], float(meta[2]), float(meta[3]))
        base = _ensure_size(base, size, f"{key}_basecolor")
        nrm = _ensure_size(nrm, size, f"{key}_normal")

        # ORM：R=AO / G=Roughness / B=Metallic（线性，不编码 sRGB）
        orm = np.empty((size, size, 3), np.float32)
        orm[..., 0] = (_read_ao(os.path.join(tex_dir, f"ao_{key}.png"), size)
                       if ao_keys is None or key in ao_keys else 1.0)
        orm[..., 1] = np.clip(rough, 0.0, 1.0)
        orm[..., 2] = np.clip(metal, 0.0, 1.0)

        p_base = _write(f"TEX_{key}_basecolor", base,
                        os.path.join(tex_dir, f"{key}_basecolor.png"), srgb=True)
        p_orm = _write(f"TEX_{key}_orm", orm,
                       os.path.join(tex_dir, f"{key}_orm.png"), srgb=False)
        p_nrm = _write(f"TEX_{key}_normal", np.clip(nrm * 0.5 + 0.5, 0.0, 1.0),
                       os.path.join(tex_dir, f"{key}_normal.png"), srgb=False)
        out[key] = {"basecolor": p_base, "orm": p_orm, "normal": p_nrm}
        print(f"[tex] {key} {size}x{size} basecolor/orm/normal 完成 {time.time() - t0:.1f}s")

    # ---- 远山：只出法线（山体本身靠自发光色阶，不需要 basecolor/orm）
    for key, spec in _MOUNT_NORMAL.items():
        if only and key not in set(only):
            continue
        size = int(MAT_META[key][4]) if key in MAT_META else 1024
        t0 = time.time()
        nrm = _ensure_size(_mount_normal(size, spec), size, f"{key}_normal")
        p_nrm = _write(f"TEX_{key}_normal", np.clip(nrm * 0.5 + 0.5, 0.0, 1.0),
                       os.path.join(tex_dir, f"{key}_normal.png"), srgb=False)
        out[key] = {"normal": p_nrm}
        print(f"[tex] {key} {size}x{size} normal 完成 {time.time() - t0:.1f}s")

    print(f"[tex] 全部完成 {len(out)} 个材质 / 共 {time.time() - t_all:.1f}s -> {tex_dir}")
    return out


if __name__ == "__main__":
    # 可直接在 Blender 里单跑：
    #   blender -b --factory-startup -P textures.py -- --tex <dir> [--only wood_dark,cloud]
    import argparse
    import sys

    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(description="程序化 PBR 贴图生成")
    ap.add_argument("--tex", default=r"D:\Design\textures", help="输出目录")
    ap.add_argument("--only", default="", help="只生成这些 key（逗号分隔）")
    ns = ap.parse_args(argv)
    generate_all(ns.tex, only=ns.only or None)
