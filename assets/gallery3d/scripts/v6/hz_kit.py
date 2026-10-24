"""华章新馆 · 古建构件库（Blender 5.2 / 程序化）

目标不是「用方块拼一个像房子的东西」，而是按清式（斗口制）做法把每个构件拆开：

    台基    须弥座（圭角/下枋/下枭/束腰/上枭/上枋）+ 阶条石 + 踏跺 + 垂带 + 栏板望柱
    柱      柱础（古镜/覆盆）+ 柱身（收分、卷杀）+ 柱头
    额枋    额枋 + 平板枋 + 垫板 + 雀替
    斗拱    栌斗 + 泥道拱 + 华拱（两跳）+ 昂 + 令拱 + 耍头 + 散斗（按斗口模数缩放）
    梁架    七架梁 -> 瓜柱 -> 五架梁 -> 三架梁 -> 脊瓜柱 + 叉手 + 托脚 + 角背
    檩椽    檩 + 垫板 + 檐椽 + 飞椽 + 望板 + 连檐 + 瓦口
    瓦作    筒瓦 / 板瓦 / 瓦当 / 滴水 / 正脊 / 垂脊 / 戗脊 / 走兽 / 鸱吻
    山花    山花板 + 博风板 + 悬鱼 + 惹草
    装修    格扇门（格心/绦环板/裙板）+ 槛窗 + 横披 + 挂落 + 雀替
    屋面    重檐歇山：下檐四坡 + 上檐歇山（山花以下四坡、以上两坡）

坐标仍用网页约定：Y 向上，+Z 建筑后方，-Z 入口前方；落盘时转 Blender Z-up。
"""

from __future__ import annotations

import json
import math
import os

import bpy
from mathutils import Euler, Vector

# ------------------------------------------------------------------ 模数

DOUKOU = 0.10          # 斗口（清式二等）
CAI = DOUKOU * 1.4     # 材广
ZHUJING = 0.42         # 柱径


def k(n: float) -> float:
    """斗口模数换算：k(11) = 11 斗口。"""
    return n * DOUKOU


# ------------------------------------------------------------------ 尺寸

F1 = 0.00            # 一层地面（台基顶）
F1_H = 5.40          # 一层檐柱高
F2 = 5.85            # 二层楼面
F2_H = 3.60          # 二层层高
EAVE_LOW = 8.40      # 下檐檐口
EAVE_UP = 12.20      # 上檐檐口
RIDGE = 15.90        # 屋脊

MX = 6.00            # 明间 / 次间 -> 三开间半宽：明间 4.8，次间 3.6
BAY = [0.0, 2.40, 6.00]          # 柱网 x（对称）：明间边柱、次间柱、角柱
BAY_Z = [0.0, 2.55, 5.10]        # 柱网 z：脊下中柱线、金柱、檐柱

BASE_TOP = 1.20      # 须弥座顶面
BASE_HALF_X = 8.30
BASE_HALF_Z = 7.10

G3D = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PROJECT = os.path.abspath(os.path.join(G3D, "..", ".."))
LOG_PATH = os.path.join(G3D, "_build_huazhang.log")


def log(msg: str) -> None:
    print("[HZ] %s" % msg, flush=True)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(str(msg) + "\n")


# ------------------------------------------------------------------ 材质

MATERIALS = {
    # 名称: (十六进制, 金属度, 粗糙度, 透明度)
    "M_stone_white": ("#e6e1d6", 0.0, 0.72, 1.0),
    "M_stone_grey": ("#b8b3a8", 0.0, 0.80, 1.0),
    "M_stone_dark": ("#6f6a62", 0.0, 0.82, 1.0),
    "M_floor_stone": ("#cfc7b8", 0.0, 0.62, 1.0),
    "M_brick_grey": ("#8d8a83", 0.0, 0.88, 1.0),
    "M_wall_plaster": ("#ece4d5", 0.0, 0.92, 1.0),
    "M_wood_column": ("#8d3b2c", 0.0, 0.52, 1.0),
    "M_wood_beam": ("#5b3a28", 0.0, 0.58, 1.0),
    "M_wood_light": ("#a57c52", 0.0, 0.62, 1.0),
    "M_wood_dark": ("#3f2a1d", 0.0, 0.55, 1.0),
    "M_paint_blue": ("#3d5f6b", 0.0, 0.60, 1.0),
    "M_paint_green": ("#4d6b52", 0.0, 0.60, 1.0),
    "M_lacquer_red": ("#8f2f24", 0.0, 0.45, 1.0),
    "M_gold": ("#c9a24a", 1.0, 0.30, 1.0),
    "M_bronze": ("#7a5a3a", 0.9, 0.42, 1.0),
    "M_tile": ("#4c565e", 0.0, 0.74, 1.0),
    "M_tile_dark": ("#39424a", 0.0, 0.78, 1.0),
    "M_tile_edge": ("#2f373d", 0.0, 0.80, 1.0),
    "M_paper": ("#f0e6d0", 0.0, 0.94, 1.0),
    "M_glass": ("#cfe0e6", 0.0, 0.06, 0.42),
    "M_ceramic": ("#7fa7a3", 0.1, 0.22, 1.0),
    "M_fabric": ("#6d5a4a", 0.0, 0.95, 1.0),
    "M_plant": ("#3f5d3a", 0.0, 0.86, 1.0),
    "M_water": ("#6f8f92", 0.2, 0.10, 1.0),
    "M_lantern": ("#f6e7c8", 0.0, 0.90, 1.0),
}

