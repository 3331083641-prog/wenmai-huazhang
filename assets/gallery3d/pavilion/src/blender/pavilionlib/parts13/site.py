# -*- coding: utf-8 -*-
"""v13 场地（80×96m 宋风四方水院）—— parts13/site.py

构件：
  1 青石大台基 x±40 y±48，顶面 z=0.00，厚 1.20，侧面垂直切平（不做须弥座/裙边/外围地坪）
  2 汉白玉收边带 四周宽 1.60，顶面 +0.012（比铺装高 12mm，防共面）
  3 青石铺装 1.8×1.8m 分缝，缝 12mm 深 8mm（真实凹槽，不靠贴图）；汉白玉御道 x±3.2
  4 台基四周汉白玉望柱栏杆（南侧 x±12 断开）
  5 金水院水池 x±20 y[-36,-14] + 汉白玉石桥（6m 宽、9 对望柱）
  6 后苑方池 x±9 y[27,39]
  （主殿月台/踏步由 parts13/hall.py 建，本文件不建，只做避让）

尺寸唯一真源：pavilionlib/dim13.py（DIM13）。本文件只出现两类数字：
  ① D 上的方案尺寸；② 由 D 推导的构造余量（缝宽/防共面高差/避让净距），全部具名常量。

竖向层叠（唯一 ±0 面 = 青石铺装完成面）：
    G      = D.GROUND_Z        = 0.000   铺装完成面
    PLATE_TOP = G - 0.008      = -0.008  台基结构面 = 铺装凹缝底（缝深 8mm）
    PLATE_BOT = G - PLATE_THICK= -1.200  台基底面
    收边带顶  = G + 0.012      比铺装高 12mm
    御道顶    = G + 0.008      比铺装高 8mm
    压顶顶    = D.POOL_COPING_Z = +0.060 比台基面高 60mm

几何铁律（本轮验收重点，已按实测标定）：
  · 面贴面「水平承托」不会被判相交（BVH 实测 hits=0），因此压在台面上的构件只留承托即可；
  · 面贴面「竖直并列」会被判共面相交（实测 hits=2），所以任何竖直接缝一律留 ≥20mm 净缝；
  · 水平共面（Z-fighting）一律用 8~12mm 高差 + 不做底面 规避。
"""
from __future__ import annotations

import math
import bmesh

from .. import mesh_util as mu
from ..dim13 import DIM13 as D

# ============================================================ 竖向基准
G = D.GROUND_Z                     #  0.000 铺装完成面
PLATE_TOP = G - 0.008              # -0.008 台基结构面 = 铺装凹缝底（8mm 凹槽）
PLATE_BOT = G - D.PLATE_THICK      # -1.200 台基底面
EDGE_BAND = D.PLATE_EDGE_BAND      #  1.600 收边带宽
EDGE_LIP = 0.012                   # 收边带高差：任务书 12mm（dim13 注释写 12mm、值给 0.12，按任务书取 0.012）
EDGE_TOP = G + EDGE_LIP            # +0.012
DAO_TOP = G + 0.008                # +0.008 御道顶
DAO_HX = 3.20                      # 御道半宽（任务书 x±3.2，即 6.4m，与 6m 石桥齐宽）

PX, PYS, PYN = D.PLATE_X, D.PLATE_Y_S, D.PLATE_Y_N
PLATE_RECT = (-PX, PX, PYS, PYN)

# ============================================================ 铺装
PAVE_STEP = 1.80                   # 石板 1.8×1.8m
PAVE_JOINT = 0.012                 # 缝宽 12mm（每侧内缩 6mm）
PAVE_HALF = PAVE_JOINT * 0.5
PAVE_MIN = 0.002                   # 铺装区离收边带内缘的名义余量；+6mm 内缩后净缝 = 8mm
PAVE_X0 = -PX + EDGE_BAND + PAVE_MIN
PAVE_X1 = PX - EDGE_BAND - PAVE_MIN
PAVE_Y0 = PYS + EDGE_BAND + PAVE_MIN
PAVE_Y1 = PYN - EDGE_BAND - PAVE_MIN

CLEAR = 0.020                      # 构件避让净缝（竖直并列一律 ≥20mm）
HOLE_GAP = 0.020                   # 铺装避让洞比实体外扩量

# ============================================================ 水池 / 石桥 / 栏杆
POOL_OPEN = (D.POOL_X0, D.POOL_X1, D.POOL_Y0, D.POOL_Y1)
RG_OPEN = (D.RG_POOL_X0, D.RG_POOL_X1, D.RG_POOL_Y0, D.RG_POOL_Y1)
POOL_WALL = D.POOL_WALL_T - 0.008  # 池壁外皮比台基洞面缩 8mm（0.442）
COP_IN = 0.040                     # 压顶内缘相对池壁内立面退 40mm ……
WATER_INSET = 0.010                # …… 水面比池壁内立面缩 10mm → 压顶内缘到水面净缝 30mm
COP_OUT = COP_IN + D.POOL_COPING_W  # 压顶外缘 0.590（主池）/ 0.540（后苑）
PLATE_HOLE = D.POOL_WALL_T          # 台基洞比池开口外扩 = 池壁厚

RAIL_X = PX - D.RAIL_IN            # 39.10 东西栏杆中线
RAIL_Y = PYN - D.RAIL_IN           # 47.10 南北栏杆中线
RAIL_Z0 = EDGE_TOP                 # 柱础落面
RAIL_TOP = RAIL_Z0 + D.RAIL_H      # 0.962
RAIL_SHAFT = 0.62                  # 柱身顶（其上柱帽）
RAIL_CAP0, RAIL_CAP1 = 0.620, 0.672
RAIL_CAP_H = 0.11                  # 柱帽半宽（0.22 见方）
BAR_W = 0.10                       # 地栿/寻杖 断面宽
BAR_DL = EDGE_TOP + 0.080          # 地栿顶 0.092
BAR_XZ0 = RAIL_TOP - 0.140         # 寻杖底 0.822
BAR_XZ1 = RAIL_TOP - 0.050         # 寻杖顶 0.912
BAL_H = BAR_XZ0 - BAR_DL           # 宝瓶净高 0.730
BAR_END = D.RAIL_POST_W * 0.5 + CLEAR   # 横杆端头离柱心 = 柱半宽 + 20mm

BR_X = D.BRIDGE_POST_X             # 2.90 桥望柱中线
BR_POST_W = D.BRIDGE_POST[0]       # 0.30
BR_POST_H = D.BRIDGE_POST[2]       # 1.05（含柱顶莲苞，绝对标高）
BR_DECK = D.BRIDGE_DECK_Z          # 0.10
BR_ARCH = 0.25                     # v15：桥面中部起拱（0.10 → 0.35）
BR_SEG = 24                        # 桥板沿跨度的扫掠段数
BR_T = D.BRIDGE_T                  # 0.26
BR_GAP = D.BRIDGE_GAP              # 0.06 两片桥板中缝
BR_BASE = BR_DECK + 0.020          # 柱础底 0.12（桥面 +20mm）
BR_PANEL_Z0 = BR_DECK + 0.020      # 栏板底 0.12（与桥面留 20mm）
BR_PANEL_Z1 = 0.860                # 栏板顶
BR_RAIL_Z1 = 0.980                 # 寻杖顶

# ============================================================ 与主殿（parts13/hall.py）的避让
# hall.py _taiji(): TJX=HX+1.20、TJY0=Y0-1.20、TJY1=Y1+1.20、勒脚外凸 e=0.035
#                  台阶 STEP_R=0.15×2 级、STEP_T=0.33、阶宽半 s=3.50、垂带石外扩 0.42、
#                  垂带石南端再外伸 0.10；东西阶 y[-5.00,-1.00]
HALL_OUT = 1.20
HALL_LEDGER = 0.035
HALL_STEP_S = 3.50
HALL_STEP_T = 0.33
HALL_STEP_N = 2
HALL_CHEEK = 0.42
HALL_CHEEK_EXT = 0.10
HALL_SIDE_Y = (-5.00, -1.00)


def _hall_keepouts():
    """主殿台明/勒脚/三面踏步的避让矩形（各外扩 HOLE_GAP）。"""
    g = HOLE_GAP
    hx = D.HALL_HX + HALL_OUT + HALL_LEDGER + g              # 14.255
    y0 = D.HALL_Y0 - HALL_OUT - HALL_LEDGER - g              # -1.255
    y1 = D.HALL_Y1 + HALL_OUT + HALL_LEDGER + g              # 19.255
    s = D.HALL_Y0 - HALL_OUT - HALL_STEP_N * HALL_STEP_T - HALL_CHEEK_EXT  # -1.960 垂带南端
    step_x = HALL_STEP_S + HALL_CHEEK + g                    # 3.940
    sx = D.HALL_HX + HALL_OUT + HALL_STEP_N * HALL_STEP_T + g  # 14.880
    return [
        (-hx, hx, y0, y1),                                   # 台明 + 勒脚
        (-step_x, step_x, s - g, y0),                        # 南阶 + 垂带
        (-HALL_STEP_S - g, HALL_STEP_S + g,
         y1, D.HALL_Y1 + HALL_OUT + HALL_STEP_N * HALL_STEP_T + g),   # 北阶
        (D.HALL_HX + HALL_OUT - g, sx, HALL_SIDE_Y[0] - g, HALL_SIDE_Y[1] + g),   # 东阶
        (-sx, -(D.HALL_HX + HALL_OUT - g), HALL_SIDE_Y[0] - g, HALL_SIDE_Y[1] + g),  # 西阶
    ]


def _paving_holes():
    """铺装避让洞：水池压顶外缘 / 主殿 / 御道 / 后苑方池，全部外扩 HOLE_GAP。"""
    g = HOLE_GAP
    holes = []
    for (x0, x1, y0, y1) in (POOL_OPEN, RG_OPEN):
        holes.append((x0 - COP_OUT - g, x1 + COP_OUT + g, y0 - COP_OUT - g, y1 + COP_OUT + g))
    holes += _hall_keepouts()
    # 御道：避让洞 = 御道矩形四边各外扩 HOLE_GAP（保证御道整块落在洞内、四周净缝 20mm）
    holes.append((-DAO_HX - g, DAO_HX + g, DAO_Y_S0 - g, DAO_Y_S1 + g))
    holes.append((-DAO_HX - g, DAO_HX + g, DAO_Y_N0 - g, DAO_N_END + g))
    return holes


# 御道：南段 y[-46.38, 池南压顶外缘]，北段 [池北压顶外缘, -2.00]；两端各留 20mm/40mm 净距
DAO_Y_S0 = PYS + EDGE_BAND + CLEAR          # -46.380（离收边带内缘 20mm，避免竖直贴面）
DAO_Y_S1 = D.POOL_Y0 - COP_OUT - 0.008     # 御道与压顶留 8 mm 分缝。
DAO_Y_N0 = D.POOL_Y1 + COP_OUT + 0.008
DAO_N_END = -2.000                          # 北端止于 hall 南阶/垂带（-1.96）之外 40mm

