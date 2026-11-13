"""v13 环境：纯净澄澈的蓝天碧云 + 暖金日光（只服务 Blender 出图，不进 GLB）。

- 天穹：半径 900m 球壳 + 顶点/Generated 竖直渐变（天顶 #4B8EC7 → 地平线 #F5F0E6）
- 祥云：程序化生成 1024×512 柔边云纹 alpha 贴图，7 朵横向舒展的白云
- 云海：台基底缘下方一层极淡云面，遮住 80×96 台基的下口，不形成"地面"
- 阳光：5600K，南偏西 35°，高度角 38°
- 室内：五馆各一盏暖白面光（EEVEE 半球天空不参与漫射，必须实体补光）

本模块不做任何假山、雾幔、草坪或外围地坪。
"""
from __future__ import annotations

import math
import random

import bmesh
import bpy
from mathutils import Vector

SKY_DOME = "SKY13_DOME"
CLOUD_TEX = "SKY13_CLOUD_TEX"


# ---------------------------------------------------------------- 贴图
def _cloud_image(w=1024, h=512, seed=13):
    """柔边祥云 alpha 贴图：若干椭圆高斯叠加 + 边缘淡出，纯白偏暖。"""
    import numpy as np

    rng = random.Random(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    field = np.zeros((h, w), dtype=np.float32)
    # 5~7 团横向舒展的云体
    for _ in range(7):
        cx = rng.uniform(0.14, 0.86) * w
        cy = rng.uniform(0.32, 0.68) * h
        rx = rng.uniform(0.10, 0.20) * w
        ry = rx * rng.uniform(0.30, 0.46)
        k = rng.uniform(0.55, 1.0)
        # 每团由 3~5 个错位椭圆组成，形成舒展的如意形
        for _ in range(rng.randint(3, 5)):
            ox = cx + rng.uniform(-0.55, 0.55) * rx
            oy = cy + rng.uniform(-0.35, 0.35) * ry * 2.0
            rrx = rx * rng.uniform(0.45, 0.85)
            rry = ry * rng.uniform(0.55, 1.0)
            field += k * np.exp(-(((xx - ox) / rrx) ** 2 + ((yy - oy) / rry) ** 2) * 1.35)

    # 边缘淡出，避免平面硬切
    u = xx / (w - 1.0)
    v = yy / (h - 1.0)
    border = np.minimum(np.minimum(u, 1.0 - u) * 4.0, np.minimum(v, 1.0 - v) * 4.0)
    border = np.clip(border, 0.0, 1.0)
    field *= border

    alpha = np.clip((field - 0.42) * 1.9, 0.0, 1.0)
    alpha = alpha ** 1.15
    # 云顶微暖、云脚微青
    warm = np.clip(field * 0.6, 0.0, 1.0)
    rgb = np.stack([
        1.0 - 0.04 * warm,
        0.985 - 0.012 * warm,
        0.955 + 0.035 * (1.0 - warm),
    ], axis=-1)

    buf = np.concatenate([rgb, alpha[..., None]], axis=-1).astype(np.float32)
    img = bpy.data.images.get(CLOUD_TEX)
    if img is not None:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(CLOUD_TEX, w, h, alpha=True)
    img.pixels.foreach_set(buf.ravel())
    img.pack()
    return img


def _cloud_material(img):
    mat = bpy.data.materials.get("SKY13_CLOUD_MAT") or bpy.data.materials.new("SKY13_CLOUD_MAT")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (620, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.location = (-140, 0)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    if "Emission Color" in bsdf.inputs:
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 0.55
    else:
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission"])
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Metallic"].default_value = 0.0
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    for attr, val in (("blend_method", "BLEND"), ("surface_render_method", "BLENDED"),
                      ("use_backface_culling", False)):
        try:
            setattr(mat, attr, val)
        except Exception:
            pass
    return mat


# ---------------------------------------------------------------- 天穹
def _dome(sc, radius=900.0, segs=72, rings=36):
    old = bpy.data.objects.get(SKY_DOME)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)

    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius)
    # 天穹是从内部观看的：必须把法线翻向球心。外法线的球壳在 EEVEE 里会盖住室内
    # 一切几何（内景渲染成一片天空），翻面后深度与遮挡才正确。
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(SKY_DOME)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(SKY_DOME, me)
    ob.hide_select = True
    sc.collection.objects.link(ob)

    mat = bpy.data.materials.get("SKY13_DOME_MAT") or bpy.data.materials.new("SKY13_DOME_MAT")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (520, 0)
    emi = nt.nodes.new("ShaderNodeEmission")
    emi.location = (320, 0)
    emi.inputs["Strength"].default_value = 1.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (60, 0)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-240, 0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-80, 0)
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], emi.inputs["Color"])
    nt.links.new(emi.outputs["Emission"], out.inputs["Surface"])

    els = ramp.color_ramp.elements
    # Generated.Z：球体包围盒 0→1，地平线在 0.5；观众只见 0.5~1.0
    els[0].position = 0.0
    els[0].color = (0.961, 0.941, 0.902, 1.0)      # 下半球（不可见）暖宣纸
    els[1].position = 1.0
    els[1].color = (0.184, 0.431, 0.651, 1.0)      # 天顶深碧 #2F6EA6
    for (pos, rgb) in (
        (0.500, (0.961, 0.941, 0.902, 1.0)),       # 地平 #F5F0E6
        (0.506, (0.949, 0.937, 0.910, 1.0)),       # 地平暖带只留 0.6° 左右
        (0.520, (0.812, 0.890, 0.929, 1.0)),       # 近地天青 #CFE3ED
        (0.560, (0.498, 0.702, 0.851, 1.0)),       # #7FB3D9
        (0.640, (0.294, 0.557, 0.780, 1.0)),       # #4B8EC7 主天青
        (0.800, (0.227, 0.490, 0.722, 1.0)),       # #3A7DB8
        (0.920, (0.184, 0.431, 0.651, 1.0)),       # #2F6EA6 天顶深碧
    ):
        e = els.new(pos)
        e.color = rgb
    nt.links.new(emi.outputs["Emission"], out.inputs["Surface"])
    try:
        ob.data.materials.append(mat)
    except Exception:
        pass
    ob.visible_diffuse = False
    ob.visible_glossy = False
    # 关键：天穹是包住全场的 900m 球壳，若参与阴影计算会把太阳光整片挡住，
    # 全场只剩 0.46 的青蓝世界光 → 屋顶发黑、没有投影。必须关掉投影。
    ob.visible_shadow = False
    ob.hide_render = False
    return ob