_CACHE: dict[str, bpy.types.Material] = {}


def srgb(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def mat(name: str) -> bpy.types.Material:
    if name in _CACHE:
        return _CACHE[name]
    spec = MATERIALS.get(name, ("#cccccc", 0.0, 0.6, 1.0))
    hex_color, metallic, roughness, alpha = spec
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    raw = hex_color.lstrip("#")
    color = tuple(srgb(int(raw[i:i + 2], 16) / 255.0) for i in (0, 2, 4)) + (1.0,)
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha
        for key in ("Specular IOR Level", "Specular"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = 0.5 if metallic > 0.5 else 0.2
                break
    if alpha < 1.0:
        material.blend_method = "BLEND"
    _CACHE[name] = material
    return material


# ------------------------------------------------------------------ 几何基元


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    for name in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = name
            break
        except TypeError:
            continue
    return scene


def collection(name: str):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def _mesh(name, verts, faces, material, col, smooth=False):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(x, -z, y) for (x, y, z) in verts], [], faces)
    mesh.validate(verbose=False)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat(material))
    (col or bpy.context.scene.collection).objects.link(obj)
    if smooth:
        for poly in mesh.polygons:
            poly.use_smooth = True
    return obj


def box(name, center, size, material, col=None, rot=(0.0, 0.0, 0.0)):
    """任意欧拉旋转的盒体。center/size 都是网页坐标（x, 高度, 进深）。"""
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    local = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                local.append(Vector((sx * hx, sy * hy, sz * hz)))
    spin = Euler((rot[0], rot[2], rot[1]), "ZXY").to_matrix()
    verts = []
    for point in local:
        p = spin @ point
        verts.append((center[0] + p.x, center[1] + p.y, center[2] + p.z))
    faces = [
        (0, 1, 3, 2), (4, 6, 7, 5),   # x-
        (0, 2, 6, 4), (1, 5, 7, 3),   # y-
        (0, 4, 5, 1), (2, 3, 7, 6),   # z-
    ]
    # 顶点顺序是 (sx,sy,sz) 三重循环，上面面表按 (x-,x+,y-,y+,z-,z+) 分组
    return _mesh(name, verts, faces, material, col)


def cyl(name, base, radius, height, material, col=None, seg=14, r_top=None, axis="y"):
    """圆柱/圆台。base 为底面中心（axis='y'）。"""
    r_top = radius if r_top is None else r_top
    verts = []
    faces = []
    for i in range(seg):
        a = (i / seg) * math.tau
        c, s = math.cos(a), math.sin(a)
        if axis == "y":
            verts.append((base[0] + c * radius, base[1], base[2] + s * radius))
            verts.append((base[0] + c * r_top, base[1] + height, base[2] + s * r_top))
        elif axis == "z":
            verts.append((base[0] + c * radius, base[1] + s * radius, base[2]))
            verts.append((base[0] + c * r_top, base[1] + s * r_top, base[2] + height))
        else:
            verts.append((base[0], base[1] + c * radius, base[2] + s * radius))
            verts.append((base[0] + height, base[1] + c * r_top, base[2] + s * r_top))
    for i in range(seg):
        a0, a1 = i * 2, ((i + 1) % seg) * 2
        faces.append((a0, a1, a1 + 1, a0 + 1))
    faces.append(tuple(range(0, seg * 2, 2))[::-1])
    faces.append(tuple(range(1, seg * 2, 2)))
    return _mesh(name, verts, faces, material, col, smooth=True)


def lathe(name, profile, center, material, col=None, seg=18, axis="y"):
    """旋转体：profile 是 [(半径, 高度)] 折线，用于柱础、香炉、宝顶。"""
    verts = []
    faces = []
    rings = len(profile)
    for i in range(seg):
        a = (i / seg) * math.tau
        c, s = math.cos(a), math.sin(a)
        for radius, height in profile:
            if axis == "y":
                verts.append((center[0] + c * radius, center[1] + height, center[2] + s * radius))
            else:
                verts.append((center[0] + c * radius, center[1] + s * radius, center[2] + height))
    for i in range(seg):
        n = (i + 1) % seg
        for j in range(rings - 1):
            a0 = i * rings + j
            b0 = n * rings + j
            faces.append((a0, b0, b0 + 1, a0 + 1))
    return _mesh(name, verts, faces, material, col, smooth=True)


def merge(objects, name, col=None):
    objects = [o for o in objects if o is not None]
    if not objects:
        return None
    if len(objects) == 1:
        objects[0].name = name
        return objects[0]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    merged = bpy.context.view_layer.objects.active
    merged.name = name
    merged.data.name = name
    return merged


