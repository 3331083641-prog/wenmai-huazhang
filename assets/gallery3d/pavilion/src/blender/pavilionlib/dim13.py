"""v13 尺寸唯一真源 —— 80×96m 宋风四方水院（零穿模疏朗布局）。

坐标：+X 东 / +Y 北 / -Y 南（牌楼方向）；z=0 = 青石大台基面 = 全场统一完成面。
台基外不再有草坪、广场或土石托盘：80×96m 台基四周利落切平，外围直接是蓝天碧云。

竖向口径（全场景唯一）：
    -1.20  台基底（裙边收口）
    -0.55  金水院水面
    -1.10  池底
    +0.06  池岸压顶
    +0.10  石桥桥面
    +0.00  青石台基面（绝对统一，不做零碎托盘）
    +0.30  主殿台明 / 月台（仅主殿一级，其余馆舍落于 0.00）
    +4.00  连廊檐口          +16.50 主殿正脊

布局（全部读本文件，parts13/* 与 props 不得写死）：
    牌楼        y=-46（三间四柱七楼，跨 x±12）
    金水院      x±20, y[-36,-14]（22m 长），6m 宽石桥 + 9 对望柱
    主殿        26×18, x[-13,13], y[0,18], 五开间，重檐歇山，正脊 16.50
    西前殿 刊木堂  12×12 @(-32,-30)   西后轩 澄怀轩 12×12 @(-32,-12)
    东前殿 针经阁  12×12 @(+32,-30)   东后阁 素肌堂 12×12 @(+32,-12)
    镂金坊     12×7 @(-20,-42)（南门西侧水榭，剪纸馆）
    连廊       环水院四周，宽 3.4，内缘 x±21.0 / y[-37.0,-13.4]
    后苑       方池 x±9 y[27,39] + 四松 + 石灯
"""
from __future__ import annotations

import math


