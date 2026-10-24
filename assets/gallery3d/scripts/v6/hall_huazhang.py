"""华章新馆 · 重檐歇山装配与导出

    blender.exe -b --factory-startup -P assets/gallery3d/scripts/v6/hall_huazhang.py -- --quick --only 01_front34

装配顺序即真实施工顺序：
    须弥座 -> 一层柱网 -> 额枋/雀替 -> 斗拱 -> 下檐 -> 二层楼板/楼梯
    -> 二层柱网 -> 斗拱 -> 上檐歇山 -> 山花/博风/悬鱼 -> 墙身门窗
    -> 室内陈设 -> 展墙/画框/相机 -> 导出 GLB + layout + 渲染
"""

from __future__ import annotations

import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import hz_kit as K  # noqa: E402
import hall_dressing as D  # noqa: E402

BLEND_OUT = os.path.join(K.G3D, "blender", "wenmai_huazhang.blend")
GLB_OUT = os.path.join(K.G3D, "exports", "wenmai_gallery_huazhang.glb")
LAYOUT_OUT = os.path.join(K.G3D, "exports", "huazhang_layout.json")
RENDER_OUT = os.path.join(K.G3D, "renders", "huazhang")
FRONT_GLB = os.path.join(K.PROJECT, "frontend", "public", "models", "wenmai_gallery_huazhang.glb")
FRONT_LAYOUT = os.path.join(
    K.PROJECT, "frontend", "src", "features", "heritage-gallery", "buildings", "layouts", "huazhang_layout.json"
)

# ---------------------------------------------------------------- 关键标高

BASE_TOP = 1.20
FY1 = BASE_TOP
COL_H1 = 5.40
Y_EF1 = FY1 + COL_H1 - 0.50
Y_DG1 = FY1 + COL_H1
Y_EAVE_LOW = FY1 + COL_H1 + 1.30
Y_EAVE_LOW_IN = Y_EAVE_LOW + 1.35
FY2 = FY1 + COL_H1 + 0.55
COL_H2 = 3.40
Y_DG2 = FY2 + COL_H2
Y_EAVE_UP = Y_DG2 + 1.15
Y_RIDGE = Y_EAVE_UP + 4.60

HALF_X1 = 6.00
HALF_Z1 = 5.10
HALF_X2 = 6.00
HALF_Z2 = 5.10
WALL_T = 0.36

UP_HALF_X = 7.25
UP_HALF_Z = 6.35
GABLE_X = 4.15

LOW_OUT_X = 7.55
LOW_OUT_Z = 6.60

COLUMNS_X = (-6.0, -2.40, 2.40, 6.0)
COLUMNS_Z = (-5.10, 5.10)

# ---------------------------------------------------------------- 展墙 / 画框

WALLS = [
    ("f1-back", 1, (0.0, FY1 + 2.30, HALF_Z1 - WALL_T / 2), math.pi, (5.20, 4.40), "一层 · 后墙"),
    ("f1-left-rear", 1, (-(HALF_X1 - WALL_T / 2), FY1 + 2.30, 2.60), math.pi / 2, (4.20, 4.40), "一层 · 左墙后段"),
    ("f1-left-mid", 1, (-(HALF_X1 - WALL_T / 2), FY1 + 2.30, -1.40), math.pi / 2, (3.60, 4.40), "一层 · 左墙中段"),
    ("f1-right-rear", 1, ((HALF_X1 - WALL_T / 2), FY1 + 2.30, 2.60), -math.pi / 2, (4.20, 4.40), "一层 · 右墙后段"),
    ("f1-right-mid", 1, ((HALF_X1 - WALL_T / 2), FY1 + 2.30, -1.40), -math.pi / 2, (3.60, 4.40), "一层 · 右墙中段"),
    ("f1-pier-left", 1, (-2.30, FY1 + 1.65, -0.90), math.pi / 2, (1.90, 3.10), "一层 · 独立展墙 左"),
    ("f1-pier-right", 1, (2.30, FY1 + 1.65, -0.90), -math.pi / 2, (1.90, 3.10), "一层 · 独立展墙 右"),
    ("f2-back", 2, (0.0, FY2 + 1.70, HALF_Z2 - WALL_T / 2), math.pi, (5.20, 3.30), "二层 · 后墙"),
    ("f2-left", 2, (-(HALF_X2 - WALL_T / 2), FY2 + 1.70, 0.60), math.pi / 2, (7.00, 3.30), "二层 · 左墙"),
    ("f2-right", 2, ((HALF_X2 - WALL_T / 2), FY2 + 1.70, 0.60), -math.pi / 2, (7.00, 3.30), "二层 · 右墙"),
    ("f2-front", 2, (0.0, FY2 + 1.70, -(HALF_Z2 - WALL_T / 2)), 0.0, (5.20, 3.30), "二层 · 前墙"),
]

FRAME_PLAN = {
    "f1-back": [(1.35, 1.10, 0.26, 0.50, "一层 · 后墙 · 左"), (1.35, 1.10, 0.74, 0.50, "一层 · 后墙 · 右")],
    "f1-left-rear": [(1.00, 1.25, 0.30, 0.50, "一层 · 左墙后段 · 前"), (1.20, 1.20, 0.74, 0.50, "一层 · 左墙后段 · 后")],
    "f1-left-mid": [(1.55, 0.95, 0.27, 0.52, "一层 · 左墙中段 · 横幅"), (0.95, 1.20, 0.76, 0.52, "一层 · 左墙中段 · 立轴")],
    "f1-right-rear": [(1.20, 1.20, 0.26, 0.50, "一层 · 右墙后段 · 后"), (1.00, 1.25, 0.70, 0.50, "一层 · 右墙后段 · 前")],
    "f1-right-mid": [(0.95, 1.20, 0.24, 0.52, "一层 · 右墙中段 · 立轴"), (1.55, 0.95, 0.73, 0.52, "一层 · 右墙中段 · 横幅")],
    "f1-pier-left": [(1.30, 1.60, 0.50, 0.54, "一层 · 独立展墙 · 左")],
    "f1-pier-right": [(1.30, 1.60, 0.50, 0.54, "一层 · 独立展墙 · 右")],
    "f2-back": [(0.90, 1.15, 0.20, 0.52, "二层 · 后墙 · 左"), (1.40, 1.00, 0.50, 0.52, "二层 · 后墙 · 中"), (0.90, 1.15, 0.80, 0.52, "二层 · 后墙 · 右")],
    "f2-left": [(1.05, 1.25, 0.20, 0.52, "二层 · 左墙 · 后"), (1.50, 1.00, 0.50, 0.52, "二层 · 左墙 · 中"), (1.05, 1.25, 0.80, 0.52, "二层 · 左墙 · 前")],
    "f2-right": [(1.05, 1.25, 0.20, 0.52, "二层 · 右墙 · 后"), (1.50, 1.00, 0.50, 0.52, "二层 · 右墙 · 中"), (1.05, 1.25, 0.80, 0.52, "二层 · 右墙 · 前")],
    "f2-front": [(0.95, 1.20, 0.20, 0.52, "二层 · 前墙 · 左"), (1.35, 1.05, 0.50, 0.52, "二层 · 前墙 · 中"), (0.95, 1.20, 0.80, 0.52, "二层 · 前墙 · 右")],
}