# ============================================================ 须弥座五段线脚（z 0 → -1.20）
# v15：台基外轮廓锁死 80×96 —— **上枋外缘 = ±40.000 / ±48.000 是唯一最外包络**，
# 上枭/束腰/下枭/下枋/圭角全部退入，不靠外挑撑尺寸，也不加托盘。
XM_CORE = 39.80                    # 台基内部实体半宽（须弥座内壁与实体共边，不做重合面）
XM_IN = -(PX - XM_CORE)            # 内壁相对名义边的偏移 -0.200
XM_TOP = PLATE_TOP                 # -0.008 上枋顶（收边带压在上面 20mm）
XM_FANG0 = (0.000, -0.080)         # 上枋：外缘严格 40.000，z 0…-0.08
XM_XT = -0.070                     # 上枭带顶（上枋底面内收 0.070 形成深挑檐）
XM_XB = -0.095                     # 上枭带底（z -0.08…-0.24 的 8 段外凸弧）
XM_UB = 0.010                      # 上枭弧中段外凸量（-0.070 → -0.060）
XM_DB = 0.040                      # 下枭弧中段外凸量（-0.095 → -0.055）
XM_XIAO0 = (XM_XB, -0.240)         # 兼容旧引用 = (-0.085, -0.240)
XM_W0, XM_W1 = -0.240, -0.680      # 束腰 z 范围
XM_WD = -0.140                     # 束腰面（= 壶门凹底；壶门框凸到 -0.120，凹深 20mm）
XM_HD = -0.140                     # 壶门凹底（与束腰面同高，凹深由凸框体现）
XM_HD0, XM_HD1 = -0.300, -0.620    # 壶门开口 z 范围（上下各留 0.06 边）
XM_G0, XM_G1 = -0.640, -0.660      # 束腰底部阴影线（宽 0.02、再凹 5mm，stone_dark）
XM_GD = -0.145
XM_DXR = -0.050                    # 下枭外张终点（退入 0.05）
XM_DX0, XM_DX1 = -0.680, -0.860    # 下枭 z 范围（8 段余弦 + 覆莲瓣）
XM_BOT = -1.200                    # 下枋圭角底（= -PLATE_THICK）
XM_ROUND = 0.020                   # 圭角底圆角半径
XM_NV = 8                          # 弧面段数（v15：8 段三角函数）

XM_ZHU_W = 0.22                    # 束腰间柱宽
XM_ZHU_OUT = -0.060                # 间柱外缘（凸出束腰 0.06）
XM_ZHU_IN = -0.145                 # 间柱内缘（埋入束腰 5mm 嵌槽）
XM_ZHU_CH = 0.015                  # 间柱倒角
XM_ZHU_Z0, XM_ZHU_Z1 = -0.248, -0.672   # 间柱上下各留 8mm，不碰上枭/下枭
XM_ZHU_STEP = 3.6                  # 间柱间距（壶门一跨一个）

# 莲瓣（仰莲 / 覆莲）：沿周每 0.75m 一瓣，凸出 21mm，瓣间自然留缝
LOTUS_STEP = 0.75                  # 瓣距
LOTUS_PER = 2                      # 每个 0.75m 节距内 2 瓣（瓣距 0.375）
LOTUS_W = 0.34                     # 单瓣宽（瓣间净缝 0.035）
LOTUS_S = (-1.00, -0.90, 0.00, 0.90, 1.00)         # 单瓣横向 5 站位（两侧近垂直的瓣缘）
LOTUS_OFF = (-0.020, 0.010, 0.055, 0.010, -0.020)  # 对应凸出量：瓣缘沉入 20mm、瓣脊 +55mm

# 壶门（每跨一个，真实凹槽）：框凸到 -0.120，凹底 -0.140 → 凹深 20mm
HM_M = 0.180                       # 壶门框距间柱内侧
HM_FRAME = 0.050                   # 框宽（沿墙）
HM_DEPTH = 0.040                   # 框凸出束腰面（壶门凹深 40mm）
HM_SCROLL_R = 0.120                # 卷云外径
HM_EXAMPLES = 16                   # 卷云采样数（≥16，连续弧）

CH_LEN = 0.55                      # 螭首长（挑出方向，含嵌入部分）
CH_W = 0.28                        # 螭首宽
CH_H = 0.26                        # 螭首高

# 螭首位置：(x, y, z, rot_z)。rot_z 使局部 +Y 指向挑出方向。
CH_CORNER = [
    (+PX + 0.017, +PYN + 0.017, -0.010, -45.0),   # 东北
    (-PX - 0.017, +PYN + 0.017, -0.010, +45.0),   # 西北
    (-PX - 0.017, PYS - 0.017, -0.010, +135.0),   # 西南
    (+PX + 0.017, PYS - 0.017, -0.010, -135.0),   # 东南
]
CH_BRIDGE = [
    (+3.55, D.POOL_Y0 + 0.022, +0.005, 0.0),
    (-3.55, D.POOL_Y0 + 0.022, +0.005, 0.0),
    (+3.55, D.POOL_Y1 - 0.022, +0.005, 180.0),
    (-3.55, D.POOL_Y1 - 0.022, +0.005, 180.0),
]


def _xumizuo_profile():
    """须弥座立面剖面 (r, z) 与逐段材质；r = 相对名义边（±40 / -48..48）的外扩量。

    自内壁顶起顺时针（在 (r,z) 平面）绕一圈，交回内壁底闭合。
    """
    P = [(XM_IN, XM_TOP)]
    S = []

    def seg(r, z, mat=1):
        S.append(mat)
        P.append((r, z))

    seg(XM_FANG0[0], XM_TOP)                           # 上枋顶（朝上，被收边带压住）
    seg(XM_FANG0[0], XM_FANG0[1])                      # 上枋立面（严格 40.000）
    seg(XM_XT, XM_FANG0[1])                            # 上枋底面挑檐（内收 0.050）
    for i in range(1, XM_NV + 1):                      # 上枭：8 段外凸弧（-0.050 → -0.020 → -0.050）
        t = i / XM_NV
        seg(XM_XT + XM_UB * math.sin(math.pi * t), -0.080 - 0.160 * t)
    seg(XM_WD, XM_W0)                                  # 上枭底 → 束腰面（朝下小台阶）
    seg(XM_WD, XM_G0)                                  # 束腰面（壶门凹底，-0.240 → -0.640）
    seg(XM_GD, XM_G0, 0)                               # 阴影线上口（stone_dark，再凹 5mm）
    seg(XM_GD, XM_G1, 0)                               # 阴影线凹面（stone_dark）
    seg(XM_WD, XM_G1, 0)                               # 阴影线下口（stone_dark）
    seg(XM_WD, XM_W1)                                  # 束腰到底 -0.680
    for i in range(1, XM_NV + 1):                      # 下枭：8 段外凸弧（-0.140 → -0.050，中段再凸 0.035）
        t = i / XM_NV
        seg(XM_WD + (XM_DXR - XM_WD) * t + XM_DB * math.sin(math.pi * t),
            XM_DX0 - 0.180 * t)
    seg(XM_DXR, -1.180)                                # 下枋立面（退入 0.04）
    for i in range(1, 4):                              # 圭角底 0.02 圆角（3 段）
        a = math.pi * 0.5 * i / 3.0
        seg(XM_DXR - XM_ROUND + XM_ROUND * math.cos(a),
            -1.180 - XM_ROUND * math.sin(a))
    seg(XM_IN, XM_BOT)                                 # 底面
    S.append(1)                                        # 闭合段 = 内壁
    return P, S


def _poly_area(P):
    """(r,z) 平面闭合多边形有向面积（>0 = 逆时针）。"""
    n = len(P)
    return 0.5 * sum(P[i][0] * P[(i + 1) % n][1] - P[(i + 1) % n][0] * P[i][1] for i in range(n))


# ============================================================ 基础原语
def _grow(rect, d):
    x0, x1, y0, y1 = rect
    return (x0 - d, x1 + d, y0 - d, y1 + d)


def _v(bm, x, y, z):
    return mu.v(bm, (x, y, z))


def _quad(bm, p0, p1, p2, p3, mi=0):
    return mu.face(bm, (p0, p1, p2, p3), mi)


def _slab(bm, x0, x1, y0, y1, z0, z1):
    """石板：顶面 + 四侧面，**不做底面**（底面压在台基面上，省掉共面隐患）。"""
    _quad(bm, _v(bm, x0, y0, z1), _v(bm, x1, y0, z1), _v(bm, x1, y1, z1), _v(bm, x0, y1, z1))
    _quad(bm, _v(bm, x0, y0, z0), _v(bm, x1, y0, z0), _v(bm, x1, y0, z1), _v(bm, x0, y0, z1))
    _quad(bm, _v(bm, x1, y0, z0), _v(bm, x1, y1, z0), _v(bm, x1, y1, z1), _v(bm, x1, y0, z1))
    _quad(bm, _v(bm, x1, y1, z0), _v(bm, x0, y1, z0), _v(bm, x0, y1, z1), _v(bm, x1, y1, z1))
    _quad(bm, _v(bm, x0, y1, z0), _v(bm, x0, y0, z0), _v(bm, x0, y0, z1), _v(bm, x0, y1, z1))


def _box(bm, x0, x1, y0, y1, z0, z1):
    """完整六面盒（底面可见时用）。"""
    mu.box_mm(bm, x0, x1, y0, y1, z0, z1)


def _walls(bm, rect, z0, z1, inward=False):
    """矩形四侧竖壁（无顶无底），法线朝外（inward=True 朝内）。"""
    x0, x1, y0, y1 = rect
    O = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    for i in range(4):
        k = (i + 1) % 4
        a, b = O[i], O[k]
        if inward:
            _quad(bm, _v(bm, b[0], b[1], z0), _v(bm, b[0], b[1], z1),
                  _v(bm, a[0], a[1], z1), _v(bm, a[0], a[1], z0))
        else:
            _quad(bm, _v(bm, a[0], a[1], z0), _v(bm, b[0], b[1], z0),
                  _v(bm, b[0], b[1], z1), _v(bm, a[0], a[1], z1))


def _hring(bm, outer, inner, z, up=False):
    """水平环形带（四个梯形，自动斜接转角）。"""
    ox0, ox1, oy0, oy1 = outer
    ix0, ix1, iy0, iy1 = inner
    O = ((ox0, oy0), (ox1, oy0), (ox1, oy1), (ox0, oy1))
    I = ((ix0, iy0), (ix1, iy0), (ix1, iy1), (ix0, iy1))
    for i in range(4):
        k = (i + 1) % 4
        if up:
            _quad(bm, _v(bm, *O[i], z), _v(bm, *O[k], z), _v(bm, *I[k], z), _v(bm, *I[i], z))
        else:
            _quad(bm, _v(bm, *I[i], z), _v(bm, *I[k], z), _v(bm, *O[k], z), _v(bm, *O[i], z))


