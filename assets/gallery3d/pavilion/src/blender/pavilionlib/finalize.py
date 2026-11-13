"""装配后处理 —— 合并网格 / UV1 / AO 烘焙 / GLB 导出 / manifest。

管线顺序（不可乱）：
    build → join_by_material → uv1_lightmap → bake_ao → (textures 生成)
         → reload_textures → save_blend → export_glb → write_manifest
"""
from __future__ import annotations

import json
import os

import bmesh
import bpy
from mathutils import Vector

from . import mesh_util as mu
from .dim import DIM
from .materials import MAT_META, MAT_ORDER


# ============================================================ 场景
def _sky_world(world, strength=1.0):
    """晴空世界：天顶蔚蓝 → 中段淡青 → 地平一抹暖曦（春日晴朗的白昼）。

    用世界法线方向（View 方向）的 Z 分量做竖直渐变，EEVEE / Cycles 通用；
    这不是 HDR，但足以给整场提供冷白天光 + 暖地平反照，配合 SUN 形成明暗层次。
    """
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    out.location = (520, 0)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.location = (330, 0)
    bg.inputs["Strength"].default_value = strength
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (110, 0)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-420, 0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-230, 0)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.location = (-60, 0)
    mr.inputs["From Min"].default_value = -0.35
    mr.inputs["From Max"].default_value = 0.62
    # 地平 → 天顶（饱和度给足：AgX 会把高亮部压灰，太淡就只剩一片白）
    # fac = (sin(仰角)+0.35)/0.97，故 Z=0（地平线）落在 0.36：
    # <0.36 是地平线以下的雾气底面，0.36 是地平暖曦，往上才是蓝天。
    el = ramp.color_ramp.elements
    el[0].position = 0.00
    el[0].color = (0.902, 0.886, 0.839, 1.0)      # #E7E2D6 地平线下雾面
    el[1].position = 0.36
    el[1].color = (0.969, 0.914, 0.808, 1.0)      # #F7E9CE 地平暖曦
    for pos, col in ((0.45, (0.812, 0.875, 0.941)),   # #CFDFF0 地平上方的乳青
                     (0.70, (0.431, 0.608, 0.816)),   # #6E9BD0 中天
                     (1.00, (0.165, 0.337, 0.584))):  # #2A5695 天顶蔚蓝
        e = el.new(pos)
        e.color = (col[0], col[1], col[2], 1.0)

    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


SKY_DOME = "SKY_DOME"


