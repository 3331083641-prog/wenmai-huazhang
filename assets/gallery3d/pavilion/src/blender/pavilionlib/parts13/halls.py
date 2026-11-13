# -*- coding: utf-8 -*-
"""v13 配殿群：四座 12x12 配殿（前殿单层 / 后阁二层）+ 镂金坊 + 环水连廊 + 后苑点景。

尺寸唯一真源：pavilionlib/dim13.py（DIM13）。本文件不写死任何总图尺寸，
只写由 DIM13 派生/按任务书 m00001+m01291 追加的构造值，逐条注明来源。

一、四馆两种类型（中心/朝向见 dim13.HALLS；门一律朝中轴）
  A 型 单层（西前殿 刊木堂 -32,-30 / 东前殿 针经阁 +32,-30）
     台明顶 0.20（任务书"0.20 高素石台明，外扩 1.0m"）→ 室内地坪 0.20
     柱顶 6.00（dim13 SIDE_COL_H 作为绝对标高，与 v11 口径一致）
     普拍枋 6.00..6.12 / 斗拱 6.12..6.40 / 檐口 6.40 / 歇山转折 8.60 / 脊帽顶 10.20
  B 型 二层阁（西后轩 澄怀轩 -32,-12 / 东后阁 素肌堂 +32,-12；m01291）
     一层净高 3.60 → 结构梁 3.80..4.10（0.30）→ 楼板 4.10..4.26（0.16）
     **二层楼面顶 = 4.26**（= 0.20 + 3.60 + 0.30 + 0.16）。
     说明：m01291 写的"二层楼面 z=3.60"与"一层净高 3.60 + 梁 0.30 + 板 0.16
     藏在楼面下"三者不能同时成立——若楼面顶取 3.60，一层净高只剩 2.94，
     3.6x3.9 的门洞放不下。此处取"净高 3.60 + 门洞 3.9"为先，楼面顶落 4.26。
     二层设 6.0x6.0 通高中庭 + 沿内墙 2.72m 宽回廊（≥1.6m）；
     楼梯靠后墙折返两跑：22 级 x 踏面 0.30 x 踏宽 1.10，休息平台 1.10x1.20，
     踢面 = (4.26-0.20)/22 = 0.1845；二层楼面开真实楼梯井 + ≥0.9 栏板。
     二层柱顶 6.90 / 普拍枋 6.90..7.02 / 斗拱 7.02..7.30 / 檐口 7.30 /
     歇山转折 8.10 / 脊帽顶 9.60（m01291）。
     门洞仍按任务书 3.6x3.9（0.20..4.10，板底 4.10，留 2mm）。
     一层槛窗 2.00..3.20（让出挂画带 0.30..1.95）；二层槛窗 4.70..6.20。
  A 型槛窗 3.20..4.80（挂画带 0.30..3.10）。

二、缝 / 偏移清单（全部为实体之间的净距，复核用）
  S1 台明底 0.008（台基面 0 上方 8mm 空气缝，"凹缝"），台明顶 0.200
  S2 门扇外面距墙外面 30mm；门框内面距墙内面 15mm；门框外面距墙外面 20mm
  S3 槛窗框四周凹入墙面 20mm，玻璃在墙厚正中（不与墙共面）
  S4 檐墙顶 6.00（B 型 6.90），栱眼壁顶 = 屋面内缘 soffit - 0.02
  S5 屋面 soffit 在墙线 = z_break - ROOF_THICK（8.26 / 7.76），与墙顶留 60/40mm
  S6 连廊屋面 soffit 在柱线 3.908，与普拍枋顶 3.900 留 8mm
  S7 连廊台明顶 0.150，配殿台明顶 0.200，两石活最近 0.60m（x=25.00 与 24.40）
  S8 两层楼板外边 5.70（墙内面 5.72，留 20mm 不共面）
  S9 栏杆/栏板距墙面 ≥0.20m（楼梯栏杆外缘 y=5.45，墙内面 5.72 → 0.27）
  S10 台明与连廊台明、与牌楼柱均不接触（见 _report 实测）
  S11 连廊屋面内檐 20.10 悬于池岸压顶（20.55）之上，竖向 3.9m，无接触
  S12 瓦面与结构层：roofkit 的 thick 内建，瓦垄起伏只作用在顶面

三、为让开既有实体所做的退让（只在本文件生效，不改 dim13）
  R1 连廊在水院西南角做缺口绕开镂金坊：西廊南端 y=-37.70，距镂金坊北墙
     (-38.50) 0.80；南廊西端 x=-12.40，距镂金坊东墙 (-14.00) 1.60
  R2 镂金坊东檐 1.60→0.80（东檐口 x=-13.20），距牌楼边楼 x=-12.40 留 0.80，
     距牌楼柱面 (-12.46) 0.74；北檐 1.60→0.55（北檐口 y=-37.95），
     距连廊西廊屋面端头 (-37.70) 留 0.25；西/南檐仍 1.60
  R3 连廊檐口不对称：内（水院侧）0.90、外（馆舍侧）0.55；
     外檐口 24.95 距配殿山墙 26.00 留 1.05（若用 dim13 CL_EAVE_OUT=0.90 只剩 0.70）
  R4 配殿歇山翼角冲出 0.55→0.30：前后两馆屋面角部净距
     6.00 - 2x2.60 - 2x(0.30x0.7071) = 0.376m（默认 0.55 时只剩 0.02）
"""
from __future__ import annotations

import math

from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from ..dim13 import DIM13 as D
from .. import mesh_util as mu
from .. import roofkit as rk

TAU = math.tau
ROOF_THICK = D.ROOF_THICK            # 0.34
_DBG = False                          # 临时：屋面分段面数诊断（交付前置 False）

# ============================================================ 配殿（局部坐标：中心原点、门朝 -Y）
HX = D.SIDE_HX                       # 6.0
HY = D.SIDE_HY                       # 6.0
EAVE_OUT = D.SIDE_EAVE_OUT           # 2.60
WALL_T = D.SIDE_WALL_T               # 0.28
DOOR_W = D.SIDE_DOOR_W               # 3.60
DOOR_H = D.SIDE_DOOR_H               # 3.90
COL_R = 0.28
IW = HX - COL_R                      # 5.72 室内墙面（与檐柱内切 → 室内绝对平面）
OW = HX + WALL_T * 0.5               # 6.14 墙外面
PLINTH_H = 0.20                      # 任务书：素石台明 0.20
PLINTH_OUT = 1.00                    # 任务书：外扩 1.0m
GAP = 0.008                          # 台明底 8mm 凹缝
BAYS = (-6.0, -2.6, 2.6, 6.0)        # 3x3 柱网（v11 口径：明间 5.2 / 次间 3.4）
Z_FLOOR = PLINTH_H                   # 0.20
WALL_LIFT = 0.008                    # 墙体底面离台明顶 8mm（避免与柱础底面共面）

# A 型（单层）
A_COL_TOP = D.SIDE_COL_H             # 6.00
A_EAVE = D.SIDE_EAVE_Z               # 6.40
A_BREAK = D.SIDE_BREAK_Z             # 8.60
A_RIDGE = D.SIDE_RIDGE_Z             # 10.20（脊帽顶）
A_WALL_TOP = 6.00
A_WIN_Z = (3.20, 4.80)

# B 型（二层阁，m01291）
B_CLEAR1 = 3.60                      # 一层净高
B_BEAM_H = 0.30                      # 结构梁
B_SLAB_H = 0.16                      # 楼板
B_SLAB_BOT = Z_FLOOR + B_CLEAR1 + B_BEAM_H          # 4.10
B_SLAB_TOP = B_SLAB_BOT + B_SLAB_H                  # 4.26
B_COL_TOP = 6.90
B_EAVE = 7.30
B_BREAK = 8.10
B_RIDGE = 9.60
B_WALL_TOP = B_COL_TOP
B_WIN1_Z = (2.00, 3.20)
B_WIN2_Z = (4.70, 6.20)
B_ATRIUM = 3.00                      # 中庭半宽（6.0x6.0）
B_CORR_IN = 5.72                     # 回廊内侧 = 墙内面
B_STAIR = dict(
    x0=0.90, x1=-2.40,               # 第一跑：从 x=0.90 向 -x 上到休息平台
    land0=-4.60, land1=-2.40,        # 休息平台 x
    y0=3.20, y1=4.30,                # 第一跑 y
    y2=4.35, y3=5.45,                # 第二跑 y
    w=0.30, n=11,
)

# ============================================================ 镂金坊
JP = dict(cx=D.JP_CX, cy=D.JP_CY, hx=D.JP_HX, hy=D.JP_HY, floor=D.JP_FLOOR,
          col_h=D.JP_COL_H, eave=D.JP_EAVE_Z, ridge=D.JP_RIDGE_Z,
          dw=D.JP_DOOR_W, dh=D.JP_DOOR_H)
JP_R = 0.24
JP_IWX = JP["hx"] - JP_R             # 5.76
JP_IWY = JP["hy"] - JP_R             # 3.26
JP_OW = JP["hx"] + WALL_T * 0.5      # 6.14
JP_OWY = JP["hy"] + WALL_T * 0.5     # 3.64
JP_PLINTH = 0.60
JP_COL_TOP = JP["floor"] + JP["col_h"]   # 3.75
JP_PUP = (JP_COL_TOP, JP_COL_TOP + 0.12)  # 3.75..3.87
JP_WALL_TOP = JP_COL_TOP
JP_BREAK = 4.75
JP_RIDGE_IN = JP["ridge"] - 0.84          # 5.36（脊帽顶 6.20）
JP_OUT = dict(x0=1.60, y0=1.60, x1=0.80, y1=0.55)   # 西/南/东/北（见 R2）
JP_PLINTH_BOX = (-26.60, -46.10, -13.40, -37.90)   # 0.6 外扩

# ============================================================ 连廊
CL_IN_X = D.CL_IN_X                  # 21.00
CL_OUT_X = D.CL_OUT_X                # 24.40
CL_IN_YS, CL_OUT_YS = D.CL_IN_YS, D.CL_OUT_YS    # -37.00 / -40.40
CL_IN_YN, CL_OUT_YN = D.CL_IN_YN, D.CL_OUT_YN    # -13.40 / -10.00
CL_EAVE = D.CL_EAVE_Z                # 3.90
CL_TOP = D.CL_ROOF_TOP               # 5.20
CL_STEP = D.CL_COL_STEP              # 3.40
CL_SLAB = 0.150                      # 台明顶面（任务书）
CL_EAVE_IN = 0.90                    # 内檐（R3）
CL_EAVE_OUT = 0.55                   # 外檐（R3）
CL_COL_TOP = 3.75                    # 0.15 + 3.60
CL_PUP = (3.75, 3.90)
CL_ROOF_T = 0.20
CL_OPEN = D.CL_N_OPEN                # 6.00 半宽 → 12m 穿堂
CX_W = -(CL_IN_X + CL_OUT_X) * 0.5   # -22.70
CX_E = (CL_IN_X + CL_OUT_X) * 0.5    # +22.70
CY_N = (CL_IN_YN + CL_OUT_YN) * 0.5  # -11.70
CY_S = (CL_IN_YS + CL_OUT_YS) * 0.5  # -38.70
CL_U_COL = 1.55                      # 柱列距中线
CL_U_OUT = -(CL_OUT_X - CL_IN_X) * 0.5 - CL_EAVE_OUT   # -2.25
CL_U_IN = (CL_OUT_X - CL_IN_X) * 0.5 + CL_EAVE_IN      # +2.60
CL_PATH_A = [(-CL_OPEN, CY_N), (CX_W, CY_N), (CX_W, -37.70)]
CL_PATH_B = [(-12.40, CY_S), (CX_E, CY_S), (CX_E, CY_N), (CL_OPEN, CY_N)]
CL_PLAT = (
    (-12.40, CL_OUT_YS, CL_OUT_X, CL_IN_YS),          # 南廊
    (CL_IN_X, CL_IN_YS, CL_OUT_X, CL_IN_YN),          # 东廊（-37.00..-13.40）
    (-CL_OUT_X, CL_IN_YN, CL_OUT_X, CL_OUT_YN),       # 北廊
    (-CL_OUT_X, -37.70, -CL_IN_X, CL_IN_YN),          # 西廊（南端 -37.70，R1）
)

# ============================================================ 后苑
RG_TREES = D.RG_TREES
RG_LANTERNS = D.RG_LANTERNS
RG_TREE_H = D.RG_TREE_H


# v15 构造常量（侧脚/生起）
SIDE_IN = 0.008          # 侧脚斜率，单位 m/m。
CORNER_RISE = 0.040


def _column_head(x, y, zc):
    edge_x, edge_y = abs(x) == HX, abs(y) == HY
    top = zc - 0.012 + (CORNER_RISE if edge_x and edge_y else 0)
    shrink = SIDE_IN * (top - Z_FLOOR) if edge_x or edge_y else 0
    r = math.hypot(x, y)
    return Vector((x - shrink * x / r, y - shrink * y / r, top))


def _head_frame(bm, zc, zf):
    # Ring sections use a shared miter at every post. Both the lintel and the
    # transverse ties reference the same measured post centres as the ring.
    posts = ([(x, -HY) for x in BAYS] + [(HX, y) for y in BAYS[1:]]
             + [(x, HY) for x in reversed(BAYS[:-1])] + [(-HX,y) for y in reversed(BAYS[1:-1])])
    heads = [_column_head(x, y, zc) for x, y in posts]
    rings = []
    for i, h in enumerate(heads):
        prev, after = heads[i - 1], heads[(i + 1) % len(heads)]
        ta = (h - prev).to_2d().normalized()
        tb = (after - h).to_2d().normalized()
        na, nb = Vector((ta.y, -ta.x)), Vector((tb.y, -tb.x))
        miter = (na + nb) / (1 + na.dot(nb))
        section = []
        for width, dz in ((.12,-.112),(.12,0),(-.12,0),(-.12,-.112)):
            section.append(_v(bm, h.x + width*miter.x, h.y + width*miter.y,
                              h.z + zf - (zc - .012) + dz))
        rings.append(section)
    for i, h in enumerate(heads):
        j = (i + 1) % len(heads)
        mu.bridge_rings(bm, rings[i], rings[j], closed=True)
        end = heads[j]
        unit = (end - h).normalized()
        # Lintel tenons terminate ~60 mm inside the 210 mm column radius.
        offset = Vector((0, 0, -.11))
        _bar(bm, h + .15*unit + offset, end - .15*unit + offset, .23, .20)
    for yy in BAYS[1:-1]:
        # Beam heads bear into the two eave posts. Interior posts are plumb.
        for x0, x1 in zip(BAYS, BAYS[1:]):
            left, right = _column_head(x0, yy, zc), _column_head(x1, yy, zc)
            unit = (right - left).normalized()
            offset = Vector((0, 0, -.39))
            _bar(bm, left + .15*unit + offset, right - .15*unit + offset, .22, .26)


# ============================================================ 基础小工具
def _box(bm, x0, x1, y0, y1, z0, z1):
    return mu.box_mm(bm, min(x0, x1), max(x0, x1), min(y0, y1),
                     max(y0, y1), min(z0, z1), max(z0, z1))


def _quad(bm, a, b, c, d):
    try:
        bm.faces.new([bm.verts.new(Vector(p)) if not hasattr(p, "co") else p
                      for p in (a, b, c, d)])
    except ValueError:
        pass


def _v(bm, x, y, z):
    return bm.verts.new(Vector((x, y, z)))


def _frustum(bm, cx, cy, h0, h1, z0, z1):
    a = [_v(bm, cx - h0, cy - h0, z0), _v(bm, cx + h0, cy - h0, z0),
         _v(bm, cx + h0, cy + h0, z0), _v(bm, cx - h0, cy + h0, z0)]
    b = [_v(bm, cx - h1, cy - h1, z1), _v(bm, cx + h1, cy - h1, z1),
         _v(bm, cx + h1, cy + h1, z1), _v(bm, cx - h1, cy + h1, z1)]
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([a[i], a[j], b[j], b[i]])
    bm.faces.new(a[::-1])
    bm.faces.new(b)


def _bar(bm, p0, p1, w, h):
    """沿 p0-p1 的方梁（w 水平宽、h 竖向高）。"""
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
    for f in idx:
        bm.faces.new([vs[i] for i in f])
    return vs


def _wbox(bm, axis, p0, p1, a0, a1, z0, z1):
    if axis == "y":
        _box(bm, a0, a1, p0, p1, z0, z1)
    else:
        _box(bm, p0, p1, a0, a1, z0, z1)


def _emit(C, bm, M, name, cat, coll, cn, mat="wood_dark", **kw):
    if len(bm.verts) == 0:
        bm.free()
        return None
    if M is not None:
        for v in bm.verts:
            v.co = M @ v.co
    mu.recalc_normals(bm)
    return C.bm_obj(bm, name, cat, coll, cn=cn, mat=mat, **kw)


# ============================================================ 墙面开洞 / 门窗
def _wall_grid(bm, axis, p0, p1, a0, a1, z0, z1, holes):
    """按矩形洞口把墙切成若干实体盒（网格法，洞内不填）。"""
    holes = [h for h in holes if h[0] < a1 and h[1] > a0 and h[2] < z1 and h[3] > z0]
    acuts = {a0, a1}
    zcuts = {z0, z1}
    for (ha0, ha1, hz0, hz1) in holes:
        for v in (ha0, ha1):
            if a0 + 1e-6 < v < a1 - 1e-6:
                acuts.add(v)
        for v in (hz0, hz1):
            if z0 + 1e-6 < v < z1 - 1e-6:
                zcuts.add(v)
    aa = sorted(acuts)
    zz = sorted(zcuts)
    for i in range(len(aa) - 1):
        for j in range(len(zz) - 1):
            ca0, ca1 = aa[i], aa[i + 1]
            cz0, cz1 = zz[j], zz[j + 1]
            am = (ca0 + ca1) * 0.5
            zm = (cz0 + cz1) * 0.5
            if any(h[0] - 1e-9 <= am <= h[1] + 1e-9 and
                   h[2] - 1e-9 <= zm <= h[3] + 1e-9 for h in holes):
                continue
            if ca1 - ca0 < 1e-4 or cz1 - cz0 < 1e-4:
                continue
            _wbox(bm, axis, p0, p1, ca0, ca1, cz0, cz1)


