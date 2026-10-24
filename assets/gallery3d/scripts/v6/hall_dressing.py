"""华章新馆 · 室内陈设与装修（固定摆设 + 画框拓位）

与 hall_huazhang.py 分开的原因：建筑结构（柱网/斗拱/屋面）和室内软装是两件
不同的事，前者一改就要重跑全部构件，后者可以单独迭代。这里只做：

    装修   墙裙 / 踢脚 / 平綦天花 / 地面拼花 / 门内匾额 / 挂屏 / 对联
    家具   条案 / 圈椅 / 茶几 / 书案 / 琴桌 / 香几 / 衣架 / 盆架 / 多宝格 / 坐榻
    陈设   青铜鼎 / 香炉 / 瓷瓶 / 漆盒 / 书卷 / 茶具 / 盆景 / 兰草 / 竹 / 荷花缸
    画框   33 个固定位（一层 17、二层 16），坐标写死在前端契约里

所有摆设都要求「落地或贴墙」：桌案的脚要落到地面，架上器物要落在格板上，
不允许悬空——这一条在导出的 layout 里也体现为画框锚点必须落在展墙矩形内。
"""

from __future__ import annotations

import math

import hz_kit as K

# 与 hall_huazhang.py 保持同一套标高（这里只读，不改结构）
BASE_TOP = 1.20
FY1 = BASE_TOP
COL_H1 = 5.40
FY2 = FY1 + COL_H1 + 0.55
COL_H2 = 3.40
HALF_X1 = 6.00
HALF_Z1 = 5.10
WALL_T = 0.36
IN_X = HALF_X1 - WALL_T / 2   # 墙中心
IN_Z = HALF_Z1 - WALL_T / 2
# 展墙锚点必须放在「内表面」而不是墙中心：
# 前端把画框贴在墙面 +0.06，若锚点在墙中心，0.36 厚的墙会把整块画框埋进去。
FACE_X = HALF_X1 - WALL_T     # 内表面 x
FACE_Z = HALF_Z1 - WALL_T     # 内表面 z
PIER_FACE = 2.20              # 独立展墙（0.20 厚）朝房间的一面

# ---------------------------------------------------------------- 展墙（15 面）

WALLS2 = [
    # 一层
    ("f1-back", 1, (0.0, FY1 + 2.30, FACE_Z), math.pi, (5.20, 4.40), "一层 · 后墙"),
    ("f1-left-rear", 1, (-FACE_X, FY1 + 2.30, 2.60), math.pi / 2, (4.20, 4.40), "一层 · 左墙后段"),
    ("f1-left-mid", 1, (-FACE_X, FY1 + 2.30, -1.40), math.pi / 2, (3.60, 4.40), "一层 · 左墙中段"),
    ("f1-right-rear", 1, (FACE_X, FY1 + 2.30, 2.60), -math.pi / 2, (4.20, 4.40), "一层 · 右墙后段"),
    ("f1-right-mid", 1, (FACE_X, FY1 + 2.30, -1.40), -math.pi / 2, (3.60, 4.40), "一层 · 右墙中段"),
    ("f1-pier-left", 1, (-PIER_FACE, FY1 + 1.65, -0.90), math.pi / 2, (1.90, 3.10), "一层 · 独立展墙 左"),
    ("f1-pier-right", 1, (PIER_FACE, FY1 + 1.65, -0.90), -math.pi / 2, (1.90, 3.10), "一层 · 独立展墙 右"),
    ("f1-front-left", 1, (-4.10, FY1 + 3.55, -FACE_Z), 0.0, (2.80, 1.50), "一层 · 前墙左次间"),
    ("f1-front-right", 1, (4.10, FY1 + 3.55, -FACE_Z), 0.0, (2.80, 1.50), "一层 · 前墙右次间"),
    # 二层
    ("f2-back", 2, (0.0, FY2 + 1.70, FACE_Z), math.pi, (5.20, 3.30), "二层 · 后墙"),
    ("f2-left", 2, (-FACE_X, FY2 + 1.70, 0.60), math.pi / 2, (7.00, 3.30), "二层 · 左墙"),
    ("f2-right", 2, (FACE_X, FY2 + 1.70, 0.60), -math.pi / 2, (7.00, 3.30), "二层 · 右墙"),
    ("f2-front", 2, (0.0, FY2 + 1.70, -FACE_Z), 0.0, (5.20, 3.30), "二层 · 前墙"),
    ("f2-left-gable", 2, (-FACE_X, FY2 + 1.70, -3.60), math.pi / 2, (2.20, 3.30), "二层 · 左山墙"),
    ("f2-right-gable", 2, (FACE_X, FY2 + 1.70, -3.60), -math.pi / 2, (2.20, 3.30), "二层 · 右山墙"),
]