# ------------------------------------------------------------------ 须弥座


def sumeru_base(col):
    """须弥座台基：圭角 / 下枋 / 下枭 / 束腰 / 上枭 / 上枋，逐层叠涩收分。"""
    hx, hz = BASE_HALF_X, BASE_HALF_Z
    top = BASE_TOP
    layers = [
        # (名称, 高度, 外扩量, 材质)
        ("GuiJiao", 0.16, 0.00, "M_stone_dark"),
        ("XiaFang", 0.20, 0.10, "M_stone_white"),
        ("XiaXiao", 0.12, 0.16, "M_stone_white"),
        ("ShuYao", 0.30, -0.16, "M_stone_grey"),
        ("ShangXiao", 0.12, 0.14, "M_stone_white"),
        ("ShangFang", 0.22, 0.20, "M_stone_white"),
    ]
    y = 0.0
    for name, height, flare, material in layers:
        box(
            "BASE_%s" % name,
            (0.0, y + height / 2, 0.0),
            ((hx + flare) * 2, height, (hz + flare) * 2),
            material,
            col,
        )
        y += height
    # 阶条石：压顶一圈，宽出 0.12
    box("BASE_JieTiao", (0.0, top + 0.05, 0.0), ((hx + 0.24) * 2, 0.10, (hz + 0.24) * 2), "M_stone_grey", col)
    # 台面铺地
    box("BASE_Floor", (0.0, top + 0.11, 0.0), (hx * 2 - 0.1, 0.06, hz * 2 - 0.1), "M_floor_stone", col)

    # 正面踏跺 7 级 + 垂带 + 御路石
    steps = 7
    for i in range(steps):
        yy = top - (i + 1) * (top / steps)
        zz = -hz - 0.30 - i * 0.34
        box(
            "BASE_Step%02d" % i,
            (0.0, yy + top / steps / 2, zz),
            (5.6, top / steps, 0.36),
            "M_stone_grey",
            col,
        )
    for side in (-1, 1):
        box(
            "BASE_ChuiDai%d" % side,
            (side * 3.06, top / 2, -hz - 1.42),
            (0.44, top + 0.22, 2.7),
            "M_stone_white",
            col,
            rot=(math.radians(-6.0 * side * 0), 0.0, 0.0),
        )
    # 御路石：中间斜置浮雕带
    box("BASE_YuLu", (0.0, top * 0.46, -hz - 1.40), (1.30, 0.12, 2.6), "M_stone_white", col,
        rot=(math.radians(24.0), 0.0, 0.0))

    # 台基栏板 + 望柱（左右后三面，前留踏跺口）
    railing_run(col, -hx - 0.08, hz + 0.08, hx + 0.08, hz + 0.08, top + 0.16, "BASE")
    railing_run(col, -hx - 0.08, -hz - 0.08, -3.4, -hz - 0.08, top + 0.16, "BASEL")
    railing_run(col, 3.4, -hz - 0.08, hx + 0.08, -hz - 0.08, top + 0.16, "BASER")
    railing_run(col, -hx - 0.08, -hz - 0.08, -hx - 0.08, hz + 0.08, top + 0.16, "BASELL")
    railing_run(col, hx + 0.08, -hz - 0.08, hx + 0.08, hz + 0.08, top + 0.16, "BASERR")
    return top + 0.14


def railing_run(col, x0, z0, x1, z1, base_y, tag):
    """汉白玉栏板 + 望柱：望柱头做海棠头，栏板分三格。"""
    length = math.hypot(x1 - x0, z1 - z0)
    if length < 0.2:
        return
    count = max(2, int(round(length / 1.65)))
    for i in range(count + 1):
        t = i / count
        x = x0 + (x1 - x0) * t
        z = z0 + (z1 - z0) * t
        box("RAIL_%s_Post%02d" % (tag, i), (x, base_y + 0.52, z), (0.20, 1.04, 0.20), "M_stone_white", col)
        box("RAIL_%s_PostCap%02d" % (tag, i), (x, base_y + 1.10, z), (0.26, 0.12, 0.26), "M_stone_white", col)
        lathe(
            "RAIL_%s_PostTop%02d" % (tag, i),
            [(0.10, 0.0), (0.13, 0.06), (0.09, 0.14), (0.0, 0.18)],
            (x, base_y + 1.16, z),
            "M_stone_white",
            col,
            seg=10,
        )
    span = length / count
    for i in range(count):
        t = (i + 0.5) / count
        x = x0 + (x1 - x0) * t
        z = z0 + (z1 - z0) * t
        angle = math.atan2(z1 - z0, x1 - x0)
        box("RAIL_%s_Panel%02d" % (tag, i), (x, base_y + 0.46, z), (span - 0.20, 0.68, 0.09), "M_stone_white", col,
            rot=(0.0, 0.0, angle))
        box("RAIL_%s_PanelTop%02d" % (tag, i), (x, base_y + 0.84, z), (span - 0.14, 0.09, 0.14), "M_stone_white", col,
            rot=(0.0, 0.0, angle))
        # 栏板浮雕：三等分的小块，远看有层次
        for j in range(3):
            box(
                "RAIL_%s_Carve%d_%d" % (tag, i, j),
                (x + math.cos(angle) * (j - 1) * span * 0.28, base_y + 0.46, z + math.sin(angle) * (j - 1) * span * 0.28),
                (span * 0.22, 0.30, 0.12),
                "M_stone_grey",
                col,
                rot=(0.0, 0.0, angle),
            )