def add_sky_dome(sc, radius=900.0, segs=64, rings=32):
    """渲染用天穹：EEVEE 的世界着色器给不出稳定的竖直天空渐变（实测 TexCoord
    Normal/Generated 都不随仰角线性变化），改为半径 900m 的球壳 + 自发光渐变，
    用网格自带的 Generated.Z 做竖直插值 —— 网格的 Generated 是可靠的锚点。

    只参与出图，不进 GLB：export_glb 只按 objs 清单 + CAM_* 选择对象。
    """
    old = bpy.data.objects.get(SKY_DOME)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)

    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius)
    me = bpy.data.meshes.new(SKY_DOME)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(SKY_DOME, me)
    sc.collection.objects.link(ob)

    mat = bpy.data.materials.get("SKY_DOME_MAT") or bpy.data.materials.new("SKY_DOME_MAT")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (420, 0)
    emi = nt.nodes.new("ShaderNodeEmission")
    emi.location = (230, 0)
    emi.inputs["Strength"].default_value = 1.35
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (10, 0)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-220, 0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-100, 0)
    # 球壳半径 900 → Generated.Z：0.5 = 地平线(z=0)，0.8 ≈ 540m 高
    el = ramp.color_ramp.elements
    el[0].position = 0.470
    el[0].color = (0.839, 0.816, 0.769, 1.0)      # #D6D0C4 地平线下雾面
    el[1].position = 0.505
    el[1].color = (0.980, 0.949, 0.886, 1.0)      # #FAF2E2 暖宣纸本色
    for pos, col in ((0.494, (0.961, 0.875, 0.722)),   # #F5DFB8 朝晖淡金
                     (0.535, (0.812, 0.878, 0.933)),   # #CFE0EE 地平乳青
                     (0.600, (0.624, 0.765, 0.875)),   # #9FC3DF 淡天青
                     (0.700, (0.498, 0.663, 0.804)),   # #7FA9CD 中天青
                     (0.800, (0.419, 0.604, 0.769))):  # #6B9AC4 天顶正天青
        e = el.new(pos)
        e.color = (col[0], col[1], col[2], 1.0)
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], emi.inputs["Color"])
    nt.links.new(emi.outputs["Emission"], out.inputs["Surface"])
    me.materials.append(mat)

    try:
        ob.visible_shadow = False
        ob.visible_diffuse = False
        ob.visible_glossy = True
    except Exception:
        pass
    return ob


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = eng
            break
        except Exception:
            continue
    # EEVEE Next 默认不开光追：水面/石材的屏幕空间反射全靠它
    try:
        # 影子池默认 512（2048 页）会被这套高密度建筑打满，翻倍到 1024
        sc.eevee.shadow_pool_size = "1024"
        sc.eevee.use_raytracing = True
        sc.eevee.ray_tracing_method = "SCREEN"
        sc.eevee.use_shadows = True
    except Exception as e:
        print("[reset] eevee 设置跳过:", e)
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "AgX" if "AgX" in [
        t.name for t in sc.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    sc.view_settings.look = "AgX - Medium High Contrast" if sc.view_settings.view_transform == "AgX" else "None"
    sc.world = bpy.data.worlds.new("WaterCourtWorld")
    sc.world.use_nodes = True
    _sky_world(sc.world, strength=0.85)
    return sc


def add_camera_anchors(sc, dim=None):
    """5 个机位 Empty（Three.js 用 scene.getObjectByName 读取）。

    `dim` 可传入另一套尺寸契约（v10 的 DIM10）；不传则沿用 v6 的 DIM。
    """
    dim = dim or DIM
    made = {}
    for name, spec in dim.CAMERAS.items():
        e = bpy.data.objects.get(name)
        if e is None:
            e = bpy.data.objects.new(name, None)
            e.empty_display_type = "PLAIN_AXES"
            e.empty_display_size = 1.5
            sc.collection.objects.link(e)
        loc = Vector(spec["loc"])
        look = Vector(spec["look"])
        e.location = loc
        e["look_at"] = list(look)
        e["lens"] = spec["lens"]
        e["cn"] = spec["cn"]
        d = (look - loc)
        if d.length > 1e-6:
            e.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        made[name] = e
    return made


def add_lights(sc):
    """日光版：一盏暖白太阳主光（5500K 左右）+ 三盏低强度补光（供 Blender 预览渲染；GLB 不导出灯光）。"""
    def _area(name, loc, look, size, energy, color=(1.0, 0.96, 0.90), shadow=True):
        ld = bpy.data.lights.new(name, "AREA")
        ld.size = size
        ld.energy = energy
        ld.color = color
        ld.use_shadow = shadow
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc
        d = Vector(look) - Vector(loc)
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(ob)
        return ob

    # 补光只负责"把暗部提起来"，主光交给太阳
    _area("KEY_Front", (6.0, -34.0, 22.0), (0, 2, 6), 26.0, 1800, (1.0, 0.95, 0.88), shadow=False)
    _area("FILL_West", (-38.0, -8.0, 14.0), (0, 4, 6), 22.0, 1100, (0.82, 0.90, 1.0), shadow=False)
    _area("RIM_North", (0.0, 30.0, 20.0), (0, 4, 10), 24.0, 900, (0.90, 0.94, 1.0), shadow=False)

    # ---- 室内补光（GLB 不导出灯光，仅服务于 Blender 出图）----
    # EEVEE 的半球天穹不参与漫射（实测 dome.visible_diffuse 开/关像素完全一致，缺光照探针），
    # 所以中庭与连廊的"天光感"必须由实体灯补：天窗透下的光柱 + 地面暖反弹 + 廊下暖灯。
    _area("INT_SkyShaft", (0.0, 9.0, 15.6), (0.0, 9.0, 4.0), 7.0, 1400, (1.0, 0.95, 0.86), shadow=True)
    _area("INT_Bounce", (0.0, 11.0, 1.2), (0.0, 11.0, 10.0), 16.0, 500, (1.0, 0.90, 0.78), shadow=False)
    _area("GAL_E", (14.9, -11.0, 3.6), (14.9, -11.0, -2.0), 9.0, 420, (1.0, 0.92, 0.82), shadow=False)
    _area("GAL_W", (-14.9, -11.0, 3.6), (-14.9, -11.0, -2.0), 9.0, 420, (1.0, 0.92, 0.82), shadow=False)

    sd = bpy.data.lights.new("SUN", "SUN")
    sd.energy = 5.6
    sd.angle = 0.030
    sd.color = (1.0, 0.961, 0.894)          # #FFF5E4 纯净暖白金阳（约 5600K）
    so = bpy.data.objects.new("SUN", sd)
    # 晴和天章：南偏西 35°、高度角 52°。水平方向 (-sin35, -cos35) 指向西南，
    # 高度 cos52 水平 / sin52 垂直，取距离 110m → (-38.9, -55.4, 86.7)。
    import math as _m
    _az = _m.radians(35.0)      # 自正南向西偏
    _alt = _m.radians(52.0)
    _d = 110.0
    so.location = (
        -_d * _m.cos(_alt) * _m.sin(_az),
        -_d * _m.cos(_alt) * _m.cos(_az),
        _d * _m.sin(_alt),
    )
    d = Vector((0.0, 0.0, 6.0)) - Vector(so.location)
    so.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(so)
    return so


# ============================================================ 合并
def merge_meshes(objs, name, cat, cn=""):
    """把多个对象按世界坐标合并成一个 bmesh 网格（单一材质槽）。"""
    objs = [o for o in objs if o and o.type == "MESH" and o.name in bpy.data.objects]
    if not objs:
        return None
    mats = []
    for o in objs:
        for m in o.data.materials:
            if m and m not in mats:
                mats.append(m)
    bm = bmesh.new()
    for ob in objs:
        n0 = len(bm.verts)
        bm.from_mesh(ob.data)
        bm.verts.ensure_lookup_table()
        M = ob.matrix_world
        for vt in bm.verts[n0:]:
            vt.co = M @ vt.co
    if len(bm.verts) == 0:
        bm.free()
        return None
    for f in bm.faces:
        f.material_index = 0
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mats:
        me.materials.append(mats[0])
    ob["cat"] = cat
    ob["cn"] = cn
    ob["merged_from"] = len(objs)
    for o in list(objs):
        if o.name in bpy.data.objects:
            bpy.data.objects.remove(o, do_unlink=True)
    return ob


def _material_sections(ob):
    """Partition a multi-material construction mesh after contact auditing, preserving UVs."""
    slots = ob.data.materials
    if len(slots) < 2:
        return [ob]
    portions = []
    for index in sorted({poly.material_index for poly in ob.data.polygons}):
        material = slots[index]
        if material is None:
            raise ValueError(f"{ob.name} has faces with an empty material slot {index}")
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        remove = [face for face in bm.faces if face.material_index != index]
        bmesh.ops.delete(bm, geom=remove, context="FACES")
        for face in bm.faces:
            face.material_index = 0
        mesh = bpy.data.meshes.new(f"{ob.name}_{material.name}")
        bm.to_mesh(mesh)
        bm.free()
        mesh.materials.append(material)
        section = bpy.data.objects.new(mesh.name, mesh)
        bpy.context.scene.collection.objects.link(section)
        section.matrix_world = ob.matrix_world.copy()
        portions.append(section)
    bpy.data.objects.remove(ob, do_unlink=True)
    return portions


def join_by_material(C, grp=None, suffix=""):
    """按材质 key 合并 —— 全场景 Mesh 数 ≈ 材质数（≤40，任务书 §3.2）。

    grp 参数用于把场景拆成两大分支（终局精修 §5）：
      grp="arch"  → 建筑本体（默认，包含所有没有 grp 标记的部件）
      grp="macro" → 600m 镜湖 / 远山 / 薄雾 / 层云（environment.py 打的标记）
    两组的 MESH 名字用 suffix 区分，避免同名冲突（MESH_water / MESH_water_macro）。
    """
    groups: dict[str, list] = {}
    for ob in C.objects:
        if ob is None:
            continue
        # 分两趟合批时，第一趟 merge_meshes 已经把源对象删掉了，
        # 这里再访问它的 .name / .type 会抛 ReferenceError（StructRNA removed）。
        try:
            if ob.name not in bpy.data.objects or ob.type != "MESH":
                continue
            obgrp = ob.get("grp", "arch")
            if grp is not None and obgrp != grp:
                continue
        except ReferenceError:
            continue
        if grp is not None and (ob.get("grp") or "arch") != grp:
            continue
        for section in _material_sections(ob):
            mat = next((m for m in section.data.materials if m), None)
            key = (mat.get("key") or mat.name) if mat else "misc"
            groups.setdefault(key, []).append(section)
    out = {}
    for key, objs in groups.items():
        cn = MAT_META.get(key, (key,))[0] if key in MAT_META else key
        ob = merge_meshes(objs, f"MESH_{key}{suffix}", _cat_of(key), cn)
        if ob is not None:
            out[key] = ob
    return out


def add_groups(arch_objs, macro_objs, anchors=(), cams=()):
    """把场景根组织成两大分支（终局精修 §5），前端据此精准取景。

    GRP_Pavilion_Architecture : 66m 建筑复合体 + 桥梁 + 近景庭院 + 5 个机位 + FRAME_* 锚点
    GRP_Macro_Environment     : 600m 镜湖 + 远山 + 薄雾 + 流云

    用 matrix_parent_inverse 抵消父级变换，保证所有 mesh 的世界坐标一动不动。
    """
    sc = bpy.context.scene
    made = {}
    for name, members in (
        ("GRP_Pavilion_Architecture", list(arch_objs) + list(anchors) + list(cams)),
        ("GRP_Macro_Environment", list(macro_objs)),
    ):
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "PLAIN_AXES"
        e.empty_display_size = 5.0
        e["grp"] = "arch" if "Pavilion" in name else "macro"
        sc.collection.objects.link(e)
        for ob in members:
            if ob is None or ob.name not in bpy.data.objects:
                continue
            ob.parent = e
            ob.matrix_parent_inverse = e.matrix_world.inverted()
        made[name] = e
        print(f"[grp] {name}: {len(members)} 个子节点")
    return made


def _cat_of(key):
    return {
        "wood_dark": "hall", "wood_lite": "interior", "wall_white": "interior",
        "roof_dai": "roof", "stone_dark": "foundation", "stone_lite": "foundation",
        "water": "water", "glass": "gallery", "bronze": "detail",
        "lightstrip": "detail", "foliage": "detail",
    }.get(key, "misc")


# ============================================================ UV1
def uv1_lightmap(objs, margin_div=0.02):
    """为每个对象建立非重叠 UVChannel 1（供 AO 烘焙）。"""
    done = []
    for ob in objs:
        if ob.type != "MESH" or ob.name not in bpy.data.objects:
            continue
        me = ob.data
        while len(me.uv_layers) < 2:
            me.uv_layers.new(name="UVMap2" if len(me.uv_layers) == 1 else "UVMap")
        if me.uv_layers[0].name != "UVMap":
            me.uv_layers[0].name = "UVMap"
        me.uv_layers[1].name = "UVMap2"
        me.uv_layers[1].active = True
        me.uv_layers[1].active_render = True
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        try:
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES",
                                     PREF_PACK_IN_ONE=True,
                                     PREF_NEW_UVLAYER=False,
                                     PREF_MARGIN_DIV=margin_div)
            bpy.ops.object.mode_set(mode="OBJECT")
            done.append(ob.name)
        except Exception as e:
            try:
                bpy.ops.object.mode_set(mode="OBJECT")
            except Exception:
                pass
            print(f"[uv1] {ob.name} lightmap_pack 失败: {e}")
    print(f"[uv1] 完成 {len(done)}/{len(objs)}")
    return done