# 室内软装模块独立迭代：把它的展墙/画框拓位接进来（33 个画框位）
WALLS[:] = D.WALLS2
FRAME_PLAN.clear()
FRAME_PLAN.update(D.FRAME_PLAN2)


def wall_point(wall, u, v, offset=0.06):
    cx, cy, cz = wall[2]
    rot = wall[3]
    width, height = wall[4]
    local_x = (u - 0.5) * width
    local_y = (v - 0.5) * height
    cos_r, sin_r = math.cos(rot), math.sin(rot)
    return (
        cx + local_x * cos_r + sin_r * offset,
        cy + local_y,
        cz - local_x * sin_r + cos_r * offset,
    )


# ---------------------------------------------------------------- 台基


def build_base(col):
    K.log("台基：须弥座 + 踏跺 + 栏板望柱")
    K.sumeru_base(col)


# ---------------------------------------------------------------- 下檐


def ring_slope(name, ix, iz, ox, oz, y_in, y_out, material, col, ntheta=96, nt=4, thickness=0.18):
    def rect_point(su, sv, rx, rz):
        tx = rx / abs(su) if abs(su) > 1e-9 else 1e12
        tz = rz / abs(sv) if abs(sv) > 1e-9 else 1e12
        t = min(tx, tz)
        return su * t, sv * t

    verts = []
    for j in range(ntheta):
        a = (j / ntheta) * math.tau
        c, s = math.cos(a), math.sin(a)
        m = max(abs(c), abs(s))
        su, sv = c / m, s / m
        pin = rect_point(su, sv, ix, iz)
        pout = rect_point(su, sv, ox, oz)
        for i in range(nt + 1):
            t = i / nt
            x = pin[0] + (pout[0] - pin[0]) * t
            z = pin[1] + (pout[1] - pin[1]) * t
            y = y_in + (y_out - y_in) * t
            y += 0.30 * ((abs(x) / ox) * (abs(z) / oz)) ** 2.6 * t
            verts.append((x, y, z))
    faces = []
    row = nt + 1
    for j in range(ntheta):
        nj = (j + 1) % ntheta
        for i in range(nt):
            a0 = j * row + i
            b0 = nj * row + i
            faces.append((a0, b0, b0 + 1, a0 + 1))
    obj = K._mesh(name, verts, faces, material, col, smooth=True)
    solid = obj.modifiers.new("Solid", "SOLIDIFY")
    solid.thickness = thickness
    solid.offset = -1.0
    solid.use_even_offset = True
    return obj


def build_lower_eave(col):
    K.log("下檐：腰檐环面 + 瓦垄 + 滴水")
    ring_slope("ROOF_Lower", HALF_X2 + 0.02, HALF_Z2 + 0.02, LOW_OUT_X, LOW_OUT_Z,
               Y_EAVE_LOW_IN, Y_EAVE_LOW, "M_tile", col)
    ribs = []
    count = 96
    for j in range(count):
        a = (j / count) * math.tau
        c, s = math.cos(a), math.sin(a)
        m = max(abs(c), abs(s))
        su, sv = c / m, s / m
        ix, iz = HALF_X2 + 0.02, HALF_Z2 + 0.02
        ox, oz = LOW_OUT_X, LOW_OUT_Z
        r_i = min(ix / abs(su) if abs(su) > 1e-9 else 1e12, iz / abs(sv) if abs(sv) > 1e-9 else 1e12)
        r_o = min(ox / abs(su) if abs(su) > 1e-9 else 1e12, oz / abs(sv) if abs(sv) > 1e-9 else 1e12)
        pts = []
        for i in range(5):
            t = i / 4
            r = r_i + (r_o - r_i) * t
            x, z = su * r, sv * r
            y = Y_EAVE_LOW_IN + (Y_EAVE_LOW - Y_EAVE_LOW_IN) * t
            y += 0.30 * ((abs(x) / ox) * (abs(z) / oz)) ** 2.6 * t + 0.055
            pts.append((x, y, z))
        ribs.append(K.ribbon("TILE_Low%03d" % j, pts, 0.20, "M_tile_dark", col))
    K.merge(ribs, "TILE_LowerRows", col)
    dis = []
    for j in range(count):
        a = (j / count) * math.tau
        c, s = math.cos(a), math.sin(a)
        m = max(abs(c), abs(s))
        su, sv = c / m, s / m
        ox, oz = LOW_OUT_X, LOW_OUT_Z
        r = min(ox / abs(su) if abs(su) > 1e-9 else 1e12, oz / abs(sv) if abs(sv) > 1e-9 else 1e12)
        x, z = su * r, sv * r
        y = Y_EAVE_LOW + 0.30 * ((abs(x) / ox) * (abs(z) / oz)) ** 2.6 - 0.02
        dis.append(K.box("DISHUI_Low%03d" % j, (x, y, z), (0.14, 0.16, 0.10), "M_tile_edge", col,
                         rot=(0.0, 0.0, math.atan2(su, sv))))
    K.merge(dis, "TILE_LowerDishui", col)
    return col


# ---------------------------------------------------------------- 上檐（歇山）