def _wall_bays(bm, axis, p0, p1, a0, a1, z0, z1, holes, cols, ct, r=0.240, n=6,
               r_base=0.372, base_h=0.30, beam_level=None):
    """分段墙：在柱位断开，段端沿柱面圆弧收进（真实让槽，柱面留 10mm 缝）。

    * cols：墙内柱位的 a 坐标（升序）；柱位处墙不连续，墙板让到柱面外
    * ct：柱心法向坐标（±HX / ±HY），圆弧量 sqrt(r^2-(u-ct)^2)
    * r：让槽半径 = 柱身最大半径 0.23 + 10mm = 0.240（不接触、不共面）
    * r_base/base_h：柱础（r=0.36）让槽，墙脚 0.30 高内按 0.372 收进，
      否则柱础 0.72 直径会插进 0.48 宽的柱身让槽（v15 审计 col × walls 根因）
    * 墙厚方向切 n 条竖带，带端按各自深度收进；同 bm 归集，内部贴合面不外露
    """
    t0, t1 = (p0, p1) if p0 < p1 else (p1, p0)
    th = t1 - t0
    edges = [a0] + [c for c in cols if a0 + 1e-6 < c < a1 - 1e-6] + [a1]
    for bi in range(len(edges) - 1):
        b0, b1 = edges[bi], edges[bi + 1]
        hs = [h for h in holes if h[0] < b1 and h[1] > b0]
        for k in range(n):
            u0 = t0 + th * k / n
            u1 = t0 + th * (k + 1) / n
            openings = hs
            if beam_level is not None and min(abs(u0), abs(u1)) < abs(ct) - 0.10:
                # 梁端由室内伸入柱头，两侧各留 4 mm 安装间隙。
                openings = hs + [(v - 0.145, v + 0.145, beam_level - 0.145, beam_level + 0.145)
                                 for v in cols]
            # 取该竖带内**离柱心最近**的深度算圆弧（带边缘最危险），
            # 否则带端会插进柱身（v15 审计 col × walls 的根因）
            if u1 <= ct:
                um = ct - u1
            elif u0 >= ct:
                um = u0 - ct
            else:
                um = 0.0
            q = r * r - um * um
            da = math.sqrt(q) if q > 0.0 else 0.0
            qb = r_base * r_base - um * um
            dab = math.sqrt(qb) if qb > 0.0 else 0.0
            sa = da          # 段首贴柱（含角柱：四角都有柱，墙不得伸进柱身）
            sb = da          # 段尾贴柱
            if b1 - b0 - sa - sb < 0.06:
                continue
            zb = z0 + base_h
            if zb < z1 - 0.02 and b1 - b0 - dab * 2.0 > 0.06:
                # 墙脚一段：柱础让槽更大；其上按柱身让槽
                _wall_grid(bm, axis, u0, u1, b0 + dab, b1 - dab, z0, zb, openings)
                _wall_grid(bm, axis, u0, u1, b0 + sa, b1 - sb, zb, z1, openings)
            else:
                _wall_grid(bm, axis, u0, u1, b0 + sa, b1 - sb, z0, z1, openings)


def _window(bw, bg, axis, p0, p1, a0, a1, z0, z1, nmid=None):
    """槛窗：框（凹入墙面 20mm）+ 棂条 + 玻璃（墙厚正中）。"""
    mid = (p0 + p1) * 0.5
    d0, d1 = mid - 0.05, mid + 0.05
    fr = 0.06
    # 四边框
    # 框比洞口每边退 5mm：不与该处墙面 0 间隙平接（v15 框嵌墙问题）
    g = 0.005
    _wbox(bw, axis, d0, d1, a0 + g, a0 + fr, z0, z1)
    _wbox(bw, axis, d0, d1, a1 - fr, a1 - g, z0, z1)
    _wbox(bw, axis, d0, d1, a0 + fr, a1 - fr, z0, z0 + fr)
    _wbox(bw, axis, d0, d1, a0 + fr, a1 - fr, z1 - fr, z1 - g)
    # 竖棂（0.24 分格）
    n = max(1, int(round((a1 - a0 - 2 * fr) / 0.24)))
    for i in range(1, n):
        c = a0 + fr + (a1 - a0 - 2 * fr) * i / n
        _wbox(bw, axis, mid - 0.02, mid + 0.02, c - 0.017, c + 0.017,
              z0 + fr, z1 - fr)
    # 横棂（0.55 分格）
    m = max(1, int(round((z1 - z0 - 2 * fr) / 0.55)))
    for j in range(1, m):
        c = z0 + fr + (z1 - z0 - 2 * fr) * j / m
        _wbox(bw, axis, mid - 0.02, mid + 0.02, a0 + fr, a1 - fr,
              c - 0.017, c + 0.017)
    # 玻璃位于内侧棂条背后 1 mm，框内四边各留 5 mm 安装缝。
    pane = mid - math.copysign(0.028, mid)
    _wbox(bg, axis, pane - 0.007, pane + 0.007, a0 + fr + g, a1 - fr - g,
          z0 + fr + g, z1 - fr - g)


def _obox(bm, f, x0, x1, y0, y1, z0, z1):
    """在任意平面框架 f(x,y,z)->点 上放一个六面体（法线由 _emit 统一重算）。"""
    pts = [f(x0, y0, z0), f(x1, y0, z0), f(x1, y1, z0), f(x0, y1, z0),
           f(x0, y0, z1), f(x1, y0, z1), f(x1, y1, z1), f(x0, y1, z1)]
    vs = [_v(bm, p[0], p[1], p[2]) for p in pts]
    for fc in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
               (2, 3, 7, 6), (3, 0, 4, 7)):
        try:
            bm.faces.new([vs[i] for i in fc])
        except ValueError:
            pass