class Dim13:
    NAME = "wenmai_v13"

    # ---------------- 总图 ----------------
    PLATE_X = 40.0            # 基台半宽 → 80m
    PLATE_Y_S = -48.0         # 南缘 → 96m 进深
    PLATE_Y_N = 48.0
    PLATE_THICK = 1.20        # 台基厚（下缘 -1.20）
    PLATE_EDGE_BAND = 1.60    # 四周汉白玉收边带宽
    PLATE_EDGE_LIP = 0.12     # 收边石比青石面高 12mm（避免共面 Z-fighting）

    GROUND_Z = 0.00           # 台基完成面 = 世界原点
    GROUND_THICK = 0.30
    PLINTH_TOP = 0.00
    PLINTH_H = 0.00           # v13 不做叠涩须弥座，只做整块青石台基 + 汉白玉收边

    # ---------------- 主殿 26×18 五开间 ----------------
    HALL_HX = 13.0
    HALL_Y0 = 0.0
    HALL_Y1 = 18.0
    HALL_CY = 9.0
    COL_X = (0.0, 3.25, 8.15, 13.0)      # 明间 6.5 + 次间 4.9×2 + 梢间 4.85×2 = 26
    COL_Y = (0.0, 5.4, 12.6, 18.0)       # 5.4 + 7.2 + 5.4 = 18
    COL_H = 9.60
    COL_R = 0.42
    COL_R_TOP = 0.38
    ARCH_Z0 = 8.90
    ARCH_Z1 = 9.15
    PUPai_H = 0.25
    DOUGONG_Z0 = 9.15
    DOUGONG_H = 1.40
    DOOR_W = 6.50
    DOOR_H = 5.60
    TAIJI_H = 0.30                       # 殿内台明（0 → 0.30）

    # 重檐竖向（沿用 v11 校验值，只随 y0 平移）
    EAVE_OUT = 3.20
    LOWER_EAVE_Z = 6.40
    LOWER_EAVE_TIP = 16.20
    LOWER_EAVE_TIP_Y0 = -3.20            # HALL_Y0 - 3.20
    LOWER_EAVE_TIP_Y1 = 21.20            # HALL_Y1 + 3.20
    LOWER_ROOF_TOP_Z = 8.80
    CLERE_Y = 3.40
    UPPER_EAVE_Z = 10.90
    UPPER_EAVE_TIP_X = 15.40
    UPPER_EAVE_TIP_Y0 = -1.60
    UPPER_EAVE_TIP_Y1 = 19.60
    RIDGE_Z = 16.50
    RIDGE_HALF = 7.80
    GABLE_X = 7.80
    SKIRT_BREAK_Z = 13.60
    GABLE_Y0 = 5.60                      # HALL_CY - 3.40
    GABLE_Y1 = 12.40                     # HALL_CY + 3.40
    ROOF_THICK = 0.34
    TILE_GAUGE = 0.42
    TILE_AMP = 0.070

    # 藻井
    HALL_CEIL = 12.00
    CAISSON_SIZE = 8.00
    CAISSON_TOP = 12.00
    CAISSON_DEPTH = 2.40
    CAISSON_LAYERS = 11
    SKYLIGHT = 1.80

    # 主殿月台（南面一级 0.30 高，三方踏步）
    TERRACE_Y0 = -3.40
    TERRACE_Y1 = 0.00
    TERRACE_HX = 11.00
    TERRACE_H = 0.30
    TERRACE_STEP_TREAD = 0.32

    # ---------------- 金水院（中轴水庭 40×22）----------------
    POOL_X0 = -20.0
    POOL_X1 = 20.0
    POOL_Y0 = -36.0
    POOL_Y1 = -14.0
    WATER_Z = -0.55
    POOL_BOTTOM_Z = -3.05
    POOL_COPING_Z = 0.06
    POOL_COPING_W = 0.55
    POOL_WALL_T = 0.45

    BRIDGE_W = 6.00
    BRIDGE_Y_S = -36.0
    BRIDGE_Y_N = -14.0
    BRIDGE_DECK_Z = 0.10
    BRIDGE_T = 0.26
    BRIDGE_GAP = 0.06
    BRIDGE_POST_X = 2.90
    BRIDGE_POST_N = 9
    BRIDGE_POST = (0.30, 0.30, 1.05)

    # ---------------- 迎宾牌楼（三间四柱七楼）----------------
    GATE_Y = -46.0
    GATE_HX = 12.0
    GATE_COL_X = (0.0, 4.40, 12.00)
    GATE_COL_R = 0.46
    GATE_H = 10.60
    GATE_SIDE_H = 7.90
    GATE_INNER_H = 6.90
    GATE_OUTER_H = 6.40
    GATE_DEPTH = 1.50
    GATE_HDR_H = 1.15
    GATE_FOUND_H = 0.24                  # 柱础（台基面上 0.24，四周留 20mm 净缝）

    # ---------------- 东西配殿 12×12 ----------------
    SIDE_HX = 6.0
    SIDE_HY = 6.0
    SIDE_CX = 32.0
    SIDE_CY_F = -30.0                    # 前殿（临水院）
    SIDE_CY_B = -12.0                    # 后阁（临主殿院）
    SIDE_GAP = SIDE_CY_B - SIDE_HY - (SIDE_CY_F + SIDE_HY)   # = 6.0m 净距
    SIDE_COL_H = 6.00
    SIDE_EAVE_Z = 6.40
    SIDE_RIDGE_Z = 10.20
    SIDE_EAVE_OUT = 2.60
    SIDE_BREAK_Z = 8.60
    SIDE_WALL_T = 0.28
    SIDE_DOOR_W = 3.60
    SIDE_DOOR_H = 3.90

    # ---------------- 镂金坊（南门西侧水榭 · 剪纸馆）12×7 ----------------
    JP_CX = -20.0
    JP_CY = -42.0
    JP_HX = 6.0
    JP_HY = 3.5
    JP_FLOOR = 0.15
    JP_COL_H = 3.60
    JP_EAVE_Z = 4.00
    JP_RIDGE_Z = 6.20
    JP_EAVE_OUT = 1.60
    JP_DOOR_W = 3.20
    JP_DOOR_H = 2.90

    # ---------------- 连廊（环水院四周）----------------
    CL_W = 3.40
    CL_IN_X = 21.00
    CL_OUT_X = 24.40
    CL_IN_YS = -37.00
    CL_OUT_YS = -40.40
    CL_IN_YN = -13.40
    CL_OUT_YN = -10.00
    CL_COL_H = 3.60
    CL_EAVE_Z = 3.90
    CL_ROOF_TOP = 5.20
    CL_EAVE_OUT = 0.90
    CL_COL_STEP = 3.40
    CL_N_OPEN = 6.00                     # 北廊正中 12m 穿堂开口（不挡主殿视轴）
    CL_SLAB_T = 0.18

    # 牌楼景墙（v13 不建，仅保留 gate.py 的常量读取接口）
    SCREEN_H = 3.20
    SCREEN_T = 0.45
    WINDOW_W = 1.40
    WINDOW_H = 1.15

    # ---------------- 汉白玉望柱栏杆（台基四周 + 池岸）----------------
    RAIL_H = 0.95
    RAIL_POST_STEP = 3.00
    RAIL_POST_W = 0.16
    RAIL_IN = 0.90                       # 栏杆中心线距台基外缘

    # ---------------- 后苑（y 18..48）----------------
    RG_POOL_X0 = -9.0
    RG_POOL_X1 = 9.0
    RG_POOL_Y0 = 27.0
    RG_POOL_Y1 = 39.0
    RG_WATER_Z = -0.30
    RG_BOTTOM_Z = -2.45
    RG_COPING_Z = 0.05
    RG_TREES = ((-30.0, 24.0), (30.0, 24.0), (-30.0, 42.0), (30.0, 42.0))
    RG_LANTERNS = ((-11.5, 22.0), (11.5, 22.0), (-11.5, 43.0), (11.5, 43.0))
    RG_TREE_H = 6.60

    # ---------------- 材质（19 种）----------------
    MAT = {
        "roof_dai":   ("宋韵青灰琉璃瓦", "#87949B", 0.74, 0.02, 2048),
        "wood_dark":  ("温润金丝楠木", "#8A6A4C", 0.62, 0.00, 2048),
        "wood_lite":  ("银杏黄暖木", "#C6A87F", 0.55, 0.00, 2048),
        "wall_white": ("羊脂温玉暖白", "#FBF7EF", 0.80, 0.00, 2048),
        "stone_dark": ("青灰玄武岩", "#8D979B", 0.60, 0.00, 2048),
        "stone_lite": ("汉白玉", "#F2EFE6", 0.50, 0.00, 1024),
        "water":      ("澄澈天空映水", "#5FA0B4", 0.05, 0.02, 1024),
        "glass":      ("影青透光玉石", "#B7D2CC", 0.12, 0.00, 1024),
        "bronze":     ("宋韵鎏金", "#DDB25C", 0.40, 0.62, 1024),
        "crimson":    ("故宫朱砂大漆", "#C0453A", 0.42, 0.05, 1024),
        "celadon":    ("宋画青绿彩画", "#5C9A97", 0.62, 0.00, 1024),
        "foliage":    ("苍翠罗汉松", "#4E7A5C", 0.75, 0.00, 1024),
        "cloud":      ("飘逸层云", "#FFF8E7", 0.92, 0.00, 512),
        "pond":       ("暖青灰池底", "#A6B3AE", 0.55, 0.00, 512),
        "silk":       ("丝光织锦", "#CE5A48", 0.55, 0.00, 512),
        "lightstrip": ("天光柔白", "#FFF3DC", 0.50, 0.00, 512),
        "lacquer":    ("黑漆匾底", "#3A2E26", 0.22, 0.00, 512),
        "cloud_soft": ("祥云柔白", "#FFFFFF", 1.00, 0.00, 512),
        "sky_azure":  ("天青湛碧", "#4B8EC7", 1.00, 0.00, 512),
    }
    MAT_ORDER = tuple(MAT.keys())

    # 天穹（只服务 Blender 出图与 Web 背景，不参与建筑合并）
    SKY = {
        "zenith": "#4B8EC7",
        "horizon": "#F5F0E6",
        "cloud": "#FFFFFF",
        "sun_warm": "#FFE6C0",
        "sun_elev": 38.0,                # 太阳高度角
        "sun_azim": 215.0,               # 南偏西 35°（正南 180°）
        "sun_kelvin": 5600,
        "clouds": 7,
    }

    # ---------------- 机位（5 个）----------------
    CAMERAS = {
        "CAM_Courtyard_Aerial": dict(loc=(-62, -94, 31), look=(0, -4, 7), lens=34, cn="水院群览"),
        "CAM_Gate_Front":       dict(loc=(0, -66, 2.20), look=(0, -40, 6.40), lens=28, cn="牌楼金水"),
        "CAM_Atrium_Grand":     dict(loc=(0, 6.60, 1.95), look=(0, 9.60, 11.20), lens=17, cn="主殿藻井"),
        "CAM_Water_Court":      dict(loc=(0, -12.0, 1.75), look=(0, -40.0, 3.00), lens=24, cn="水院回望"),
        "CAM_Rear_Garden":      dict(loc=(0, 20.0, 1.95), look=(0, 42.0, 3.00), lens=24, cn="后苑松石"),
    }
    CAM_ORDER = ("CAM_Courtyard_Aerial", "CAM_Gate_Front", "CAM_Atrium_Grand",
                 "CAM_Water_Court", "CAM_Rear_Garden")

    # 一键进馆（Web 第一人称传送；loc 已是地面 +1.65m 眼高，Blender 坐标）
    TELEPORTS = {
        "gate":        {"cn": "牌楼 · 金水桥", "loc": (0.0, -62.0, 1.65), "look": (0.0, -44.0, 4.50)},
        "courtyard":   {"cn": "水院 · 丹陛",   "loc": (0.0, -8.0, 1.65), "look": (0.0, 4.0, 5.00)},
        "bianxiu":     {"cn": "针经阁 · 汴绣", "loc": (25.0, -30.0, 1.65), "look": (33.0, -30.0, 1.20)},
        "songhua":     {"cn": "澄怀轩 · 宋画", "loc": (-25.0, -12.0, 1.65), "look": (-33.0, -12.0, 1.20)},
        "qinghua":     {"cn": "素肌堂 · 青花", "loc": (25.0, -12.0, 1.65), "look": (33.0, -12.0, 1.20)},
        "zhuxianzhen": {"cn": "刊木堂 · 年画", "loc": (-25.0, -30.0, 1.65), "look": (-33.0, -30.0, 1.20)},
        "jianzhi":     {"cn": "镂金坊 · 剪纸", "loc": (-20.0, -37.2, 1.80), "look": (-20.0, -43.0, 1.20)},
    }

    # ---------------- 画框与吸附 ----------------
    FRAME_CLASSES = {"A": (1.20, 1.60, 1.70), "B": (1.50, 0.90, 1.55), "C": (0.90, 0.90, 1.55)}
    SNAP_KINDS = ("desk", "shelf", "floor")

    # ---------------- 展馆定义（供 parts13/exhibits 与 Web 共用）----------------
    HALLS = {
        "main":        dict(cn="天章殿 · 主殿",  style="",          cx=0.0,   cy=9.0,  hx=13.0, hy=9.0),
        "zhuxianzhen": dict(cn="刊木堂 · 年画",  style="zhuxianzhen", cx=-32.0, cy=-30.0, hx=6.0, hy=6.0),
        "songhua":     dict(cn="澄怀轩 · 宋画",  style="songhua",     cx=-32.0, cy=-12.0, hx=6.0, hy=6.0),
        "bianxiu":     dict(cn="针经阁 · 汴绣",  style="bianxiu",     cx=32.0,  cy=-30.0, hx=6.0, hy=6.0),
        "qinghua":     dict(cn="素肌堂 · 青花",  style="qinghua",     cx=32.0,  cy=-12.0, hx=6.0, hy=6.0),
        "jianzhi":     dict(cn="镂金坊 · 剪纸",  style="jianzhi",     cx=-20.0, cy=-42.0, hx=6.0, hy=3.5),
    }

    # 各馆桌面高度（道具落位基准）
    DESK_H = 0.86
    SHELF_H = (0.55, 1.05, 1.55)


DIM13 = Dim13()

if __name__ == "__main__":
    d = DIM13
    print(f"[dim13] 台基 {d.PLATE_X*2:.0f} × {d.PLATE_Y_N - d.PLATE_Y_S:.0f} m，厚 {d.PLATE_THICK}")
    print(f"[dim13] 主殿 26×18 y[{d.HALL_Y0},{d.HALL_Y1}] 正脊 {d.RIDGE_Z}")
    print(f"[dim13] 水院 x[{d.POOL_X0},{d.POOL_X1}] y[{d.POOL_Y0},{d.POOL_Y1}] 水面 {d.WATER_Z}")
    print(f"[dim13] 配殿净距 {d.SIDE_GAP:.2f} m / 连廊宽 {d.CL_W}")
    print(f"[dim13] 材质 {len(d.MAT_ORDER)} / 机位 {len(d.CAMERAS)} / 传送 {len(d.TELEPORTS)}")