# ============================================================ AO 烘焙
def bake_ao(objs, tex_dir, samples=24, margin=6, only=None, reuse=False, skip=()):
    """Cycles 烘焙软 AO 到 <tex_dir>/ao_<key>.png（2048 / 1024 按材质档次）。

    reuse=True 时，已存在且非空的 ao_<key>.png 直接复用，跳过重烘（迭代省 8~10 分钟）。
    """
    os.makedirs(tex_dir, exist_ok=True)
    sc = bpy.context.scene
    _keep = (sc.render.engine, sc.view_settings.view_transform, sc.view_settings.look)
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 1
    rb = sc.render.bake
    rb.margin = margin
    rb.use_clear = True
    rb.use_selected_to_active = False
    for attr in ("use_pass_direct", "use_pass_indirect", "use_pass_color"):
        if hasattr(rb, attr):
            setattr(rb, attr, False)

    results = {}
    for ob in objs:
        if ob is None or ob.type != "MESH" or ob.name not in bpy.data.objects:
            continue
        key = ob.data.materials[0].get("key") if ob.data.materials else None
        if key is None:
            continue
        if only and key not in only:
            continue
        if key in skip:
            print(f"[ao] {key} 跳过（skip 列表：自发光/介质类不需 AO）")
            continue
        size = MAT_META.get(key, ("", "", 0, 0, 1024))[4]
        old = os.path.join(tex_dir, f"ao_{key}.png")
        if reuse and os.path.exists(old) and os.path.getsize(old) > 4096:
            results[key] = {"path": old, "size": size, "sec": 0.0, "reused": True}
            print(f"[ao] {key} 复用已有 {old}")
            continue
        img = bpy.data.images.get(f"AO_{key}")
        if img:
            bpy.data.images.remove(img)
        img = bpy.data.images.new(f"AO_{key}", size, size, alpha=False, float_buffer=False)
        img.colorspace_settings.name = "Non-Color"
        nt = ob.data.materials[0].node_tree
        node = nt.nodes.new("ShaderNodeTexImage")
        node.name = "BAKE_TARGET"
        node.image = img
        node.select = True
        nt.nodes.active = node

        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        t0 = __import__("time").time()
        try:
            bpy.ops.object.bake(type="AO")
            path = os.path.join(tex_dir, f"ao_{key}.png")
            img.filepath_raw = path
            img.file_format = "PNG"
            img.save()
            dt = __import__("time").time() - t0
            results[key] = {"path": path, "size": size, "sec": round(dt, 1)}
            print(f"[ao] {key} {size}px {dt:.1f}s -> {path}")
        except Exception as e:
            print(f"[ao] {key} 失败: {e}")
        finally:
            nt.nodes.remove(node)
    # 烘焙会把引擎切到 CYCLES / 色彩管理切到 Filmic：存盘前还原成 EEVEE + AgX，
    # 否则交付的 .blend 打开是 Cycles 视图，与渲染图观感不一致。
    try:
        sc.render.engine, sc.view_settings.view_transform, sc.view_settings.look = _keep
    except Exception:
        pass
    return results


