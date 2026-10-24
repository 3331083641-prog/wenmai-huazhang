"""华章新馆 · 几何与材质工具库（Blender 5.2）

所有几何都用**网页坐标**（three.js 约定：Y 向上，+Z 建筑后方，-Z 入口前方）书写，
落盘前统一转成 Blender 的 Z-up：

    V(x, y, z) -> (x, -z, y)

这样做的好处：尺寸表能直接对着前端的 layout 契约核，不用在脑子里反复翻转坐标。
"""

from __future__ import annotations

import json
import math
import os

import bpy
from mathutils import Vector

# ------------------------------------------------------------------ 尺寸表

F1 = 0.45            # 一层地面
F1_H = 4.55          # 一层净高
BEAM1 = 5.0          # 一层梁架底
SLAB_T = 0.22        # 二层楼板厚
F2 = 5.22            # 二层地面
F2_H = 3.6           # 二层净高
F2_CLEAR = 3.6       # 二层净高（别名，供 build 脚本使用）
COL_TOP = 8.82       # 檐柱柱头（也是二层天花标高）
WALL_TOP = 10.25     # 外墙顶 = 围脊标高，把下檐与上檐接起来
EAVE_LOW = 9.0       # 下檐檐口
EAVE_LOW_IN = 10.25  # 下檐内沿（贴外墙顶）
EAVE_UP = 10.55      # 上檐檐口（略高于围脊，重檐才连得起来）
RIDGE = 14.9         # 屋脊

HX = 6.6             # 主体半宽（面阔 13.2）
HZ = 4.8             # 主体半深（进深 9.6）
WALL_T = 0.32
BASE_TOP = 0.45

COL_X = [0.0, 1.6, -1.6, 4.2, -4.2, 6.4, -6.4]
COL_Z = [0.0, 2.2, -2.2, 4.5, -4.5]

# 屋面出挑
LOW_OVER_X = 1.75
LOW_OVER_Z = 1.75
UP_HALF_X = 7.15     # 上檐半宽（出挑 0.55，重檐上层出挑本来就不大）
UP_HALF_Z = 5.35

# 上檐垄脊线长度（庑殿顶的「正脊」）
RIDGE_HALF = 1.9

G3D = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PROJECT = os.path.abspath(os.path.join(G3D, "..", ".."))
LOG_PATH = os.path.join(G3D, "_build_huazhang.log")


def log(msg: str) -> None:
    print("[HZ] %s" % msg, flush=True)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(str(msg) + "\n")


# ------------------------------------------------------------------ 坐标


def V(x: float, y: float, z: float) -> Vector:
    """网页坐标 -> Blender 坐标。"""
    return Vector((x, -z, y))


def vlist(x: float, y: float, z: float):
    return (x, -z, y)


# ------------------------------------------------------------------ 场景


def set_engine(scene, *candidates: str) -> str:
    """按候选顺序设置渲染引擎（5.x 的 EEVEE 枚举名与 4.x 不同）。"""
    for name in candidates:
        try:
            scene.render.engine = name
            return name
        except TypeError:
            continue
    return scene.render.engine


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    set_engine(scene, "BLENDER_EEVEE", "BLENDER_EEVEE_NEXT")
    return scene


def collection(name: str):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


# ------------------------------------------------------------------ 材质

_MATERIALS: dict[str, bpy.types.Material] = {}