FRAME_PLAN2 = {
    "f1-back": [
        (1.15, 1.00, 0.20, 0.50, "一层 · 后墙 · 左"),
        (1.55, 1.15, 0.50, 0.50, "一层 · 后墙 · 中"),
        (1.15, 1.00, 0.80, 0.50, "一层 · 后墙 · 右"),
    ],
    "f1-left-rear": [
        (0.95, 1.20, 0.26, 0.50, "一层 · 左墙后段 · 后"),
        (1.30, 1.05, 0.50, 0.50, "一层 · 左墙后段 · 中"),
        (0.95, 1.20, 0.74, 0.50, "一层 · 左墙后段 · 前"),
    ],
    "f1-left-mid": [
        (1.50, 0.92, 0.28, 0.52, "一层 · 左墙中段 · 横幅"),
        (0.92, 1.18, 0.74, 0.52, "一层 · 左墙中段 · 立轴"),
    ],
    "f1-right-rear": [
        (0.95, 1.20, 0.26, 0.50, "一层 · 右墙后段 · 后"),
        (1.30, 1.05, 0.50, 0.50, "一层 · 右墙后段 · 中"),
        (0.95, 1.20, 0.74, 0.50, "一层 · 右墙后段 · 前"),
    ],
    "f1-right-mid": [
        (0.92, 1.18, 0.26, 0.52, "一层 · 右墙中段 · 立轴"),
        (1.50, 0.92, 0.72, 0.52, "一层 · 右墙中段 · 横幅"),
    ],
    "f1-pier-left": [(1.30, 1.55, 0.50, 0.54, "一层 · 独立展墙 · 左")],
    "f1-pier-right": [(1.30, 1.55, 0.50, 0.54, "一层 · 独立展墙 · 右")],
    "f1-front-left": [(1.45, 0.78, 0.50, 0.52, "一层 · 前墙左次间")],
    "f1-front-right": [(1.45, 0.78, 0.50, 0.52, "一层 · 前墙右次间")],
    "f2-back": [
        (0.85, 1.10, 0.20, 0.52, "二层 · 后墙 · 左"),
        (1.35, 0.95, 0.50, 0.52, "二层 · 后墙 · 中"),
        (0.85, 1.10, 0.80, 0.52, "二层 · 后墙 · 右"),
    ],
    "f2-left": [
        (0.92, 1.15, 0.16, 0.52, "二层 · 左墙 · 一"),
        (1.30, 0.95, 0.38, 0.52, "二层 · 左墙 · 二"),
        (0.92, 1.15, 0.62, 0.52, "二层 · 左墙 · 三"),
        (1.30, 0.95, 0.85, 0.52, "二层 · 左墙 · 四"),
    ],
    "f2-right": [
        (0.92, 1.15, 0.16, 0.52, "二层 · 右墙 · 一"),
        (1.30, 0.95, 0.38, 0.52, "二层 · 右墙 · 二"),
        (0.92, 1.15, 0.62, 0.52, "二层 · 右墙 · 三"),
        (1.30, 0.95, 0.85, 0.52, "二层 · 右墙 · 四"),
    ],
    "f2-front": [
        (0.88, 1.12, 0.20, 0.52, "二层 · 前墙 · 左"),
        (1.35, 1.00, 0.50, 0.52, "二层 · 前墙 · 中"),
        (0.88, 1.12, 0.80, 0.52, "二层 · 前墙 · 右"),
    ],
    "f2-left-gable": [(1.30, 1.05, 0.50, 0.52, "二层 · 左山墙")],
    "f2-right-gable": [(1.30, 1.05, 0.50, 0.52, "二层 · 右山墙")],
}


# ---------------------------------------------------------------- 小件


def vase(col, name, x, y, z, h=0.42, r=0.10, material="M_ceramic"):
    """瓶花：瓶身 + 瓶颈 + 三枝花。"""
    K.cyl(name + "_Body", (x, y, z), r, h * 0.55, material, col, seg=12, r_top=r * 0.55)
    K.cyl(name + "_Neck", (x, y + h * 0.55, z), r * 0.55, h * 0.18, material, col, seg=10, r_top=r * 0.72)
    for k in range(3):
        a = k * 2.094
        K.box(
            "%s_Branch%d" % (name, k),
            (x + math.cos(a) * 0.10, y + h * 0.82, z + math.sin(a) * 0.10),
            (0.02, h * 0.30, 0.02),
            "M_plant",
            col,
            rot=(math.sin(a) * 0.35, 0.0, math.cos(a) * 0.35),
        )
        K.box(
            "%s_Bloom%d" % (name, k),
            (x + math.cos(a) * 0.16, y + h * 1.02, z + math.sin(a) * 0.16),
            (0.10, 0.05, 0.10),
            "M_lacquer_red",
            col,
        )