def _prism_plane(bm, axis, pts, t0, t1):
    """墙平面内的多边形 pts=[(a,z)...] 沿墙法向 t0..t1 挤出的棱柱。"""
    def mk(a, t, z):
        return (a, t, z) if axis == "y" else (t, a, z)
    aa = [_v(bm, *mk(p[0], t0, p[1])) for p in pts]
    bb = [_v(bm, *mk(p[0], t1, p[1])) for p in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        try:
            bm.faces.new([aa[i], aa[j], bb[j], bb[i]])
        except ValueError:
            pass
    for ring in (aa, bb):
        try:
            bm.faces.new(ring)
        except ValueError:
            pass


def _queti(bm, axis, t_in, sgn_in, a_corner, sgn_a, z_top):
    """门额雀替（角蝉）：0.55 长 x 0.30 高 x 0.08 厚，45 度斜边 + 卷草线脚。

    贴在门洞上角、室内面外 0.10（不与墙面共面），随门框一起用 wood_dark。
    """
    L, H, T = 0.55, 0.30, 0.08
    p0 = a_corner
    tri = [(p0, z_top), (p0 + sgn_a * L, z_top), (p0, z_top - H)]
    _prism_plane(bm, axis, tri, t_in + sgn_in * 0.10, t_in + sgn_in * 0.18)
    # 卷草线脚：沿斜边三段小方条（比斜面凸 0.012，错开 0.004）
    for k in range(3):
        f0 = 0.12 + k * 0.26
        f1 = f0 + 0.16
        x0 = p0 + sgn_a * L * f0
        z0 = z_top - H * f0
        _prism_plane(bm, axis, [(x0, z0), (p0 + sgn_a * L * f1, z_top - H * f1),
                                (x0 + sgn_a * 0.05, z0)],
                     t_in + sgn_in * 0.184, t_in + sgn_in * 0.196)


def _leaf_open(bm, w, h, P, ux, uy, zb=0.0):
    """一扇格心门（铰链在 P，宽向 ux、厚向 uy，frame 内 x 0..w、z 0..h）。"""
    st, th = 0.080, 0.0275

    def f(x, y, z):
        return (P[0] + ux[0] * x + uy[0] * y,
                P[1] + ux[1] * x + uy[1] * y, zb + z)

    _obox(bm, f, 0.0, st, -th, th, 0.0, h)              # 铰链侧边梃
    _obox(bm, f, w - st, w, -th, th, 0.0, h)            # 开启侧边梃
    # 注意：循环变量不能叫 zb，否则遮蔽函数参数 zb（门扇整体抬高 h 的 bug）
    for (zlo, zhi) in ((0.0, 0.10), (0.86, 0.94), (h - 0.10, h)):
        _obox(bm, f, st, w - st, -th, th, zlo, zhi)     # 抹头
    _obox(bm, f, st + 0.010, w - st - 0.010, -0.0125, 0.0125,
          0.10, 0.86)                                    # 裙板
    z0, z1 = 0.94, h - 0.10
    n = max(2, int(round((w - 2 * st) / 0.20)))
    for i in range(1, n):
        c = st + (w - 2 * st) * i / n
        _obox(bm, f, c - 0.015, c + 0.015, -0.018, 0.018, z0, z1)
    m = max(2, int(round((z1 - z0) / 0.42)))
    for j in range(1, m):
        c = z0 + (z1 - z0) * j / m
        _obox(bm, f, st, w - st, -0.018, 0.018, c - 0.015, c + 0.015)
    return f


def _door(bm_w, bm_d, bm_g, axis, p0, p1, a0, a1, z0, z1):
    """双扇格心门以关闭位装配，前端沿内面两侧铰链向内开启。"""
    if abs(p0) > abs(p1):
        outer, inner = p0, p1
    else:
        outer, inner = p1, p0
    sgn_in = -1.0 if outer > inner else 1.0     # 墙外 -> 室内
    sgn_out = -sgn_in
    fr = 0.12
    f0 = inner - sgn_out * 0.015                # 框内面：比墙内面深 15mm
    f1 = outer - sgn_out * 0.020                # 框外面：比墙外面深 20mm
    for aa in ((a0 + 0.009, a0 + fr), (a1 - fr, a1 - 0.009)):
        _wbox(bm_d, axis, f0, f1, aa[0], aa[1], z0, z1 - 0.004)
    _wbox(bm_d, axis, f0, f1, a0 + fr, a1 - fr, z1 - fr, z1 - 0.004)  # 上槛
    # 门额雀替：左右各一，45 度贴角
    # 雀替安在门框的另一侧，与开启到 85° 的门扇错开。
    _queti(bm_d, axis, inner, sgn_out, a0 + fr, 1.0, z1 - fr)
    _queti(bm_d, axis, inner, sgn_out, a1 - fr, -1.0, z1 - fr)
    aw = (a1 - a0 - 2 * fr) * 0.5 - 0.010
    hinge = inner + sgn_in * 0.045
    for (a_h, sgn_a) in ((a0 + fr + 0.005, 1.0), (a1 - fr - 0.005, -1.0)):
        if axis == "y":
            ux = (sgn_a, 0.0, 0.0)
            uy = (0.0, sgn_a, 0.0)
            P = (a_h, hinge, 0.0)
        else:
            ux = (0.0, sgn_a, 0.0)
            uy = (-sgn_a, 0.0, 0.0)
            P = (hinge, a_h, 0.0)
        hh = (z1 - fr - .008) - (z0 + 0.02)
        f = _leaf_open(bm_d, aw, hh, P, ux, uy, zb=z0 + 0.02)
        # 8 mm 格心玻璃安在棂条背面，离棂 1 mm；薄于门梃 55 mm。
        _obox(bm_g, f, 0.09, aw - 0.09, 0.019, 0.027, 0.96, hh - 0.105)


def _railing(bm, pts, z0, h=0.90, post=0.08, rail=(0.06, 0.09)):
    """望柱 + 扶手（沿 pts 折线，z0 为地面）。"""
    for p in pts:
        _box(bm, p[0] - post * 0.5, p[0] + post * 0.5,
             p[1] - post * 0.5, p[1] + post * 0.5, z0, z0 + h - rail[1])
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        _bar(bm, (a[0], a[1], z0 + h - rail[1] * 0.5),
             (b[0], b[1], z0 + h - rail[1] * 0.5), rail[0], rail[1])
        _bar(bm, (a[0], a[1], z0 + 0.30), (b[0], b[1], z0 + 0.30), 0.04, 0.06)


# ============================================================ 屋面
def _roof(bm, outer, z_eave, inner, z_break, gable_x, ridge_y, z_ridge,
          lift, run_out, nv=8, gable_nu=None):
    """歇山一片：裙檐 + 上部两坡 + 正脊 + 4 垂脊（无 eave_course，v11 口径）。"""
    n0 = len(bm.verts)
    f0 = len(bm.faces)
    ep = rk.corrugated_skirt(bm, outer, z_eave, inner, z_break, lift=lift,
                             run_out=run_out, gauge=D.TILE_GAUGE,
                             amp=D.TILE_AMP, thick=ROOF_THICK, nv=nv,
                             mat=0, soffit=True)
    f1 = len(bm.faces)
    rk.gable_body(bm, inner, z_break, ridge_y, z_ridge, gable_x, mat=0,
                  thick=ROOF_THICK, nu=gable_nu, mat_barge=0)
    f2 = len(bm.faces)
    x0, y0, x1, y1 = inner
    rk.ridge_bar(bm, Vector((x0 - 0.12, ridge_y, z_ridge - 0.10)),
                 Vector((x1 + 0.12, ridge_y, z_ridge - 0.10)),
                 w=0.62, h=0.94, mat=0)
    crowns = []
    for ci in range(4):
        p = rk.hip_ridge_path(outer, z_eave, inner, z_break, ci, lift=lift,
                              n=6)
        # 垂脊按竖向逐皮砌筑。短戗脊若按法向平移 460 mm，会在翼角回弯处折叠。
        axis = (p[-1] - p[0]).normalized()
        side = Vector((-axis.y, axis.x, 0)).normalized()
        profile = rk._ridge_profile(0.36, 0.46)
        rings = [[mu.v(bm, q + side * u + Vector((0, 0, h))) for u, h in profile] for q in p]
        for lower, upper in zip(rings, rings[1:]):
            mu.bridge_rings(bm, lower, upper, closed=True)
        mu.cap_ring(bm, rings[0], flip=True)
        mu.cap_ring(bm, rings[-1], flip=False)
        crowns.append([q + Vector((0, 0, 0.46)) for q in p])
    f3 = len(bm.faces)
    rk._weld(bm, n0, 3.0e-4)
    if _DBG:
        print(f"[roofdbg] skirt={f1 - f0} gable={f2 - f1} ridge={f3 - f2} "
              f"faces  nv={nv}")
    return ep, crowns


def _gongyan(C, M, roof, name, cn, coll, hx, hy, width, z0, zmax):
    """依真实歇山底面收栱眼壁；四角用同一剖面闭合。"""
    tree = BVHTree.FromBMesh(roof)
    bm = mu.new_bm()
    corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    sections = []
    for i, a in enumerate(corners):
        b = corners[(i + 1) % 4]
        length = math.dist(a, b)
        n = math.ceil(length / 0.10)
        for k in range(n):
            t = k / n
            x, y = a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t
            outer = Vector((x, y, 0))
            inner = Vector((x*(hx-width)/hx, y*(hy-width)/hy, 0))
            top = zmax
            for j in range(9):
                probe = outer.lerp(inner, j / 8)
                pt, _, _, _ = tree.ray_cast((probe.x, probe.y, z0 + 0.001), (0, 0, 1))
                if pt is not None:
                    top = min(top, pt.z - .012)
            if top <= z0:
                raise ValueError(f"{name}: no height for spandrel at {x}, {y}")
            sections.append((outer, inner, top))
    rings = []
    for i,(outer, inner, top) in enumerate(sections):
        # 沿额枋的连续落脚带，在每攒栌斗/拱臂所在柱间留下真实开口。
        along = min(abs(outer.x), abs(outer.y))
        if name == "jianzhi":
            sill = JP_PUP[1] + .0005
        else:
            rise = CORNER_RISE * max(0.0, (along - 2.58) / (HX - 2.58))
            sill = z0 + .05 + rise + .001
            nearest = min(abs(along - station) for station in (0,2.6,4.3,6))
            if nearest <= .72:
                sill = z0 + .05 + rise + .36
        # Extend local valleys by one station to keep facets below the curved soffit.
        z = min(top, sections[i-1][2], sections[(i+1)%len(sections)][2])
        rings.append([_v(bm, v.x, v.y, h) for v,h in
                      ((outer,sill),(outer,z),(inner,z),(inner,sill))])
    for i, section in enumerate(rings):
        mu.bridge_rings(bm, section, rings[(i+1)%len(rings)], closed=True)
    _emit(C, bm, M, f"{name}_gongyan", "hall", coll, cn=f"{cn}·栱眼壁", mat="wall_white")


def _ridge_animals(C, M, crowns, name, cn):
    # Each foot lies on a single planar cap facet; short asymmetric hips at the
    # paper-cutting hall scale to the available length of the individual facet.
    animals = [(_proto_chuishou(C), "垂兽")]
    for kind, label in ((4, "骑凤"), (3, "凤"), (0, "狮"), (1, "马"), (2, "鱼龙")):
        animals.append((_proto_zoushou(C, kind), "走兽" + label))
    for ci, crown in enumerate(crowns):
        for a, b, (proto, label) in zip(crown[:-1], crown[1:], animals, strict=True):
            forward = (a - b).normalized()
            side = Vector((-forward.y, forward.x, 0.0)).normalized()
            normal = forward.cross(side).normalized()
            size = min(1.0, (b - a).length / 0.28)
            axes = Matrix((forward, side, normal)).transposed().to_4x4()
            pose = Matrix.Translation((a + b) * 0.5 + normal * 0.0005) @ axes
            C.place_world(proto, M @ pose @ Matrix.Scale(size, 4),
                          name=f"{name}_{ci}_{label}", cat="hall",
                          coll_path=("配殿", cn), cn=f"{cn}·{label}")


def _resample(path, step):
    """把 3D 折线按弧长重采样，返回 [(point, unit_tangent)]。"""
    pts = [Vector(p) for p in path]
    out = []
    carry = 0.0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        seg = (b - a).length
        if seg < 1e-9:
            continue
        d = (b - a) / seg
        t = carry
        while t < seg:
            out.append((a + d * t, d))
            t += step
        carry = t - seg
    if not out:
        out.append((pts[0], Vector((1, 0, 0))))
    return out


def _edge_tiles(bm, path, pitch, outward):
    # One tile back lies parallel to one rendered eave facet, 0.5 mm outside it.
    distances = [0.0]
    for a,b in zip(path,path[1:]):
        distances.append(distances[-1]+(b-a).to_2d().length)
    count=max(1,round(distances[-1]/pitch))
    i=0
    for k in range(count):
        dist=(k+.5)*distances[-1]/count
        while i+2<len(path) and distances[i+1]<dist:
            i+=1
        a,b=path[i:i+2]
        tangent=(b-a).to_2d().normalized()
        n=Vector((tangent.y,-tangent.x,0))
        if n.dot(outward(i))<0: n.negate()
        length=distances[i+1]-distances[i]
        if length < .14: continue
        mid=(dist-distances[i])/length
        # Keep both ends on this facet (also works at hard gallery miters).
        half=min(.057,length*.45)
        mid=max(half/length,min(1-half/length,mid))
        rows=[]
        for t in (mid-half/length,mid+half/length):
            q=a.lerp(b,t)
            rows.append([mu.v(bm,q+n*u+Vector((0,0,dz))) for u,dz in
                         ((.0005,-.105),(.052,-.105),(.052,-.018),(.0005,-.018))])
        mu.bridge_rings(bm,*rows,closed=True)
        mu.cap_ring(bm,rows[0],flip=True)
        mu.cap_ring(bm,rows[1],flip=False)


def _tile_ends(bm, ep, gauge):
    for path in ep.values():
        _edge_tiles(bm,path,gauge,lambda i: path[i])


# ============================================================ 斗拱 / 椽头 / 柱（原型）
def _prism_x(bm, prof_yz, x0, x1):
    """剖面 (y,z) 沿 X 挤出的棱柱（斗拱昂身/昂嘴用）。"""
    a = [_v(bm, x0, p[0], p[1]) for p in prof_yz]
    b = [_v(bm, x1, p[0], p[1]) for p in prof_yz]
    n = len(prof_yz)
    for i in range(n):
        j = (i + 1) % n
        try:
            bm.faces.new([a[i], a[j], b[j], b[i]])
        except ValueError:
            pass
    for ring in (a, b):
        try:
            bm.faces.new(ring)
        except ValueError:
            pass


def _round_y(bm, cx, y0, y1, r, zc, seg=6):
    """沿 Y 的圆椽（seg 棱柱近似，含两端封头）。"""
    ring = [(cx + r * math.cos(TAU * i / seg), zc + r * math.sin(TAU * i / seg))
            for i in range(seg)]
    a = [_v(bm, p[0], y0, p[1]) for p in ring]
    b = [_v(bm, p[0], y1, p[1]) for p in ring]
    for i in range(seg):
        j = (i + 1) % seg
        try:
            bm.faces.new([a[i], a[j], b[j], b[i]])
        except ValueError:
            pass
    for ring2 in (a, b):
        try:
            bm.faces.new(ring2)
        except ValueError:
            pass


def _eave_band(bm, ep, off0, off1, zlo, zhi, step=0.55):
    """沿檐口扫一条矩形带（封檐板/描边）：径向 off0..off1、竖向 zlo..zhi。

    与檐口端面留 off0 的空隙（>=0.03），不与瓦面/望板共面。
    """
    for path in ep.values():
        st = _resample(path, step)
        if len(st) < 2:
            continue
        rings = []
        for (p, d) in st:
            n = Vector((d.y, -d.x, 0.0))
            if n.dot(Vector((p.x, p.y, 0.0))) < 0:
                n = -n
            if n.length < 1e-9:
                continue
            n.normalize()
            q = (p + n * off0 + Vector((0, 0, zlo)),
                 p + n * off1 + Vector((0, 0, zlo)),
                 p + n * off1 + Vector((0, 0, zhi)),
                 p + n * off0 + Vector((0, 0, zhi)))
            rings.append([_v(bm, c.x, c.y, c.z) for c in q])
        for i in range(len(rings) - 1):
            for k in range(4):
                k2 = (k + 1) % 4
                try:
                    bm.faces.new([rings[i][k], rings[i][k2],
                                  rings[i + 1][k2], rings[i + 1][k]])
                except ValueError:
                    pass
        if _DBG:
            print(f"[banddbg] off={off0},{off1} z={zlo},{zhi} n={len(rings)} "
                  f"r0={tuple(round(v, 3) for v in rings[0][0].co)} "
                  f"r2={tuple(round(v, 3) for v in rings[0][2].co)}")
        for ring, rev in ((rings[0], True), (rings[-1], False)):
            try:
                bm.faces.new(ring[::-1] if rev else ring)
            except ValueError:
                pass


# ============================================================ 斗拱 / 椽头 / 吻兽 / 柱（原型）
def _gong5(bm, axis, a0, a1, t_c, halfw, z0, z1, n=5, cut=0.09, drop=0.05):
    """五瓣卷杀拱（宋《营造法式》卷杀）：端部 n 段折杀、中段等截面。

    axis="x"：拱沿 X 走（法向 Y）；axis="y"：拱沿 Y 走（法向 X）。
    t_c=法向中心、halfw=法向半宽；z0..z1 拱底..拱顶。约 40 tri/根。
    """
    s0, s1 = (a0, a1) if a0 < a1 else (a1, a0)
    cut = min(cut, (s1 - s0) * 0.42)
    prof = [(s0, z0)]
    for i in range(n + 1):                      # 左端卷杀（向上收 5 折）
        prof.append((s0 + cut * i / n, z1 - drop + drop * i / n))
    prof.append((s1 - cut, z1))
    for i in range(n - 1, -1, -1):              # 右端卷杀
        prof.append((s1 - cut * i / n, z1 - drop + drop * i / n))
    prof.append((s1, z0))
    _prism_plane(bm, axis, prof, t_c - halfw, t_c + halfw)


def _dou15(bm, cx=0.0, cy=0.0, z0=0.0, h=0.100, half=0.165, slot=0.048, ear=0.006,
           simple=False):
    """栌斗（v15）：斗底 + 四角斗欹（留出真实十字槽）+ 斗耳外唇。

    十字槽：四角各一块斗欹，中间留十字形通槽（槽半宽 slot），
    泥道拱（X 向）/华拱（Y 向）从槽中穿过 —— 真开槽不是贴面。
    """
    _frustum(bm, cx, cy, half * 1.02, half * 0.90, z0, z0 + h * 0.30)   # 斗底收分
    if simple:
        # 散斗：一段斗欹 + 一圈斗耳（24 tri，控 tri 不砍外形）
        _frustum(bm, cx, cy, half * 0.86, half * 0.72, z0 + h * 0.30, z0 + h * 0.82)
        _frustum(bm, cx, cy, half * 0.72 + ear, half * 0.72 + ear,
                 z0 + h * 0.82, z0 + h)
        return
    bx = half * 0.62
    off = slot + bx * 0.5
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            _frustum(bm, cx + sx * off, cy + sy * off, bx * 0.55, bx * 0.66,
                     z0 + h * 0.30, z0 + h * 0.86)                        # 斗欹
            _frustum(bm, cx + sx * off, cy + sy * off, bx * 0.66 + ear,
                     bx * 0.66 + ear, z0 + h * 0.86, z0 + h)              # 斗耳


def _proto_dougong(C):
    """v15 五铺作下昂（柱头/补间）：真实栌斗十字槽、五瓣卷杀、30 度昂尖、
    散斗、泥道拱/慢拱/瓜子拱/令拱、正心枋/柱头枋。

    局部：柱心原点、-Y 朝檐外、z=0 坐在普拍枋顶；整攒高 0.28、外挑 0.95。
    约 410 tri/攒；柱头与补间同一原型（v15 起角柱位置改用 45 度角铺作）。
    """
    def build(bm):
        _dou15(bm)                                          # 栌斗 0..0.10
        # 泥道拱（沿墙 1.00，五瓣卷杀；穿过栌斗 Y 向槽）
        _gong5(bm, "y", -0.50, 0.50, 0.0, 0.075, 0.100, 0.180,
               n=5, cut=0.10, drop=0.050)
        # 慢拱（沿墙 1.20）
        _gong5(bm, "y", -0.60, 0.60, 0.0, 0.070, 0.180, 0.235,
               n=4, cut=0.10, drop=0.038)
        # 华拱第一跳（外挑 0.30，X 向槽）
        _gong5(bm, "x", -0.300, 0.060, 0.0, 0.060, 0.100, 0.180,
               n=5, cut=0.075, drop=0.048)
        # 瓜子拱（第一跳跳头）
        _gong5(bm, "y", -0.35, 0.35, -0.260, 0.060, 0.180, 0.222,
               n=4, cut=0.070, drop=0.030)
        # 华拱第二跳（外挑到 0.58）
        _gong5(bm, "x", -0.580, 0.020, 0.0, 0.055, 0.180, 0.235,
               n=4, cut=0.070, drop=0.038)
        # 令拱（第二跳跳头 0.86）
        _gong5(bm, "y", -0.43, 0.43, -0.530, 0.060, 0.235, 0.275,
               n=5, cut=0.080, drop=0.030)
        # 散斗三枚（瓜子拱两端 + 令拱两端，斗欹带耳）
        for (dx, dy, dz) in ((-0.28, -0.26, 0.222), (0.28, -0.26, 0.222),
                             (-0.36, -0.53, 0.275), (0.36, -0.53, 0.275)):
            _dou15(bm, dx, dy, dz, h=0.042, half=0.062, slot=0.020,
                   ear=0.004, simple=True)
        # 正心枋 / 柱头枋（夹在栱眼壁内 0.02）
        _box(bm, -0.130, 0.130, -0.080, 0.020, 0.100, 0.275)
        _box(bm, -0.160, 0.160, -0.060, 0.040, 0.235, 0.280)
        # 下昂 30 度下冲实腹（穿二跳十字咬合）
        _prism_x(bm, [(-0.10, 0.250), (-0.88, 0.086), (-0.88, 0.120),
                      (-0.10, 0.278)], -0.050, 0.050)
        # 昂嘴：30 度斜削尖（尖点 -0.95、落差 0.074 = tan30 x 0.128）
        _prism_x(bm, [(-0.88, 0.086), (-0.95, 0.048), (-0.95, 0.052),
                      (-0.88, 0.120)], -0.044, 0.044)
    return C.proto("hall_dougong", build, mat="wood_dark", smooth=20.0)


def _proto_dougong_corner(C):
    """v15 转角铺作（45 度）：角栌斗 + 角华拱两跳 + 角昂 + 两条 45 度令拱臂。

    局部：-Y 指向建筑对角线外（放置时按 atan2(sx,-sy) 转 45 度），
    z=0 坐在角柱头普拍枋上（角柱生起 +0.04 已含在放置 z 里）。约 480 tri。
    """
    def build(bm):
        _dou15(bm, half=0.185)
        # 角华拱两跳（沿对角线）
        _gong5(bm, "x", -0.360, 0.050, 0.0, 0.065, 0.100, 0.185,
               n=5, cut=0.080, drop=0.050)
        _gong5(bm, "x", -0.660, 0.010, 0.0, 0.058, 0.185, 0.240,
               n=4, cut=0.075, drop=0.040)
        # 角昂（30 度，斜穿）
        _prism_x(bm, [(-0.12, 0.250), (-0.90, 0.090), (-0.90, 0.124),
                      (-0.12, 0.278)], -0.052, 0.052)
        _prism_x(bm, [(-0.90, 0.090), (-0.97, 0.052), (-0.97, 0.056),
                      (-0.90, 0.124)], -0.046, 0.046)
        # 两条 45 度令拱臂：在 0.50 半径处呈 X 交叉（沿两侧立面）
        for sd in (-1.0, 1.0):
            p0 = (-0.406 * sd, -0.50 + 0.406, 0.240)
            p1 = (0.406 * sd, -0.50 - 0.406, 0.240)
            _bar(bm, p0, p1, 0.105, 0.048)
            _dou15(bm, p1[0], p1[1], 0.288, h=0.040, half=0.058,
                   slot=0.018, ear=0.004, simple=True)
        # 正心枋（转角处一段）
        _box(bm, -0.150, 0.150, -0.075, 0.025, 0.100, 0.285)
    return C.proto("hall_dougong_corner", build, mat="wood_dark", smooth=20.0)


def _proto_rafter(C):
    """檐口双层椽：圆檐椽（d0.085 六棱）+ 方飞椽（0.09x0.07，错半格、外挑 0.12）。

    局部：X=沿檐，Y=朝檐内，Z 上；z=0 即瓦底皮 -0.02（放置 z=p.z-0.36，
    p 为檐口点），故所有构件顶面 <= 0，椽顶永远低于瓦底 0.02 以上。
    """
    def build(bm):
        # 圆檐椽：y -0.10..0.42，中心 z=-0.1175 -> 顶 -0.075，仍在瓦底 -0.02 下
        _round_y(bm, 0.0, -0.10, 0.42, 0.0425, -0.1175, seg=6)
        # 方飞椽：错半格（+0.45），挑出更远 0.12，顶面 -0.005
        _box(bm, 0.405, 0.495, -0.22, 0.30, -0.075, -0.005)
    return C.proto("hall_rafter", build, mat="wood_dark", smooth=0.0)


def _proto_rafter_red(C):
    """双层椽红封头：在圆檐椽/方飞椽的端面各贴一块朱砂封头（12 tri/块）。"""

    def build(bm):
        # 只做方飞椽红封头：飞椽头局部 y=-0.22 外露于封檐板之外（板在 0.07..0.11、
        # 顶 -0.10），封头径向 0.20..0.25 与飞椽端 20mm 插入榫接，板外 0.09 净距。
        _box(bm, 0.403, 0.497, -0.250, -0.200, -0.082, 0.006)

    return C.proto("hall_rafter_red", build, mat="crimson", smooth=0.0)


def _actual_tree(obj, M):
    mesh = obj.data
    mesh.calc_loop_triangles()
    remap = M.inverted() @ obj.matrix_world
    return BVHTree.FromPolygons([remap@v.co for v in mesh.vertices],
        [tuple(f.vertices) for f in mesh.loop_triangles],all_triangles=True)


def _fitted_rafters(C, M, ep, name, cn, coll, roof, fascia, trim):
    """Fly and round eave tails follow the rendered soffit, with an under-tail saddle."""
    raf,red=_proto_rafter(C),_proto_rafter_red(C)
    bearings=mu.new_bm()
    up=Vector((0,0,1))
    def loft(bm,stations,profiles):
        # Keep the fitted section wherever its departure from a linear face exceeds 0.35 mm.
        def simplify(i,j):
            if j<=i+1:return [i,j]
            errors=[]
            for k in range(i+1,j):
                error=0
                for p,a,b in zip(profiles[k],profiles[i],profiles[j]):
                    d=b-a
                    t=max(0,min(1,(p-a).dot(d)/max(d.length_squared,1e-12)))
                    error=max(error,(p-(a+t*d)).length)
                errors.append((error,k))
            err,k=max(errors)
            return simplify(i,k)[:-1]+simplify(k,j) if err>.00035 else [i,j]
        rings=[[mu.v(bm,x) for x in profiles[k]] for k in simplify(0,len(stations)-1)]
        for a,b in zip(rings,rings[1:]):mu.bridge_rings(bm,a,b,closed=True)
        mu.cap_ring(bm,rings[0],flip=True);mu.cap_ring(bm,rings[-1],flip=False)
    for path in ep.values():
        stations=_resample(path,.90)
        for k,(p,raw) in enumerate(stations):
            along=Vector((raw.x,raw.y,0)).normalized()
            inward=Vector((-along.y,along.x,0))
            if inward.dot(p)>0:inward.negate()
            across=Vector((inward.y,-inward.x,0))
            if k==0:p=p+along*.64
            if k==len(stations)-1:p=p-along*max(0,.64-(path[-1]-p).to_2d().length)
            def point(x,y,h):
                return Vector((p.x+across.x*x+inward.x*y,p.y+across.y*x+inward.y*y,h))
            def overhead(x,y,layers):
                q=point(x,y,0)
                hits=[t.ray_cast(q,up)[0] for t in layers]
                return min((h.z for h in hits if h is not None),default=None)
            body=mu.new_bm()
            for xc,r,y0,y1,upper,round_section in (
                    (0,.0425,-.10,.42,-.1175+.0425*math.sin(math.pi/3),True),
                    (.45,.045,-.22,.30,-.005,False)):
                # Fit a straight wooden blank from the eave to the actual rear seat.
                # Its angle is constrained by the underside and the fascia at the head.
                constraints=[]
                for j in range(71):
                    y=y0-.04+(y1-y0+.04)*j/70
                    hs=[overhead(xc+dx,y,(roof,fascia,trim)) for dx in (-r-.002,0,r+.002)]
                    hs=[h for h in hs if h is not None]
                    if hs:constraints.append((y,min(hs)-(.018 if not round_section and y<-.17 else .003)))
                seat_y=y1-.03
                ref=overhead(xc,seat_y,(roof,))
                grade=(overhead(xc,seat_y+.025,(roof,))-overhead(xc,seat_y-.025,(roof,)))/.05
                def fit(m):
                    intercept=min(h-m*y for y,h in constraints)
                    loss=abs(ref-intercept-m*seat_y)+.0005*abs(m-grade)
                    return loss,intercept,m
                _,intercept,slope=min(fit(i/40) for i in range(-15,89))
                angle=math.atan(slope)
                orient=Matrix((across,inward,up)).transposed().to_4x4() @ Matrix.Rotation(angle,4,'X')
                head=intercept-upper/math.cos(angle)
                part_pose=Matrix.Translation((p.x,p.y,head))@orient
                if not round_section: pose=part_pose
                prof=([(r*math.cos(TAU*i/6),r*(math.sin(TAU*i/6)-math.sin(math.pi/3))) for i in range(6)]
                      if round_section else [(-r,-.070),(r,-.070),(r,0),(-r,0)])
                ys=[y0]+[y0+(y1-y0)*i/40 for i in range(1,40)]+[y1]
                seat0,seat1=y1-.055,y1-.006
                ys=sorted(set(ys+[seat0,seat1]))
                top_by_y={}
                for y in ys:
                    hs=[overhead(xc+r*ix/3,y,(roof,fascia,trim)) for ix in range(-3,4)]
                    hs=[h for h in hs if h is not None]
                    upper_limit=min(hs)-.0018 if hs else None
                    head_line=head+slope*y+upper/math.cos(angle)
                    blend=max(0,min(1,(y-(y1-.17))/.10))
                    blend=blend*blend*(3-2*blend)
                    if y>=.095 and upper_limit is None:raise ValueError('missing eave soffit')
                    top_by_y[y]=((1-blend)*head_line+blend*upper_limit if upper_limit is not None else head_line)
                    if upper_limit is not None:top_by_y[y]=min(top_by_y[y],upper_limit)
                rings=[]
                for y in ys:
                    ring=[]
                    for dx,dz in prof:
                        # Transition from the straight rigid nose to vertical loft stations.
                        f=max(0,min(1,(y+.10)/.16));f=f*f*(3-2*f)
                        outer=part_pose@Vector((xc+dx,y,upper+dz))
                        inside=point(xc+dx,y,top_by_y[y]+dz)
                        q=outer.lerp(inside,f)
                        ring.append(q)
                    rings.append(ring)
                loft(body,ys,rings)
                # Small soffit-fixed shoe. The underside shelf carries the tail; two narrow
                # cheeks reach the underside of the boarding alongside it, never above the timber.
                for x0,x1,shelf in ((xc-r-.009,xc-r-.0009,False),(xc+r+.0009,xc+r+.009,False),
                                     (xc-r-.009,xc+r+.009,True)):
                    br=[]
                    samples=[t for t in ys if seat0<=t<=seat1]
                    for y in samples:
                        low=top_by_y[y]+min(z for _,z in prof)-.0012
                        section=[]
                        for x,high in ((x0,False),(x1,False),(x1,True),(x0,True)):
                            if not high:h=low-.008 if shelf else low+.0004
                            else:h=low if shelf else min(overhead(x,y+dy,(roof,)) for dy in (-.004,0,.004))-.0017
                            section.append(point(x,y,h))
                        br.append(section)
                    loft(bearings,samples,br)
            # Give each double rafter its own fitted mesh, with its origin coincident with the
            # red cap's rigid frame. Its enamel/wood axial insertion is still exactly 20 mm.
            inv=pose.inverted()
            for v in body.verts:v.co=inv@v.co
            mu.recalc_normals(body)
            mu.uv_box_project(body,1.0)
            obj=C.place_world(raf,M@pose,name=f"{name}_raf",cat="hall",coll_path=coll,cn=f"{cn}·随坡檐椽")
            me=raf.data.copy();body.to_mesh(me);body.free();me.update();obj.data=me
            C.place_world(red,M@pose,name=f"{name}_rafred",cat="hall",coll_path=coll,cn=f"{cn}·椽头红封头")
    _emit(C,bearings,M,f"{name}_rafter_bearings","hall",coll,cn=f"{cn}·承椽鞍座",mat="wood_dark")


def _proto_chiwen(C):
    """宋式鸱吻（v15）：双面鼓腮 + 螺旋尾鳍 + 鳞甲，高 1.30、身厚 0.34。

    局部：X 沿正脊、Y 横跨脊、Z 从脊帽顶起算；底部 0.02 坐口套住脊帽。
    """
    prof = [(-0.12, 0.00), (0.34, 0.00), (0.38, 0.12), (0.30, 0.30),
            (0.16, 0.50), (0.05, 0.72), (0.10, 0.94), (0.28, 1.10),
            (0.36, 1.26), (0.20, 1.30), (0.04, 1.16), (-0.06, 0.94),
            (-0.14, 0.64), (-0.18, 0.32)]

    def build(bm):
        _prism_plane(bm, "y", prof, -0.17, 0.17)          # 吻身
        # 双面鼓腮：两颊鼓出，边缘收圆（不与吻身共面）
        for sy in (-1.0, 1.0):
            _frustum(bm, 0.02, sy * 0.20, 0.155, 0.120, 0.30, 0.62)
            _frustum(bm, 0.02, sy * 0.20, 0.120, 0.060, 0.62, 0.74)
        # 吞口（大口吞脊的缺口，两侧各一）
        for sy in (-1.0, 1.0):
            _box(bm, -0.10, 0.10, sy * 0.172, sy * 0.196, 0.28, 0.46)
        # 鳞甲：沿背脊两列小凸鳞（每侧 5 片）
        for sy in (-1.0, 1.0):
            for k in range(5):
                t = k / 4.0
                sx = -0.06 + 0.26 * t
                sz = 0.42 + 0.55 * t
                _frustum(bm, sx, sy * 0.178, 0.052, 0.028, sz, sz + 0.06)
        # 螺旋尾鳍：平面螺线（真 3D，厚 0.09），向脊内舒卷
        path = []
        npt = 34
        for k in range(npt + 1):
            t = k / npt
            ang = math.radians(-115.0 + 300.0 * t)
            rad = 0.30 * (1.0 - 0.86 * t)
            path.append(Vector((0.10 + rad * math.cos(ang), 0.0,
                                1.06 + rad * math.sin(ang))))
        mu.swept_profile_along(bm, path, mu.rect_profile(0.090, 0.052),
                               up_hint=(0.0, 1.0, 0.0), closed_profile=True)
        _frustum(bm, 0.20, 0.0, 0.085, 0.055, 1.16, 1.28)   # 尾鳍颈部

    return C.proto("hall_chiwen", build, mat="roof_dai", smooth=25.0)


def _proto_chiwen_edge(C):
    """鸱吻勾边（bronze）：沿背脊三道细棱 + 螺旋尾鳍外缘一道，凸 0.03。"""
    def build(bm):
        for sign in (-1,1):
            for x,z,width in ((-.015,.82,.060),(.005,.94,.068),(.092,1.065,.067)):
                _box(bm,x,x+width,sign*.1705,sign*.184,z,z+.018)
            # The tail outline is applied to the flank of the ceramic fin.
            path=[]
            for k in range(24):
                t=(k+3)/34
                ang=math.radians(-115+300*t)
                rad=.30*(1-.86*t)
                x=.10+rad*math.cos(ang)
                z=1.06+rad*math.sin(ang)
                path.append(Vector((x,sign*.173,z)))
            # Trace only the part on the wing body; project the rest on the
            # narrow ceramic spiral instead of passing through the wing.
            shape=_proto_chiwen(C)
            me=shape.data;me.calc_loop_triangles()
            tree=BVHTree.FromPolygons([v.co for v in me.vertices],
                 [tuple(f.vertices) for f in me.loop_triangles],all_triangles=True)
            for a,b in zip(path,path[1:]):
                points=[a.lerp(b,i/4) for i in range(5)]
                for c,d in zip(points,points[1:]):
                    samples=[]
                    for q in (c,d):
                        hit=tree.ray_cast((q.x,sign*1,q.z),(0,-sign,0))[0]
                        if hit is not None: samples.append(abs(hit.y))
                    if len(samples)==2 and max(samples)-min(samples)<.003:
                        y=sign*(max(samples)+.003)
                        _bar(bm,(c.x,y,c.z),(d.x,y,d.z),.004,.007)
    return C.proto("hall_chiwen_edge", build, mat="bronze", smooth=20.0)


def _proto_zoushou(C, kind=0):
    """垂脊走兽（三型区分，高 0.14~0.16）：
    0 狮（卷鬃、大头）、1 马（长颈、四腿）、2 鱼龙（锥身、尾鳍、背鳍）。
    """
    def build(bm):
        _box(bm, -0.078, 0.078, -0.048, 0.048, 0.000, 0.020)   # 共用座
        if kind == 0:
            _frustum(bm, -0.005, 0.0, 0.060, 0.044, 0.020, 0.086)   # 蹲身
            _box(bm, 0.018, 0.088, -0.034, 0.034, 0.066, 0.124)     # 大头
            for sy in (-1.0, 1.0):                                   # 卷鬃
                for k in range(3):
                    _frustum(bm, -0.020 + 0.028 * k, sy * 0.040,
                             0.026, 0.014, 0.070 + 0.018 * k, 0.098 + 0.018 * k)
            _box(bm, -0.096, -0.042, -0.016, 0.016, 0.036, 0.100)   # 尾
        elif kind == 1:
            _frustum(bm, -0.010, 0.0, 0.052, 0.038, 0.020, 0.078)   # 马身
            _box(bm, 0.030, 0.062, -0.026, 0.026, 0.070, 0.128)     # 颈
            _box(bm, 0.048, 0.104, -0.028, 0.028, 0.116, 0.152)     # 头
            for (px, py) in ((0.036, 0.032), (0.036, -0.032),
                             (-0.052, 0.032), (-0.052, -0.032)):
                _box(bm, px - 0.010, px + 0.010, py - 0.010, py + 0.010,
                     0.020, 0.060)                                  # 四腿
            _box(bm, -0.104, -0.050, -0.014, 0.014, 0.052, 0.086)   # 尾
        elif kind == 2:
            _frustum(bm, 0.0, 0.0, 0.030, 0.062, 0.020, 0.092)      # 锥身
            _frustum(bm, 0.0, 0.0, 0.062, 0.030, 0.092, 0.132)      # 头
            for sy in (-1.0, 1.0):                                   # 尾鳍
                bm.faces.new([_v(bm, -0.060, sy * 0.012, 0.070),
                              _v(bm, -0.128, sy * 0.030, 0.118),
                              _v(bm, -0.060, sy * 0.012, 0.128)])
            _box(bm, -0.016, 0.016, -0.010, 0.010, 0.120, 0.160)    # 背鳍
        elif kind == 3:
            # 凤：立身 + 长颈曲首 + 双翼 + 三根飘尾
            _frustum(bm, 0.0, 0.0, 0.048, 0.034, 0.020, 0.092)      # 身
            _box(bm, 0.022, 0.052, -0.016, 0.016, 0.082, 0.124)     # 颈
            _box(bm, 0.040, 0.080, -0.020, 0.020, 0.118, 0.142)     # 头
            _box(bm, 0.080, 0.100, -0.009, 0.009, 0.120, 0.130)     # 喙
            _box(bm, 0.048, 0.076, -0.008, 0.008, 0.140, 0.166)     # 冠
            for sy in (-1.0, 1.0):                                  # 双翼（竖板）
                _box(bm, -0.050, 0.030, sy * 0.030, sy * 0.042,
                     0.062, 0.150)
                _box(bm, -0.078, -0.040, sy * 0.030, sy * 0.040,
                     0.098, 0.140)                                  # 翼尖
            for (dx, dz, dy) in ((-0.120, 0.096, 0.0), (-0.132, 0.076, 0.018),
                                 (-0.132, 0.076, -0.018)):          # 三根尾羽
                _box(bm, dx, -0.038, dy - 0.008, dy + 0.008, dz, dz + 0.014)
            for sy in (-1.0, 1.0):                                  # 双腿
                _box(bm, -0.018, 0.004, sy * 0.026, sy * 0.040, 0.0, 0.024)
        else:
            # 骑凤：凤（缩 0.86）+ 骑者（身/头/双腿/前臂），整体约 0.235 高
            _frustum(bm, 0.0, 0.0, 0.044, 0.031, 0.020, 0.086)      # 凤身
            _box(bm, 0.020, 0.048, -0.015, 0.015, 0.078, 0.118)     # 凤颈
            _box(bm, 0.038, 0.074, -0.018, 0.018, 0.112, 0.134)     # 凤头
            _box(bm, 0.074, 0.092, -0.008, 0.008, 0.114, 0.124)     # 喙
            for sy in (-1.0, 1.0):                                  # 凤翼
                _box(bm, -0.046, 0.026, sy * 0.028, sy * 0.040,
                     0.058, 0.132)
            _box(bm, -0.118, -0.036, -0.008, 0.008, 0.086, 0.100)   # 尾羽
            _frustum(bm, -0.010, 0.0, 0.030, 0.020, 0.130, 0.196)   # 人身（坐姿）
            _frustum(bm, -0.014, 0.0, 0.017, 0.013, 0.192, 0.222)   # 人头
            for sy in (-1.0, 1.0):                                  # 双腿
                _box(bm, -0.020, 0.030, sy * 0.020, sy * 0.032,
                     0.120, 0.150)
                _box(bm, 0.026, 0.044, sy * 0.020, sy * 0.030,
                     0.092, 0.128)
            _box(bm, 0.004, 0.048, -0.012, 0.012, 0.166, 0.182)     # 前臂
    return C.proto(f"hall_zoushou{kind}", build, mat="roof_dai", smooth=30.0)


def _proto_chuishou(C):
    """垂兽座（0.18x0.14x0.16）+ 垂兽（有角、卷尾，约 0.16 高）。"""
    def build(bm):
        _box(bm, -0.090, 0.090, -0.070, 0.070, 0.000, 0.160)   # 座
        _frustum(bm, 0.0, 0.0, 0.060, 0.038, 0.160, 0.240)     # 身
        _box(bm, 0.022, 0.088, -0.030, 0.030, 0.218, 0.282)    # 头
        for sy in (-1.0, 1.0):                                  # 双角
            _box(bm, 0.040, 0.070, sy * 0.020, sy * 0.044, 0.276, 0.310)
        _box(bm, -0.100, -0.044, -0.016, 0.016, 0.176, 0.258)  # 尾
        _frustum(bm, -0.086, 0.0, 0.026, 0.012, 0.248, 0.268)  # 卷尾端
    return C.proto("hall_chuishou", build, mat="roof_dai", smooth=30.0)


def _proto_column(C, key, r0, r1, z0, z1, base_r, base_h, seg=12):
    def build(bm):
        prof = [(0.0, z0), (base_r, z0), (base_r, z0 + base_h),
                (r0, z0 + base_h + 0.03), (r1, z1), (0.0, z1)]
        mu.revolve(bm, prof, (0.0, 0.0, 0.0), segments=seg, mat_index=0)
    return C.proto(key, build, mat="wood_dark", smooth=30.0)


# ============================================================ 配殿
def _hall_walls(C, M, bm_w, bm_g, bm_d, two, z_top):
    """四面墙（局部坐标）：-Y 开门，其余三面开槛窗；二层阁再开一圈高窗。

    * 门洞 (-1.80,1.80, 0.20,4.10)：3.60x3.90，下沿即地坪，无门槛。
    * all 洞口一次性喂给 _wall_grid（含 2F 窗带），不重复建墙。
    """
    win = B_WIN1_Z if two else A_WIN_Z
    w2 = B_WIN2_Z
    side1 = ((-5.50, -3.10), (3.10, 5.50))
    back3 = ((-5.50, -3.10), (-1.20, 1.20), (3.10, 5.50))

    def _band(hs, zz):
        return [(a0, a1, zz[0], zz[1]) for (a0, a1) in hs]

    # v15：墙在柱位断开（±2.6 两根檐柱），段端沿柱面收进 r=0.240 让槽；
    # 柱心法向 ±HX/±HY，墙厚方向 6 条竖带各自收进，柱面留 ≥10mm 缝。
    cols = (-2.6, 2.6)

    # -Y 门墙：门 + 次间窗（+ 2F 高窗）
    holes = [(-1.80, 1.80, Z_FLOOR, 4.10)] + _band(side1, win)
    if two:
        holes += _band(side1, w2)
    _wall_bays(bm_w, "y", -OW, -IW, -IW, IW, Z_FLOOR + WALL_LIFT, z_top,
               holes, cols, -HX, r=0.275)
    _door(bm_w, bm_d, bm_g, "y", -OW, -IW, -1.80, 1.80, Z_FLOOR, 4.10)
    for (a0, a1) in side1:
        _window(bm_w, bm_g, "y", -OW, -IW, a0, a1, win[0], win[1])

    # +Y 后墙 3 窗
    hb = list(_band(back3, win))
    if two:
        hb += _band(back3, w2)
    _wall_bays(bm_w, "y", IW, OW, -IW, IW, Z_FLOOR + WALL_LIFT, z_top,
               hb, cols, HX, r=0.275)
    for (a0, a1) in back3:
        _window(bm_w, bm_g, "y", IW, OW, a0, a1, win[0], win[1])

    # ±X 山墙各 3 窗
    for sgn in (-1.0, 1.0):
        p0, p1 = (sgn * IW, sgn * OW)
        _wall_bays(bm_w, "x", p0, p1, -IW, IW, Z_FLOOR + WALL_LIFT, z_top,
                   hb, cols, sgn * HX, r=0.275, beam_level=(B_COL_TOP if two else A_COL_TOP) - .402)
        for (a0, a1) in back3:
            _window(bm_w, bm_g, "x", p0, p1, a0, a1, win[0], win[1])

    if two:
        # 二层窗只在主网格里开洞，这里只补窗框/棂条/玻璃
        for (axis, p0, p1, hs) in (("y", -OW, -IW, side1),
                                   ("y", IW, OW, back3),
                                   ("x", -IW, -OW, back3),
                                   ("x", IW, OW, back3)):
            for (a0, a1) in hs:
                _window(bm_w, bm_g, axis, p0, p1, a0, a1, w2[0], w2[1])


def _hall_stairs(C, M, name, cn, coll):
    """折返两跑楼梯 + 休息平台 + 栏杆（局部坐标，靠 +Y 后墙）。"""
    st = B_STAIR
    bm = mu.new_bm()
    rise = (B_SLAB_TOP - Z_FLOOR) / (2 * st["n"])
    # Each flight has a continuous stepped outline, including the riser at
    # its foot. The last upper tread meets the gallery at x0 exactly.
    zl = Z_FLOOR + rise * st["n"]
    for start, sign, low, y0, y1 in (
            (st["x0"], -1, Z_FLOOR, st["y0"], st["y1"]),
            (st["x1"], 1, zl, st["y2"], st["y3"])):
        end = start + sign * st["w"] * st["n"]
        profile = [(end, Z_FLOOR-.002), (start, Z_FLOOR-.002)]
        for k in range(st["n"]):
            height = low + rise * (k + 1)
            profile.extend(((start + sign*st["w"]*k, height),
                            (start + sign*st["w"]*(k+1), height)))
        _prism_plane(bm, "y", profile, y0, y1)
    _box(bm, st["land0"], st["land1"], st["y0"], st["y3"],
         Z_FLOOR-.002, zl)
    _emit(C, bm, M, f"{name}_stair", "hall", coll, cn=f"{cn}·楼梯", mat="stone_lite")

    # 栏杆：两跑各两侧 + 平台外侧
    bm = mu.new_bm()
    for (yy, x0, x1, z0, z1) in (
            (st["y0"] + 0.04, st["x0"], st["x1"], Z_FLOOR, zl),
            (st["y1"] - 0.04, st["x0"], st["x1"], Z_FLOOR, zl),
            (st["y3"] - 0.04, st["x1"], st["x0"] + 0.02, zl, B_SLAB_TOP)):
        posts=[]
        for k in range(0,st["n"],2):
            xx=x0+(x1-x0)*(k+.5)/st["n"]
            tread=z0+(z1-z0)*(k+1)/st["n"]
            _box(bm,xx-.04,xx+.04,yy-.04,yy+.04,tread-.012,tread+.82)
            posts.append((xx,tread))
        for (xa,za),(xb,zb) in zip(posts,posts[1:]):
            _bar(bm,(xa,yy,za+.86),(xb,yy,zb+.86),.06,.09)
            _bar(bm,(xa,yy,za+.36),(xb,yy,zb+.36),.04,.05)
    # 平台外侧（x=land0）封边栏杆
    for i in range(0, 5):
        yy = st["y0"] + (st["y3"] - st["y0"]) * i / 4
        _box(bm, st["land0"] + 0.01, st["land0"] + 0.09, yy - 0.04, yy + 0.04,
             zl, zl + 0.82)
    _bar(bm, (st["land0"] + 0.05, st["y0"], zl + 0.86),
         (st["land0"] + 0.05, st["y3"], zl + 0.86), 0.06, 0.09)
    _emit(C, bm, M, f"{name}_stairrail", "hall", coll, cn=f"{cn}·楼梯栏杆",
          mat="wood_dark")


def _hall_upper(C, M, name, cn, coll, bm_wood, bm_stone, bm_white):
    """二层楼面环 + 中庭栏板 + 楼梯井洞口栏板（局部坐标）。"""
    z0, z1 = B_SLAB_BOT, B_SLAB_TOP
    # 环板（四块，互不重叠：南北通长，东西内收）
    _box(bm_wood, -B_CORR_IN + 0.02, B_CORR_IN - 0.02, B_ATRIUM, B_CORR_IN - 0.02, z0, z1)
    _box(bm_wood, -B_CORR_IN + 0.02, B_CORR_IN - 0.02, -B_CORR_IN + 0.02, -B_ATRIUM, z0, z1)
    _box(bm_wood, -B_CORR_IN + 0.02, -B_ATRIUM, -B_ATRIUM, B_ATRIUM, z0, z1)
    _box(bm_wood, B_ATRIUM, B_CORR_IN - 0.02, -B_ATRIUM, B_ATRIUM, z0, z1)
    # 楼梯井洞口（切掉北侧环板上的一块）——用四块补板围合，实际开洞：
    #   洞口 x[-2.45, 0.92] y[4.44, 5.66]
    #   先删掉覆盖该区的板：上面北侧通长板改为左右两块
    # 为避免负布尔，直接重建北侧板：
    #   （上面的第一块板已覆盖 y[3.0,5.70]，此处不再重建，改为在 _hall_upper2 中处理）


def _hall_upper_floor(C, M, name, cn, coll, bm):
    """二层楼面：四块矩形拼成环，北侧被楼梯井切开。"""
    z0, z1 = B_SLAB_BOT, B_SLAB_TOP
    x0, x1 = -B_CORR_IN + 0.02, B_CORR_IN - 0.02
    # 南板
    _box(bm, x0, x1, -B_CORR_IN + 0.02, -B_ATRIUM, z0, z1)
    # 东板 / 西板（y -3.0..3.0）
    _box(bm, B_ATRIUM, x1, -B_ATRIUM, B_ATRIUM, z0, z1)
    _box(bm, x0, -B_ATRIUM, -B_ATRIUM, B_ATRIUM, z0, z1)
    # Keep both flights and the turning platform open to the upper storey.
    west, east = B_STAIR["land0"]-.12, B_STAIR["x0"]
    south, north = B_STAIR["y0"]-.10, B_STAIR["y3"]+.10
    _box(bm, x0, x1, B_ATRIUM, south, z0, z1)
    _box(bm, x0, x1, north, B_CORR_IN-.02, z0, z1)
    _box(bm, x0, west, south, north, z0, z1)
    _box(bm, east, x1, south, north, z0, z1)
    # 结构梁（0.30 深，藏在楼面下）：中庭环梁 + 楼梯井边梁
    zb0, zb1 = z0 - B_BEAM_H, z0
    _box(bm, -B_ATRIUM - 0.12, B_ATRIUM + 0.12, B_ATRIUM - 0.12, B_ATRIUM + 0.12, zb0, zb1)
    _box(bm, -B_ATRIUM - 0.12, B_ATRIUM + 0.12, -B_ATRIUM - 0.12, -B_ATRIUM + 0.12, zb0, zb1)
    _box(bm, -B_ATRIUM - 0.12, -B_ATRIUM + 0.12, -B_ATRIUM, B_ATRIUM, zb0, zb1)
    _box(bm, B_ATRIUM - 0.12, B_ATRIUM + 0.12, -B_ATRIUM, B_ATRIUM, zb0, zb1)
    _box(bm, west, east, south-.10, south, zb0, zb1)
    _box(bm, west-.12, west, south, north, zb0, zb1)


def _hall_atrium_rail(C, M, name, cn, coll, bm):
    """中庭四周 + 楼梯井的 0.9 栏板（望柱 80x80 + 扶手 60x90）。"""
    z = B_SLAB_TOP
    post_centres=set()
    for (a, b) in (((-B_ATRIUM, -B_ATRIUM), (B_ATRIUM, -B_ATRIUM)),
                   ((-B_ATRIUM, B_ATRIUM), (B_ATRIUM, B_ATRIUM)),
                   ((-B_ATRIUM, -B_ATRIUM), (-B_ATRIUM, B_ATRIUM)),
                   ((B_ATRIUM, -B_ATRIUM), (B_ATRIUM, B_ATRIUM))):
        # 让开楼梯井（北侧 x -2.45..0.92 处）
        if abs(a[1] - B_ATRIUM) < 1e-6:
            spans = [(a,(-2.45,B_ATRIUM)),((.92,B_ATRIUM),b)]
        else:
            spans = [(a,b)]
        for (start,end) in spans:
            n=max(2,math.ceil(math.dist(start,end)/.60))
            pts=[tuple(start[j]+(end[j]-start[j])*i/n for j in (0,1)) for i in range(n+1)]
            for p in pts:
                if p in post_centres: continue
                post_centres.add(p)
                _box(bm, p[0] - 0.04, p[0] + 0.04, p[1] - 0.04, p[1] + 0.04,
                     z, z + 0.82)
            for i in range(n):
                _bar(bm, (pts[i][0], pts[i][1], z + 0.86),
                     (pts[i + 1][0], pts[i + 1][1], z + 0.86), 0.06, 0.09)
                _bar(bm, (pts[i][0], pts[i][1], z + 0.36),
                     (pts[i + 1][0], pts[i + 1][1], z + 0.36), 0.04, 0.05)
    # 楼梯井：东、南、西三面 0.9 栏板
    for (xa, xb, ya, yb) in ((B_STAIR["land0"]-.19, B_STAIR["land0"]-.13, 3.12, 5.54),
                             (B_STAIR["x0"]+.01, B_STAIR["x0"]+.07, 3.12, 4.27)):
        _box(bm, xa, xb, ya, yb, z, z + 0.90)
        _box(bm, xa - 0.01, xb + 0.01, ya - 0.01, yb + 0.01, z + 0.90, z + 0.96)


def _hall(C, h):
    """建一座配殿（局部坐标 + 世界矩阵）。"""
    name, cn = h["id"], h["cn"]
    two = h["storeys"] == 2
    M = (Matrix.Translation((h["cx"], h["cy"], 0.0))
         @ Matrix.Rotation(math.radians(h["rot"]), 4, "Z"))
    coll = ("配殿", cn)

    # ---------------- 台明（14x14，底 8mm 凹缝）
    bm = mu.new_bm()
    _box(bm, -PLINTH_OUT - HX + 0.0, PLINTH_OUT + HX, -PLINTH_OUT - HY,
         PLINTH_OUT + HY, GAP, PLINTH_H)
    _emit(C, bm, M, f"{name}_taiming", "hall", coll, cn=f"{cn}·台明",
          mat="brick")

    # ---------------- 后墙外踏步：v13 取消
    # 台基外缘一圈汉白玉栏杆正好从馆后经过，这个朝外的踏步必然与栏板/望柱相撞
    # （overlap13 抓到 28 对跨部件相交）。馆内 0.20m 台明本身可上，取消后踏步。
    # （若要恢复，必须同时让 site13 的栏杆绕开馆后台明外扩 1.0m 的范围。）

    # ---------------- 墙 + 门窗
    bm_w, bm_g, bm_d = mu.new_bm(), mu.new_bm(), mu.new_bm()
    z_top = B_WALL_TOP if two else A_WALL_TOP
    lintel_bottom = z_top - .230
    _hall_walls(C, M, bm_w, bm_g, bm_d, two, lintel_bottom)
    for v in bm_w.verts:
        if abs(v.co.z - lintel_bottom) < 1e-5:
            along = min(abs(v.co.x), abs(v.co.y))
            v.co.z += CORNER_RISE * max(0.0, min(1.0, (along - 2.6) / (HX - 2.6)))
    _emit(C, bm_w, M, f"{name}_walls", "hall", coll, cn=f"{cn}·墙",
          mat="wall_white")
    _emit(C, bm_g, M, f"{name}_glass", "hall", coll, cn=f"{cn}·窗玻璃",
          mat="glass", smooth=0.0)
    _emit(C, bm_d, M, f"{name}_door", "hall", coll, cn=f"{cn}·格扇门",
          mat="wood_dark")

    zf = (B_EAVE if two else A_EAVE) - 0.28

    # ---------------- 普拍枋（一圈，柱顶 8mm 以下）
    bm = mu.new_bm()
    # v15：普拍枋随角柱生起 +0.04（两端 rise_len 内线性抬升），中段仍 zf-0.12..zf
    _head_frame(bm, z_top, zf)
    pupai = _emit(C, bm, M, f"{name}_pupai", "hall", coll, cn=f"{cn}·普拍枋",
          mat="wood_dark")

    # ---------------- 柱（3x3 柱网，实例化）
    zc = B_COL_TOP if two else A_COL_TOP
    # 柱径收 20mm（0.46→0.50 径）：柱身外切 6.23，距普拍枋外皮 6.24 留 10mm，
    # 避免 12 边形柱面与普拍枋外立面近平行共面（v15 审计）
    # 柱顶再降 12mm：角柱生起后顶 6.028，距普拍枋环底（转角 6.048）留 20mm，
    # 避免柱顶面与环底斜面近平行共面；生起量仍为 4cm（6.028 vs 标准 5.988）。
    col = _proto_column(C, f"hall_col_{'b' if two else 'a'}", COL_R - 0.05,
                        COL_R - 0.07, -0.008, zc - Z_FLOOR - 0.012, 0.36, 0.26)
    for gx in BAYS:
        for gy in BAYS:
            base = Vector((gx, gy, Z_FLOOR))
            direction = _column_head(gx, gy, zc) - base
            rotation = Vector((0, 0, 1)).rotation_difference(direction).to_matrix().to_4x4()
            length = direction.length / (zc - Z_FLOOR - .012)
            loc = M @ Matrix.Translation(base) @ rotation @ Matrix.Diagonal((1, 1, length, 1))
            C.place_world(col, loc, name=f"{name}_col", cat="hall",
                          coll_path=("配殿", cn), cn=f"{cn}·柱")

    # ---------------- 斗拱（柱头 + 补间，实例化）
    dg = _proto_dougong(C)
    frame_tree = _actual_tree(pupai,M)
    def seated(x,y,half,z):
        vals=[]
        for i in range(13):
            for j in range(13):
                hit = frame_tree.ray_cast((x+half*(i/6-1),y+half*(j/6-1),z+1),(0,0,-1))[0]
                if hit is not None: vals.append(hit.z)
        return max(vals) + .0007
    # +0.004：斗拱底面比普拍枋顶/栱眼壁底高 4mm（避开共面判定），顶面仍在檐口下
    z_dg = ((B_EAVE - 0.28) if two else (A_EAVE - 0.28)) + 0.004
    for side, (axis, sgn) in enumerate((("y", -1.0), ("y", 1.0),
                                        ("x", 1.0), ("x", -1.0))):
        pos = [t for t in BAYS if abs(abs(t) - HX) > 1e-6]   # 角柱位留给角铺作
        for t in (-4.3, 0.0, 4.3):
            if all(abs(t - p) > 0.4 for p in pos):
                pos.append(t)
        for t in pos:
            if axis == "y":
                p = (t, sgn * 5.995)
                rz = 0.0 if sgn < 0 else 180.0
            else:
                p = (sgn * 5.995, t)
                rz = 90.0 if sgn > 0 else -90.0
            seat_rise = CORNER_RISE * max(0.0, (abs(t)+.175-2.58)/(HX-2.58))
            loc = M @ Matrix.Translation((p[0], p[1], seated(p[0],p[1],.176,z_dg))) @ \
                Matrix.Rotation(math.radians(rz), 4, "Z")
            C.place_world(dg, loc, name=f"{name}_dg", cat="hall",
                          coll_path=("配殿", cn), cn=f"{cn}·斗拱")
    # v15 转角铺作：45 度角华拱/角昂，坐角柱头（生起 +0.04）
    dgc = _proto_dougong_corner(C)
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            rz = math.degrees(math.atan2(sx, -sy))
            loc = M @ Matrix.Translation((sx * 5.995, sy * 5.995,
                                          seated(sx*5.995,sy*5.995,.27,z_dg))) @ \
                Matrix.Rotation(math.radians(rz), 4, "Z")
            C.place_world(dgc, loc, name=f"{name}_dgc", cat="hall",
                          coll_path=("配殿", cn), cn=f"{cn}·转角铺作")

    # ---------------- 屋面
    # nv=16：裙檐横分格加密，翼角起翘（roofkit 的 _cf_dist 二次曲线）看起来平滑；
    # gable_nu=48：山花/博风采样降到 48（nv 加倍后控 tri，不砍功能）。
    outer = (-(HX + EAVE_OUT), -(HY + EAVE_OUT),
             HX + EAVE_OUT, HY + EAVE_OUT)
    inner = (-HX, -HY, HX, HY)
    z_eave = B_EAVE if two else A_EAVE
    z_break = B_BREAK if two else A_BREAK
    z_ridge = (B_RIDGE if two else A_RIDGE) - 0.84
    bm = mu.new_bm()
    ep, crowns = _roof(bm, outer, z_eave, inner, z_break, HX, 0.0, z_ridge,
               lift=0.85, run_out=0.30, nv=16, gable_nu=48)
    _gongyan(C, M, bm, name, cn, coll, 6.10, 6.10, .24, zf - .05, z_break - ROOF_THICK - .02)
    roof_obj = _emit(C, bm, M, f"{name}_roof", "roof", coll, cn=f"{cn}·歇山顶",
          mat="roof_dai", uv=0.2)
    underside = _actual_tree(roof_obj,M)

    # ---------------- 瓦当 + 双层椽头（实例化椽头）
    bm = mu.new_bm()
    _tile_ends(bm, ep, D.TILE_GAUGE)
    _emit(C, bm, M, f"{name}_tiles", "roof", coll, cn=f"{cn}·瓦当",
          mat="roof_dai", uv=0.2)
    # ---------------- 封檐板（连续）+ 朱砂描边
    # 板内面离檐口端面 0.03、顶面比瓦口低 0.08（不高出坡面）；
    # 描边贴在板外面 0.004 处（4mm 缝，错开不共面）。
    bm = mu.new_bm()
    # step=0.45：与椽头取同一条檐口折线的 0.90 整数倍站位，瓦垄波相位一致，
    # 飞椽顶 p.z-0.365 与板底 p.z-0.330 恒留 35mm（lead m00345 的 8 对共面即相位差导致）
    _eave_band(bm, ep, 0.070, 0.110, -0.330, -0.100, step=0.45)
    fascia_obj = _emit(C, bm, M, f"{name}_fascia", "roof", coll, cn=f"{cn}·封檐板",
          mat="wood_dark")
    fascia = _actual_tree(fascia_obj,M)
    bm = mu.new_bm()
    _eave_band(bm, ep, 0.114, 0.118, -0.320, -0.300, step=0.55)
    trim_obj = _emit(C, bm, M, f"{name}_trim", "roof", coll, cn=f"{cn}·檐口描边",
          mat="crimson")
    edge_trim = _actual_tree(trim_obj,M)

    _fitted_rafters(C, M, ep, name, cn, coll, underside, fascia, edge_trim)

    # ---------------- 天际线：正脊鸱吻 + 四垂脊垂兽/走兽
    z_cap = (B_RIDGE if two else A_RIDGE)
    chi = _proto_chiwen(C)
    che = _proto_chiwen_edge(C)
    for sgn in (-1.0, 1.0):
        loc = M @ Matrix.Translation((sgn * (HX + 0.12), 0.0, z_cap - 0.02)) \
            @ Matrix.Rotation(0.0 if sgn > 0 else math.pi, 4, "Z")
        C.place_world(chi, loc, name=f"{name}_chiwen", cat="hall",
                      coll_path=("配殿", cn), cn=f"{cn}·鸱吻")
        C.place_world(che, loc, name=f"{name}_chiwen_e", cat="hall",
                      coll_path=("配殿", cn), cn=f"{cn}·鸱吻勾边")
    _ridge_animals(C, M, crowns, name, cn)

    # ---------------- 室内（天花 / 明栿）
    bm = mu.new_bm()
    zc_ceil = 5.70
    if not two:
        # v15：二层阁不建整片天花——楼板底面 4.10 即回廊天花；中庭 6x6 与楼梯井必须通透。
        # 原整片天花 4.05..4.08 封住中庭，且楼梯末级/栏杆穿出（ceil × stair/stairrail 2+2 面）
        # 独立天花板格：两道明栿处留槽，四根内柱处截短板端。
        cuts = [-IW+.02,-2.82,-2.75,-2.45,-2.38,2.38,2.45,2.75,2.82,IW-.02]
        xs = [-IW+.02,-2.82,-2.38,2.38,2.82,IW-.02]
        hangers=mu.new_bm()
        for ya,yb in zip(cuts,cuts[1:]):
            yy = abs((ya+yb)/2)
            for xa,xb in zip(xs,xs[1:]):
                xx=abs((xa+xb)/2)
                if abs(yy-2.6)<.15 or (abs(yy-2.6)<.22 and abs(xx-2.6)<.22):
                    continue
                _box(bm,xa,xb,ya,yb,zc_ceil-.03,zc_ceil)
                # 板缝绕开明栿后，每板四角设吊木，顶部随梁底或望板实际坡面切斜。
                for u,v in ((.2,.2),(.8,.2),(.8,.8),(.2,.8)):
                    x,y=xa+u*(xb-xa),ya+v*(yb-ya)
                    rx,ry=min(.018,.08*(xb-xa)),min(.018,.08*(yb-ya))
                    lo=[];hi=[]
                    for dx,dy in ((-rx,-ry),(rx,-ry),(rx,ry),(-rx,ry)):
                        pos=(x+dx,y+dy,zc_ceil+.001)
                        supports=[tree.ray_cast(pos,(0,0,1))[0] for tree in (underside,frame_tree)]
                        h=min(p.z for p in supports if p is not None)
                        lo.append(_v(hangers,x+dx,y+dy,zc_ceil+.0005))
                        hi.append(_v(hangers,x+dx,y+dy,h-.0007))
                    mu.bridge_rings(hangers,lo,hi,closed=True)
                    mu.cap_ring(hangers,lo,flip=True);mu.cap_ring(hangers,hi,flip=False)
        _emit(C,hangers,M,f"{name}_ceil_hangers","hall",coll,cn=f"{cn}·天花吊木",mat="wood_dark")
    _emit(C, bm, M, f"{name}_ceil", "hall", coll, cn=f"{cn}·天花",
          mat="wood_dark")

    # ---------------- 二层
    if two:
        bm = mu.new_bm()
        _hall_upper_floor(C, M, name, cn, coll, bm)
        _emit(C, bm, M, f"{name}_f2", "hall", coll, cn=f"{cn}·二层楼面",
              mat="wood_lite")
        bm = mu.new_bm()
        _hall_atrium_rail(C, M, name, cn, coll, bm)
        _emit(C, bm, M, f"{name}_f2rail", "hall", coll,
              cn=f"{cn}·二层栏板", mat="wood_dark")
        _hall_stairs(C, M, name, cn, coll)


def _jianzhi(C):
    """镂金坊 12x7，门朝北（-Y），三面槛窗，卷棚不采用→歇山自洽。"""
    name, cn = "jianzhi", "镂金坊"
    cx, cy = JP["cx"], JP["cy"]
    M = Matrix.Translation((cx, cy, 0.0))
    coll = ("配殿", cn)

    # 台明 0.6 外扩，底 8mm 缝，顶 0.15
    bm = mu.new_bm()
    x0, y0, x1, y1 = JP_PLINTH_BOX
    _box(bm, x0 - cx, x1 - cx, y0 - cy, y1 - cy, GAP, JP["floor"])
    _emit(C, bm, M, f"{name}_taiming", "hall", coll, cn=f"{cn}·台明",
          mat="brick")

    # 墙：北墙开门 3.2x2.9（0.15..3.05），其余三面各 2 窗
    bm_w, bm_g, bm_d = mu.new_bm(), mu.new_bm(), mu.new_bm()
    w0, w1 = 2.20, 3.35
    hx, hy = JP_IWX, JP_IWY
    # 北墙（-Y）——v15：在 ±2.6 两根檐柱处断开（让槽 r0.240），窗改到 ±3.00 外
    _wall_bays(bm_w, "y", -JP_OWY, -hy, -hx, hx, JP["floor"] + WALL_LIFT,
               JP_PUP[0] - 0.008,
               [(-1.60, 1.60, JP["floor"], 3.05),
                (-5.10, -3.00, w0, w1), (3.00, 5.10, w0, w1)],
               (-2.6, 2.6), -JP["hy"], r_base=0.332)
    _door(bm_w, bm_d, bm_g, "y", -JP_OWY, -hy, -1.60, 1.60, JP["floor"], 3.05)
    for (a0, a1) in ((-5.10, -3.00), (3.00, 5.10)):
        _window(bm_w, bm_g, "y", -JP_OWY, -hy, a0, a1, w0, w1)
    # 南墙（+Y）3 窗
    hs = [(-5.10, -3.00), (-1.20, 1.20), (3.00, 5.10)]
    _wall_bays(bm_w, "y", hy, JP_OWY, -hx, hx, JP["floor"] + WALL_LIFT,
               JP_PUP[0] - 0.008,
               [(a0, a1, w0, w1) for (a0, a1) in hs], (-2.6, 2.6), JP["hy"],
               r_base=0.332)
    for (a0, a1) in hs:
        _window(bm_w, bm_g, "y", hy, JP_OWY, a0, a1, w0, w1)
    # 东西山墙各 2 窗
    for sgn in (-1.0, 1.0):
        p0, p1 = (sgn * hx, sgn * JP_OW)
        _wall_bays(bm_w, "x", p0, p1, -hy, hy, JP["floor"] + WALL_LIFT,
                   JP_PUP[0] - 0.008,
                   [(-2.30, -0.70, w0, w1), (0.70, 2.30, w0, w1)], (), sgn * hx,
                   r_base=0.332)
        for (a0, a1) in ((-2.30, -0.70), (0.70, 2.30)):
            _window(bm_w, bm_g, "x", p0, p1, a0, a1, w0, w1)
    _emit(C, bm_w, M, f"{name}_walls", "hall", coll, cn=f"{cn}·墙",
          mat="wall_white")
    _emit(C, bm_g, M, f"{name}_glass", "hall", coll, cn=f"{cn}·窗玻璃",
          mat="glass", smooth=0.0)
    _emit(C, bm_d, M, f"{name}_door", "hall", coll, cn=f"{cn}·格扇门",
          mat="wood_dark")

    # 普拍枋 + 栱眼壁
    bm = mu.new_bm()
    for (xx0, xx1, yy0, yy1) in ((-hx - 0.14, hx + 0.14, hy - 0.02, JP_OWY),
                                 (-hx - 0.14, hx + 0.14, -JP_OWY, -hy + 0.02),
                                 (hx - 0.02, JP_OW, -hy, hy),
                                 (-JP_OW, -hx + 0.02, -hy, hy)):
        _box(bm, xx0, xx1, yy0, yy1, JP_PUP[0], JP_PUP[1])
    _emit(C, bm, M, f"{name}_pupai", "hall", coll, cn=f"{cn}·普拍枋",
          mat="wood_dark")

    # 柱（周圈，实例化）
    col = _proto_column(C, "jp_col", JP_R - 0.03, JP_R - 0.05, -0.008,
                        JP["col_h"], 0.32, 0.22)
    for gx in (-6.0, -2.6, 2.6, 6.0):   # v15：恢复 ±2.6 檐柱（墙已分段让槽）
        for gy in (-3.5, 3.5):
            C.place_world(col, M @ Matrix.Translation((gx, gy, JP["floor"])),
                          name=f"{name}_col", cat="hall",
                          coll_path=("配殿", cn), cn=f"{cn}·柱")

    # 屋面（歇山，脊帽顶 6.20；四向出檐不对称，见 R2）
    outer = (-(JP["hx"] + JP_OUT["x0"]),
             -(JP["hy"] + JP_OUT["y0"]),
             JP["hx"] + JP_OUT["x1"],
             JP["hy"] + JP_OUT["y1"])
    inner = (-JP["hx"], -JP["hy"], JP["hx"], JP["hy"])
    bm = mu.new_bm()
    ep, crowns = _roof(bm, outer, JP["eave"], inner, JP_BREAK, JP["hx"], 0.0,
               JP_RIDGE_IN, lift=0.55, run_out=0.20, nv=10, gable_nu=30)
    _gongyan(C, M, bm, name, cn, coll, JP_OW-.02, JP_OWY-.02, .27,
             JP_PUP[1]-.05, JP_BREAK - ROOF_THICK - .02)
    _emit(C, bm, M, f"{name}_roof", "roof", coll, cn=f"{cn}·歇山顶",
          mat="roof_dai", uv=0.2)
    bm = mu.new_bm()
    _tile_ends(bm, ep, D.TILE_GAUGE)
    _emit(C, bm, M, f"{name}_tiles", "roof", coll, cn=f"{cn}·瓦当",
          mat="roof_dai", uv=0.2)
    # 封檐板 + 描边（同配殿口径：板内面离檐口 0.03、顶面低于瓦口 0.08）
    bm = mu.new_bm()
    # step=0.45：与椽头取同一条檐口折线的 0.90 整数倍站位，瓦垄波相位一致，
    # 飞椽顶 p.z-0.365 与板底 p.z-0.330 恒留 35mm（lead m00345 的 8 对共面即相位差导致）
    _eave_band(bm, ep, 0.070, 0.110, -0.330, -0.100, step=0.45)
    _emit(C, bm, M, f"{name}_fascia", "roof", coll, cn=f"{cn}·封檐板",
          mat="wood_dark")
    bm = mu.new_bm()
    _eave_band(bm, ep, 0.114, 0.118, -0.320, -0.300, step=0.55)
    _emit(C, bm, M, f"{name}_trim", "roof", coll, cn=f"{cn}·檐口描边",
          mat="crimson")
    # 鸱吻 + 垂脊垂兽/走兽
    chi = _proto_chiwen(C)
    che = _proto_chiwen_edge(C)
    for sgn in (-1.0, 1.0):
        loc = M @ Matrix.Translation((sgn * (JP["hx"] + 0.12), 0.0,
                                      JP["ridge"] - 0.02)) @ \
            Matrix.Rotation(0.0 if sgn > 0 else math.pi, 4, "Z")
        C.place_world(chi, loc, name=f"{name}_chiwen", cat="hall",
                      coll_path=("配殿", cn), cn=f"{cn}·鸱吻")
        C.place_world(che, loc, name=f"{name}_chiwen_e", cat="hall",
                      coll_path=("配殿", cn), cn=f"{cn}·鸱吻勾边")
    _ridge_animals(C, M, crowns, name, cn)

    # 天花（3.55）
    bm = mu.new_bm()
    _box(bm, -hx + 0.02, hx - 0.02, -hy + 0.02, hy - 0.02, 3.50, 3.55)
    _emit(C, bm, M, f"{name}_ceil", "hall", coll, cn=f"{cn}·天花",
          mat="wood_dark")


# ============================================================ 连廊
def _gal_stations(pts, step=0.55):
    pts = [Vector((p[0], p[1], 0.0)) for p in pts]
    st = []
    s = 0.0
    n = len(pts) - 1
    dirs = [(pts[i + 1] - pts[i]).normalized() for i in range(n)]
    Ls = [Vector((-d.y, d.x, 0.0)) for d in dirs]
    st.append((pts[0].copy(), Ls[0].copy(), 0.0))
    for i in range(n):
        a, b = pts[i], pts[i + 1]
        seg = (b - a).length
        k = max(1, int(math.ceil(seg / step)))
        for j in range(1, k + 1):
            P = a + (b - a) * (j / k)
            ss = s + seg * j / k
            L = Ls[i].copy()
            reach = 3.20
            if i > 0:
                L += Ls[i-1] * max(0.0, 1.0-seg*j/k/reach)
            if i+1 < n:
                L += Ls[i+1] * max(0.0, 1.0-seg*(1-j/k)/reach)
            st.append((P, L, ss))
        s += seg
    return st


def _gal_us():
    us = []
    for k in range(4):
        us.append(-2.25 + 0.70 * k / 3.0)
    for k in range(1, 13):
        us.append(-1.55 + 1.55 * k / 12.0)
    for k in range(1, 13):
        us.append(1.55 * k / 12.0)
    for k in range(1, 4):
        us.append(1.55 + 1.05 * k / 3.0)
    return us


def _gal_z(u):
    z_e, z_c, z_t = CL_EAVE, 4.108, CL_TOP
    if u <= -CL_U_COL:
        t = (u - CL_U_OUT) / (CL_U_COL + CL_U_OUT) if CL_U_OUT < 0 else 0.0
        t = (u - (-2.25)) / 0.70
        return z_e + (z_c - z_e) * max(0.0, min(1.0, t))
    if u >= CL_U_COL:
        t = (2.60 - u) / 1.05
        return z_e + (z_c - z_e) * max(0.0, min(1.0, t))
    return z_c + (z_t - z_c) * math.cos(0.5 * math.pi * abs(u) / 1.55) ** 1.3


def _sweep_gal(bm_t, bm_s, st, us, thick, gauge, amp):
    rt, rb = [], []
    for (P, L, s) in st:
        a, b = [], []
        for u in us:
            q = P + L * u
            z = _gal_z(u)
            ph = s / gauge
            a.append(_v(bm_t, q.x, q.y, z + amp * rk._tile_wave(ph)))
            b.append(_v(bm_s, q.x, q.y, z - thick))
        rt.append(a)
        rb.append(b)
    ns, nu = len(st), len(us)
    # 檐口立面必须落在 bm_s 自己这一张网格里：复制一份顶面顶点给封边用，
    # 直接把 bm_t 的顶点塞进 bm_s.faces.new 会报 “BMVert is from another mesh”。
    rs = [[_v(bm_s, v.co.x, v.co.y, v.co.z) for v in row] for row in rt]
    for i in range(ns - 1):
        for j in range(nu - 1):
            bm_t.faces.new([rt[i][j], rt[i + 1][j], rt[i + 1][j + 1], rt[i][j + 1]])
            bm_s.faces.new([rb[i][j], rb[i][j + 1], rb[i + 1][j + 1], rb[i + 1][j]])
    for j in (0, nu - 1):
        for i in range(ns - 1):
            bm_s.faces.new([rs[i][j], rs[i + 1][j], rb[i + 1][j], rb[i][j]])
    for i in (0, ns - 1):
        for j in range(nu - 1):
            bm_s.faces.new([rs[i][j], rs[i][j + 1], rb[i][j + 1], rb[i][j]])
    return rt, rb


def _gal_barge(bm, P, L, us, outward, off=0.02, drop=0.26, th=0.06):
    up = Vector((0.0, 0.0, 1.0))
    A, B = [], []
    for u in us:
        q = P + L * u + outward * off
        z = _gal_z(u) - 0.005
        A.append(Vector((q.x, q.y, z)))
        B.append(Vector((q.x, q.y, z)) + outward * th)
    for j in range(len(us) - 1):
        a0, a1, b0, b1 = A[j], A[j + 1], B[j], B[j + 1]
        for (p, q) in ((a0, a1), (b1, b0)):
            bm.faces.new([_v(bm, p.x, p.y, p.z), _v(bm, q.x, q.y, q.z),
                          _v(bm, q.x, q.y, q.z - drop),
                          _v(bm, p.x, p.y, p.z - drop)])
        # 顶面
        bm.faces.new([_v(bm, a0.x, a0.y, a0.z), _v(bm, b0.x, b0.y, b0.z),
                      _v(bm, b1.x, b1.y, b1.z), _v(bm, a1.x, a1.y, a1.z)])


def _gal_band(bm, st, uc, hw, z0, z1):
    rings = []
    samples = _gal_us()
    def soffit(u):
        for u0,u1 in zip(samples,samples[1:]):
            if u0 <= u <= u1:
                return _gal_z(u0)+(_gal_z(u1)-_gal_z(u0))*(u-u0)/(u1-u0)-CL_ROOF_T-.0007
        raise ValueError(u)
    for (P, L, s) in st:
        a, b = P + L * (uc - hw), P + L * (uc + hw)
        ring=[_v(bm, a.x, a.y, z0), _v(bm, b.x, b.y, z0)]
        for u in ((uc+hw,uc,uc-hw) if z1 is None else (uc+hw,uc-hw)):
            q=P+L*u
            ring.append(_v(bm,q.x,q.y,soffit(u) if z1 is None else z1))
        rings.append(ring)
    for i in range(len(rings) - 1):
        mu.bridge_rings(bm,rings[i],rings[i+1],closed=True)
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])


