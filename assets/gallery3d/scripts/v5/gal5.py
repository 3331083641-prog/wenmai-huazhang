"""Shared foundation for the gallery V5 parametric build.

All comments are ASCII on purpose: these files round-trip through
PowerShell on Windows, and non-ASCII source has been corrupted before.

Coordinate convention (must match the web contract):
    Blender Z-up, +Y is the FRONT of the building (the street side).
    three.js conversion used by the layout exporter is (x, z, -y).

Levels are taken from the live layout contract
(frontend/src/features/heritage-gallery/data/gallery_layout.json) so the
existing 15 frame anchors, wall rectangles and camera presets keep working
without any change on the web side.
"""

from __future__ import annotations

import math
import os

import bpy
from mathutils import Vector

# ----------------------------------------------------------------- levels
BASE = 16.0          # base plan 16 x 16 m
BASE_TOP = 0.25      # walking level of the base / street
BASE_BOT = -0.40     # underside of the base (floating slab)

F1 = 0.25            # floor 1 finished level
F2 = 3.60            # floor 2 finished level
TOP = 6.55           # head of the second floor windows
ATTIC = 7.45         # attic band above the skirt roof
EAVE_Z = 6.15        # skirt (pent) roof outer eave
SKIRT_IN = 7.05      # skirt roof where it meets the attic wall
RIDGE_Z = 11.30      # main roof ridge (raised with the eave: the 斗拱 band
                     # needs room and the roof mass must read like the concept art)

BW = 8.40            # building width  (X)
BD = 7.50            # building depth  (Y)
BCY = -0.55          # building centre Y  (shifted back: street in front)

EAVE_OV = 1.38       # main roof eave overhang, X
EAVE_OV_Y = 0.80     # main roof eave overhang, Y
SKIRT_OV = 1.28      # skirt roof overhang: must project PAST the main eave, otherwise the
                     # main roof swallows it and the whole lower tier disappears
VER_W = 1.35         # veranda / balcony projection

# roof plan of the main roof. X and Y overhangs differ on purpose: that is what
# gives the hip roof a real ridge (ridge length = ROOF_W - ROOF_D) instead of
# collapsing into a pyramid, which is how the V4 roof read from every angle.
ROOF_W = BW + EAVE_OV * 2.0
ROOF_D = BD + EAVE_OV_Y * 2.0
ROOF_MAIN_EAVE = 7.95

# ----------------------------------------------------------------- scene
COLS: dict = {}
MATS: dict = {}
LOG: list = []


def log(msg: str) -> None:
    LOG.append(msg)
    print("[v5] " + msg)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    for block in (bpy.data.objects, bpy.data.meshes, bpy.data.materials,
                  bpy.data.curves, bpy.data.lights, bpy.data.cameras):
        for item in list(block):
            try:
                block.remove(item)
            except Exception:
                pass
    return scene


def collection(name: str):
    if name in COLS:
        return COLS[name]
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    COLS[name] = col
    return col


# ----------------------------------------------------------------- materials
def mat(name, rgb, rough=0.78, metal=0.0, emit=None, emit_str=0.0, alpha=1.0):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    r, g, b = rgb
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.28
    if emit is not None:
        bsdf.inputs["Emission Color"].default_value = (emit[0], emit[1], emit[2], 1.0)
        bsdf.inputs["Emission Strength"].default_value = emit_str
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        m.blend_method = "BLEND"
    m.diffuse_color = (r, g, b, alpha)
    MATS[name] = m
    return m


