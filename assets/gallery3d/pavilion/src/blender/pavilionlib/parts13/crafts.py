# -*- coding: utf-8 -*-
"""v15 室内非遗工序陈列（五馆 Hero Craft Vignette）—— 只做「工序现场」，不做展柜。

口径（与 parts13/halls.py 对齐，全部读 halls/dim13 的既有坐标，不另造一套）：
  * 建筑局部坐标：原点在馆中心，门在 y=-6 一侧（镂金坊门在 y=-3.26 侧）；
    世界矩阵 M = Translation((cx,cy,0)) @ Rotation(rot,4,'Z')，几何按局部建，_emit 里乘 M，
    与 halls.py 第 228 行 _emit() 的写法逐字一致。
  * 室内平面：配殿 |x|,|y| < 5.55（墙内表面 5.72）；镂金坊 |x|<5.60, |y|<3.10。
  * 柱网：配殿柱在 x,y ∈ {-6.0,-2.6,2.6,6.0}；中央 |x|,|y|<2.4 无柱 → 主案落中央。
  * 二层阁（songhua/qinghua）：一层净高 3.60，楼板底 4.10；本文件一层陈列一律 <3.4m。
    楼梯占局部 x[-4.60,0.90] × y[3.20,5.45]，博古架/晾坯架因此只上后墙东半段。
  * 镂金坊层高 3.40（天花底 3.50），屏风高 2.15，窗洞在 ±X 墙 z[2.20,3.35] → 不遮挡。

接触口径（保证 overlap13 判据下「跨部件 0 对 / 同部件共面 0 对」）：
  器具落面 LIFT=1.5mm、落地 FLIFT=2.5mm、叠放 SEAM=3.5mm 的亚毫米缝。
  同一对象内部的榫卯/嵌固允许互插（审计按对象成对比较，不比较对象内部）。
  器具使用 MAT_META 中登记的材质。

命名：cr_<hall>_<item>；cat = "detail" / "exhibit"；coll_path = ("展陈", "<馆名>")。
出口：HERO_DESKS（每馆主案一条，供 exhibits.py 替换旧案台锚点）/ hero_desks()。
"""
from __future__ import annotations

import math

import bmesh
from mathutils import Matrix, Vector
from mathutils.geometry import delaunay_2d_cdt

from .. import mesh_util as mu

TAU = math.tau

LIFT = 0.0015          # 器具落案面的缝
FLIFT = 0.0025         # 家具落地坪的缝
SEAM = 0.0035          # 叠放件之间的缝（> overlap13 共面判据 2.5mm）
PSEAM = 0.0002         # 同一 bmesh 内的纸张叠层微缝（审计只比对象间，可用亚毫米）
DENS = 2.0             # 回转体分段加密系数（tri 预算 8~14 万）

# ---------------------------------------------------------------- 五馆坐标契约
HALLS = {
    "zhuxianzhen": dict(cn="刊木堂", cx=-32.0, cy=-30.0, rot=90.0,
                        floor=0.20, clear=5.50, hx=5.55, hy=5.55),
    "songhua": dict(cn="澄怀轩", cx=-32.0, cy=-12.0, rot=90.0,
                    floor=0.20, clear=3.60, hx=5.55, hy=5.55),
    "bianxiu": dict(cn="针经阁", cx=32.0, cy=-30.0, rot=-90.0,
                    floor=0.20, clear=5.50, hx=5.55, hy=5.55),
    "qinghua": dict(cn="素肌堂", cx=32.0, cy=-12.0, rot=-90.0,
                    floor=0.20, clear=3.60, hx=5.55, hy=5.55),
    "jianzhi": dict(cn="镂金坊", cx=-20.0, cy=-42.0, rot=0.0,
                    floor=0.15, clear=3.40, hx=5.60, hy=3.10),
}

ORDER = ("zhuxianzhen", "songhua", "bianxiu", "qinghua", "jianzhi")

# ---------------------------------------------------------------- 主案锚点
HERO_DESKS = [
    dict(key="desk_zhuxianzhen_hero", hall="zhuxianzhen", cn="刊木堂·主案",
         x=-32.0, y=-30.0, rot=90.0, w=2.60, d=1.10, top_z=1.06),
    dict(key="desk_songhua_hero", hall="songhua", cn="澄怀轩·主案",
         x=-32.0, y=-12.0, rot=90.0, w=3.60, d=1.20, top_z=1.08),
    dict(key="desk_bianxiu_hero", hall="bianxiu", cn="针经阁·主案",
         x=32.0, y=-30.0, rot=-90.0, w=1.40, d=0.62, top_z=1.25),
    dict(key="desk_qinghua_hero", hall="qinghua", cn="素肌堂·主案",
         x=32.0, y=-12.0, rot=-90.0, w=2.60, d=1.10, top_z=1.06),
    dict(key="desk_jianzhi_hero", hall="jianzhi", cn="镂金坊·主案",
         x=-20.0, y=-42.0, rot=0.0, w=2.20, d=1.00, top_z=0.93),
]


def hero_desks():
    return HERO_DESKS


# ============================================================================
# 基础工具（与 halls.py 同口径）
# ============================================================================
def _v(bm, x, y, z):
    return bm.verts.new(Vector((x, y, z)))


def _f(bm, face):
    try:
        return bm.faces.new(face)
    except ValueError:
        return None


def _box(bm, x0, x1, y0, y1, z0, z1):
    return mu.box_mm(bm, min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1),
                     min(z0, z1), max(z0, z1))


def _cube8(bm, x0, x1, y0, y1, z0, z1):
    """8 顶点 6 面盒（外向绕序），返回 8 个顶点。"""
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    z0, z1 = min(z0, z1), max(z0, z1)
    vs = [_v(bm, x0, y0, z0), _v(bm, x1, y0, z0),
          _v(bm, x1, y1, z0), _v(bm, x0, y1, z0),
          _v(bm, x0, y0, z1), _v(bm, x1, y0, z1),
          _v(bm, x1, y1, z1), _v(bm, x0, y1, z1)]
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
              (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        _f(bm, [vs[i] for i in q])
    return vs


def _boxb(bm, x0, x1, y0, y1, z0, z1, bev=0.004, seg=1):
    """倒角盒：真实小倒角，clamp_overlap 防炸。"""
    vs = _cube8(bm, x0, x1, y0, y1, z0, z1)
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    dz = abs(z1 - z0)
    b = min(bev, 0.32 * min(dx, dy, dz))
    if b > 1.0e-5:
        es = set()
        for v in vs:
            es.update(v.link_edges)
        mu.bevel_edges(bm, list(es), b, seg)
    return vs


def _post(bm, cx, cy, z0, z1, s0, s1=None):
    """收分方柱（柱脚 s0 → 柱头 s1）。"""
    s1 = s0 if s1 is None else s1
    a = [_v(bm, cx - s0 / 2, cy - s0 / 2, z0), _v(bm, cx + s0 / 2, cy - s0 / 2, z0),
         _v(bm, cx + s0 / 2, cy + s0 / 2, z0), _v(bm, cx - s0 / 2, cy + s0 / 2, z0)]
    b = [_v(bm, cx - s1 / 2, cy - s1 / 2, z1), _v(bm, cx + s1 / 2, cy - s1 / 2, z1),
         _v(bm, cx + s1 / 2, cy + s1 / 2, z1), _v(bm, cx - s1 / 2, cy + s1 / 2, z1)]
    for i in range(4):
        j = (i + 1) % 4
        _f(bm, [a[i], a[j], b[j], b[i]])
    _f(bm, a[::-1])
    _f(bm, b)
    return a + b


def _bar(bm, p0, p1, w, h):
    """沿 p0-p1 的方枨（w 水平宽、h 竖向高），两端封口。"""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    if d.length < 1e-9:
        return
    d.normalize()
    up = Vector((0.0, 0.0, 1.0))
    s = d.cross(up)
    if s.length < 1e-6:
        s = Vector((1.0, 0.0, 0.0))
    s.normalize()
    u = s.cross(d).normalized()
    corners = []
    for p in (p0, p1):
        for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            corners.append(p + s * (a * w * 0.5) + u * (b * h * 0.5))
    idx = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
           (2, 3, 7, 6), (3, 0, 4, 7)]
    vs = [_v(bm, c.x, c.y, c.z) for c in corners]
    for q in idx:
        _f(bm, [vs[i] for i in q])


def _lathe(bm, prof, cx, cy, z0=None, seg=16, cap=True):
    """回转体：prof=[(r,z)...] 开放剖面（z 为绝对高度；给了 z0 则视为相对偏移），
    自下而上、外壁→口沿→内壁；两端封口。"""
    if z0:
        prof = [(r, z0 + z) for (r, z) in prof]
    seg = max(8, int(seg * DENS))
    rings = mu.revolve(bm, prof, (cx, cy, 0.0), segments=seg, close_profile=False)
    if cap and rings:
        mu.cap_ring(bm, [meridian[0] for meridian in rings], True)
        mu.cap_ring(bm, [meridian[-1] for meridian in rings])
    return rings


def _lathe_closed(bm, loop, cx, cy, z0=None, seg=16):
    """闭合剖面回转（环形件：绣绷箍、镇尺卷云环、箍）—— 剖面自带绝对 z。"""
    if z0:
        loop = [(r, z0 + z) for (r, z) in loop]
    return mu.revolve(bm, loop, (cx, cy, 0.0),
                      segments=max(8, int(seg * DENS)), close_profile=True)


def _disc(bm, cx, cy, z0, r, t=0.004, seg=20):
    return _lathe(bm, [(0.0008, z0), (r, z0), (r, z0 + t), (0.0008, z0 + t)],
                  cx, cy, seg=seg)


def _annulus(bm, cx, cy, z0, z1, r0, r1, seg=16):
    return _lathe_closed(bm, [(r0, z0), (r1, z0), (r1, z1), (r0, z1)],
                         cx, cy, seg=seg)


def _tube(bm, pts, r, seg=5, caps=True, r_end=None):
    mu.swept_tube(bm, [Vector(p) for p in pts], r, segments=seg, caps=caps,
                  radius_end=r_end)


def _torus_y(bm, cx, cy, cz, R, r, seg=24, rseg=6):
    """轴向沿 Y 的圆环面（竹箍/绷圈）：闭合无缝，无退化面。"""
    rings = []
    for i in range(seg):
        a = TAU * i / seg
        ca, sa = math.cos(a), math.sin(a)
        row = []
        for j in range(rseg):
            b = TAU * j / rseg
            rr = R + math.cos(b) * r
            row.append(_v(bm, cx + ca * rr, cy + math.sin(b) * r, cz + sa * rr))
        rings.append(row)
    for i in range(seg):
        a_row = rings[i]
        b_row = rings[(i + 1) % seg]
        for j in range(rseg):
            j2 = (j + 1) % rseg
            _f(bm, [a_row[j], b_row[j], b_row[j2], a_row[j2]])
    return rings


def _panel(bm, fn, nu, nv, off):
    """双面薄板：fn(u,v)->Vector 为正面点，off 为向厚度方向的偏移向量。"""
    off = Vector(off)
    top = [[None] * (nv + 1) for _ in range(nu + 1)]
    bot = [[None] * (nv + 1) for _ in range(nu + 1)]
    for i in range(nu + 1):
        u = i / nu
        for j in range(nv + 1):
            p = fn(u, j / nv)
            top[i][j] = _v(bm, p.x, p.y, p.z)
            q = p + off
            bot[i][j] = _v(bm, q.x, q.y, q.z)
    for i in range(nu):
        for j in range(nv):
            _f(bm, [top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]])
            _f(bm, [bot[i][j], bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j]])
    for j in range(nv):
        _f(bm, [top[0][j], top[0][j + 1], bot[0][j + 1], bot[0][j]])
        _f(bm, [top[nu][j], bot[nu][j], bot[nu][j + 1], top[nu][j + 1]])
    for i in range(nu):
        _f(bm, [top[i][0], bot[i][0], bot[i + 1][0], top[i + 1][0]])
        _f(bm, [top[i][nv], top[i + 1][nv], bot[i + 1][nv], bot[i][nv]])
    return top, bot


def _apron(bm, axis, a0, a1, at, z_top, hgt, thick, n=14, rise=0.85):
    """壸门牙板：上缘平、下缘起拱（rise 越大中段挖得越深），下沿起珠线脚。"""
    lo, hi = at - thick * 0.5, at + thick * 0.5
    arch = min(0.62, 0.62 * rise)
    n = max(8, int(n * DENS))
    front, back, ftop, btop = [], [], [], []
    zbs = []
    for i in range(n + 1):
        t = i / n
        a = a0 + (a1 - a0) * t
        zb = z_top - hgt * (1.0 - arch * math.sin(math.pi * t) ** 1.5)
        zb = min(zb, z_top - 0.006)
        zbs.append(zb)
        if axis == "x":
            front.append(_v(bm, a, lo, zb))
            back.append(_v(bm, a, hi, zb))
            ftop.append(_v(bm, a, lo, z_top))
            btop.append(_v(bm, a, hi, z_top))
        else:
            front.append(_v(bm, lo, a, zb))
            back.append(_v(bm, hi, a, zb))
            ftop.append(_v(bm, lo, a, z_top))
            btop.append(_v(bm, hi, a, z_top))
    for i in range(n):
        _f(bm, [front[i], front[i + 1], ftop[i + 1], ftop[i]])
        _f(bm, [back[i], btop[i], btop[i + 1], back[i + 1]])
        _f(bm, [front[i], back[i], back[i + 1], front[i + 1]])
        _f(bm, [ftop[i], ftop[i + 1], btop[i + 1], btop[i]])
    _f(bm, [front[0], ftop[0], btop[0], back[0]])
    _f(bm, [front[n], back[n], btop[n], ftop[n]])
    # 下沿起珠（两面半圆线脚，沿起拱曲线）
    if hgt >= 0.05:
        for face, sg in ((lo, -1.0), (hi, 1.0)):
            path = []
            for i in range(n + 1):
                t = i / n
                a = a0 + (a1 - a0) * t
                zz = zbs[i] + 0.0042
                if axis == "x":
                    path.append((a, face + sg * 0.0030, zz))
                else:
                    path.append((face + sg * 0.0030, a, zz))
            _tube(bm, path, 0.0040, 5)


def _emit(C, bm, M, name, cat, coll, cn, mat="wood_dark", **kw):
    """局部 bmesh → 世界对象（照抄 halls.py 第 228 行的模式）。"""
    if len(bm.verts) == 0:
        bm.free()
        return None
    if M is not None:
        for v in bm.verts:
            v.co = M @ v.co
    if name.endswith(("_block_main","_inkstone","_blue_sketch")):
        # CDT intersections can make micrometre-wide slivers. Collapse their
        # shortest edges here so the global clean never punches holes in stock.
        for _ in range(12):
            tiny=[f for f in bm.faces if f.calc_area() <=1.1e-10]
            if not tiny:
                break
            chosen,used=[],set()
            for face in tiny:
                edge=min(face.edges,key=lambda e:e.calc_length())
                if not any(v in used for v in edge.verts):
                    chosen.append(edge)
                    used.update(edge.verts)
            bmesh.ops.collapse(bm,edges=chosen)
    mu.recalc_normals(bm)
    return C.bm_obj(bm, name, cat, coll, cn=cn, mat=mat, **kw)


def _M(H):
    return (Matrix.Translation((H["cx"], H["cy"], 0.0))
            @ Matrix.Rotation(math.radians(H["rot"]), 4, "Z"))


# ============================================================================
# 通用器型（回转剖面：r 归一 0..1，z 归一 0..1）
# ============================================================================
PROF_MEIPING = [
    (0.26, 0.000), (0.52, 0.000), (0.58, 0.060), (0.55, 0.190),
    (0.66, 0.340), (0.97, 0.470), (1.00, 0.630), (0.90, 0.760),
    (0.62, 0.840), (0.40, 0.900), (0.34, 0.940), (0.34, 1.000),
    (0.25, 1.000), (0.25, 0.940), (0.30, 0.900), (0.52, 0.840),
    (0.80, 0.760), (0.90, 0.630), (0.87, 0.470), (0.56, 0.340),
    (0.45, 0.190), (0.43, 0.100), (0.26, 0.100),
]
PROF_YUHUCHUN = [
    (0.28, 0.000), (0.55, 0.000), (0.60, 0.050), (0.52, 0.160),
    (0.56, 0.280), (0.80, 0.450), (1.00, 0.580), (0.95, 0.720),
    (0.62, 0.840), (0.40, 0.920), (0.36, 1.000),
    (0.26, 1.000), (0.26, 0.920), (0.34, 0.840), (0.56, 0.720),
    (0.86, 0.580), (0.72, 0.450), (0.48, 0.280), (0.44, 0.160),
    (0.46, 0.060), (0.28, 0.060),
]
PROF_BOWL = [
    (0.30, 0.000), (0.55, 0.000), (0.62, 0.100), (0.80, 0.450),
    (0.96, 0.850), (1.00, 1.000),
    (0.90, 1.000), (0.86, 0.850), (0.70, 0.450), (0.52, 0.140),
    (0.30, 0.120),
]
PROF_JAR = [
    (0.30, 0.000), (0.52, 0.000), (0.58, 0.050), (0.60, 0.120),
    (0.86, 0.280), (1.00, 0.480), (0.96, 0.680), (0.80, 0.820),
    (0.62, 0.900), (0.58, 0.940), (0.58, 1.000),
    (0.50, 1.000), (0.50, 0.920), (0.56, 0.860), (0.74, 0.800),
    (0.90, 0.660), (0.94, 0.480), (0.80, 0.280), (0.54, 0.140),
    (0.36, 0.100), (0.30, 0.100),
]
PROF_JAR_LID = [
    (0.30, 0.000), (0.52, 0.000), (0.54, 0.030), (0.44, 0.070),
    (0.26, 0.100), (0.10, 0.130), (0.06, 0.170), (0.05, 0.200),
    (0.060, 0.200), (0.075, 0.160), (0.150, 0.120), (0.330, 0.086),
    (0.430, 0.050), (0.400, 0.020), (0.300, 0.014),
]
PROF_WAN = [
    (0.30, 0.000), (0.42, 0.000), (0.44, 0.058), (0.50, 0.231),
    (0.80, 0.635), (0.97, 0.904), (1.00, 1.000),
    (0.93, 1.000), (0.90, 0.904), (0.74, 0.635), (0.46, 0.269),
    (0.30, 0.212),
]


def _shape(prof, R, H, z0=0.0):
    return [(r * R, z0 + z * H) for (r, z) in prof]


def _vessel(bm, prof, cx, cy, z0, R, H, seg=16):
    return _lathe(bm, _shape(prof, R, H), cx, cy, z0, seg=seg)


def _crystal(bm, cx, cy, z0, r, h, seed=0.0, n=4):
    """矿物晶簇：n 根六棱柱 + 锥顶，略有倾角与高差。"""
    for k in range(n):
        ang = seed + TAU * k / n * 1.7
        rr = r * (0.42 if k else 0.0)
        px = cx + math.cos(ang) * rr
        py = cy + math.sin(ang) * rr
        hh = h * (0.55 + 0.45 * ((k * 37 + 11) % 7) / 6.0)
        rad = r * (0.55 if k else 0.78)
        tilt = 0.16 * math.sin(ang * 1.7 + 1.0)
        prof = []
        m = 6
        for i in range(m):
            a = TAU * i / m
            prof.append((math.cos(a) * rad, math.sin(a) * rad))
        base = []
        for (u, w) in prof:
            base.append(_v(bm, px + u, py + w, z0))
        mid = []
        for (u, w) in prof:
            mid.append(_v(bm, px + u + tilt * hh * 0.4, py + w * 0.92,
                          z0 + hh * 0.78))
        tip = _v(bm, px + tilt * hh * 0.9, py - rad * 0.25, z0 + hh)
        for i in range(m):
            j = (i + 1) % m
            _f(bm, [base[i], base[j], mid[j], mid[i]])
            _f(bm, [mid[i], mid[j], tip])
        _f(bm, base[::-1])