def _gal_at(st, s):
    """按弧长 s 在站点序列内线性插值，返回 (P, L, T)。"""
    for i in range(len(st) - 1):
        if st[i][2] <= s <= st[i + 1][2]:
            k = (s - st[i][2]) / max(1e-9, st[i + 1][2] - st[i][2])
            P = st[i][0].lerp(st[i + 1][0], k)
            L = (st[i][1].lerp(st[i + 1][1], k))
            if L.length < 1e-6:
                L = st[i][1].copy()
            T = (st[i + 1][0] - st[i][0])
            T.z = 0.0
            T.normalize()
            return P, L, T
    P = st[-1][0].copy()
    T = (st[-1][0] - st[-2][0])
    T.z = 0.0
    return P, st[-1][1].copy(), T.normalized()


def _sweep_prof(bm, pts, prof):
    """把闭合剖面 prof=[(u,z)] 沿 pts=[(P,L)] 扫成实体（端头封口）。"""
    rings = []
    for (P, L) in pts:
        rings.append([_v(bm, (P + L * u).x, (P + L * u).y, z) for (u, z) in prof])
    npf = len(prof)
    for i in range(len(rings) - 1):
        for k in range(npf):
            a0, a1 = rings[i][k], rings[i][(k + 1) % npf]
            b0, b1 = rings[i + 1][k], rings[i + 1][(k + 1) % npf]
            bm.faces.new([a0, a1, b1, b0])
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    return rings