def _rect_tube(bm, rect, prof, close=False, mats=None):
    """沿矩形环路径扫掠剖面 (r, z)：r = 相对开口/名义矩形的外扩量（转角自动斜接成直角）。

    法线由绕序决定（已验证）：闭合剖面会先按 (r,z) 有向面积统一成逆时针，再按
    quad=[a_i, a_k, b_k, b_i] 铺面 ⇒ 外侧朝外、顶面朝上、底面朝下。
    mats 为逐段材质索引（长度 = 剖面段数 = len(prof) 或 len(prof) 含闭合段）。
    """
    x0, x1, y0, y1 = rect
    n = len(prof)
    seg_n = n if close else n - 1
    if mats is None:
        mats = [0] * seg_n
    if close and _poly_area(prof) < 0.0:
        # 反向：段序也随之镜像，保证材质跟段走
        prof = list(prof)[::-1]
        mats = [mats[(n - 2 - i) % n] for i in range(n)]
    rings = [((x0 - r, y0 - r, z), (x1 + r, y0 - r, z), (x1 + r, y1 + r, z), (x0 - r, y1 + r, z))
             for (r, z) in prof]
    for j in range(seg_n):
        a, b = rings[j], rings[(j + 1) % n]
        mi = mats[j] if j < len(mats) else 0
        if {prof[j],prof[(j+1)%n]}=={(0,XM_TOP),(0,-.080)}:
            # 四个对角尾榫共用各自的水平石托，45° 槽背退入 54 mm。
            # 将槽直接放进上枋的外轮廓，三角托面与上部遮檐同属一片石材。
            profiles=[(-.080,0),(-.065,0),(-.065,.054),(-.020,.054),(-.020,0),(XM_TOP,0)]
            if a[0][2]>b[0][2]:profiles.reverse()
            bands=[[(x0+d,y0,z),(x1-d,y0,z),(x1,y0+d,z),(x1,y1-d,z),
                    (x1-d,y1,z),(x0+d,y1,z),(x0,y1-d,z),(x0,y0+d,z)] for z,d in profiles]
            for ra,rb in zip(bands,bands[1:]):
                for k in range(8):
                    l=(k+1)%8
                    face=list(dict.fromkeys((ra[k],ra[l],rb[l],rb[k])))
                    if len(face)>2 and len({v[2] for v in face})==1 and k%2==0:
                        continue  # 同一水平边直段共线，只有四个端角需要托面。
                    if len(face)>2:mu.face(bm,[_v(bm,*v) for v in face],mi)
            continue
        for i in range(4):
            k = (i + 1) % 4
            _quad(bm, _v(bm, *a[i]), _v(bm, *a[k]), _v(bm, *b[k]), _v(bm, *b[i]), mi)


# ============================================================ 矩形布尔（只减不并）
def _cuts(lo, hi, step, origin):
    """在 [lo,hi] 内生成切分点，含 origin + k*step 的格线。"""
    pts = {round(lo, 6), round(hi, 6)}
    k0 = int(math.floor((lo - origin) / step)) - 1
    k1 = int(math.ceil((hi - origin) / step)) + 1
    for k in range(k0, k1 + 1):
        x = origin + k * step
        if lo + 1e-6 < x < hi - 1e-6:
            pts.add(round(x, 6))
    return sorted(pts)


def _sub_many(rect, holes):
    """矩形减去若干矩形洞 → 互不重叠的矩形列表（沿 X 分带、带内沿 Y 切）。"""
    x0, x1, y0, y1 = rect
    if x1 - x0 < 1e-9 or y1 - y0 < 1e-9:
        return []
    xs = {round(x0, 6), round(x1, 6)}
    for (hx0, hx1, hy0, hy1) in holes:
        if hy1 <= y0 + 1e-9 or hy0 >= y1 - 1e-9:
            continue
        for xv in (hx0, hx1):
            if x0 + 1e-6 < xv < x1 - 1e-6:
                xs.add(round(xv, 6))
    xs = sorted(xs)
    out = []
    for i in range(len(xs) - 1):
        a, b = xs[i], xs[i + 1]
        if b - a < 1e-9:
            continue
        mid = (a + b) * 0.5
        ys = {round(y0, 6), round(y1, 6)}
        for (hx0, hx1, hy0, hy1) in holes:
            if hx0 > mid or hx1 < mid:
                continue
            if y0 + 1e-6 < hy0 < y1 - 1e-6:
                ys.add(round(hy0, 6))
            if y0 + 1e-6 < hy1 < y1 - 1e-6:
                ys.add(round(hy1, 6))
        ys = sorted(ys)
        for j in range(len(ys) - 1):
            c, d = ys[j], ys[j + 1]
            if d - c < 1e-9:
                continue
            cx, cy = mid, (c + d) * 0.5
            inside = False
            for (hx0, hx1, hy0, hy1) in holes:
                if hx0 < cx < hx1 and hy0 < cy < hy1:
                    inside = True
                    break
            if not inside:
                out.append((a, b, c, d))
    return out


# ============================================================ 1) 台基（宋式须弥座）
def _plate(C):
    """台基 = ①内部实体（须弥座内壁以内，含两处池洞） + ②沿四条外边一次挤出的五段线脚。

    内壁与实体共边（x=±XM_CORE），不做重合面；线脚剖面闭合，转角自动斜接。
    """
    bm = mu.new_bm()
    holes = [(_grow(POOL_OPEN, PLATE_HOLE)), _grow(RG_OPEN, PLATE_HOLE)]
    core = (POOL_OPEN[0] * 0 - XM_CORE, XM_CORE,
            PYS + (PX - XM_CORE), PYN - (PX - XM_CORE))
    for (a, b, c, d) in _sub_many(core, holes):
        _box(bm, a, b, c, d, PLATE_BOT, XM_TOP)
    prof, mats = _xumizuo_profile()
    _rect_tube(bm, PLATE_RECT, prof, close=True, mats=mats)
    C.bm_obj(bm, "site13_plate", "foundation", ("宫苑", "台基"),
             cn="青石大台基 80×96m（宋式须弥座五段线脚，上枋外挑 0.04）",
             mat=("stone_dark", "stone_lite"), uv=1.0)
    print("[site13] 须弥座 上枋 0…-0.08 外缘=40.000（锁定最外，底面挑檐 0.05）｜"
          "上枭 -0.08…-0.24 内收 0.070→-0.060 外凸弧（8 段 + 仰莲瓣脊 55mm）｜"
          "束腰 -0.24…-0.68 面-0.140（壶门凸框至 -0.100，凹深 40mm）｜"
          "下枭 -0.68…-0.86 回 -0.050（8 段外凸弧 + 覆莲瓣脊 55mm）｜"
          "下枋圭角 -0.86…-1.20 退入 0.050 + 圆角 0.02")


def _prism_z(bm, poly, z0, z1, mi=0):
    """竖直棱柱：poly = [(x,y), ...]，自动统一为逆时针，侧面朝外 + 上下封盖。"""
    area = 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1]
                     - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    if area < 0.0:
        poly = list(reversed(poly))
    n = len(poly)
    a = [_v(bm, x, y, z0) for (x, y) in poly]
    b = [_v(bm, x, y, z1) for (x, y) in poly]
    for i in range(n):
        k = (i + 1) % n
        _quad(bm, a[i], a[k], b[k], b[i], mi)          # 侧壁朝外
    mu.face(bm, tuple(b), mi)                          # 顶 +Z
    mu.face(bm, tuple(reversed(a)), mi)                # 底 -Z


def _zhu_poly(u, face, n, hw, ch):
    """间柱横截面（贴墙）：u = 沿墙位置，face = 名义边坐标，n = 外法线方向 ±1。

    s_in = XM_ZHU_IN(-0.145) 内缘、s_out = XM_ZHU_OUT(-0.060) 外缘，均沿 n 量取。
    """
    a0, a1 = u - hw, u + hw
    b_in, b_out = face + n * XM_ZHU_IN, face + n * XM_ZHU_OUT
    if n > 0:
        return [(a0, b_in), (a1, b_in), (a1, b_out - ch),
                (a1 - ch, b_out), (a0 + ch, b_out), (a0, b_out - ch)]
    return [(a0, b_in), (a0, b_out + ch), (a0 + ch, b_out),
            (a1 - ch, b_out), (a1, b_out + ch), (a1, b_in)]


def _xumizuo_relief(C):
    """束腰间柱（每 3.6m 一根，四面）+ 四角角柱：凸出束腰 0.06，内缘埋入 5mm 嵌槽。"""
    bm = mu.new_bm()
    hw = XM_ZHU_W * 0.5
    n_zhu = 0
    # (face, lo, hi, 墙沿 x? or y?, 外法线符号)
    sides = [
        (PYN, -PX, PX, True, +1),      # 北墙 y=+48，沿 x
        (PYS, -PX, PX, True, -1),      # 南墙 y=-48
        (PX, PYS, PYN, False, +1),     # 东墙 x=+40，沿 y
        (-PX, PYS, PYN, False, -1),    # 西墙 x=-40
    ]
    for (face, lo, hi, along_x, n) in sides:
        us, cnt = _post_us(lo, hi)
        for u in us[1:-1]:                           # 两端交给角柱，与壶门分跨同一节距
            pts = _zhu_poly(u, face, n, hw, XM_ZHU_CH)
            if along_x:
                poly = [(a, b) for (a, b) in pts]
            else:
                poly = [(b, a) for (a, b) in pts]
            _prism_z(bm, poly, XM_ZHU_Z0, XM_ZHU_Z1, 0)
            n_zhu += 1
    # 四角角柱：0.22×0.22 方块，外缘各退 0.06，只切外角
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx = sx * PX
            cy = sy * PYN if sy > 0 else sy * abs(PYS)
            x_in, x_out = cx - sx * 0.28, cx - sx * (-XM_ZHU_OUT)
            y_in, y_out = cy - sy * 0.28, cy - sy * (-XM_ZHU_OUT)
            ch = XM_ZHU_CH
            x_back=cx+sx*XM_ZHU_IN
            y_back=cy+sy*XM_ZHU_IN
            poly = [(x_back,y_in),(x_out,y_in),(x_out,y_out-sy*ch),
                    (x_out-sx*ch,y_out),(x_in,y_out),(x_in,y_back),(x_back,y_back)]
            _prism_z(bm, poly, XM_ZHU_Z0, XM_ZHU_Z1, 0)
    C.bm_obj(bm, "site13_xumizuo_zhu", "foundation", ("宫苑", "台基"),
             cn="须弥座束腰间柱（3.6m 一根）与四角角柱", mat="stone_lite", uv=1.0)
    print("[site13] 须弥座间柱 %d 根 + 角柱 4 根（凸出 0.06、嵌槽 5mm、倒角 0.015）" % n_zhu)