# ============================================================ 导出
def export_glb(path, objs, draco=False):
    bpy.ops.object.select_all(action="DESELECT")
    n = 0
    for ob in objs:
        if ob and ob.name in bpy.data.objects:
            ob.select_set(True)
            n += 1
    # 机位 Empty 必须一起导出：Three.js 端用 scene.getObjectByName("CAM_...") 取机位
    # GRP_* 分组节点与 FRAME_* 展陈锚点同理（前端要按名取组、按名贴画）
    for ob in bpy.context.scene.objects:
        if ob.type == "EMPTY" and (
                ob.name.startswith("CAM_")
                or ob.name.startswith("GRP_")
                or ob.name.startswith("FRAME_")
                or ob.name.startswith("SNAP_")):
            ob.select_set(True)
            n += 1
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if meshes:
        bpy.context.view_layer.objects.active = meshes[0]
    base = dict(filepath=path, export_format="GLB", use_selection=True,
                export_yup=True, export_apply=True, export_extras=True,
                export_cameras=False, export_lights=False,
                export_texcoords=True, export_normals=True, export_tangents=False,
                export_materials="EXPORT")
    attempts = []
    if draco:
        attempts.append(dict(base, export_draco_mesh_compression_enable=True,
                             export_draco_mesh_compression_level=6))
    attempts += [dict(base), dict(filepath=path, export_format="GLB", use_selection=True,
                                  export_yup=True)]
    last = None
    for kw in attempts:
        try:
            bpy.ops.export_scene.gltf(**kw)
            print(f"[glb] OK {path} {os.path.getsize(path)/1e6:.2f} MB ({n} objs)")
            return True
        except Exception as e:
            last = e
    print(f"[glb] 失败: {last}")
    return False


