"""华章新馆 · 主构建脚本

    blender.exe -b --factory-startup -P assets/gallery3d/scripts/v6/build_huazhang.py -- --stage all

阶段：
    mass   只建台基 / 墙体 / 屋面，快速看体量
    all    全部构件 + 导出 GLB + layout + 渲染自检图

设计要点（详见 .work/2026-10-24/specs/huazhang-building-spec.md）：
    · 重檐庑殿 + 通高中庭 + 脊部采光带
    · 一层大厅 / 左右展厅 / 后厅，二层环形回廊
    · 24 个画框（一层 12、二层 12），11 面展墙
    · 全部材质为纯色 Principled BSDF，不用贴图
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

import hz_common as H  # noqa: E402
from hz_common import (  # noqa: E402
    F1, F2, F1_H, F2_CLEAR, BEAM1, SLAB_T, COL_TOP, WALL_TOP, EAVE_LOW, EAVE_LOW_IN,
    EAVE_UP, RIDGE, HX, HZ, WALL_T, BASE_TOP, COL_X, COL_Z, LOW_OVER_X, LOW_OVER_Z,
    UP_HALF_X, UP_HALF_Z, RIDGE_HALF, G3D, PROJECT,
    box, cylinder, ring, poly_prism, mesh_object, empty, join_objects, log, mat,
    roof_surface, tile_ridges, eave_trim, eave_band, band_along, V, vlist,
)

BLEND_OUT = os.path.join(G3D, "blender", "wenmai_huazhang.blend")
GLB_OUT = os.path.join(G3D, "exports", "wenmai_gallery_huazhang.glb")
RENDER_OUT = os.path.join(G3D, "renders", "huazhang")
LAYOUT_OUT = os.path.join(G3D, "exports", "huazhang_layout.json")
FRONT_GLB = os.path.join(PROJECT, "frontend", "public", "models", "wenmai_gallery_huazhang.glb")
FRONT_LAYOUT = os.path.join(
    PROJECT, "frontend", "src", "features", "heritage-gallery", "buildings", "layouts", "huazhang_layout.json"
)

# ------------------------------------------------------------------ 展墙 / 画框


def wall_defs():
    """11 面展墙：id, floor, 中心(网页坐标), 朝向, 尺寸, 标签。

    朝向沿用前端约定：rotationY = 0 时法线朝 +Z（房间内侧）。
    """
    y1 = F1 + F1_H / 2
    y2 = F2 + F2_CLEAR / 2
    return [
        ("f1-back", 1, (0.0, y1, 4.64), math.pi, (6.0, F1_H), "一层 · 后墙"),
        ("f1-left-rear", 1, (-6.44, y1, 2.3), math.pi / 2, (4.4, F1_H), "一层 · 左墙后段"),
        ("f1-left-mid", 1, (-6.44, y1, -1.0), math.pi / 2, (3.4, F1_H), "一层 · 左墙中段"),
        ("f1-right-rear", 1, (6.44, y1, 2.3), -math.pi / 2, (4.4, F1_H), "一层 · 右墙后段"),
        ("f1-right-mid", 1, (6.44, y1, -1.0), -math.pi / 2, (3.4, F1_H), "一层 · 右墙中段"),
        ("f1-pier-left", 1, (-2.6, F1 + 1.55, -1.2), math.pi / 2, (1.7, 2.8), "一层 · 独立展墙 左"),
        ("f1-pier-right", 1, (2.6, F1 + 1.55, -1.2), -math.pi / 2, (1.7, 2.8), "一层 · 独立展墙 右"),
        ("f2-back", 2, (0.0, y2, 4.64), math.pi, (6.0, F2_CLEAR), "二层 · 后墙"),
        ("f2-left", 2, (-6.44, y2, 0.6), math.pi / 2, (7.2, F2_CLEAR), "二层 · 左墙"),
        ("f2-right", 2, (6.44, y2, 0.6), -math.pi / 2, (7.2, F2_CLEAR), "二层 · 右墙"),
        ("f2-front", 2, (0.0, y2, -4.64), 0.0, (6.0, F2_CLEAR), "二层 · 前墙"),
    ]


FRAME_PLAN = {
    "f1-back": [(1.25, 1.05, 0.27, 0.47, "一层 · 后墙 · 左"), (1.25, 1.05, 0.73, 0.47, "一层 · 后墙 · 右")],
    "f1-left-rear": [(0.9, 1.15, 0.32, 0.48, "一层 · 左墙后段 · 前"), (1.1, 1.1, 0.72, 0.48, "一层 · 左墙后段 · 后")],
    "f1-left-mid": [(1.4, 0.9, 0.28, 0.5, "一层 · 左墙中段 · 横幅"), (0.85, 1.1, 0.74, 0.5, "一层 · 左墙中段 · 立轴")],
    "f1-right-rear": [(1.1, 1.1, 0.28, 0.48, "一层 · 右墙后段 · 后"), (0.9, 1.15, 0.68, 0.48, "一层 · 右墙后段 · 前")],
    "f1-right-mid": [(0.85, 1.1, 0.26, 0.5, "一层 · 右墙中段 · 立轴"), (1.4, 0.9, 0.72, 0.5, "一层 · 右墙中段 · 横幅")],
    "f1-pier-left": [(1.2, 1.5, 0.5, 0.52, "一层 · 独立展墙 · 左")],
    "f1-pier-right": [(1.2, 1.5, 0.5, 0.52, "一层 · 独立展墙 · 右")],
    "f2-back": [(0.85, 1.1, 0.2, 0.5, "二层 · 后墙 · 左"), (1.3, 0.95, 0.5, 0.5, "二层 · 后墙 · 中"), (0.85, 1.1, 0.8, 0.5, "二层 · 后墙 · 右")],
    "f2-left": [(1.0, 1.2, 0.22, 0.5, "二层 · 左墙 · 后"), (1.45, 0.95, 0.5, 0.5, "二层 · 左墙 · 中"), (1.0, 1.2, 0.78, 0.5, "二层 · 左墙 · 前")],
    "f2-right": [(1.0, 1.2, 0.22, 0.5, "二层 · 右墙 · 后"), (1.45, 0.95, 0.5, 0.5, "二层 · 右墙 · 中"), (1.0, 1.2, 0.78, 0.5, "二层 · 右墙 · 前")],
    "f2-front": [(0.9, 1.15, 0.22, 0.5, "二层 · 前墙 · 左"), (1.25, 1.0, 0.5, 0.5, "二层 · 前墙 · 中"), (0.9, 1.15, 0.78, 0.5, "二层 · 前墙 · 右")],
}


def wall_point(wall, u, v, offset=0.055):
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


# ------------------------------------------------------------------ 台基


def build_site(col):
    log("site: 台基 / 踏步 / 前庭")
    # 三级台基
    box("BASE_L1", 0, 0.075, -0.3, 22.0, 0.15, 17.8, "M_stone_base", col)
    box("BASE_L2", 0, 0.225, -0.3, 20.8, 0.15, 16.6, "M_stone_base", col)
    box("BASE_L3", 0, 0.375, 0.0, 19.6, 0.15, 15.2, "M_stone_base", col)
    # 压边石：三层台阶的边沿各一圈，避免大面积纯色
    for i, (sx, sz, y) in enumerate(((22.0, 17.8, 0.15), (20.8, 16.6, 0.30), (19.6, 15.2, 0.45))):
        box("BASE_TRIM%d" % i, 0, y, -0.3 if i < 2 else 0.0, sx + 0.06, 0.05, sz + 0.06, "M_stone_dark", col)

    # 御路踏跺（正面 z = -9.2 一侧）
    steps = 3
    for i in range(steps):
        y = 0.45 - i * 0.15
        z = -9.2 + i * 0.4
        box("STAIR_APP%d" % i, 0, y - 0.075, z + 0.2, 3.6, 0.15, 0.4, "M_stone_base", col)
    # 垂带石
    for side in (-1, 1):
        box("STAIR_RAIL%d" % side, side * 2.0, 0.225, -8.6, 0.34, 0.45, 1.4, "M_stone_dark", col)

    # 前庭水池（低于台基顶面）
    box("POND_Floor", 0, 0.02, -7.2, 8.2, 0.1, 2.8, "M_granite_dark", col)
    box("POND_Water", 0, 0.062, -7.2, 7.8, 0.02, 2.5, "M_water", col)
    for side in (-1, 1):
        box("POND_Kerb%d" % side, side * 4.18, 0.13, -7.2, 0.26, 0.26, 2.9, "M_stone_dark", col)
    box("POND_KerbF", 0, 0.13, -8.62, 8.4, 0.26, 0.26, "M_stone_dark", col)
    box("POND_KerbB", 0, 0.13, -5.78, 8.4, 0.26, 0.26, "M_stone_dark", col)

    # 石灯 2 对
    for i, (x, z) in enumerate(((-5.4, -7.6), (5.4, -7.6), (-8.2, -3.0), (8.2, -3.0))):
        box("STONE_LAMP%d_Base" % i, x, 0.30, z, 0.52, 0.30, 0.52, "M_stone_base", col)
        cylinder("STONE_LAMP%d_Post" % i, x, 0.45, z, 0.09, 0.62, "M_stone_dark", col, seg=10)
        box("STONE_LAMP%d_Box" % i, x, 1.16, z, 0.40, 0.42, 0.40, "M_paper", col)
        box("STONE_LAMP%d_Cap" % i, x, 1.44, z, 0.56, 0.12, 0.56, "M_stone_dark", col)

    # 抱鼓石 2 对（门前）
    for i, x in enumerate((-2.9, 2.9)):
        cylinder("DRUM%d" % i, x, 0.45, -8.9, 0.30, 0.34, "M_stone_base", col, axis="z", seg=16)
        box("DRUM%d_Stand" % i, x, 0.30, -8.9, 0.34, 0.3, 0.5, "M_stone_dark", col)

    # 松树 3 株（台基两侧与前方）
    for i, (x, z, hgt) in enumerate(((-8.6, 1.2, 3.4), (8.6, 1.2, 3.2), (-8.4, -5.4, 2.8))):
        cylinder("PLANT_Pine%d_Trunk" % i, x, 0.45, z, 0.13, hgt, "M_wood_walnut", col, seg=8)
        for k in range(3):
            y = 0.45 + hgt * (0.45 + 0.18 * k)
            r = 1.0 - 0.2 * k
            cylinder("PLANT_Pine%d_Foliage%d" % (i, k), x, y, z, r, 0.55, "M_plant", col, seg=12)
    return col


# ------------------------------------------------------------------ 外壳


def build_shell(col):
    log("shell: 墙 / 柱 / 门窗 / 楼板 / 楼梯")
    # ---- 地面 ----
    box("WALL_Floor1", 0, F1 - 0.04, 0.0, HX * 2 - 0.2, 0.08, HZ * 2 - 0.2, "M_stone_floor", col)

    # ---- 后墙 / 侧墙（整片，窗做贴面） ----
    box("WALL_Back", 0, (F1 + WALL_TOP) / 2, HZ - WALL_T / 2, HX * 2, WALL_TOP - F1, WALL_T, "M_wall_plaster", col)
    for side in (-1, 1):
        box(
            "WALL_Side%d" % side,
            side * (HX - WALL_T / 2),
            (F1 + WALL_TOP) / 2,
            0.0,
            WALL_T,
            WALL_TOP - F1,
            HZ * 2,
            "M_wall_plaster",
            col,
        )

    # ---- 前墙：中央 3.2 m 门洞，两侧实墙 ----
    open_w = 1.6
    for side in (-1, 1):
        seg_w = (HX - open_w)
        box(
            "WALL_Front%d" % side,
            side * (open_w + seg_w / 2),
            (F1 + WALL_TOP) / 2,
            -(HZ - WALL_T / 2),
            seg_w,
            WALL_TOP - F1,
            WALL_T,
            "M_wall_plaster",
            col,
        )
    # 门楣（门洞上方到围脊）
    box("WALL_FrontLintel", 0, (4.65 + WALL_TOP) / 2, -(HZ - WALL_T / 2), open_w * 2, WALL_TOP - 4.65, WALL_T, "M_wall_plaster", col)
    # 门槛石
    box("WALL_Threshold", 0, F1 - 0.02, -(HZ - 0.1), open_w * 2, 0.14, 0.42, "M_stone_dark", col)

    # ---- 侧墙槛窗（贴面：槛墙 + 玻璃 + 木框） ----
    for side in (-1, 1):
        for i, z in enumerate((-2.6, 0.0, 2.6)):
            x = side * (HX + 0.02)
            box("WALL_Sill%d_%d" % (side, i), x, F1 + 0.35, z, 0.06, 0.7, 2.1, "M_wood_walnut", col)
            box("WINDOW_Glass%d_%d" % (side, i), x + side * 0.01, F1 + 1.9, z, 0.04, 2.4, 1.9, "M_glass", col)
            # 窗框
            box("WINDOW_Frame%d_%d_T" % (side, i), x + side * 0.02, F1 + 3.12, z, 0.07, 0.08, 2.1, "M_wood_walnut", col)
            box("WINDOW_Frame%d_%d_B" % (side, i), x + side * 0.02, F1 + 0.68, z, 0.07, 0.08, 2.1, "M_wood_walnut", col)
            for j in (-1, 1):
                box(
                    "WINDOW_Frame%d_%d_S%d" % (side, i, j),
                    x + side * 0.02,
                    F1 + 1.9,
                    z + j * 1.0,
                    0.07,
                    2.4,
                    0.08,
                    "M_wood_walnut",
                    col,
                )
            # 棂条
            for k in range(3):
                box(
                    "WINDOW_Mullion%d_%d_%d" % (side, i, k),
                    x + side * 0.03,
                    F1 + 1.9,
                    z - 0.5 + k * 0.5,
                    0.06,
                    2.28,
                    0.035,
                    "M_wood_light",
                    col,
                )

    # ---- 后墙小窗 ----
    box("WINDOW_BackGlass", 0, F1 + 2.6, HZ - 0.12, 1.8, 1.2, 0.04, "M_glass", col)
    for j in (-1, 0, 1):
        box("WINDOW_BackMullion%d" % j, j * 0.6, F1 + 2.6, HZ - 0.14, 0.05, 1.2, 0.05, "M_wood_light", col)

    # ---- 立面节奏：台明 / 腰线 / 壁柱 / 二层槛窗 / 额枋 ----
    # 台明：一圈石活，把白墙从台基上「托」起来
    box("WALL_PlinthF", 0, F1 + 0.07, -(HZ + 0.04), HX * 2 + 0.2, 0.14, 0.16, "M_stone_dark", col)
    box("WALL_PlinthB", 0, F1 + 0.07, HZ + 0.04, HX * 2 + 0.2, 0.14, 0.16, "M_stone_dark", col)
    for side in (-1, 1):
        box("WALL_PlinthS%d" % side, side * (HX + 0.04), F1 + 0.07, 0, 0.16, 0.14, HZ * 2, "M_stone_dark", col)

    # 腰线：一层与二层之间的石线脚，横向把 9.8 m 高的墙分段
    box("WALL_BeltF", 0, 8.24, -(HZ + 0.05), HX * 2 + 0.24, 0.26, 0.12, "M_stone_dark", col)
    box("WALL_BeltB", 0, 8.24, HZ + 0.05, HX * 2 + 0.24, 0.26, 0.12, "M_stone_dark", col)
    for side in (-1, 1):
        box("WALL_BeltS%d" % side, side * (HX + 0.05), 8.24, 0, 0.12, 0.26, HZ * 2, "M_stone_dark", col)

    # 壁柱：开间分隔处的竖向木柱，给大白墙做出「五间」的节奏
    for x in (-4.2, -1.6, 1.6, 4.2):
        box("WALL_PilasterF%d" % int(x * 10), x, (F1 + 8.1) / 2 + 0.05, -(HZ + 0.06), 0.34, 7.5, 0.12, "M_wood_walnut", col)
        box("WALL_PilasterB%d" % int(x * 10), x, (F1 + 8.1) / 2 + 0.05, HZ + 0.06, 0.34, 7.5, 0.12, "M_wood_walnut", col)
    for z in (-2.2, 2.2):
        for side in (-1, 1):
            box(
                "WALL_PilasterS%d_%d" % (int(z * 10), side),
                side * (HX + 0.06),
                (F1 + 8.1) / 2 + 0.05,
                z,
                0.12,
                7.5,
                0.34,
                "M_wood_walnut",
                col,
            )

    # 额枋：檐下一圈深色木带，压住墙面顶部
    box("BEAM_FriezeF", 0, 8.62, -(HZ + 0.07), HX * 2 + 0.18, 0.30, 0.14, "M_wood_walnut", col)
    box("BEAM_FriezeB", 0, 8.62, HZ + 0.07, HX * 2 + 0.18, 0.30, 0.14, "M_wood_walnut", col)
    for side in (-1, 1):
        box("BEAM_FriezeS%d" % side, side * (HX + 0.07), 8.62, 0, 0.14, 0.30, HZ * 2, "M_wood_walnut", col)

    # 正立面梢间槛窗（每侧两樘，贴面：槛墙 + 玻璃 + 窗框 + 棂条）
    for side in (-1, 1):
        for i, x in enumerate((3.0, 5.2)):
            wx = side * x
            wz = -(HZ + 0.03)
            box("WINDOW_FrontSill%d_%d" % (side, i), wx, F1 + 0.5, wz, 1.9, 1.1, 0.10, "M_wood_walnut", col)
            box("WINDOW_FrontGlass%d_%d" % (side, i), wx, F1 + 2.05, wz - 0.01, 1.72, 2.0, 0.05, "M_glass", col)
            for j, dy in ((0, 1.02), (1, -1.02)):
                box("WINDOW_FrontFrame%d_%d_%d" % (side, i, j), wx, F1 + 2.05 + dy, wz, 1.9, 0.10, 0.11, "M_wood_walnut", col)
            for j, dx in ((0, 0.94), (1, -0.94)):
                box("WINDOW_FrontJamb%d_%d_%d" % (side, i, j), wx + dx, F1 + 2.05, wz, 0.09, 2.14, 0.11, "M_wood_walnut", col)
            for k in (-1, 0, 1):
                box("WINDOW_FrontBar%d_%d_%d" % (side, i, k), wx + k * 0.47, F1 + 2.05, wz - 0.02, 0.045, 2.0, 0.06, "M_wood_light", col)

    # 二层槛窗（贴面）：让二层外立面有开窗节奏，而不是一整片白墙
    for side in (-1, 1):
        for i, x in enumerate((2.6, 5.0)):
            wx = side * x
            wz = -(HZ + 0.03)
            box("WINDOW_F2F%d_%d" % (side, i), wx, 6.55, wz - 0.01, 1.66, 1.9, 0.05, "M_glass", col)
            box("WINDOW_F2Fsill%d_%d" % (side, i), wx, 5.55, wz, 1.86, 0.14, 0.11, "M_wood_walnut", col)
            box("WINDOW_F2Flintel%d_%d" % (side, i), wx, 7.56, wz, 1.86, 0.14, 0.11, "M_wood_walnut", col)
            for k in (-1, 0, 1):
                box("WINDOW_F2Fbar%d_%d_%d" % (side, i, k), wx + k * 0.45, 6.55, wz - 0.02, 0.045, 1.9, 0.06, "M_wood_light", col)

    # ---- 檐柱 ----
    for i, x in enumerate((-6.4, -4.2, -1.6, 1.6, 4.2, 6.4)):
        for z in (HZ - 0.35, -(HZ - 0.35)):
            box("COLUMN_Base%d_%d" % (i, int(z)), x, F1 + 0.12, z, 0.52, 0.24, 0.52, "M_stone_base", col)
            cylinder("COLUMN_Eave%d_%d" % (i, int(z)), x, F1 + 0.24, z, 0.15, COL_TOP - F1 - 0.24, "M_lacquer_red", col, seg=12)
    # ---- 金柱 ----
    for i, x in enumerate((-4.2, -1.6, 1.6, 4.2)):
        for j, z in enumerate((-2.2, 2.2)):
            box("COLUMN_GoldBase%d_%d" % (i, j), x, F1 + 0.14, z, 0.62, 0.28, 0.62, "M_stone_base", col)
            cylinder("COLUMN_Gold%d_%d" % (i, j), x, F1 + 0.28, z, 0.19, F1_H - 0.28, "M_lacquer_red", col, seg=12)

    # ---- 一层梁架（BEAM_ 前缀：DIY 悬挂锚点识别） ----
    # 只沿中庭边界（z=±2.2）设两道横梁；跨中庭的纵梁会切断通高视线，故不设，
    # 只在两侧梢间（x=±4.2）保留纵梁承担楼板。
    for i, z in enumerate((-2.2, 2.2)):
        box("BEAM_F1_X%d" % i, 0, BEAM1 - 0.22, z, HX * 2, 0.44, 0.30, "M_wood_walnut", col)
    for i, x in enumerate((-4.2, 4.2)):
        box("BEAM_F1_Z%d" % i, x, BEAM1 - 0.20, 0, 0.26, 0.36, HZ * 2, "M_wood_walnut", col)
    # 檩条：贴两侧梢间，中庭范围内不设
    for i, x in enumerate((-5.2, -3.6, 3.6, 5.2)):
        box("PURLIN_F1_%d" % i, x, BEAM1 - 0.04, 0, 0.16, 0.16, HZ * 2, "M_wood_light", col)

    # ---- 二层楼板（环形，中庭挑空） ----
    hole_x, hole_z = 3.4, 2.3
    box("WALL_Floor2L", -(hole_x + (HX - hole_x) / 2), F2 - SLAB_T / 2, 0, HX - hole_x, SLAB_T, HZ * 2, "M_wood_walnut", col)
    box("WALL_Floor2R", (hole_x + (HX - hole_x) / 2), F2 - SLAB_T / 2, 0, HX - hole_x, SLAB_T, HZ * 2, "M_wood_walnut", col)
    box("WALL_Floor2F", 0, F2 - SLAB_T / 2, -(hole_z + (HZ - hole_z) / 2), hole_x * 2, SLAB_T, HZ - hole_z, "M_wood_walnut", col)
    box("WALL_Floor2B", 0, F2 - SLAB_T / 2, (hole_z + (HZ - hole_z) / 2), hole_x * 2, SLAB_T, HZ - hole_z, "M_wood_walnut", col)
    # 楼板面材
    box("WALL_Floor2Top", 0, F2 + 0.02, 0, hole_x * 2 - 0.2, 0.04, hole_z * 2 - 0.2, "M_stone_floor", col)

    # ---- 二层回廊栏杆（模型自带，前端不再补画） ----
    rail_segments = [
        ((-hole_x, hole_z), (hole_x, hole_z)),
        ((-hole_x, -hole_z), (hole_x, -hole_z)),
        ((-hole_x, -hole_z), (-hole_x, hole_z)),
        ((hole_x, -hole_z), (hole_x, hole_z)),
    ]
    for i, ((x0, z0), (x1, z1)) in enumerate(rail_segments):
        length = math.hypot(x1 - x0, z1 - z0)
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        horizontal = abs(x1 - x0) > abs(z1 - z0)
        box("RAIL_2F_Hand%d" % i, cx, F2 + 0.96, cz, length, 0.08, 0.10, "M_wood_walnut", col)
        box("RAIL_2F_Panel%d" % i, cx, F2 + 0.48, cz, length, 0.84, 0.04, "M_wood_light", col)
        n = max(2, int(length / 0.9) + 1)
        for k in range(n):
            t = k / (n - 1)
            box(
                "RAIL_2F_Post%d_%d" % (i, k),
                x0 + (x1 - x0) * t,
                F2 + 0.5,
                z0 + (z1 - z0) * t,
                0.09,
                1.0,
                0.09,
                "M_wood_walnut",
                col,
            )
    return col


def build_stair(col):
    log("stair: 后厅东侧双跑折返楼梯")
    # 第一跑：z 从 -2.2 到 -4.3，x 2.6..3.75，14 级
    steps = 14
    rise = (2.85 - F1) / steps
    run = 2.1 / steps
    for i in range(steps):
        y = F1 + rise * (i + 1)
        z = -2.2 - run * (i + 0.5)
        box("STAIR_A_Tread%02d" % i, 3.175, y - 0.07, z, 1.15, 0.14, run + 0.02, "M_stone_floor", col)
        box("STAIR_A_Riser%02d" % i, 3.175, y - 0.12, z - run / 2, 1.15, 0.12, 0.05, "M_stone_dark", col)
    # 中间平台
    box("STAIR_Landing", 2.6, 2.90, -4.55, 2.3, 0.14, 0.9, "M_stone_floor", col)
    # 第二跑：x 1.45..2.6，z 从 -4.75 到 -2.6，14 级
    rise2 = (F2 - 3.0) / steps
    run2 = 2.15 / steps
    for i in range(steps):
        y = 3.0 + rise2 * (i + 1)
        z = -4.75 + run2 * (i + 0.5)
        box("STAIR_B_Tread%02d" % i, 2.025, y - 0.07, z, 1.15, 0.14, run2 + 0.02, "M_stone_floor", col)
        box("STAIR_B_Riser%02d" % i, 2.025, y - 0.12, z + run2 / 2, 1.15, 0.12, 0.05, "M_stone_dark", col)
    # 楼梯栏杆
    for side_x, x in (("L", 3.75), ("R", 2.6)):
        for k in range(0, steps, 2):
            y = F1 + rise * (k + 1)
            z = -2.2 - run * (k + 0.5)
            box("STAIR_PostA%s%02d" % (side_x, k), x, y + 0.42, z, 0.08, 0.9, 0.08, "M_wood_walnut", col)
        box("STAIR_HandA%s" % side_x, x, F1 + 1.35, -3.25, 0.07, 0.08, 2.2, "M_wood_walnut", col)
    return col


# ------------------------------------------------------------------ 屋面


def build_roof(col):
    log("roof: 下檐 / 上檐 / 瓦垄 / 斗拱 / 天窗")
    # ---- 下檐：环绕主体的浅坡腰檐 ----
    outer_x, outer_z = HX + LOW_OVER_X, HZ + LOW_OVER_Z
    inner_x, inner_z = HX + 0.02, HZ + 0.02
    y_out, y_in = EAVE_LOW, EAVE_LOW_IN
    H.ring_hip(
        "ROOF_Lower",
        inner_x,
        inner_z,
        outer_x,
        outer_z,
        y_in,
        y_out,
        "M_tile_grey",
        col,
        ntheta=88,
        nt=4,
        thickness=0.13,
    )
    steps = 24
    lower_edges = [
        lambda t: (-outer_x + 2 * outer_x * t, outer_z),
        lambda t: (outer_x, outer_z - 2 * outer_z * t),
        lambda t: (outer_x - 2 * outer_x * t, -outer_z),
        lambda t: (-outer_x, -outer_z + 2 * outer_z * t),
    ]
    for index, fn in enumerate(lower_edges):
        pts = []
        for i in range(steps + 1):
            x, z = fn(i / steps)
            lift = 0.18 * ((abs(x) / outer_x) * (abs(z) / outer_z)) ** 2.4
            pts.append((x, y_out + lift - 0.05, z))
        band_along("ROOF_LowerEave%d" % index, pts, 0.14, "M_tile_dark", col)

    # ---- 上檐：庑殿 ----
    upper = roof_surface(
        "ROOF_Upper",
        UP_HALF_X,
        UP_HALF_Z,
        RIDGE_HALF,
        EAVE_UP,
        RIDGE,
        "M_tile_grey",
        col,
        nx=56,
        nz=44,
        curve=1.35,
        thickness=0.16,
    )
    eave_band("ROOF_UpperEave", UP_HALF_X, UP_HALF_Z, RIDGE_HALF, EAVE_UP, RIDGE, "M_tile_dark", col)
    return upper


def build_roof_details(col):
    log("roof detail: 瓦垄 / 斗拱 / 正脊 / 天窗")
    # ---- 上檐瓦垄 ----
    ridges = tile_ridges(
        "TILE_Upper", UP_HALF_X, UP_HALF_Z, RIDGE_HALF, EAVE_UP, RIDGE,
        "M_tile_dark", col, spacing=0.40, width=0.19, lift=0.065,
    )
    join_objects(ridges, "TILE_UpperRows", col)

    # ---- 正脊（沿 x：面阔方向才是长边）----
    ridge_len = (UP_HALF_X - UP_HALF_Z) * 2
    box("ROOF_Ridge", 0, RIDGE + 0.15, 0, ridge_len + 0.5, 0.38, 0.34, "M_tile_dark", col)
    for side in (-1, 1):
        # 鸱吻：正脊两端翘起的脊饰
        box("ROOF_Finial%d" % side, side * (ridge_len / 2 + 0.18), RIDGE + 0.40, 0, 0.30, 0.52, 0.24, "M_tile_dark", col)
        box("ROOF_Finial%d_t" % side, side * (ridge_len / 2 + 0.30), RIDGE + 0.66, 0, 0.14, 0.16, 0.14, "M_gold_brass", col)
        # 垂脊：从正脊端沿对角下到檐角；用脊带而不是一串方块，才有连续的脊线
        for zsign in (-1, 1):
            pts = []
            for k in range(15):
                t = k / 14
                x = side * (ridge_len / 2 + (UP_HALF_X - ridge_len / 2) * t)
                z = zsign * UP_HALF_Z * t
                y = H.roof_height(x, z, UP_HALF_X, UP_HALF_Z, RIDGE_HALF, EAVE_UP, RIDGE, 1.35)
                pts.append((x, y + 0.09, z))
            band_along("ROOF_Hip%d_%d" % (side, zsign), pts, 0.34, "M_tile_dark", col)

    # ---- 斗拱：檐下三步出挑，比单个方块更有层次 ----
    buckets = []
    for i in range(-5, 6):
        x = i * 1.15
        if abs(x) > HX + 0.4:
            continue
        for z in (HZ + LOW_OVER_Z - 0.62, -(HZ + LOW_OVER_Z - 0.62)):
            tag = "X%d_%d" % (i, int(z))
            buckets.append(box("BRACKET_%s_A" % tag, x, EAVE_LOW - 0.66, z, 0.34, 0.16, 0.46, "M_wood_walnut", col))
            buckets.append(box("BRACKET_%s_B" % tag, x, EAVE_LOW - 0.52, z, 0.46, 0.13, 0.36, "M_wood_light", col))
            buckets.append(box("BRACKET_%s_C" % tag, x, EAVE_LOW - 0.41, z, 0.58, 0.11, 0.28, "M_wood_walnut", col))
    for j in range(-3, 4):
        z = j * 1.3
        if abs(z) > HZ + 0.4:
            continue
        for x in (HX + LOW_OVER_X - 0.62, -(HX + LOW_OVER_X - 0.62)):
            tag = "Z%d_%d" % (j, int(x))
            buckets.append(box("BRACKET_%s_A" % tag, x, EAVE_LOW - 0.66, z, 0.46, 0.16, 0.34, "M_wood_walnut", col))
            buckets.append(box("BRACKET_%s_B" % tag, x, EAVE_LOW - 0.52, z, 0.36, 0.13, 0.46, "M_wood_light", col))
            buckets.append(box("BRACKET_%s_C" % tag, x, EAVE_LOW - 0.41, z, 0.28, 0.11, 0.58, "M_wood_walnut", col))
    join_objects(buckets, "BRACKET_Eave", col)

    # ---- 围脊：压住墙顶与上檐之间的接缝，免得露出一条白线 ----
    # 墙顶先盖一块深色平板，任何缝隙下面都是瓦色而不是白灰泥
    box("ROOF_WallTopCap", 0, WALL_TOP + 0.03, 0, HX * 2 + 0.5, 0.06, HZ * 2 + 0.5, "M_tile_dark", col)
    for side in (-1, 1):
        box("ROOF_CollarF%d" % side, 0, WALL_TOP + 0.10, side * (HZ + 0.30), HX * 2 + 0.8, 0.16, 0.80, "M_tile_dark", col)
        box("ROOF_CollarS%d" % side, side * (HX + 0.30), WALL_TOP + 0.10, 0, 0.80, 0.16, HZ * 2, "M_tile_dark", col)
    return col


# ------------------------------------------------------------------ 门窗


def build_doors(col):
    log("doors: 中央格扇门（含可开启门扇）")
    # 6 扇格扇，每扇 0.533 宽，高 4.2，底 0.50
    width = 3.2
    leaves = 6
    leaf_w = width / leaves
    z = -(HZ - WALL_T / 2)
    for i in range(leaves):
        x = -width / 2 + leaf_w * (i + 0.5)
        # 边框
        box("DOOR_Frame%02d_L" % i, x - leaf_w / 2 + 0.03, F1 + 2.4, z, 0.06, 4.2, 0.09, "M_wood_walnut", col)
        box("DOOR_Frame%02d_R" % i, x + leaf_w / 2 - 0.03, F1 + 2.4, z, 0.06, 4.2, 0.09, "M_wood_walnut", col)
        box("DOOR_Frame%02d_T" % i, x, F1 + 4.44, z, leaf_w, 0.12, 0.09, "M_wood_walnut", col)
        box("DOOR_Frame%02d_B" % i, x, F1 + 0.56, z, leaf_w, 0.12, 0.09, "M_wood_walnut", col)
        # 格心宣纸 + 棂条
        box("DOOR_Paper%02d" % i, x, F1 + 2.7, z + 0.02, leaf_w - 0.12, 3.2, 0.03, "M_paper", col)
        for k in range(4):
            box("DOOR_MullionV%02d_%d" % (i, k), x - leaf_w / 2 + 0.1 + k * (leaf_w - 0.2) / 3, F1 + 2.7, z + 0.05, 0.03, 3.2, 0.03, "M_wood_light", col)
        for k in range(5):
            box("DOOR_MullionH%02d_%d" % (i, k), x, F1 + 1.35 + k * 0.68, z + 0.05, leaf_w - 0.12, 0.03, 0.03, "M_wood_light", col)
        # 裙板
        box("DOOR_Skirt%02d" % i, x, F1 + 0.92, z + 0.01, leaf_w - 0.08, 0.55, 0.05, "M_lacquer_red", col)

    # 可开启的两扇（交给前端 DOOR_HingeL / DOOR_HingeR 旋转）
    hinge_y = F1 + 2.45
    for side, hinge_x in ((-1, -width / 2), (1, width / 2 - leaf_w)):
        obj = empty(
            "DOOR_Hinge%s" % ("L" if side < 0 else "R"),
            hinge_x,
            hinge_y,
            z + 0.06,
            {"floor": 1},
            col,
        )
        leaf_center = (leaf_w / 2) * side if side > 0 else (leaf_w / 2)
        # 子对象坐标相对铰链
        tmp = box(
            "DOOR_Leaf%s" % ("L" if side < 0 else "R"),
            hinge_x + (leaf_w / 2 if side < 0 else -leaf_w / 2),
            hinge_y,
            z + 0.06,
            leaf_w - 0.02,
            4.0,
            0.06,
            "M_wood_walnut",
            col,
        )
        tmp.parent = obj
        tmp.matrix_parent_inverse = obj.matrix_world.inverted()
        tmp.location = (leaf_w / 2 if side < 0 else -leaf_w / 2, 0, 0)

    # 匾额
    box("PLAQUE_Board", 0, 5.05, -(HZ + 0.06), 3.0, 0.85, 0.12, "M_wood_walnut", col)
    box("PLAQUE_Border", 0, 5.05, -(HZ + 0.02), 3.2, 1.0, 0.06, "M_gold_brass", col)
    return col


# ------------------------------------------------------------------ 室内


def build_interior(col):
    log("interior: 大厅 / 展柜 / 家具 / 陈设 / 二层")
    # ---- 中央展台（压低、缩小，别把大厅采光与视线全挡掉） ----
    box("DISPLAY_Main", 0, F1 + 0.26, 0.7, 2.6, 0.52, 1.5, "M_granite_dark", col)
    box("DISPLAY_MainTop", 0, F1 + 0.54, 0.7, 2.5, 0.05, 1.4, "M_stone_floor", col)
    for sx in (-1, 1):
        for sz in (-1, 1):
            box("DISPLAY_Trim%d%d" % (sx, sz), sx * 1.26, F1 + 0.27, 0.7 + sz * 0.71, 0.08, 0.5, 0.08, "M_gold_brass", col)

    # ---- 独立展墙（双面） ----
    for side in (-1, 1):
        box("DISPLAY_Pier%d" % side, side * 2.6, F1 + 1.55, -1.2, 0.18, 2.8, 1.7, "M_wall_plaster", col)
        box("DISPLAY_PierCap%d" % side, side * 2.6, F1 + 3.0, -1.2, 0.30, 0.14, 1.9, "M_wood_walnut", col)

    # ---- 通长玻璃展柜（沿左右墙） ----
    case_id = 0
    for side in (-1, 1):
        for z in (-2.0, 0.6, 3.0):
            x = side * (HX - 0.75)
            box("CABINET_%d_Body" % case_id, x, F1 + 0.45, z, 0.55, 0.90, 1.4, "M_wood_walnut", col)
            box("CABINET_%d_Top" % case_id, x, F1 + 0.92, z, 0.60, 0.05, 1.45, "M_gold_brass", col)
            box("CABINET_%d_Glass" % case_id, x, F1 + 1.35, z, 0.50, 0.80, 1.35, "M_glass", col)
            box("CABINET_%d_Frame" % case_id, x, F1 + 1.76, z, 0.54, 0.06, 1.40, "M_gold_brass", col)
            # 柜内瓷器
            for k in range(3):
                cz = z - 0.42 + k * 0.42
                cylinder("CABINET_%d_Vase%d" % (case_id, k), x, F1 + 0.96, cz, 0.10, 0.30, "M_ceramic", col, seg=10)
            case_id += 1

    # ---- 博古架 ----
    for side in (-1, 1):
        x = side * (HX - 0.45)
        z = 2.6
        box("FURN_Shelf%d_Back" % side, x, F1 + 1.3, z, 0.10, 2.6, 2.2, "M_wood_walnut", col)
        for k in range(4):
            box("FURN_Shelf%d_Side%d" % (side, k), x - side * 0.18, F1 + 1.3, z - 1.1 + k * 0.73, 0.36, 2.6, 0.06, "M_wood_walnut", col)
        for k in range(5):
            box("FURN_Shelf%d_Board%d" % (side, k), x - side * 0.18, F1 + 0.1 + k * 0.6, z, 0.4, 0.05, 2.2, "M_wood_light", col)
        # 架上器物
        for k in range(4):
            cylinder("FURN_Shelf%d_Pot%d" % (side, k), x - side * 0.18, F1 + 0.75 + k * 0.6, z - 0.5 + (k % 2) * 0.9, 0.13, 0.26, "M_ceramic", col, seg=10)

    # ---- 条案 + 圈椅 ----
    for side in (-1, 1):
        x = side * 4.6
        z = -0.2
        box("FURN_Table%d_Top" % side, x, F1 + 0.86, z, 0.55, 0.08, 2.2, "M_wood_walnut", col)
        for sx in (-1, 1):
            for sz in (-1, 1):
                box("FURN_Table%d_Leg%d%d" % (side, sx, sz), x + sx * 0.2, F1 + 0.43, z + sz * 0.95, 0.09, 0.86, 0.09, "M_wood_walnut", col)
        # 案上花瓶 + 香炉
        cylinder("FURN_Table%d_Vase" % side, x, F1 + 0.90, z + 0.6, 0.11, 0.42, "M_ceramic", col, seg=12)
        cylinder("FURN_Table%d_Censer" % side, x, F1 + 0.90, z - 0.55, 0.13, 0.16, "M_bronze", col, seg=12)
        # 圈椅
        for k, chair_z in enumerate((z + 0.5, z - 0.5)):
            cx = side * 3.7
            box("FURN_Chair%d_%d_Seat" % (side, k), cx, F1 + 0.44, chair_z, 0.58, 0.08, 0.55, "M_wood_light", col)
            box("FURN_Chair%d_%d_Back" % (side, k), cx - side * 0.25, F1 + 0.78, chair_z, 0.07, 0.68, 0.52, "M_wood_light", col)
            for sx in (-1, 1):
                for sz in (-1, 1):
                    box("FURN_Chair%d_%d_Leg%d%d" % (side, k, sx, sz), cx + sx * 0.24, F1 + 0.22, chair_z + sz * 0.22, 0.05, 0.44, 0.05, "M_wood_walnut", col)

    # ---- 屏风 ----
    for side in (-1, 1):
        x = side * 5.2
        z = -3.6
        for k in range(3):
            box("SCREEN%d_%d" % (side, k), x + side * (k - 1) * 0.02, F1 + 1.15, z + (k - 1) * 0.58, 0.07, 2.2, 0.56, "M_fabric", col)
            box("SCREEN%d_%d_Frame" % (side, k), x + side * 0.02, F1 + 1.15, z + (k - 1) * 0.58, 0.09, 2.3, 0.62, "M_lacquer_red", col)

    # ---- 宫灯 4 盏 ----
    for i, (x, z) in enumerate(((-1.9, 2.9), (1.9, 2.9), (-1.9, -3.0), (1.9, -3.0))):
        cylinder("LANTERN%d_Post" % i, x, F1, z, 0.05, 1.9, "M_gold_brass", col, seg=8)
        box("LANTERN%d_Shade" % i, x, F1 + 2.1, z, 0.44, 0.62, 0.44, "M_lantern_glow", col)
        box("LANTERN%d_Cap" % i, x, F1 + 2.46, z, 0.54, 0.07, 0.54, "M_wood_walnut", col)
        box("LANTERN%d_Base" % i, x, F1 + 0.03, z, 0.32, 0.06, 0.32, "M_stone_dark", col)

    # ---- 地毯 ----
    box("CARPET_Main", 0, F1 + 0.006, 0.2, 6.0, 0.012, 4.2, "M_fabric", col)
    for side in (-1, 1):
        box("CARPET_Side%d" % side, side * 4.3, F1 + 0.006, 1.0, 2.4, 0.012, 3.4, "M_fabric", col)

    # ---- 竹丛 + 松盆景 ----
    for i, (x, z) in enumerate(((-5.9, -4.2), (5.9, -4.2), (-5.9, 0.2), (5.9, 0.2))):
        cylinder("PLANT_Bamboo%d_Pot" % i, x, F1, z, 0.22, 0.32, "M_stone_dark", col, seg=12)
        for k in range(5):
            bx = x + (k - 2) * 0.09
            cylinder("PLANT_Bamboo%d_Stalk%d" % (i, k), bx, F1 + 0.30, z + (k % 2) * 0.06, 0.022, 2.2 - k * 0.12, "M_plant", col, seg=6)
            for m in range(3):
                box("PLANT_Bamboo%d_Leaf%d_%d" % (i, k, m), bx + 0.12, F1 + 1.5 + m * 0.35, z, 0.26, 0.02, 0.12, "M_plant", col)
    for side in (-1, 1):
        x = side * 1.9
        box("PLANT_Bonsai%d_Pot" % side, x, F1 + 0.62, 0.2, 0.46, 0.22, 0.34, "M_ceramic", col)
        cylinder("PLANT_Bonsai%d_Trunk" % side, x, F1 + 0.72, 0.2, 0.05, 0.5, "M_wood_walnut", col, seg=6)
        for k in range(3):
            cylinder("PLANT_Bonsai%d_Pad%d" % (side, k), x + (k - 1) * 0.12, F1 + 1.06 + k * 0.08, 0.2, 0.24, 0.1, "M_plant", col, seg=10)

    # ---- 二层陈设 ----
    for i, z in enumerate((-2.6, 0.0, 2.6)):
        x = -(HX - 0.55)
        box("FURN_2F_Table%d" % i, x, F2 + 0.86, z, 0.5, 0.08, 1.8, "M_wood_walnut", col)
        for sz in (-1, 1):
            box("FURN_2F_Table%d_Leg%d" % (i, sz), x, F2 + 0.43, z + sz * 0.8, 0.5, 0.86, 0.08, "M_wood_walnut", col)
        cylinder("FURN_2F_Vase%d" % i, x, F2 + 0.90, z, 0.1, 0.34, "M_ceramic", col, seg=10)
    # 坐榻 + 书案
    box("FURN_2F_Couch", 2.4, F2 + 0.22, 3.4, 2.0, 0.20, 0.8, "M_wood_light", col)
    box("FURN_2F_CouchBack", 2.4, F2 + 0.45, 3.74, 2.0, 0.5, 0.12, "M_wood_walnut", col)
    box("FURN_2F_Desk", -3.6, F2 + 0.78, 3.6, 1.5, 0.08, 0.7, "M_wood_walnut", col)
    for sx in (-1, 1):
        for sz in (-1, 1):
            box("FURN_2F_DeskLeg%d%d" % (sx, sz), -3.6 + sx * 0.66, F2 + 0.39, 3.6 + sz * 0.28, 0.07, 0.78, 0.07, "M_wood_walnut", col)
    # 二层灯笼 + 兰草
    for i, (x, z) in enumerate(((-1.4, 3.9), (1.4, 3.9))):
        cylinder("LANTERN_2F%d_Post" % i, x, F2, z, 0.04, 1.5, "M_gold_brass", col, seg=8)
        box("LANTERN_2F%d_Shade" % i, x, F2 + 1.66, z, 0.36, 0.52, 0.36, "M_lantern_glow", col)
    for side in (-1, 1):
        cylinder("PLANT_2F_Orchid%d_Pot" % side, side * 5.7, F2, -3.9, 0.18, 0.24, "M_ceramic", col, seg=10)
        for k in range(4):
            box("PLANT_2F_Orchid%d_Leaf%d" % (side, k), side * 5.7 + (k - 1.5) * 0.07, F2 + 0.42, -3.9, 0.03, 0.5, 0.1, "M_plant", col)
    return col


# ------------------------------------------------------------------ 锚点


def build_anchors(col):
    log("anchors: 展墙 / 画框 / 相机")
    walls = wall_defs()
    for wall_id, floor, center, rot, size, label in walls:
        empty(
            "GALWALL_" + wall_id,
            center[0],
            center[1],
            center[2],
            {"floor": floor, "width": size[0], "height": size[1], "label": label},
            col,
            rotation_y=rot,
        )

    wall_map = {w[0]: w for w in walls}
    index = {1: 0, 2: 0}
    frames = []
    for wall_id, items in FRAME_PLAN.items():
        wall = wall_map[wall_id]
        for size_w, size_h, u, v, label in items:
            index[wall[1]] += 1
            fid = "FRAME_F%d_%03d" % (wall[1], index[wall[1]])
            x, y, z = wall_point(wall, u, v)
            empty(
                fid,
                x,
                y,
                z,
                {
                    "floor": wall[1],
                    "wall_id": wall_id,
                    "u": round(u, 4),
                    "v": round(v, 4),
                    "frame_size": [size_w, size_h],
                    "label": label,
                },
                col,
                rotation_y=wall[3],
            )
            frames.append(fid)

    # 相机
    cameras = [
        ("front34", (26.0, 13.5, -24.0), (0.0, 6.2, 0.0), 44.0),
        ("front", (0.0, 9.2, -42.0), (0.0, 6.6, 0.0), 42.0),
        ("back", (17.0, 13.0, 36.0), (0.0, 6.0, 0.0), 42.0),
        ("left", (-38.0, 11.0, -6.0), (0.0, 6.2, 0.0), 42.0),
        ("right", (38.0, 11.0, -6.0), (0.0, 6.2, 0.0), 42.0),
        ("top", (17.0, 42.0, -17.0), (0.0, 2.0, 0.0), 44.0),
        ("f1", (0.0, 1.78, -3.3), (0.0, 2.4, 2.9), 16.0),
        ("f2", (-1.4, 6.95, -3.0), (0.9, 6.5, 2.7), 17.0),
        ("ceiling", (0.8, 6.3, -1.4), (0.0, 12.6, 0.5), 18.0),
        ("eave", (11.2, 10.2, -9.4), (5.8, 9.6, -4.4), 50.0),
        ("low34", (19.0, 3.4, -21.0), (0.0, 5.4, 0.0), 44.0),
    ]
    for cam_id, pos, target, lens in cameras:
        cam_data = bpy.data.cameras.new("CAM_" + cam_id)
        cam_data.lens = lens
        cam_data.sensor_width = 36.0
        cam = bpy.data.objects.new("CAM_" + cam_id, cam_data)
        cam.location = (pos[0], -pos[2], pos[1])
        direction = Vector((target[0] - pos[0], -(target[2] - pos[2]), target[1] - pos[1]))
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        cam["target"] = [target[0], target[1], target[2]]
        (col or bpy.context.scene.collection).objects.link(cam)
    return frames


# ------------------------------------------------------------------ 灯光


def build_lighting(scene):
    log("lighting: 天光 + 室内暖光")
    world = bpy.data.worlds.new("HZSky")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputWorld")
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.62, 0.72, 0.86, 1.0)
    bg.inputs["Strength"].default_value = 0.55
    world.node_tree.links.new(bg.outputs["Background"], out.inputs["Surface"])

    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 6.0
    sun_data.angle = math.radians(2.6)
    sun_data.color = (1.0, 0.955, 0.885)
    sun = bpy.data.objects.new("Sun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(48), 0.0, math.radians(-36))

    # 前侧补光（避免正立面全黑）
    for i, (loc, energy) in enumerate((((16.0, 12.0, -14.0), 900.0), ((-16.0, 8.0, -8.0), 380.0))):
        ad = bpy.data.lights.new("Fill%d" % i, "AREA")
        ad.energy = energy
        ad.size = 16.0
        ad.color = (0.86, 0.92, 1.0)
        ob = bpy.data.objects.new("Fill%d" % i, ad)
        scene.collection.objects.link(ob)
        ob.location = (loc[0], loc[2], loc[1])
        direction = Vector((0.0, 0.6, 4.0)) - Vector((loc[0], -loc[2], loc[1]))
        ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    # 室内点光
    for i, (x, y, z, power) in enumerate(
        (
            (0.0, 3.2, 0.2, 260.0),
            (-3.6, 2.6, 1.2, 120.0),
            (3.6, 2.6, 1.2, 120.0),
            (0.0, 7.4, 0.0, 220.0),
            (-3.6, 7.0, 2.0, 110.0),
            (3.6, 7.0, 2.0, 110.0),
            (0.0, 12.0, 0.4, 260.0),
        )
    ):
        pd = bpy.data.lights.new("In%d" % i, "POINT")
        pd.energy = power
        pd.color = (1.0, 0.82, 0.58)
        pd.shadow_soft_size = 0.8
        pd.use_shadow = False
        ob = bpy.data.objects.new("In%d" % i, pd)
        scene.collection.objects.link(ob)
        ob.location = (x, -z, y)


# ------------------------------------------------------------------ 导出


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


def merge_by_category():
    """按「命名类别 + 材质」合并静态网格。

    为什么必须合并：程序化建模会产出几百个小块（窗棂、栏杆柱、家具腿），
    每个对象一次 draw call，网页端帧率会直接崩。合并后同类同材质只有一个对象，
    命名仍保留类别前缀（ROOF_ / BEAM_ / TILE_ …），前端的图层规则与悬挂射线照常工作。

    门扇（DOOR_LeafL/R）与带父级的对象不合并：它们要绕铰链旋转。
    """
    groups: dict[tuple[str, str], list] = {}
    for obj in list(bpy.data.objects):
        if obj.type != "MESH":
            continue
        if obj.parent is not None:
            continue
        if obj.name.startswith("DOOR_Leaf"):
            continue
        category = obj.name.split("_")[0]
        material = obj.data.materials[0].name if obj.data.materials else "none"
        groups.setdefault((category, material), []).append(obj)

    merged = 0
    for (category, material), objects in sorted(groups.items()):
        if not objects:
            continue
        name = "%s_%s" % (category, material.replace("M_", ""))
        join_objects(objects, name)
        merged += 1
    log("merged static meshes into %d batches" % merged)


def export_glb():
    os.makedirs(os.path.dirname(GLB_OUT), exist_ok=True)
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
    log("exported %s (%d bytes)" % (GLB_OUT, os.path.getsize(GLB_OUT)))


def to_web(v):
    return [round(v[0], 4), round(v[2], 4), round(-v[1], 4)]


def write_layout():
    walls = []
    frames = []
    wall_index = {}
    for ob in bpy.data.objects:
        if ob.type != "EMPTY" or not ob.name.startswith("GALWALL_"):
            continue
        props = {k: ob[k] for k in ob.keys() if not k.startswith("_")}
        wid = ob.name.replace("GALWALL_", "")
        # 局部 -Y 指向房间内侧（见 hz_common.empty 的约定说明）
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
        props = {k: ob[k] for k in ob.keys() if not k.startswith("_")}
        parts = ob.name.split("_")
        floor = int(parts[1][1])
        idx = int(parts[2])
        n = ob.matrix_world.to_3x3() @ Vector((0.0, -1.0, 0.0))
        n.normalize()
        size = props.get("frame_size") or [1.0, 0.85]
        wid = props.get("wall_id", "")
        frames.append(
            {
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
            }
        )

    walls.sort(key=lambda w: w["id"])
    frames.sort(key=lambda f: (f["floor"], f["index"]))

    cams = []
    for ob in bpy.data.objects:
        if ob.type != "CAMERA" or not ob.name.startswith("CAM_"):
            continue
        mw = ob.matrix_world
        if "target" in ob.keys():
            # target 存的就是网页坐标，不要再做一次 to_web（会把 y/z 掉个个儿）
            target = Vector([float(v) for v in ob["target"]])
        else:
            fwd = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
            target = mw.translation + fwd * 20.0
            target = Vector((target.x, target.z, -target.y))
        cams.append(
            {
                "id": ob.name.replace("CAM_", "").lower(),
                "position": to_web(mw.translation),
                "target": [round(target[0], 4), round(target[1], 4), round(target[2], 4)],
                "lens": round(ob.data.lens, 1),
                "sensor": round(ob.data.sensor_width, 1),
                "fov": round(math.degrees(2 * math.atan(ob.data.sensor_width / 2 / ob.data.lens)), 2),
            }
        )
    cams.sort(key=lambda c: c["id"])

    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    tris = 0
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
        ob.data.calc_loop_triangles()
        tris += len(ob.data.loop_triangles)

    doc = {
        "schema": 2,
        "generatedBy": "assets/gallery3d/scripts/v6/build_huazhang.py",
        "units": "metre",
        "up": "Y (three.js), converted from Blender Z-up",
        "envelope": {
            "min": [round(lo.x, 3), round(lo.z, 3), round(-hi.y, 3)],
            "max": [round(hi.x, 3), round(hi.z, 3), round(-lo.y, 3)],
            "baseSize": 22.0,
            "baseThickness": round(BASE_TOP, 3),
            "floor1Z": F1,
            "floor2Z": F2,
            "floor1Height": round(F1_H, 3),
            "floor2Height": round(F2_CLEAR, 3),
            "topZ": WALL_TOP,
            "eaveZ": EAVE_LOW,
            "ridgeZ": RIDGE,
            "footprintX": HX * 2,
            "footprintZ": HZ * 2,
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
    log("layout: walls=%d frames=%d cams=%d tris=%d" % (len(walls), len(frames), len(cams), tris))
    return doc


# ------------------------------------------------------------------ 渲染


def render_views(scene, only=None, quick=False):
    os.makedirs(RENDER_OUT, exist_ok=True)
    H.set_engine(scene, "BLENDER_EEVEE", "BLENDER_EEVEE_NEXT")
    scene.render.resolution_x = 960 if quick else 1400
    scene.render.resolution_y = 720 if quick else 1050
    scene.render.resolution_percentage = 100
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
            log("render: missing camera %s" % cam_name)
            continue
        scene.camera = cam
        night = tag.endswith("night")
        if night:
            for ob in bpy.data.objects:
                if ob.type == "LIGHT" and ob.name.startswith("In"):
                    ob.data.energy *= 2.4
                if ob.type == "LIGHT" and ob.name.startswith("Fill"):
                    ob.data.energy *= 0.35
        scene.render.filepath = os.path.join(RENDER_OUT, tag + ".png")
        bpy.ops.render.render(write_still=True)
        log("rendered %s" % scene.render.filepath)
        if night:
            for ob in bpy.data.objects:
                if ob.type == "LIGHT" and ob.name.startswith("In"):
                    ob.data.energy /= 2.4
                if ob.type == "LIGHT" and ob.name.startswith("Fill"):
                    ob.data.energy /= 0.35


# ------------------------------------------------------------------ 主流程


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = argv[argv.index("--stage") + 1] if "--stage" in argv else "all"
    quick = "--quick" in argv
    no_render = "--no-render" in argv
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None

    open(H.LOG_PATH, "w", encoding="utf-8").close()
    log("=== 华章新馆 build: stage=%s quick=%s no_render=%s" % (stage, quick, no_render))

    scene = H.reset_scene()
    build_lighting(scene)

    c_site = H.collection("HZ_SITE")
    c_shell = H.collection("HZ_SHELL")
    c_roof = H.collection("HZ_ROOF")
    c_interior = H.collection("HZ_INTERIOR")
    c_anchor = H.collection("HZ_ANCHOR")

    build_site(c_site)
    build_shell(c_shell)
    build_stair(c_shell)
    build_doors(c_shell)
    if stage != "mass":
        build_interior(c_interior)
        build_roof_details(c_roof)
    build_roof(c_roof)
    build_anchors(c_anchor)

    apply_modifiers()
    merge_by_category()
    recalc_normals()

    counts = {"MESH": 0, "EMPTY": 0, "CAMERA": 0}
    tris = 0
    for ob in bpy.data.objects:
        counts[ob.type] = counts.get(ob.type, 0) + 1
        if ob.type == "MESH":
            ob.data.calc_loop_triangles()
            tris += len(ob.data.loop_triangles)
    log("objects=%s triangles=%d" % (counts, tris))

    os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
    log("saved " + BLEND_OUT)

    export_glb()
    write_layout()

    os.makedirs(os.path.dirname(FRONT_GLB), exist_ok=True)
    with open(GLB_OUT, "rb") as src, open(FRONT_GLB, "wb") as dst:
        dst.write(src.read())
    log("copied glb -> " + FRONT_GLB)

    if not no_render:
        render_views(scene, only=only, quick=quick)
    log("=== done")


if __name__ == "__main__":
    main()