def _gal_gap(P):
    """美人靠/挂落断开处：北廊 12m 穿堂（含桥北落客点）、南廊桥头通路。"""
    if abs(P.x) < CL_OPEN + 0.20 and P.y > -14.0:
        return True
    if abs(P.x) < 4.60 and P.y < -36.0:
        return True
    return False


# 美人靠剖面（u 朝水院内，z 绝对）：坐凳 0.56..0.68、靠背斜到 1.14
MK_PROF = ((1.56, 0.56), (1.90, 0.56), (1.90, 0.62),
           (1.95, 0.73), (2.02, 0.87), (2.09, 1.01), (2.155, 1.12),
           (2.10, 1.165), (2.02, 1.02), (1.94, 0.87), (1.87, 0.73), (1.84, 0.68),
           (1.56, 0.68))


def _goose(bm, P, L, u0, z0, u1, z1, n=12, r=0.042):
    """鹅颈立柱：沿 (u,z) 的参数曲线采样，再按世界点扫掠圆管（v15 平滑曲线，非 3 段折线）。

    曲线：u 随 t 线性 + 0.075*sin(pi*t) 的外鼓，z 线性；下脚 0.16m 保持竖直。
    """
    pts = []
    for k in range(n + 1):
        t = k / float(n)
        z = z0 + (z1 - z0) * t
        if (z - z0) < 0.16:
            u = u0
        else:
            u = u0 + (u1 - u0) * t + 0.075 * math.sin(math.pi * t)
        q = P + L * u
        pts.append((q.x, q.y, z))
    mu.swept_tube(bm, pts, r, segments=6, caps=True)