# 名称 -> (基色 sRGB hex, 金属度, 粗糙度, 透明度)
MATERIAL_TABLE = {
    "M_stone_base": ("#d8d2c6", 0.0, 0.85, 1.0),
    "M_stone_floor": ("#cfc8bb", 0.0, 0.55, 1.0),
    "M_stone_dark": ("#8f8a80", 0.0, 0.7, 1.0),
    "M_wall_plaster": ("#ece5d8", 0.0, 0.92, 1.0),
    "M_wood_walnut": ("#4a3428", 0.0, 0.55, 1.0),
    "M_wood_light": ("#a8825a", 0.0, 0.6, 1.0),
    "M_lacquer_red": ("#8f2f24", 0.05, 0.45, 1.0),
    "M_gold_brass": ("#c9a24a", 1.0, 0.28, 1.0),
    "M_tile_grey": ("#59636b", 0.0, 0.72, 1.0),
    "M_tile_dark": ("#39424a", 0.0, 0.78, 1.0),
    "M_glass": ("#cfe0e6", 0.0, 0.06, 0.45),
    "M_paper": ("#f3ead6", 0.0, 0.95, 1.0),
    "M_fabric": ("#6d5a4a", 0.0, 0.95, 1.0),
    "M_ceramic": ("#7fa7a3", 0.1, 0.2, 1.0),
    "M_plant": ("#3f5d3a", 0.0, 0.85, 1.0),
    "M_water": ("#6f8f92", 0.2, 0.08, 1.0),
    "M_lantern_glow": ("#f6e7c8", 0.0, 0.9, 1.0),
    "M_granite_dark": ("#5d5a55", 0.0, 0.65, 1.0),
    "M_bronze": ("#7a5a3a", 0.9, 0.4, 1.0),
}


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear(hex_color: str):
    raw = hex_color.lstrip("#")
    r = int(raw[0:2], 16) / 255.0
    g = int(raw[2:4], 16) / 255.0
    b = int(raw[4:6], 16) / 255.0
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), 1.0)


def mat(name: str) -> bpy.types.Material:
    if name in _MATERIALS:
        return _MATERIALS[name]
    spec = MATERIAL_TABLE.get(name, ("#cccccc", 0.0, 0.6, 1.0))
    color, metallic, roughness, alpha = spec
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = material.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        out = material.node_tree.nodes.get("Material Output")
        material.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    rgba = hex_to_linear(color)
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = alpha
    # 石材/木作不该是镜面：默认 0.5 的 IOR level 会让台基在网页里泛白反光
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.5 if metallic > 0.5 else 0.22
    elif "Specular" in bsdf.inputs:
        bsdf.inputs["Specular"].default_value = 0.5 if metallic > 0.5 else 0.22
    if alpha < 1.0:
        material.blend_method = "BLEND"
        try:
            material.use_backface_culling = False
        except AttributeError:
            pass
    _MATERIALS[name] = material
    return material


# ------------------------------------------------------------------ 基础几何


def _link(obj, col):
    (col or bpy.context.scene.collection).objects.link(obj)
    return obj


def mesh_object(name: str, verts, faces, material: str, col=None, smooth=False):
    """从顶点/面建网格。verts 是网页坐标三元组列表。"""
    mesh = bpy.data.meshes.new(name)
    bl_verts = [vlist(*v) for v in verts]
    mesh.from_pydata(bl_verts, [], faces)
    mesh.validate(verbose=False)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat(material))
    _link(obj, col)
    if smooth:
        for poly in mesh.polygons:
            poly.use_smooth = True
    return obj


def box(name, cx, cy, cz, sx, sy, sz, material, col=None, rot_z=0.0):
    """轴对齐盒体；cx/cy/cz 为网页坐标中心，sx/sy/sz 为全尺寸（x/高度/进深）。"""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    cos_r = math.cos(rot_z)
    sin_r = math.sin(rot_z)
    corners = []
    for dx in (-hx, hx):
        for dz in (-hz, hz):
            wx = cx + dx * cos_r - dz * sin_r
            wz = cz + dx * sin_r + dz * cos_r
            for dy in (-hy, hy):
                corners.append((wx, cy + dy, wz))
    # 顶点顺序必须与面索引对应
    v = [
        corners[0], corners[1], corners[2], corners[3],   # dx=-hx
        corners[4], corners[5], corners[6], corners[7],   # dx=+hx
    ]
    faces = [
        (0, 1, 3, 2), (4, 6, 7, 5),
        (0, 4, 5, 1), (2, 3, 7, 6),
        (0, 2, 6, 4), (1, 5, 7, 3),
    ]
    return mesh_object(name, v, faces, material, col)