def build_upper_roof(col):
    K.log("上檐：歇山屋面 + 瓦垄 + 正脊 + 垂脊 + 山花")
    K.roof_slab("ROOF_Upper", UP_HALF_X, UP_HALF_Z, Y_EAVE_UP, Y_RIDGE, GABLE_X, "M_tile", col,
                nx=72, nz=52, thickness=0.22)
    tiles = K.tile_field("TILE_Up", UP_HALF_X, UP_HALF_Z, Y_EAVE_UP, Y_RIDGE, GABLE_X, col,
                         spacing=0.34, tile_w=0.20, lift=0.06)
    K.merge(tiles, "TILE_UpperRows", col)
    wadang = K.eave_edge("EAVE_Up", UP_HALF_X, UP_HALF_Z, Y_EAVE_UP, Y_RIDGE, GABLE_X, col,
                         tile_w=0.20, spacing=0.34)
    K.merge(wadang, "TILE_EaveEdge", col)

    ridge_len = GABLE_X * 2
    K.main_ridge("ROOF_MainRidge", ridge_len + 0.6, Y_RIDGE, col, height=0.50)
    for side in (-1, 1):
        K.chiwen("ROOF_ChiWen%d" % side, side * (ridge_len / 2 + 0.20), Y_RIDGE + 0.10, 0.0, col, flip=side)
        for zsign in (-1, 1):
            K.hip_ridge(
                "ROOF_HipRidge%d_%d" % (side, zsign),
                side * ridge_len / 2, 0.0,
                side * UP_HALF_X, zsign * UP_HALF_Z,
                Y_RIDGE, Y_EAVE_UP,
                col, UP_HALF_X, UP_HALF_Z, Y_EAVE_UP, Y_RIDGE, GABLE_X,
                width=0.30, steps=18,
            )
    K.gable_face("ROOF_Gable", GABLE_X, UP_HALF_Z, Y_EAVE_UP, Y_RIDGE, col)
    # 不再放「山面小披檐」：那是一块竖直板，会从屋面上穿出来
    return col


# ---------------------------------------------------------------- 主体


def build_frame(col):
    K.log("一层：柱网 / 额枋 / 雀替 / 斗拱")
    for x in COLUMNS_X:
        for z in COLUMNS_Z:
            K.column("COLUMN_Eave_%d_%d" % (int(x * 10), int(z * 10)), x, z, FY1, COL_H1, col)
    for x in (-HALF_X1, HALF_X1):
        K.column("COLUMN_Side_%d" % int(x * 10), x, 0.0, FY1, COL_H1, col)
    for x in (-2.40, 2.40):
        for z in (-2.55, 2.55):
            K.column("COLUMN_Gold_%d_%d" % (int(x * 10), int(z * 10)), x, z, FY1, COL_H1, col,
                     diameter=0.50)

    for z in COLUMNS_Z:
        for i in range(len(COLUMNS_X) - 1):
            K.lintel_set("EF_F%d_%d" % (int(z), i), COLUMNS_X[i], COLUMNS_X[i + 1], z, Y_EF1, 0.34, col)
        for x in COLUMNS_X:
            K.queti("QT_F%d_%d" % (int(z), int(x * 10)), x, z, Y_EF1 - 0.28, 0.0, col)
    for x in (-HALF_X1, HALF_X1):
        for i in range(len(COLUMNS_Z) - 1):
            K.lintel_set("EF_S%d_%d" % (int(x), i), COLUMNS_Z[i], COLUMNS_Z[i + 1], x, Y_EF1, 0.34, col)
        for z in COLUMNS_Z:
            K.queti("QT_S%d_%d" % (int(x), int(z * 10)), x, z, Y_EF1 - 0.28, math.pi / 2, col)

    parts = []
    for z, facing in ((COLUMNS_Z[1], 0.0), (COLUMNS_Z[0], math.pi)):
        n = 8
        for i in range(n + 1):
            x = -HALF_X1 + (2 * HALF_X1) * (i / n)
            parts += K.dougong("DG_F%d_%02d" % (int(z), i), x, Y_DG1, z, facing, col, 1.0)
    for x, facing in ((HALF_X1, -math.pi / 2), (-HALF_X1, math.pi / 2)):
        n = 6
        for i in range(n + 1):
            z = -HALF_Z1 + (2 * HALF_Z1) * (i / n)
            parts += K.dougong("DG_S%d_%02d" % (int(x), i), x, Y_DG1, z, facing, col, 1.0)
    K.merge(parts, "BRACKET_F1", col)
    return col


def build_upper_frame(col):
    K.log("二层：柱网 / 额枋 / 斗拱")
    for x in COLUMNS_X:
        for z in COLUMNS_Z:
            K.column("COLUMN_2E_%d_%d" % (int(x * 10), int(z * 10)), x, z, FY2, COL_H2, col,
                     diameter=K.ZHUJING * 0.88)
    for x in (-HALF_X2, HALF_X2):
        K.column("COLUMN_2S_%d" % int(x * 10), x, 0.0, FY2, COL_H2, col, diameter=K.ZHUJING * 0.88)

    y_ef = FY2 + COL_H2 - 0.42
    for z in COLUMNS_Z:
        for i in range(len(COLUMNS_X) - 1):
            K.lintel_set("EF2_F%d_%d" % (int(z), i), COLUMNS_X[i], COLUMNS_X[i + 1], z, y_ef, 0.30, col)
    for x in (-HALF_X2, HALF_X2):
        for i in range(len(COLUMNS_Z) - 1):
            K.lintel_set("EF2_S%d_%d" % (int(x), i), COLUMNS_Z[i], COLUMNS_Z[i + 1], x, y_ef, 0.30, col)

    parts = []
    for z, facing in ((COLUMNS_Z[1], 0.0), (COLUMNS_Z[0], math.pi)):
        n = 7
        for i in range(n + 1):
            x = -HALF_X2 + (2 * HALF_X2) * (i / n)
            parts += K.dougong("DG2_F%d_%02d" % (int(z), i), x, Y_DG2, z, facing, col, 0.9)
    for x, facing in ((HALF_X2, -math.pi / 2), (-HALF_X2, math.pi / 2)):
        n = 5
        for i in range(n + 1):
            z = -HALF_Z2 + (2 * HALF_Z2) * (i / n)
            parts += K.dougong("DG2_S%d_%02d" % (int(x), i), x, Y_DG2, z, facing, col, 0.9)
    K.merge(parts, "BRACKET_F2", col)
    return col