def _gal_meiren(C, st, slist, name):
    """连续鹅颈美人靠：按柱距分段、遇穿堂/桥头断开，坐凳+斜靠背一次扫出。"""
    bm = mu.new_bm()
    nseg = 0
    posts=[_gal_at(st,s)[0]+_gal_at(st,s)[1]*u for s in slist for u in (-CL_U_COL,CL_U_COL)]
    def clear(s):
        P,L,_=_gal_at(st,s)
        # 全宽座板与柱、柱础之间留出安装缝；转角处法线的长度随斜接变化。
        x,y=P+L*1.58,P+L*2.16
        line=y-x
        return all((x+line*min(1,max(0,(p-x).dot(line)/line.length_squared))-p).length>.262 for p in posts)
    for i in range(len(slist) - 1):
        s0, s1 = slist[i], slist[i + 1]
        mid = _gal_at(st, (s0 + s1) * 0.5)[0]
        if _gal_gap(mid) or (s1 - s0) < 1.0:
            continue
        a, b = s0 + 0.44, s1 - 0.44
        while a < b and not clear(a): a+=.02
        while a < b and not clear(b): b-=.02
        if b-a<.25: continue
        n = max(1, int(math.ceil((b - a) / 0.55)))
        pts = []
        for k in range(n + 1):
            P, L, T = _gal_at(st, a + (b - a) * k / n)
            pts.append((P, L))
        _sweep_prof(bm, pts, MK_PROF)
        nseg += 1
        # 鹅颈立柱：smooth 扫掠（下脚直段 → 坐凳 → S 形卷向靠背顶），每跨 2 根
        for k in (0.28, 0.72):
            P, L, T = _gal_at(st, a + (b - a) * k)
            _goose(bm, P, L, 1.58, CL_SLAB + 0.0005, 2.145, 1.13, n=12, r=0.042)
        # v15：座面出挑的可见托臂（斜撑 + 抱脚），每跨 3 道；脚落台明（+8mm 缝）
        for k in (0.02, 0.5, 0.98):
            P, L, T = _gal_at(st, a + (b - a) * k)
            def w2(u, z):
                q = P + L * u
                return (q.x, q.y, z)
            for u,w,h in ((1.852,.060,.055),(1.735,.050,.048)):
                bar=_bar(bm,w2(1.58,CL_SLAB+.0005),w2(u,.548),w,h)
                for v in bar[:4]: v.co.z=CL_SLAB+.0005
    if nseg:
        _emit(C, bm, None, f"{name}_meiren", "gallery", ("连廊", "美人靠"),
              cn="临水美人靠", mat="wood_dark")
    else:
        bm.free()