def scene_bbox(objs):
    mn = Vector((1e18,) * 3)
    mx = Vector((-1e18,) * 3)
    for ob in objs:
        if ob.type != "MESH":
            continue
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            mn = Vector((min(mn[i], w[i]) for i in range(3)))
            mx = Vector((max(mx[i], w[i]) for i in range(3)))
    if mn.x > 1e17:
        return (0, 0, 0), (0, 0, 0)
    return tuple(round(x, 3) for x in mn), tuple(round(x, 3) for x in mx)


def architecture_bbox(objs, radius=90.0):
    """只统计"建筑本体"的包围盒（剔除 600m 镜湖、远山与层云）。

    做法：逐顶点筛 |x|,|y| <= radius 的顶点再求包围盒。宏观环境（镜湖/远山/层云）
    会把整体 bbox 撑到 1200m 见方，Web 端若拿它做自动取景会缩成一个点，
    所以两套数据都给：bbox（全场景）/ bbox_architecture（建筑本体，供取景用）。
    """
    mn = Vector((1e18,) * 3)
    mx = Vector((-1e18,) * 3)
    for ob in objs:
        if ob.type != "MESH":
            continue
        # 宏观环境（草甸 / 松林带 / 矶头）现在有落在 ±90m 以内的顶点，光靠半径筛
        # 会把草甸 72m、松林 77m 一起算进"建筑本体"，实测把 bbox 撑到 172×180。
        # 所以先按合并后的对象名剔除宏观组（assemble 的合批名带 _macro 后缀）。
        if ob.name.endswith("_macro"):
            continue
        mw = ob.matrix_world
        for v in ob.data.vertices:
            w = mw @ v.co
            if abs(w.x) > radius or abs(w.y) > radius:
                continue
            mn = Vector((min(mn[i], w[i]) for i in range(3)))
            mx = Vector((max(mx[i], w[i]) for i in range(3)))
    if mn.x > 1e17:
        return (0, 0, 0), (0, 0, 0)
    return tuple(round(x, 3) for x in mn), tuple(round(x, 3) for x in mx)