# ------------------------------------------------------------------ 柱与额枋


def column(name, x, z, base_y, height, col, diameter=ZHUJING, head=True):
    """柱：柱础 + 收分柱身 + 柱头卷杀。"""
    lathe(
        name + "_Base",
        [(0.0, 0.0), (diameter * 0.85, 0.0), (diameter * 0.85, 0.06), (diameter * 0.68, 0.12),
         (diameter * 0.62, 0.20), (0.0, 0.20)],
        (x, base_y, z),
        "M_stone_white",
        col,
        seg=16,
    )
    cyl(
        name + "_Shaft",
        (x, base_y + 0.20, z),
        diameter / 2,
        height - 0.20,
        "M_wood_column",
        col,
        seg=16,
        r_top=diameter * 0.44,
    )
    if head:
        cyl(
            name + "_Head",
            (x, base_y + height - 0.06, z),
            diameter * 0.46,
            0.06,
            "M_wood_dark",
            col,
            seg=16,
            r_top=diameter * 0.42,
        )


def lintel_set(name, x0, x1, z, y, depth, col, material="M_wood_beam"):
    """额枋 + 垫板 + 平板枋：开间之间的三件套。"""
    width = abs(x1 - x0)
    cx = (x0 + x1) / 2
    box(name + "_EF", (cx, y, z), (width, 0.52, depth), material, col)
    box(name + "_DB", (cx, y + 0.40, z), (width, 0.28, depth * 0.72), "M_paint_blue", col)
    box(name + "_PB", (cx, y + 0.62, z), (width + 0.10, 0.22, depth * 1.12), "M_wood_beam", col)


def queti(name, x, z, y, face_angle, col, size=1.0):
    """雀替：柱头与额枋之间的三角形托木，做两级收分。"""
    for i, (dx, dy, w, h) in enumerate(((0.34, -0.16, 0.68, 0.30), (0.22, -0.34, 0.44, 0.24))):
        box(
            "%s_%d" % (name, i),
            (x + math.sin(face_angle) * 0.0, y + dy, z),
            (w * size, h * size, 0.34),
            "M_wood_light",
            col,
            rot=(0.0, 0.0, face_angle),
        )


# ------------------------------------------------------------------ 斗拱


def dougong(name, x, y, z, facing, col, scale=1.0):
    """一攒斗拱（五铺作）：从栌斗到大斗、华拱两跳、昂、令拱、耍头、散斗。

    facing: 0 表示面向 -Z（前檐），pi 表示 +Z，±pi/2 表示侧檐。
    """
    s = scale
    parts = []

    def add(offset_x, offset_y, offset_z, size, material):
        # 先把局部坐标按 facing 旋转，再落位
        cos_f, sin_f = math.cos(facing), math.sin(facing)
        wx = x + offset_x * cos_f + offset_z * sin_f
        wz = z - offset_x * sin_f + offset_z * cos_f
        parts.append(
            box(
                "%s_%02d" % (name, len(parts)),
                (wx, y + offset_y, wz),
                (size[0] * s, size[1] * s, size[2] * s),
                material,
                col,
                rot=(0.0, 0.0, facing),
            )
        )

    # 栌斗（斗欹 + 斗平）
    add(0.0, 0.08, 0.0, (0.40, 0.16, 0.40), "M_wood_dark")
    add(0.0, 0.20, 0.0, (0.52, 0.10, 0.52), "M_wood_beam")
    # 泥道拱（顺墙面）
    add(0.0, 0.34, 0.0, (0.96, 0.16, 0.20), "M_paint_blue")
    # 华拱第一跳（出跳 0.30）
    add(0.0, 0.34, 0.30, (0.22, 0.16, 0.78), "M_wood_light")
    # 华拱第二跳（出跳 0.62）
    add(0.0, 0.50, 0.62, (0.22, 0.16, 1.10), "M_wood_light")
    # 昂：斜向下伸出的尖头
    add(0.0, 0.42, 0.86, (0.20, 0.14, 0.66), "M_wood_beam")
    # 令拱
    add(0.0, 0.66, 0.62, (0.86, 0.14, 0.18), "M_paint_green")
    # 耍头
    add(0.0, 0.72, 0.90, (0.18, 0.12, 0.40), "M_wood_dark")
    # 散斗：三处
    add(-0.34, 0.44, 0.0, (0.16, 0.10, 0.16), "M_wood_beam")
    add(0.34, 0.44, 0.0, (0.16, 0.10, 0.16), "M_wood_beam")
    add(0.0, 0.76, 0.62, (0.16, 0.10, 0.16), "M_wood_beam")
    return parts


# ------------------------------------------------------------------ 梁架