def build_walls(col):
    K.log("墙身 / 格扇门 / 槛窗 / 挂落")
    K.box("WALL_Back1", (0.0, (FY1 + COL_H1) / 2 + 0.4, HALF_Z1 - WALL_T / 2),
          (HALF_X1 * 2, COL_H1 - 0.4, WALL_T), "M_wall_plaster", col)
    for side in (-1, 1):
        K.box("WALL_Side1_%d" % side, (side * (HALF_X1 - WALL_T / 2), (FY1 + COL_H1) / 2 + 0.4, 1.70),
              (WALL_T, COL_H1 - 0.4, 6.70), "M_wall_plaster", col)
        K.box("WALL_Side1F_%d" % side, (side * (HALF_X1 - WALL_T / 2), FY1 + 0.9, -3.30),
              (WALL_T, 1.8, 3.40), "M_wall_plaster", col)

    zf = -(HALF_Z1 - WALL_T / 2)
    K.lattice_door("DOOR_Main", 0.0, zf, FY1 + 0.12, 4.40, 4.30, col, leaves=6)
    for side, hinge_x in ((-1, -0.733), (1, 0.733)):
        obj = K.box("DOOR_Leaf%s" % ("L" if side < 0 else "R"),
                    (hinge_x + (0.73 if side < 0 else -0.73), FY1 + 2.30, zf + 0.08),
                    (0.72, 4.10, 0.08), "M_wood_beam", col)
        hinge = bpy.data.objects.new("DOOR_Hinge%s" % ("L" if side < 0 else "R"), None)
        hinge.empty_display_type = "PLAIN_AXES"
        hinge.location = (hinge_x, -zf - 0.08, FY1 + 2.30)
        col.objects.link(hinge)
        obj.parent = hinge
        obj.matrix_parent_inverse = hinge.matrix_world.inverted()
        obj.location = (0.73 if side < 0 else -0.73, 0, 0)

    for side in (-1, 1):
        K.lattice_window("WINDOW_F1_%d" % side, side * 4.20, zf, FY1 + 0.10, 2.60, 2.60, col)
        # 次间墙芯：窗是贴面构件，后面必须有实墙，否则站在外面能直接看进大厅
        K.box("WALL_FrontBay%d" % side, (side * 4.10, (FY1 + COL_H1) / 2 + 0.30, zf + 0.26),
              (3.80, COL_H1 - 0.30, 0.14), "M_wall_plaster", col)
    for z in (HALF_Z1, -HALF_Z1):
        K.guaLuo("GUA_F%d" % int(z), 0.0, z, Y_EF1 - 0.72, 11.4, col)
    for x in (-HALF_X1, HALF_X1):
        K.guaLuo("GUA_S%d" % int(x), 0.0, x, Y_EF1 - 0.72, 9.4, col)

    y2 = FY2 + COL_H2
    K.box("WALL_Back2", (0.0, (FY2 + y2) / 2, HALF_Z2 - WALL_T / 2),
          (HALF_X2 * 2, COL_H2, WALL_T), "M_wall_plaster", col)
    for side in (-1, 1):
        K.box("WALL_Side2_%d" % side, (side * (HALF_X2 - WALL_T / 2), (FY2 + y2) / 2, 0.0),
              (WALL_T, COL_H2, HALF_Z2 * 2), "M_wall_plaster", col)
    zf2 = -(HALF_Z2 - WALL_T / 2)
    for side in (-1, 1):
        for i, x in enumerate((2.40, 5.00)):
            K.lattice_window("WINDOW_F2_%d_%d" % (side, i), side * x, zf2, FY2 + 0.30, 2.10, 2.10, col)
    K.box("WALL_F2Mid", (0.0, FY2 + 0.90, zf2), (4.0, 1.8, WALL_T), "M_wall_plaster", col)
    for side in (-1, 1):
        K.lattice_window("WINDOW_B1_%d" % side, side * 3.20, HALF_Z1 - WALL_T / 2, FY1 + 0.50, 2.60, 2.40, col)
    return col


def build_floor_and_stair(col):
    K.log("楼板 / 楼梯 / 二层栏杆")
    hole_x, hole_z = 3.40, 2.40
    K.box("FLOOR2_L", (-(hole_x + (HALF_X2 - hole_x) / 2), FY2 - 0.11, 0.0),
          (HALF_X2 - hole_x, 0.22, HALF_Z2 * 2), "M_wood_beam", col)
    K.box("FLOOR2_R", ((hole_x + (HALF_X2 - hole_x) / 2), FY2 - 0.11, 0.0),
          (HALF_X2 - hole_x, 0.22, HALF_Z2 * 2), "M_wood_beam", col)
    K.box("FLOOR2_F", (0.0, FY2 - 0.11, -(hole_z + (HALF_Z2 - hole_z) / 2)),
          (hole_x * 2, 0.22, HALF_Z2 - hole_z), "M_wood_beam", col)
    K.box("FLOOR2_B", (0.0, FY2 - 0.11, (hole_z + (HALF_Z2 - hole_z) / 2)),
          (hole_x * 2, 0.22, HALF_Z2 - hole_z), "M_wood_beam", col)
    K.box("FLOOR2_Top", (0.0, FY2 + 0.02, 0.0), (hole_x * 2 - 0.10, 0.04, hole_z * 2 - 0.10),
          "M_floor_stone", col)

    for tag, (x0, z0, x1, z1) in {
        "N": (-hole_x, hole_z, hole_x, hole_z),
        "S": (-hole_x, -hole_z, hole_x, -hole_z),
        "W": (-hole_x, -hole_z, -hole_x, hole_z),
        "E": (hole_x, -hole_z, hole_x, hole_z),
    }.items():
        K.railing_run(col, x0, z0, x1, z1, FY2 + 0.02, "F2" + tag)

    steps = 14
    rise = (FY2 - FY1) / (steps * 2)
    run = 2.30 / steps
    for i in range(steps):
        y = FY1 + rise * (i + 1)
        z = -2.30 - run * (i + 0.5)
        K.box("STAIR_A%02d" % i, (3.55, y - 0.08, z), (1.10, 0.16, run + 0.02), "M_floor_stone", col)
        K.box("STAIR_A_R%02d" % i, (3.55, y - 0.14, z - run / 2), (1.10, 0.14, 0.05), "M_wood_dark", col)
    K.box("STAIR_Landing", (3.05, FY1 + rise * steps, -4.72), (2.10, 0.18, 0.95), "M_floor_stone", col)
    for i in range(steps):
        y = FY1 + rise * (steps + i + 1)
        z = -4.72 + run * (i + 0.5)
        K.box("STAIR_B%02d" % i, (2.50, y - 0.08, z), (1.10, 0.16, run + 0.02), "M_floor_stone", col)
        K.box("STAIR_B_R%02d" % i, (2.50, y - 0.14, z + run / 2), (1.10, 0.14, 0.05), "M_wood_dark", col)
    for tag, x in (("A", 4.10), ("B", 1.95)):
        K.railing_run(col, x, -2.30, x, -4.60, FY1 + 0.30, "ST" + tag)
    return col