def censer(col, name, x, y, z, scale=1.0):
    """香炉：三足 + 炉身 + 双耳 + 盖。"""
    s = scale
    for k in range(3):
        a = k * 2.094
        K.cyl("%s_Foot%d" % (name, k), (x + math.cos(a) * 0.11 * s, y, z + math.sin(a) * 0.11 * s),
              0.03 * s, 0.09 * s, "M_bronze", col, seg=6)
    K.lathe(name + "_Body", [(0.0, 0.0), (0.16 * s, 0.02), (0.19 * s, 0.12 * s), (0.17 * s, 0.24 * s),
                             (0.0, 0.26 * s)],
            (x, y + 0.08 * s, z), "M_bronze", col, seg=14)
    for side in (-1, 1):
        K.box("%s_Ear%d" % (name, side), (x + side * 0.17 * s, y + 0.26 * s, z),
              (0.04 * s, 0.12 * s, 0.06 * s), "M_bronze", col)
    K.lathe(name + "_Lid", [(0.0, 0.0), (0.16 * s, 0.0), (0.10 * s, 0.07 * s), (0.0, 0.10 * s)],
            (x, y + 0.34 * s, z), "M_bronze", col, seg=12)


def ding(col, name, x, y, z, scale=1.0):
    """青铜鼎：方座 + 鼎身 + 双耳 + 四足，展台上的主陈设。"""
    s = scale
    K.box(name + "_Base", (x, y + 0.04 * s, z), (0.56 * s, 0.08 * s, 0.44 * s), "M_stone_dark", col)
    for sx in (-1, 1):
        for sz in (-1, 1):
            K.box("%s_Leg%d%d" % (name, sx, sz), (x + sx * 0.20 * s, y + 0.18 * s, z + sz * 0.15 * s),
                  (0.07 * s, 0.22 * s, 0.07 * s), "M_bronze", col)
    K.box(name + "_Body", (x, y + 0.36 * s, z), (0.50 * s, 0.26 * s, 0.38 * s), "M_bronze", col)
    K.box(name + "_Lip", (x, y + 0.51 * s, z), (0.56 * s, 0.05 * s, 0.44 * s), "M_bronze", col)
    for sx in (-1, 1):
        K.box("%s_Ear%d" % (name, sx), (x + sx * 0.24 * s, y + 0.60 * s, z),
              (0.06 * s, 0.18 * s, 0.26 * s), "M_bronze", col)


def scroll(col, name, x, y, z, length=0.42, rot=0.0):
    """卷轴：案上或架上的横卷。"""
    K.cyl(name + "_Body", (x - length / 2, y, z), 0.035, length, "M_paper", col, seg=8, axis="x")
    for side in (-1, 1):
        K.cyl("%s_End%d" % (name, side), (x + side * length / 2 - 0.02, y, z), 0.045, 0.04,
              "M_wood_dark", col, seg=8, axis="x")