def beam_frame(col, y_floor, span_x, span_z, label="F1"):
    """三开间梁架：七架梁 -> 瓜柱 -> 五架梁 -> 三架梁 -> 脊瓜柱 + 叉手。"""
    half_x = span_x / 2
    half_z = span_z / 2
    # 七架梁（沿进深，承檐柱）
    for side in (-1, 1):
        box(
            "BEAM_%s_QJ%d" % (label, side),
            (side * (half_x - 0.6), y_floor + 0.30, 0.0),
            (0.46, 0.60, span_z),
            "M_wood_beam",
            col,
        )
    # 五架梁
    for side in (-1, 1):
        box(
            "BEAM_%s_WJ%d" % (label, side),
            (side * (half_x - 1.9), y_floor + 1.42, 0.0),
            (0.40, 0.50, span_z * 0.66),
            "M_wood_beam",
            col,
        )
        # 瓜柱
        for zz in (-span_z * 0.22, span_z * 0.22):
            box(
                "BEAM_%s_GZ%d_%d" % (label, side, int(zz * 10)),
                (side * (half_x - 1.9), y_floor + 0.86, zz),
                (0.30, 0.62, 0.34),
                "M_wood_light",
                col,
            )
    # 三架梁 + 脊瓜柱 + 叉手
    box("BEAM_%s_SJ" % label, (0.0, y_floor + 2.32, 0.0), (0.36, 0.46, span_z * 0.36), "M_wood_beam", col)
    box("BEAM_%s_JGZ" % label, (0.0, y_floor + 2.86, 0.0), (0.30, 0.64, 0.32), "M_wood_light", col)
    for side in (-1, 1):
        box(
            "BEAM_%s_ChaShou%d" % (label, side),
            (side * 0.52, y_floor + 2.72, 0.0),
            (0.90, 0.18, 0.26),
            "M_wood_light",
            col,
            rot=(0.0, math.radians(38.0) * side, 0.0),
        )
        # 托脚（斜撑）
        box(
            "BEAM_%s_TuoJiao%d" % (label, side),
            (side * 2.6, y_floor + 1.94, 0.0),
            (1.30, 0.16, 0.22),
            "M_wood_light",
            col,
            rot=(0.0, math.radians(-34.0) * side, 0.0),
        )


# ------------------------------------------------------------------ 檩椽


def purlin_row(name, z, y, span_x, col, diameter=0.26):
    cyl(name, (-span_x / 2, y, z), diameter / 2, span_x, "M_wood_light", col, seg=12, axis="x")


def rafters(col, half_x, half_z, y_eave, y_ridge, z_purlin, prefix="RAFTER_F", spacing=0.42, rafter_h=0.11):
    """檐椽 + 飞椽 + 望板：沿进深方向从檐口铺到脊，成排密铺。"""
    count = int((2 * half_x) / spacing)
    objs = []
    for i in range(count):
        x = -half_x + spacing * (i + 0.5)
        # 从檐口 (z=half_z, y=y_eave) 到脊 (z=0, y=y_ridge)
        length = math.hypot(half_z, y_ridge - y_eave)
        angle = math.atan2(y_ridge - y_eave, half_z)
        for zsign in (1, -1):
            zc = zsign * half_z / 2
            yc = y_eave + (y_ridge - y_eave) / 2
            objs.append(
                box(
                    "%s_X%03d_%d" % (prefix, i, zsign),
                    (x, yc, zc),
                    (rafter_h, 0.10, length),
                    "M_wood_light",
                    col,
                    rot=(angle * zsign, 0.0, 0.0),
                )
            )
    # 飞椽（檐口出挑段，稍短、朝上翘）
    for i in range(count):
        x = -half_x + spacing * (i + 0.5)
        for zsign in (1, -1):
            objs.append(
                box(
                    "FLY_%03d_%d" % (i, zsign),
                    (x, y_eave - 0.06, zsign * (half_z + 0.34)),
                    (rafter_h * 0.9, 0.10, 0.92),
                    "M_wood_dark",
                    col,
                    rot=(-math.radians(16.0) * zsign, 0.0, 0.0),
                )
            )
    return objs


# ------------------------------------------------------------------ 屋面


def roof_h(x, z, half_x, half_z, y_eave, y_ridge, gable_x=None, curve=1.5, corner=0.34):
    """屋面高度场。

    歇山：|x| <= gable_x 时只有前后坡（山花以上）；
    |x| > gable_x 时取前后坡与山面坡的较小值（下半部四坡）。
    """
    slope_z = (y_ridge - y_eave) / half_z
    h_fb = min(y_ridge, y_eave + slope_z * (half_z - abs(z)))
    if gable_x is not None and abs(x) > gable_x:
        slope_x = (y_ridge - y_eave) / (half_x - gable_x)
        h_side = min(y_ridge, y_eave + slope_x * (half_x - abs(x)))
        h_fb = min(h_fb, h_side)
    t = (h_fb - y_eave) / max(1e-6, (y_ridge - y_eave))
    t = min(1.0, max(0.0, t))
    base = y_eave + (y_ridge - y_eave) * (t ** curve)
    if corner:
        u = abs(x) / half_x
        v = abs(z) / half_z
        base += corner * ((u * v) ** 2.6) * ((1.0 - t) ** 1.15)
    return base