# Warm, low-saturation palette close to the concept art. Kept in one place so
# the whole model can be re-timed without hunting colours in the builders.
PALETTE = {
    "tile":      ((0.262, 0.282, 0.302), 0.84, 0.0),
    "tile_d":    ((0.186, 0.202, 0.218), 0.88, 0.0),
    "wood":      ((0.196, 0.110, 0.062), 0.66, 0.0),
    "wood_m":    ((0.300, 0.176, 0.098), 0.62, 0.0),
    "wood_l":    ((0.412, 0.262, 0.148), 0.60, 0.0),
    "wood_d":    ((0.086, 0.048, 0.028), 0.58, 0.0),   # 深栗：门框 / 柱础
    "plaster":   ((0.902, 0.868, 0.792), 0.92, 0.0),
    "plaster_d": ((0.812, 0.776, 0.700), 0.92, 0.0),
    "stone":     ((0.556, 0.545, 0.520), 0.90, 0.0),
    "stone_l":   ((0.690, 0.678, 0.648), 0.90, 0.0),
    "stone_d":   ((0.352, 0.350, 0.338), 0.92, 0.0),
    "pave":      ((0.612, 0.602, 0.578), 0.88, 0.0),
    "gold":      ((0.612, 0.470, 0.212), 0.42, 0.72),
    "chap":      ((0.118, 0.238, 0.232), 0.58, 0.10),   # 青绿彩画
    "chap_l":    ((0.196, 0.352, 0.330), 0.58, 0.10),
    "lacquer":   ((0.320, 0.072, 0.052), 0.44, 0.0),
    "red":       ((0.520, 0.108, 0.080), 0.58, 0.0),
    "glass":     ((0.760, 0.830, 0.842), 0.10, 0.0),
    "carpet":    ((0.470, 0.106, 0.090), 0.96, 0.0),
    "paper":     ((0.918, 0.888, 0.812), 0.94, 0.0),
    "ink":       ((0.120, 0.108, 0.098), 0.90, 0.0),
    "leaf":      ((0.268, 0.408, 0.156), 0.80, 0.0),
    "leaf_l":    ((0.406, 0.556, 0.216), 0.80, 0.0),
    "bark":      ((0.230, 0.170, 0.118), 0.84, 0.0),
    "bamboo":    ((0.446, 0.520, 0.236), 0.78, 0.0),
    "flower":    ((0.868, 0.836, 0.760), 0.86, 0.0),
    "lamp":      ((0.960, 0.560, 0.280), 0.55, 0.0),
}


def P(key):
    """Palette material (cached)."""
    if key in MATS:
        return MATS[key]
    rgb, rough, metal = PALETTE[key]
    alpha = 0.24 if key == "glass" else 1.0
    return mat("M_" + key, rgb, rough=rough, metal=metal, alpha=alpha)


def E(key, rgb=(1.0, 0.62, 0.32), strength=3.0):
    """Emissive material for lanterns / lamp glass."""
    name = "E_" + key
    if name in MATS:
        return MATS[name]
    return mat(name, rgb, rough=0.5, emit=rgb, emit_str=strength)


# ----------------------------------------------------------------- primitives
def _attach(name, mesh, col, material, loc, rot):
    ob = bpy.data.objects.new(name, mesh)
    col.objects.link(ob)
    if loc:
        ob.location = Vector(loc)
    if rot:
        ob.rotation_euler = rot if not isinstance(rot, tuple) else rot
    if material is not None:
        ob.data.materials.append(material)
    return ob