def build_interior(col):
    K.log("室内：展台 / 展柜 / 家具 / 陈设")
    K.box("DISPLAY_Main", (0.0, FY1 + 0.30, 0.60), (2.80, 0.60, 1.60), "M_stone_dark", col)
    K.box("DISPLAY_Top", (0.0, FY1 + 0.62, 0.60), (2.70, 0.05, 1.50), "M_floor_stone", col)
    for sx in (-1, 1):
        for sz in (-1, 1):
            K.box("DISPLAY_Trim%d%d" % (sx, sz), (sx * 1.36, FY1 + 0.32, 0.60 + sz * 0.76),
                  (0.08, 0.56, 0.08), "M_gold", col)
    for side in (-1, 1):
        K.box("DISPLAY_Pier%d" % side, (side * 2.30, FY1 + 1.65, -0.90), (0.20, 3.10, 1.90),
              "M_wall_plaster", col)
        K.box("DISPLAY_PierCap%d" % side, (side * 2.30, FY1 + 3.24, -0.90), (0.34, 0.16, 2.10),
              "M_wood_beam", col)

    cid = 0
    for side in (-1, 1):
        for z in (-2.60, 0.20, 2.90):
            x = side * (HALF_X1 - 0.85)
            K.box("CABINET_%d_Body" % cid, (x, FY1 + 0.45, z), (0.60, 0.90, 1.45), "M_wood_dark", col)
            K.box("CABINET_%d_Top" % cid, (x, FY1 + 0.93, z), (0.66, 0.06, 1.50), "M_gold", col)
            K.box("CABINET_%d_Glass" % cid, (x, FY1 + 1.36, z), (0.54, 0.80, 1.40), "M_glass", col)
            K.box("CABINET_%d_Frame" % cid, (x, FY1 + 1.78, z), (0.58, 0.06, 1.44), "M_gold", col)
            for j in range(3):
                K.cyl("CABINET_%d_Vase%d" % (cid, j), (x, FY1 + 0.97, z - 0.44 + j * 0.44),
                      0.10, 0.28, "M_ceramic", col, seg=10)
            cid += 1

    for side in (-1, 1):
        x = side * (HALF_X1 - 0.55)
        K.box("FURN_Shelf%d_Back" % side, (x, FY1 + 1.35, 3.80), (0.12, 2.70, 2.20), "M_wood_dark", col)
        for j in range(4):
            K.box("FURN_Shelf%d_S%d" % (side, j), (x - side * 0.20, FY1 + 1.35, 3.80 - 1.10 + j * 0.73),
                  (0.40, 2.70, 0.06), "M_wood_beam", col)
        for j in range(5):
            K.box("FURN_Shelf%d_B%d" % (side, j), (x - side * 0.20, FY1 + 0.20 + j * 0.62, 3.80),
                  (0.44, 0.06, 2.20), "M_wood_light", col)
        for j in range(4):
            K.cyl("FURN_Shelf%d_P%d" % (side, j),
                  (x - side * 0.20, FY1 + 0.86 + j * 0.62, 3.80 - 0.5 + (j % 2) * 0.9),
                  0.12, 0.26, "M_ceramic", col, seg=10)

    for side in (-1, 1):
        x = side * 4.30
        K.box("FURN_Table%d_Top" % side, (x, FY1 + 0.86, -0.40), (0.58, 0.09, 2.30), "M_wood_beam", col)
        for sx in (-1, 1):
            for sz in (-1, 1):
                K.box("FURN_Table%d_L%d%d" % (side, sx, sz), (x + sx * 0.21, FY1 + 0.43, -0.40 + sz * 1.0),
                      (0.09, 0.86, 0.09), "M_wood_beam", col)
        K.cyl("FURN_Table%d_Vase" % side, (x, FY1 + 0.90, 0.10), 0.11, 0.42, "M_ceramic", col, seg=12)
        K.cyl("FURN_Table%d_Censer" % side, (x, FY1 + 0.90, -0.90), 0.13, 0.16, "M_bronze", col, seg=12)
        for j, cz in enumerate((-0.90, 0.40)):
            cx = side * 3.30
            K.box("FURN_Chair%d_%d_Seat" % (side, j), (cx, FY1 + 0.46, cz), (0.60, 0.08, 0.56), "M_wood_light", col)
            K.box("FURN_Chair%d_%d_Back" % (side, j), (cx - side * 0.26, FY1 + 0.80, cz), (0.07, 0.70, 0.54), "M_wood_light", col)
            for sx in (-1, 1):
                for sz in (-1, 1):
                    K.box("FURN_Chair%d_%d_L%d%d" % (side, j, sx, sz),
                          (cx + sx * 0.25, FY1 + 0.23, cz + sz * 0.23), (0.05, 0.46, 0.05), "M_wood_beam", col)

    for side in (-1, 1):
        x = side * 5.00
        for j in range(3):
            K.box("SCREEN%d_%d" % (side, j), (x, FY1 + 1.20, -3.60 + (j - 1) * 0.60),
                  (0.07, 2.30, 0.58), "M_fabric", col)
            K.box("SCREEN%d_%d_F" % (side, j), (x + side * 0.02, FY1 + 1.20, -3.60 + (j - 1) * 0.60),
                  (0.09, 2.40, 0.64), "M_lacquer_red", col)

    for i, (x, z) in enumerate(((-1.80, 2.60), (1.80, 2.60), (-1.80, -3.10), (1.80, -3.10))):
        K.cyl("LANTERN%d_Post" % i, (x, FY1, z), 0.05, 2.10, "M_gold", col, seg=8)
        K.box("LANTERN%d_Shade" % i, (x, FY1 + 2.30, z), (0.44, 0.64, 0.44), "M_lantern", col)
        K.box("LANTERN%d_Cap" % i, (x, FY1 + 2.68, z), (0.54, 0.08, 0.54), "M_wood_dark", col)

    K.box("CARPET_Main", (0.0, FY1 + 0.01, 0.60), (6.0, 0.02, 4.0), "M_fabric", col)
    for i, (x, z) in enumerate(((-5.60, -4.40), (5.60, -4.40), (-5.60, 0.40), (5.60, 0.40))):
        K.cyl("PLANT_Bamboo%d_Pot" % i, (x, FY1, z), 0.22, 0.32, "M_stone_dark", col, seg=12)
        for j in range(5):
            K.cyl("PLANT_Bamboo%d_S%d" % (i, j), (x + (j - 2) * 0.09, FY1 + 0.30, z),
                  0.022, 2.4 - j * 0.10, "M_plant", col, seg=6)
            for m in range(3):
                K.box("PLANT_Bamboo%d_L%d_%d" % (i, j, m),
                      (x + (j - 2) * 0.09 + 0.14, FY1 + 1.50 + m * 0.36, z),
                      (0.30, 0.02, 0.12), "M_plant", col)
    for side in (-1, 1):
        x = side * 1.90
        K.box("PLANT_Bonsai%d_Pot" % side, (x, FY1 + 0.64, 0.60), (0.46, 0.22, 0.34), "M_ceramic", col)
        K.cyl("PLANT_Bonsai%d_T" % side, (x, FY1 + 0.74, 0.60), 0.05, 0.50, "M_wood_dark", col, seg=6)

    for i, z in enumerate((-2.60, 0.0, 2.60)):
        x = -(HALF_X2 - 0.60)
        K.box("FURN_2F_T%d" % i, (x, FY2 + 0.86, z), (0.50, 0.09, 1.80), "M_wood_beam", col)
        for sz in (-1, 1):
            K.box("FURN_2F_T%d_L%d" % (i, sz), (x, FY2 + 0.43, z + sz * 0.80), (0.50, 0.86, 0.08), "M_wood_beam", col)
        K.cyl("FURN_2F_V%d" % i, (x, FY2 + 0.90, z), 0.10, 0.34, "M_ceramic", col, seg=10)
    K.box("FURN_2F_Couch", (2.20, FY2 + 0.24, 3.60), (2.0, 0.24, 0.82), "M_wood_light", col)
    K.box("FURN_2F_CouchBack", (2.20, FY2 + 0.50, 3.96), (2.0, 0.54, 0.12), "M_wood_beam", col)
    K.box("FURN_2F_Desk", (-3.60, FY2 + 0.80, 3.80), (1.5, 0.09, 0.72), "M_wood_beam", col)
    for i, (x, z) in enumerate(((-1.20, 3.90), (1.20, 3.90))):
        K.cyl("LANTERN_2F%d_P" % i, (x, FY2, z), 0.04, 1.60, "M_gold", col, seg=8)
        K.box("LANTERN_2F%d_S" % i, (x, FY2 + 1.78, z), (0.36, 0.54, 0.36), "M_lantern", col)
    return col