def roof_slab(name, half_x, half_z, y_eave, y_ridge, gable_x, material, col,
              nx=64, nz=48, thickness=0.20):
    xs = sorted(set(
        [-half_x + (2 * half_x) * (i / nx) for i in range(nx + 1)]
        + ([gable_x, -gable_x] if gable_x else [])
    ))
    zs = [-half_z + (2 * half_z) * (j / nz) for j in range(nz + 1)]
    verts = []
    for z in zs:
        for x in xs:
            verts.append((x, roof_h(x, z, half_x, half_z, y_eave, y_ridge, gable_x), z))
    faces = []
    row = len(xs)
    for j in range(nz):
        for i in range(row - 1):
            a = j * row + i
            faces.append((a, a + 1, a + row + 1, a + row))
    obj = _mesh(name, verts, faces, material, col)
    solid = obj.modifiers.new("Solid", "SOLIDIFY")
    solid.thickness = thickness
    solid.offset = -1.0
    solid.use_even_offset = True
    return obj


def tile_field(prefix, half_x, half_z, y_eave, y_ridge, gable_x, col,
               spacing=0.34, tile_w=0.20, lift=0.055, curve=1.5, corner=0.34):
    """瓦作：筒瓦垄 + 板瓦沟。每条垄由「凸起的筒瓦」和两侧压低的板瓦组成。"""
    objs = []
    # 前后坡
    count = int((2 * half_x) / spacing)
    for i in range(count):
        x = -half_x + spacing * (i + 0.5)
        for zsign in (1, -1):
            pts = []
            steps = 16
            for s in range(steps + 1):
                z = zsign * half_z * (s / steps)
                y = roof_h(x, z, half_x, half_z, y_eave, y_ridge, gable_x, curve, corner) + lift
                pts.append((x, y, z))
            objs.append(ribbon("%s_X%03d_%d" % (prefix, i, zsign), pts, tile_w, "M_tile", col))
            # 板瓦：筒瓦两侧压低的窄条
            for side in (-1, 1):
                pts2 = []
                for s in range(steps + 1):
                    z = zsign * half_z * (s / steps)
                    xx = x + side * spacing * 0.32
                    if abs(xx) >= half_x:
                        break
                    y = roof_h(xx, z, half_x, half_z, y_eave, y_ridge, gable_x, curve, corner) + lift * 0.35
                    pts2.append((xx, y, z))
                if len(pts2) > 2:
                    objs.append(ribbon("%s_P%03d_%d_%d" % (prefix, i, zsign, side), pts2, tile_w * 0.62, "M_tile_dark", col))
    # 山面坡（歇山下半部）
    if gable_x is not None:
        count_z = int((2 * half_z) / spacing)
        for i in range(count_z):
            z = -half_z + spacing * (i + 0.5)
            for xsign in (1, -1):
                pts = []
                steps = 12
                for s in range(steps + 1):
                    x = xsign * (gable_x + (half_x - gable_x) * (s / steps))
                    y = roof_h(x, z, half_x, half_z, y_eave, y_ridge, gable_x, curve, corner) + lift
                    pts.append((x, y, z))
                objs.append(ribbon("%s_Z%03d_%d" % (prefix, i, xsign), pts, tile_w, "M_tile", col))
    return objs


def ribbon(name, pts, width, material, col):
    """沿折线的微凸窄条（瓦垄 / 脊带）。"""
    half = width / 2
    verts = []
    faces = []
    for idx, (x, y, z) in enumerate(pts):
        if idx < len(pts) - 1:
            nx, _, nz = pts[idx + 1]
            tx, tz = nx - x, nz - z
        else:
            px, _, pz = pts[idx - 1]
            tx, tz = x - px, z - pz
        length = math.hypot(tx, tz) or 1.0
        ox, oz = -tz / length * half, tx / length * half
        verts.append((x + ox, y - 0.02, z + oz))
        verts.append((x, y + 0.035, z))
        verts.append((x - ox, y - 0.02, z - oz))
    for i in range(len(pts) - 1):
        a, b = i * 3, (i + 1) * 3
        faces.append((a, b, b + 1, a + 1))
        faces.append((a + 1, b + 1, b + 2, a + 2))
    return _mesh(name, verts, faces, material, col, smooth=True)


def eave_edge(prefix, half_x, half_z, y_eave, y_ridge, gable_x, col, tile_w=0.20, spacing=0.34):
    """檐口瓦当与滴水：一圈小圆饼 + 下垂的尖片。"""
    objs = []
    count = int((2 * half_x) / spacing)
    for i in range(count):
        x = -half_x + spacing * (i + 0.5)
        for zsign in (1, -1):
            y = roof_h(x, zsign * half_z, half_x, half_z, y_eave, y_ridge, gable_x) + 0.03
            objs.append(
                cyl(
                    "WADANG_%03d_%d" % (i, zsign),
                    (x, y, zsign * (half_z + 0.02)),
                    tile_w * 0.46,
                    0.05,
                    "M_tile_dark",
                    col,
                    seg=8,
                    axis="z",
                )
            )
            objs.append(
                box(
                    "DISHUI_%03d_%d" % (i, zsign),
                    (x, y - 0.14, zsign * (half_z + 0.10)),
                    (tile_w * 0.56, 0.18, 0.05),
                    "M_tile_dark",
                    col,
                    rot=(math.radians(18.0) * zsign, 0.0, 0.0),
                )
            )
    return objs