def _gal_guadeng(C, st, slist, name):
    """挂落：阑额下连续横枋 + 竖向棂条（0.30 一根），穿堂处断开。"""
    bm = mu.new_bm()
    nseg = 0
    for i in range(len(slist) - 1):
        s0, s1 = slist[i], slist[i + 1]
        mid = _gal_at(st, (s0 + s1) * 0.5)[0]
        if _gal_gap(mid) or (s1 - s0) < 1.0:
            continue
        a, b = s0 + 0.46, s1 - 0.46
        n = max(1, int(math.ceil((b - a) / 0.55)))
        pts = []
        for k in range(n + 1):
            P, L, T = _gal_at(st, a + (b - a) * k / n)
            pts.append((P, L))
        _sweep_prof(bm, pts, ((1.64, 2.96), (1.72, 2.96), (1.72, 3.02), (1.64, 3.02)))
        _sweep_prof(bm, pts, ((1.63, 3.40), (1.73, 3.40), (1.73, 3.436), (1.63, 3.436)))
        nb = max(1, int(round((b - a) / 0.30)))
        for k in range(nb + 1):
            P, L, T = _gal_at(st, a + (b - a) * k / nb)
            q = P + L * 1.68
            _box(bm, q.x - 0.022, q.x + 0.022, q.y - 0.022, q.y + 0.022,
                 2.99, 3.41)
        nseg += 1
    if nseg:
        _emit(C, bm, None, f"{name}_guadeng", "gallery", ("连廊", "挂落"),
              cn="连廊挂落", mat="wood_dark")
    else:
        bm.free()


def _gal_columns(C, st, name):
    """沿两行柱线布柱（3.4 柱距，转角处去重）。"""
    col = _proto_column(C, "gal_col", 0.135, 0.115, -0.008, 3.44 - CL_SLAB - .0005,
                        0.21, 0.16, seg=10)
    pts = []
    for (P, L, s) in st:
        pass
    # 按段布点：直接以站点序列取整距
    n = len(st)
    acc = 0.0
    for i in range(1, n):
        acc += (st[i][0] - st[i - 1][0]).length
        if acc >= CL_STEP - 0.01:
            acc = 0.0
            for u in (-CL_U_COL, CL_U_COL):
                q = st[i][0] + st[i][1] * u
                pts.append((round(q.x, 3), round(q.y, 3)))
    # 两端柱
    for idx in (0, n - 1):
        for u in (-CL_U_COL, CL_U_COL):
            q = st[idx][0] + st[idx][1] * u
            pts.append((round(q.x, 3), round(q.y, 3)))
    seen = set()
    for (x, y) in pts:
        key = (round(x, 2), round(y, 2))
        if key in seen:
            continue
        seen.add(key)
        C.place_at(col, (x, y, CL_SLAB), rot_z=0.0,
                   name="gallery_col", cat="gallery",
                   coll_path=("连廊", "柱"), cn="廊柱")
    # 柱位弧长表（美人靠/挂落按柱距分段）
    sl, acc = [0.0], 0.0
    for i in range(1, n):
        acc += (st[i][0] - st[i - 1][0]).length
        if acc >= CL_STEP - 0.01:
            acc = 0.0
            sl.append(st[i][2])
    sl.append(st[-1][2])
    return sl


def _gallery(C):
    name, cn = "gallery", "环水连廊"
    coll = ("连廊",)

    # 台明 4 块（互不重叠，铺满 C 形）
    bm = mu.new_bm()
    for (x0, y0, x1, y1) in CL_PLAT:
        _box(bm, x0, x1, y0, y1, GAP, CL_SLAB)
    _emit(C, bm, None, f"{name}_slab", "gallery", coll, cn=f"{cn}·台明",
          mat="stone_lite")

    # 2 级踏步（1 级踏面 + 地面）
    bm = mu.new_bm()
    for (x0, x1, y0, y1) in ((-1.5, 1.5, CL_OUT_YN, CL_OUT_YN + 0.36),
                             (-1.5, 1.5, CL_OUT_YS - 0.36, CL_OUT_YS)):
        y0, y1 = min(y0, y1), max(y0, y1)
        _box(bm, x0, x1, y0, y1, GAP, CL_SLAB * 0.5)
    _emit(C, bm, None, f"{name}_step", "gallery", coll, cn=f"{cn}·踏步",
          mat="stone_lite")

    us = _gal_us()
    for tag, path in (("A", CL_PATH_A), ("B", CL_PATH_B)):
        st = _gal_stations(path)
        bm_t, bm_s = mu.new_bm(), mu.new_bm()
        _sweep_gal(bm_t, bm_s, st, us, CL_ROOF_T, D.TILE_GAUGE, 0.045)
        for (P, L, s) in (st[0], st[-1]):
            i = 0 if (P - st[0][0]).length < 1e-9 else 1
            d = (st[1][0] - st[0][0]).normalized() if i == 0 else \
                (st[-1][0] - st[-2][0]).normalized()
            outward = -d if i == 0 else d
            _gal_barge(bm_s, P, L, us, outward)
        _emit(C, bm_t, None, f"{name}_roof{tag}", "roof",
              ("连廊", "屋面"), cn=f"{cn}·卷棚瓦面", mat="roof_dai", uv=0.2)
        _emit(C, bm_s, None, f"{name}_roof{tag}b", "roof",
              ("连廊", "屋面"), cn=f"{cn}·卷棚底棚", mat="wood_dark")

        # 阑额 / 普拍枋（两道柱线）
        bm = mu.new_bm()
        for u in (-CL_U_COL, CL_U_COL):
            _gal_band(bm, st, u, 0.09, 3.44, CL_COL_TOP - 0.008)
            _gal_band(bm, st, u, 0.11, CL_COL_TOP - .0075, None)
        _emit(C, bm, None, f"{name}_beam{tag}", "gallery", coll,
              cn=f"{cn}·阑额普拍枋", mat="wood_dark")

        # 瓦当
        bm = mu.new_bm()
        for j in (0,len(us)-1):
            u=us[j]
            points=[]
            for P,L,arc in st:
                q=P+L*u
                q.z=_gal_z(u)+.045*rk._tile_wave(arc/D.TILE_GAUGE)
                points.append(q)
            _edge_tiles(bm,points,.55,lambda i: st[i][1]*(1 if u>0 else -1))
        _emit(C, bm, None, f"{name}_tile{tag}", "roof",
              ("连廊", "屋面"), cn=f"{cn}·瓦当", mat="roof_dai", uv=0.2)

        sl = _gal_columns(C, st, name + tag)
        _gal_meiren(C, st, sl, name)
        _gal_guadeng(C, st, sl, name)

    # 开口两侧的柱（封檐收头柱）
    # （已由 _gal_columns 的端柱覆盖）


# ============================================================ 后苑点景
def _proto_pine(C, seed):
    # 罗汉松：主干弯曲，侧枝斜伸；短枝末端生密集、带中脊的披针形叶。
    import random
    rng = random.Random(1807 + seed)
    twist = rng.uniform(0, TAU)
    def axis(height):
        return Vector((.23*math.sin(.94*height+twist)-.23*math.sin(twist),
                       .10*height+.16*(math.cos(height+twist)-math.cos(twist)), height))
    leader = [axis(i*.54+.002) for i in range(13)]
    leader[1].x, leader[1].y = leader[0].x, leader[0].y
    branches = [(leader,.21,.018,12)]
    sprays = []
    for i in range(38):
        h = 1.25 + i*.132 + rng.uniform(-.09,.09)
        angle = twist + i*2.39996 + rng.uniform(-.46,.46)
        radial = Vector((math.cos(angle),math.sin(angle),0))
        across = Vector((-radial.y,radial.x,0))
        reach = (.38+1.82*(1-((h-2.0)/4.85)**2))*rng.uniform(.78,1.15)
        start = axis(h)
        elbow = start+radial*(.45*reach)+across*rng.uniform(-.21,.21)+Vector((0,0,-.13))
        tip = start+radial*reach+across*rng.uniform(-.29,.29)+Vector((0,0,rng.uniform(.22,.58)))
        branches.append(([start,elbow,tip],.035+.023*reach,.012,7))
        for k in range(7):
            at = elbow.lerp(tip,.11+k*.135)
            side = (-1 if k%2 else 1)*across
            end = at + side*rng.uniform(.22,.56)+radial*.18+Vector((0,0,rng.uniform(.10,.32)))
            branches.append(([at,end],.015,.005,5))
            for j in range(5):
                base = at.lerp(end,(j+1)/6)
                stem = (radial*rng.uniform(-.15,.22)+side*rng.uniform(.08,.30)+Vector((0,0,rng.uniform(.10,.34))))
                sprays.append((base,stem,rng.uniform(0,TAU)))
    def trunk(bm):
        for path,r0,r1,n in branches:
            mu.swept_tube(bm,path,r0,radius_end=r1,segments=n)
        for base,stem,_ in sprays:
            mu.swept_tube(bm,[base,base+stem],.006,radius_end=.002,segments=5)
    def foliage(bm):
        for base,stem,phase in sprays:
            for j in range(16):
                t=j/16
                a=phase+j*2.39996
                direction=Vector((math.cos(a),math.sin(a),.15+.60*t)).normalized()
                width=Vector((-math.sin(a),math.cos(a),0))*(.019-.005*t)
                foot=base+stem*t
                mid=foot+direction*(.083-.017*t)
                end=foot+direction*(.19-.045*t)+Vector((0,0,-.028))
                v=[bm.verts.new(q) for q in (foot,mid+width,mid+Vector((0,0,.009)),mid-width,end)]
                for ids in ((0,2,1),(0,3,2),(1,2,4),(2,3,4)):
                    bm.faces.new([v[n] for n in ids])
    return (C.proto(f"rg_pine_trunk_{seed}",trunk,mat="wood_dark",smooth=34),
            C.proto(f"rg_pine_foliage_{seed}",foliage,mat="foliage",smooth=28))


def _prune_flush_blades(trunk, leaves):
    """Remove complete blades lying against the wood after final triangulation."""
    import bmesh
    import bpy
    from ..overlap13 import _world_geom
    bpy.context.view_layer.update()
    verts, tris, _, normals = _world_geom(trunk)
    wood = BVHTree.FromPolygons(verts,tris,all_triangles=True)
    verts, tris, _, leaf_normals = _world_geom(leaves)
    blades = BVHTree.FromPolygons(verts,tris,all_triangles=True)
    # Each independent blade has five vertices. Follow face adjacency to
    # remove the entire blade regardless of mesh ordering.
    hits = {j for i,j in wood.overlap(blades) if abs(normals[i].dot(leaf_normals[j]))>.98}
    if hits:
        bm = bmesh.new()
        bm.from_mesh(leaves.data)
        bm.verts.ensure_lookup_table()
        remove = {bm.verts[k] for j in hits for k in tris[j]}
        for v in list(remove):
            remove.update(u for f in v.link_faces for u in f.verts)
        for v in list(remove):
            remove.update(u for f in v.link_faces for u in f.verts)
        bmesh.ops.delete(bm,geom=list(remove),context='VERTS')
        bm.to_mesh(leaves.data)
        bm.free()
        leaves.data.update()
        _prune_flush_blades(trunk, leaves)


def _proto_lantern(C):
    def build(bm):
        _frustum(bm, 0.0, 0.0, 0.24, 0.22, 0.008, 0.10)          # 座
        _box(bm, -0.19, 0.19, -0.19, 0.19, 0.10, 0.24)
        _box(bm, -0.06, 0.06, -0.06, 0.06, 0.24, 0.62)           # 柱身
        _box(bm, -0.17, 0.17, -0.17, 0.17, 0.62, 0.68)           # 灯室底
        for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            _box(bm, sx * 0.17 - 0.04, sx * 0.17 + 0.04,
                 sy * 0.17 - 0.04, sy * 0.17 + 0.04, 0.68, 1.02)
        _box(bm, -0.19, 0.19, -0.19, 0.19, 1.02, 1.08)           # 灯室顶
        _frustum(bm, 0.0, 0.0, 0.28, 0.02, 1.08, 1.40)           # 攒尖
        _frustum(bm, 0.0, 0.0, 0.06, 0.02, 1.40, 1.56)           # 宝顶
        # 灯室内的灯芯（暖光）
        _box(bm, -0.07, 0.07, -0.07, 0.07, 0.70, 0.98)
    return C.proto("rg_lantern", build, mat="stone_lite", smooth=20.0)


def _rock_ring(bm, cx, cy, z0, R, r0, ph=0.0, seg=30, nsec=10,
               wob=0.13, lean=0.0, squash=0.94):
    """竖立石环（环面 ≈ XZ，孔轴 ≈ Y）：环内空腔即**真贯通孔**。

    孔缘由扫掠管的外壁自然形成，管半径沿环起伏（0.80~1.16 r0）→ 孔缘卷曲；
    lean 给环一个整体侧倾，避免正圆环的机械感。
    底部由 `_rock_base` 石根托住，环最低点比石根顶低 0.06（融合，不共面）。
    """
    zc = z0 + R * (1.0 + wob) * squash + r0 * 1.08
    pts, rad = [], []
    for i in range(seg):
        t = TAU * i / seg
        rr = R * (1.0 + wob * math.sin(2 * t + ph) + 0.055 * math.sin(5 * t + ph * 0.7)
                 + 0.030 * math.sin(7 * t + ph * 1.9))
        x = cx + rr * math.cos(t)
        z = zc + rr * math.sin(t) * squash
        y = cy + 0.17 * math.sin(3 * t + ph) + lean * math.sin(t)
        pts.append(Vector((x, y, z)))
        rad.append(r0 * (0.74 + 0.40 * math.sin(3 * t + ph * 1.7)
                         + 0.12 * math.sin(7 * t + ph)))
    rings = []
    nsec += 3
    for i, P in enumerate(pts):
        T = (pts[(i + 1) % seg] - pts[(i - 1) % seg])
        T.normalize()
        N = T.cross(Vector((0.0, 1.0, 0.0)))
        if N.length < 1e-6:
            N = Vector((0.0, 1.0, 0.0))
        N.normalize()
        B = T.cross(N).normalized()
        ring = []
        for j in range(nsec):
            a = TAU * j / nsec
            # Water-worn longitudinal grooves continue round the rim.
            groove = max(0.0, math.cos(4 * a + 0.75 * math.sin(TAU * i / seg + ph))) ** 4
            rj = rad[i] * (1.0 + 0.16 * math.sin(3 * a + ph) - 0.17 * groove)
            ring.append(mu.v(bm, P + N * (math.cos(a) * rj) + B * (math.sin(a) * rj * 0.88)))
        rings.append(ring)
    for i in range(seg):
        mu.bridge_rings(bm, rings[i], rings[(i + 1) % seg], closed=True)