# ============================================================ 1a) 墙面局部坐标 / 分跨
def _wall(side):
    """墙面局部坐标映射：w(u, r) → (x, y)，u 沿墙、r 为外法线方向、z 向上。

    四个映射都是刚体旋转（行列式 +1），因此在局部空间里算好的绕序搬到世界仍然朝外。
    """
    if side == "N":                                   # y=+48，u=x
        return (lambda u, r: (u, PYN + r)), -PX, PX
    if side == "S":                                   # y=-48，u=-x（保持右手）
        return (lambda u, r: (-u, PYS - r)), -PX, PX
    if side == "E":                                   # x=+40，u=-y
        return (lambda u, r: (PX + r, -u)), -PYN, -PYS
    return (lambda u, r: (-PX - r, u)), -PYN, -PYS    # W：x=-40，u=y


def _post_us(lo, hi):
    """间柱（含两端角柱）的 u 坐标与跨数：按 3.6m 节距布置，两端余量对称（不整边等分）。"""
    L = hi - lo
    n = max(1, int(L / XM_ZHU_STEP))
    margin = 0.5 * (L - n * XM_ZHU_STEP)
    return [lo + margin + XM_ZHU_STEP * i for i in range(n + 1)], n


def _lbox(bm, w, u0, u1, r0, r1, z0, z1):
    """局部墙坐标系 (u,r,z) 的六面盒，法线朝外。"""
    def P(u, r, z):
        x, y = w(u, r)
        return _v(bm, x, y, z)
    _quad(bm, P(u0, r0, z0), P(u1, r0, z0), P(u1, r0, z1), P(u0, r0, z1))   # -r
    _quad(bm, P(u0, r1, z0), P(u0, r1, z1), P(u1, r1, z1), P(u1, r1, z0))   # +r
    _quad(bm, P(u0, r0, z0), P(u0, r0, z1), P(u0, r1, z1), P(u0, r1, z0))   # -u
    _quad(bm, P(u1, r0, z0), P(u1, r1, z0), P(u1, r1, z1), P(u1, r0, z1))   # +u
    _quad(bm, P(u0, r0, z0), P(u0, r1, z0), P(u1, r1, z0), P(u1, r0, z0))   # -z
    _quad(bm, P(u0, r0, z1), P(u1, r0, z1), P(u1, r1, z1), P(u0, r1, z1))   # +z


def _prism_wall(bm, w, poly_uz, r0, r1, cap_front=True, cap_back=False):
    """把 (u,z) 平面多边形沿 r 挤出成柱体（局部墙坐标）。

    (u,z) 逆时针 → r0 端面法线 -r、r1 端面 +r；侧壁朝外。
    cap_back=False 时省掉 r0 端面（它贴在束腰凹底上，省一面也避开共面）。
    """
    area = 0.5 * sum(poly_uz[i][0] * poly_uz[(i + 1) % len(poly_uz)][1]
                     - poly_uz[(i + 1) % len(poly_uz)][0] * poly_uz[i][1]
                     for i in range(len(poly_uz)))
    poly = list(poly_uz) if area > 0.0 else list(reversed(poly_uz))
    n = len(poly)

    def P(u, r, z):
        x, y = w(u, r)
        return _v(bm, x, y, z)

    for i in range(n):
        k = (i + 1) % n
        _quad(bm, P(poly[i][0], r0, poly[i][1]), P(poly[k][0], r0, poly[k][1]),
              P(poly[k][0], r1, poly[k][1]), P(poly[i][0], r1, poly[i][1]))
    if cap_back:
        mu.face(bm, tuple(P(u, r0, z) for (u, z) in poly))
    if cap_front:
        mu.face(bm, tuple(P(u, r1, z) for (u, z) in reversed(poly)))


def _lotus_rows(j):
    """莲瓣带的三行 (z, r)：j=0 上枭仰莲、j=1 下枭覆莲，与剖面同一公式取点。"""
    rows = []
    for k in (0.0, 0.5, 1.0):
        if j == 0:
            z = -0.090 - 0.140 * k
            t = (-0.080 - z) / 0.160
            r = XM_XT + XM_UB * math.sin(math.pi * t)
        else:
            z = -0.690 - 0.160 * k
            t = (-0.680 - z) / 0.180
            r = XM_WD + (XM_DXR - XM_WD) * t + XM_DB * math.sin(math.pi * t)
        rows.append((z, r))
    return rows


def _lotus(C):
    """五段线脚上的立体莲瓣：上枭仰莲、下枭覆莲，每 0.75m 一瓣。
    横向 5 站位（瓣缘沉入石面 12mm 形成刻线，瓣脊凸 55mm），瓣尖按行收窄。"""
    bm = mu.new_bm()
    n = 0
    nl = len(LOTUS_OFF)
    for side in ("N", "S", "E", "W"):
        w, lo, hi = _wall(side)
        for j in (0, 1):
            rows = _lotus_rows(j)
            wf = (0.72, 0.88, 1.00) if j == 0 else (1.00, 0.88, 0.72)
            pitch = LOTUS_STEP / LOTUS_PER
            k = int(math.floor((lo + 0.20) / pitch)) - 1
            while True:
                u = k * pitch
                k += 1
                if u > hi - 0.20:
                    break
                if u < lo + 0.20:
                    continue
                st = []
                for i, off in enumerate(LOTUS_OFF):
                    s = LOTUS_S[i]
                    st.append([(u + s * 0.5 * LOTUS_W * wf[m],
                                rows[m][1] + off * wf[m], rows[m][0])
                               for m in range(3)])
                for i in range(len(st) - 1):
                    for m in range(2):
                        _quad(bm, *[_v(bm, *w(a[0], a[1]), a[2]) for a in
                                    (st[i][m], st[i][m + 1], st[i + 1][m + 1], st[i + 1][m])])
                # 两端封口（各自端面的 3 行）
                mu.face(bm, tuple(_v(bm, *w(a[0], a[1]), a[2])
                                  for a in (st[0][0], st[0][2], st[0][1])))
                mu.face(bm, tuple(_v(bm, *w(a[0], a[1]), a[2])
                                  for a in (st[-1][2], st[-1][0], st[-1][1])))
                n += 1
    C.bm_obj(bm, "site13_lotus", "foundation", ("宫苑", "台基"),
             cn="须弥座上枭仰莲 / 下枭覆莲（每 0.75m 一瓣，瓣脊凸 55mm）",
             mat="stone_lite", uv=1.0, smooth=28.0)
    print("[site13] 莲瓣 %d 瓣（仰莲 + 覆莲，每 0.75m，瓣脊凸 55mm）" % n)


def _scroll_uz(cu, cz, r0, mirror, n=HM_EXAMPLES):
    """16 样本连续弧的卷云收口（填充螺旋，(u,z) 多边形）。"""
    pts = []
    for k in range(n):
        f = k / (n - 1.0)
        a = math.pi * 1.45 * (1.0 - f)                  # 261° → 0°，连续弧
        rr = r0 * (1.0 - 0.80 * f)
        pts.append((cu + mirror * rr * math.cos(a), cz + rr * math.sin(a)))
    return pts


def _humen(C):
    """间柱之间一个真实壶门：束腰面 -0.140 为凹底，四周凸框到 -0.120（凹深 20mm），
    上两角 16 样本卷云收口。98 跨 = 南北各 22 + 东西各 27。"""
    bm = mu.new_bm()
    n = 0
    for side in ("N", "S", "E", "W"):
        w, lo, hi = _wall(side)
        us, cnt = _post_us(lo, hi)
        for i in range(cnt):
            a, b = us[i], us[i + 1]
            u0 = a + XM_ZHU_W * 0.5 + 0.060
            u1 = b - XM_ZHU_W * 0.5 - 0.060
            if u1 - u0 < 4.0 * HM_FRAME:
                continue
            z0, z1 = XM_HD1, XM_HD0                        # 由下至上
            fw = HM_FRAME
            r0, r1 = XM_HD, XM_HD + HM_DEPTH               # -0.140 … -0.120
            _lbox(bm, w, u0, u1, r0, r1, z0, z0 + fw)      # 上框
            _lbox(bm, w, u0, u1, r0, r1, z1 - fw, z1)      # 下框
            _lbox(bm, w, u0, u0 + fw, r0, r1, z0 + fw, z1 - fw)   # 左框
            _lbox(bm, w, u1 - fw, u1, r0, r1, z0 + fw, z1 - fw)   # 右框
            # 上两角卷云（在框内侧，收口），镜像方向朝内
            _prism_wall(bm, w, _scroll_uz(u0 + fw + 0.075, z1 - fw - 0.075,
                                          HM_SCROLL_R, +1), r0, r1)
            _prism_wall(bm, w, _scroll_uz(u1 - fw - 0.075, z1 - fw - 0.075,
                                          HM_SCROLL_R, -1), r0, r1)
            n += 1
    C.bm_obj(bm, "site13_humen", "foundation", ("宫苑", "台基"),
             cn="须弥座间柱间壶门（凹深 20mm，凸框 0.05，卷云收口 16 样本）",
             mat="stone_lite", uv=1.0, smooth=26.0)
    print("[site13] 壶门 %d 个（凹深 %.0fmm、框宽 %.0fmm、卷云 %d 样本）"
          % (n, HM_DEPTH * 1000, HM_FRAME * 1000, HM_EXAMPLES))


# ============================================================ 1b) 螭首（吐水兽）
def _taper(bm, y0, a, y1, b, mi=0):
    """沿 +Y 从截面 a=(x0,x1,z0,z1) 渐变到 b 的六面体（六面全部朝外）。"""
    xa0, xa1, za0, za1 = a
    xb0, xb1, zb0, zb1 = b
    p = lambda x, y, z: _v(bm, x, y, z)
    _quad(bm, p(xa0, y0, za0), p(xa1, y0, za0), p(xa1, y0, za1), p(xa0, y0, za1), mi)
    _quad(bm, p(xb1, y1, zb0), p(xb0, y1, zb0), p(xb0, y1, zb1), p(xb1, y1, zb1), mi)
    _quad(bm, p(xa0, y0, za0), p(xb0, y1, zb0), p(xb1, y1, zb0), p(xa1, y0, za0), mi)
    _quad(bm, p(xa0, y0, za1), p(xa1, y0, za1), p(xb1, y1, zb1), p(xb0, y1, zb1), mi)
    _quad(bm, p(xa0, y0, za0), p(xa0, y0, za1), p(xb0, y1, zb1), p(xb0, y1, zb0), mi)
    _quad(bm, p(xa1, y0, za0), p(xb1, y1, zb0), p(xb1, y1, zb1), p(xa1, y0, za1), mi)