def _turned(bm, cx, cy, z0, z1, r0=0.036, r1=0.052, seg=14, n=9):
    """车木旋纹立柱：沿 z 起伏的鼓棱剖面（绣架立柱/桌腿）。"""
    prof = []
    for i in range(n + 1):
        t = i / n
        z = z0 + (z1 - z0) * t
        r = r1 * (0.80 + 0.20 * math.sin(math.pi * t)) \
            - 0.010 * math.sin(t * math.pi * 5.0) ** 2
        prof.append((max(0.012, r), z))
    for i in range(n, -1, -1):
        t = i / n
        z = z0 + (z1 - z0) * t
        r = (r1 * 0.80 - 0.004) * (0.9 + 0.1 * math.sin(math.pi * t))
        prof.append((max(0.008, r), z))
    # 首尾相接形成闭合剖面环 → 用闭合回转
    return _lathe_closed(bm, prof, cx, cy, 0.0, seg=seg)


# ============================================================================
# 1 刊木堂：朱仙镇木版年画（雕版 → 套色 → 晾画）
# ============================================================================
def _dedupe(pts, eps=2.0e-4):
    """去掉相邻重合点（避免零面积面与退化三角）。"""
    out = []
    for p in pts:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > eps:
            out.append((p[0], p[1]))
    return out


def _cr(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    x = 0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t
               + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
               + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
    y = 0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t
               + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
               + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
    return (x, y)


def _bez(pts, n=3, closed=False):
    """Catmull-Rom 平滑：每段加密 n 个点（雕刻曲线 / 刀痕 / 飘带）。"""
    ps = _dedupe(pts)
    m = len(ps)
    if m < 3 or n < 1:
        return ps
    out = []
    if closed:
        for i in range(m):
            p0, p1 = ps[(i - 1) % m], ps[i]
            p2, p3 = ps[(i + 1) % m], ps[(i + 2) % m]
            for k in range(n):
                out.append(_cr(p0, p1, p2, p3, k / float(n)))
        return out
    ext = [ps[0]] + ps + [ps[-1]]
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(n):
            out.append(_cr(p0, p1, p2, p3, k / float(n)))
    out.append(ps[-1])
    return out


def _arc(cx, cy, rx, ry, a0, a1, n=10):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / float(n)),
             cy + ry * math.sin(a0 + (a1 - a0) * i / float(n)))
            for i in range(n + 1)]


def _ell(cx, cy, rx, ry, n=18):
    return [(cx + rx * math.cos(TAU * i / float(n)),
             cy + ry * math.sin(TAU * i / float(n))) for i in range(n)]


def _wavy(p0, p1, amp, waves, n=14):
    """两点之间的波动曲线（飘带 / 衣褶 / 纸边纤维）。"""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy)
    if L < 1e-9:
        return [p0, p1]
    nx, ny = -dy / L, dx / L
    out = []
    for i in range(n + 1):
        t = i / float(n)
        s = amp * math.sin(TAU * waves * t) * math.sin(math.pi * t)
        out.append((p0[0] + dx * t + nx * s, p0[1] + dy * t + ny * s))
    return out


def _carved_face(bm, bounds, zbase, depth, strokes, cuts=True, ink=False):
    """Triangulate all cutter and ridge outlines together into one continuous skin.

    A stroke stores its centreline, top width, height from the groove floor and
    closure. Intersecting strokes share CDT vertices. Coordinates are in metres.
    """
    x0, x1, y0, y1 = bounds
    positions = []
    edges = []
    bins = {}
    cell = 0.012
    slope = math.tan(math.radians(70))

    def trace(points, closed=True):
        first = len(positions)
        positions.extend(Vector(p) for p in points)
        edges.extend((i, i + 1) for i in range(first, len(positions) - 1))
        if closed:
            edges.append((len(positions) - 1, first))

    perimeter = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    trace(perimeter)
    for path, width, height, closed in strokes:
        pts = _dedupe(path)
        if len(pts) < 2:
            continue
        if closed and math.dist(pts[0], pts[-1]) < 1e-6:
            pts.pop()
        half = width / 2
        foot = half + height / slope
        shoulder = foot + 0.0009
        limit = shoulder + depth / slope
        radii = [half, foot, shoulder, limit] if cuts else [half, foot]
        for i, p in enumerate(pts if closed else pts[:-1]):
            q = pts[(i + 1) % len(pts)]
            dx, dy = q[0] - p[0], q[1] - p[1]
            length2 = dx * dx + dy * dy
            if length2 < 1e-14:
                continue
            record = (p[0], p[1], dx, dy, length2, half, height, shoulder, limit)
            for ix in range(math.floor((min(p[0], q[0]) - limit) / cell),
                            math.floor((max(p[0], q[0]) + limit) / cell) + 1):
                for iy in range(math.floor((min(p[1], q[1]) - limit) / cell),
                                math.floor((max(p[1], q[1]) + limit) / cell) + 1):
                    bins.setdefault((ix, iy), []).append(record)
        normals = []
        for i in range(len(pts)):
            prev = pts[i-1 if i or closed else 0]
            nxt = pts[(i+1) % len(pts) if closed else min(i+1, len(pts)-1)]
            d = (Vector(nxt) - Vector(prev)).normalized()
            normals.append(Vector((-d.y, d.x)))
        for radius in dict.fromkeys(radii):
            sides = [[Vector(p) + sign * radius * n for p, n in zip(pts, normals)]
                     for sign in (1, -1)]
            if closed:
                for side in sides:
                    trace(side)
            else:
                # Semicircular ends keep isolated eye dots and short strokes rounded.
                def round_end(k, sign):
                    n = normals[k] * sign
                    start = math.atan2(n.y, n.x)
                    return [Vector(pts[k]) + radius * Vector((math.cos(start - j * math.pi / 4),
                                                              math.sin(start - j * math.pi / 4)))
                            for j in range(1, 4)]
                trace(sides[0] + round_end(-1, 1) + sides[1][::-1] + round_end(0, -1))

    xy, _, triangles, *_ = delaunay_2d_cdt(positions, edges, [], 0, 1.5e-5, False)
    vs = []
    levels = []
    for x, y in xy:
        if x < x0 - 1e-6 or x > x1 + 1e-6 or y < y0 - 1e-6 or y > y1 + 1e-6:
            raise ValueError("carving extends outside stock")
        floor = depth if cuts else 0.
        ridge = 0.
        for px, py, dx, dy, length2, half, h, shoulder, limit in bins.get(
                (math.floor(x / cell), math.floor(y / cell)), ()):
            t = max(0., min(1., ((x - px) * dx + (y - py) * dy) / length2))
            r = math.hypot(x - px - t * dx, y - py - t * dy)
            if r <= limit:
                floor = min(floor, max(0., r - shoulder) * slope)
                ridge = max(ridge, h - max(0., r - half) * slope)
        level = max(floor, ridge)
        vs.append(_v(bm, x, y, zbase + level))
        levels.append(level)
    for tri in triangles:
        f = bm.faces.new([vs[i] for i in tri])
        if ink and min(levels[i] for i in tri) >= 0.003495:
            f.material_index = 1
    return [vs[min(range(len(xy)), key=lambda i: (xy[i] - Vector(corner)).length_squared)]
            for corner in perimeter]


def _fill2(bm, pts, z0, z1):
    """平面轮廓挤出，形成封闭薄片。"""
    ps = _dedupe(list(pts))
    if len(ps) > 2 and math.hypot(ps[0][0] - ps[-1][0], ps[0][1] - ps[-1][1]) < 1e-6:
        ps = ps[:-1]
    if len(ps) < 3 or abs(z1 - z0) < 1e-6:
        return
    r0 = [_v(bm, p[0], p[1], z0) for p in ps]
    r1 = [_v(bm, p[0], p[1], z1) for p in ps]
    mu.bridge_rings(bm, r0, r1, closed=True)
    mu.cap_ring(bm, r0, flip=True)
    mu.cap_ring(bm, r1, flip=False)


def _bored_plate(bm, bounds, holes, z0, z1):
    """Extrude a continuous rectangle with polygonal through-bores."""
    x0,x1,y0,y1=bounds
    outlines=[[(x0,y0),(x1,y0),(x1,y1),(x0,y1)]]+holes
    coordinates, edges=[],[]
    for outline in outlines:
        start=len(coordinates)
        coordinates.extend(Vector(p) for p in outline)
        edges.extend((start+i,start+(i+1)%len(outline)) for i in range(len(outline)))
    pts,_,triangles,*_=delaunay_2d_cdt(coordinates,edges,[],0,1e-8,False)
    floor=[_v(bm,p.x,p.y,z0) for p in pts]
    top=[_v(bm,p.x,p.y,z1) for p in pts]
    boundary={}
    for ids in triangles:
        x,y=tuple(sum(pts[i][k] for i in ids)/3 for k in (0,1))
        if any(all((q[0]-p[0])*(y-p[1])-(q[1]-p[1])*(x-p[0])>=0.
                   for p,q in zip(loop,loop[1:]+loop[:1])) for loop in holes):
            continue
        bm.faces.new([top[i] for i in ids])
        bm.faces.new([floor[i] for i in reversed(ids)])
        for i,j in zip(ids,ids[1:]+ids[:1]):
            key=tuple(sorted((i,j)))
            if key in boundary:
                del boundary[key]
            else:
                boundary[key]=(i,j)
    for i,j in boundary.values():
        bm.faces.new((floor[i],floor[j],top[j],top[i]))


def _sleeve_y(bm,cx,cz,y0,y1,inner,outer,n=32):
    rings=[]
    for y,r in ((y0,inner),(y0,outer),(y1,outer),(y1,inner)):
        rings.append([_v(bm,cx+r*math.cos(TAU*k/n),y,cz+r*math.sin(TAU*k/n)) for k in range(n)])
    for j in range(4):
        mu.bridge_rings(bm,rings[j],rings[(j+1)%4],closed=True)


def _fg_menmen(strokes, u0, v0, S=0.55, mirror=1.0, knobs=6):
    """朱仙镇门神立像（标准坐标 u∈±0.24、v∈[-0.30,0.46]）：
    秦琼金锏 6 节 / 尉迟恭竹节钢鞭 13 节，mirror 控制执兵之手。"""
    def T(p):
        return (u0 + mirror * p[0] * S, v0 + p[1] * S)

    def ink(pts, w=0.0022, h=0.0022, closed=False, sm=2):
        pp = [T(p) for p in pts]
        if closed or len(pp) >= 3:
            pp = _bez(pp, sm, closed)
        strokes.append((pp, w, 0.0035, closed))

    def rel(pts, h1=0.0018, sm=2):
        strokes.append((_bez([T(p) for p in pts], sm, True), h1, 0.0035, True))

    def dot(cu, cv, rx, ry, h1=0.0024):
        rel(_ell(cu, cv, rx, ry, 10), h1)

    # ---------------- 靴（圆头厚底）
    for sg in (-1.0, 1.0):
        rel([(sg * 0.020, -0.292), (sg * 0.094, -0.292), (sg * 0.102, -0.258),
             (sg * 0.014, -0.258)], 0.0015)
        ink([(sg * 0.014, -0.258), (sg * 0.102, -0.258), (sg * 0.110, -0.298),
             (sg * 0.020, -0.298)], 0.0016, closed=True)
        ink([(sg * 0.020, -0.298), (sg * 0.110, -0.298)], 0.0018)   # 靴底
        ink([(sg * 0.018, -0.274), (sg * 0.098, -0.274)], 0.0011)   # 靴口

    # ---------------- 袍身（含躯干外形 / 下摆 / 五道褶）
    robe = [(-0.052, 0.300), (-0.100, 0.150), (-0.132, -0.020), (-0.156, -0.130),
            (-0.170, -0.238), (0.0, -0.252), (0.170, -0.238), (0.156, -0.130),
            (0.132, -0.020), (0.100, 0.150), (0.052, 0.300)]
    ink(robe, 0.0022, closed=True)
    ink([(-0.160, -0.238), (0.0, -0.250), (0.160, -0.238)], 0.0017)   # 下摆
    for k in (-2, -1, 0, 1, 2):
        ink(_arc(k * 0.062, -0.244, 0.024, 0.011, math.pi, 2 * math.pi, 6), 0.0012)
    for k in range(5):                                                # 袍褶
        uu = -0.096 + k * 0.048
        ink([(uu, 0.040), (uu * 1.30, -0.120), (uu * 1.56, -0.232)], 0.0015)
    ink([(-0.052, 0.300), (0.0, 0.246), (0.052, 0.300)], 0.0017)      # 领口

    # ---------------- 腰带 + 带扣
    ink([(-0.072, 0.056), (0.072, 0.056)], 0.0020)
    ink([(-0.072, 0.078), (0.072, 0.078)], 0.0018)
    rel([(-0.020, 0.050), (0.020, 0.050), (0.020, 0.084), (-0.020, 0.084)], 0.0022)
    ink([(-0.014, 0.067), (0.014, 0.067)], 0.0012)

    # ---------------- 锁子甲（四排 × 七片鳞，落在躯干内）
    for r in range(4):
        vv = 0.108 + r * 0.038
        for k in range(7):
            cu = -0.084 + k * 0.028 + (0.014 if r % 2 else 0.0)
            ink(_arc(cu, vv, 0.015, 0.012, 0.0, math.pi, 5), 0.0013)

    # ---------------- 护心镜（圆镜 + 内环 + 镜钮 + 四朵云）
    rel(_ell(0.0, 0.214, 0.038, 0.035, 12), 0.0024)
    ink(_ell(0.0, 0.214, 0.038, 0.035, 12), 0.0016, closed=True)
    ink(_ell(0.0, 0.214, 0.021, 0.019, 10), 0.0011, closed=True)
    dot(0.0, 0.214, 0.008, 0.007, 0.0028)
    for k in range(4):
        a = k * math.pi / 2.0 + math.pi / 4.0
        ink(_arc(0.026 * math.cos(a), 0.214 + 0.024 * math.sin(a),
                 0.008, 0.006, a - 0.9, a + 0.9, 4), 0.0010)

    # ---------------- 肩甲
    for sg in (-1.0, 1.0):
        ink([(sg * 0.060, 0.300), (sg * 0.120, 0.292), (sg * 0.164, 0.250),
             (sg * 0.150, 0.212), (sg * 0.100, 0.226), (sg * 0.062, 0.256)],
            0.0017, closed=True)
        for k in range(3):
            ink([(sg * (0.072 + k * 0.030), 0.288 - k * 0.010),
                 (sg * (0.126 + k * 0.024), 0.256 - k * 0.014),
                 (sg * (0.126 + k * 0.022), 0.232 - k * 0.012)], 0.0012)

    # ---------------- 双臂（宽阳线读作袍袖）+ 袖箍 + 手
    for sg in (-1.0, 1.0):
        ink([(sg * 0.092, 0.262), (sg * 0.130, 0.196), (sg * 0.150, 0.132)],
            0.013, h=0.0026)
        ink([(sg * 0.124, 0.202), (sg * 0.140, 0.186)], 0.0017)
        dot(sg * 0.156, 0.118, 0.015, 0.013, 0.0024)

    # ---------------- 脸 / 五官
    ink(_ell(0.0, 0.352, 0.058, 0.084, 14), 0.0018, closed=True)
    rel(_ell(0.0, 0.348, 0.052, 0.076, 14), 0.0011)
    for sg in (-1.0, 1.0):
        ink([(sg * 0.010, 0.394), (sg * 0.038, 0.406), (sg * 0.056, 0.392)], 0.0020)
        rel(_ell(sg * 0.030, 0.376, 0.016, 0.010, 10), 0.0016)        # 眼窝
        dot(sg * 0.030, 0.376, 0.008, 0.007, 0.0026)                  # 眼珠
        ink([(sg * 0.005, 0.372), (sg * 0.004, 0.350)], 0.0012)       # 鼻梁
        ink([(sg * 0.016, 0.342), (sg * 0.034, 0.336)], 0.0013)       # 鼻翼
        ink([(sg * 0.014, 0.322), (sg * 0.038, 0.312)], 0.0018)       # 髭
        ink([(sg * 0.010, 0.302), (sg * 0.028, 0.250), (sg * 0.034, 0.206)], 0.0016)
        ink([(sg * 0.058, 0.356), (sg * 0.066, 0.340), (sg * 0.060, 0.324)], 0.0012)
    ink([(0.0, 0.324), (0.0, 0.302)], 0.0016)
    ink([(-0.022, 0.302), (0.022, 0.302)], 0.0013)                    # 上唇
    ink([(-0.014, 0.292), (0.014, 0.292)], 0.0011)                    # 下唇
    for sg in (-1.0, 1.0):                                            # 中髯（两股收尖）
        ink([(sg * 0.004, 0.292), (sg * 0.008, 0.252), (sg * 0.010, 0.216)], 0.0013)

    # ---------------- 凤翅盔
    ink([(-0.066, 0.396), (-0.062, 0.436), (-0.038, 0.460), (0.0, 0.466),
         (0.038, 0.460), (0.062, 0.436), (0.066, 0.396)], 0.0019)
    ink([(-0.068, 0.400), (0.068, 0.400)], 0.0017)                    # 盔檐
    ink([(-0.052, 0.428), (0.0, 0.442), (0.052, 0.428)], 0.0013)
    for sg in (-1.0, 1.0):                                            # 双凤翅
        wing = [(sg * 0.056, 0.394), (sg * 0.090, 0.412), (sg * 0.120, 0.446),
                (sg * 0.132, 0.470), (sg * 0.116, 0.452), (sg * 0.100, 0.424),
                (sg * 0.108, 0.414), (sg * 0.086, 0.398), (sg * 0.070, 0.384),
                (sg * 0.058, 0.380)]
        rel(wing, 0.0020)
        ink(wing, 0.0015, closed=True)
        for k in range(3):
            ink([(sg * (0.068 + k * 0.008), 0.396 + k * 0.006),
                 (sg * (0.096 + k * 0.010), 0.418 + k * 0.012),
                 (sg * (0.118 + k * 0.006), 0.444 + k * 0.012)], 0.0011)
    for k in range(3):                                                # 盔缨三缕
        ink([(0.0, 0.466), (0.010 - k * 0.010, 0.498 - k * 0.004)], 0.0017)

    # ---------------- 兵器（金锏 / 竹节钢鞭）
    hx = 0.176
    hw = 0.026
    ink([(hx, 0.092), (hx, 0.386), (hx + hw, 0.386), (hx + hw, 0.092)],
        0.0016, closed=True)
    ink([(hx, 0.386), (hx + hw * 0.5, 0.418), (hx + hw, 0.386)],
        0.0016, closed=True)                                          # 锏锋
    ink([(hx, 0.098), (hx + hw, 0.098)], 0.0017)                      # 锏把箍
    for k in range(knobs):
        vv = 0.132 + k * (0.230 / float(max(1, knobs - 1)))
        ink([(hx + 0.003, vv), (hx + hw - 0.003, vv)], 0.0011)