def main_ridge(prefix, length, y, col, height=0.46):
    box("%s_Body" % prefix, (0.0, y + height / 2, 0.0), (length, height, 0.36), "M_tile_dark", col)
    box("%s_Cap" % prefix, (0.0, y + height + 0.05, 0.0), (length + 0.10, 0.12, 0.44), "M_tile_edge", col)
    # 脊筒上的小兽（每 0.9 m 一个）
    count = int(length / 0.9)
    for i in range(count):
        x = -length / 2 + 0.45 + i * 0.9
        box("%s_Beast%02d" % (prefix, i), (x, y + height + 0.16, 0.0), (0.16, 0.16, 0.16), "M_tile_edge", col)


def chiwen(prefix, x, y, z, col, flip=1):
    """鸱吻：正脊两端的吞脊兽，做三层收分 + 尾翅。"""
    for i, (dy, h, w) in enumerate(((0.0, 0.80, 0.34), (0.34, 0.44, 0.26), (0.58, 0.26, 0.18))):
        box("%s_%d" % (prefix, i), (x + flip * i * 0.10, y + dy + h / 2, z), (w, h, 0.30), "M_tile_edge", col,
            rot=(0.0, math.radians(-14.0 * flip), 0.0))
    box("%s_Tail" % prefix, (x + flip * 0.34, y + 0.92, z), (0.16, 0.34, 0.20), "M_tile_edge", col,
        rot=(0.0, math.radians(-38.0 * flip), 0.0))


def hip_ridge(prefix, x0, z0, x1, z1, y0, y1, col, half_x, half_z, y_eave, y_ridge, gable_x,
              width=0.30, steps=14):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t
        z = z0 + (z1 - z0) * t
        y = roof_h(x, z, half_x, half_z, y_eave, y_ridge, gable_x) + 0.06
        pts.append((x, y, z))
    return ribbon(prefix, pts, width, "M_tile_dark", col)


def gable_face(prefix, gable_x, half_z, y_eave, y_ridge, col, z_signs=(-1, 1)):
    """山花：垂直三角形封板 + 博风板 + 悬鱼 + 惹草。

    山花板贴在 x = ±gable_x 的垂直面上：底边是山面檐口线，顶点是正脊端，
    整块都在屋面以下，不会从瓦面上穿出来。
    博风板沿这条斜边**逐段采样屋面高度**，而不是拉一条直线——
    直线会浮在曲面之上，远看就是两道白条。
    """
    objs = []
    edge_z = half_z * 0.86
    for side in (-1, 1):
        xx = side * gable_x
        # 山花板：必须做成「沿屋面曲线采样的曲面多边形」。
        # 用三角形的话，两条斜边是直线，而屋面的举折是凹曲线，直线会高出曲面，
        # 从远处看就是两道白边穿出瓦面。
        fx = side * (gable_x - 0.30)
        zs = [edge_z * (i / 8) for i in range(9)]
        ring = [(-z) for z in reversed(zs)] + zs[1:]
        verts = []
        for z in ring:
            y = roof_h(fx, z, gable_x, half_z, y_eave, y_ridge, gable_x) - 0.10
            verts.append((fx, y, z))
        apex = (fx, roof_h(fx, 0.0, gable_x, half_z, y_eave, y_ridge, gable_x) - 0.10, 0.0)
        verts.append(apex)
        apex_index = len(verts) - 1
        faces = []
        for i in range(len(verts) - 2):
            faces.append((apex_index, i, i + 1))
        faces.append((apex_index, len(verts) - 2, 0))
        objs.append(_mesh(prefix + "_Face%d" % side, verts, faces, "M_wall_plaster", col))
        objs.append(_mesh(prefix + "_FaceB%d" % side, verts,
                          [(a, c, b) for (a, b, c) in faces], "M_wall_plaster", col))
        # 博风板：沿屋面轮廓分段采样的脊带
        for zsign in (-1, 1):
            pts = []
            for i in range(13):
                z = zsign * edge_z * (1 - i / 12)
                y = roof_h(gable_x, z, gable_x, half_z, y_eave, y_ridge, gable_x) - 0.04
                pts.append((xx, y, z))
            objs.append(ribbon("%s_BoFeng%d_%d" % (prefix, side, zsign), pts, 0.30, "M_wood_dark", col))
        # 悬鱼 + 惹草
        apex_y = roof_h(gable_x, 0.0, gable_x, half_z, y_eave, y_ridge, gable_x)
        base_y = roof_h(gable_x, edge_z, gable_x, half_z, y_eave, y_ridge, gable_x)
        objs.append(box("%s_XuanYu%d" % (prefix, side), (xx + side * 0.06, (apex_y + base_y) / 2 - 0.35, 0.0),
                        (0.09, 0.66, 0.36), "M_wood_dark", col))
        for zs, tag in ((1, "A"), (-1, "B")):
            objs.append(box("%s_ReCao%d%s" % (prefix, side, tag),
                            (xx + side * 0.06, base_y + 0.46, zs * edge_z * 0.82),
                            (0.08, 0.28, 0.24), "M_wood_dark", col))
    return objs