def tea_set(col, name, x, y, z):
    """茶具：托盘 + 四盏 + 壶。"""
    K.box(name + "_Tray", (x, y + 0.02, z), (0.44, 0.04, 0.30), "M_wood_dark", col)
    for i in range(4):
        tx = x - 0.14 + (i % 2) * 0.28
        tz = z - 0.08 + (i // 2) * 0.16
        K.cyl("%s_Cup%d" % (name, i), (tx, y + 0.05, tz), 0.035, 0.06, "M_ceramic", col, seg=8)
    K.cyl(name + "_Pot", (x, y + 0.05, z), 0.07, 0.10, "M_ceramic", col, seg=10)


def hanging_scroll(col, name, x, y, z, w=0.55, h=1.30, facing=0.0):
    """挂屏 / 对联所用的立轴：双轴 + 绢面 + 天头地脚。"""
    K.box(name + "_Silk", (x, y, z + 0.03), (w, h, 0.02), "M_paper", col, rot=(0.0, 0.0, facing))
    for dy in (1, -1):
        K.box("%s_Rod%d" % (name, dy), (x, y + dy * (h / 2 + 0.04), z + 0.05), (w + 0.10, 0.06, 0.06),
              "M_wood_dark", col, rot=(0.0, 0.0, facing))
    K.box(name + "_Frame", (x, y, z + 0.02), (w + 0.08, h + 0.10, 0.01), "M_lacquer_red", col,
          rot=(0.0, 0.0, facing))


# ---------------------------------------------------------------- 装修


def build_finish(col):
    K.log("装修：墙裙 / 平綦天花 / 地面拼花 / 匾额")
    # ---- 墙裙：沿内墙一圈木护墙板（高 0.92）----
    skirt_h = 0.92
    for side in (-1, 1):
        K.box("TRIM_SkirtB%d" % side, (0.0, FY1 + skirt_h / 2, side * (IN_Z - 0.03)),
              (IN_X * 2 - 0.1, skirt_h, 0.05), "M_wood_beam", col)
        K.box("TRIM_SkirtS%d" % side, (side * (IN_X - 0.03), FY1 + skirt_h / 2, 0.0),
              (0.05, skirt_h, IN_Z * 2 - 0.1), "M_wood_beam", col)
        K.box("TRIM_SkirtCap%d" % side, (0.0, FY1 + skirt_h + 0.03, side * (IN_Z - 0.03)),
              (IN_X * 2 - 0.1, 0.06, 0.08), "M_wood_dark", col)
        K.box("TRIM_SkirtCapS%d" % side, (side * (IN_X - 0.03), FY1 + skirt_h + 0.03, 0.0),
              (0.08, 0.06, IN_Z * 2 - 0.1), "M_wood_dark", col)
    # 二层墙裙
    for side in (-1, 1):
        K.box("TRIM_SkirtB2_%d" % side, (0.0, FY2 + skirt_h / 2, side * (IN_Z - 0.03)),
              (IN_X * 2 - 0.1, skirt_h, 0.05), "M_wood_beam", col)

    # ---- 平綦天花：二层楼板底（一层）与二层顶 ----
    def grid_ceiling(tag, y, x0, x1, z0, z1, step=0.95):
        nx = max(1, int((x1 - x0) / step))
        nz = max(1, int((z1 - z0) / step))
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            K.box("%s_X%d" % (tag, i), (x, y, (z0 + z1) / 2), (0.07, 0.07, z1 - z0), "M_wood_dark", col)
        for j in range(nz + 1):
            z = z0 + (z1 - z0) * j / nz
            K.box("%s_Z%d" % (tag, j), ((x0 + x1) / 2, y, z), (x1 - x0, 0.07, 0.07), "M_wood_dark", col)

    # 一层：楼板底做天花，但中庭挑空区（x±3.4 / z±2.4）留空
    for sx, (xa, xb) in enumerate(((-IN_X + 0.05, -3.40), (3.40, IN_X - 0.05))):
        grid_ceiling("COFFER_1F_L%d" % sx, FY2 - 0.30, xa, xb, -IN_Z + 0.05, IN_Z - 0.05)
    for sz, (za, zb) in enumerate(((-IN_Z + 0.05, -2.40), (2.40, IN_Z - 0.05))):
        grid_ceiling("COFFER_1F_F%d" % sz, FY2 - 0.30, -3.40, 3.40, za, zb)
    # 二层：满铺（先加一层顶板，否则格眼里会直接看到瓦背）
    K.box("COFFER_2F_Slab", (0.0, FY2 + COL_H2 - 0.04, 0.0), (IN_X * 2 - 0.1, 0.05, IN_Z * 2 - 0.1),
          "M_wall_plaster", col)
    grid_ceiling("COFFER_2F", FY2 + COL_H2 - 0.10, -IN_X + 0.05, IN_X - 0.05, -IN_Z + 0.05, IN_Z - 0.05)

    # ---- 地面拼花：中央大方砖 + 四周深色边线 ----
    K.box("PAVE_Center", (0.0, FY1 + 0.012, 0.30), (5.20, 0.02, 5.20), "M_floor_stone", col)
    for side in (-1, 1):
        K.box("PAVE_EdgeX%d" % side, (side * 3.10, FY1 + 0.012, 0.30), (0.30, 0.02, 6.90),
              "M_stone_dark", col)
        K.box("PAVE_EdgeZ%d" % side, (0.0, FY1 + 0.012, 0.30 + side * 3.10), (6.90, 0.02, 0.30),
              "M_stone_dark", col)

    # ---- 门内匾额 ----
    K.box("PLAQUE_Inner", (0.0, FY1 + 4.55, -(IN_Z - 0.10)), (2.60, 0.80, 0.10), "M_wood_dark", col)
    K.box("PLAQUE_InnerGold", (0.0, FY1 + 4.55, -(IN_Z - 0.16)), (2.75, 0.95, 0.05), "M_gold", col)

    # ---- 挂屏与对联 ----
    for side in (-1, 1):
        hanging_scroll(col, "SCROLL_L%d" % side, side * (IN_X - 0.10), FY1 + 2.55, 2.60,
                       0.52, 1.30, facing=math.pi / 2)
    for side in (-1, 1):
        hanging_scroll(col, "COUPLET_%d" % side, side * 1.90, FY1 + 2.55, IN_Z - 0.10,
                       0.34, 1.90, facing=0.0)
    return col


# ---------------------------------------------------------------- 一层陈设


def build_interior(col):
    K.log("室内：展台 / 展柜 / 家具 / 陈设")
    # ---- 中央展台（石质须弥座式基座 + 铜包边）----
    K.box("DISPLAY_Main", (0.0, FY1 + 0.30, 0.60), (2.80, 0.60, 1.60), "M_stone_dark", col)
    K.box("DISPLAY_Belt", (0.0, FY1 + 0.44, 0.60), (2.92, 0.10, 1.72), "M_gold", col)
    K.box("DISPLAY_Top", (0.0, FY1 + 0.62, 0.60), (2.70, 0.05, 1.50), "M_floor_stone", col)
    ding(col, "DISPLAY_DingL", -0.80, FY1 + 0.64, 0.60, 1.0)
    ding(col, "DISPLAY_DingR", 0.80, FY1 + 0.64, 0.60, 1.0)
    censer(col, "DISPLAY_Censer", 0.0, FY1 + 0.64, 0.05, 1.15)
    vase(col, "DISPLAY_Vase", 0.0, FY1 + 0.64, 1.10, 0.46, 0.11)

    # ---- 独立展墙 ----
    for side in (-1, 1):
        K.box("DISPLAY_Pier%d" % side, (side * 2.30, FY1 + 1.65, -0.90), (0.20, 3.10, 1.90),
              "M_wall_plaster", col)
        K.box("DISPLAY_PierBase%d" % side, (side * 2.30, FY1 + 0.10, -0.90), (0.46, 0.20, 2.16),
              "M_stone_dark", col)
        K.box("DISPLAY_PierCap%d" % side, (side * 2.30, FY1 + 3.24, -0.90), (0.34, 0.16, 2.10),
              "M_wood_beam", col)
        # 展墙两侧的射灯支架
        for zz in (-1.60, -0.20):
            K.cyl("DISPLAY_LampPost%d_%d" % (side, int(zz * 10)),
                  (side * 2.30, FY1 + 3.30, zz), 0.035, 0.42, "M_gold", col, seg=8)
            K.box("DISPLAY_LampHead%d_%d" % (side, int(zz * 10)),
                  (side * 2.30, FY1 + 3.76, zz), (0.22, 0.10, 0.22), "M_gold", col)

    # ---- 通长玻璃展柜（左右各三组）----
    cid = 0
    for side in (-1, 1):
        for z in (-2.60, 0.20, 2.90):
            x = side * (HALF_X1 - 0.85)
            K.box("CABINET_%d_Plinth" % cid, (x, FY1 + 0.14, z), (0.70, 0.28, 1.55), "M_stone_dark", col)
            K.box("CABINET_%d_Body" % cid, (x, FY1 + 0.58, z), (0.60, 0.62, 1.45), "M_wood_dark", col)
            K.box("CABINET_%d_Top" % cid, (x, FY1 + 0.93, z), (0.68, 0.06, 1.52), "M_gold", col)
            K.box("CABINET_%d_Glass" % cid, (x, FY1 + 1.36, z), (0.54, 0.80, 1.40), "M_glass", col)
            K.box("CABINET_%d_Frame" % cid, (x, FY1 + 1.78, z), (0.60, 0.06, 1.46), "M_gold", col)
            for j in range(3):
                K.cyl("CABINET_%d_Vase%d" % (cid, j), (x, FY1 + 0.97, z - 0.44 + j * 0.44),
                      0.10, 0.28, "M_ceramic", col, seg=10)
            cid += 1

    # ---- 多宝格（左右靠后墙）----
    for side in (-1, 1):
        x = side * (HALF_X1 - 0.55)
        K.box("FURN_Shelf%d_Base" % side, (x, FY1 + 0.16, 3.80), (0.52, 0.32, 2.30), "M_wood_dark", col)
        K.box("FURN_Shelf%d_Back" % side, (x, FY1 + 1.45, 3.80), (0.12, 2.60, 2.20), "M_wood_dark", col)
        for j in range(4):
            K.box("FURN_Shelf%d_S%d" % (side, j), (x - side * 0.22, FY1 + 1.45, 3.80 - 1.10 + j * 0.73),
                  (0.44, 2.60, 0.06), "M_wood_beam", col)
        for j in range(1, 5):
            K.box("FURN_Shelf%d_B%d" % (side, j), (x - side * 0.22, FY1 + 0.32 + j * 0.62, 3.80),
                  (0.48, 0.06, 2.20), "M_wood_light", col)
        # 格内器物：瓷瓶 / 漆盒 / 书卷
        for j in range(4):
            zz = 3.80 - 0.72 + (j % 2) * 0.86
            yy = FY1 + 0.38 + j * 0.62
            if j % 3 == 0:
                vase(col, "FURN_Shelf%d_V%d" % (side, j), x - side * 0.22, yy, zz, 0.34, 0.09)
            elif j % 3 == 1:
                K.box("FURN_Shelf%d_Box%d" % (side, j), (x - side * 0.22, yy + 0.08, zz),
                      (0.26, 0.16, 0.20), "M_lacquer_red", col)
            else:
                scroll(col, "FURN_Shelf%d_Sc%d" % (side, j), x - side * 0.22, yy + 0.06, zz, 0.36)

    # ---- 条案 + 圈椅 + 茶几（左右次间）----
    for side in (-1, 1):
        x = side * 4.30
        K.box("FURN_Table%d_Top" % side, (x, FY1 + 0.86, -0.40), (0.58, 0.09, 2.30), "M_wood_beam", col)
        K.box("FURN_Table%d_Apron" % side, (x, FY1 + 0.76, -0.40), (0.52, 0.12, 2.24), "M_wood_dark", col)
        for sx in (-1, 1):
            for sz in (-1, 1):
                K.box("FURN_Table%d_L%d%d" % (side, sx, sz),
                      (x + sx * 0.21, FY1 + 0.43, -0.40 + sz * 1.0), (0.09, 0.86, 0.09),
                      "M_wood_beam", col)
        vase(col, "FURN_Table%d_Vase" % side, x, FY1 + 0.90, 0.10, 0.44, 0.11)
        censer(col, "FURN_Table%d_Censer" % side, x, FY1 + 0.90, -0.90, 1.0)
        K.box("FURN_Table%d_Box" % side, (x, FY1 + 0.94, 0.70), (0.24, 0.10, 0.30), "M_lacquer_red", col)
        # 圈椅两把 + 茶几
        for j, cz in enumerate((-1.50, 0.60)):
            cx = side * 3.20
            K.box("FURN_Chair%d_%d_Seat" % (side, j), (cx, FY1 + 0.46, cz), (0.60, 0.08, 0.56), "M_wood_light", col)
            K.box("FURN_Chair%d_%d_Back" % (side, j), (cx - side * 0.26, FY1 + 0.80, cz), (0.07, 0.70, 0.54),
                  "M_wood_light", col)
            K.box("FURN_Chair%d_%d_Arm" % (side, j), (cx - side * 0.02, FY1 + 0.66, cz), (0.52, 0.06, 0.60),
                  "M_wood_light", col)
            for sx in (-1, 1):
                for sz in (-1, 1):
                    K.box("FURN_Chair%d_%d_L%d%d" % (side, j, sx, sz),
                          (cx + sx * 0.25, FY1 + 0.23, cz + sz * 0.23), (0.05, 0.46, 0.05),
                          "M_wood_beam", col)
        K.box("FURN_TeaTable%d" % side, (side * 3.20, FY1 + 0.52, -0.45), (0.56, 0.07, 0.86),
              "M_wood_light", col)
        for sz in (-1, 1):
            K.box("FURN_TeaTable%d_L%d" % (side, sz), (side * 3.20, FY1 + 0.26, -0.45 + sz * 0.34),
                  (0.46, 0.52, 0.06), "M_wood_beam", col)
        tea_set(col, "FURN_Tea%d" % side, side * 3.20, FY1 + 0.55, -0.45)

    # ---- 后厅：书案 / 琴桌 / 香几 / 衣架 / 盆架 ----
    K.box("FURN_Desk_Top", (-3.80, FY1 + 0.82, 3.90), (1.60, 0.09, 0.74), "M_wood_beam", col)
    for sx in (-1, 1):
        for sz in (-1, 1):
            K.box("FURN_Desk_L%d%d" % (sx, sz), (-3.80 + sx * 0.72, FY1 + 0.41, 3.90 + sz * 0.30),
                  (0.07, 0.82, 0.07), "M_wood_beam", col)
    scroll(col, "FURN_Desk_Scroll", -3.90, FY1 + 0.90, 3.86, 0.50)
    K.box("FURN_Desk_Ink", (-3.30, FY1 + 0.89, 3.90), (0.22, 0.05, 0.16), "M_stone_dark", col)
    K.box("FURN_Desk_Brush", (-3.10, FY1 + 0.92, 3.86), (0.04, 0.04, 0.22), "M_wood_dark", col)
    K.cyl("FURN_Desk_Vase", (-4.20, FY1 + 0.88, 4.05), 0.07, 0.22, "M_ceramic", col, seg=10)

    K.box("FURN_Qin_Top", (3.60, FY1 + 0.76, 3.90), (1.20, 0.08, 0.46), "M_wood_beam", col)
    for sx in (-1, 1):
        K.box("FURN_Qin_L%d" % sx, (3.60 + sx * 0.50, FY1 + 0.38, 3.90), (0.08, 0.76, 0.40), "M_wood_beam", col)
    K.box("FURN_Qin_Body", (3.60, FY1 + 0.84, 3.90), (1.10, 0.06, 0.20), "M_wood_dark", col)

    for i, x in enumerate((-1.10, 1.10)):
        K.box("FURN_Incense%d_Top" % i, (x, FY1 + 0.74, 4.20), (0.46, 0.07, 0.46), "M_wood_light", col)
        for sx in (-1, 1):
            for sz in (-1, 1):
                K.box("FURN_Incense%d_L%d%d" % (i, sx, sz), (x + sx * 0.18, FY1 + 0.37, 4.20 + sz * 0.18),
                      (0.05, 0.74, 0.05), "M_wood_light", col)
        censer(col, "FURN_Incense%d_Censer" % i, x, FY1 + 0.78, 4.20, 0.85)

    # 衣架 / 盆架
    K.box("FURN_Cloth_Top", (-5.30, FY1 + 1.86, 2.70), (0.10, 0.10, 0.90), "M_wood_dark", col)
    for sz in (-1, 1):
        K.box("FURN_Cloth_L%d" % sz, (-5.30, FY1 + 0.93, 2.70 + sz * 0.36), (0.08, 1.86, 0.08),
              "M_wood_dark", col)
    K.box("FURN_Cloth_Silk", (-5.30, FY1 + 1.60, 2.70), (0.04, 0.50, 0.70), "M_fabric", col)

    K.cyl("FURN_Basin_Leg", (5.30, FY1, 2.70), 0.06, 0.60, "M_wood_dark", col, seg=8)
    K.lathe("FURN_Basin", [(0.0, 0.0), (0.26, 0.02), (0.30, 0.14), (0.24, 0.20), (0.0, 0.20)],
            (5.30, FY1 + 0.60, 2.70), "M_ceramic", col, seg=14)

    # ---- 屏风（左右后角）----
    for side in (-1, 1):
        x = side * 5.00
        for j in range(3):
            K.box("SCREEN%d_%d" % (side, j), (x, FY1 + 1.20, -3.60 + (j - 1) * 0.60),
                  (0.07, 2.30, 0.58), "M_fabric", col)
            K.box("SCREEN%d_%d_F" % (side, j), (x + side * 0.02, FY1 + 1.20, -3.60 + (j - 1) * 0.60),
                  (0.09, 2.40, 0.64), "M_lacquer_red", col)

    # ---- 宫灯 / 地毯 / 植物 ----
    for i, (x, z) in enumerate(((-1.80, 2.60), (1.80, 2.60), (-1.80, -3.10), (1.80, -3.10))):
        K.cyl("LANTERN%d_Base" % i, (x, FY1, z), 0.20, 0.10, "M_stone_dark", col, seg=12)
        K.cyl("LANTERN%d_Post" % i, (x, FY1 + 0.10, z), 0.05, 2.00, "M_gold", col, seg=8)
        K.box("LANTERN%d_Shade" % i, (x, FY1 + 2.30, z), (0.44, 0.64, 0.44), "M_lantern", col)
        for j in range(4):
            a = j * math.pi / 2
            K.box("LANTERN%d_Rib%d" % (i, j), (x + math.cos(a) * 0.22, FY1 + 2.30, z + math.sin(a) * 0.22),
                  (0.03, 0.64, 0.03), "M_wood_dark", col)
        K.box("LANTERN%d_Cap" % i, (x, FY1 + 2.68, z), (0.54, 0.08, 0.54), "M_wood_dark", col)
        K.box("LANTERN%d_Top" % i, (x, FY1 + 2.76, z), (0.30, 0.08, 0.30), "M_gold", col)

    K.box("CARPET_Main", (0.0, FY1 + 0.02, 0.60), (5.40, 0.02, 4.00), "M_fabric", col)
    K.box("CARPET_MainBorder", (0.0, FY1 + 0.022, 0.60), (5.60, 0.02, 4.20), "M_lacquer_red", col)
    for side in (-1, 1):
        K.box("CARPET_Side%d" % side, (side * 3.60, FY1 + 0.02, -2.60), (2.20, 0.02, 1.60), "M_fabric", col)

    for i, (x, z) in enumerate(((-5.55, -4.30), (5.55, -4.30), (-5.55, 0.60), (5.55, 0.60))):
        K.cyl("PLANT_Bamboo%d_Pot" % i, (x, FY1, z), 0.24, 0.34, "M_stone_dark", col, seg=12)
        for j in range(5):
            K.cyl("PLANT_Bamboo%d_S%d" % (i, j), (x + (j - 2) * 0.09, FY1 + 0.32, z),
                  0.022, 2.4 - j * 0.10, "M_plant", col, seg=6)
            for m in range(3):
                K.box("PLANT_Bamboo%d_L%d_%d" % (i, j, m),
                      (x + (j - 2) * 0.09 + 0.14, FY1 + 1.50 + m * 0.36, z),
                      (0.30, 0.02, 0.12), "M_plant", col)
    for side in (-1, 1):
        K.box("PLANT_Bonsai%d_Pot" % side, (side * 1.90, FY1 + 0.64, 1.90), (0.46, 0.22, 0.34),
              "M_ceramic", col)
        K.cyl("PLANT_Bonsai%d_T" % side, (side * 1.90, FY1 + 0.74, 1.90), 0.05, 0.50, "M_wood_dark", col, seg=6)
        for k in range(3):
            K.cyl("PLANT_Bonsai%d_P%d" % (side, k), (side * 1.90 + (k - 1) * 0.12, FY1 + 1.10 + k * 0.08, 1.90),
                  0.22, 0.10, "M_plant", col, seg=10)
    # 荷花缸
    K.lathe("PLANT_Lotus_Pot", [(0.0, 0.0), (0.34, 0.04), (0.40, 0.36), (0.36, 0.40), (0.0, 0.40)],
            (0.0, FY1, 4.30), "M_ceramic", col, seg=16)
    K.cyl("PLANT_Lotus_Water", (0.0, FY1 + 0.34, 4.30), 0.33, 0.02, "M_water", col, seg=14)
    for k in range(3):
        a = k * 2.094
        K.cyl("PLANT_Lotus_Stem%d" % k, (math.cos(a) * 0.14, FY1 + 0.36, 4.30 + math.sin(a) * 0.14),
              0.012, 0.40, "M_plant", col, seg=6)
        K.cyl("PLANT_Lotus_Leaf%d" % k, (math.cos(a) * 0.14, FY1 + 0.74, 4.30 + math.sin(a) * 0.14),
              0.14, 0.03, "M_plant", col, seg=10)
    # 兰草
    for side in (-1, 1):
        K.cyl("PLANT_Orchid%d_Pot" % side, (side * 4.90, FY1 + 0.02, 4.30), 0.16, 0.24, "M_ceramic", col, seg=10)
        for k in range(5):
            K.box("PLANT_Orchid%d_L%d" % (side, k), (side * 4.90 + (k - 2) * 0.05, FY1 + 0.42, 4.30),
                  (0.03, 0.46, 0.10), "M_plant", col,
                  rot=(0.0, 0.0, math.radians(-18 + k * 9)))

    # ---- 二层陈设 ----
    for i, z in enumerate((-2.60, 0.0, 2.60)):
        x = -(HALF_X1 - 0.60)
        K.box("FURN_2F_T%d_Top" % i, (x, FY2 + 0.86, z), (0.50, 0.09, 1.80), "M_wood_beam", col)
        for sz in (-1, 1):
            K.box("FURN_2F_T%d_L%d" % (i, sz), (x, FY2 + 0.43, z + sz * 0.80), (0.50, 0.86, 0.08),
                  "M_wood_beam", col)
        vase(col, "FURN_2F_V%d" % i, x, FY2 + 0.90, z, 0.36, 0.09)
    K.box("FURN_2F_Couch", (2.20, FY2 + 0.24, 3.60), (2.0, 0.24, 0.82), "M_wood_light", col)
    K.box("FURN_2F_CouchBack", (2.20, FY2 + 0.50, 3.96), (2.0, 0.54, 0.12), "M_wood_beam", col)
    for sz in (-1, 1):
        K.box("FURN_2F_Cushion%d" % sz, (2.20 + sz * 0.55, FY2 + 0.40, 3.62), (0.70, 0.10, 0.66),
              "M_lacquer_red", col)
    K.box("FURN_2F_Desk", (-3.60, FY2 + 0.80, 3.80), (1.5, 0.09, 0.72), "M_wood_beam", col)
    scroll(col, "FURN_2F_Scroll", -3.70, FY2 + 0.88, 3.76, 0.46)
    for i, (x, z) in enumerate(((-1.20, 3.90), (1.20, 3.90))):
        K.cyl("LANTERN_2F%d_P" % i, (x, FY2, z), 0.04, 1.60, "M_gold", col, seg=8)
        K.box("LANTERN_2F%d_S" % i, (x, FY2 + 1.78, z), (0.36, 0.54, 0.36), "M_lantern", col)
    for side in (-1, 1):
        K.cyl("PLANT_2F_Orchid%d_Pot" % side, (side * 5.40, FY2 + 0.02, -3.90), 0.16, 0.24,
              "M_ceramic", col, seg=10)
        for k in range(4):
            K.box("PLANT_2F_Orchid%d_L%d" % (side, k), (side * 5.40 + (k - 1.5) * 0.06, FY2 + 0.42, -3.90),
                  (0.03, 0.44, 0.09), "M_plant", col)
    # 二层多宝格 + 香几
    for side in (-1, 1):
        x = side * (HALF_X1 - 0.50)
        K.box("FURN_2F_Shelf%d" % side, (x, FY2 + 1.20, -2.00), (0.36, 2.20, 1.60), "M_wood_dark", col)
        for j in range(3):
            K.box("FURN_2F_Shelf%d_B%d" % (side, j), (x - side * 0.18, FY2 + 0.28 + j * 0.70, -2.00),
                  (0.40, 0.05, 1.60), "M_wood_light", col)
            vase(col, "FURN_2F_Shelf%d_V%d" % (side, j), x - side * 0.18, FY2 + 0.32 + j * 0.70, -2.00,
                 0.28, 0.08)
    return col