def cylinder(name, cx, cy, cz, radius, height, material, col=None, axis="y", seg=16):
    """圆柱；axis='y' 竖直，'x'/'z' 水平。cy 是底面中心。"""
    verts = []
    faces = []
    half = height / 2
    for i in range(seg):
        a = (i / seg) * math.tau
        c = math.cos(a) * radius
        s = math.sin(a) * radius
        if axis == "y":
            verts.append((cx + c, cy - half, cz + s))
            verts.append((cx + c, cy + half, cz + s))
        elif axis == "x":
            verts.append((cx - half, cy + c, cz + s))
            verts.append((cx + half, cy + c, cz + s))
        else:
            verts.append((cx + c, cy + s, cz - half))
            verts.append((cx + c, cy + s, cz + half))
    for i in range(seg):
        a0 = i * 2
        a1 = ((i + 1) % seg) * 2
        faces.append((a0, a1, a1 + 1, a0 + 1))
    faces.append(tuple(range(0, seg * 2, 2))[::-1])
    faces.append(tuple(range(1, seg * 2, 2)))
    return mesh_object(name, verts, faces, material, col, smooth=True)


def ring(name, cx, cy, cz, r_outer, r_inner, height, material, col=None, seg=24):
    """圆环（井口护栏、香炉口沿等），竖直轴向。"""
    verts = []
    faces = []
    for i in range(seg):
        a = (i / seg) * math.tau
        c, s = math.cos(a), math.sin(a)
        for r in (r_outer, r_inner):
            for y in (0.0, height):
                verts.append((cx + c * r, cy + y, cz + s * r))
    for i in range(seg):
        n = (i + 1) % seg
        for k in range(2):  # 外圈 / 内圈
            a0 = i * 4 + k * 2
            b0 = n * 4 + k * 2
            faces.append((a0, b0, b0 + 1, a0 + 1))
        # 顶面
        faces.append((i * 4, n * 4, n * 4 + 2, i * 4 + 2))
        # 底面
        faces.append((i * 4 + 1, i * 4 + 3, n * 4 + 3, n * 4 + 1))
    return mesh_object(name, verts, faces, material, col, smooth=True)


def poly_prism(name, points_xy, y0, y1, material, col=None):
    """二维多边形（网页 x/z）沿高度拉伸。"""
    n = len(points_xy)
    verts = [(x, y0, z) for x, z in points_xy] + [(x, y1, z) for x, z in points_xy]
    faces = []
    faces.append(tuple(range(n - 1, -1, -1)))
    faces.append(tuple(range(n, n * 2)))
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))
    return mesh_object(name, verts, faces, material, col)


# ------------------------------------------------------------------ 屋面


def roof_height(x: float, z: float, half_x: float, half_z: float, ridge_half: float,
                y_eave: float, y_ridge: float, curve: float = 1.35,
                corner_lift: float = 0.22) -> float:
    """庑殿顶高度场（正确版）。

    四坡顶的高度 = 檐口高度 + 坡度 × 到最近檐口的距离，再截断到脊高：

        h = y_eave + slope * min(half_z - |z|, half_x - |x|),  h <= y_ridge

    因为面阔（x）比进深（z）大，截断后剩下的是一条**沿 x 的正脊**，
    长度自动等于 2*(half_x - half_z)；四条垂脊就是两个坡面的交线。
    最后叠加「举折」（越靠脊越陡）与**檐角起翘**（越靠角部越高）。

    之前误用 max(...) 取范数，得到的是攒尖圆顶——屋顶看起来像穹顶就是这个原因。
    """
    slope = (y_ridge - y_eave) / half_z
    d = max(0.0, min(half_z - abs(z), half_x - abs(x)))
    h = min(y_ridge, y_eave + slope * d)
    t = (h - y_eave) / max(1e-6, (y_ridge - y_eave))
    t = min(1.0, max(0.0, t))
    base = y_eave + (y_ridge - y_eave) * (t ** curve)
    if corner_lift and t < 0.999:
        u = abs(x) / half_x
        v = abs(z) / half_z
        # 只在檐口附近（t 小）抬起，脊部不受影响；角部权重用高次方保持中段平直
        base += corner_lift * ((u * v) ** 2.4) * ((1.0 - t) ** 1.2)
    return base