# ------------------------------------------------------------------ 门窗


def lattice_door(name, x, z, base_y, width, height, col, facing=0.0, leaves=4, paper=True):
    """格扇门：边框 + 格心（步步锦棂条）+ 绦环板 + 裙板。"""
    leaf_w = width / leaves
    objs = []
    for i in range(leaves):
        cx = x - width / 2 + leaf_w * (i + 0.5)
        local = []
        # 边框
        local.append(box("%s_%d_F" % (name, i), (cx, base_y + height / 2, z), (leaf_w - 0.02, height, 0.09), "M_wood_beam", col, rot=(0.0, 0.0, facing)))
        # 格心：宣纸
        if paper:
            local.append(box("%s_%d_P" % (name, i), (cx, base_y + height * 0.66, z + 0.03), (leaf_w - 0.14, height * 0.50, 0.03), "M_paper", col, rot=(0.0, 0.0, facing)))
        # 棂条：横 6 竖 4，形成步步锦
        for r in range(6):
            local.append(box("%s_%d_H%d" % (name, i, r), (cx, base_y + height * 0.44 + r * height * 0.095, z + 0.05), (leaf_w - 0.12, 0.028, 0.028), "M_wood_light", col, rot=(0.0, 0.0, facing)))
        for c in range(4):
            local.append(box("%s_%d_V%d" % (name, i, c), (cx - (leaf_w - 0.16) / 2 + c * (leaf_w - 0.16) / 3, base_y + height * 0.66, z + 0.05), (0.028, height * 0.50, 0.028), "M_wood_light", col, rot=(0.0, 0.0, facing)))
        # 绦环板 + 裙板
        local.append(box("%s_%d_T" % (name, i), (cx, base_y + height * 0.35, z + 0.02), (leaf_w - 0.10, 0.16, 0.05), "M_lacquer_red", col, rot=(0.0, 0.0, facing)))
        local.append(box("%s_%d_S" % (name, i), (cx, base_y + height * 0.17, z + 0.02), (leaf_w - 0.10, height * 0.28, 0.05), "M_lacquer_red", col, rot=(0.0, 0.0, facing)))
        # 门钉
        for r in range(3):
            for c in range(2):
                local.append(box("%s_%d_N%d%d" % (name, i, r, c), (cx - 0.12 + c * 0.24, base_y + height * 0.10 + r * 0.10, z + 0.05), (0.04, 0.04, 0.02), "M_gold", col, rot=(0.0, 0.0, facing)))
        objs.extend(local)
    return objs


def lattice_window(name, x, z, base_y, width, height, col, facing=0.0):
    """槛窗：槛墙 + 窗框 + 格心。"""
    objs = [
        box("%s_Sill" % name, (x, base_y + 0.35, z), (width, 0.70, 0.12), "M_wood_beam", col, rot=(0.0, 0.0, facing)),
        box("%s_Glass" % name, (x, base_y + 0.70 + height / 2, z + 0.01), (width - 0.10, height, 0.03), "M_paper", col, rot=(0.0, 0.0, facing)),
        box("%s_Top" % name, (x, base_y + 0.70 + height + 0.05, z), (width + 0.10, 0.12, 0.14), "M_wood_beam", col, rot=(0.0, 0.0, facing)),
    ]
    cols = max(3, int(width / 0.34))
    for i in range(cols):
        xx = x - width / 2 + width * (i + 0.5) / cols
        objs.append(box("%s_V%d" % (name, i), (xx, base_y + 0.70 + height / 2, z + 0.04), (0.05, height, 0.05), "M_wood_beam", col, rot=(0.0, 0.0, facing)))
    for i in range(5):
        objs.append(box("%s_H%d" % (name, i), (x, base_y + 0.70 + height * (i + 0.5) / 5, z + 0.04), (width - 0.08, 0.05, 0.05), "M_wood_beam", col, rot=(0.0, 0.0, facing)))
    return objs


def guaLuo(name, x, z, y, width, col, facing=0.0, depth=0.30):
    """挂落：檐下悬垂的木格栅。"""
    objs = [box("%s_Rail" % name, (x, y, z), (width, 0.09, 0.09), "M_wood_beam", col, rot=(0.0, 0.0, facing))]
    count = max(2, int(width / 0.22))
    for i in range(count):
        xx = x - width / 2 + width * (i + 0.5) / count
        objs.append(box("%s_Bar%d" % (name, i), (xx, y - depth / 2, z), (0.035, depth, 0.035), "M_wood_light", col, rot=(0.0, 0.0, facing)))
    return objs