def write_manifest(path, objs, extra=None):
    tris_per_mat = {}
    total = 0
    for ob in objs:
        if ob is None or ob.type != "MESH":
            continue
        key = ob.data.materials[0].get("key") if ob.data.materials else ob.name
        n = mu.tri_count(ob)
        total += n
        tris_per_mat[key] = tris_per_mat.get(key, 0) + n
    mn, mx = scene_bbox(objs)
    amn, amx = architecture_bbox(objs)
    tex_root = os.path.join(os.path.dirname(path) or ".", "textures")

    def _tex(key, attr):
        """实际落盘的贴图文件名：发布版是 jpg，源版是 png；两样都没有则返回 None
        （mount_near / mount_far / mist 是自发光无贴图材质，不能写不存在的路径）。"""
        for ext in (".jpg", ".png"):
            if os.path.exists(os.path.join(tex_root, f"{key}_{attr}{ext}")):
                return f"textures/{key}_{attr}{ext}"
        return None

    def _ao(key):
        if extra and "baked_ao" in extra and key not in extra["baked_ao"]:
            return None
        p = os.path.join(tex_root, f"ao_{key}.png")
        return f"textures/ao_{key}.png" if os.path.exists(p) else None

    mat_table = {}
    for key in MAT_ORDER:
        cn, hexc, rough, metal, size = MAT_META[key]
        if key not in tris_per_mat:
            continue
        mat_table[key] = {
            "cn": cn, "basecolor": hexc, "roughness": rough, "metallic": metal,
            "texture_size": size, "mesh": f"MESH_{key}", "tris": tris_per_mat[key],
            "textures": {
                "basecolor": _tex(key, "basecolor"),
                "orm": _tex(key, "orm"),
                "normal": _tex(key, "normal"),
                "ao": _ao(key),
            },
        }
    cams = {}
    for name, spec in DIM.CAMERAS.items():
        cams[name] = {"cn": spec["cn"], "location": list(spec["loc"]),
                      "look_at": list(spec["look"]), "lens_mm": spec["lens"]}
    manifest = {
        "building": "文脉·新中式殿堂级水院展馆复合体",
        "version": "v1.0",
        "coordinate_system": {
            "unit": "meter", "blender_up": "Z", "gltf_up": "Y",
            "origin": "主殿入口大门正中 / 地面水平线 (0,0,0)",
            "axis": "+X 东, +Y 殿内(北), -Y 桥引道(南), +Z 上",
        },
        "bbox": {"min": list(mn), "max": list(mx),
                 "size": [round(mx[i] - mn[i], 3) for i in range(3)],
                 "note": "导出网格在 Blender 世界坐标中的包围盒"},
        "bbox_architecture": {
            "min": list(amn), "max": list(amx),
            "size": [round(amx[i] - amn[i], 3) for i in range(3)],
            "note": "建筑本体包围盒（剔除宏观环境），Web 端自动取景请用这一组",
        },
        "mesh_count": len([o for o in objs if o and o.type == "MESH"]),
        "draw_calls": len([o for o in objs if o and o.type == "MESH"]),
        "total_tris": total,
        "materials": mat_table,
        "cameras": cams,
        "lod": {"note": "单档 PBR，材质级合批；draw call 数 = 材质数"},
        "web3d": {
            "up_axis": "+Y (glTF 直出，根节点无旋转)",
            "origin": "主殿入口大门正中地面水平线 = (0,0,0)，单位为米",
            "uv_channel_0": "UVMap —— albedo / normal / metallic-roughness 平铺贴图",
            "uv_channel_1": "UVMap2 —— lightmap_pack 非重叠布局，供 AO 使用",
            "orm_packing": "单图 R=AO, G=Roughness, B=Metallic；occlusionTexture 指向同一 image、texCoord=1",
            "camera_nodes": "5 个 Empty 随 GLB 导出，extras 含 look_at(Blender 坐标)/lens_mm/cn；"
                            "Three.js: scene.getObjectByName('CAM_...')",
            "css_safe_area": {
                "sky_top": 0.15, "side_margin": 0.10,
                "subject_band": [0.30, 0.75],
                "note": "五个机位构图已按此安全区留白；背景建议透明或 #0b111e→#161e2e 渐变叠加",
            },
            "target_fps": 60,
        },
    }
    if extra:
        manifest.update(extra)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"[manifest] {path}: {manifest['mesh_count']} mesh / {total} tris")
    return manifest


def save_blend(path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    directory = os.path.abspath(os.path.dirname(path) or ".")
    for image in bpy.data.images:
        if image.source == "FILE" and image.filepath:
            absolute = os.path.abspath(bpy.path.abspath(image.filepath))
            if os.path.dirname(absolute) == os.path.join(directory, "textures"):
                image.filepath = "//textures/" + os.path.basename(absolute)
    bpy.ops.wm.save_as_mainfile(filepath=path, relative_remap=False)
    print(f"[blend] saved {path}")