# ---------------------------------------------------------------- 祥云
def _clouds(sc, d, img, mat):
    old = [o for o in sc.objects if o.name.startswith("SKY13_CLOUD_")]
    for o in old:
        bpy.data.objects.remove(o, do_unlink=True)

    cfg = d.SKY
    rng = random.Random(1313)
    n = int(cfg["clouds"])
    made = 0
    for i in range(n):
        az = math.radians(rng.uniform(-180.0, 180.0))
        dist = rng.uniform(90.0, 230.0)
        z = rng.uniform(34.0, 72.0)
        w = rng.uniform(56.0, 118.0)
        h = w * rng.uniform(0.42, 0.58)
        bm = bmesh.new()
        # 水平舒展的长方形（底面朝下，观众仰视即见祥云）
        verts = [bm.verts.new((-w / 2, -h / 2, 0.0)), bm.verts.new((w / 2, -h / 2, 0.0)),
                 bm.verts.new((w / 2, h / 2, 0.0)), bm.verts.new((-w / 2, h / 2, 0.0))]
        bm.faces.new(verts)
        me = bpy.data.meshes.new(f"SKY13_CLOUD_{i:02d}")
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(f"SKY13_CLOUD_{i:02d}", me)
        ob.location = (math.cos(az) * dist, math.sin(az) * dist, z)
        ob.rotation_euler = (math.radians(rng.uniform(-4.0, 4.0)),
                             math.radians(rng.uniform(-4.0, 4.0)),
                             math.radians(rng.uniform(0.0, 360.0)))
        me.materials.append(mat)
        ob.visible_shadow = False
        sc.collection.objects.link(ob)
        made += 1
    print(f"[sky] 祥云 {made} 朵 / 天穹渐变 #4B8EC7 → #F5F0E6")


# ---------------------------------------------------------------- 云海
def _cloud_sea(sc, d, img, mat):
    old = bpy.data.objects.get("SKY13_CLOUD_SEA")
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    z = -1.45
    r = 320.0
    bm = bmesh.new()
    segs = 72
    ring = []
    for i in range(segs):
        a = 2.0 * math.pi * i / segs
        ring.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, z)))
    bm.faces.new(ring)
    me = bpy.data.meshes.new("SKY13_CLOUD_SEA")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("SKY13_CLOUD_SEA", me)
    me.materials.append(mat)
    ob.visible_shadow = False
    sc.collection.objects.link(ob)
    return ob