def _rock_base(bm, cx, cy, z0, r=0.50, h=0.20, seg=9, ph=0.0):
    """石根：九边形矮墩，顶面被环/石芽压入 0.06（融合）。"""
    ring0, ring1 = [], []
    for i in range(seg):
        a = TAU * i / seg
        rr = r * (1.0 + 0.12 * math.sin(2 * a + ph))
        ring0.append(mu.v(bm, (cx + rr * math.cos(a), cy + rr * math.sin(a), z0)))
        rr1 = rr * (0.80 + 0.06 * math.sin(3 * a + ph))
        ring1.append(mu.v(bm, (cx + rr1 * math.cos(a), cy + rr1 * math.sin(a), z0 + h)))
    mu.bridge_rings(bm, ring0, ring1, closed=True)
    mu.cap_ring(bm, ring0, flip=True)
    mu.cap_ring(bm, ring1, flip=False)


def _spike(bm, cx, cy, z0, r, h, ph=0.0, seg=7):
    """错轴岩芽：圆钝末梢，侧面受冲刷形成纵沟。"""
    rings = []
    for t, width in ((0, .82), (.10, 1.1), (.28, .87), (.52, .94),
                     (.72, .74), (.88, .54), (.96, .35), (1.0, .15)):
        row = []
        for j in range(seg + 3):
            angle = TAU * j / (seg + 3)
            groove = max(0, math.cos(3 * angle + ph + 2 * t)) ** 3
            radius = r * width * (1 + .11 * math.sin(2 * angle + ph) - .23 * groove)
            x = cx + .46 * r * math.sin(ph + 3 * t) * t + radius * math.cos(angle)
            y = cy + .41 * r * math.cos(ph + 2 * t) * t + .82 * radius * math.sin(angle)
            row.append(mu.v(bm, (x, y, z0 + h * t)))
        rings.append(row)
    for lower, upper in zip(rings, rings[1:]):
        mu.bridge_rings(bm, lower, upper, closed=True)
    mu.cap_ring(bm, rings[0], flip=True)
    mu.cap_ring(bm, rings[-1], flip=False)


def _proto_taihu(C, key, variant=0):
    """多孔太湖石（v15 A 步重构）：竖立石环 = 真贯通孔 + 石根 + 石芽，三/四块形态各异。"""

    def build(bm):
        if variant == 0:            # 高环 + 四根石柱
            _rock_base(bm, 0.0, 0.0, 0.0, 0.46, 0.20, ph=1.1)
            _rock_ring(bm, 0.0, 0.0, 0.0, 0.66, 0.200, ph=0.4, lean=0.06, seg=36, nsec=12)
            _rock_ring(bm, -0.40, 0.04, 0.0, 0.25, 0.100, ph=2.1, seg=22, nsec=8, squash=1.0)
            for (ang, rr2, hh, rad) in ((2.55, 0.62, 1.72, 0.150), (4.30, 0.58, 1.30, 0.125),
                                        (5.40, 0.60, 0.86, 0.105)):
                _spike(bm, rr2 * math.cos(ang), rr2 * math.sin(ang), 0.06, rad, hh, ph=ang)
            buds = ((0.34, 0.16, 1.86, 0.19), (-0.30, -0.14, 1.24, 0.16),
                    (0.22, -0.20, 0.46, 0.17))
        elif variant == 1:          # 双环（两个孔，高低不同）
            _rock_base(bm, 0.0, 0.0, 0.0, 0.50, 0.20, ph=2.3)
            _rock_ring(bm, -0.26, 0.02, 0.0, 0.40, 0.145, ph=1.9, lean=0.05, seg=30, nsec=10)
            _rock_ring(bm, 0.34, 0.10, 0.0, 0.32, 0.125, ph=0.7, lean=-0.04,
                       seg=26, nsec=9, squash=1.02)
            _spike(bm, 0.16, -0.32, 0.04, 0.140, 1.06, ph=2.2)
            _spike(bm, -0.52, -0.18, 0.04, 0.115, 1.32, ph=0.9)
            buds = ((0.40, 0.12, 1.16, 0.15), (-0.42, -0.12, 0.92, 0.15))
        elif variant == 2:          # 矮阔环 + 立峰
            _rock_base(bm, 0.0, 0.0, 0.0, 0.52, 0.20, ph=0.2)
            _rock_ring(bm, -0.12, 0.0, 0.0, 0.46, 0.165, ph=2.8, lean=-0.07, squash=0.86,
                       seg=32, nsec=11)
            _rock_ring(bm, 0.40, 0.02, 0.0, 0.22, 0.095, ph=1.4, seg=20, nsec=8, squash=1.0)
            _spike(bm, 0.46, 0.08, 0.04, 0.135, 1.52, ph=1.7)
            _spike(bm, -0.46, -0.14, 0.04, 0.110, 1.14, ph=2.9)
            buds = ((-0.34, 0.14, 1.06, 0.16), (0.26, -0.22, 0.62, 0.14))
        else:                        # 斜环 + 双芽
            _rock_base(bm, 0.0, 0.0, 0.0, 0.46, 0.18, ph=3.6)
            _rock_ring(bm, 0.0, 0.0, 0.0, 0.44, 0.16, ph=1.3, lean=0.10,
                       seg=32, nsec=11, squash=1.06)
            _rock_ring(bm, -0.34, 0.06, 0.0, 0.21, 0.090, ph=0.6, seg=20, nsec=8, squash=1.0)
            _spike(bm, 0.30, 0.22, 0.04, 0.115, 1.22, ph=0.4)
            buds = ((0.18, 0.18, 1.02, 0.15), (-0.24, -0.16, 0.52, 0.13))
        for (bx, by, bz, br) in buds:
            _spike(bm, bx, by, max(0.0, bz - br - 0.16), br * 1.15, br + 0.30, ph=bx * 7.1)
        mu.recalc_normals(bm)

    return C.proto(key, build, mat="stone_dark", smooth=30.0, uv=0.6)


def _proto_lotus(C, key, kind="leaf"):
    """后苑水面荷叶/荷花（薄面，浮在水面之上 4cm，不插入水面）。"""

    def build_leaf(bm):
        seg = 13
        cen = _v(bm, 0.0, 0.0, 0.055)
        inner, outer = [], []
        for k in range(seg):
            a = TAU * k / seg
            r0 = 0.13
            r1 = 0.44 + 0.05 * math.cos(3.0 * a)
            inner.append(_v(bm, r0 * math.cos(a), r0 * math.sin(a), 0.045))
            outer.append(_v(bm, r1 * math.cos(a), r1 * math.sin(a), 0.0))
        for k in range(seg):
            k2 = (k + 1) % seg
            bm.faces.new([cen, inner[k], inner[k2]])
            bm.faces.new([inner[k], outer[k], outer[k2], inner[k2]])

    def build_flower(bm):
        seg = 7
        for ring, (rr0, rr1, z0, z1) in enumerate(((0.05, 0.19, 0.00, 0.10),
                                                   (0.04, 0.13, 0.09, 0.19))):
            for k in range(seg):
                a = TAU * (k + 0.5 * ring) / seg
                bm.faces.new([
                    _v(bm, rr0 * math.cos(a - 0.22), rr0 * math.sin(a - 0.22), z0),
                    _v(bm, rr1 * math.cos(a - 0.30), rr1 * math.sin(a - 0.30), z1),
                    _v(bm, rr1 * math.cos(a + 0.30), rr1 * math.sin(a + 0.30), z1),
                    _v(bm, rr0 * math.cos(a + 0.22), rr0 * math.sin(a + 0.22), z0)])
        _frustum(bm, 0.0, 0.0, 0.045, 0.02, 0.10, 0.20)

    fn = build_leaf if kind == "leaf" else build_flower
    return C.proto(key, fn, mat="foliage", smooth=40.0, uv=0.5)


def _garden(C):
    coll = ("后苑",)
    bm = mu.new_bm()
    for seed, (x, y) in enumerate(RG_TREES):
        t, f = _proto_pine(C, seed)
        # 树池 1.2x1.2 石框（4 边，8mm 离台基面）
        for (dx, dy, w, h) in ((0.0, 0.54, 1.20, 0.12),
                               (0.0, -0.54, 1.20, 0.12),
                               (0.54, 0.0, 0.12, 0.96),
                               (-0.54, 0.0, 0.12, 0.96)):
            _box(bm, x + dx - w * 0.5, x + dx + w * 0.5,
                 y + dy - h * 0.5, y + dy + h * 0.5, GAP, 0.30)
        trunk = C.place_at(t, (x, y, 0.0), rot_z=(x * 1.7 + y * 0.9) % 360.0,
                   name="rg_pine_trunk", cat="detail", coll_path=("后苑", "罗汉松"),
                   cn="罗汉松·树干")
        leaves = C.place_at(f, (x, y, 0.0), rot_z=(x * 1.7 + y * 0.9) % 360.0,
                   name="rg_pine_foliage", cat="foliage",
                   coll_path=("后苑", "罗汉松"), cn="罗汉松·针叶")
        _prune_flush_blades(trunk, leaves)
    _emit(C, bm, None, "rg_treepool", "detail", coll, cn="罗汉松树池石框",
          mat="stone_lite")

    lan = _proto_lantern(C)
    for (x, y) in RG_LANTERNS:
        C.place_at(lan, (x, y, GAP), rot_z=0.0, name="rg_lantern",
                   cat="detail", coll_path=("后苑", "石灯"), cn="石灯")

    # ---------------- 太湖石两组（用户 v15 明确要，覆盖旧禁假山） ----------------
    # v15-A：四块形态各异（A 高环/B 双环双孔/C 矮阔环+立峰/D 斜环），每块至少一处真贯通孔
    ta = _proto_taihu(C, "rg_taihu_a", 0)
    tb = _proto_taihu(C, "rg_taihu_b", 1)
    tc = _proto_taihu(C, "rg_taihu_c", 2)
    td = _proto_taihu(C, "rg_taihu_d", 3)
    for (x, y, rot, sc, proto, nm) in ((-8.60, 24.20, 24.0, 1.00, ta, "rg_taihu_w"),
                                       (-7.10, 25.40, 118.0, 0.66, tc, "rg_taihu_w2"),
                                       (8.80, 41.60, -35.0, 0.88, tb, "rg_taihu_e"),
                                       (9.60, 40.20, 200.0, 0.58, td, "rg_taihu_e2")):
        # 石根与台基面（site 的 site13_paving 顶面 z=0）留 1.5mm 支撑接触缝：
        # 不共面、不穿插（lead m00819 点名的 4 对 site13_paving × rg_taihu 重合）
        C.place_at(proto, (x, y, 0.0015), rot_z=rot, name=nm, cat="detail",
                   coll_path=("后苑", "太湖石"),
                   cn={"rg_taihu_w": "太湖石·西", "rg_taihu_w2": "太湖石·西副",
                       "rg_taihu_e": "太湖石·东", "rg_taihu_e2": "太湖石·东副"}[nm],
                   scale=sc)

    # ---------------- 睡莲/荷花（水面 -0.30，叶面浮在 -0.26） ----------------
    lf = _proto_lotus(C, "rg_lotus_leaf", "leaf")
    fl = _proto_lotus(C, "rg_lotus_flower", "flower")
    for (cx, cy) in ((-3.20, 35.80), (2.60, 32.60)):
        for k in range(5):
            ang = TAU * k / 5.0
            lx = cx + 1.15 * math.cos(ang)
            ly = cy + 1.15 * math.sin(ang)
            C.place_at(lf, (lx, ly, -0.26), rot_z=72.0 * k + 11.0,
                       name="rg_lotus_leaf", cat="foliage",
                       coll_path=("后苑", "睡莲"), cn="睡莲·叶",
                       scale=0.70 + 0.06 * (k % 3))
        for (dx, dy, rot) in ((0.30, 0.10, 30.0), (-0.55, -0.25, 190.0)):
            C.place_at(fl, (cx + dx, cy + dy, -0.22), rot_z=rot,
                       name="rg_lotus_flower", cat="foliage",
                       coll_path=("后苑", "睡莲"), cn="荷花")


# ============================================================ 对外契约
INTERIOR = {}


def _interior():
    out = {}
    for (hid, cn, cx, cy, two, axis) in (
            ("zhuxianzhen", "刊木堂", -32.0, -30.0, False, "+X"),
            ("songhua", "澄怀轩", -32.0, -12.0, True, "+X"),
            ("bianxiu", "针经阁", 32.0, -30.0, False, "-X"),
            ("qinghua", "素肌堂", 32.0, -12.0, True, "-X")):
        out[hid] = dict(x0=cx - IW, x1=cx + IW, y0=cy - IW, y1=cy + IW,
                        floor=Z_FLOOR, door_axis=axis,
                        clear_h=(3.60 if two else 5.50),
                        frame_z=(0.30, 1.95) if two else (0.30, 3.10),
                        storeys=(2 if two else 1))
    out["jianzhi"] = dict(x0=JP["cx"] - JP_IWX, x1=JP["cx"] + JP_IWX,
                          y0=JP["cy"] - JP_IWY, y1=JP["cy"] + JP_IWY,
                          floor=JP["floor"], door_axis="-Y",
                          clear_h=3.40, frame_z=(0.30, 1.95), storeys=1)
    return out


DESKS = []


def _desks():
    out = []
    for hid, cx, cy in (("zhuxianzhen", -32.0, -30.0),
                        ("songhua", -32.0, -12.0),
                        ("bianxiu", 32.0, -30.0),
                        ("qinghua", 32.0, -12.0)):
        for i, yy in enumerate((cy + 3.55, cy - 3.55)):
            out.append(dict(key=f"desk_{hid}_{i + 1}", hall=hid,
                            cn=f"{INTERIOR[hid].get('cn', hid)}·案台{i + 1}",
                            x=cx, y=yy, rot=0.0, w=2.40, d=1.05,
                            top_z=0.86))
    for i, xx in enumerate((JP["cx"] - 3.6, JP["cx"] + 3.6)):
        out.append(dict(key=f"desk_jianzhi_{i + 1}", hall="jianzhi",
                        cn=f"镂金坊·案台{i + 1}", x=xx, y=JP["cy"] + 0.40,
                        rot=0.0, w=2.40, d=1.05, top_z=0.86))
    return out


def build(C):
    t0 = __import__("time").time()
    n0 = len(C.objects)
    for h in (
            dict(id="zhuxianzhen", cn="刊木堂", cx=-32.0, cy=-30.0,
                 rot=90.0, storeys=1),
            dict(id="songhua", cn="澄怀轩", cx=-32.0, cy=-12.0,
                 rot=90.0, storeys=2),
            dict(id="bianxiu", cn="针经阁", cx=32.0, cy=-30.0,
                 rot=-90.0, storeys=1),
            dict(id="qinghua", cn="素肌堂", cx=32.0, cy=-12.0,
                 rot=-90.0, storeys=2)):
        _hall(C, h)
    _jianzhi(C)
    _gallery(C)
    _garden(C)

    global INTERIOR, DESKS
    INTERIOR = _interior()
    for k, v in INTERIOR.items():
        v["cn"] = dict(zhuxianzhen="刊木堂", songhua="澄怀轩",
                       bianxiu="针经阁", qinghua="素肌堂",
                       jianzhi="镂金坊")[k]
    DESKS = _desks()
    for d in DESKS:
        d["cn"] = INTERIOR[d["hall"]]["cn"] + d["cn"].split("·")[-1]
    _report(C, n0, t0)
    return C


def _report(C, n0, t0):
    objs = C.objects[n0:]
    tot = 0
    for ob in objs:
        tot += mu.tri_count(ob)
    xs = [ob.matrix_world.translation for ob in objs]
    import mathutils
    mn = mathutils.Vector((1e9, 1e9, 1e9))
    mx = mathutils.Vector((-1e9, -1e9, -1e9))
    for ob in objs:
        for c in ob.bound_box:
            p = ob.matrix_world @ mathutils.Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], p[i])
                mx[i] = max(mx[i], p[i])
    zmax = 0.0
    for ob in objs:
        for c in ob.bound_box:
            zmax = max(zmax, (ob.matrix_world @ mathutils.Vector(c)).z)
    print(f"[halls] {len(objs)} 对象 {tot} tri  {time_since(t0):.2f}s  "
          f"max(z)={zmax:.3f}")
    print(f"[halls] bbox=({mn.x:.3f},{mn.y:.3f},{mn.z:.3f}) -> "
          f"({mx.x:.3f},{mx.y:.3f},{mx.z:.3f})")
    print("[halls] INTERIOR:")
    for k, v in INTERIOR.items():
        print(f"   {k:12s} {v['cn']:4s} x[{v['x0']:.2f},{v['x1']:.2f}] "
              f"y[{v['y0']:.2f},{v['y1']:.2f}] floor={v['floor']:.2f} "
              f"{v['storeys']}F door={v['door_axis']}")
    print(f"[halls] DESKS {len(DESKS)}:")
    for d in DESKS:
        print(f"   {d['key']:20s} ({d['x']:.2f},{d['y']:.2f}) rot={d['rot']} "
              f"w={d['w']} d={d['d']}")
    # 预算诊断：按对象 tri 排序（实例化对象共享 mesh，但审计按对象计 tri）
    rows = []
    for ob in objs:
        rows.append((mu.tri_count(ob), ob.name))
    rows.sort(reverse=True)
    print(f"[halls] tri 前 12 对象: " + ", ".join(
        f"{n}={t}" for t, n in rows[:12]))
    bycat = {}
    for ob in objs:
        k = ob.get("cat", "")
        bycat[k] = bycat.get(k, 0) + mu.tri_count(ob)
    print("[halls] tri 分类: " + ", ".join(
        f"{k}={v}" for k, v in sorted(bycat.items())))


def time_since(t0):
    import time
    return time.time() - t0