def _loft_y(bm, secs, n=12, cap0=True, cap1=True):
    """沿 +Y 放样椭圆截面（曲面头颅/颚）：secs = [(y, cz, rx, rz), ...]，
    截面 x = rx·cos a、z = cz + rz·sin a。"""
    rings = []
    for (y, cz, rx, rz) in secs:
        ring = []
        for k in range(n):
            a = 2.0 * math.pi * k / n
            ring.append(_v(bm, rx * math.cos(a), y, cz + rz * math.sin(a)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        mu.bridge_rings(bm, rings[i], rings[i + 1], closed=True)
    if cap0:
        mu.cap_ring(bm, rings[0], flip=True)
    if cap1:
        mu.cap_ring(bm, rings[-1])
    return rings


def _washer_y(bm, y0, y1, cz, ro, ri, seg=12):
    """沿 Y 轴的圆环（吐水孔）：外圆 ro、内孔 ri，圆心在 (x=0, z=cz)，两端环面封口。"""
    rings = [[] for _ in range(4)]
    # ri 是对边净半径，使 52 mm 圆柱能从多边形孔中通过。
    inner_vertex_r = ri / math.cos(math.pi / seg)
    for k in range(seg):
        a = 2.0 * math.pi * (k + 0.5) / seg
        c, s = math.cos(a), math.sin(a)
        for ring, y, r in zip(rings, (y0, y1, y1, y0), (ro, ro, inner_vertex_r, inner_vertex_r)):
            ring.append(_v(bm, r * c, y, cz + r * s))
    for i, ring in enumerate(rings):
        mu.bridge_rings(bm, ring, rings[(i + 1) % 4])


def _washer_z(bm, z0, z1, cx, cy, ro, ri, seg=12):
    """沿 Z 轴的真贯通圆孔（吐水孔）：外圆 ro、内孔 ri，圆心 (cx, cy)，上下环面封口。

    孔是真实隧道（孔壁 12 quad + 上下环面），不是贴片/黑圈；绕序由调用方 recalc 统一。
    """
    ao, ai = [], []
    for k in range(seg):
        a = 2.0 * math.pi * k / seg
        c, s = math.cos(a), math.sin(a)
        ao.append((cx + ro * c, cy + ro * s))
        ai.append((cx + ri * c, cy + ri * s))
    for i in range(seg):
        j = (i + 1) % seg
        # 外壁
        _quad(bm, _v(bm, ao[i][0], ao[i][1], z0), _v(bm, ao[i][0], ao[i][1], z1),
              _v(bm, ao[j][0], ao[j][1], z1), _v(bm, ao[j][0], ao[j][1], z0))
        # 孔壁
        _quad(bm, _v(bm, ai[i][0], ai[i][1], z0), _v(bm, ai[j][0], ai[j][1], z0),
              _v(bm, ai[j][0], ai[j][1], z1), _v(bm, ai[i][0], ai[i][1], z1))
        # 上环面 / 下环面
        _quad(bm, _v(bm, ai[i][0], ai[i][1], z1), _v(bm, ai[j][0], ai[j][1], z1),
              _v(bm, ao[j][0], ao[j][1], z1), _v(bm, ao[i][0], ao[i][1], z1))
        _quad(bm, _v(bm, ao[i][0], ao[i][1], z0), _v(bm, ai[i][0], ai[i][1], z0),
              _v(bm, ai[j][0], ai[j][1], z0), _v(bm, ao[j][0], ao[j][1], z0))


def _eye_relief(bm, sx, xc, yc, zc, depth, width, height):
    """沿颅侧放样一枚半椭球，底面落入颅面或眼球。"""
    rings = []
    for i in range(5):
        t = i * math.pi / 10
        ring = []
        for j in range(14):
            a = 2 * math.pi * j / 14
            ring.append(_v(bm, sx * (xc + depth * math.sin(t)),
                           yc + width * math.cos(t) * math.cos(a),
                           zc + height * math.cos(t) * math.sin(a)))
        rings.append(ring)
    mu.cap_ring(bm, rings[0], flip=True)
    for a, b in zip(rings, rings[1:]):
        mu.bridge_rings(bm, a, b)
    pole = _v(bm, sx * (xc + depth), yc, zc)
    for j in range(14):
        mu.face(bm, (rings[-1][j], rings[-1][(j + 1) % 14], pole))


def _build_chishou(bm):
    """螭首：局部 +Y 朝外（挑出），原点在台基（上枋）外皮立面上，z=0 为坐口标高。

    兽首长 0.55（含嵌入尾座）、宽 0.28、高 0.26；张口（上下颚分开、口内圆排水孔）、
    双角、须鬃、前爪扒台基边缘；尾部没入上枋（嵌槽，靠嵌合不靠穿模）。
    """
    # 尾座（嵌入上枋 58mm，不另外留缝：嵌槽即坐口）
    _box(bm, -.060,.060,-.060,.008,-.055,-.012)
    _taper(bm, .008, (-.060,.060,-.055,-.012), .030, (-.078,.078,-.118,-.022))
    # 身—颈—颅—吻：一条椭圆放样（12 边），消除方块感；口腔上缘（颅底/上颚下缘）z=-0.160
    _loft_y(bm, [
        (0.010, -0.100, 0.112, 0.082),
        (0.090, -0.122, 0.126, 0.092),
        (0.180, -0.136, 0.118, 0.088),
        (0.265, -0.150, 0.108, 0.086),
        (0.330, -0.156, 0.104, 0.086),
        (0.390, -0.148, 0.106, 0.082),
        (0.440, -0.120, 0.104, 0.050),
        (0.478, -0.106, 0.092, 0.056),
        (0.522, -0.124, 0.074, 0.040),
        (0.548, -0.132, 0.058, 0.032),
    ], n=12)
    # 下颚：独立椭圆放样（10 边），上缘 -0.220，与颅底留 60mm 口裂
    _loft_y(bm, [
        (0.430, -0.240, 0.080, 0.020),
        (0.478, -0.242, 0.072, 0.020),
        (0.520, -0.244, 0.056, 0.018),
        (0.552, -0.246, 0.044, 0.016),
    ], n=10)
    # 吐水口：口腔内横置圆环（轴沿 +Y），环体嵌入上下颚，环内空腔 = 真贯通水路，孔 52mm
    _washer_y(bm, 0.492, 0.540, -0.190, 0.045, 0.026, 24)
    # 双角：卷角（215° 连续弧 16 样本 + 扫掠圆管，末端收细到 8mm）
    for sx in (-1, 1):
        path = []
        for k in range(16):
            t = k / 15.0
            ang = math.radians(-70.0) + math.radians(215.0) * t
            rr = 0.072 * (1.0 - 0.72 * t)
            path.append((sx * (0.052 + 0.012 * t),
                         0.356 + rr * math.cos(ang),
                         -0.006 + rr * math.sin(ang)))
        mu.swept_tube(bm, path, 0.021, segments=5, caps=True, radius_end=0.008)
    # 双耳（贴颅侧外张）
    for sx in (-1, 1):
        xs = sorted((sx * 0.098, sx * 0.126))
        _taper(bm, 0.352, (xs[0], xs[1], -0.076, -0.038),
               0.394, (xs[0], xs[1], -0.086, -0.050))
    # 眉脊（压颅顶前缘，隆起 24mm）
    _taper(bm, 0.412, (-0.098, 0.098, -0.072, -0.048), 0.470, (-0.088, 0.088, -0.084, -0.060))
    # 额顶凸块
    _taper(bm, 0.395, (-0.040, 0.040, -0.074, -0.056), 0.437, (-0.034, 0.034, -0.078, -0.060))
    # 石质突眼与瞳珠，各自有连续曲面；瞳底嵌在眼冠上。
    for sx in (-1, 1):
        _eye_relief(bm, sx, 0.090, 0.438, -0.119, 0.025, 0.027, 0.021)
        _eye_relief(bm, sx, 0.112, 0.441, -0.119, 0.007, 0.010, 0.011)
    # 鼻端双鼻孔
    for sx in (-1, 1):
        xs = sorted((sx * 0.018, sx * 0.040))
        _taper(bm, 0.520, (xs[0], xs[1], -0.100, -0.084),
               0.542, (xs[0], xs[1], -0.104, -0.088))
    # 背脊鬃棱（三块，起伏）
    for (y0, y1, t0, t1) in ((0.300, 0.330, -0.074, -0.052), (0.338, 0.368, -0.076, -0.054),
                             (0.376, 0.406, -0.074, -0.052)):
        _taper(bm, y0, (-0.026, 0.026, t0, t0 + 0.014), y1, (-0.020, 0.020, t1, t1 + 0.014))
    # 五道片状须鬃从脸侧向后梳，截面扁圆，随弧线收成细梢。
    for sx in (-1, 1):
        for i in range(5):
            rings = []
            for j in range(9):
                t = j / 8
                y = 0.403 + 0.009 * i - (0.118 + 0.004 * i) * t
                z = -0.113 - 0.014 * i - 0.026 * math.sin(math.pi * t) + 0.023 * t * t
                x = 0.094 + 0.012 * math.sin(math.pi * t) + 0.008 * t
                scale = 1.0 - 0.91 * t
                ring = []
                for k in range(6):
                    a = k * math.pi / 3
                    ring.append(_v(bm, sx * (x + 0.010 * scale * math.cos(a)), y,
                                   z + 0.009 * scale * math.sin(a)))
                rings.append(ring)
            for a, b in zip(rings, rings[1:]):
                mu.bridge_rings(bm, a, b)
            mu.cap_ring(bm, rings[0], flip=True)
            mu.cap_ring(bm, rings[-1])
    # 前爪：扒住上枋下口（局部 y<0 段嵌入台基 15mm）
    for sx in (-1, 1):
        x0, x1 = sx * 0.100, sx * 0.142
        _taper(bm, -0.015, (min(x0, x1), max(x0, x1), -0.115, -0.020),
               0.075, (min(x0, x1) - 0.004, max(x0, x1) - 0.010, -0.132, -0.062))
        # 三趾（前探 25mm、下探 4mm，读出爪子）
        for c in (0.108, 0.122, 0.136):
            xs = sorted((sx * (c - 0.005), sx * (c + 0.005)))
            _taper(bm, 0.070, (xs[0], xs[1], -0.136, -0.112),
                   0.100, (xs[0], xs[1], -0.140, -0.118))
    # 上下颚各两枚锥牙，牙根入颚，牙尖前后错开。
    for sx in (-1, 1):
        for y0, z0, dz, r in ((0.496, -0.142, -0.064, 0.011), (0.511, -0.240, 0.047, 0.009)):
            path = [(sx * (0.055 - 0.004 * (k / 5)**2), y0 + 0.011 * (k / 5)**2,
                     z0 + dz * k / 5) for k in range(6)]
            mu.swept_tube(bm, path, r, segments=7, caps=True, radius_end=0.0008)
    # 颏（颌下唇棱，贴在颚底外侧）
    _taper(bm, 0.462, (-0.060, 0.060, -0.272, -0.260), 0.545, (-0.038, 0.038, -0.276, -0.264))
    mu.recalc_normals(bm)          # 多个独立闭合壳体，逐个统一朝外


def _chishou(C):
    proto = C.proto("chishou", _build_chishou, mat="stone_lite", smooth=30.0, uv=1.0)
    n = 0
    for (x, y, z, rz) in CH_CORNER + CH_BRIDGE:
        C.place_at(proto, (x, y, z), rot_z=rz,      # place_at 的 rot_z 单位是度
                   name="site13_chishou_%02d" % n, cat="detail",
                   coll_path=("宫苑", "台基"), cn="螭首（吐水兽，须弥座挑出）")
        n += 1
    print("[site13] 螭首 %d 尊（四角 45° 斜挑 + 金水桥两端桥头各 2 尊）" % n)


# ============================================================ 2) 汉白玉收边带
# 牌楼（parts13/gate.py）柱础 0.90 见方（x±4.40/±12.00、y GY±0.45）与夹杆石
# （x±0.26、y GY-0.42±0.16 → 到 y=-46.58）压进收边带 12mm 高差里，
# 故在收边带上开两个口袋（各留 20mm 余量），口袋完全藏在柱础/夹杆石之下。
GATE_BAND_KEEP = []
for _cx in (-D.GATE_COL_X[2], -D.GATE_COL_X[1], D.GATE_COL_X[1], D.GATE_COL_X[2]):
    _y = D.GATE_Y
    GATE_BAND_KEEP.append((_cx - 0.47, _cx + 0.47, _y - 0.47, _y + 0.45))
    GATE_BAND_KEEP.append((_cx - 0.28, _cx + 0.28, _y - 0.695, _y - 0.47))


def _edge_band(C):
    bm = mu.new_bm()
    south = (-PX, PX, PYS, PYS + EDGE_BAND)
    for (a, b, c, d) in _sub_many(south, GATE_BAND_KEEP):
        _slab(bm, a, b, c, d, PLATE_TOP, EDGE_TOP)
    # 落底石和柱础在带石上沉座至铺装标高，保持足底实承。
    for x in (-D.GATE_COL_X[2],-D.GATE_COL_X[1],D.GATE_COL_X[1],D.GATE_COL_X[2]):
        _slab(bm,x-.47,x+.47,D.GATE_Y-.47,PYS+EDGE_BAND,PLATE_TOP,G)
        _slab(bm,x-.28,x+.28,D.GATE_Y-.695,D.GATE_Y-.47,PLATE_TOP,G)
    _slab(bm, -PX, PX, PYN - EDGE_BAND, PYN, PLATE_TOP, EDGE_TOP)
    for sx in (-1, 1):
        xa, xb = (PX - EDGE_BAND, PX) if sx > 0 else (-PX, -(PX - EDGE_BAND))
        strip=(xa,xb,PYS+EDGE_BAND,PYN-EDGE_BAND)
        seats=[]
        for key in ("bianxiu","qinghua","zhuxianzhen","songhua"):
            h=D.HALLS[key]
            if sx*h["cx"]>0:
                rim=h["cx"]+sx*(h["hx"]+1)
                a,b=(xa,rim+.002) if sx>0 else (rim-.002,xb)
                seats.append((a,b,h["cy"]-h["hy"]-1-.002,h["cy"]+h["hy"]+1+.002))
        for a,b,c,d in _sub_many(strip,seats):
            _slab(bm,a,b,c,d,PLATE_TOP,EDGE_TOP)
        for a,b,c,d in seats:
            _slab(bm,a,b,c,d,PLATE_TOP,G+.008)
    C.bm_obj(bm, "site13_edge_band", "foundation", ("宫苑", "台基"),
             cn="汉白玉收边带 1.60m（顶 +12mm）", mat="stone_lite", uv=1.0)


# ============================================================ 3) 青石铺装
def _paving_x_cells():
    """X 向石板格：以御道洞边（±(DAO_HX+HOLE_GAP)）为原点，两侧各自排 1.8m 格。"""
    inner = DAO_HX + HOLE_GAP          # 3.22
    out = []
    for (lo, hi) in ((PAVE_X0, -inner), (inner, PAVE_X1)):
        cs = _cuts(lo, hi, PAVE_STEP, lo if lo > 0 else hi)
        out.extend((cs[i], cs[i + 1]) for i in range(len(cs) - 1))
    return out


def _paving(C):
    bm = mu.new_bm()
    holes = _paving_holes()
    xs = _paving_x_cells()
    ys = _cuts(PAVE_Y0, PAVE_Y1, PAVE_STEP, 0.0)
    n = 0
    for (xa, xb) in xs:
        for j in range(len(ys) - 1):
            cell = (xa, xb, ys[j], ys[j + 1])
            for (a, b, c, d) in _sub_many(cell, holes):
                a2, b2 = a + PAVE_HALF, b - PAVE_HALF
                c2, d2 = c + PAVE_HALF, d - PAVE_HALF
                if b2 - a2 < 0.05 or d2 - c2 < 0.05:
                    continue
                _slab(bm, a2, b2, c2, d2, PLATE_TOP, G)
                n += 1
    C.bm_obj(bm, "site13_paving", "foundation", ("宫苑", "广场"),
             cn=f"青石铺装 1.8m 分缝（缝 12mm/深 8mm，{n} 块）", mat="stone_dark", uv=1.0)
    print(f"[site13] 铺装石板 {n} 块（1.8m 格，缝 {PAVE_JOINT * 1000:.0f}mm，"
          f"深 {-PLATE_TOP * 1000:.0f}mm）")


# ============================================================ 4) 汉白玉御道
def _daolong(C):
    bm = mu.new_bm()
    _slab(bm, -DAO_HX, DAO_HX, DAO_Y_S0, DAO_Y_S1, PLATE_TOP, DAO_TOP)
    _slab(bm, -DAO_HX, DAO_HX, DAO_Y_N0, DAO_N_END, PLATE_TOP, DAO_TOP)
    C.bm_obj(bm, "site13_daolong", "foundation", ("宫苑", "广场"),
             cn="汉白玉御道 x±3.2（顶 +8mm，跨池断开）", mat="stone_lite", uv=1.0)
    print(f"[site13] 御道 x±{DAO_HX} y[{DAO_Y_S0:.2f},{DAO_Y_S1:.2f}] ∪ "
          f"[{DAO_Y_N0:.2f},{DAO_N_END:.2f}]（北端 {DAO_N_END:.2f}，离 hall 垂带 0.04）")


# ============================================================ 5) 水池（壁+压顶+底+水面）
def _pool_block(bm, axis, t0, t1, b0, b1, za, zb, inner_low, water):
    """在临水面整石留出 24 mm 宽压边线，上下各切一条 10 mm 深的斜槽。"""
    levels = [(water + dz, recess) for dz, recess in
              ((0.028, 0), (0.038, 0.010), (0.048, 0),
               (0.072, 0), (0.082, 0.010), (0.092, 0))]
    def recess_at(z):
        for (lo, r0), (hi, r1) in zip(levels, levels[1:]):
            if lo <= z <= hi:
                return r0 + (r1 - r0) * (z - lo) / (hi - lo)
        return 0.0
    section = [(za, recess_at(za)), *((z, r) for z, r in levels if za < z < zb), (zb, recess_at(zb))]
    rings = []
    for z, inset in section:
        a = b0 + inset if inner_low else b0
        b = b1 if inner_low else b1 - inset
        x0, x1, y0, y1 = (t0, t1, a, b) if axis == "x" else (a, b, t0, t1)
        rings.append([_v(bm, x, y, z) for x, y in ((x0,y0), (x1,y0), (x1,y1), (x0,y1))])
    for a, b in zip(rings, rings[1:]):
        mu.bridge_rings(bm, a, b)
    mu.cap_ring(bm, rings[0], flip=True)
    mu.cap_ring(bm, rings[-1])


def _pool(C, key, rect, z_bot, z_cop, z_water, coll, cn):
    x0, x1, y0, y1 = rect
    w = POOL_WALL
    # ---- 池壁：三皮错缝砌筑（每皮一块 1.5m、竖缝 8mm、逐皮错半块、角部整石、外皮逐皮退 3mm 成线）
    bm = mu.new_bm()
    nz = 3
    dz = (PLATE_TOP - z_bot) / nz
    nblk = 0
    for c in range(nz):
        za, zb = z_bot + c * dz, z_bot + (c + 1) * dz
        wc = w - 0.003 * c                      # 外皮逐皮内退 3mm，皮缝成线（不与上皮共面）
        # 四角整石（方形，宽 = 当皮壁厚）
        for (cx_, cy_, sx, sy) in ((x0, y0, -1, -1), (x1, y0, 1, -1),
                                   (x0, y1, -1, 1), (x1, y1, 1, 1)):
            _box(bm, cx_ + min(0.0, sx * wc), cx_ + max(0.0, sx * wc),
                 cy_ + min(0.0, sy * wc), cy_ + max(0.0, sy * wc), za, zb)
        # 四条直段（角石以外），逐皮错半块
        for (axis, a0, a1, b0, b1) in (("x", x0, x1, y0 - wc, y0), ("x", x0, x1, y1, y1 + wc),
                                       ("y", y0, y1, x0 - wc, x0), ("y", y0, y1, x1, x1 + wc)):
            ln = a1 - a0
            n = max(1, int(round(ln / 1.50)))
            pitch = ln / n
            cuts = [a0]
            t = a0 + (0.5 * pitch if (c % 2) else 0.0)
            while t < a1 - 0.05:
                if t > a0 + 0.05:
                    cuts.append(t)
                t += pitch
            cuts.append(a1)
            for i in range(len(cuts) - 1):
                t0, t1 = cuts[i] + 0.004, cuts[i + 1] - 0.004     # 竖缝 8mm
                if t1 - t0 < 0.10:
                    continue
                if key=="jinshui" and axis=="x" and za < -.050 < zb:
                    _pool_block(bm,axis,t0,t1,b0,b1,za,-.050,b0==y1,z_water)
                    pockets=[(x-.062,x+.062,y0-.040,y0) if b1==y0 else
                             (x-.062,x+.062,y1,y1+.040) for x in (-3.55,3.55)]
                    for aa,bb,cc,dd in _sub_many((t0,t1,b0,b1),pockets):
                        _box(bm,aa,bb,cc,dd,-.050,zb)
                else:
                    _pool_block(bm, axis, t0, t1, b0, b1, za, zb, b0 in (y1, x1), z_water)
                nblk += 1
    C.bm_obj(bm, f"site13_pool_{key}", "water", coll,
             cn=f"{cn} 池壁 0.45m 三皮错缝（{nblk} 块，缝 8mm，顶 -8mm 坐压顶）",
             mat="stone_lite", uv=1.0)

    # ---- 压顶：0.9m 分块、缝 8mm、四角整石，相邻两边错半块
    bm = mu.new_bm()
    xo0, xo1 = x0 - COP_OUT, x1 + COP_OUT
    yo0, yo1 = y0 - COP_OUT, y1 + COP_OUT
    cw = D.POOL_COPING_W
    for (ca, cb, cc, cd) in ((xo0, xo0 + cw, yo0, yo0 + cw), (xo1 - cw, xo1, yo0, yo0 + cw),
                             (xo0, xo0 + cw, yo1 - cw, yo1), (xo1 - cw, xo1, yo1 - cw, yo1)):
        _box(bm, ca, cb, cc, cd, PLATE_TOP, z_cop)
    runs = (("x", xo0 + cw, xo1 - cw, yo0, yo1 - cw, 0.5, yo0, yo0 + cw),
            ("x", xo0 + cw, xo1 - cw, yo0 + cw, yo1, 0.5, yo1 - cw, yo1),
            ("y", yo0 + cw, yo1 - cw, xo0, xo1 - cw, 0.0, xo0, xo0 + cw),
            ("y", yo0 + cw, yo1 - cw, xo0 + cw, xo1, 0.0, xo1 - cw, xo1))
    nb = 0
    for (ax, a0, a1, b0, b1, off, c0, c1) in runs:
        ln = a1 - a0
        if ln <= 0.10:
            continue
        n = max(1, int(round(ln / 0.90)))
        pitch = ln / n
        edges = [a0]
        e = a0 + (0.5 * pitch if off else 0.0)
        while e < a1 - 0.10:
            if e > a0 + 0.10:
                edges.append(e)
            e += pitch
        edges.append(a1)
        for i in range(len(edges) - 1):
            t0, t1 = edges[i] + 0.004, edges[i + 1] - 0.004   # 缝 8mm（两侧各 4mm）
            if t1 - t0 < 0.05:
                continue
            if ax == "x":
                _box(bm, t0, t1, c0, c1, PLATE_TOP, z_cop)
            else:
                _box(bm, c0, c1, t0, t1, PLATE_TOP, z_cop)
            nb += 1
    C.bm_obj(bm, f"site13_coping_{key}", "water", coll,
             cn=f"{cn} 压顶 0.55m（{nb} 块，缝 8mm 错半块，四角整石）",
             mat="stone_lite", uv=1.0)

    # ---- 四内角抱角石：四分之一圆角石，从池底砌到压顶下，凸入水面 0.18
    bm = mu.new_bm()
    for (cx_, cy_, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1),
                               (x0, y1, 1, -1), (x1, y1, -1, -1)):
        r = 0.18
        poly = [(cx_, cy_)]
        for k in range(7):
            a = 0.5 * math.pi * (k / 6.0)
            poly.append((cx_ + sx * r * math.cos(a), cy_ + sy * r * math.sin(a)))
        _prism_z(bm, poly, z_bot, PLATE_TOP)
    C.bm_obj(bm, f"site13_corner_{key}", "water", coll,
             cn=f"{cn} 四内角抱角石（R180）", mat="stone_lite", uv=1.0)

    bm = mu.new_bm()
    _box(bm, x0 - w, x1 + w, y0 - w, y1 + w, min(PLATE_BOT, z_bot - 0.10), z_bot)
    C.bm_obj(bm, f"site13_pond_{key}", "water", coll,
             cn=f"{cn} 池底暖青灰石板", mat="pond", uv=1.0)

    bm = mu.new_bm()
    # 水边跟随四个抱角石的实际六段折面，沿每个侧面退 1 mm。
    from mathutils import Vector
    shore=[]
    for cx,cy,sx,sy in ((x0,y0,1,1),(x1,y0,-1,1),(x1,y1,-1,-1),(x0,y1,1,-1)):
        arc=[]
        radius=.180+.001/math.cos(math.pi/24)
        for i in range(7):
            theta=i*math.pi/12
            arc.append(Vector((radius*math.cos(theta),radius*math.sin(theta))))
        arc[0]=arc[0].lerp(arc[1],WATER_INSET/arc[1].y)
        arc[-1]=arc[-1].lerp(arc[-2],WATER_INSET/arc[-2].x)
        if sx*sy>0: arc.reverse()
        shore.extend(_v(bm,cx+sx*v.x,cy+sy*v.y,z_water) for v in arc)
    mu.face(bm,shore)
    C.bm_obj(bm, f"site13_water_{key}", "water", coll,
             cn=f"{cn} 水面（供 Reflector）", mat="water", uv=1.0)


def _jinshui(C):
    _pool(C, "jinshui", POOL_OPEN, D.POOL_BOTTOM_Z, D.POOL_COPING_Z, D.WATER_Z,
          ("金水院", "水池"), "金水院")
    print(f"[site13] 金水院水池 x±{D.POOL_X1} y[{D.POOL_Y0},{D.POOL_Y1}] "
          f"水面 {D.WATER_Z} 池底 {D.POOL_BOTTOM_Z} 压顶顶 {D.POOL_COPING_Z} "
          f"壁厚 {D.POOL_WALL_T} 压顶宽 {D.POOL_COPING_W}")


def _houyuan(C):
    _pool(C, "houyuan", RG_OPEN, D.RG_BOTTOM_Z, D.RG_COPING_Z, D.RG_WATER_Z,
          ("后苑", "方池"), "后苑方池")
    print(f"[site13] 后苑方池 x±{D.RG_POOL_X1} y[{D.RG_POOL_Y0},{D.RG_POOL_Y1}] "
          f"水面 {D.RG_WATER_Z} 池底 {D.RG_BOTTOM_Z} 压顶顶 {D.RG_COPING_Z}")


# ============================================================ 6) 汉白玉石桥
def _deck_z(y):
    """桥面标高：两端 BR_DECK，中部 +BR_ARCH 缓和拱（sin² 曲线，两端切线水平）。"""
    t = (y - D.BRIDGE_Y_S) / float(D.BRIDGE_Y_N - D.BRIDGE_Y_S)
    t = min(max(t, 0.0), 1.0)
    return BR_DECK + BR_ARCH * math.sin(math.pi * t) ** 2


def _arching(bm, x0, x1, y0, y1, zb, zt, n=8):
    """随桥拱起伏的板：zt(y)/zb(y) 为顶/底标高函数，x0/x1 两侧立面 + 两端封口。"""
    yy = [y0 + (y1 - y0) * i / float(n) for i in range(n + 1)]
    for i in range(n):
        ya, yb = yy[i], yy[i + 1]
        at, bt = zt(ya), zt(yb)
        ab, bb = zb(ya), zb(yb)
        _quad(bm, _v(bm, x0, ya, at), _v(bm, x1, ya, at),
              _v(bm, x1, yb, bt), _v(bm, x0, yb, bt))            # 顶 +Z
        _quad(bm, _v(bm, x0, ya, ab), _v(bm, x0, yb, bb),
              _v(bm, x1, yb, bb), _v(bm, x1, ya, ab))            # 底 -Z
        _quad(bm, _v(bm, x0, ya, ab), _v(bm, x0, ya, at),
              _v(bm, x0, yb, bt), _v(bm, x0, yb, bb))            # x0 侧 -X
        _quad(bm, _v(bm, x1, ya, ab), _v(bm, x1, yb, bb),
              _v(bm, x1, yb, bt), _v(bm, x1, ya, at))            # x1 侧 +X
    at, ab = zt(y0), zb(y0)
    bt, bb = zt(y1), zb(y1)
    _quad(bm, _v(bm, x0, y0, ab), _v(bm, x1, y0, ab),
          _v(bm, x1, y0, at), _v(bm, x0, y0, at))                # 南端 -Y
    _quad(bm, _v(bm, x0, y1, bb), _v(bm, x0, y1, bt),
          _v(bm, x1, y1, bt), _v(bm, x1, y1, bb))                # 北端 +Y


def _build_bridge_post(bm, slope):
    """八角莲苞覆叶望柱：八棱柱身（上下 3mm 倒棱）→ 柱帽 → 覆叶 → 莲苞。"""
    prof = [(0.1625, 0.000), (0.1625, 0.700),           # 柱身 0.30 对边（八棱）
            (0.1900, 0.700), (0.1900, 0.756),           # 柱帽 0.38 对边
            (0.1680, 0.762), (0.1500, 0.772),           # 覆叶外翻
            (0.1500, 0.800), (0.1200, 0.845),           # 莲苞
            (0.0800, 0.890), (0.0400, 0.925), (0.0180, 0.930)]
    k = 0.950 / 0.930                                # 柱顶 = 桥面 + 0.95（中部 1.30）
    prof = [(r, z * k) for (r, z) in prof]
    rings = mu.revolve(bm, prof, (0, 0, 0), segments=8, close_profile=False)
    # revolve 按方位返回子午线。封盖应横跨八个方位。
    mu.cap_ring(bm, [meridian[0] for meridian in rings], flip=True)
    mu.cap_ring(bm, [meridian[-1] for meridian in rings])
    mu.recalc_normals(bm)
    shaft = {meridian[j] for meridian in rings for j in (0, 1)}
    edges = [edge for edge in bm.edges if all(v in shaft for v in edge.verts)]
    bmesh.ops.bevel(bm, geom=edges, offset=0.003, segments=2, affect='EDGES', clamp_overlap=True)
    # 柱身竖直。柱脚底面及其倒棱按所在桥跨的纵坡切削。
    for vert in bm.verts:
        if vert.co.z < 0.010:
            vert.co.z += slope * vert.co.y


def _prism_y(bm, poly_xz, y0, y1, cap0=True, cap1=True):
    """沿 Y 挤出的棱柱：poly_xz = [(x,z), ...]（自动统一为逆时针，侧壁朝外）。"""
    area = 0.5 * sum(poly_xz[i][0] * poly_xz[(i + 1) % len(poly_xz)][1]
                     - poly_xz[(i + 1) % len(poly_xz)][0] * poly_xz[i][1]
                     for i in range(len(poly_xz)))
    if area < 0.0:
        poly_xz = list(reversed(poly_xz))
    n = len(poly_xz)
    a = [_v(bm, x, y0, z) for (x, z) in poly_xz]
    b = [_v(bm, x, y1, z) for (x, z) in poly_xz]
    for i in range(n):
        k = (i + 1) % n
        _quad(bm, a[i], b[i], b[k], a[k])              # 侧壁朝外
    if cap1:
        mu.face(bm, tuple(b))
    if cap0:
        mu.face(bm, tuple(reversed(a)))


def _build_boli(bm):
    """卷云抱鼓石：基座 + 鼓身（12 边圆盘，轴向 Y）+ 两面卷云浮雕。"""
    _box(bm, -0.150, 0.150, -0.100, 0.100, 0.000, 0.100)   # 基座，坐池压顶
    rs, cz = 0.145, 0.120
    disc = [(rs * math.cos(math.radians(15 + 30 * i)),
             cz + rs * math.sin(math.radians(15 + 30 * i))) for i in range(12)]
    seated=[]
    for p,q in zip(disc,disc[1:]+disc[:1]):
        if p[1]>=.10: seated.append(p)
        if (p[1]<.10)!=(q[1]<.10):
            seated.append((p[0]+(q[0]-p[0])*(.10-p[1])/(q[1]-p[1]),.10))
    _prism_y(bm, seated, -0.075, 0.075)
    for (ya, yb, c0, c1) in ((0.060, 0.090, False, True),
                             (-0.090, -0.060, True, False)):
        _prism_y(bm, _scroll_uz(0.0, cz, 0.085, +1, HM_EXAMPLES),
                 ya, yb, cap0=c0, cap1=c1)                 # 卷云，内端埋入鼓身
    mu.recalc_normals(bm)


def _bridge(C):
    bx = D.BRIDGE_W * 0.5
    ys, yn = D.BRIDGE_Y_S, D.BRIDGE_Y_N
    e = 0.005                                # 桥板端头离池壁内立面 5mm（反共面）
    coll = ("金水院", "石桥")
    zb = lambda y: _deck_z(y) - BR_T         # noqa: E731

    bm = mu.new_bm()
    _arching(bm, -bx, -BR_GAP * 0.5, ys + e, yn - e, zb, _deck_z, BR_SEG)
    _arching(bm, BR_GAP * 0.5, bx, ys + e, yn - e, zb, _deck_z, BR_SEG)
    C.bm_obj(bm, "site13_bridge_deck", "water", coll,
             cn="汉白玉桥板（两片，中缝 60mm，厚 0.26，中部起拱 0.25）",
             mat="stone_lite", uv=1.0)

    # ---- 中缝压条：60mm 缝在渲染里会漏出下面的水，读成一道蓝裂缝。
    # 用一条顶面下沉 12mm 的青石压条把缝封住，既是真实石作做法，又留出阴影线。
    bm = mu.new_bm()
    _arching(bm, -BR_GAP * 0.5, BR_GAP * 0.5, ys + e, yn - e,
             lambda y: _deck_z(y) - 0.10, lambda y: _deck_z(y) - 0.012, BR_SEG)
    C.bm_obj(bm, "site13_bridge_seam", "detail", coll,
             cn="桥面中缝压条（凹 12mm）", mat="stone_dark", uv=1.0)

    # ---- 9 对八角莲苞覆叶望柱（实例化，柱脚随拱）
    n = D.BRIDGE_POST_N
    y_a, y_b = ys + 0.30, yn - 0.30
    pitch = (y_b - y_a) / (n - 1)
    ys_posts = [y_a + i * pitch for i in range(n)]
    for i, y in enumerate(ys_posts):
        step = (yn - ys - 2 * e) / BR_SEG
        seg = int((y - ys - e) / step)
        y0 = ys + e + step * seg
        slope = (_deck_z(y0 + step) - _deck_z(y0)) / step
        z = _deck_z(y0) + (y - y0) * slope + 0.002
        proto = C.proto(f"site13_bridge_post_{i}", lambda bm: _build_bridge_post(bm, slope),
                        mat="stone_lite", smooth=32.0, uv=1.0)
        for sx in (-1, 1):
            C.place_at(proto, (sx * BR_X, y, z),
                       name=f"site13_brpost_{i}{'e' if sx > 0 else 'w'}",
                       cat="detail", coll_path=coll,
                       cn="桥望柱 八角 0.30 高 0.95（随拱）")

    # ---- 栏板 + 寻杖（随拱，柱间分段，两头离柱面 20mm）
    bm = mu.new_bm()
    for i in range(n - 1):
        y0 = ys_posts[i] + 0.190 + CLEAR
        y1 = ys_posts[i + 1] - 0.190 - CLEAR
        if y1 - y0 < 0.05:
            continue
        for sx in (-1, 1):
            xc = sx * BR_X
            _arching(bm, xc - 0.05, xc + 0.05, y0, y1,
                     lambda y: _deck_z(y) + 0.020, lambda y: _deck_z(y) + 0.760, 4)
            _arching(bm, xc - 0.07, xc + 0.07, y0, y1,
                     lambda y: _deck_z(y) + 0.755, lambda y: _deck_z(y) + 0.880, 4)
    C.bm_obj(bm, "site13_bridge_panel", "detail", coll,
             cn="桥栏板 0.10 厚（底离桥面 20mm）+ 寻杖（随拱）", mat="stone_lite", uv=1.0)

    # ---- 4 卷云抱鼓石：桥两端、池压顶上，抱住栏杆端头
    proto_b = C.proto("site13_boli", _build_boli, mat="stone_lite", smooth=30.0, uv=1.0)
    for (yy, tag) in ((ys - 0.30, "s"), (yn + 0.30, "n")):
        for sx in (-1, 1):
            C.place_at(proto_b, (sx * BR_X, yy, D.POOL_COPING_Z),
                       name=f"site13_boli_{tag}{'e' if sx > 0 else 'w'}",
                       cat="detail", coll_path=coll, cn="卷云抱鼓石 0.30×0.20×0.33")
    print(f"[site13] 石桥 宽 {D.BRIDGE_W} 跨 y[{ys},{yn}] 桥面 {BR_DECK}→"
          f"{BR_DECK + BR_ARCH:.2f}（中部起拱 {BR_ARCH}）望柱 {n} 对（八角 {BR_X}）"
          f"柱顶 {BR_DECK + BR_ARCH + 0.95:.2f} 抱鼓石 4 尊")


# ============================================================ 7) 栏杆
def _rail_runs():
    """[(axis, fixed, a0, a1, n_bay)]；axis='x' 沿 X 走（南/北），'y' 沿 Y 走（东/西）。"""
    ex, ey = RAIL_X, RAIL_Y
    runs = [
        ("x", +ey, -ex, +ex),                          # 北
        ("x", -ey, -ex, -D.GATE_HX),                   # 南（西段，牌楼开口断开）
        ("x", -ey, +D.GATE_HX, +ex),                   # 南（东段）
        ("y", -ex, -ey, +ey),                          # 西
        ("y", +ex, -ey, +ey),                          # 东
    ]
    out = []
    for axis, fixed, a0, a1 in runs:
        lo, hi = min(a0, a1), max(a0, a1)
        n = max(1, int(round((hi - lo) / D.RAIL_POST_STEP)))
        out.append((axis, fixed, lo, hi, n))
    return out


def _build_rail_post(bm):
    s = D.RAIL_POST_W * 0.5           # 0.08
    c = RAIL_CAP_H                    # 0.11
    z0, z1 = RAIL_CAP0, RAIL_CAP1
    _walls(bm, (-s, s, -s, s), 0.0, z0)
    _hring(bm, (-c, c, -c, c), (-s, s, -s, s), z0, up=False)
    _walls(bm, (-c, c, -c, c), z0, z1)
    _quad(bm, _v(bm, -c, -c, z1), _v(bm, c, -c, z1), _v(bm, c, c, z1), _v(bm, -c, c, z1))
    zt = D.RAIL_H                      # 0.95 局部顶
    hh = zt - z1
    rings = mu.revolve(bm, [(0.100, z1), (0.098, z1 + hh * 0.22), (0.070, z1 + hh * 0.52),
                            (0.040, z1 + hh * 0.78), (0.024, zt)],
                       (0, 0, 0), segments=10, close_profile=False)
    mu.cap_ring(bm, rings[-1])


def _build_baluster(bm):
    prof = [(0.056, 0.0), (0.050, BAL_H * 0.12), (0.070, BAL_H * 0.38),
            (0.064, BAL_H * 0.63), (0.034, BAL_H * 0.86), (0.024, BAL_H)]
    mu.revolve(bm, prof, (0, 0, 0), segments=6, close_profile=False)


def _rail(C):
    coll = ("宫苑", "栏杆")
    proto_p = C.proto("site13_rail_post", _build_rail_post, mat="stone_lite",
                      smooth=40.0, uv=1.0)
    proto_b = C.proto("site13_rail_baluster", _build_baluster, mat="stone_lite",
                      smooth=80.0, uv=1.0)

    posts = {}
    bm = mu.new_bm()
    n_bal = 0
    for (axis, fixed, lo, hi, n) in _rail_runs():
        pitch = (hi - lo) / n
        coords = [lo + i * pitch for i in range(n + 1)]
        for a in coords:
            key = (round(a if axis == "x" else fixed, 3),
                   round(fixed if axis == "x" else a, 3))
            posts.setdefault(key, None)
        for i in range(n):
            a0, a1 = coords[i] + BAR_END, coords[i + 1] - BAR_END
            if a1 - a0 < 0.05:
                continue
            if axis == "x":
                _slab(bm, a0, a1, fixed - BAR_W * 0.5, fixed + BAR_W * 0.5, RAIL_Z0, BAR_DL)
                _box(bm, a0, a1, fixed - BAR_W * 0.5, fixed + BAR_W * 0.5, BAR_XZ0, BAR_XZ1)
            else:
                _slab(bm, fixed - BAR_W * 0.5, fixed + BAR_W * 0.5, a0, a1, RAIL_Z0, BAR_DL)
                _box(bm, fixed - BAR_W * 0.5, fixed + BAR_W * 0.5, a0, a1, BAR_XZ0, BAR_XZ1)
        for i in range(n):
            for t in (0.25, 0.50, 0.75):
                a = coords[i] + pitch * t
                loc = (a, fixed, BAR_DL) if axis == "x" else (fixed, a, BAR_DL)
                C.place_at(proto_b, loc, name=f"site13_bal_{n_bal:04d}",
                           cat="detail", coll_path=coll, cn="汉白玉宝瓶")
                n_bal += 1

    for idx, (px, py) in enumerate(sorted(posts)):
        C.place_at(proto_p, (px, py, RAIL_Z0), name=f"site13_railpost_{idx:04d}",
                   cat="detail", coll_path=coll, cn="汉白玉望柱 0.16 方 高 0.95")
    C.bm_obj(bm, "site13_rail_bar", "detail", coll,
             cn="栏杆地栿 + 寻杖", mat="stone_lite", uv=1.0)
    print(f"[site13] 栏杆 望柱 {len(posts)} 根 / 宝瓶 {n_bal} 个 / "
          f"中线 x±{RAIL_X} y±{RAIL_Y}（南侧 x±{D.GATE_HX} 断开）")


# ============================================================ 入口
def build(C):
    _plate(C)
    _lotus(C)
    _humen(C)
    _xumizuo_relief(C)
    _chishou(C)
    _edge_band(C)
    _paving(C)
    _daolong(C)
    _jinshui(C)
    _bridge(C)
    _houyuan(C)
    _rail(C)
    print(f"[site13] 台基 {2 * PX:.0f}×{PYN - PYS:.0f}m 设计面 z={G:+.3f}（铺装完成面）"
          f" 结构面 {PLATE_TOP:+.3f} 底 {PLATE_BOT:+.3f}｜"
          f"收边 {EDGE_BAND:.2f}m 顶 {EDGE_TOP:+.3f}｜御道顶 {DAO_TOP:+.3f}｜"
          f"压顶顶 {D.POOL_COPING_Z:+.3f}")