def roof_surface(name, half_x, half_z, ridge_half, y_eave, y_ridge,
                 material, col=None, nx=30, nz=26, curve=1.35, thickness=0.14,
                 smooth=False):
    """生成一整片庑殿屋面（带厚度），返回对象。

    默认 flat shading：举折曲面靠细分表达，垂脊是坡面交线，必须保持锐利；
    用 smooth 会把四条垂脊平滑掉，屋顶就变成「穹顶」了。
    """
    xs = [-half_x + (2 * half_x) * (i / nx) for i in range(nx + 1)]
    zs = [-half_z + (2 * half_z) * (j / nz) for j in range(nz + 1)]
    verts = []
    for z in zs:
        for x in xs:
            verts.append((x, roof_height(x, z, half_x, half_z, ridge_half, y_eave, y_ridge, curve), z))
    faces = []
    row = nx + 1
    for j in range(nz):
        for i in range(nx):
            a = j * row + i
            b = a + 1
            c = a + row + 1
            d = a + row
            faces.append((a, b, c, d))
    obj = mesh_object(name, verts, faces, material, col, smooth=smooth)
    if thickness > 0:
        solid = obj.modifiers.new("Solid", "SOLIDIFY")
        solid.thickness = thickness
        solid.offset = -1.0
        solid.use_even_offset = True
    return obj


def tile_ridges(prefix, half_x, half_z, ridge_half, y_eave, y_ridge,
                material, col=None, spacing=0.42, width=0.16, lift=0.05, curve=1.35):
    """瓦垄：沿坡向的窄条带，抬离屋面上表面一点，形成可读的瓦纹。

    必须按坡面分段：一条瓦垄从檐口铺到正脊就该停，跨过脊线继续铺到另一坡，
    方向就乱了（早期版本里那圈放射状黑线就是这么来的）。
    """
    objects = []
    # 前后坡：固定 x，沿 z 从檐口铺到正脊
    count_x = int((2 * half_x) / spacing)
    for i in range(count_x):
        x = -half_x + spacing * (i + 0.5)
        for zsign in (1, -1):
            pts = []
            steps = 12
            for k in range(steps + 1):
                z = zsign * half_z * (k / steps)
                y = roof_height(x, z, half_x, half_z, ridge_half, y_eave, y_ridge, curve) + lift
                pts.append((x, y, z))
            objects.append(_ribbon("%s_X%03d_%d" % (prefix, i, zsign), pts, width, material, col))
    # 左右山面：固定 z，沿 x 从檐口铺到正脊端
    count_z = int((2 * half_z) / spacing)
    for i in range(count_z):
        z = -half_z + spacing * (i + 0.5)
        for xsign in (1, -1):
            pts = []
            steps = 12
            for k in range(steps + 1):
                x = xsign * half_x * (k / steps)
                y = roof_height(x, z, half_x, half_z, ridge_half, y_eave, y_ridge, curve) + lift
                pts.append((x, y, z))
            objects.append(_ribbon("%s_Z%03d_%d" % (prefix, i, xsign), pts, width, material, col))
    return objects


def _ribbon(name, pts, width, material, col=None):
    """沿折线生成一条微凸的窄瓦条。"""
    verts = []
    faces = []
    half = width / 2
    for idx, (x, y, z) in enumerate(pts):
        if idx < len(pts) - 1:
            nx, _, nz = pts[idx + 1]
            tx, tz = nx - x, nz - z
        else:
            px, _, pz = pts[idx - 1]
            tx, tz = x - px, z - pz
        length = math.hypot(tx, tz) or 1.0
        # 水平法向
        ox, oz = -tz / length * half, tx / length * half
        verts.append((x + ox, y - 0.012, z + oz))
        verts.append((x, y + 0.014, z))
        verts.append((x - ox, y - 0.012, z - oz))
    for i in range(len(pts) - 1):
        a = i * 3
        b = (i + 1) * 3
        faces.append((a, b, b + 1, a + 1))
        faces.append((a + 1, b + 1, b + 2, a + 2))
    return mesh_object(name, verts, faces, material, col, smooth=True)


def eave_trim(prefix, half_x, half_z, y, material, col=None, droop=0.16):
    """檐口封边：沿四周的折线带，略向下收，遮住屋面板厚。"""
    ring_pts = []
    steps = 12
    # 前/后檐
    for i in range(steps + 1):
        x = -half_x + (2 * half_x) * (i / steps)
        ring_pts.append((x, y, half_z))
    for i in range(steps + 1):
        x = half_x - (2 * half_x) * (i / steps)
        ring_pts.append((x, y, -half_z))
    pts = [(x, yy, z) for x, yy, z in ring_pts]
    pts.append(pts[0])
    obj = _ribbon(prefix, pts, 0.16, material, col)
    obj.location.y -= droop
    return obj