def _zhuxianzhen(C, H):
    coll = C.coll("展陈", H["cn"])
    M = _M(H)
    zf = H["floor"]
    P = "cr_zhuxianzhen_"
    cn = H["cn"]

    # ---------------- 正中雕印主画案 w2.60×d1.10×h0.86
    bm = mu.new_bm()
    w, d, h = 2.60, 1.10, 0.86
    zt = zf + h
    zb = zf + FLIFT
    _boxb(bm, -w / 2, w / 2, -d / 2, d / 2, zt - 0.056, zt, 0.007, 2)
    _boxb(bm, -w / 2 + 0.007, w / 2 - 0.007, -d / 2 + 0.007, d / 2 - 0.007,
          zt - 0.072, zt - 0.056, 0.0025, 1)
    ins = 0.085
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            lx = sx * (w / 2 - ins)
            ly = sy * (d / 2 - ins)
            _post(bm, lx, ly, zb, zt - 0.056, 0.098, 0.078)
            _boxb(bm, lx - 0.082, lx + 0.082, ly - 0.082, ly + 0.082,
                  zb, zb + 0.030, 0.004, 1)
    za = zt - 0.072
    hh = 0.135
    _apron(bm, "x", -w / 2 + ins, w / 2 - ins, -d / 2 + 0.012, za, hh, 0.018, 18, 0.90)
    _apron(bm, "x", -w / 2 + ins, w / 2 - ins, d / 2 - 0.012, za, hh, 0.018, 18, 0.90)
    _apron(bm, "y", -d / 2 + ins, d / 2 - ins, -w / 2 + 0.012, za, hh, 0.018, 8, 0.55)
    _apron(bm, "y", -d / 2 + ins, d / 2 - ins, w / 2 - 0.012, za, hh, 0.018, 8, 0.55)
    for sy in (-1.0, 1.0):
        ly = sy * (d / 2 - ins)
        _bar(bm, (-w / 2 + ins, ly, zb + 0.20), (w / 2 - ins, ly, zb + 0.20),
             0.028, 0.042)
    for sx in (-1.0, 1.0):
        lx = sx * (w / 2 - ins)
        _bar(bm, (lx, -d / 2 + ins, zb + 0.34), (lx, d / 2 - ins, zb + 0.34),
             0.024, 0.036)
    _emit(C, bm, M, P + "desk", "exhibit", coll,
          cn=cn + "·红木雕印主画案", mat="wood_dark")

    # ---------------- 案面：宣纸垫 + 墨线主版（v15：双门神 / 70° 阳线 / 台阶凹框 / 十字榫）
    zpaper = zt + LIFT
    bm = mu.new_bm()
    _boxb(bm, -0.46, 0.46, -0.23, 0.35, zpaper, zpaper + 0.0040, 0.0006, 1)
    _boxb(bm, -0.462, 0.462, -0.232, 0.352, zpaper + 0.0040 + SEAM,
          zpaper + 0.0080 + SEAM, 0.0006, 1)
    _emit(C, bm, M, P + "paper_pad", "detail", coll,
          cn=cn + "·垫版宣纸（两层）", mat="paper_xuan")

    zblk = zpaper + 0.0080 + 2 * SEAM
    bw, bd, bh = 0.86, 0.52, 0.045
    cy0 = 0.06
    x0, x1 = -bw / 2.0, bw / 2.0
    y0, y1 = cy0 - bd / 2.0, cy0 + bd / 2.0
    zt1 = zblk + bh - 0.010          # 第一台阶（外框面）
    zt2 = zt1 + 0.006                # 第二台阶（中框面）
    ztop = zblk + bh                 # 版心面

    bm = mu.new_bm()
    strokes = []
    scale = 0.50
    ybase = cy0 - 0.05
    for side, knobs in ((-1., 6), (1., 13)):
        _fg_menmen(strokes, side * 0.185, ybase, S=scale, mirror=side, knobs=knobs)
    carved = _carved_face(bm, (x0+.044, x1-.044, y0+.044, y1-.044),
                          ztop-.002, .002, strokes, ink=True)
    outer = None
    for inset, zz in ((0., zblk), (0., zt1), (.022, zt1),
                      (.022, zt2), (.044, zt2)):
        ring = [_v(bm, xx, yy, zz) for xx, yy in
                ((x0+inset,y0+inset),(x1-inset,y0+inset),
                 (x1-inset,y1-inset),(x0+inset,y1-inset))]
        if outer is None:
            bm.faces.new(ring[::-1])
        else:
            mu.bridge_rings(bm, outer, ring, closed=True)
        outer = ring
    mu.bridge_rings(bm, outer, carved, closed=True)
    for sx in (-1.0, 1.0):                                           # 十字套印榫
        bx = sx * bw / 2.0
        _box(bm, min(bx, bx + sx * 0.016), max(bx, bx + sx * 0.016),
             cy0 - 0.007, cy0 + 0.007, zblk + 0.002, zt1 - 0.004)
        _box(bm, min(bx, bx + sx * 0.016), max(bx, bx + sx * 0.016),
             cy0 - 0.024, cy0 + 0.024, zt1 - 0.026, zt1 - 0.012)

    _emit(C, bm, M, P + "block_main", "exhibit", coll,
          cn=cn + "·杜梨木主版（双门神·局部凹槽与保留阳线）", mat=("wood_lite", "lacquer"))

    # ---------------- 左侧三块套色版（朱砂 / 槐黄 / 石绿），阶梯叠放
    cols = (("crimson", "朱砂红"), ("mount_gold", "槐黄"), ("celadon", "石绿"))
    bxc, byc = -0.90, 0.26
    for k, (mat, ccn) in enumerate(cols):
        bm = mu.new_bm()
        ox = bxc + k * 0.055
        oy = byc - k * 0.030
        z0 = zt + LIFT + k * (0.040 + SEAM)
        cw, cd, ch = 0.62, 0.42, 0.040
        _boxb(bm, ox - cw / 2, ox + cw / 2, oy - cd / 2, oy + cd / 2, z0, z0 + ch,
              0.0032, 1)
        # 两个对位套印榫口：一侧凹口（两颊）+ 一侧凸榫
        for sy in (-1.0, 1.0):
            ey = oy + sy * cd / 2
            _box(bm, ox - 0.022, ox + 0.022,
                 min(ey, ey + sy * 0.016), max(ey, ey + sy * 0.016),
                 z0 + ch - 0.012, z0 + ch + 0.0015)
            for sgn in (-1.0, 1.0):
                _box(bm, min(ox + sgn * 0.031, ox + sgn * 0.045),
                     max(ox + sgn * 0.031, ox + sgn * 0.045),
                     ey - 0.014, ey + 0.014, z0 + ch - 0.012, z0 + ch + 0.0015)
        _emit(C, bm, M, P + "color_block_%d" % (k + 1), "detail", coll,
              cn=cn + "·套色版·" + ccn, mat=mat)

    # ---------------- 右侧：马鬃棕刷 / 马尾圆盘擦子
    bm = mu.new_bm()
    bx, by = 0.66, 0.34
    _boxb(bm, bx - 0.115, bx + 0.115, by - 0.045, by + 0.045, zt + LIFT,
          zt + LIFT + 0.048, 0.006, 2)
    # 刷毛成束：23 束，长短错落
    for k in range(11):
        for j in range(2):
            hx = bx - 0.098 + k * 0.0196
            hy = by - 0.020 + j * 0.040
            ln = 0.085 + 0.012 * math.sin(k * 1.7 + j)
            _box(bm, hx - 0.0085, hx + 0.0085, hy - 0.0085, hy + 0.0085,
                 zt + LIFT + 0.042, zt + LIFT + 0.042 + ln)
    _emit(C, bm, M, P + "brush_ma", "detail", coll,
          cn=cn + "·马鬃棕刷（刷柄+成束刷毛）", mat="bamboo")

    bm = mu.new_bm()
    rx, ry = 1.00, 0.29
    _disc(bm, rx, ry, zt + LIFT, 0.078, 0.014, 24)
    _annulus(bm, rx, ry, zt + LIFT + 0.014, zt + LIFT + 0.030, 0.020, 0.062, 20)
    # 马尾盘面（密排圆环）
    for k in range(3):
        _annulus(bm, rx, ry, zt + LIFT + 0.030 + k * 0.006,
                 zt + LIFT + 0.036 + k * 0.006, 0.030 + k * 0.010, 0.040 + k * 0.010, 20)
    _boxb(bm, rx - 0.022, rx + 0.022, ry + 0.060, ry + 0.115, zt + LIFT + 0.006,
          zt + LIFT + 0.026, 0.004, 1)
    _emit(C, bm, M, P + "rubber", "detail", coll,
          cn=cn + "·圆盘马尾擦子", mat="silk_raw")

    # ---------------- 一对纯铜压纸镇尺（卷云线脚）
    bm = mu.new_bm()
    for k, px in enumerate((0.55, 1.00)):
        py = -0.36
        _boxb(bm, px - 0.16, px + 0.16, py - 0.024, py + 0.024, zt + LIFT,
              zt + LIFT + 0.017, 0.005, 2)
        # 两端卷云：小环 + 短条
        for sx in (-1.0, 1.0):
            ex = px + sx * 0.160
            _annulus(bm, ex, py, zt + LIFT + 0.004, zt + LIFT + 0.015, 0.008, 0.019, 12)
            _box(bm, min(ex, ex + sx * 0.022), max(ex, ex + sx * 0.022),
                 py - 0.010, py + 0.010, zt + LIFT + 0.005, zt + LIFT + 0.014)
    _emit(C, bm, M, P + "paperweights", "detail", coll,
          cn=cn + "·纯铜压纸镇尺（卷云线脚）", mat="brass")

    # ---------------- 粗陶朱砂颜料大碗（口 0.26，浆面低于碗沿 0.02）
    bm = mu.new_bm()
    vx, vy = -0.62, -0.36
    _lathe(bm, [(0.055, 0.000), (0.098, 0.000), (0.108, 0.012), (0.120, 0.050),
                (0.130, 0.086), (0.130, 0.100), (0.118, 0.100), (0.116, 0.086),
                (0.106, 0.050), (0.092, 0.020), (0.055, 0.020)],
           vx, vy, zt + LIFT, seg=22)
    _emit(C, bm, M, P + "ink_bowl", "detail", coll,
          cn=cn + "·粗陶朱砂大碗", mat="clay_wet")
    bm = mu.new_bm()
    _lathe(bm,[(.0549,.0201),(.0919,.0201),(.1059,.050),(.1159,.086),
               (.11615,.0878),(.001,.0878)],vx,vy,zt+LIFT,22)
    _emit(C, bm, M, P + "ink_surface", "detail", coll,
          cn=cn + "·朱砂浆面", mat="crimson")

    # ---------------- 五孔调色瓷碟
    bm = mu.new_bm()
    px, py = -1.10, -0.36
    _lathe(bm, [(0.020, 0.000), (0.085, 0.000), (0.100, 0.008), (0.104, 0.020),
                (0.100, 0.030), (0.092, 0.026), (0.080, 0.014), (0.020, 0.010)],
           px, py, zt + LIFT, seg=20)
    for k in range(5):
        a = TAU * k / 5
        _annulus(bm, px + math.cos(a) * 0.058, py + math.sin(a) * 0.058,
                 zt + LIFT + 0.024, zt + LIFT + 0.031, 0.013, 0.020, 12)
    _emit(C, bm, M, P + "palette", "detail", coll,
          cn=cn + "·五孔调色瓷碟", mat="bisque")
    paints = (("crimson", (0, 1, 3)), ("celadon", (2,)), ("mount_gold", (4,)))
    for mat, idxs in paints:
        bm = mu.new_bm()
        for k in idxs:
            a = TAU * k / 5
            _disc(bm, px + math.cos(a) * 0.058, py + math.sin(a) * 0.058,
                  zt + LIFT + 0.01355, 0.0125, 0.01095, 14)
        _emit(C, bm, M, P + "paint_" + mat, "detail", coll,
              cn=cn + "·调色浆·" + mat, mat=mat)

    # ---------------- 后墙木架 + 两张半湿门神年画
    bx0, bx1, by = -1.95, 1.15, 5.34
    bm = mu.new_bm()
    for sx in (bx0, bx1):
        _post(bm, sx, by, zf + FLIFT, 2.55, 0.062, 0.052)
        _boxb(bm, sx - 0.075, sx + 0.075, by - 0.16, by + 0.09, zf + FLIFT,
              zf + FLIFT + 0.055, 0.006, 1)
    _bar(bm, (bx0, by, 2.50), (bx1, by, 2.50), 0.075, 0.085)
    _bar(bm, (bx0, by, 1.50), (bx1, by, 1.50), 0.055, 0.065)
    _bar(bm, (bx0, by, 0.60), (bx1, by, 0.60), 0.050, 0.060)
    # 斜撑
    _bar(bm, (bx0, by + 0.02, 2.42), (bx0 + 0.42, by + 0.02, 0.66), 0.030, 0.034)
    _bar(bm, (bx1, by + 0.02, 2.42), (bx1 - 0.42, by + 0.02, 0.66), 0.030, 0.034)
    _emit(C, bm, M, P + "hang_rack", "exhibit", coll,
          cn=cn + "·后墙晾画木架", mat="wood_dark")

    for k, hx in enumerate((-1.28, 0.30)):
        pw, ph = 0.46, 0.72
        z0 = 1.62
        yface = by - 0.062 - 0.010

        def fn(u, v, hx=hx, pw=pw, ph=ph, z0=z0, yface=yface):
            x = hx + (u - 0.5) * pw
            z = z0 + v * ph
            # 半湿纸面：横向微鼓 + 下缘略垂 + 长波起伏
            sag = 0.012 * (v ** 2.4)
            y = (yface - 0.0030 * math.sin(math.pi * u) * math.sin(math.pi * v)
                 - 0.0018 * math.sin(TAU * u * 2.2) * v
                 + 0.0020 * math.sin(TAU * v * 1.5) * math.sin(math.pi * u))
            return Vector((x, y, z - sag))

        bm = mu.new_bm()
        _panel(bm, fn, 14, 16, (0.0, 0.0035, 0.0))
        _emit(C, bm, M, P + "print_%d" % (k + 1), "exhibit", coll,
              cn=cn + "·半湿门神年画（第%d张）" % (k + 1), mat="paper_xuan")

    bm = mu.new_bm()
    for hx in (-1.28, 0.30):
        for zz in (1.60, 2.33):
            _boxb(bm, hx - 0.245, hx + 0.245, by - 0.086, by - 0.056,
                  zz, zz + 0.022, 0.003, 1)
    _emit(C, bm, M, P + "print_bars", "detail", coll,
          cn=cn + "·细木压条（四根）", mat="wood_dark")

    # ---------------- 纸料台（后墙东段）+ 连史纸垛 + 刻刀架
    bm = mu.new_bm()
    tx, ty = 2.72, 4.86
    tw, td, th = 1.45, 0.55, 0.72
    tz = zf + th
    _boxb(bm, tx - tw / 2, tx + tw / 2, ty - td / 2, ty + td / 2, tz - 0.042, tz,
          0.005, 2)
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            _post(bm, tx + sx * (tw / 2 - 0.07), ty + sy * (td / 2 - 0.07),
                  zf + FLIFT, tz - 0.042, 0.062, 0.052)
    _bar(bm, (tx - tw / 2 + 0.07, ty - td / 2 + 0.07, zf + 0.20),
         (tx + tw / 2 - 0.07, ty - td / 2 + 0.07, zf + 0.20), 0.024, 0.034)
    _bar(bm, (tx - tw / 2 + 0.07, ty + td / 2 - 0.07, zf + 0.20),
         (tx + tw / 2 - 0.07, ty + td / 2 - 0.07, zf + 0.20), 0.024, 0.034)
    _emit(C, bm, M, P + "side_table", "exhibit", coll,
          cn=cn + "·纸料台", mat="wood_dark")

    # 连史纸垛：36 束×2 张错边叠放，侧边可见毛边分层（≈0.22m 厚，60+ 张的读感）
    bm = mu.new_bm()
    sx0, sy0 = 2.44, 4.84
    zc = tz + LIFT
    for k in range(36):
        dz = 0.0048 + 0.0007 * ((k * 7) % 5)
        ox = 0.0018 * math.sin(k * 2.1)
        oy = 0.0014 * math.cos(k * 1.7)
        _boxb(bm, sx0 - 0.275 + ox, sx0 + 0.275 + ox,
              sy0 - 0.19 + oy, sy0 + 0.19 + oy, zc, zc + dz, 0.0008, 1)
        zc += dz + PSEAM
    _emit(C, bm, M, P + "paper_stack", "detail", coll,
          cn=cn + "·连史纸垛（层叠毛边）", mat="paper_xuan")

    # 雕版刀具架 + 5 把刻刀
    bm = mu.new_bm()
    kx = 3.30
    bores=[_ell(kx-.085+i*.052,ty-.02+.02*(i%2),.013,.013,16) for i in range(5)]
    _bored_plate(bm,(kx-.14,kx+.14,ty-.07,ty+.07),bores,tz+LIFT+.003,tz+LIFT+.055)
    _box(bm,kx-.14,kx+.14,ty-.07,ty+.07,tz+LIFT,tz+LIFT+.003)
    _emit(C, bm, M, P + "knife_rack", "detail", coll,
          cn=cn + "·雕版刀具架", mat="wood_lite")

    bm_h = mu.new_bm()
    bm_b = mu.new_bm()
    kinds = ("伐刀", "支刀", "挑刀", "跟刀", "净缝刀")
    for i in range(5):
        ox = kx - 0.085 + i * 0.052
        oy = ty - 0.02 + 0.02 * (i % 2)
        z0 = tz + LIFT + 0.00310
        # 木柄（微斜）+ 铜箍
        _tube(bm_h, [(ox, oy, z0), (ox, oy, z0 + 0.115)],
              0.0125, 8)
        # The ferrule has a square tang aperture and a circular outer wall.
        _bored_plate(bm_h,(ox-.0145,ox+.0145,oy-.0145,oy+.0145),
                     [[(ox-.0065,oy-.0025),(ox+.0065,oy-.0025),
                       (ox+.0065,oy+.0025),(ox-.0065,oy+.0025)]],
                     z0+.115,z0+.124)
        tipx,tipy=ox,oy
        _boxb(bm_b, tipx - 0.0055, tipx + 0.0055, tipy - 0.0018, tipy + 0.0018,
              z0 + 0.1151, z0 + 0.230, 0.0012, 1)
        _boxb(bm_b, tipx - 0.0045, tipx + 0.0045, tipy - 0.0012, tipy + 0.0012,
              z0 + 0.230, z0 + 0.246, 0.0009, 1)
        _box(bm_b, tipx - 0.0060, tipx + 0.0060, tipy - 0.0020, tipy + 0.0020,
             z0 + 0.244, z0 + 0.250)
    _emit(C, bm_h, M, P + "knife_handles", "detail", coll,
          cn=cn + "·刻刀木柄（5 把：" + "/".join(kinds) + "）", mat="wood_dark")
    _emit(C, bm_b, M, P + "knife_blades", "detail", coll,
          cn=cn + "·刻刀斜刃刀身", mat="steel")


# ============================================================================
# 器型辅助：剖面查表 / 器表缠枝 / yz 平面扁条（剪纸）
# ============================================================================
MEI_ZR = [(0.00, 0.26), (0.06, 0.58), (0.19, 0.55), (0.34, 0.66),
          (0.47, 0.97), (0.63, 1.00), (0.76, 0.90), (0.84, 0.62),
          (0.90, 0.40), (1.00, 0.34)]
YHC_ZR = [(0.00, 0.28), (0.05, 0.60), (0.16, 0.52), (0.28, 0.56),
          (0.45, 0.80), (0.58, 1.00), (0.72, 0.95), (0.84, 0.62),
          (0.92, 0.40), (1.00, 0.36)]
WAN_ZR = [(0.00, 0.42), (0.06, 0.45), (0.24, 0.56), (0.63, 0.86),
          (0.90, 0.98), (1.00, 1.00)]


def _zr(tab, zn):
    """按高度线性插值取外壁半径系数。"""
    if zn <= tab[0][0]:
        return tab[0][1]
    for i in range(len(tab) - 1):
        a, b = tab[i], tab[i + 1]
        if zn <= b[0]:
            f = (zn - a[0]) / max(1e-9, (b[0] - a[0]))
            return a[1] + (b[1] - a[1]) * f
    return tab[-1][1]


def _paint_lathe(bm, outlines, profile, cx, cy, zbase, radius, height, sides, offset):
    """Clip pigment outlines against each real lathe facet in an unwrapped chart."""
    tab=[]
    for r,z in profile:
        if tab and z<tab[-1][0]:
            break
        if tab and z==tab[-1][0]:
            tab[-1]=(z,max(tab[-1][1],r))
        else:
            tab.append((z,r))
    vertices, edges, contours, regions = [], [], [], []
    period=TAU*radius
    def add(p):
        vertices.append(Vector(p))
        return len(vertices)-1
    for i in range(sides+1):
        x=period*i/sides
        edges.append((add((x,0)),add((x,height))))
    for z,r in tab:
        edges.append((add((0,z*height)),add((period,z*height))))
    for outline in outlines:
        for shift in (-TAU,0,TAU):
            poly=[((ang+shift)*radius,u*height) for ang,u in outline]
            if max(x for x,y in poly)<0 or min(x for x,y in poly)>period:
                continue
            contours.append([add(p) for p in poly])
            regions.append((min(x for x,y in poly),max(x for x,y in poly),
                            min(y for x,y in poly),max(y for x,y in poly),poly))
    def inked(x,y):
        for xmin,xmax,ymin,ymax,poly in regions:
            if xmin<=x<=xmax and ymin<=y<=ymax:
                inside=False
                for j,(xa,ya) in enumerate(poly):
                    xb,yb=poly[j-1]
                    if (ya>y)!=(yb>y) and x<(xb-xa)*(y-ya)/(yb-ya)+xa:
                        inside=not inside
                if inside:
                    return True
        return False
    xy,_,tris,*_=delaunay_2d_cdt(vertices,edges,contours,0,1e-6,False)
    created={}
    sector=TAU/sides
    for ids in tris:
        x=sum(xy[k].x for k in ids)/3
        y=sum(xy[k].y for k in ids)/3
        if not 0 <= x <= period or not inked(x,y):
            continue
        face=[]
        for k in ids:
            if k not in created:
                x,z=xy[k]
                ang=x/radius
                cosine=math.cos(ang%sector-sector/2)
                r=_zr(tab,z/height)*radius*math.cos(sector/2)/cosine+offset
                created[k]=_v(bm,cx+r*math.cos(ang),cy+r*math.sin(ang),zbase+z)
            face.append(created[k])
        bm.faces.new(face)