# ---------------------------------------------------------------- 锚点


def build_anchors(col):
    K.log("锚点：展墙 / 画框 / 相机")
    for wall_id, floor, center, rot, size, label in WALLS:
        obj = bpy.data.objects.new("GALWALL_" + wall_id, None)
        obj.empty_display_type = "PLAIN_AXES"
        obj.location = (center[0], -center[2], center[1])
        obj.rotation_euler = (0.0, 0.0, rot)
        col.objects.link(obj)
        obj["floor"] = floor
        obj["width"] = size[0]
        obj["height"] = size[1]
        obj["label"] = label

    wall_map = {w[0]: w for w in WALLS}
    index = {1: 0, 2: 0}
    for wall_id, items in FRAME_PLAN.items():
        wall = wall_map[wall_id]
        for w, h, u, v, label in items:
            index[wall[1]] += 1
            fid = "FRAME_F%d_%03d" % (wall[1], index[wall[1]])
            x, y, z = wall_point(wall, u, v)
            obj = bpy.data.objects.new(fid, None)
            obj.empty_display_type = "PLAIN_AXES"
            obj.location = (x, -z, y)
            obj.rotation_euler = (0.0, 0.0, wall[3])
            col.objects.link(obj)
            obj["floor"] = wall[1]
            obj["wall_id"] = wall_id
            obj["u"] = round(u, 4)
            obj["v"] = round(v, 4)
            obj["frame_size"] = [w, h]
            obj["label"] = label

    cameras = [
        ("front34", (34.0, 18.0, -30.0), (0.0, 7.6, 0.0), 44.0),
        ("front", (0.0, 10.5, -52.0), (0.0, 8.0, 0.0), 42.0),
        ("back", (22.0, 16.0, 46.0), (0.0, 7.4, 0.0), 42.0),
        ("left", (-48.0, 14.0, -8.0), (0.0, 7.6, 0.0), 42.0),
        ("right", (48.0, 14.0, -8.0), (0.0, 7.6, 0.0), 42.0),
        ("top", (24.0, 52.0, -24.0), (0.0, 2.0, 0.0), 44.0),
        ("f1", (0.0, 2.60, -4.20), (0.0, 3.10, 3.20), 16.0),
        ("f2", (-1.60, 9.10, -3.60), (1.00, 8.40, 3.20), 17.0),
        ("ceiling", (0.80, 8.20, -1.80), (0.0, 14.60, 0.80), 18.0),
        ("eave", (12.4, 12.4, -9.6), (6.4, 11.2, -4.6), 50.0),
        ("low34", (24.0, 4.2, -26.0), (0.0, 6.6, 0.0), 44.0),
    ]
    for cam_id, pos, target, lens in cameras:
        data = bpy.data.cameras.new("CAM_" + cam_id)
        data.lens = lens
        data.sensor_width = 36.0
        cam = bpy.data.objects.new("CAM_" + cam_id, data)
        cam.location = (pos[0], -pos[2], pos[1])
        direction = Vector((target[0] - pos[0], -(target[2] - pos[2]), target[1] - pos[1]))
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        cam["target"] = [target[0], target[1], target[2]]
        col.objects.link(cam)
    return col


# ---------------------------------------------------------------- 画框框饰


def build_frame_preview(col):
    """在每个画框锚点上放一层实体框饰（木框 + 卡纸 + 画心底色）。

    为什么不只靠前端画框：
      · Blender 渲染室内图时，锚点如果只是空坐标，整面墙就是一片白，
        室内细节根本看不出「这里挂了画」；
      · 网页端由 GalleryFrame 在墙面 +0.06 处画完整画框，正好盖住这层框饰
        （框饰贴在 +0.02），所以不会出现两套画框打架。

    尺寸与 FRAME_PLAN 完全一致，换画时前端按同一份 layout 定位。
    """
    wall_map = {w[0]: w for w in WALLS}
    seq = 0
    for wall_id, items in FRAME_PLAN.items():
        wall = wall_map[wall_id]
        facing = wall[3]
        nx, nz = math.sin(facing), math.cos(facing)
        # 不用欧拉旋转：按法线方向直接指定尺寸轴。
        # 旋转一走偏，宽/厚就会互换，画框会变成一块垂直于墙的窄板，
        # 远看等于墙上什么都没挂。
        along_z = abs(nz) > 0.5
        for w, h, u, v, _label in items:
            seq += 1
            x, y, z = wall_point(wall, u, v, 0.015)
            tag = "PW_%02d" % seq

            def slab(suffix, material, width, height, depth, push):
                cx = x + nx * push
                cz = z + nz * push
                size = (width, height, depth) if along_z else (depth, height, width)
                return K.box(tag + suffix, (cx, y, cz), size, material, col)

            slab("_Frame", "M_wood_dark", w, h, 0.05, 0.02)
            slab("_Mat", "M_paper", w - 0.14, h - 0.14, 0.02, 0.05)
            slab("_Art", "M_ceramic", w - 0.28, h - 0.28, 0.01, 0.07)
    K.log("frame dressing: %d frames" % seq)
    return col