def add_box(name, dims, loc, col, material=None, rot_z=0.0, rot=None):
    me = bpy.data.meshes.new(name)
    dx, dy, dz = dims[0] * 0.5, dims[1] * 0.5, dims[2] * 0.5
    verts = [(-dx, -dy, -dz), (dx, -dy, -dz), (dx, dy, -dz), (-dx, dy, -dz),
             (-dx, -dy, dz), (dx, -dy, dz), (dx, dy, dz), (-dx, dy, dz)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me.from_pydata(verts, [], faces)
    me.update()
    r = rot if rot is not None else (0.0, 0.0, rot_z)
    return _attach(name, me, col, material, loc, r)


def add_cyl(name, radius, depth, loc, col, material=None, segments=20, rot=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments, radius=radius,
                                        depth=depth, location=loc)
    ob = bpy.context.object
    ob.name = name
    _move_to(ob, col)
    if rot:
        ob.rotation_euler = rot
    if material is not None:
        ob.data.materials.append(material)
    return ob


def add_cone(name, r1, r2, depth, loc, col, material=None, segments=16, rot=None):
    bpy.ops.mesh.primitive_cone_add(vertices=segments, radius1=r1, radius2=r2,
                                    depth=depth, location=loc)
    ob = bpy.context.object
    ob.name = name
    _move_to(ob, col)
    if rot:
        ob.rotation_euler = rot
    if material is not None:
        ob.data.materials.append(material)
    return ob


def add_sphere(name, radius, loc, col, material=None, segments=16, rings=10,
               scale=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,
                                         ring_count=rings, radius=radius,
                                         location=loc)
    ob = bpy.context.object
    ob.name = name
    _move_to(ob, col)
    if scale:
        ob.scale = scale
    if material is not None:
        ob.data.materials.append(material)
    return ob


def add_mesh(name, verts, faces, col, material=None, loc=(0, 0, 0), rot=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    me.validate(verbose=False)
    return _attach(name, me, col, material, loc, rot)


def _move_to(ob, col):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    col.objects.link(ob)


def shade_smooth(ob, angle=math.radians(34)):
    for poly in ob.data.polygons:
        poly.use_smooth = True
    if hasattr(ob.data, "use_auto_smooth"):
        ob.data.use_auto_smooth = True
    try:
        mod = ob.modifiers.new("Sharp", "EDGE_SPLIT")
        mod.split_angle = angle
    except Exception:
        pass
    return ob


def join_objs(name, objs):
    """Join a list of objects into one, preserving the first material slots."""
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    if len(objs) == 1:
        objs[0].name = name
        return objs[0]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.object
    ob.name = name
    return ob


def text_mesh(name, body, size, loc, col, material, font_path=None,
              extrude=0.012, align_x="CENTER", rot=None):
    """Real 3D text (used for the hall plaque and the exhibition labels)."""
    curve = bpy.data.curves.new(name, type="FONT")
    curve.body = body
    if font_path and os.path.exists(font_path):
        try:
            curve.font = bpy.data.fonts.load(font_path, check_existing=True)
        except Exception:
            pass
    curve.size = size
    curve.extrude = extrude
    curve.align_x = align_x
    curve.align_y = "CENTER"
    ob = bpy.data.objects.new(name, curve)
    col.objects.link(ob)
    ob.location = Vector(loc)
    if rot:
        ob.rotation_euler = rot
    if material is not None:
        ob.data.materials.append(material)
    return ob


FONT_CANDIDATES = (
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
)


def cjk_font():
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


# ----------------------------------------------------------------- roof maths
def apex_z(t, eave_z, ridge_z, k=0.58):
    """Juzhe (concave) profile: t=0 at the eave, t=1 at the ridge."""
    return eave_z + (ridge_z - eave_z) * (k * t + (1.0 - k) * t * t)


def roof_point(x, y, w, d, eave_z, ridge_z, lift=0.26, lift_r=1.05,
               lift_t=0.30, k=0.58, cy=None):
    """Hip roof surface with a gentle corner upturn.

    y is passed in BUILDING space (already relative to the building centre) so
    the caller does not have to remember the BCY offset.
    """
    half_w, half_d = w * 0.5, d * 0.5
    dist = min(half_d - abs(y), half_w - abs(x))
    t = max(0.0, min(1.0, dist / half_d))
    z = apex_z(t, eave_z, ridge_z, k)
    fade = max(0.0, 1.0 - t / lift_t)
    if fade > 0.0:
        acc = 0.0
        for cx in (-half_w, half_w):
            for cyy in (-half_d, half_d):
                dd = math.hypot(x - cx, y - cyy)
                acc = max(acc, math.exp(-(dd / lift_r) ** 2))
        z += lift * acc * (fade ** 2)
    return z


def roof_grid(name, w, d, eave_z, ridge_z, col, material, nx=72, ny=64,
              lift=0.26, k=0.58, ring_inner=None, thickness=0.16):
    """Solid hip roof shell (top surface + skirt thickness).

    ring_inner=(iw, id) clips the middle out, which is how the skirt roof is
    built around the wall; the clipped edges are dropped down by `thickness`
    so the roof reads as a slab instead of a paper sheet.
    """
    rows_t, rows_b = [], []
    for j in range(ny + 1):
        y = -d * 0.5 + d * j / ny
        top_row, bot_row = [], []
        for i in range(nx + 1):
            x = -w * 0.5 + w * i / nx
            z = roof_point(x, y, w, d, eave_z, ridge_z, lift=lift, k=k)
            top_row.append((x, y + BCY, z))
            bot_row.append((x, y + BCY, z - thickness))
        rows_t.append(top_row)
        rows_b.append(bot_row)
    verts = [v for row in rows_t for v in row] + [v for row in rows_b for v in row]
    n = (nx + 1) * (ny + 1)
    faces = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            quad = (a, a + 1, a + nx + 2, a + nx + 1)
            if ring_inner is not None:
                iw, idd = ring_inner
                xs = [verts[q][0] for q in quad]
                ys = [verts[q][1] - BCY for q in quad]
                if (min(xs) > -iw * 0.5 and max(xs) < iw * 0.5 and
                        min(ys) > -idd * 0.5 and max(ys) < idd * 0.5):
                    continue
            faces.append(quad)
            faces.append(tuple(reversed(tuple(q + n for q in quad))))
    if ring_inner is None:
        # close the four sides of the slab
        for j in range(ny):
            for i in (0, nx):
                a = j * (nx + 1) + i
                b = (j + 1) * (nx + 1) + i
                if i == 0:
                    faces.append((a, b, b + n, a + n))
                else:
                    faces.append((b, a, a + n, b + n))
        for i in range(nx):
            for j in (0, ny):
                a = j * (nx + 1) + i
                b = j * (nx + 1) + i + 1
                if j == 0:
                    faces.append((b, a, a + n, b + n))
                else:
                    faces.append((a, b, b + n, a + n))
    ob = add_mesh(name, verts, faces, col, material)
    shade_smooth(ob)
    return ob


# ----------------------------------------------------------------- ornament
def huiwen_band(name, length, height, depth, loc, col, material, axis="x",
                period=0.42, bar=0.055, sign=1.0):
    """Continuous meander (huiwen) frieze built from real extruded bars.

    A flat dark stripe never reads as carving; the alternating long/short bars
    with a connecting rail do, even at miniature scale.
    """
    obs = []
    n = max(2, int(round(length / period)))
    step = length / n
    for i in range(n):
        u = -length * 0.5 + step * (i + 0.5)
        # vertical stub
        obs.append(_band_bar(name + "_V%d" % i, bar, height * 0.92, depth, u, 0,
                             loc, col, material, axis))
        # horizontal connector, alternating up / down to make the meander
        v = height * (0.30 if i % 2 == 0 else -0.30)
        obs.append(_band_bar(name + "_H%d" % i, step * 0.94, bar, depth, u, v,
                             loc, col, material, axis))
    return join_objs(name, obs)


def _band_bar(name, su, sv, depth, u, v, loc, col, material, axis):
    if axis == "x":
        dims = (su, depth, sv)
        p = (loc[0] + u, loc[1], loc[2] + v)
    else:
        dims = (depth, su, sv)
        p = (loc[0], loc[1] + u, loc[2] + v)
    return add_box(name, dims, p, col, material)


def lotus_medallion(name, radius, thickness, loc, col, material, petals=8,
                    rot_z=0.0):
    """Eight-petal stone roundel (the corner motif on the base)."""
    obs = []
    core = add_cyl(name + "_Core", radius * 0.42, thickness,
                   (loc[0], loc[1], loc[2]), col, material, segments=24,
                   rot=(math.pi * 0.5, 0, rot_z))
    obs.append(core)
    for k in range(petals):
        ang = 2.0 * math.pi * k / petals + rot_z
        px = loc[0] + math.cos(ang) * radius * 0.58
        pz = loc[2] + math.sin(ang) * radius * 0.58
        ob = add_cyl(name + "_P%d" % k, radius * 0.26, thickness * 0.72,
                     (px, loc[1], pz), col, material, segments=12,
                     rot=(math.pi * 0.5, 0, ang))
        ob.scale = (1.0, 1.0, 1.0)
        obs.append(ob)
    return join_objs(name, obs)