def band_along(name, points, width, material, col=None):
    """沿一条三维折线生成窄脊带（瓦脊 / 封边），公开给 build 脚本使用。"""
    return _ribbon(name, points, width, material, col)


def eave_band(prefix, half_x, half_z, ridge_half, y_eave, y_ridge,
              material, col=None, width=0.12, curve=1.35, corner_lift=0.22):
    """檐口封边：沿整个檐口起伏（含檐角起翘），盖住屋面板的厚度。

    四条边分别生成独立的脊带，而不是首尾相连的一整圈：
    环状折线在转角处两段方向跳变，_ribbon 的水平法向会在角部歪出去，
    看起来像四根伸出来的黑刺。
    """
    steps = 26
    edges = [
        lambda t: (-half_x + 2 * half_x * t, half_z),
        lambda t: (half_x, half_z - 2 * half_z * t),
        lambda t: (half_x - 2 * half_x * t, -half_z),
        lambda t: (-half_x, -half_z + 2 * half_z * t),
    ]
    objects = []
    for index, fn in enumerate(edges):
        pts = []
        for i in range(steps + 1):
            x, z = fn(i / steps)
            y = roof_height(x, z, half_x, half_z, ridge_half, y_eave, y_ridge, curve, corner_lift) - 0.05
            pts.append((x, y, z))
        objects.append(_ribbon("%s_%d" % (prefix, index), pts, width, material, col))
    return objects


def ring_hip(name, ix, iz, ox, oz, y_in, y_out, material, col=None,
             ntheta=72, nt=4, thickness=0.12, corner_lift=0.18):
    """矩形环状坡屋面（腰檐 / 下檐）。

    内矩形 (ix, iz, y_in) 贴墙，外矩形 (ox, oz, y_out) 是檐口。
    用「正方形边界方向 -> 矩形求交」参数化，保证角部斜接干净、不重叠。
    外沿四角做一点起翘，免得腰檐看起来像一只平盘子。
    """
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
            if corner_lift:
                y += corner_lift * ((abs(x) / ox) * (abs(z) / oz)) ** 2.4 * t
            verts.append((x, y, z))

    faces = []
    row = nt + 1
    for j in range(ntheta):
        nj = (j + 1) % ntheta
        for i in range(nt):
            a0 = j * row + i
            b0 = nj * row + i
            faces.append((a0, b0, b0 + 1, a0 + 1))
    obj = mesh_object(name, verts, faces, material, col, smooth=True)
    if thickness > 0:
        solid = obj.modifiers.new("Solid", "SOLIDIFY")
        solid.thickness = thickness
        solid.offset = -1.0
        solid.use_even_offset = True
    return obj


# ------------------------------------------------------------------ 组合


def join_objects(objects, name, col=None):
    """合并同类构件，降低 draw call；返回合并后的对象。"""
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


def mirror_x(obj, name):
    """按 x 轴镜像一份（左右对称构件）。"""
    dup = obj.copy()
    dup.data = obj.data.copy()
    dup.name = name
    for child in obj.children:
        pass
    bpy.context.scene.collection.objects.link(dup)
    dup.scale.x = -1
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    dup.select_set(True)
    bpy.context.view_layer.objects.active = dup
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return dup


def empty(name, x, y, z, props=None, col=None, rotation_y=0.0):
    """空物体锚点。

    法线约定：**局部 -Y 指向房间内侧**。
    Blender 绕 Z 轴转 θ 时，局部 -Y 变成 (sinθ, -cosθ, 0)；
    转成 three.js 坐标（x, z, -y）正好是 (sinθ, 0, cosθ)，
    也就是前端约定的 rotationY = θ。所以直接把网页 rotationY 写进 rotation_euler.z，
    导出脚本再用局部 -Y 反推即可（早先导出用了 +Y，导致展墙法线全部朝反、
    画框会翻到墙背面）。
    """
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.4
    obj.location = (x, -z, y)
    obj.rotation_euler = (0.0, 0.0, rotation_y)
    _link(obj, col)
    if props:
        for key, value in props.items():
            obj[key] = value
    return obj