# ---------------------------------------------------------------- 灯光


def build_lighting(scene):
    world = bpy.data.worlds.new("HZSky")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputWorld")
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.58, 0.68, 0.82, 1.0)
    bg.inputs["Strength"].default_value = 0.60
    world.node_tree.links.new(bg.outputs["Background"], out.inputs["Surface"])

    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 5.6
    sun_data.angle = math.radians(2.2)
    sun_data.color = (1.0, 0.95, 0.87)
    sun = bpy.data.objects.new("Sun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(52), 0.0, math.radians(-38))

    for i, (loc, energy, size) in enumerate((((20.0, 16.0, -18.0), 1200.0, 18.0),
                                            ((-18.0, 10.0, -10.0), 420.0, 16.0))):
        ad = bpy.data.lights.new("Fill%d" % i, "AREA")
        ad.energy = energy
        ad.size = size
        ad.color = (0.86, 0.92, 1.0)
        ob = bpy.data.objects.new("Fill%d" % i, ad)
        scene.collection.objects.link(ob)
        ob.location = (loc[0], loc[2], loc[1])
        direction = Vector((-loc[0], -loc[2] + 2.0, 6.0)) - Vector((loc[0], loc[2], loc[1]))
        ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    for i, (x, y, z, power) in enumerate((
        (0.0, 4.6, 0.6, 320.0),
        (-3.6, 3.6, 1.0, 150.0),
        (3.6, 3.6, 1.0, 150.0),
        (0.0, 9.6, 0.0, 280.0),
        (-3.6, 9.2, 2.4, 130.0),
        (3.6, 9.2, 2.4, 130.0),
        (0.0, 14.0, 0.4, 340.0),
    )):
        pd = bpy.data.lights.new("In%d" % i, "POINT")
        pd.energy = power
        pd.color = (1.0, 0.80, 0.56)
        pd.shadow_soft_size = 0.9
        pd.use_shadow = False
        ob = bpy.data.objects.new("In%d" % i, pd)
        scene.collection.objects.link(ob)
        ob.location = (x, -z, y)


# ---------------------------------------------------------------- 导出


def recalc_normals():
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode="OBJECT")


def apply_modifiers():
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.modifiers:
            continue
        bpy.context.view_layer.objects.active = obj
        for modifier in list(obj.modifiers):
            try:
                bpy.ops.object.modifier_apply(modifier=modifier.name)
            except RuntimeError:
                obj.modifiers.remove(modifier)


def batch_merge():
    groups = {}
    for obj in list(bpy.data.objects):
        if obj.type != "MESH" or obj.parent is not None:
            continue
        if obj.name.startswith("DOOR_Leaf"):
            continue
        category = obj.name.split("_")[0]
        material = obj.data.materials[0].name if obj.data.materials else "none"
        groups.setdefault((category, material), []).append(obj)
    count = 0
    for (category, material), objects in sorted(groups.items()):
        K.merge(objects, "%s_%s" % (category, material.replace("M_", "")), None)
        count += 1
    K.log("batched -> %d objects" % count)


def export_glb():
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.export_scene.gltf(
        filepath=GLB_OUT,
        export_format="GLB",
        use_selection=False,
        export_apply=True,
        export_yup=True,
        export_cameras=False,
        export_lights=False,
        export_materials="EXPORT",
        export_extras=True,
        export_texcoords=True,
        export_tangents=False,
        export_animations=False,
    )
    K.log("exported %s (%d bytes)" % (GLB_OUT, os.path.getsize(GLB_OUT)))


def to_web(v):
    return [round(v[0], 4), round(v[2], 4), round(-v[1], 4)]