def _bar2(bm, p0, p1, wid, x0, x1):
    """yz 平面扁条（剪纸/镂空用）：从 p0 到 p1，宽 wid，厚 x0..x1。"""
    y0, z0 = p0
    y1, z1 = p1
    dy, dz = y1 - y0, z1 - z0
    L = math.hypot(dy, dz)
    if L < 1e-6:
        return
    ny, nz = -dz / L * wid * 0.5, dy / L * wid * 0.5
    xs = (min(x0, x1), max(x0, x1))
    cs = []
    for x in xs:
        for p in ((y0 + ny, z0 + nz), (y1 + ny, z1 + nz),
                  (y1 - ny, z1 - nz), (y0 - ny, z0 - nz)):
            cs.append((x, p[0], p[1]))
    vs = [_v(bm, c[0], c[1], c[2]) for c in cs]
    for q in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
              (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        _f(bm, [vs[i] for i in q])


def _pen(bm, x, y0, y1, zc, r, seg=8, br=0.008):
    """毛笔：笔杆 + 竹节 + 毫尖（沿 y 轴平放）。"""
    _tube(bm, [(x, y0, zc), (x, y1, zc)], r, seg)
    _tube(bm, [(x, y0 - br * 1.9, zc - 0.0004), (x, y0, zc)], br * 0.55,
          seg, r_end=0.0012)


# ============================================================================
# 2 澄怀轩：宋画青绿山水（长卷 → 研墨 → 设色）
# ============================================================================
def _songhua(C, H):
    coll = C.coll("展陈", H["cn"])
    M = _M(H)
    zf = H["floor"]
    P = "cr_songhua_"
    cn = H["cn"]

    # ---------------- 巨型紫檀通长画案 w3.60×d1.20×h0.88
    w, d, h = 3.60, 1.20, 0.88
    zt = zf + h
    bw, bd = 3.24, 0.84
    xo, yo = -0.09, 0.02
    bx0, bx1 = xo - bw / 2, xo + bw / 2
    by0, by1 = yo - bd / 2, yo + bd / 2
    bm = mu.new_bm()
    _boxb(bm, bx0, bx1, by0, by1, zt - 0.062, zt, 0.008, 2)
    _boxb(bm, bx0 + 0.008, bx1 - 0.008, by0 + 0.008, by1 - 0.008,
          zt - 0.082, zt - 0.062, 0.0028, 1)
    ins = 0.135
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            lx = (bx1 - ins) if sx > 0 else (bx0 + ins)
            ly = (by1 - ins) if sy > 0 else (by0 + ins)
            _post(bm, lx, ly, zf + FLIFT, zt - 0.062, 0.112, 0.088)
            _boxb(bm, lx - 0.092, lx + 0.092, ly - 0.092, ly + 0.092,
                  zf + FLIFT, zf + FLIFT + 0.032, 0.004, 1)
    za = zt - 0.082
    _apron(bm, "x", bx0 + ins, bx1 - ins, by0 + 0.012, za, 0.165, 0.020, 22, 0.92)
    _apron(bm, "x", bx0 + ins, bx1 - ins, by1 - 0.012, za, 0.165, 0.020, 22, 0.92)
    _apron(bm, "y", by0 + ins, by1 - ins, bx0 + 0.012, za, 0.150, 0.020, 10, 0.70)
    _apron(bm, "y", by0 + ins, by1 - ins, bx1 - 0.012, za, 0.150, 0.020, 10, 0.70)
    # 托泥 + 底枨
    for sy in (-1.0, 1.0):
        ly = (by1 - ins) if sy > 0 else (by0 + ins)
        _bar(bm, (bx0 + ins, ly, zf + FLIFT + 0.075), (bx1 - ins, ly, zf + FLIFT + 0.075),
             0.052, 0.048)
    for sx in (-1.0, 1.0):
        lx = (bx1 - ins) if sx > 0 else (bx0 + ins)
        _bar(bm, (lx, by0 + ins, zf + FLIFT + 0.075), (lx, by1 - ins, zf + FLIFT + 0.075),
             0.046, 0.042)
    _emit(C, bm, M, P + "desk", "exhibit", coll,
          cn=cn + "·紫檀通长画案（壸门牙板）", mat="wood_dark")

    # ---------------- 《千里江山图》绢本长卷
    zd = zt + LIFT
    th = 0.0022
    seg = ((-1.100, -0.8812), (-0.8800, 0.5188), (0.5200, 0.8300))
    amp = (0.0005, 0.0012, 0.0009)
    mats = ("silk", "stone_lite", "stone_lite")
    ys = (-0.130, 0.190)
    names = ("scroll_head", "scroll_body", "scroll_tail")
    for k, (sx0, sx1) in enumerate(seg):
        def fn(u, v, sx0=sx0, sx1=sx1, a=amp[k]):
            return Vector((sx0 + (sx1 - sx0) * u, ys[0] + (ys[1] - ys[0]) * v,
                           zd + a * math.sin(math.pi * u) * math.sin(math.pi * v * 1.6)))
        bm = mu.new_bm()
        _panel(bm, fn, 22, 6, (0.0, 0.0, th))
        _emit(C, bm, M, P + names[k], "exhibit", coll,
              cn=cn + ("·宋绫天头" if k == 0 else ("·青绿画心（绢本）" if k == 1 else "·拖尾跋文")),
              mat=mats[k])

    # 右侧自然卷起的卷筒（与绢面相切）
    bm = mu.new_bm()
    _sleeve_y(bm,.885,zd+.058,ys[0]-.004,ys[0]+.334,.0122,.058,32)
    _emit(C,bm,M,P+"scroll_roll","exhibit",coll,cn=cn+"·右侧中空绢卷",mat="stone_lite")
    bm=mu.new_bm()
    mu.cylinder(bm,(.885,ys[0]-.016,zd+.058),.012,.362,segments=32,axis="Y")
    _emit(C, bm, M, P + "scroll_axle", "detail", coll,
          cn=cn + "·卷轴轴头（两端）", mat="wood_dark")

    # 青绿山体：立起的实心剪影板（远峰石青在后、近峰石绿在前），板厚 6mm，
    # 板前另加三层错落矿物色块（各倾 3°，侧视不穿薄板）；非贴图、非单一方块
    ztop = zd + th
    z0 = ztop + 0.0016          # 山脚离绢面 1.6mm（不穿绢，也不与绢面共面）

    def _sil(bm_, ridge, y0, y1, tilt=0.0):
        """XZ 平面上的山形多边形沿 y 挤出（板厚 6mm）→ 立起的实心山板。"""
        na = [_v(bm_, x, y0, z) for (x, z) in ridge]
        nb = [_v(bm_, x, y1, z) for (x, z) in ridge]
        m = len(ridge)
        for i in range(m):
            j = (i + 1) % m
            mu.face(bm_, [na[i], na[j], nb[j], nb[i]])
        mu.cap_ring(bm_, na, flip=True)
        mu.cap_ring(bm_, nb, flip=False)
        if tilt:
            for vv_ in na + nb:
                vv_.co.y += tilt * (vv_.co.z - z0)
        return bm_

    # 远峰（石青，mount_far）：峰高 0.010~0.071，y=0.100..0.114
    far = [(-0.855, 0.004), (-0.802, 0.041), (-0.754, 0.016), (-0.702, 0.059),
           (-0.650, 0.021), (-0.598, 0.071), (-0.542, 0.025), (-0.488, 0.053),
           (-0.432, 0.019), (-0.378, 0.067), (-0.320, 0.023), (-0.264, 0.059),
           (-0.206, 0.017), (-0.150, 0.047), (-0.092, 0.015), (-0.034, 0.063),
           (0.024, 0.019), (0.080, 0.051), (0.138, 0.017), (0.194, 0.045),
           (0.250, 0.015), (0.308, 0.057), (0.366, 0.021), (0.424, 0.049),
           (0.495, 0.010)]
    far = _bez(far, 4)          # 峰脊平滑：折线锯齿 → 起伏山峦
    far = [(x, zz * (0.34 + 0.66 * (0.5 + 0.5 * math.sin(x * 6.1 + 0.6))))
           for (x, zz) in far]   # 高程包络：成组峰群 + 低鞍部
    bm = _sil(mu.new_bm(), [(x, z0 + zz) for (x, zz) in far] +
              [(0.495, z0), (-0.855, z0)], 0.100, 0.106)
    _emit(C, bm, M, P + "mountains_far", "detail", coll,
          cn=cn + "·青绿山体（远峰石青）", mat="azurite")
    # 近峰（石绿，celadon）：峰高 0.008~0.043，y=0.006..0.020
    near = [(-0.858, 0.003), (-0.796, 0.026), (-0.742, 0.010), (-0.688, 0.038),
            (-0.632, 0.012), (-0.578, 0.043), (-0.520, 0.014), (-0.464, 0.032),
            (-0.408, 0.010), (-0.352, 0.040), (-0.296, 0.013), (-0.240, 0.034),
            (-0.184, 0.009), (-0.128, 0.028), (-0.072, 0.010), (-0.014, 0.037),
            (0.044, 0.012), (0.100, 0.030), (0.158, 0.010), (0.214, 0.026),
            (0.272, 0.009), (0.330, 0.033), (0.388, 0.012), (0.446, 0.028),
            (0.512, 0.008)]
    near = _bez(near, 4)
    near = [(x, zz * (0.40 + 0.60 * (0.5 + 0.5 * math.sin(x * 5.3 - 1.1))))
            for (x, zz) in near]
    bm = _sil(mu.new_bm(), [(x, z0 + zz) for (x, zz) in near] +
              [(0.512, z0), (-0.858, z0)], 0.006, 0.012)
    _emit(C, bm, M, P + "mountains_near", "detail", coll,
          cn=cn + "·青绿山体（近峰石绿）", mat="malachite")

    # 板前三层错落矿物色块（石青深/石绿/赭石），平行略倾并在前后层间留出净距
    for (ridge, y0_, y1_, tl, mat_, cn_, sc_, zb_, k0, k1) in (
            (far, 0.0020, 0.0026, -0.020, "mount_far", "石青深色块（后层）",
             0.55, 0.0000, 0, 0),
            (near, -0.0002, 0.0004, -0.020, "malachite", "石绿色块（中层）",
             0.34, 0.0000, 2, 2),
            (far, -0.0024, -0.0018, -0.020, "mineral_ochre", "赭石底色块（前层）",
             0.18, 0.0000, 4, 4)):
        rk = ridge[k0:len(ridge) - k1] if k1 else ridge[k0:]
        bm = _sil(mu.new_bm(),
                  [(x, z0 + zz * sc_ + zb_) for (x, zz) in rk] +
                  [(rk[-1][0], z0 + zb_), (rk[0][0], z0 + zb_)],
                  y0_, y1_, tl)
        _emit(C, bm, M, P + "mountain_layer_%s" % mat_, "detail", coll,
              cn=cn + "·青绿山体·" + cn_, mat=mat_)

    # 皴笔：沿峰脊下行的短促笔触（斧劈皴），贴在山板正面 1.4mm 处，不触板面
    bm = mu.new_bm()
    for (ridge, yface) in ((near, 0.0046), (far, 0.0984)):
        for i in range(1, len(ridge) - 1):
            (xa, za), (xb, zb), (xc, zc2) = ridge[i - 1], ridge[i], ridge[i + 1]
            if zb <= (za + zc2) * 0.5:                 # 只从凸起的峰顶落笔
                continue
            for k in (-1, 0, 1):
                dz = zb - (za + zc2) * 0.5
                ln = min(0.030, 0.42 * dz + 0.008)
                ang = 1.42 + k * 0.22
                x0 = xb + k * 0.006
                pts = [(x0, yface, z0 + zb - 0.0020),
                       (x0 + math.cos(ang) * ln * 0.45,
                        yface, z0 + zb - 0.0020 - math.sin(ang) * ln * 0.45),
                       (x0 + math.cos(ang) * ln * 0.80,
                        yface, z0 + zb - 0.0020 - math.sin(ang) * ln * 0.80)]
                _tube(bm, pts, 0.0010, 3, r_end=0.0004)
    _emit(C, bm, M, P + "mountain_cun", "detail", coll,
          cn=cn + "·山体皴笔（斧劈皴·近峰远峰）", mat="lacquer")
    # 金碧设色：沿远峰脊线骑一条金线（落在板厚 y 中段、脊上 1.4mm，不触板面）
    bm = mu.new_bm()
    # Continuous gold ribbon follows the two top ridge stations at each x.
    rows=[]
    for x,zz in far:
        rows.append([_v(bm,x,y,z0+zz+.00010) for y in (.102,.104)])
    for l,r in zip(rows,rows[1:]):
        bm.faces.new((l[0],r[0],r[1],l[1]))
    _emit(C, bm, M, P + "mineral_gold", "detail", coll,
          cn=cn + "·金碧设色（远峰脊线金线）", mat="mount_gold")

    # 拖尾跋文
    bm = mu.new_bm()
    for k in range(9):
        x0 = 0.548 + k * 0.030
        _tube(bm, [(x0, -0.075, ztop + 0.0042), (x0, 0.135, ztop + 0.0042)],
              0.0013, 4)
    _emit(C, bm, M, P + "colophon", "detail", coll,
          cn=cn + "·拖尾跋文", mat="lacquer")

    # ---------------- 左侧研墨区：宋代老坑抄手式松鹤端砚（砚池真凹陷 + 抄手空底）
    px, py = -0.95, -0.26
    ox0, ox1 = px - 0.130, px + 0.130
    oy0, oy1 = py - 0.090, py + 0.090
    zr0 = zt + LIFT
    zr1 = zr0 + 0.034
    t = 0.026
    bm = mu.new_bm()
    _boxb(bm, ox0, ox1, oy0, oy0 + t, zr0, zr1, 0.004, 2)          # 前壁
    # The cartouche spans the back wall itself. Its carved field is 2.5 mm
    # below the lip, including under the crane and the individual pine needles.
    stamps = []
    center = oy1 - .014
    def line(points, width, h, closed=False):
        stamps.append(([(px+x, center+y) for x, y in points], width, h, closed))
    line([(-.087,-.007),(-.066,-.001),(-.055,.004),(-.034,.007)],.002,.002)
    for k in range(3):
        tx, ty = -.073 + .017*k, -.002 + .002*k
        for j in range(7):
            ang = .35 + j*.37
            line([(tx,ty),(tx+.009*math.cos(ang),ty+.006*math.sin(ang))],.0007,.0012)
    line([(0.019,-.002),(.026,.001),(.032,.002)], .005,.002)
    line([(.030,.002),(.036,.005),(.042,.007),(.046,.004),(.054,.003)],.0012,.0018)
    for sx in (-1.,1.):
        line([(.025+sx*.002,-.002),(.022+sx*.004,-.007)],.0008,.0012)
    line([(.022,0.),(.012,.003),(.009,.005)],.002,.0016)
    rim = _carved_face(bm,(ox0,ox1,oy1-t,oy1),zr1-.0025,.0025,stamps,cuts=False)
    lower = [_v(bm, v.co.x, v.co.y, zr0) for v in rim]
    mu.bridge_rings(bm, lower, rim, closed=True)
    bm.faces.new(lower[::-1])
    _boxb(bm, ox0, ox0 + t, oy0 + t, oy1 - t, zr0, zr1, 0.004, 2)  # 左壁
    _boxb(bm, ox1 - t, ox1, oy0 + t, oy1 - t, zr0, zr1, 0.004, 2)  # 右壁
    _boxb(bm, ox0 + t, ox1 - t, oy0 + t, oy1 - t,
          zr0 + 0.010, zr0 + 0.012, 0.002, 1)                      # 砚池底（低 2.2cm）
    for (bx0_, bx1_, by0_, by1_) in ((ox0, ox1, oy0, oy0 + 0.016),
                                     (ox0, ox1, oy1 - 0.016, oy1),
                                     (ox0, ox0 + 0.016, oy0 + 0.016, oy1 - 0.016),
                                     (ox1 - 0.016, ox1, oy0 + 0.016, oy1 - 0.016)):
        _boxb(bm, bx0_, bx1_, by0_, by1_, zr0, zr0 + 0.010, 0.002, 1)   # 抄手：底只留边圈
    for (zz_, rr_) in ((zr1, 0.0032), (zr1 - 0.0034, 0.0018)):     # 双道砚唇卷边
        ring = [(ox0 + 0.008, oy0 + 0.008, zz_), (ox1 - 0.008, oy0 + 0.008, zz_),
                (ox1 - 0.008, oy1 - 0.008, zz_), (ox0 + 0.008, oy1 - 0.008, zz_),
                (ox0 + 0.008, oy0 + 0.008, zz_)]
        _tube(bm, ring, rr_, 6)
    _emit(C, bm, M, P + "inkstone", "exhibit", coll,
          cn=cn + "·老坑抄手式松鹤端砚（砚池凹陷·砚额真减料 2.5mm/空底）",
          mat="stone_dark")
    bm = mu.new_bm()
    _boxb(bm, ox0 + t + 0.002, ox1 - t - 0.002, oy0 + t + 0.002, oy1 - t - 0.002,
          zr0 + 0.0125, zr0 + 0.0148, 0.0006, 1)
    _emit(C, bm, M, P + "ink_pool", "detail", coll,
          cn=cn + "·砚池墨面", mat="lacquer")

    # 金字徽墨条
    mx, my = -0.66, -0.20
    bm = mu.new_bm()
    _boxb(bm, mx - 0.043, mx + 0.043, my - 0.011, my + 0.011, zt + LIFT,
          zt + LIFT + 0.013, 0.003, 1)
    _emit(C, bm, M, P + "inkstick", "detail", coll,
          cn=cn + "·徽墨条（金字款）", mat="lacquer")
    bm = mu.new_bm()
    _tube(bm, [(mx - 0.032, my, zt + LIFT + 0.0136),
               (mx - 0.018, my + 0.004, zt + LIFT + 0.0142),
               (mx - 0.002, my - 0.003, zt + LIFT + 0.0142),
               (mx + 0.014, my + 0.004, zt + LIFT + 0.0142),
               (mx + 0.030, my, zt + LIFT + 0.0136)], 0.0015, 4)
    for k in range(4):                                        # 龙足
        xx = mx - 0.020 + k * 0.012
        _tube(bm, [(xx, my, zt + LIFT + 0.0140), (xx + 0.004, my - 0.008,
                                                  zt + LIFT + 0.0152)], 0.0008, 3)
    _disc(bm, mx + 0.036, my, zt + LIFT + 0.0134, 0.0042, 0.0016, 8)   # 龙头
    for v in bm.verts:
        # Flatten the gold leaf against the planar stock; preserve its design in XY.
        v.co.z=zt+LIFT+.01305+(v.co.z-(zt+LIFT+.012))*0.020
    _emit(C, bm, M, P + "inkstick_gold", "detail", coll,
          cn=cn + "·墨条金龙（贴面金线）", mat="mount_gold")

    # 影青开片瓷水注（小壶带流）
    vx, vy = -1.42, -0.30
    bm = mu.new_bm()
    _lathe(bm, [(0.014, zt + LIFT), (0.042, zt + LIFT), (0.048, zt + LIFT + 0.008),
                (0.052, zt + LIFT + 0.030), (0.040, zt + LIFT + 0.056),
                (0.024, zt + LIFT + 0.068), (0.022, zt + LIFT + 0.078),
                (0.014, zt + LIFT + 0.078), (0.014, zt + LIFT + 0.064)],
           vx, vy, seg=16)
    _tube(bm, [(vx + 0.030, vy, zt + LIFT + 0.030), (vx + 0.070, vy, zt + LIFT + 0.055),
               (vx + 0.082, vy, zt + LIFT + 0.062)], 0.0075, 8, r_end=0.0042)
    _tube(bm, [(vx - 0.030, vy, zt + LIFT + 0.034), (vx - 0.060, vy, zt + LIFT + 0.056),
               (vx - 0.032, vy, zt + LIFT + 0.070)], 0.0050, 6)
    _emit(C, bm, M, P + "water_drop", "detail", coll,
          cn=cn + "·影青开片瓷水注", mat="celadon")

    # ---------------- 白瓷笔搁 + 3 支笔
    qx, qy = -0.30, -0.26
    zb0 = zt + LIFT
    bm = mu.new_bm()
    _boxb(bm, qx - 0.130, qx + 0.130, qy - 0.023, qy + 0.023, zb0, zb0 + 0.014,
          0.004, 1)
    for k in range(4):
        cx0 = qx - 0.090 + k * 0.060
        _post(bm, cx0, qy, zb0 + 0.014, zb0 + 0.034, 0.030, 0.011)
    _emit(C, bm, M, P + "brush_rest", "detail", coll,
          cn=cn + "·白瓷笔搁（四峰三谷）", mat="bisque")

    pens = ((-0.360, 0.0058, "狼毫勾线"), (-0.300, 0.0068, "山马毫排笔"),
            (-0.240, 0.0082, "大兰竹提笔"))
    for k, (pxs, pr, pcn) in enumerate(pens):
        zc = zb0 + 0.014 + pr
        bm_h = mu.new_bm()
        _pen(bm_h, pxs, -0.450, -0.175, zc, pr, 8, 0.0100 if k == 2 else 0.0080)
        for yy in (-0.365, -0.185):
            _annulus(bm_h, pxs, yy, zc - 0.0004, zc + 0.0004, pr, pr + 0.0022, 10)
        _emit(C, bm_h, M, P + "pen_%d" % (k + 1), "detail", coll,
              cn=cn + "·毛笔·" + pcn, mat="wood_lite")

    # ---------------- 右侧设色区：五瓣梅花调色碟 + 三色浆
    dx, dy = 0.20, -0.28
    bm = mu.new_bm()
    _lathe(bm, [(0.018, zt + LIFT), (0.062, zt + LIFT), (0.070, zt + LIFT + 0.006),
                (0.074, zt + LIFT + 0.016), (0.070, zt + LIFT + 0.022),
                (0.062, zt + LIFT + 0.018), (0.058, zt + LIFT + 0.010),
                (0.018, zt + LIFT + 0.008)], dx, dy, seg=18)
    for k in range(5):
        a = TAU * k / 5 + 0.3
        _annulus(bm, dx + math.cos(a) * 0.050, dy + math.sin(a) * 0.050,
                 zt + LIFT + 0.014, zt + LIFT + 0.021, 0.017, 0.025, 12)
    _emit(C, bm, M, P + "palette", "detail", coll,
          cn=cn + "·五瓣梅花调色碟", mat="bisque")
    for mat, idxs, ccp in (("mount_far", (0, 1), "石青"), ("celadon", (2, 3), "石绿"),
                           ("mount_gold", (4,), "赭石")):
        bm = mu.new_bm()
        for k in idxs:
            a = TAU * k / 5 + 0.3
            _disc(bm, dx + math.cos(a) * 0.050, dy + math.sin(a) * 0.050,
                  zt + LIFT + 0.0212, 0.0145, 0.0022, 12)
        _emit(C, bm, M, P + "color_" + ccp, "detail", coll,
              cn=cn + "·" + ccp + "浆", mat=mat)

    # 白玉研钵 + 研杵
    bx, by = 0.56, -0.26
    bm = mu.new_bm()
    _lathe(bm, [(0.020, zt + LIFT), (0.056, zt + LIFT), (0.066, zt + LIFT + 0.010),
                (0.070, zt + LIFT + 0.044), (0.076, zt + LIFT + 0.048),
                (0.070, zt + LIFT + 0.050), (0.062, zt + LIFT + 0.046),
                (0.062, zt + LIFT + 0.018), (0.020, zt + LIFT + 0.012)],
           bx, by, seg=18)
    _emit(C, bm, M, P + "mortar", "detail", coll,
          cn=cn + "·白玉研钵", mat="jade")
    bm = mu.new_bm()
    _lathe(bm,[(.004,.0121),(.008,.014),(.009,.020),(.006,.025)],bx,by,zt+LIFT,12)
    _tube(bm,[(bx,by,zt+LIFT+.021),(bx+.020,by+.010,zt+LIFT+.070),
              (bx+.028,by+.014,zt+LIFT+.095)],.007,12,r_end=.012)
    _emit(C, bm, M, P + "pestle", "detail", coll,
          cn=cn + "·研杵", mat="jade")

    # 孔雀石 / 蓝铜矿原石
    # 孔雀石：葡萄状（botryoidal）结核层层叠生 + 一处断口平面
    bm = mu.new_bm()
    for (dx_, dy_, r_, zz_) in ((0.000, 0.000, 0.048, 0.000),
                                (0.026, 0.014, 0.032, 0.030),
                                (-0.024, 0.018, 0.027, 0.052),
                                (0.010, -0.022, 0.021, 0.068)):
        zb_ = zt + LIFT + zz_
        _lathe(bm, [(0.0015, zb_), (0.42 * r_, zb_ + 0.004),
                    (0.80 * r_, zb_ + 0.014), (0.98 * r_, zb_ + 0.026),
                    (0.70 * r_, zb_ + 0.036), (0.30 * r_, zb_ + 0.042),
                    (0.0015, zb_ + 0.043)],
               -1.56 + dx_, -0.20 + dy_, seg=12)
    _boxb(bm, -1.598, -1.548, -0.238, -0.196, zt + LIFT, zt + LIFT + 0.030, 0.0018, 1)
    _emit(C, bm, M, P + "malachite", "exhibit", coll,
          cn=cn + "·孔雀石原石（葡萄状层理 + 断口）", mat="malachite")
    # 蓝铜矿：方晶（三组互错的方柱 + 晶面）
    bm = mu.new_bm()
    for (dx_, dy_, sx_, sy_, zz_, h_) in ((0.000, 0.000, 0.052, 0.042, 0.000, 0.034),
                                          (0.030, 0.012, 0.030, 0.026, 0.024, 0.028),
                                          (-0.028, 0.016, 0.024, 0.020, 0.040, 0.022)):
        _boxb(bm, -1.56 + dx_ - sx_ * 0.5, -1.56 + dx_ + sx_ * 0.5,
              0.020 + dy_ - sy_ * 0.5, 0.020 + dy_ + sy_ * 0.5,
              zt + LIFT + zz_, zt + LIFT + zz_ + h_, 0.0016, 1)
    _emit(C, bm, M, P + "azurite", "exhibit", coll,
          cn=cn + "·蓝铜矿原石（方晶）", mat="azurite")

    # ---------------- 后墙书画博古架（避开楼梯：只占后墙东半段）
    ax0, ax1 = 1.15, 5.30
    ay0, ay1 = 5.06, 5.48
    ah = 2.35
    bm = mu.new_bm()
    px_ = (ax0, (ax0 + ax1) * 0.5, ax1)
    for pxv in px_:
        for sy in (0.0, 1.0):
            ly = ay0 + 0.03 if sy == 0.0 else ay1 - 0.03
            _post(bm, pxv, ly, zf + FLIFT, ah + zf, 0.058, 0.050)
    for zz in (0.34, 0.76, 1.18, 1.60, 2.02):
        _boxb(bm, ax0, ax1, ay0 + 0.012, ay1 - 0.012, zf + zz, zf + zz + 0.022,
              0.0035, 1)
    _boxb(bm, ax0 - 0.02, ax1 + 0.02, ay0, ay1, zf + ah - 0.045, zf + ah, 0.005, 1)
    # 多宝格竖向分隔（上下错落）
    for (dxv, z0_, z1_) in ((1.95, 0.34, 1.18), (2.62, 0.76, 1.60),
                            (3.48, 0.34, 0.76), (4.10, 1.18, 2.02),
                            (4.62, 0.76, 1.60)):
        _boxb(bm, dxv - 0.012, dxv + 0.012, ay0 + 0.012, ay1 - 0.012,
              zf + z0_, zf + z1_, 0.0025, 1)
    _emit(C, bm, M, P + "cabinet", "exhibit", coll,
          cn=cn + "·书画博古架（多宝格）", mat="wood_dark")

    # 画缸 + 插宣纸卷/画轴
    gx, gy = 1.60, 5.27
    gz = zf + 0.3635
    bm = mu.new_bm()
    _lathe(bm, [(0.055, gz), (0.100, gz), (0.108, gz + 0.012), (0.132, gz + 0.086),
                (0.150, gz + 0.170), (0.152, gz + 0.230), (0.160, gz + 0.262),
                (0.150, gz + 0.262), (0.142, gz + 0.230), (0.141, gz + 0.170),
                (0.122, gz + 0.086), (0.098, gz + 0.020), (0.055, gz + 0.016)],
           gx, gy, seg=18)
    _emit(C, bm, M, P + "scroll_jar", "exhibit", coll,
          cn=cn + "·画缸（青花）", mat="celadon")
    bm = mu.new_bm()
    for k, (ox, oy, tilt) in enumerate(((-0.035, 0.010, 0.10), (0.030, -0.020, -0.12),
                                        (0.005, 0.040, 0.03))):
        _tube(bm, [(gx + ox, gy + oy, gz + 0.022),
                   (gx + ox + tilt * 0.35, gy + oy + tilt * 0.10, gz + 0.375)],
              0.026, 10)
    _emit(C, bm, M, P + "scroll_rolls", "detail", coll,
          cn=cn + "·宣纸卷与画轴（插缸）", mat="paper_xuan")

    # 生绢/熟绢布卷
    bm = mu.new_bm()
    for k, (sx, sz, r_) in enumerate(((2.22, .8121, .030), (2.89, .8081, .026),
                                      (2.25, 1.2301, .028))):
        mu.cylinder(bm, (sx, 5.27 - 0.16, zf + sz), r_, 0.30, segments=14, axis="X")
    _emit(C, bm, M, P + "silk_rolls", "detail", coll,
          cn=cn + "·生绢/熟绢布卷", mat="silk_raw")

    # ---------------- 仿宋古琴琴台 + 琴
    qx0, qx1 = 2.55, 3.85
    qy0, qy1 = 4.12, 4.48
    qh = 0.62
    bm = mu.new_bm()
    _boxb(bm, qx0, qx1, qy0, qy1, zf + qh - 0.040, zf + qh, 0.006, 2)
    for sx in (qx0 + 0.075, qx1 - 0.075):
        for sy in (qy0 + 0.060, qy1 - 0.060):
            _post(bm, sx, sy, zf + FLIFT, zf + qh - 0.040, 0.052, 0.044)
    _apron(bm, "x", qx0 + 0.075, qx1 - 0.075, qy0 + 0.010, zf + qh - 0.040, 0.090,
           0.016, 14, 0.70)
    _apron(bm, "x", qx0 + 0.075, qx1 - 0.075, qy1 - 0.010, zf + qh - 0.040, 0.090,
           0.016, 14, 0.70)
    _emit(C, bm, M, P + "qin_table", "exhibit", coll,
          cn=cn + "·仿宋古琴琴台", mat="wood_dark")

    zq = zf + qh + LIFT
    bm = mu.new_bm()
    ccx, ccy = (qx0 + qx1) * 0.5, (qy0 + qy1) * 0.5 + 0.01
    _boxb(bm, ccx - 0.570, ccx + 0.570, ccy - 0.085, ccy + 0.085, zq, zq + 0.042,
          0.008, 2)
    # 岳山（琴头）/ 龙龈（琴尾）承露
    for k, sx in enumerate((ccx - 0.560, ccx + 0.480)):
        _boxb(bm, sx, sx + 0.080, ccy - 0.080, ccy + 0.080,
              zq + 0.042, zq + 0.048, 0.003, 1)
    _emit(C, bm, M, P + "qin_body", "exhibit", coll,
          cn=cn + "·古琴（仲尼式）", mat="wood_dark")
    bm = mu.new_bm()
    for k in range(7):
        yy = ccy - 0.070 + k * 0.0233
        _tube(bm, [(ccx - 0.545, yy, zq + 0.04892), (ccx + 0.545, yy, zq + 0.04892)],
              0.0009, 8)
    _emit(C, bm, M, P + "qin_strings", "detail", coll,
          cn=cn + "·七弦", mat="silk_raw")


# ============================================================================
# 3 针经阁：开封汴绣（绷绢 → 分丝 → 盘金）
# ============================================================================
def _bianxiu(C, H):
    coll = C.coll("展陈", H["cn"])
    M = _M(H)
    zf = H["floor"]
    P = "cr_bianxiu_"
    cn = H["cn"]

    # ---------------- 落地立式红木雕花大绣架（高 1.65 / 宽 1.40）
    ztop_ = zf + 1.65
    bm = mu.new_bm()
    for sx in (-1.0, 1.0):
        lx = sx * 0.62
        _turned(bm, lx, 0.0, zf + FLIFT, ztop_ - 0.10, 0.038, 0.052, 14, 10)
        # 柱脚（前后出脚，防倾倒）
        _boxb(bm, lx - 0.070, lx + 0.070, -0.30, 0.22, zf + FLIFT,
              zf + FLIFT + 0.055, 0.006, 1)
        _bar(bm, (lx, 0.0, zf + FLIFT + 0.050), (lx, -0.28, zf + FLIFT + 0.050),
             0.030, 0.030)
        _bar(bm, (lx, 0.0, zf + FLIFT + 0.050), (lx, 0.20, zf + FLIFT + 0.050),
             0.030, 0.030)
    # Bracket aprons with an ogee outline and a three-lobed ruyi head.
    for side in (-1.,1.):
        profile = [(0.,0.),(.185,0.),(.155,-.016),(.137,-.04),(.116,-.046),
                   (.11,-.029),(.094,-.032),(.095,-.049),(.082,-.059),
                   (.068,-.054),(.069,-.039),(.052,-.043),(.048,-.073),
                   (.026,-.086),(0.,-.14)]
        outline = _bez(profile,3,True)
        loops = [[_v(bm,side*(.62-x),y,ztop_-.115+z) for x,z in outline]
                 for y in (-.025,.025)]
        mu.bridge_rings(bm,*loops,closed=True)
        mu.cap_ring(bm,loops[0],flip=True)
        mu.cap_ring(bm,loops[1])
    # 横梁（雕花：回纹 + 卷草）
    _boxb(bm, -0.700, 0.700, -0.048, 0.048, ztop_ - 0.100, ztop_, 0.007, 2)
    _bored_plate(bm,(-.66,.66,-.058,.058),[_ell(.30,-.043,.0062,.0062,24)],
                 ztop_-.132,ztop_-.100)
    for k in range(9):
        x0 = -0.60 + k * 0.15
        _tube(bm, [(x0, -0.049, ztop_ - 0.050), (x0 + 0.075, -0.049, ztop_ - 0.030),
                   (x0 + 0.15, -0.049, ztop_ - 0.050)], 0.0045, 5)
    # 下横枨 + 前后斜撑（在立柱外侧的 YZ 平面内，不穿绢面）
    _boxb(bm, -0.620, 0.620, -0.036, 0.036, zf + 0.150, zf + 0.200, 0.005, 1)
    for sx in (-1.0, 1.0):
        _bar(bm, (sx * 0.60, 0.030, zf + 0.210), (sx * 0.60, 0.030, ztop_ - 0.135),
             0.022, 0.022)
        _tube(bm, [(sx * 0.604, 0.040, ztop_ - 0.250), (sx * 0.604, 0.040, zf + 0.480),
                   (sx * 0.604, -0.070, zf + 0.235), (sx * 0.604, -0.230, zf + 0.075)],
              0.0038, 5)
    # Horizontal guide eyes; the alternating lacing goes through their bores.
    for side in (-1.,1.):
        for k in range(1,22,2):
            zz=zf+.72+.72*(.045+.91*k/22)
            _annulus(bm,side*.565,-.030,zz-.0015,zz+.0015,.0032,.0155,12)
            _box(bm,side*.577,side*.619,-.034,-.026,zz-.002,zz+.002)
    # Turned radial bearing for each butterfly handle; the spindle enters the
    # bore from outside and stops short of the wooden column inside.
    for sign in (-1.,1.):
        ring=[]
        for x,r in ((.648,.0103),(.648,.021),(.685,.021),(.685,.0103)):
            ring.append([_v(bm,sign*x,r*math.cos(TAU*j/24),zf+1.17+r*math.sin(TAU*j/24))
                         for j in range(24)])
        for j in range(4):
            mu.bridge_rings(bm,ring[j],ring[(j+1)%4],closed=True)
    _emit(C, bm, M, P + "stand", "exhibit", coll,
          cn=cn + "·红木雕花大绣架（车木旋纹立柱）", mat="wood_dark")

    # 两侧旋钮（张紧用）
    bm = mu.new_bm()
    for sx in (-1.,1.):
        zz = zf + 1.17
        mu.cylinder(bm,(min(sx*.673,sx*.703),0.,zz),.010,.030,segments=24,axis="X")
        for sy in (-1.,1.):
            outline = _bez([(0.,-.006),(.018,-.016),(.042,-.019),(.050,-.011),
                            (.042,.004),(.053,.015),(.043,.030),(.022,.022),
                            (.008,.008)],3,True)
            _plyz(bm,[(sy*y,zz+z) for y,z in outline],sx*.695-.008,sx*.695+.008)
    _emit(C,bm,M,P+"knobs","detail",coll,cn=cn+"·张紧蝶形旋钮",mat="wood_dark")

    # 绣绷上紧绷真丝素绢（微鼓 0.01）
    yb, amp = -0.030, 0.0005

    def silk_y(u, v):
        return yb - amp * math.sin(math.pi * u) * math.sin(math.pi * v)

    def sx_of(u):
        return -0.420 + 0.840 * u

    def sz_of(v):
        return zf + 0.720 + 0.720 * v

    def fn(u, v):
        return Vector((sx_of(u), silk_y(u, v), sz_of(v)))

    bm = mu.new_bm()
    _panel(bm, fn, 16, 20, (0.0, -0.0022, 0.0))
    # 素绢底色用 stone_lite（纸白）：silk 材质是 #C0402F/Alpha0.55 的朱红织锦，
    # 用作未上色生绢会透出背后家具且偏红；锦缎件（绣墩软垫、绢卷）仍用 silk。
    for side in (-1.,1.):
        for k in range(0,23,2):
            zz=sz_of(.045+.91*k/22)
            _annulus(bm,side*.426,yb,zz-.0015,zz+.0015,.0032,.0095,12)
    _emit(C, bm, M, P + "silk", "exhibit", coll,
          cn=cn + "·绣绷真丝素绢（微鼓）", mat="silk_raw")

    # 上下木夹条
    bm = mu.new_bm()
    for vv in (0.0, 1.0):
        z0 = sz_of(vv) - (0.014 if vv > 0.5 else 0.0)
        for ya,yz in ((yb-.016,yb-.00236),(yb+.00012,yb+.014)):
            _boxb(bm,-.445,.445,ya,yz,z0,z0+.014,.0012,1)
        for sign in (-1.,1.):
            _box(bm,sign*.42025,sign*.444,yb-.00236,yb+.00012,z0+.001,z0+.013)
    _emit(C, bm, M, P + "clamps", "detail", coll,
          cn=cn + "·绣绷木夹条", mat="wood_lite")

    bm = mu.new_bm()
    for sign in (-1.,1.):
        cord=[]
        for k in range(23):
            x=sign*(.426 if k%2==0 else .565)
            zz=sz_of(.045+.91*k/22)
            for dz in (-.006,.006):
                cord.append((x+sign*.0003,yb,zz+dz))
        _tube(bm,cord,.0025,8)
        for k in (0,22):
            zz=sz_of(.045+.91*k/22)
            ds=-1. if k==0 else 1.
            _lathe(bm,[(.0043,zz+ds*.0016),(.0047,zz+ds*.0032),
                       (.0033,zz+ds*.0059),(.0025,zz+ds*.0062)],sign*.426,yb,seg=8)

    _emit(C,bm,M,P+"tension_cords","detail",coll,cn=cn+"·绣绷锯齿穿绳",mat="silk_raw")

    # Interpolate the triangles of the actual 16 x 20 silk mesh. Threads rise
    # at most 0.15 mm above its front skin, including the radius of the yarn.
    def silk_point(u,v,offset):
        i,j = min(15,int(u*16)),min(19,int(v*20))
        x,y = u*16-i,v*20-j
        z00,z11 = silk_y(i/16,j/20),silk_y((i+1)/16,(j+1)/20)
        if x>=y:
            front = (1-x)*z00+(x-y)*silk_y((i+1)/16,j/20)+y*z11
        else:
            front = (1-y)*z00+(y-x)*silk_y(i/16,(j+1)/20)+x*z11
        return Vector((sx_of(u),front-.0022-offset,sz_of(v)))

    def stitch(bm,path,top):
        # Flatten an elliptical strand against the silk. It stays wide enough
        # for a close-up to show thread direction at the physical stitch height.
        rows = []
        for i,(u,v) in enumerate(path):
            tangent = Vector(path[min(i+1,len(path)-1)])-Vector(path[max(i-1,0)])
            normal = Vector((-tangent.y,tangent.x)).normalized()
            ring = []
            for k in range(6):
                ang = TAU*k/6
                p = Vector((u,v)) + normal*(.00060*math.cos(ang))
                ring.append(bm.verts.new(silk_point(*p,top-.000006+.000006*math.sin(ang))))
            rows.append(ring)
        for first,last in zip(rows,rows[1:]):
            mu.bridge_rings(bm,first,last,closed=True)
        mu.cap_ring(bm,rows[0],flip=True)
        mu.cap_ring(bm,rows[-1])

    cu,cv=.315,.575
    for layer,(count,base,length,width,phase,mat) in enumerate((
            (8,.026,.086,.029,0.,"thread_04"),(7,.018,.062,.024,.24,"thread_09"),
            (5,.011,.038,.018,.50,"thread_13"),(3,.006,.020,.012,.90,"thread_20"))):
        bm=mu.new_bm()
        for k in range(count):
            angle=TAU*k/count+phase
            for index in range(-9,10):
                strand=[]
                for j in range(9):
                    t=j/8
                    aa=angle+.26*t*t*(-1 if layer%2 else 1)
                    rad=base+length*t
                    spread=index/9*width*(.11+.89*math.sin(math.pi*t))
                    strand.append((cu+math.cos(aa)*rad-math.sin(aa)*spread,
                                   cv+math.sin(aa)*rad+math.cos(aa)*spread))
                stitch(bm,strand,.000045+layer*.000025)
        _emit(C,bm,M,P+"peony_L%d"%layer,"detail",coll,
              cn=cn+"·牡丹顺瓣绣线层",mat=mat)

    bm=mu.new_bm()
    for k in range(13):
        ang=TAU*k/13
        u,v=cu+.012*math.cos(ang),cv+.012*math.sin(ang)
        stitch(bm,[(u+.002*math.cos(ang+j*.55),v+.002*math.sin(ang+j*.55))
                   for j in range(12)],.00015)
    _emit(C,bm,M,P+"peony_knots","detail",coll,cn=cn+"·牡丹打籽绣线层",mat="thread_deep")
    bm=mu.new_bm()
    stem=[(cu-.024-.156*t+.034*math.sin(math.pi*t),cv-.036-.318*t) for t in [j/20 for j in range(21)]]
    stitch(bm,stem,.000020)
    for k in (3,6,9,13,16):
        u,v=stem[k]
        sign=-1 if k%2 else 1
        for n in range(-6,7):
            stitch(bm,[(u+sign*.055*j/12,v+.032*j/12+n*.002*math.sin(math.pi*j/12))
                       for j in range(13)],.000020)
    _emit(C,bm,M,P+"peony_leaves","detail",coll,cn=cn+"·枝叶绣线层",mat="celadon")

    # Satin stitches trace the body, wing and tail. The beak remains at the
    # same end as the head, unlike the former second head on the opposite end.
    for part,u,v,ln,wd,angle,mat in (
            ("body",.644,.422,.064,.026,.20,"thread_13"),
            ("wing",.646,.440,.053,.017,1.0,"thread_20"),
            ("head",.615,.435,.024,.014,.30,"thread_04"),
            ("beak",.605,.440,.018,.004,2.65,"thread_deep"),
            ("tail",.680,.430,.066,.013,-.22,"thread_09")):
        bm=mu.new_bm()
        for k in range(-8,9):
            strand=[]
            for j in range(13):
                t=j/12
                w=wd*(k/8)*(.06+.94*math.sin(math.pi*t))
                strand.append((u+ln*t*math.cos(angle)-w*math.sin(angle),
                               v+ln*t*math.sin(angle)+w*math.cos(angle)))
            stitch(bm,strand,{"wing":.00015,"head":.00012,"beak":.00008,"tail":.000045,"body":.00010}[part])
        _emit(C,bm,M,P+"bird_"+part,"detail",coll,cn=cn+"·绣花鸟绣线层",mat=mat)

    # 横梁插一只双层竹制手持方绣绷
    bm = mu.new_bm()
    hx, hz = 0.30, zf + 1.60
    for (yy, R, rr) in ((-0.075, 0.084, 0.0060), (-0.066, 0.075, 0.0050)):
        _torus_y(bm, hx, yy, hz, R, rr, 24, 6)
    _emit(C, bm, M, P + "hoop", "detail", coll,
          cn=cn + "·双层竹制手持方绣绷", mat="wood_lite")
    bm = mu.new_bm()
    mu.cylinder(bm, (hx, -0.067, hz), 0.0699, 0.002, segments=24, axis="Y")
    _emit(C, bm, M, P + "hoop_silk", "detail", coll,
          cn=cn + "·手绷素绢", mat="silk_raw")
    bm = mu.new_bm()
    shelf=hz-.0901
    _boxb(bm,hx-.011,hx+.011,-.084,-.040,shelf-.006,shelf,.001,1)
    mu.cylinder(bm,(hx,-.043,shelf-.003),.006,ztop_-.1002-shelf+.003,segments=24)
    _boxb(bm,hx-.010,hx+.010,-.087,-.083,shelf-.005,shelf+.005,.0007,1)
    _emit(C, bm, M, P + "hoop_peg", "detail", coll,
          cn=cn + "·挂绷木栓", mat="wood_dark")

    # ---------------- 高足实木绣墩（h0.45，织锦软垫）
    bx, by = 1.05, 0.62
    bm = mu.new_bm()
    _lathe(bm, [(0.070, zf + FLIFT), (0.130, zf + FLIFT), (0.140, zf + 0.020),
                (0.116, zf + 0.060), (0.072, zf + 0.130), (0.068, zf + 0.300),
                (0.092, zf + 0.345), (0.150, zf + 0.372), (0.152, zf + 0.392),
                (0.120, zf + 0.392)], bx, by, seg=18)
    _emit(C, bm, M, P + "stool", "exhibit", coll,
          cn=cn + "·高足实木绣墩", mat="wood_dark")
    bm = mu.new_bm()
    _lathe(bm, [(0.150, zf + 0.3935), (0.150, zf + 0.404), (0.146, zf + 0.436),
                (0.120, zf + 0.450), (0.020, zf + 0.452), (0.020, zf + 0.402)],
           bx, by, seg=18)
    _emit(C, bm, M, P + "stool_cushion", "detail", coll,
          cn=cn + "·织锦软垫", mat="crimson")

    # ---------------- 南窗下分丝配线长案 w2.40×d0.90（h0.80）
    bx0, bx1 = 4.30, 5.20
    by0, by1 = -1.20, 1.20
    zt = zf + 0.80
    bm = mu.new_bm()
    _boxb(bm, bx0, bx1, by0, by1, zt - 0.048, zt, 0.006, 2)
    for sy in (by0 + 0.085, (by0 + by1) * 0.5, by1 - 0.085):
        for sx in (bx0 + 0.085, bx1 - 0.085):
            _post(bm, sx, sy, zf + FLIFT, zt - 0.048, 0.070, 0.058)
    _bar(bm, (bx0 + 0.085, by0 + 0.085, zf + 0.22), (bx1 - 0.085, by0 + 0.085, zf + 0.22),
         0.026, 0.036)
    _bar(bm, (bx0 + 0.085, by1 - 0.085, zf + 0.22), (bx1 - 0.085, by1 - 0.085, zf + 0.22),
         0.026, 0.036)
    _bar(bm, (bx0 + 0.085, by0 + 0.085, zf + 0.22), (bx0 + 0.085, by1 - 0.085, zf + 0.22),
         0.026, 0.036)
    _emit(C, bm, M, P + "thread_desk", "exhibit", coll,
          cn=cn + "·分丝配线长案", mat="wood_dark")

    # 真丝分丝排线木板（24 道由浅入深的丝线束）
    pbx, pby = 4.72, -0.60
    pw, pd = 0.34, 0.66
    zpt = zt + LIFT
    bm = mu.new_bm()
    _boxb(bm, pbx - pw / 2, pbx + pw / 2, pby - pd / 2, pby + pd / 2,
          zpt, zpt + 0.024, 0.004, 1)
    for k in range(24):
        yy = pby - pd / 2 + 0.018 + k * (pd - 0.036) / 23.0
        _box(bm, pbx - 0.012, pbx + 0.012, yy - 0.004, yy + 0.004,
             zpt + 0.024, zpt + 0.030)
    _emit(C, bm, M, P + "thread_board", "detail", coll,
          cn=cn + "·真丝分丝排线木板", mat="wood_dark")

    # 24 道丝线束：逐条各用 thread_00..thread_23（真 24 级色阶，不分组充数）
    for k in range(24):
        yy = pby - pd / 2 + 0.018 + k * (pd - 0.036) / 23.0
        bm = mu.new_bm()
        _tube(bm,[(pbx-.142,yy,zpt+.02585),(pbx-.112,yy+.001,zpt+.02585),
                  (pbx-.018,yy+.002,zpt+.03185),(pbx+.018,yy+.001,zpt+.03185),
                  (pbx+.112,yy-.002,zpt+.02585),(pbx+.142,yy-.003,zpt+.02585)],.0018,8)
        _emit(C, bm, M, P + "thread_%02d" % k, "detail", coll,
              cn=cn + "·分丝线束 %02d 号（色阶 %d/24）" % (k + 1, k + 1),
              mat="thread_%02d" % k)

    # 实木多轴盘金银线架
    sx0 = 4.70
    sy0 = 0.14
    bm = mu.new_bm()
    _boxb(bm, sx0 - 0.11, sx0 + 0.11, sy0 - 0.055, sy0 + 0.055, zpt, zpt + 0.016, 0.004, 1)
    for sxx in (sx0 - 0.095, sx0 + 0.095):
        _post(bm, sxx, sy0, zpt + 0.016, zpt + 0.140, 0.024, 0.020)
    _bar(bm, (sx0 - 0.095, sy0, zpt + 0.132), (sx0 + 0.095, sy0, zpt + 0.132),
         0.024, 0.018)
    for sign in (-1.,1.):
        xx=sx0+sign*.040
        _post(bm,xx,sy0+.043,zpt+.016,zpt+.093,.013)
        mu.cylinder(bm,(xx,sy0-.032,zpt+.082),.003,.076,segments=24,axis="Y")
    _emit(C, bm, M, P + "spool_rack", "detail", coll,
          cn=cn + "·多轴盘金银线架", mat="wood_dark")
    for k, (mat, sgn) in enumerate((("mount_gold", -1), ("bronze", 1))):
        bm = mu.new_bm()
        _sleeve_y(bm,sx0+sgn*.040,zpt+.082,sy0-.030,sy0+.030,.0032,.022,24)
        _emit(C, bm, M, P + "spool_%d" % (k + 1), "detail", coll,
              cn=cn + ("·金线木轴" if k == 0 else "·银线木轴"), mat=mat)
    bm = mu.new_bm()
    _tube(bm,[(sx0-.0631,sy0-.014,zpt+.082),(sx0-.0631,sy0-.015,zpt+.069),
              (sx0-.079,sy0-.055,zpt+.034),(sx0-.150,sy0-.120,zpt+.0011)],.001,8)
    _emit(C, bm, M, P + "gold_wire", "detail", coll,
          cn=cn + "·盘金线迹", mat="mount_gold")

    # 葫芦形针插 + 8 根针
    hx0, hy0 = 4.68, 0.66
    bm = mu.new_bm()
    _lathe(bm, [(0.030, zpt), (0.060, zpt), (0.066, zpt + 0.014), (0.058, zpt + 0.040),
                (0.036, zpt + 0.056), (0.026, zpt + 0.068), (0.030, zpt + 0.080),
                (0.028, zpt + 0.094), (0.014, zpt + 0.100), (0.014, zpt + 0.086)],
           hx0, hy0, seg=16)
    _emit(C, bm, M, P + "pincushion", "detail", coll,
          cn=cn + "·大红缎面葫芦形针插", mat="crimson")
    bm = mu.new_bm()
    for k in range(8):
        a = TAU * k / 8
        _tube(bm, [(hx0 + math.cos(a) * 0.010, hy0 + math.sin(a) * 0.010, zpt + 0.090),
                   (hx0 + math.cos(a) * 0.020, hy0 + math.sin(a) * 0.020, zpt + 0.150)],
              0.0007, 3, r_end=0.0002)
    _emit(C, bm, M, P + "needles", "detail", coll,
          cn=cn + "·细针 8 根", mat="steel")

    # 仿宋鹤形铜剪刀 + 小号纱线折剪
    bm = mu.new_bm()
    cx0, cy0 = 4.44, 0.02
    for sgn in (-1.0, 1.0):
        _boxb(bm, cx0 - 0.006, cx0 + 0.006, cy0 + sgn * 0.010, cy0 + sgn * 0.150,
              zpt + 0.004, zpt + 0.012, 0.0025, 1)
        _annulus(bm, cx0, cy0 + sgn * 0.180, zpt + 0.004, zpt + 0.012, 0.008, 0.016, 10)
        _bar(bm, (cx0, cy0 + sgn * 0.150, zpt + 0.008),
             (cx0, cy0 + sgn * 0.166, zpt + 0.008), 0.010, 0.006)
    _annulus(bm, cx0, cy0, zpt + 0.002, zpt + 0.014, 0.006, 0.013, 10)
    _tube(bm, [(cx0, cy0 - 0.020, zpt + 0.030), (cx0, cy0 - 0.040, zpt + 0.048),
               (cx0, cy0 - 0.030, zpt + 0.062)], 0.0032, 5)
    _emit(C, bm, M, P + "scissors_crane", "exhibit", coll,
          cn=cn + "·仿宋鹤形铜剪刀", mat="brass")

    bm = mu.new_bm()
    ex0, ey0 = 4.86, 0.40
    for sgn in (-1.0, 1.0):
        _boxb(bm, ex0 - 0.004, ex0 + 0.004, ey0 + sgn * 0.006, ey0 + sgn * 0.088,
              zpt + 0.003, zpt + 0.009, 0.002, 1)
        _annulus(bm, ex0, ey0 + sgn * 0.104, zpt + 0.003, zpt + 0.009, 0.005, 0.011, 8)
    _annulus(bm, ex0, ey0, zpt + 0.002, zpt + 0.010, 0.004, 0.009, 8)
    _emit(C, bm, M, P + "scissors_small", "detail", coll,
          cn=cn + "·小号纱线折剪", mat="steel")


# ============================================================================
# 4 素肌堂：景德青花（拉坯 → 修坯 → 画坯 → 晾坯）
# ============================================================================
def _qinghua(C, H):
    coll = C.coll("展陈", H["cn"])
    M = _M(H)
    zf = H["floor"]
    P = "cr_qinghua_"
    cn = H["cn"]

    # ---------------- 靠窗古法拉坯作坊位：单轴木质陶车
    cx, cy = -4.70, -1.60
    bm = mu.new_bm()
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            _post(bm, cx + sx * 0.280, cy + sy * 0.280, zf + FLIFT,
                  zf + 0.46, 0.078, 0.064)
            _boxb(bm, cx + sx * 0.280 - 0.055, cx + sx * 0.280 + 0.055,
                  cy + sy * 0.280 - 0.055, cy + sy * 0.280 + 0.055,
                  zf + FLIFT, zf + FLIFT + 0.026, 0.004, 1)
    for sy in (-1.0, 1.0):
        _bar(bm, (cx - 0.280, cy + sy * 0.280, zf + 0.435),
             (cx + 0.280, cy + sy * 0.280, zf + 0.435), 0.048, 0.040)
    for sx in (-1.0, 1.0):
        _bar(bm, (cx + sx * 0.280, cy - 0.280, zf + 0.435),
             (cx + sx * 0.280, cy + 0.280, zf + 0.435), 0.048, 0.040)
    # 中轴 + 旋转圆盘
    mu.cylinder(bm, (cx, cy, zf + 0.455), 0.034, 0.105, segments=14)
    _lathe(bm, [(0.020, zf + 0.548), (0.392, zf + 0.548), (0.412, zf + 0.560),
                (0.422, zf + 0.582), (0.418, zf + 0.596), (0.398, zf + 0.602),
                (0.300, zf + 0.602), (0.296, zf + 0.592), (0.020, zf + 0.592)],
           cx, cy, seg=26)                                    # 轮盘 Ø0.85
    for k in range(8):                                        # 轮辐
        a0 = TAU * k / 8
        _bar(bm, (cx + math.cos(a0) * 0.060, cy + math.sin(a0) * 0.060, zf + 0.544),
             (cx + math.cos(a0) * 0.392, cy + math.sin(a0) * 0.392, zf + 0.544),
             0.026, 0.020)
    _annulus(bm, cx, cy, zf + 0.598, zf + 0.606, 0.392, 0.420, 26)   # 轮缘铜箍
    # 脚踏杆 + 踏板
    _bar(bm, (cx + 0.280, cy, zf + 0.150), (cx + 0.720, cy, zf + 0.040),
         0.038, 0.032)
    _boxb(bm, cx + 0.680, cx + 0.800, cy - 0.075, cy + 0.075, zf + 0.020,
          zf + 0.040, 0.005, 1)
    for j in range(6):
        x = cx+.689+j*.018
        _bar(bm,(x,cy-.065,zf+.041),(x,cy+.065,zf+.041),.005,.003)
    mu.cylinder(bm,(cx+.28,cy,zf+.15),.019,.12,segments=16,axis="Y")
    _bar(bm,(cx+.28,cy+.037,zf+.15),(cx+.10,cy+.037,zf+.40),.020,.022)
    _emit(C, bm, M, P + "wheel", "exhibit", coll,
          cn=cn + "·单轴木质拉坯陶车", mat="wood_dark")

    # 刚拉坯成型的湿润泥坯水滴梅瓶（轮制旋纹）
    zmb = zf + 0.5965
    bm = mu.new_bm()
    # Revolve the entire wall profile, deforming its outer radius in the
    # potter's wheel coordinates. Rim, hollow interior and bottom stay closed.
    zs=sorted(set([j/64 for j in range(65)]+[z for r,z in PROF_MEIPING[:12]]))
    profile=[(.26,0.)]+[(_zr([(.0,.52),(.06,.58),(.19,.55),(.34,.66),
                               (.47,.97),(.63,1.),(.76,.90),(.84,.62),(.90,.40),
                               (.94,.34),(1.,.34)],z),z) for z in zs]
    profile.extend(PROF_MEIPING[12:])
    meridians=mu.revolve(bm,[(r*.105,zmb+u*.32) for r,u in profile],(cx,cy,0.),segments=72)
    for i,meridian in enumerate(meridians):
        ang=TAU*i/len(meridians)
        for v,(_,u) in zip(meridian[1:1+len(zs)],profile[1:1+len(zs)]):
            deform=.0008*math.sin(TAU*(19*u-ang/TAU))*math.sin(math.pi*u)**2
            for level,n in ((.30,10),(.42,10),(.66,6)):
                da=math.remainder(ang-level*3.,TAU/n)
                deform-=.0026*math.exp(-((u-level)/.017)**2-(da/.080)**2)
            v.co.x+=deform*math.cos(ang)
            v.co.y+=deform*math.sin(ang)
    mu.cap_ring(bm,[m[0] for m in meridians],flip=True)
    mu.cap_ring(bm,[m[-1] for m in meridians])
    _emit(C,bm,M,P+"wet_blank","exhibit",coll,cn=cn+"·湿坯梅瓶（轮制旋纹与指压凹窝）",mat="clay_wet")

    # 木水桶 + 海绵 + 牛骨修坯刀 + 割泥铜线
    bx, by = -4.05, -1.15
    bm = mu.new_bm()
    _lathe(bm, [(0.086, zf + FLIFT), (0.104, zf + FLIFT), (0.110, zf + 0.020),
                (0.114, zf + 0.150), (0.112, zf + 0.186), (0.100, zf + 0.186),
                (0.100, zf + 0.150), (0.096, zf + 0.020), (0.086, zf + 0.012)],
           bx, by, seg=18)
    _tube(bm,[(bx+.109*math.cos(t),by,zf+.171+.104*math.sin(t))
               for t in [math.pi*j/24 for j in range(25)]],.0045,8)
    _emit(C, bm, M, P + "bucket", "detail", coll,
          cn=cn + "·木水桶", mat="wood_lite")
    bm = mu.new_bm()
    for zz in (0.045, 0.140):
        r0=.110+.004*(zz-.020)/.130+.00012
        r1=.110+.004*min(1.,(zz+.012-.020)/.130)+.00012
        _lathe_closed(bm,[(r0,zf+zz),(r0+.006,zf+zz),(r1+.006,zf+zz+.012),(r1,zf+zz+.012)],
                      bx,by,seg=18)
    _emit(C, bm, M, P + "bucket_hoops", "detail", coll,
          cn=cn + "·水桶铜箍", mat="brass")

    bm = mu.new_bm()
    # Sponge lobes share a continuous, corrugated skin and a flat floor contact.
    rows=[]
    for zz,scale in ((0.,.76),(.008,1.),(.052,.95),(.066,.82),(.071,.43)):
        row=[]
        for j in range(32):
            ang=TAU*j/32
            r=scale*(1.+.07*math.cos(5*ang)+.045*math.sin(9*ang+.8))
            row.append(_v(bm,-3.90+.045*r*math.cos(ang),-.92+.035*r*math.sin(ang),
                          zf+FLIFT+zz+(.002*math.sin(5*ang) if zz else 0.)))
        if rows:
            mu.bridge_rings(bm,rows[-1],row,closed=True)
        rows.append(row)
    mu.cap_ring(bm,rows[0],flip=True)
    mu.cap_ring(bm,rows[-1])
    _emit(C, bm, M, P + "sponge", "detail", coll,
          cn=cn + "·海绵块", mat="mount_gold")

    bm = mu.new_bm()
    rib=_bez([(-.072,-.003),(-.055,-.010),(-.009,-.012),(.038,-.005),
              (.070,.008),(.073,.015),(.052,.018),(.011,.008),(-.042,.007)],4,True)
    _fill2(bm,[(-4.28+x,-.91+y) for x,y in rib],zf+FLIFT,zf+FLIFT+.004)
    _emit(C, bm, M, P + "rib_tool", "detail", coll,
          cn=cn + "·牛骨修坯刀", mat="bisque")

    bm = mu.new_bm()
    for yy in (-2.43,-2.17):
        _tube(bm,[(-4.82,yy,zf+.012),(-4.75,yy,zf+.010),(-4.68,yy,zf+.011)],.009,10)
    _tube(bm,[(-4.75-.06*math.sin(math.pi*j/20),-2.43+.26*j/20,zf+.007)
              for j in range(21)],.0008,6)
    _emit(C, bm, M, P + "cut_wire", "detail", coll,
          cn=cn + "·割泥铜线", mat="brass")

    # ---------------- 中央画坯青料工作大案 w2.60×d1.10
    w, d, h = 2.60, 1.10, 0.86
    zt = zf + h
    bm = mu.new_bm()
    _boxb(bm, -w / 2, w / 2, -d / 2, d / 2, zt - 0.052, zt, 0.007, 2)
    _boxb(bm, -w / 2 + 0.007, w / 2 - 0.007, -d / 2 + 0.007, d / 2 - 0.007,
          zt - 0.070, zt - 0.052, 0.0025, 1)
    ins = 0.090
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            lx = sx * (w / 2 - ins)
            ly = sy * (d / 2 - ins)
            _post(bm, lx, ly, zf + FLIFT, zt - 0.052, 0.096, 0.076)
            _boxb(bm, lx - 0.080, lx + 0.080, ly - 0.080, ly + 0.080,
                  zf + FLIFT, zf + FLIFT + 0.030, 0.004, 1)
    _apron(bm, "x", -w / 2 + ins, w / 2 - ins, -d / 2 + 0.012, zt - 0.070, 0.130, 0.018, 18, 0.88)
    _apron(bm, "x", -w / 2 + ins, w / 2 - ins, d / 2 - 0.012, zt - 0.070, 0.130, 0.018, 18, 0.88)
    _apron(bm, "y", -d / 2 + ins, d / 2 - ins, -w / 2 + 0.012, zt - 0.070, 0.120, 0.018, 8, 0.60)
    _apron(bm, "y", -d / 2 + ins, d / 2 - ins, w / 2 - 0.012, zt - 0.070, 0.120, 0.018, 8, 0.60)
    _bar(bm, (-w / 2 + ins, 0.0, zf + 0.22), (w / 2 - ins, 0.0, zf + 0.22),
         0.026, 0.038)
    _emit(C, bm, M, P + "desk", "exhibit", coll,
          cn=cn + "·画坯青料工作大案", mat="wood_lite")

    # 高岭土白色素坯梅瓶（半干生胎，瓶身半绘青花缠枝莲）
    vx, vy = -0.62, -0.02
    zvb = zt + LIFT
    bm = mu.new_bm()
    _vessel(bm, PROF_MEIPING, vx, vy, zvb, 0.108, 0.340, 18)
    _emit(C, bm, M, P + "bisque_vase", "exhibit", coll,
          cn=cn + "·高岭土素坯梅瓶（半干生胎）", mat="bisque")

    cobalt, pale = [], []
    for k in range(3):
        center = (.55+k*2.4, .40+k*.15)
        for petal in range(6):
            phi=TAU*petal/6+k*.4
            outline=[]
            for j in range(20):
                t=TAU*j/20
                along=.008*(1-math.cos(t))
                across=.003*math.sin(t)
                outline.append((center[0]+(along*math.cos(phi)-across*math.sin(phi))/.108,
                                center[1]+(along*math.sin(phi)+across*math.cos(phi))/.340))
            cobalt.append(outline)
    twists=[(.30+TAU*1.35*t+.55*math.sin(TAU*t),.34+.44*t) for t in [j/100 for j in range(101)]]
    cobalt.append([(ang,u+.003) for ang,u in twists]+[(ang,u-.003) for ang,u in reversed(twists)])
    for k in range(8):
        angle,u=twists[8+10*k]
        sign=(-1)**k
        pale.append([(angle+.13*(1-math.cos(t)),u+sign*.022*(1-math.cos(t))+.010*math.sin(t))
                     for t in [TAU*j/20 for j in range(20)]])
    for i,(polys,name,mat,label) in enumerate(((cobalt,"blue_sketch","cobalt_2","缠枝莲"),
                                                (pale,"blue_leaves","cobalt_1","卷草叶纹"))):
        bm=mu.new_bm()
        _paint_lathe(bm,polys,PROF_MEIPING,vx,vy,zvb,.108,.340,36,.00004+i*.00001)
        _emit(C,bm,M,P+name,"detail",coll,cn=cn+"·釉下彩绘层·"+label,mat=mat)

    # 苏麻离青研磨石钵 + 圆头杵
    mrx, mry = -0.14, -0.31
    bm = mu.new_bm()
    _lathe(bm, [(0.030, zt + LIFT), (0.062, zt + LIFT), (0.070, zt + LIFT + 0.008),
                (0.076, zt + LIFT + 0.040), (0.082, zt + LIFT + 0.052),
                (0.072, zt + LIFT + 0.054), (0.066, zt + LIFT + 0.040),
                (0.060, zt + LIFT + 0.014), (0.030, zt + LIFT + 0.010)],
           mrx, mry, seg=18)
    _emit(C, bm, M, P + "cobalt_mortar", "detail", coll,
          cn=cn + "·苏麻离青研磨石钵", mat="stone_dark")
    bm = mu.new_bm()
    _lathe(bm,[(.004,.0101),(.008,.012),(.009,.016),(.006,.020),(.006,.024)],
           mrx+.009,mry,zt+LIFT,12)
    _tube(bm,[(mrx+.009,mry,zt+LIFT+.021),(mrx+.021,mry+.005,zt+LIFT+.060),
              (mrx+.038,mry+.012,zt+LIFT+.108)],.006,12,r_end=.010)
    _emit(C, bm, M, P + "cobalt_pestle", "detail", coll,
          cn=cn + "·圆头杵", mat="stone_dark")

    # 五色试片瓷盘
    tpx, tpy = 0.36, -0.29
    bm = mu.new_bm()
    _lathe(bm, [(0.018, zt + LIFT), (0.078, zt + LIFT), (0.090, zt + LIFT + 0.006),
                (0.096, zt + LIFT + 0.014), (0.088, zt + LIFT + 0.016),
                (0.076, zt + LIFT + 0.010), (0.018, zt + LIFT + 0.006)],
           tpx, tpy, seg=18)
    _emit(C, bm, M, P + "test_plate", "detail", coll,
          cn=cn + "·五色试片瓷盘", mat="bisque")
    for k, mat in enumerate(("cobalt_0", "cobalt_1", "cobalt_2", "cobalt_3", "cobalt_4")):
        a = TAU * k / 5 + 0.55
        tx = tpx + math.cos(a) * 0.050
        ty = tpy + math.sin(a) * 0.050
        bm = mu.new_bm()
        _boxb(bm, tx - 0.013, tx + 0.013, ty - 0.013, ty + 0.013,
              zt + LIFT + 0.0095, zt + LIFT + 0.0122, 0.0016, 1)
        _emit(C, bm, M, P + "test_tile_%d" % (k + 1), "detail", coll,
              cn=cn + "·试片", mat="bisque")
        bm = mu.new_bm()
        _disc(bm, tx, ty, zt + LIFT + 0.0124, 0.0112, 0.0012, 12)
        _emit(C, bm, M, P + "test_color_%d" % (k + 1), "detail", coll,
              cn=cn + "·青料发色试片（%d/5 浓度）" % (k + 1), mat=mat)

    # 两支长锋羊毫分水大笔 + 一支铁骨勾线小笔
    for k, (pxs, pr, nm) in enumerate(((0.62, 0.0072, "长锋羊毫分水大笔甲"),
                                       (0.70, 0.0068, "长锋羊毫分水大笔乙"),
                                       (0.78, 0.0042, "铁骨勾线小笔"))):
        bm = mu.new_bm()
        _pen(bm, pxs, -0.300, 0.260, zt + LIFT + pr, pr, 8, 0.0110 if k < 2 else 0.0070)
        _emit(C, bm, M, P + "brush_%d" % (k + 1), "detail", coll,
              cn=cn + "·" + nm, mat="bamboo")

    # ---------------- 靠山墙三层松木晾坯架（≤2.3m）
    ax0, ax1 = 5.02, 5.46
    bm = mu.new_bm()
    for py_ in (-2.15, 0.0, 2.15):
        for pxv in (ax0 + 0.024, ax1 - 0.024):
            _post(bm, pxv, py_, zf + FLIFT, zf + 1.90, 0.048, 0.042)
    for zz in (0.28, 0.80, 1.32, 1.90):
        _boxb(bm, ax0, ax1, -2.15, 2.15, zf + zz, zf + zz + 0.022, 0.0035, 1)
    for py_ in (-2.15, 0.0, 2.15):
        _boxb(bm, ax0 - 0.010, ax0 + 0.010, py_ - 0.010, py_ + 0.010,
              zf + 0.30, zf + 1.88, 0.002, 1)
    _emit(C, bm, M, P + "drying_rack", "exhibit", coll,
          cn=cn + "·三层松木晾坯架", mat="wood_lite")

    shelves = ((0.302, (-1.70, -1.20, -0.70), (0.20, 0.90, 1.60)),
               (0.822, (-1.70, -1.20, -0.70), (0.00, 0.70, 1.40)),
               (1.342, (-1.70, -1.20), (-0.40, 0.40)))
    # Turning marks are circumferential grooves in the clay wall profile.
    bowl_profile=PROF_WAN[:5]+[(.983,.930),(.966,.943),(.990,.967)]+PROF_WAN[5:]
    vase_profile=PROF_YUHUCHUN[:10]+[(.36,.961),(.342,.972),(.36,.985)]+PROF_YUHUCHUN[10:]
    for si,(zsh,bowls,vases) in enumerate(shelves):
        for rows,profile,key,label,r,h in (
                (bowls,bowl_profile,"bowls","白胎直口碗",.062,.058),
                (vases,vase_profile,"vases","白胎玉壶春瓶",.052,.190)):
            bm=mu.new_bm()
            for yy in rows:
                _vessel(bm,profile,5.24,yy,zf+zsh+LIFT,r,h,14)
            _emit(C,bm,M,P+f"{key}_{si+1}","detail",coll,cn=cn+"·"+label+"（修坯槽）",mat="bisque")

    # 顶层青花缠枝莲大盖罐（成品，带盖鼓腹）
    jx, jy = 5.24, 1.50
    zjb = zf + 1.342 + LIFT
    bm = mu.new_bm()
    _vessel(bm, PROF_JAR, jx, jy, zjb, 0.105, 0.255, 18)
    _emit(C, bm, M, P + "big_jar", "exhibit", coll,
          cn=cn + "·青花缠枝莲大盖罐", mat="bisque")
    bm = mu.new_bm()
    _vessel(bm, PROF_JAR_LID, jx, jy, zjb + 0.255 + .0001, 0.135, 0.170, 18)
    _emit(C, bm, M, P + "big_jar_lid", "detail", coll,
          cn=cn + "·大盖罐盖", mat="bisque")
    bm = mu.new_bm()
    vine=[(TAU*2.6*t,t) for t in [.16+j*.72/100 for j in range(101)]]
    band=[(angle,u+.004) for angle,u in vine]+[(angle,u-.004) for angle,u in reversed(vine)]
    _paint_lathe(bm,[band],PROF_JAR,jx,jy,zjb,.105,.255,36,.00005)
    _emit(C,bm,M,P+"big_jar_pattern","detail",coll,cn=cn+"·成品釉下彩绘层",mat="cobalt_3")


# ============================================================================
# 5 镂金坊：民间剪纸（刻花 → 剪刻 → 透光展陈）
# ============================================================================
def _plyz(bm, pts, xa, xb):
    """YZ 平面多边形沿 X 挤出 4mm —— 剪纸的「实纸片」（不镂空处就是纸）。"""
    ps = _dedupe(list(pts))
    if len(ps) > 2 and math.hypot(ps[0][0] - ps[-1][0], ps[0][1] - ps[-1][1]) < 1e-6:
        ps = ps[:-1]
    if len(ps) < 3:
        return
    # 去掉共线/近重复点：封口 ngon 里若含共线点，三角化会产生零面积面
    keep = []
    n0 = len(ps)
    for k in range(n0):
        a, p, c = ps[(k - 1) % n0], ps[k], ps[(k + 1) % n0]
        cr = (p[0] - a[0]) * (c[1] - a[1]) - (p[1] - a[1]) * (c[0] - a[0])
        if abs(cr) > 3.0e-9:
            keep.append(p)
    ps = keep
    if len(ps) < 3:
        return
    ar = 0.0
    for k in range(len(ps)):
        a, c = ps[k], ps[(k + 1) % len(ps)]
        ar += a[0] * c[1] - c[0] * a[1]
    if abs(ar) * 0.5 < 2.0e-6:
        return
    r0 = [_v(bm, xa, p[0], p[1]) for p in ps]
    r1 = [_v(bm, xb, p[0], p[1]) for p in ps]
    mu.bridge_rings(bm, r0, r1, closed=True)
    mu.cap_ring(bm, r0, flip=True)
    mu.cap_ring(bm, r1, flip=False)


def _xi_glyph(bm, yc, zc, hw, hh, x0, x1, wid=0.016):
    """「喜」字（剪纸实笔画）：士 / 口 / 丷+一 / 口 / 一，逐笔为实纸带。
    结构照字书：上「士」两横一竖，两「口」作方框，中横最长，下有「丷」两点。"""
    def hbar(v, hwid, th):
        _box(bm, x0, x1, yc - hwid, yc + hwid,
             zc + v * hh - th * 0.5, zc + v * hh + th * 0.5)

    def vbar(u, v0, v1, th):
        _box(bm, x0, x1, yc + u - th * 0.5, yc + u + th * 0.5,
             zc + v0 * hh, zc + v1 * hh)

    def frame(u_half, v0, v1, th):
        hbar(v1, u_half, th)
        hbar(v0, u_half, th)
        vbar(-u_half, v0, v1, th)
        vbar(u_half, v0, v1, th)

    hbar(0.470, hw * 0.98, wid)             # 士：上横
    vbar(0.0, 0.320, 0.470, wid)            # 士：竖
    hbar(0.320, hw * 0.84, wid)             # 士：下横
    frame(hw * 0.72, 0.110, 0.270, wid)     # 口（一）
    hbar(0.020, hw * 0.98, wid * 1.05)      # 中横（全字最长）
    for sg in (-1.0, 1.0):                  # 丷
        _plyz(bm, [(yc + sg * 0.40 * hw, zc + 0.070 * hh),
                   (yc + sg * 0.58 * hw, zc + 0.100 * hh),
                   (yc + sg * 0.58 * hw, zc + 0.062 * hh)], x0, x1)
    frame(hw * 0.72, -0.250, -0.110, wid)   # 口（二）
    hbar(-0.400, hw * 0.98, wid)            # 底横


def _ellr(cu, cv, ru, rv, ang, n=14):
    """旋转椭圆（cu,cv 在 YZ 平面）。"""
    ca, sa = math.cos(ang), math.sin(ang)
    out = []
    for k in range(n):
        t = TAU * k / float(n)
        c, s_ = math.cos(t), math.sin(t)
        out.append((cu + ru * c * ca - rv * s_ * sa,
                    cv + ru * c * sa + rv * s_ * ca))
    return out


def _bird(bm, yc, zc, sc, x0, x1, wid=0.011, tail=False):
    """实纸飞鸟（正面剪影）：横身 + 头喙 + 双翼三出羽 + 尾扇。sc=尺度，翼展≈0.14*sc 米。"""
    b = 0.070 * sc
    _plyz(bm, _ell(yc, zc, 0.20 * b, 0.34 * b, 14), x0, x1)                  # 身
    _plyz(bm, _ell(yc, zc + 0.44 * b, 0.155 * b, 0.155 * b, 12), x0, x1)     # 头
    _plyz(bm, [(yc + 0.08 * b, zc + 0.48 * b), (yc + 0.30 * b, zc + 0.40 * b),
               (yc + 0.08 * b, zc + 0.34 * b)], x0, x1)                      # 喙
    for sg in (-1.0, 1.0):                                                   # 双翼（三出羽）
        _plyz(bm, [(yc + sg * 0.10 * b, zc + 0.16 * b),
                   (yc + sg * 0.52 * b, zc + 0.64 * b),
                   (yc + sg * 0.78 * b, zc + 0.44 * b),
                   (yc + sg * 0.56 * b, zc + 0.36 * b),
                   (yc + sg * 0.96 * b, zc + 0.24 * b),
                   (yc + sg * 0.60 * b, zc + 0.16 * b),
                   (yc + sg * 0.98 * b, zc - 0.02 * b),
                   (yc + sg * 0.44 * b, zc - 0.06 * b),
                   (yc + sg * 0.10 * b, zc - 0.14 * b)], x0, x1)
    if tail:
        for k in (-1, 0, 1):
            _plyz(bm, [(yc + k * 0.075 * b, zc - 0.28 * b),
                       (yc + k * 0.135 * b, zc - 0.96 * b),
                       (yc + (k * 0.135 - 0.055) * b, zc - 0.86 * b),
                       (yc + (k * 0.075 - 0.055) * b, zc - 0.28 * b)], x0, x1)
    else:
        _plyz(bm, [(yc - 0.13 * b, zc - 0.28 * b), (yc + 0.13 * b, zc - 0.28 * b),
                   (yc + 0.09 * b, zc - 0.72 * b), (yc, zc - 0.62 * b),
                   (yc - 0.09 * b, zc - 0.72 * b)], x0, x1)


def _fenghuang(bm, yc, zc, sc, x0, x1):
    """凤鸟：鸟形 + 凤冠三出 + 长尾三缕（sc=尺度，翼展≈0.14*sc 米）。"""
    b = 0.070 * sc
    _bird(bm, yc, zc, sc, x0, x1, tail=True)
    for k in range(3):                                                       # 凤冠
        _plyz(bm, [(yc + (k - 1) * 0.14 * b, zc + 0.56 * b),
                   (yc + (k - 1) * 0.34 * b, zc + 1.08 * b - abs(k - 1) * 0.16 * b),
                   (yc + (k - 1) * 0.02 * b, zc + 0.74 * b)], x0, x1)


def _jianzhi(C, H):
    coll = C.coll("展陈", H["cn"])
    M = _M(H)
    zf = H["floor"]
    P = "cr_jianzhi_"
    cn = H["cn"]

    # ---------------- 正中手工剪刻雕花案 w2.20×d1.00×h0.78
    w, d, h = 2.20, 1.00, 0.78
    zt = zf + h
    bm = mu.new_bm()
    _boxb(bm, -w / 2, w / 2, -d / 2, d / 2, zt - 0.048, zt, 0.007, 2)
    _boxb(bm, -w / 2 + 0.007, w / 2 - 0.007, -d / 2 + 0.007, d / 2 - 0.007,
          zt - 0.066, zt - 0.048, 0.0025, 1)
    ins = 0.080
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            lx = sx * (w / 2 - ins)
            ly = sy * (d / 2 - ins)
            _post(bm, lx, ly, zf + FLIFT, zt - 0.048, 0.088, 0.070)
            _boxb(bm, lx - 0.072, lx + 0.072, ly - 0.072, ly + 0.072,
                  zf + FLIFT, zf + FLIFT + 0.028, 0.004, 1)
    _apron(bm, "x", -w / 2 + ins, w / 2 - ins, -d / 2 + 0.012, zt - 0.066, 0.120, 0.018, 16, 0.88)
    _apron(bm, "x", -w / 2 + ins, w / 2 - ins, d / 2 - 0.012, zt - 0.066, 0.120, 0.018, 16, 0.88)
    _apron(bm, "y", -d / 2 + ins, d / 2 - ins, -w / 2 + 0.012, zt - 0.066, 0.110, 0.018, 8, 0.62)
    _apron(bm, "y", -d / 2 + ins, d / 2 - ins, w / 2 - 0.012, zt - 0.066, 0.110, 0.018, 8, 0.62)
    _bar(bm, (-w / 2 + ins, 0.0, zf + 0.20), (w / 2 - ins, 0.0, zf + 0.20),
         0.024, 0.034)
    _emit(C, bm, M, P + "desk", "exhibit", coll,
          cn=cn + "·手工剪刻雕花案", mat="wood_dark")

    # 天然蜂蜡牛油刻花蜡盘（厚 0.05，边缘刀痕）
    wx, wy = -0.50, 0.06
    ww, wd = 0.46, 0.34
    zw = zt + LIFT
    bm = mu.new_bm()
    cuts=[]
    for k in range(9):
        y=wy-wd/2+.024+k*.036
        cuts.append(([(wx-.190,y),(wx+.190,y+.012)],.00035,0.,False))
    for k in range(5):
        x=wx-.170+k*.085
        cuts.append(([(x,wy-.130),(x+.030,wy+.130)],.00035,0.,False))
    rim=_carved_face(bm,(wx-ww/2,wx+ww/2,wy-wd/2,wy+wd/2),zw+.0494,.0006,cuts)
    base=[_v(bm,v.co.x,v.co.y,zw) for v in rim]
    mu.bridge_rings(bm,base,rim,closed=True)
    bm.faces.new(base[::-1])
    _emit(C,bm,M,P+"wax_pad","exhibit",coll,cn=cn+"·蜂蜡刻花盘与交叉浅刀槽",mat="amber")

    # 大红宣纸垛（几十层 + 纸捻穿孔紧固）
    sx_, sy_ = 0.30, -0.12
    sw, sd = 0.34, 0.26
    zs = zt + LIFT
    bm = mu.new_bm()
    holes=[(sx_+dx,sy_+dy) for dx,dy in ((-.13,-.10),(.13,-.10),(-.13,.10),(.13,.10),(0.,0.))]
    outlines=[_ell(x,y,.0069,.0069,24) for x,y in holes]
    sheet=(.025-25*PSEAM)/26
    for k in range(26):
        ox=.0012*math.sin(k*2.3)
        oy=.0010*math.cos(k*1.9)
        lo=zs+k*(sheet+PSEAM)
        _bored_plate(bm,(sx_-sw/2+ox,sx_+sw/2+ox,sy_-sd/2+oy,sy_+sd/2+oy),
                     outlines,lo,lo+sheet)
    _emit(C,bm,M,P+"red_paper_stack","detail",coll,cn=cn+"·五孔万年红纸垛（25 mm）",mat="crimson")
    bm=mu.new_bm()
    for x,y in holes:
        mu.cylinder(bm,(x,y,zs+.0001),.0064,.0258,segments=24)
        _tube(bm,[(x,y,zs+.027),(x+.012,y+.002,zs+.027),
                  (x+.021,y-.003,zs+.0269)],.00175,8)
    _emit(C, bm, M, P + "paper_twists", "detail", coll,
          cn=cn + "·纸捻穿孔紧固", mat="paper_xuan")

    # 4 把不同刀头刻刀（斜口/月牙冲/扁刃/尖刀）
    names = ("斜口刀", "月牙冲", "扁刃刀", "尖头刀")
    for k in range(4):
        kx = 0.78 + k * 0.062
        y0, y1 = 0.020, 0.320
        bm = mu.new_bm()
        _tube(bm, [(kx, y0, zt + LIFT + 0.0115), (kx, y1, zt + LIFT + 0.0115)],
              0.0115, 8)
        _annulus(bm, kx, y1 - 0.010, zt + LIFT + 0.0085, zt + LIFT + 0.0145,
                 0.0105, 0.0135, 8)
        _emit(C, bm, M, P + "knife_handle_%d" % (k + 1), "detail", coll,
              cn=cn + "·刻刀木柄·" + names[k], mat="wood_dark")
        bm = mu.new_bm()
        yi = y1 - 0.004     # 刀头根部埋入柄内 4mm（避免端面与柄口共面）
        if k == 0:      # 斜口
            _boxb(bm, kx - 0.009, kx + 0.009, yi, y1 + 0.052, zt + LIFT + 0.004,
                  zt + LIFT + 0.016, 0.002, 1)
            _boxb(bm, kx - 0.009, kx + 0.009, y1 + 0.040, y1 + 0.062,
                  zt + LIFT + 0.004, zt + LIFT + 0.009, 0.002, 1)
        elif k == 1:    # 月牙冲
            _tube(bm, [(kx - 0.010, yi, zt + LIFT + 0.010),
                       (kx - 0.006, y1 + 0.040, zt + LIFT + 0.016),
                       (kx + 0.006, y1 + 0.052, zt + LIFT + 0.010),
                       (kx + 0.010, y1 + 0.030, zt + LIFT + 0.004)], 0.0042, 5)
        elif k == 2:    # 扁刃
            _boxb(bm, kx - 0.026, kx + 0.026, yi, y1 + 0.048, zt + LIFT + 0.006,
                  zt + LIFT + 0.013, 0.0018, 1)
            _boxb(bm, kx - 0.026, kx + 0.026, y1 + 0.040, y1 + 0.058,
                  zt + LIFT + 0.006, zt + LIFT + 0.0085, 0.0012, 1)
        else:           # 尖头
            _tube(bm, [(kx, yi, zt + LIFT + 0.0115), (kx, y1 + 0.070,
                                                      zt + LIFT + 0.0085)],
                  0.0055, 6, r_end=0.0008)
        _emit(C, bm, M, P + "knife_tip_%d" % (k + 1), "detail", coll,
              cn=cn + "·刀头·" + names[k], mat="steel")

    # 案头精钢长柄尖头细剪刀 + 黑铁老剪刀
    bm = mu.new_bm()
    cx0, cy0 = -0.94, 0.32
    for sgn in (-1.0, 1.0):
        _boxb(bm, cx0 - 0.004, cx0 + 0.004, cy0 + sgn * 0.012, cy0 + sgn * 0.300,
              zt + LIFT + 0.004, zt + LIFT + 0.010, 0.0018, 1)
        _boxb(bm, cx0 - 0.013, cx0 + 0.013, cy0 + sgn * 0.300, cy0 + sgn * 0.345,
              zt + LIFT + 0.004, zt + LIFT + 0.010, 0.0018, 1)
        _annulus(bm, cx0, cy0 + sgn * 0.372, zt + LIFT + 0.002,
                 zt + LIFT + 0.012, 0.008, 0.018, 10)
    _annulus(bm, cx0, cy0, zt + LIFT, zt + LIFT + 0.014, 0.005, 0.011, 10)
    _emit(C, bm, M, P + "scissors_fine", "exhibit", coll,
          cn=cn + "·精钢长柄尖头细剪刀", mat="steel")

    bm = mu.new_bm()
    ex0, ey0 = 1.052, 0.28
    for sgn in (-1.0, 1.0):
        _boxb(bm, ex0 - 0.007, ex0 + 0.007, ey0 + sgn * 0.014, ey0 + sgn * 0.150,
              zt + LIFT + 0.005, zt + LIFT + 0.013, 0.0026, 1)
        _annulus(bm, ex0, ey0 + sgn * 0.176, zt + LIFT + 0.003,
                 zt + LIFT + 0.015, 0.009, 0.020, 10)
    _annulus(bm, ex0, ey0, zt + LIFT, zt + LIFT + 0.016, 0.006, 0.012, 10)
    _emit(C, bm, M, P + "scissors_iron", "exhibit", coll,
          cn=cn + "·黑铁老剪刀", mat="stone_dark")

    # 彩色宣纸卷（3~4 卷）
    for k, (mats, ccp) in enumerate((("crimson", "大红"), ("mount_gold", "槐黄"),
                                     ("celadon", "石绿"), ("stone_lite", "白") )):
        bm = mu.new_bm()
        mu.cylinder(bm, (-1.00 + k * 0.062, -0.44, zt + LIFT + 0.028),
                    0.026, 0.300, segments=12, axis="Y")
        _emit(C, bm, M, P + "paper_roll_%d" % (k + 1), "detail", coll,
              cn=cn + "·彩色宣纸卷·" + ccp, mat=mats)

    # 展开的民俗花样底本线装折页
    bm = mu.new_bm()

    def fold_fn(u, v):
        x = -0.02 + 0.260 * u
        y = 0.300 + 0.170 * v
        z = zt + LIFT + 0.0012 + 0.0075 * abs(math.sin(u * math.pi * 3.0))
        return Vector((x, y, z))

    _panel(bm, fold_fn, 24, 4, (0.0, 0.0, 0.0016))
    _emit(C, bm, M, P + "pattern_book", "exhibit", coll,
          cn=cn + "·民俗花样底本线装折页", mat="paper_xuan")
    bm = mu.new_bm()
    for row in range(3):
        ring=[]
        for j in range(1,48):
            u=j/48
            y=.327+row*.052+.008*math.sin(4*TAU*u)+.003*math.sin(9*TAU*u)
            station=min(23,int(24*u))
            t=24*u-station
            z=(1-t)*fold_fn(station/24,0).z+t*fold_fn((station+1)/24,0).z
            ring.append([_v(bm,-.02+.26*u,y+dy,z+.00166) for dy in (-.0009,.0009)])
        for l,r in zip(ring,ring[1:]):
            bm.faces.new((l[0],r[0],r[1],l[1]))
    _emit(C, bm, M, P + "pattern_lines", "detail", coll,
          cn=cn + "·底本白描花样（墨线）", mat="lacquer")

    # ---------------- 临水窗：镂空红木透光屏风展架 + 双喜百鸟朝凤窗花
    px_, dh = 5.16, 0.045
    bm = mu.new_bm()
    for sy in (-0.920, 0.920):
        _post(bm, px_, sy, zf + FLIFT, zf + 2.150, 0.062, 0.054)
        _boxb(bm, px_ - 0.095, px_ + 0.095, sy - 0.085, sy + 0.085,
              zf + FLIFT, zf + FLIFT + 0.055, 0.006, 1)
    _boxb(bm, px_ - 0.032, px_ + 0.032, -0.950, 0.950, zf + 2.096, zf + 2.150, 0.005, 1)
    _boxb(bm, px_ - 0.026, px_ + 0.026, -0.950, 0.950, zf + 0.380, zf + 0.440, 0.004, 1)
    _boxb(bm, px_ - 0.026, px_ + 0.026, -0.950, 0.950, zf + 1.900, zf + 1.960, 0.004, 1)
    for sign in (-1.,1.):
        yy=sign*.760
        for xa,xb in ((px_-.024,px_-.00225),(px_+.00225,px_+.024)):
            _boxb(bm,xa,xb,yy-.022,yy+.022,zf+.440,zf+1.900,.001,1)
        _box(bm,px_-.00225,px_+.00225,yy+sign*.0004,yy+sign*.022,zf+.440,zf+1.900)
        _box(bm,px_-.003,px_+.003,sign*.719,sign*.730,zf+.440,zf+.4519)
    # 透雕角花（四个角）
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            _tube(bm, [(px_ - 0.028, sx * 0.740, zf + 0.470 + (0.0 if sz < 0 else 1.360)),
                       (px_ - 0.028, sx * 0.640, zf + 0.520 + (0.0 if sz < 0 else 1.260)),
                       (px_ - 0.028, sx * 0.600, zf + 0.470 + (0.0 if sz < 0 else 1.360))],
                  0.0055, 5)
    _emit(C, bm, M, P + "screen_frame", "exhibit", coll,
          cn=cn + "·镂空红木透光屏风展架", mat="wood_dark")

    # 窗花：厚 0.004 的实纸片，镂空处即无几何（真镂空：双喜 + 凤鸟 + 百鸟 + 缠枝云）
    xa, xb = px_ - 0.002, px_ + 0.002
    bm = mu.new_bm()
    zc0 = zf + 0.440
    zc1 = zf + 1.900
    for zz in (zc0 + 0.022, zc1 - 0.022, zc0 + 0.052, zc1 - 0.052):     # 双线外框
        _bar2(bm, (-0.742, zz), (0.742, zz), 0.020, xa, xb)
    for yy in (-0.742, 0.742, -0.712, 0.712):
        _bar2(bm, (yy, zc0 + 0.022), (yy, zc1 - 0.022), 0.020, xa, xb)
    # 双喜（两字并置，字口留 24mm 间距）
    for yc_ in (-0.148, 0.148):
        _xi_glyph(bm, yc_, zf + 1.090, 0.122, 0.430, xa, xb, 0.019)
    # 凤鸟在上，两侧各一对小凤
    _fenghuang(bm, 0.0, zf + 1.640, 2.60, xa, xb)
    for sy_ in (-1.0, 1.0):
        _fenghuang(bm, sy_ * 0.470, zf + 1.680, 1.45, xa, xb)
    # 百鸟环飞（身 + 翼 + 尾，实片）
    for (yy_, zz_, sc_, tl) in ((-0.560, zf + 1.560, 1.30, 1), (0.560, zf + 1.560, 1.30, 1),
                                (-0.600, zf + 1.240, 1.10, 0), (0.600, zf + 1.240, 1.10, 0),
                                (-0.610, zf + 0.900, 1.05, 1), (0.610, zf + 0.900, 1.05, 1),
                                (-0.320, zf + 0.700, 0.95, 0), (0.320, zf + 0.700, 0.95, 0),
                                (0.0, zf + 0.660, 1.05, 1)):
        _bird(bm, yy_, zz_, sc_, xa, xb, tail=bool(tl))
    # 下摆缠枝云纹（实片卷云，三瓣相叠）
    for k in range(24):                                  # 缠枝藤（实片细带，起伏）
        ya = -0.640 + k * 0.0556
        yb = ya + 0.0556
        za = zf + 0.520 + 0.022 * math.sin(k * 1.1)
        zb = zf + 0.520 + 0.022 * math.sin((k + 1) * 1.1)
        _bar2(bm, (ya, za), (yb, zb), 0.011, xa, xb)
    # Three tapering, curved leaves per junction; each has a through-cut vein.
    for root_y in (-.56,-.28,0.,.28,.56):
        root_z = zf + .52 + .022*math.sin((root_y+.64)/.0556*1.1)
        for bend, length in ((-.070,.105),(.068,.108),(.012,.082)):
            outside, inside = [], []
            for j in range(32):
                angle = TAU*j/32
                t = .5 - .5*math.cos(angle)
                def contour(t, width):
                    return (root_y + bend*t**1.4 + width*math.sin(angle)*(1.-.38*t),
                            root_z + length*t)
                outside.append(contour(t,.013))
                inside.append(contour(.22+.58*t,.005))
            rings = [[_v(bm, xx,y,z) for y,z in loop]
                     for xx,loop in ((xa,outside),(xb,outside),(xb,inside),(xa,inside))]
            for k in range(4):
                mu.bridge_rings(bm,rings[k],rings[(k+1)%4],closed=True)
    # 四角卷云（实片，两旋）
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            cz = zf + (1.760 if sz > 0 else 0.600)
            _plyz(bm, _ellr(sx * 0.660, cz, 0.075, 0.030, sx * sz * 0.55, 14), xa, xb)
            _plyz(bm, _ellr(sx * 0.585, cz + sz * 0.034, 0.045, 0.020, sx * sz * 1.10, 12),
                  xa, xb)
    _emit(C, bm, M, P + "paper_cut", "exhibit", coll,
          cn=cn + "·双喜百鸟朝凤大红镂空窗花（实纸片/真镂空）", mat="crimson")


# ============================================================================
# 装配
# ============================================================================
_BUILDERS = {
    "zhuxianzhen": _zhuxianzhen,
    "songhua": _songhua,
    "bianxiu": _bianxiu,
    "qinghua": _qinghua,
    "jianzhi": _jianzhi,
}


def _stats(objs):
    tri = 0
    x0 = y0 = z0 = 1.0e9
    x1 = y1 = z1 = -1.0e9
    for ob in objs:
        tri += mu.tri_count(ob)
        mw = ob.matrix_world
        for vt in ob.data.vertices:
            co = mw @ vt.co
            x0 = min(x0, co.x)
            x1 = max(x1, co.x)
            y0 = min(y0, co.y)
            y1 = max(y1, co.y)
            z0 = min(z0, co.z)
            z1 = max(z1, co.z)
    if not objs:
        x0 = y0 = z0 = x1 = y1 = z1 = 0.0
    return tri, (x0, x1, y0, y1, z0, z1)


def build(C):
    """入口：五馆室内非遗工序陈列。返回本次新建的对象列表。"""
    import time
    n0 = len(C.objects)
    t0 = time.time()
    new = []
    for hall in ORDER:
        h0 = len(C.objects)
        _BUILDERS[hall](C, HALLS[hall])
        objs = list(C.objects[h0:])
        new.extend(objs)
        tri, bb = _stats(objs)
        print("[crafts] %-11s %3d 对象 %6d tri bbox=(%.2f..%.2f, %.2f..%.2f, %.2f..%.2f)"
              % (hall, len(objs), tri, bb[0], bb[1], bb[2], bb[3], bb[4], bb[5]))
        for ob in objs:
            mz = min((ob.matrix_world @ vt.co).z for vt in ob.data.vertices)
            if mz < HALLS[hall]["floor"] - 0.0005:
                print("[crafts] !! %s min(z)=%.4f 低于地坪 %.3f"
                      % (ob.name, mz, HALLS[hall]["floor"]))
    tri, bb = _stats(new)
    print("[crafts] %d 对象 %d tri bbox=(%.2f..%.2f, %.2f..%.2f, %.2f..%.2f) %.2fs"
          % (len(new), tri, bb[0], bb[1], bb[2], bb[3], bb[4], bb[5],
             time.time() - t0))
    return new