# ---------------------------------------------------------------- 阳光与室内
def _sun(sc, d):
    sun = bpy.data.objects.get("SUN")
    if sun is None:
        ld = bpy.data.lights.new("SUN", "SUN")
        sun = bpy.data.objects.new("SUN", ld)
        sc.collection.objects.link(sun)
    cfg = d.SKY
    ld = sun.data
    ld.energy = 3.9
    ld.angle = math.radians(2.6)
    ld.color = (1.0, 0.955, 0.885)          # 5600K 暖白金黄
    alt = math.radians(float(cfg["sun_elev"]))
    az = math.radians(180.0 - float(cfg["sun_azim"]))   # 215° → 正南偏西 35°
    dist = 120.0
    sun.location = (dist * math.cos(alt) * math.sin(az),
                    -dist * math.cos(alt) * math.cos(az),
                    dist * math.sin(alt))
    dvec = Vector((0.0, 0.0, 4.0)) - Vector(sun.location)
    sun.rotation_euler = dvec.to_track_quat("-Z", "Y").to_euler()
    print(f"[sky] 日光 5600K 高度角 {cfg['sun_elev']}° 方位 {cfg['sun_azim']}°")


def _hall_lights(sc, d):
    """五馆 + 主殿 + 连廊暖白补光（仅 Blender 出图）。"""
    for name in ("P13_KM", "P13_CH", "P13_ZJ", "P13_SJ", "P13_LJ",
                 "P13_KM2", "P13_CH2", "P13_ZJ2", "P13_SJ2",
                 "P13_MAIN", "P13_MAIN_DN"):
        ob = bpy.data.objects.get(name)
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)

    specs = [
        # 主殿：一盏向上打亮 11 层藻井，一盏向下补地面（原单盏向下，藻井全黑）
        ("P13_MAIN", (0.0, 6.0, 1.20), (0.0, 6.0, 13.0), 9.0, 420.0, False),
        ("P13_MAIN_DN", (0.0, 9.0, 8.60), (0.0, 9.0, 0.30), 9.0, 260.0, True),
        ("P13_KM", (-32.0, -30.0, 3.70), (-32.0, -28.40, 0.90), 7.0, 130.0, False),
        ("P13_CH", (-32.0, -12.0, 3.70), (-32.0, -10.40, 0.90), 7.0, 130.0, False),
        ("P13_ZJ", (32.0, -30.0, 3.70), (32.0, -28.40, 0.90), 7.0, 130.0, False),
        ("P13_SJ", (32.0, -12.0, 3.70), (32.0, -10.40, 0.90), 7.0, 130.0, False),
        ("P13_LJ", (-20.0, -42.0, 2.70), (-20.0, -40.40, 0.80), 5.0, 85.0, False),
        # 第二盏弱补光：贴墙侧洗墙，压掉檐下死黑（不投影）
        ("P13_KM2", (-32.0, -34.60, 3.30), (-32.0, -33.00, 1.60), 5.0, 60.0, False),
        ("P13_CH2", (-32.0, -16.60, 3.30), (-32.0, -15.00, 1.60), 5.0, 60.0, False),
        ("P13_ZJ2", (32.0, -34.60, 3.30), (32.0, -33.00, 1.60), 5.0, 60.0, False),
        ("P13_SJ2", (32.0, -16.60, 3.30), (32.0, -15.00, 1.60), 5.0, 60.0, False),
    ]
    for name, loc, look, size, energy, shadow in specs:
        ld = bpy.data.lights.new(name, "AREA")
        ld.shape = "SQUARE"
        ld.size = size
        ld.energy = energy
        ld.color = (1.0, 0.935, 0.855)
        ld.use_shadow = shadow
        ob = bpy.data.objects.new(name, ld)
        ob.location = Vector(loc)
        ob.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(ob)
    print(f"[sky] 室内暖白面光 {len(specs)} 盏")


def _world():
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    out.location = (300, 0)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.location = (80, 0)
    bg.inputs["Color"].default_value = (0.62, 0.76, 0.90, 1.0)   # 天青环境光
    bg.inputs["Strength"].default_value = 0.46
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def build_sky(sc, dim):
    img = _cloud_image()
    mat = _cloud_material(img)
    _dome(sc)
    _clouds(sc, dim, img, mat)
    _cloud_sea(sc, dim, img, mat)
    _sun(sc, dim)
    _hall_lights(sc, dim)
    _world()
    try:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        pass
    try:
        sc.eevee.use_raytracing = True
    except Exception:
        pass
    print("[sky] 蓝天碧云环境完成（天穹 / 7 朵祥云 / 云海 / 日光 / 室内补光）")