def write_layout():
    walls = []
    frames = []
    wall_index = {}
    for ob in bpy.data.objects:
        if ob.type != "EMPTY" or not ob.name.startswith("GALWALL_"):
            continue
        props = {key: ob[key] for key in ob.keys() if not key.startswith("_")}
        wid = ob.name.replace("GALWALL_", "")
        n = ob.matrix_world.to_3x3() @ Vector((0.0, -1.0, 0.0))
        n.normalize()
        entry = {
            "id": wid,
            "floor": int(props.get("floor", 1)),
            "center": to_web(ob.matrix_world.translation),
            "rotationY": round(math.atan2(n.x, -n.y), 4),
            "size": [round(float(props.get("width", 1.6)), 3), round(float(props.get("height", 2.6)), 3)],
            "label": props.get("label", wid),
        }
        walls.append(entry)
        wall_index[wid] = entry

    for ob in bpy.data.objects:
        if ob.type != "EMPTY" or not ob.name.startswith("FRAME_F"):
            continue
        props = {key: ob[key] for key in ob.keys() if not key.startswith("_")}
        parts = ob.name.split("_")
        floor = int(parts[1][1])
        idx = int(parts[2])
        n = ob.matrix_world.to_3x3() @ Vector((0.0, -1.0, 0.0))
        n.normalize()
        size = props.get("frame_size") or [1.0, 0.85]
        wid = props.get("wall_id", "")
        frames.append({
            "id": ob.name,
            "floor": floor,
            "index": idx,
            "position": to_web(ob.matrix_world.translation),
            "rotationY": round(math.atan2(n.x, -n.y), 4),
            "wallId": wid,
            "group": wid.split("-", 1)[1] if "-" in wid else "wall",
            "size": [round(float(size[0]), 3), round(float(size[1]), 3)],
            "u": round(float(props.get("u", 0.5)), 4),
            "v": round(float(props.get("v", 0.5)), 4),
            "label": props.get("label", ob.name),
            "rotZ": round(float(ob.rotation_euler.z), 4),
            "wallSize": wall_index[wid]["size"] if wid in wall_index else None,
        })
    walls.sort(key=lambda item: item["id"])
    frames.sort(key=lambda item: (item["floor"], item["index"]))

    cams = []
    for ob in bpy.data.objects:
        if ob.type != "CAMERA" or not ob.name.startswith("CAM_"):
            continue
        mw = ob.matrix_world
        if "target" in ob.keys():
            target = [float(v) for v in ob["target"]]
        else:
            fwd = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
            p = mw.translation + fwd * 20.0
            target = [p.x, p.z, -p.y]
        cams.append({
            "id": ob.name.replace("CAM_", "").lower(),
            "position": to_web(mw.translation),
            "target": [round(v, 4) for v in target],
            "lens": round(ob.data.lens, 1),
            "sensor": round(ob.data.sensor_width, 1),
            "fov": round(math.degrees(2 * math.atan(ob.data.sensor_width / 2 / ob.data.lens)), 2),
        })
    cams.sort(key=lambda item: item["id"])

    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    tris = 0
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        for corner in ob.bound_box:
            world = ob.matrix_world @ Vector(corner)
            for i in range(3):
                lo[i] = min(lo[i], world[i])
                hi[i] = max(hi[i], world[i])
        ob.data.calc_loop_triangles()
        tris += len(ob.data.loop_triangles)

    doc = {
        "schema": 2,
        "generatedBy": "assets/gallery3d/scripts/v6/hall_huazhang.py",
        "units": "metre",
        "up": "Y (three.js), converted from Blender Z-up",
        "envelope": {
            "min": [round(lo.x, 3), round(lo.z, 3), round(-hi.y, 3)],
            "max": [round(hi.x, 3), round(hi.z, 3), round(-lo.y, 3)],
            "baseSize": 16.6,
            "baseThickness": round(BASE_TOP, 3),
            "floor1Z": FY1,
            "floor2Z": FY2,
            "floor1Height": round(COL_H1, 3),
            "floor2Height": round(COL_H2, 3),
            "topZ": Y_EF1,
            "eaveZ": Y_EAVE_LOW,
            "ridgeZ": Y_RIDGE,
            "footprintX": HALF_X1 * 2,
            "footprintZ": HALF_Z1 * 2,
            "hallOffsetZ": 0.0,
            "triangles": tris,
        },
        "walls": walls,
        "frames": frames,
        "cameras": cams,
        "counts": {
            "floor1": sum(1 for f in frames if f["floor"] == 1),
            "floor2": sum(1 for f in frames if f["floor"] == 2),
        },
    }
    body = json.dumps(doc, indent=1, ensure_ascii=False)
    for dst in (LAYOUT_OUT, FRONT_LAYOUT):
        os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(body + "\n")
    K.log("layout: walls=%d frames=%d cams=%d tris=%d" % (len(walls), len(frames), len(cams), tris))
    return doc


def render_views(scene, only=None, quick=False):
    os.makedirs(RENDER_OUT, exist_ok=True)
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError:
        pass
    scene.render.resolution_x = 1000 if quick else 1500
    scene.render.resolution_y = 750 if quick else 1125
    scene.render.image_settings.file_format = "PNG"
    try:
        scene.eevee.taa_render_samples = 24 if quick else 64
    except AttributeError:
        pass
    views = [
        ("01_front34", "CAM_front34"),
        ("02_front", "CAM_front"),
        ("03_back", "CAM_back"),
        ("04_side", "CAM_right"),
        ("05_top", "CAM_top"),
        ("06_floor1", "CAM_f1"),
        ("07_floor2", "CAM_f2"),
        ("08_ceiling", "CAM_ceiling"),
        ("09_eave", "CAM_eave"),
        ("10_night", "CAM_front34"),
    ]
    for tag, cam_name in views:
        if only and tag not in only and cam_name.replace("CAM_", "") not in only:
            continue
        cam = bpy.data.objects.get(cam_name)
        if cam is None:
            continue
        scene.camera = cam
        night = tag.endswith("night")
        if night:
            for ob in bpy.data.objects:
                if ob.type == "LIGHT" and ob.name.startswith("In"):
                    ob.data.energy *= 2.6
                if ob.type == "LIGHT" and ob.name.startswith("Fill"):
                    ob.data.energy *= 0.30
        scene.render.filepath = os.path.join(RENDER_OUT, tag + ".png")
        bpy.ops.render.render(write_still=True)
        K.log("rendered " + tag)
        if night:
            for ob in bpy.data.objects:
                if ob.type == "LIGHT" and ob.name.startswith("In"):
                    ob.data.energy /= 2.6
                if ob.type == "LIGHT" and ob.name.startswith("Fill"):
                    ob.data.energy /= 0.30


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    quick = "--quick" in argv
    no_render = "--no-render" in argv
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None

    open(K.LOG_PATH, "w", encoding="utf-8").close()
    K.log("=== 华章新馆（重檐歇山）quick=%s no_render=%s" % (quick, no_render))

    scene = K.reset()
    build_lighting(scene)

    c_site = K.collection("HZ_BASE")
    c_frame = K.collection("HZ_FRAME")
    c_roof = K.collection("HZ_ROOF")
    c_wall = K.collection("HZ_WALL")
    c_interior = K.collection("HZ_INTERIOR")
    c_anchor = K.collection("HZ_ANCHOR")

    build_base(c_site)
    build_frame(c_frame)
    build_lower_eave(c_roof)
    build_floor_and_stair(c_frame)
    build_upper_frame(c_frame)
    build_upper_roof(c_roof)
    build_walls(c_wall)
    D.build_finish(c_wall)
    D.build_interior(c_interior)
    build_anchors(c_anchor)
    build_frame_preview(c_interior)

    apply_modifiers()
    batch_merge()
    recalc_normals()

    stats = {"MESH": 0, "EMPTY": 0, "CAMERA": 0}
    tris = 0
    for ob in bpy.data.objects:
        stats[ob.type] = stats.get(ob.type, 0) + 1
        if ob.type == "MESH":
            ob.data.calc_loop_triangles()
            tris += len(ob.data.loop_triangles)
    K.log("objects=%s triangles=%d" % (stats, tris))

    os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
    export_glb()
    write_layout()
    os.makedirs(os.path.dirname(FRONT_GLB), exist_ok=True)
    with open(GLB_OUT, "rb") as src, open(FRONT_GLB, "wb") as dst:
        dst.write(src.read())
    K.log("copied -> %s" % FRONT_GLB)

    if not no_render:
        render_views(scene, only=only, quick=quick)
    K.log("=== done")


if __name__ == "__main__":
    main()