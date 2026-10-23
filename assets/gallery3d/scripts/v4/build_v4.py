"""Wenmai Gallery V4 - parametric rebuild driven by the 10 reference images.

Stage S1 = massing / roof form / base / street only (clay material).
Run:  blender.exe -b --factory-startup -P build_v4.py -- --stage s1
ASCII-only source (Windows PowerShell mangles UTF-8 in .py round-trips).

Coordinate contract (metres, Z up, front faces -Y):
  plinth     16.0 x 16.0, top at z = 1.50
  building   10.4 (X) x 9.0 (Y), centre y = +0.60
  F1 floor   1.50, F1 top 4.10, F2 floor 4.10, F2 wall top 6.60
  main roof  eave 6.60 -> ridge 9.60, overhang 1.10
  skirt roof lower eave 4.02 -> 4.62, overhang 0.78
"""
from __future__ import annotations

import math
import os
import sys
import bpy
import bmesh
from mathutils import Vector, Matrix

# ---------------------------------------------------------------- constants
BASE = 16.0
PL_TOP = 1.50
PL_TIER1 = 0.90          # sumeru seat height
PL_TIER2 = 0.60          # stone platform height
BW = 10.4                # building width  (X)
BD = 7.6                 # building depth  (Y)
BCY = 0.60               # building centre Y
F1 = 1.50
F1_TOP = 4.10
F2 = 4.10
F2_TOP = 6.95
RIDGE = 9.35
EAVE_OV = 1.45
SKIRT_OV = 1.18
BALC_OV = 0.95           # second floor balcony projection

HERE = os.path.dirname(os.path.abspath(__file__))
G3D = os.path.abspath(os.path.join(HERE, "..", ".."))
BLEND_OUT = os.path.join(G3D, "blender", "wenmai_gallery_v4.blend")
RENDER_OUT = os.path.join(G3D, "renders", "v4")

COLS = {}
MATS = {}
LOG = []


def log(msg):
    LOG.append(str(msg))
    print("[v4] " + str(msg))


# ---------------------------------------------------------------- scene utils
def reset_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.curves,
                  bpy.data.cameras, bpy.data.lights, bpy.data.images):
        for b in list(block):
            try:
                block.remove(b)
            except Exception:
                pass
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    return sc


def collection(name):
    if name in COLS:
        return COLS[name]
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    COLS[name] = col
    return col


def mat(name, rgb, rough=0.75, metal=0.0, emit=None, emit_str=0.0, alpha=1.0):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        m.blend_method = "BLEND"
    if emit is not None:
        bsdf.inputs["Emission Color"].default_value = (emit[0], emit[1], emit[2], 1.0)
        bsdf.inputs["Emission Strength"].default_value = emit_str
    MATS[name] = m
    return m


def M(clay=False):
    if clay:
        return mat("CLAY", (0.58, 0.56, 0.52), rough=0.88)
    return mat("CLAY", (0.58, 0.56, 0.52), rough=0.88)


def _finish(name, bm, col, material, loc=(0, 0, 0), rot=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    if rot is not None:
        ob.rotation_euler = rot
    ob.location = loc
    col.objects.link(ob)
    if material:
        ob.data.materials.append(material)
    return ob


def add_box(name, dims, loc, col, material=None, rot_z=0.0, rot=None):
    sx, sy, sz = dims
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    r = rot
    if r is None and rot_z:
        r = (0.0, 0.0, rot_z)
    return _finish(name, bm, col, material, loc=loc, rot=r)


def add_cyl(name, radius, depth, loc, col, material=None, segments=16, rot=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=radius, radius2=radius, depth=depth)
    return _finish(name, bm, col, material, loc=loc, rot=rot)


def add_cone(name, r1, r2, depth, loc, col, material=None, segments=16, rot=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=r1, radius2=r2, depth=depth)
    return _finish(name, bm, col, material, loc=loc, rot=rot)


def add_mesh(name, verts, faces, col, material=None, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    col.objects.link(ob)
    if material:
        ob.data.materials.append(material)
    return ob


def shade_smooth(ob, angle=math.radians(35)):
    for p in ob.data.polygons:
        p.use_smooth = True
    try:
        mod = ob.modifiers.new("smooth", "EDGE_SPLIT")
        mod.split_angle = angle
    except Exception:
        pass


def join_objs(name, objs):
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    if len(objs) == 1:
        objs[0].name = name
        return objs[0]
    ctx = bpy.context
    for o in ctx.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    ctx.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = ctx.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


# ---------------------------------------------------------------- roof maths
def roof_point(x, y, w, d, eave_z, ridge_z, lift=0.18, lift_r=0.72, k1=0.70):
    """Hip-roof surface. t=0 at eave, 1 at ridge, curved (juzhe) + corner lift."""
    half_d = d * 0.5
    half_w = w * 0.5
    dist = min(half_d - abs(y), half_w - abs(x))
    t = max(0.0, min(1.0, dist / half_d))
    z = eave_z + (ridge_z - eave_z) * (k1 * t + (1.0 - k1) * t * t)
    # corner upturn: gaussian bump around each plan corner, faded along slope
    fade = max(0.0, 1.0 - t / 0.34)
    if fade > 0.0:
        acc = 0.0
        for cx in (-half_w, half_w):
            for cy in (-half_d, half_d):
                dd = math.hypot(x - cx, y - cy)
                acc += math.exp(-(dd / lift_r) ** 2)
        z += lift * min(1.0, acc) * (fade ** 2)
    return x, y, z


def roof_grid(name, w, d, eave_z, ridge_z, col, material, nx=48, ny=44,
              cut_ridge=1.0, lift=0.18, inner=None):
    """Hip-roof surface. inner=(w,d,z) clips the middle out (skirt-ring roof)."""
    rows = []
    for j in range(ny + 1):
        y = -d * 0.5 + d * j / ny
        row = []
        for i in range(nx + 1):
            x = -w * 0.5 + w * i / nx
            px, py, pz = roof_point(x, y, w, d, eave_z, ridge_z, lift=lift)
            row.append((px, py + BCY, pz))
        rows.append(row)
    verts = [v for row in rows for v in row]
    faces = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            quad = (a, a + 1, a + nx + 2, a + nx + 1)
            if inner is not None:
                iw, idd, iz = inner
                xs = [verts[q][0] for q in quad]
                ys = [verts[q][1] for q in quad]
                if (min(xs) > -iw * 0.5 and max(xs) < iw * 0.5 and
                        min(ys) > -idd * 0.5 and max(ys) < idd * 0.5):
                    continue
            faces.append(quad)
    if inner is not None:
        iw, idd, iz = inner
        verts = [((v[0], v[1], iz) if (abs(v[0]) <= iw * 0.5 and abs(v[1]) <= idd * 0.5)
                  else v) for v in verts]
    ob = add_mesh(name, verts, faces, col, material)
    shade_smooth(ob)
    return ob


def tile_rows(name, w, d, eave_z, ridge_z, col, material, spacing=0.312,
              radius=0.085, lift=0.18, samples=18):
    """Half-round tile courses running up the slope, parallel to the eave normal."""
    obs = []
    half_w, half_d = w * 0.5, d * 0.5

    def make_row(points, tag):
        if len(points) < 3:
            return None
        verts, faces = [], []
        for idx, p in enumerate(points):
            p_prev = points[max(0, idx - 1)]
            p_next = points[min(len(points) - 1, idx + 1)]
            tan = (Vector(p_next) - Vector(p_prev))
            if tan.length < 1e-6:
                tan = Vector((0, 1, 0))
            tan.normalize()
            binorm = tan.cross(Vector((0, 0, 1)))
            if binorm.length < 1e-6:
                binorm = Vector((1, 0, 0))
            binorm.normalize()
            up = binorm.cross(tan)
            up.normalize()
            base = Vector(p)
            for a in range(5):
                ang = math.pi * a / 4.0
                off = binorm * (radius * math.cos(ang)) + up * (radius * math.sin(ang))
                verts.append(tuple(base + off))
        for idx in range(len(points) - 1):
            for a in range(4):
                v0 = idx * 5 + a
                faces.append((v0, v0 + 1, v0 + 6, v0 + 5))
        return add_mesh(name + "_" + tag, verts, faces, col, material)

    # front / back slopes: constant X
    n_x = int(round(w / spacing))
    for i in range(n_x + 1):
        x = -half_w + w * i / n_x
        if abs(x) > half_w - 0.02:
            continue
        for sign in (-1, 1):
            dmax = min(half_d, half_w - abs(x))
            if dmax < 0.35:
                continue
            pts = []
            for s in range(samples + 1):
                ds = dmax * s / samples
                y = BCY + sign * (half_d - ds)
                px, py, pz = roof_point(x, y - BCY, w, d, eave_z, ridge_z, lift=lift)
                pts.append((px, py + BCY, pz))
            ob = make_row(pts, "F%d%s" % (i, "a" if sign < 0 else "b"))
            if ob:
                obs.append(ob)
    # left / right slopes: constant Y
    n_y = int(round(d / spacing))
    for j in range(n_y + 1):
        y = -half_d + d * j / n_y
        if abs(y) > half_d - 0.02:
            continue
        for sign in (-1, 1):
            dmax = min(half_w, half_d - abs(y))
            if dmax < 0.35:
                continue
            pts = []
            for s in range(samples + 1):
                ds = dmax * s / samples
                x = sign * (half_w - ds)
                px, py, pz = roof_point(x, y, w, d, eave_z, ridge_z, lift=lift)
                pts.append((px, py + BCY, pz))
            ob = make_row(pts, "S%d%s" % (j, "a" if sign < 0 else "b"))
            if ob:
                obs.append(ob)
    joined = join_objs(name, obs)
    return joined


def eave_tiles(name, w, d, eave_z, col, material, spacing=0.312, lift=0.18):
    """Round tile ends (wadang) sitting on the drip edge, one per tile course."""
    obs = []
    half_w, half_d = w * 0.5, d * 0.5
    z = eave_z - 0.15
    n_x = max(2, int(round(w / spacing)))
    for i in range(n_x + 1):
        x = -half_w + 0.17 + i * (w - 0.34) / n_x
        for sign in (-1, 1):
            obs.append(add_cyl("%s_FB%d_%d" % (name, sign, i), 0.086, 0.06,
                               (x, BCY + sign * (half_d + 0.035), z), col,
                               material, segments=12,
                               rot=(math.pi * 0.5, 0, 0)))
    n_y = max(2, int(round(d / spacing)))
    for j in range(n_y + 1):
        y = BCY - half_d + 0.17 + j * (d - 0.34) / n_y
        for sign in (-1, 1):
            obs.append(add_cyl("%s_LR%d_%d" % (name, sign, j), 0.086, 0.06,
                               (sign * (half_w + 0.035), y, z), col, material,
                               segments=12, rot=(0, math.pi * 0.5, 0)))
    return join_objs(name, obs)


def ridge_beam(name, p0, p1, col, material, width=0.26, height=0.22, layers=3):
    p0 = Vector(p0)
    p1 = Vector(p1)
    vec = p1 - p0
    length = vec.length
    if length < 1e-4:
        return None
    mid = (p0 + p1) * 0.5
    rot = vec.to_track_quat("Y", "Z").to_euler()
    obs = []
    for i in range(layers):
        shrink = 1.0 - i * 0.14
        zoff = (height * 0.5) * i * 1.35
        ob = add_box("%s_L%d" % (name, i),
                     (width * shrink, length, height * 0.85),
                     (mid.x, mid.y, mid.z + zoff), col, material, rot=rot)
        obs.append(ob)
    return join_objs(name, obs)


def chiwen(name, loc, col, material, flip=1.0):
    """Curled ridge-end ornament built from a swept profile."""
    pts = [(0.0, 0.0), (0.10, 0.30), (0.26, 0.52), (0.46, 0.62),
           (0.60, 0.50), (0.58, 0.34), (0.44, 0.30)]
    verts, faces = [], []
    thick = 0.22
    for i, (u, v) in enumerate(pts):
        for t in (-0.5, 0.5):
            verts.append((u * flip, t * thick, v))
    for i in range(len(pts) - 1):
        a = i * 2
        faces.append((a, a + 1, a + 3, a + 2))
    ob = add_mesh(name, verts, faces, col, material, loc=loc)
    return ob


# ---------------------------------------------------------------- base / street
def build_base(col, material):
    obs = []
    # sumeru seat: three stacked slabs (base, waist, cap)
    b = add_box("BASE_SeatBottom", (BASE, BASE, 0.34), (0, 0, 0.17), col, material)
    obs.append(b)
    w = add_box("BASE_SeatWaist", (BASE - 0.34, BASE - 0.34, 0.34), (0, 0, 0.51), col, material)
    obs.append(w)
    c = add_box("BASE_SeatCap", (BASE, BASE, 0.24), (0, 0, 0.79), col, material)
    obs.append(c)
    # stone platform
    p = add_box("BASE_Platform", (BASE - 0.10, BASE - 0.10, PL_TIER2), (0, 0, 1.20), col, material)
    obs.append(p)
    # coping stones around platform edge
    for sx in (-1, 1):
        obs.append(add_box("BASE_Cope_X%d" % sx, (0.34, BASE - 0.10, 0.10),
                           (sx * (BASE - 0.10) * 0.5, 0, PL_TOP - 0.05), col, material))
    for sy in (-1, 1):
        obs.append(add_box("BASE_Cope_Y%d" % sy, (BASE - 0.10, 0.34, 0.10),
                           (0, sy * (BASE - 0.10) * 0.5, PL_TOP - 0.05), col, material))
    # timber bearers under the diorama
    for i in range(-2, 3):
        obs.append(add_box("BASE_Bearer%d" % (i + 2), (BASE * 0.62, 0.20, 0.20),
                           (0, i * 2.6, -0.10), col, material))
    return join_objs("V4_BASE", obs)


def build_street(col, material):
    """Paving inside the plinth top; building sits at BCY."""
    half = (BASE - 0.10) * 0.5
    top = PL_TOP
    b = add_box("STREET_Paving", (BASE - 0.24, BASE - 0.24, 0.06), (0, 0, top), col, material)
    return b


# ---------------------------------------------------------------- building core
def build_walls(col, material, wood=None):
    wood = wood or material
    obs = []
    x0, x1 = -BW * 0.5, BW * 0.5
    y0, y1 = BCY - BD * 0.5, BCY + BD * 0.5
    # ground floor: plinth strip + wall band
    obs.append(add_box("WALL_F1_Low", (BW, BD, 0.42), (0, BCY, F1 + 0.21), col, material))
    # ground floor wall band from 1.92 to 4.10, with door gap on front (-Y)
    door_w = 2.60
    front_y = y0
    seg_w = (BW - door_w) * 0.5
    for i, sx in enumerate((-1, 1)):
        cx = sx * (door_w * 0.5 + seg_w * 0.5)
        obs.append(add_box("WALL_F1_Front%d" % i, (seg_w, 0.36, F1_TOP - F1 - 0.42),
                           (cx, front_y, (F1 + 0.42 + F1_TOP) * 0.5), col, material))
    obs.append(add_box("WALL_F1_Header", (door_w, 0.36, 0.5),
                       (0, front_y, F1_TOP - 0.25), col, material))
    obs.append(add_box("WALL_F1_Back", (BW, 0.36, F1_TOP - F1 - 0.42),
                       (0, y1, (F1 + 0.42 + F1_TOP) * 0.5), col, material))
    for i, sx in enumerate((-1, 1)):
        obs.append(add_box("WALL_F1_Side%d" % i, (0.36, BD, F1_TOP - F1 - 0.42),
                           (sx * BW * 0.5, BCY, (F1 + 0.42 + F1_TOP) * 0.5), col, material))
    # corner columns F1
    for sx in (-1, 1):
        for sy in (-1, 1):
            obs.append(add_cyl("COL_F1_%d%d" % (sx, sy), 0.20, F1_TOP - F1,
                               (sx * BW * 0.5, BCY + sy * BD * 0.5, (F1 + F1_TOP) * 0.5),
                               col, wood, segments=12))
    # second floor: balcony slab + set-back wall
    bal_w = BW + BALC_OV * 2
    bal_d = BD + BALC_OV * 2
    hole_w, hole_d = 6.6, 4.8
    band = 0.30
    # ring slab: leaves the central void (tao kong) open to the ground floor
    obs.append(add_box("SLAB_F2_Front", (bal_w, (bal_d - hole_d) * 0.5, band),
                       (0, BCY - (bal_d + hole_d) * 0.25, F2 + 0.11), col, wood))
    obs.append(add_box("SLAB_F2_Back", (bal_w, (bal_d - hole_d) * 0.5, band),
                       (0, BCY + (bal_d + hole_d) * 0.25, F2 + 0.11), col, wood))
    obs.append(add_box("SLAB_F2_Left", ((bal_w - hole_w) * 0.5, hole_d, band),
                       (-(bal_w + hole_w) * 0.25, BCY, F2 + 0.11), col, wood))
    obs.append(add_box("SLAB_F2_Right", ((bal_w - hole_w) * 0.5, hole_d, band),
                       ((bal_w + hole_w) * 0.25, BCY, F2 + 0.11), col, wood))
    # second floor: open gallery ring (no intermediate ceiling, roof is exposed)
    f2w = BW - 0.30
    f2d = BD - 0.30
    obs.append(add_box("F2_Sill", (f2w, f2d, 0.26), (0, BCY, F2 + 0.38), col, wood))
    for sign in (-1, 1):
        obs.append(add_box("F2_TopBeam_FB%d" % sign, (f2w, 0.30, 0.34),
                           (0, BCY + sign * (f2d * 0.5 - 0.15), F2_TOP - 0.17),
                           col, material))
        obs.append(add_box("F2_TopBeam_LR%d" % sign, (0.30, f2d - 0.6, 0.34),
                           (sign * (f2w * 0.5 - 0.15), BCY, F2_TOP - 0.17),
                           col, material))
    for sx in (-1, 1):
        for sy in (-1, 1):
            obs.append(add_cyl("F2_Corner_%d%d" % (sx, sy), 0.16, F2_TOP - F2 - 0.5,
                               (sx * f2w * 0.5, BCY + sy * f2d * 0.5,
                                (F2 + 0.5 + F2_TOP - 0.34) * 0.5), col, wood,
                               segments=12))
    for sx in (-1, 1):
        for sy in (-1, 1):
            for k in (-1, 1):
                px = sx * f2w * 0.5
                py = BCY + sy * f2d * 0.5 * 0.34 * k
                obs.append(add_cyl("F2_Mull_%d%d_%d" % (sx, sy, k), 0.10,
                                   F2_TOP - F2 - 0.6, (px, py, (F2 + F2_TOP) * 0.5),
                                   col, wood, segments=10))
                obs.append(add_cyl("F2_MullF_%d%d_%d" % (sx, sy, k), 0.10,
                                   F2_TOP - F2 - 0.6,
                                   (py, BCY - sy * f2d * 0.5,
                                    (F2 + F2_TOP) * 0.5), col, wood, segments=10))
    return join_objs("V4_WALLS", obs)


def build_skirt_roof(col, material):
    """Lower eave ring between F1 and the balcony (chongyan layer)."""
    ow = BW + SKIRT_OV * 2
    od = BD + SKIRT_OV * 2
    return ring_roof("ROOF_Skirt", ow, od, BW + 0.02, BD + 0.02,
                     F1_TOP - 0.60, F1_TOP - 0.04, col, material, lift=0.22)


def build_veranda(col, material):
    """Front colonnade carrying the skirt roof + entrance steps."""
    obs = []
    y_front = BCY - BD * 0.5 - 0.62
    for i, x in enumerate((-4.45, -1.55, 1.55, 4.45)):
        obs.append(add_cyl("VER_Col%d" % i, 0.21, F1_TOP - F1 - 0.10,
                           (x, y_front, (F1 + F1_TOP) * 0.5 - 0.05), col,
                           material, segments=14))
        # queti: angled brackets between column and beam
        for sx in (-1, 1):
            obs.append(add_box("VER_Queti%d_%d" % (i, sx), (0.46, 0.16, 0.13),
                               (x + sx * 0.26, y_front, F1_TOP - 0.38), col,
                               P("wood_l"), rot=(0, math.radians(22 * sx), 0)))
    obs.append(add_box("VER_Beam", (BW + 0.3, 0.26, 0.30),
                       (0, y_front, F1_TOP - 0.18), col, material))
    # entrance steps
    for i, (dz, wdt) in enumerate(((0.18, 3.6), (0.36, 3.2), (0.54, 2.9))):
        obs.append(add_box("VER_Step%d" % i, (wdt, 0.52, 0.18),
                           (0, BCY - BD * 0.5 - 0.30 - 0.5 * i, PL_TOP + dz),
                           col, material))
    return join_objs("V4_VERANDA", obs)


def ring_roof(name, ow, od, iw, idd, eave_z, wall_z, col, material,
              lift=0.20, n=16, lift_r=1.0):
    """Picture-frame skirt roof: linear ramp from outer eave up to the wall line."""
    n_out = 24
    verts, faces = [], []

    def add_strip(outer_fn, inner_fn, tag):
        base = len(verts)
        for side in (0, 1):
            for i in range(n_out + 1):
                u = i / n_out
                if side == 0:
                    x, y = outer_fn(u)
                    t = 0.0
                else:
                    x, y = inner_fn(u)
                    t = 1.0
                verts.append((x, y, eave_z + (wall_z - eave_z) * t))
        for i in range(n_out):
            a = base + i
            faces.append((a, a + 1, base + n_out + 2 + i, base + n_out + 1 + i))
        return base

    # four trapezoid strips, overlapping slightly at the corners
    half_ow, half_od = ow * 0.5, od * 0.5
    half_iw, half_id = iw * 0.5, idd * 0.5

    def strip_from_spec(y_out, y_in, x_out_half, x_in_half):
        base = len(verts)
        for t in (0.0, 1.0):
            y = y_out + (y_in - y_out) * t
            xh = x_out_half + (x_in_half - x_out_half) * t
            for i in range(n_out + 1):
                u = -1.0 + 2.0 * i / n_out
                x = u * xh
                z = eave_z + (wall_z - eave_z) * (t ** 1.1)
                if t < 0.34:
                    fade = 1.0 - t / 0.34
                    corner = min(abs(u), 1.0)
                    bell = math.exp(-((1.0 - corner) * xh / lift_r) ** 2)
                    z += lift * bell * (fade ** 2)
                verts.append((x, y, z))
        for i in range(n_out):
            a = base + i
            faces.append((a, a + 1, base + n_out + 2 + i, base + n_out + 1 + i))

    for sign in (-1, 1):
        strip_from_spec(sign * half_od, sign * half_id, half_ow, half_iw)
    # sides are rotated 90deg: build by swapping axes through a temporary mesh
    side_verts, side_faces = [], []
    for sign in (-1, 1):
        base = len(side_verts)
        for t in (0.0, 1.0):
            x = sign * (half_ow + (half_iw - half_ow) * t)
            yh = half_od + (half_id - half_od) * t
            for i in range(n_out + 1):
                u = -1.0 + 2.0 * i / n_out
                y = BCY + u * yh
                z = eave_z + (wall_z - eave_z) * (t ** 1.1)
                if t < 0.34:
                    fade = 1.0 - t / 0.34
                    bell = math.exp(-((1.0 - abs(u)) * yh / lift_r) ** 2)
                    z += lift * bell * (fade ** 2)
                side_verts.append((x, y, z))
        for i in range(n_out):
            a = base + i
            side_faces.append((a, a + 1, base + n_out + 2 + i, base + n_out + 1 + i))

    # front/back strips were authored around y = 0; move them onto the building centre
    verts = [(v[0], v[1] + BCY, v[2]) for v in verts]
    ob_a = add_mesh(name + "_FB", verts, faces, col, material)
    ob_b = add_mesh(name + "_LR", side_verts, side_faces, col, material)
    shade_smooth(ob_a)
    shade_smooth(ob_b)
    return join_objs(name, [ob_a, ob_b])


def railing_run(name, p0, p1, col, material, height=1.02):
    p0 = Vector(p0)
    p1 = Vector(p1)
    length = (p1 - p0).length
    if length < 0.3:
        return None
    n = max(2, int(length / 0.45) + 1)
    dirv = (p1 - p0).normalized()
    rot = dirv.to_track_quat("X", "Z").to_euler()
    obs = []
    obs.append(add_box(name + "_Top", (length, 0.10, 0.09),
                       ((p0 + p1).x * 0.5, (p0 + p1).y * 0.5, p0.z + height),
                       col, material, rot=rot))
    obs.append(add_box(name + "_Bot", (length, 0.09, 0.08),
                       ((p0 + p1).x * 0.5, (p0 + p1).y * 0.5, p0.z + 0.20),
                       col, material, rot=rot))
    for i in range(n):
        t = i / (n - 1)
        p = p0.lerp(p1, t)
        obs.append(add_box("%s_P%d" % (name, i), (0.075, 0.075, height - 0.06),
                           (p.x, p.y, p.z + height * 0.5), col, material, rot=rot))
    return join_objs(name, obs)


def build_balcony_railing(col, material):
    obs = []
    w = BW + BALC_OV * 2
    d = BD + BALC_OV * 2
    z = F2 + 0.22
    x0, x1 = -w * 0.5, w * 0.5
    y0, y1 = BCY - d * 0.5, BCY + d * 0.5
    obs.append(railing_run("RAIL_Front", (x0, y0, z), (x1, y0, z), col, material))
    obs.append(railing_run("RAIL_Left", (x0, y0, z), (x0, y1, z), col, material))
    obs.append(railing_run("RAIL_Right", (x1, y0, z), (x1, y1, z), col, material))
    obs.append(railing_run("RAIL_Back", (x0, y1, z), (x1, y1, z), col, material))
    return join_objs("V4_RAILING", obs)


def build_eave_board(w, d, eave_z, col, material):
    """Continuous eave fascia + drip board: gives the eave real thickness."""
    obs = []
    z = eave_z - 0.04
    for sign in (-1, 1):
        obs.append(add_box("EAVE_FB%d" % sign, (w, 0.12, 0.18),
                           (0, BCY + sign * (d * 0.5 - 0.05), z), col, material))
        obs.append(add_box("EAVE_LR%d" % sign, (0.12, d, 0.18),
                           (sign * (w * 0.5 - 0.05), BCY, z), col, material))
        # drip tiles just under the fascia
        n = int(w / 0.312)
        for i in range(n):
            x = -w * 0.5 + 0.16 + i * (w - 0.32) / (n - 1)
            obs.append(add_box("DRIP_F%d_%d" % (sign, i), (0.16, 0.07, 0.12),
                               (x, BCY + sign * (d * 0.5 + 0.02), z - 0.13),
                               col, material))
        n2 = int(d / 0.312)
        for i in range(n2):
            y = BCY - d * 0.5 + 0.16 + i * (d - 0.32) / (n2 - 1)
            obs.append(add_box("DRIP_L%d_%d" % (sign, i), (0.07, 0.16, 0.12),
                               (sign * (w * 0.5 + 0.02), y, z - 0.13), col,
                               material))
    return join_objs("ROOF_EAVE_BOARD", obs)


def build_main_roof(col, material, stage="s1"):
    w = BW + EAVE_OV * 2
    d = BD + EAVE_OV * 2
    obs = []
    roof = roof_grid("ROOF_Main_V4", w, d, F2_TOP, RIDGE, col, material,
                     nx=56, ny=52, lift=0.18)
    obs.append(roof)
    obs.append(build_eave_board(w, d, F2_TOP, col, material))
    if stage != "s1":
        obs.append(tile_rows("ROOF_TilesV4", w, d, F2_TOP, RIDGE, col, material,
                             spacing=0.312, lift=0.18, samples=22))
        obs.append(eave_tiles("ROOF_WadangV4", w, d, F2_TOP, col, material, lift=0.18))
    # main ridge along X
    obs.append(ridge_beam("RIDGE_Main", (-w * 0.5 + d * 0.5, BCY, RIDGE + 0.10),
                          (w * 0.5 - d * 0.5, BCY, RIDGE + 0.10), col, material,
                          width=0.30, height=0.26, layers=3))
    # chiwen at both ends
    obs.append(chiwen("RIDGE_ChiwenL", (-w * 0.5 + d * 0.5 - 0.30, BCY, RIDGE + 0.06),
                      col, material, flip=1.0))
    obs.append(chiwen("RIDGE_ChiwenR", (w * 0.5 - d * 0.5 + 0.30, BCY, RIDGE + 0.06),
                      col, material, flip=1.0))
    # hip ridges: from each ridge end down to the four corners
    for sx in (-1, 1):
        rx = sx * (w * 0.5 - d * 0.5)
        for sy in (-1, 1):
            px = sx * w * 0.5
            py = BCY + sy * d * 0.5
            p0 = (rx, BCY, RIDGE - 0.02)
            p1 = (px, py, F2_TOP + 0.08)
            obs.append(ridge_beam("RIDGE_Hip_%d%d" % (sx, sy), p0, p1, col, material,
                                  width=0.24, height=0.13, layers=3))
            obs.append(add_box("HIP_Tip_%d%d" % (sx, sy), (0.20, 0.20, 0.20),
                               (px, py, F2_TOP + 0.20), col, material))
            obs.append(add_box("HIP_Horn_%d%d" % (sx, sy), (0.14, 0.14, 0.26),
                               (px, py, F2_TOP + 0.34), col, material,
                               rot=(math.radians(-18), 0, 0)))
    return join_objs("V4_ROOF_MAIN", obs)


# ---------------------------------------------------------------- S2 details
PAL = {}


def P(key):
    """Palette cache: stage-2 materials with real colours."""
    if key in PAL:
        return PAL[key]
    spec = {
        "wall":    ((0.90, 0.87, 0.79), 0.80, 0.0),
        "wood":    ((0.21, 0.12, 0.07), 0.62, 0.0),
        "wood_l":  ((0.34, 0.21, 0.11), 0.60, 0.0),
        "plaster": ((0.93, 0.90, 0.83), 0.85, 0.0),
        "stone":   ((0.56, 0.55, 0.52), 0.88, 0.0),
        "stone_d": ((0.31, 0.31, 0.30), 0.90, 0.0),
        "stone_l": ((0.70, 0.69, 0.65), 0.86, 0.0),
        "tile":    ((0.255, 0.265, 0.275), 0.72, 0.0),
        "gold":    ((0.66, 0.50, 0.22), 0.35, 0.85),
        "red":     ((0.58, 0.10, 0.07), 0.55, 0.0),
        "lacquer": ((0.30, 0.06, 0.05), 0.42, 0.0),
        "glass":   ((0.72, 0.80, 0.82), 0.10, 0.0),
        "interior": ((0.09, 0.07, 0.055), 0.92, 0.0),
        "leaf":    ((0.32, 0.45, 0.16), 0.75, 0.0),
        "leaf_l":  ((0.47, 0.58, 0.20), 0.75, 0.0),
        "cloth":   ((0.86, 0.79, 0.66), 0.92, 0.0),
        "carpet":  ((0.48, 0.09, 0.09), 0.95, 0.0),
        "paint":   ((0.22, 0.36, 0.34), 0.80, 0.0),
    }[key]
    m = mat("M_" + key, spec[0], rough=spec[1], metal=spec[2],
            alpha=0.22 if key == "glass" else 1.0)
    PAL[key] = m
    return m


def glow(key, rgb, strength=2.0):
    if key in PAL:
        return PAL[key]
    PAL[key] = mat("E_" + key, rgb, rough=0.5, emit=rgb, emit_str=strength)
    return PAL[key]


def build_base_carving(col):
    """Meander (huiwen) bands + lotus medallions on the sumeru seat."""
    obs = []
    half = BASE * 0.5
    # continuous carved band (reads as a recessed frieze on all four faces)
    band_z = 0.66
    band_h = 0.20
    for sign in (-1, 1):
        obs.append(add_box("HUI_FB%d" % sign, (BASE - 0.06, 0.05, band_h),
                           (0, sign * (half + 0.012), band_z), col, P("stone_d")))
        obs.append(add_box("HUI_LR%d" % sign, (0.05, BASE - 0.06, band_h),
                           (sign * (half + 0.012), 0, band_z), col, P("stone_d")))
    # sparse raised motifs so the band is not a flat stripe
    for i in range(14):
        t = -half + 0.55 + i * (BASE - 1.10) / 13.0
        for axis in ("x", "y"):
            for sign in (-1, 1):
                if axis == "x":
                    loc = (sign * (half + 0.03), t, band_z)
                    dims = (0.05, 0.22, 0.13)
                else:
                    loc = (t, sign * (half + 0.03), band_z)
                    dims = (0.22, 0.05, 0.13)
                obs.append(add_box("HUI_%s%d_%d" % (axis, sign, i), dims, loc,
                                   col, P("stone_l")))
    # lotus medallion on all four faces
    for axis in ("x", "y"):
        for sign in (-1, 1):
            cz = 0.52
            if axis == "x":
                base = (sign * (half + 0.02), 0.0, cz)
                rot0 = math.pi * 0.5
            else:
                base = (0.0, sign * (half + 0.02), cz)
                rot0 = 0.0
            obs.append(add_cyl("MED_Core_%s%d" % (axis, sign), 0.17, 0.07,
                               base, col, P("stone_l"), segments=20,
                               rot=(0, rot0, 0)))
            for k in range(8):
                ang = 2 * math.pi * k / 8
                px = base[0] + (math.cos(ang) * 0.30 if axis == "x" else 0.0)
                py = base[1] + (0.0 if axis == "x" else math.cos(ang) * 0.30)
                pz = cz + math.sin(ang) * 0.30
                if axis == "x":
                    pz = cz + math.sin(ang) * 0.30
                obs.append(add_box("MED_P_%s%d_%d" % (axis, sign, k),
                                   (0.09, 0.06, 0.16), (px, py, pz), col,
                                   P("stone_l"),
                                   rot=(0, rot0, ang)))
    return join_objs("V4_BASE_CARVE", obs)


def build_rafters(col):
    """Eave assembly: frieze board + rafter ends + bracket blocks."""
    obs = []
    w = BW + EAVE_OV * 2
    d = BD + EAVE_OV * 2
    z = F2_TOP - 0.10
    for sign in (-1, 1):
        # front / back frieze
        obs.append(add_box("FRIEZE_FB%d" % sign, (w, 0.10, 0.34),
                           (0, BCY + sign * (d * 0.5 - 0.05), z), col, P("wood")))
        obs.append(add_box("FRIEZE_LR%d" % sign, (0.10, d, 0.34),
                           (sign * (w * 0.5 - 0.05), BCY, z), col, P("wood")))
        n = int(w / 0.34)
        for i in range(n + 1):
            x = -w * 0.5 + 0.18 + i * (w - 0.36) / n
            obs.append(add_box("RAF_FB%d_%d" % (sign, i), (0.075, 0.34, 0.09),
                               (x, BCY + sign * (d * 0.5 + 0.08), z - 0.05),
                               col, P("wood")))
            if i % 2 == 0:
                # bracket set: block + arm + diagonal (dougong silhouette)
                obs.append(add_box("DOU_FB%d_%d" % (sign, i), (0.17, 0.17, 0.15),
                                   (x, BCY + sign * (d * 0.5 - 0.02), z - 0.19),
                                   col, P("gold")))
                obs.append(add_box("ARM_FB%d_%d" % (sign, i), (0.62, 0.12, 0.09),
                                   (x, BCY + sign * (d * 0.5 + 0.02), z - 0.26),
                                   col, P("wood_l")))
                obs.append(add_box("ANG_FB%d_%d" % (sign, i), (0.10, 0.34, 0.08),
                                   (x, BCY + sign * (d * 0.5 + 0.10), z - 0.31),
                                   col, P("wood")))
        n2 = int(d / 0.34)
        for i in range(n2 + 1):
            y = BCY - d * 0.5 + 0.18 + i * (d - 0.36) / n2
            obs.append(add_box("RAF_LR%d_%d" % (sign, i), (0.34, 0.075, 0.09),
                               (sign * (w * 0.5 + 0.08), y, z - 0.05),
                               col, P("wood")))
            if i % 2 == 0:
                obs.append(add_box("DOU_LR%d_%d" % (sign, i), (0.17, 0.17, 0.17),
                                   (sign * (w * 0.5 - 0.02), y, z - 0.20),
                                   col, P("gold")))
    return join_objs("V4_RAFTERS", obs)


def lattice(name, w, h, col, x_cols, y_rows, bar=0.036, depth=0.06,
            loc=(0, 0, 0), rot_z=0.0):
    """Parametric lattice panel (geshan / ice-crack style grid)."""
    obs = []
    obs.append(add_box(name + "_F", (w, depth, 0.07), loc, col, P("wood"),
                       rot_z=rot_z))
    for i in range(x_cols + 1):
        u = -w * 0.5 + w * i / x_cols
        obs.append(add_box("%s_V%d" % (name, i), (bar, depth * 0.8, h),
                           (loc[0] + math.cos(rot_z) * u,
                            loc[1] + math.sin(rot_z) * u, loc[2] + h * 0.5),
                           col, P("wood_l"), rot_z=rot_z))
    for j in range(y_rows + 1):
        v = h * j / y_rows
        obs.append(add_box("%s_H%d" % (name, j), (w, depth * 0.8, bar),
                           (loc[0], loc[1], loc[2] + v), col, P("wood_l"),
                           rot_z=rot_z))
    return join_objs(name, obs)


def build_facade(col):
    """Openings: 1F lattice shopfronts, 2F open gallery bays."""
    obs = []
    y_front = BCY - BD * 0.5
    y_back = BCY + BD * 0.5
    # 1F front: two lattice bays each side of the door
    for sx in (-1, 1):
        cx = sx * 3.55
        obs.append(lattice("LAT_F1_%d" % sx, 3.1, 2.05, col, 7, 8,
                           loc=(cx, y_front - 0.20, F1 + 0.36)))
    # 1F side windows
    for sx in (-1, 1):
        for sy in (-1, 1):
            obs.append(lattice("LAT_F1S_%d%d" % (sx, sy), 1.5, 1.75, col, 5, 6,
                               loc=(sx * BW * 0.5, BCY + sy * 1.6, F1 + 0.55),
                               rot_z=math.pi * 0.5))
    # 2F front: three lattice bays inside the balcony (wall is inset)
    for i, cx in enumerate((-3.4, 0.0, 3.4)):
        obs.append(lattice("LAT_F2_%d" % i, 2.9, 2.08, col, 7, 7,
                           loc=(cx, BCY - BD * 0.5 + 0.18, F2 + 0.32)))
    # 2F back + sides
    for i, cx in enumerate((-3.4, 0.0, 3.4)):
        obs.append(lattice("LAT_F2B_%d" % i, 2.9, 1.85, col, 7, 6,
                           loc=(cx, y_back - 0.18, F2 + 0.55), rot_z=math.pi))
    for sx in (-1, 1):
        for i, cy in enumerate((BCY - 1.9, BCY + 1.9)):
            obs.append(lattice("LAT_F2S_%d%d" % (sx, i), 2.2, 1.85, col, 6, 6,
                               loc=(sx * BW * 0.5, cy, F2 + 0.55),
                               rot_z=math.pi * 0.5))
    # stone plinth band (lejiao) around the ground floor, skipping the doorway
    door_w = 2.60
    seg = (BW - door_w) * 0.5
    for sx in (-1, 1):
        obs.append(add_box("LEJ_F%d" % sx, (seg, 0.10, 0.54),
                           (sx * (door_w * 0.5 + seg * 0.5), y_front - 0.04,
                            F1 + 0.27), col, P("stone_l")))
    obs.append(add_box("LEJ_B", (BW, 0.10, 0.54), (0, y_back + 0.04, F1 + 0.27),
                       col, P("stone_l")))
    for sx in (-1, 1):
        obs.append(add_box("LEJ_S%d" % sx, (0.10, BD, 0.54),
                           (sx * BW * 0.5, BCY, F1 + 0.27), col, P("stone_l")))
    # hanging fascia under the balcony slab
    obs.append(add_box("GUA_F", (BW + BALC_OV * 2 - 0.12, 0.09, 0.24),
                       (0, BCY - BD * 0.5 - BALC_OV, F2 + 0.03), col, P("wood_l")))
    return join_objs("V4_FACADE", obs)


def build_plaque(col):
    """Black lacquer board with gilt frame and raised characters."""
    z = 4.60
    y = BCY - BD * 0.5 - BALC_OV - 0.02
    obs = []
    obs.append(add_box("PLAQUE_Board", (2.62, 0.10, 0.66), (0, y, z), col,
                       P("lacquer")))
    obs.append(add_box("PLAQUE_FrameT", (2.78, 0.13, 0.06), (0, y, z + 0.34),
                       col, P("gold")))
    obs.append(add_box("PLAQUE_FrameB", (2.78, 0.13, 0.06), (0, y, z - 0.34),
                       col, P("gold")))
    for sx in (-1, 1):
        obs.append(add_box("PLAQUE_FrameS%d" % sx, (0.06, 0.13, 0.74),
                           (sx * 1.36, y, z), col, P("gold")))
    # characters
    try:
        cu = bpy.data.curves.new("PLQ_TXT", "FONT")
        cu.body = "\u975e\u9057\u827a\u672f\u9986"
        cu.align_x = "CENTER"
        cu.align_y = "CENTER"
        cu.size = 0.40
        cu.extrude = 0.02
        for path in ("C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/msyh.ttc"):
            if os.path.exists(path):
                try:
                    cu.font = bpy.data.fonts.load(path)
                    break
                except Exception:
                    pass
        ob = bpy.data.objects.new("PLQ_TXT", cu)
        bpy.context.scene.collection.objects.link(ob)
        ob.location = (0, y - 0.06, z)
        ob.rotation_euler = (math.pi * 0.5, 0, 0)
        bpy.context.view_layer.objects.active = ob
        obs.append(ob)
    except Exception as exc:
        log("plaque text skipped: %s" % exc)
    return join_objs("V4_PLAQUE", obs)


def build_lanterns(col):
    """Red paper lanterns with caps, ribs and tassels."""
    red = glow("lantern", (0.86, 0.11, 0.05), 0.7)
    obs = []
    spots = []
    yf = BCY - BD * 0.5
    for x in (-4.45, -1.55, 1.55, 4.45):
        spots.append((x, yf - 0.95, F1_TOP - 0.80, 0.32))
    for x in (-3.9, 0.0, 3.9):
        spots.append((x, yf - 1.05, F2_TOP - 0.70, 0.36))
    for sx in (-1, 1):
        spots.append((sx * (BW * 0.5 + 1.0), yf + 0.6, F2_TOP - 0.70, 0.30))
    for i, (x, y, z, r) in enumerate(spots):
        obs.append(add_cyl("LAN_%d_Rod" % i, 0.012, 0.55, (x, y, z + 0.42), col,
                           P("wood")))
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=r)
        bmesh.ops.scale(bm, vec=(1.0, 1.0, 0.78), verts=bm.verts)
        ob = _finish("LAN_%d_Body" % i, bm, col, red, loc=(x, y, z))
        shade_smooth(ob)
        obs.append(ob)
        for cap_z in (z + r * 0.80, z - r * 0.80):
            obs.append(add_cyl("LAN_%d_Cap_%.2f" % (i, cap_z), r * 0.42, 0.055,
                               (x, y, cap_z), col, P("gold"), segments=12))
        obs.append(add_cyl("LAN_%d_Tas" % i, 0.016, 0.26, (x, y, z - r * 1.05),
                           col, P("red"), segments=6))
    return join_objs("V4_LANTERNS", obs)


def build_railing_v2(col):
    """Replace the picket fence with a timber balustrade (posts + rails + slats)."""
    obs = []
    w = BW + BALC_OV * 2
    d = BD + BALC_OV * 2
    z = F2 + 0.22
    h = 0.88
    x0, x1 = -w * 0.5, w * 0.5
    y0, y1 = BCY - d * 0.5, BCY + d * 0.5
    sides = (((x0, y0), (x1, y0), 0.0), ((x1, y0), (x1, y1), math.pi * 0.5),
             ((x0, y1), (x1, y1), 0.0), ((x0, y0), (x0, y1), math.pi * 0.5))
    for si, (p0, p1, rz) in enumerate(sides):
        p0 = Vector((p0[0], p0[1], 0))
        p1 = Vector((p1[0], p1[1], 0))
        length = (p1 - p0).length
        cx = (p0.x + p1.x) * 0.5
        cy = (p0.y + p1.y) * 0.5
        obs.append(add_box("RL2_Top%d" % si, (length, 0.11, 0.10),
                           (cx, cy, z + h), col, P("wood_l"), rot_z=rz))
        obs.append(add_box("RL2_Mid%d" % si, (length, 0.08, 0.07),
                           (cx, cy, z + 0.24), col, P("wood_l"), rot_z=rz))
        n_post = max(2, int(length / 1.15) + 1)
        for i in range(n_post):
            t = i / (n_post - 1)
            p = p0.lerp(p1, t)
            obs.append(add_box("RL2_Post%d_%d" % (si, i), (0.14, 0.14, h + 0.14),
                               (p.x, p.y, z + (h + 0.14) * 0.5), col, P("wood"),
                               rot_z=rz))
            obs.append(add_box("RL2_Cap%d_%d" % (si, i), (0.20, 0.20, 0.06),
                               (p.x, p.y, z + h + 0.17), col, P("gold"), rot_z=rz))
        n_slat = max(4, int(length / 0.24))
        for i in range(1, n_slat):
            t = i / n_slat
            p = p0.lerp(p1, t)
            obs.append(add_box("RL2_Slat%d_%d" % (si, i), (0.055, 0.055, h - 0.30),
                               (p.x, p.y, z + 0.27 + (h - 0.30) * 0.5), col,
                               P("wood_l"), rot_z=rz))
    return join_objs("V4_RAIL2", obs)


def build_interior_shell(col):
    """Interior floors only; the enclosure now comes from the real room geometry."""
    obs = []
    obs.append(add_box("INT_FLOOR_F1", (BW - 0.7, BD - 0.7, 0.05),
                       (0, BCY, F1 + 0.025), col, P("stone_l")))
    obs.append(add_box("INT_FLOOR_F2", (BW - 0.7, BD - 0.7, 0.05),
                       (0, BCY, F2 + 0.275), col, P("wood_l")))
    return join_objs("V4_INT_SHELL", obs)


def blob(name, radius, loc, col, material, subdiv=2, squash=1.0):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    bmesh.ops.scale(bm, vec=(1.0, 1.0, squash), verts=bm.verts)
    ob = _finish(name, bm, col, material, loc=loc)
    shade_smooth(ob)
    return ob


def build_street_props(col):
    """Micro-diorama street corner: planters, trees, bamboo, lamps, banners."""
    obs = []
    warm = glow("lamplight", (1.0, 0.72, 0.38), 1.6)
    # stone planters along the front street
    for i, (cx, cy, sx) in enumerate(((-5.6, -5.6, 2.6), (5.4, -5.7, 2.2))):
        obs.append(add_box("PLANTER_%d" % i, (sx, 0.95, 0.52),
                           (cx, cy, PL_TOP + 0.26), col, P("stone")))
        obs.append(add_box("PLANTER_S%d" % i, (sx - 0.18, 0.78, 0.10),
                           (cx, cy, PL_TOP + 0.50), col, P("interior")))
        for k in range(4):
            obs.append(blob("FLOWER_%d_%d" % (i, k), 0.20,
                            (cx - sx * 0.35 + k * sx * 0.24, cy,
                             PL_TOP + 0.62), col, P("leaf_l"), subdiv=1, squash=0.7))
    # trees: trunk + leaf clusters
    for i, (tx, ty) in enumerate(((-6.6, -6.4), (6.3, -6.2))):
        obs.append(add_cyl("TREE_%d_Trunk" % i, 0.16, 2.4, (tx, ty, PL_TOP + 1.2),
                           col, P("wood"), segments=8))
        for k, (dx, dy, dz, r) in enumerate(((0.0, 0.0, 2.55, 0.98),
                                             (-0.62, 0.18, 2.20, 0.72),
                                             (0.58, 0.22, 2.25, 0.68),
                                             (0.10, -0.48, 2.85, 0.62),
                                             (-0.30, 0.55, 2.60, 0.55),
                                             (0.42, -0.30, 2.45, 0.58),
                                             (-0.10, 0.05, 3.05, 0.60))):
            obs.append(blob("TREE_%d_L%d" % (i, k), r, (tx + dx, ty + dy, PL_TOP + dz),
                            col, P("leaf_l") if k % 2 else P("leaf"), subdiv=2))
        for k, (ax, ay) in enumerate(((-0.45, 0.1), (0.4, -0.15))):
            obs.append(add_cyl("TREE_%d_Branch%d" % (i, k), 0.07, 1.5,
                               (tx + ax * 0.5, ty + ay * 0.5, PL_TOP + 2.05),
                               col, P("wood"), segments=6,
                               rot=(ay * 0.5, ax * 0.5, 0)))
    # bamboo clumps
    for i, (bx, by) in enumerate(((-7.1, -1.2), (7.2, -0.6), (-7.2, 2.6))):
        for k in range(5):
            h = 2.6 + 0.35 * k
            obs.append(add_cyl("BAM_%d_%d" % (i, k), 0.045, h,
                               (bx + 0.13 * k - 0.2, by + 0.1 * k, PL_TOP + h * 0.5),
                               col, P("leaf"), segments=6))
    # stone lanterns
    for i, (lx, ly) in enumerate(((-4.2, -6.3), (4.6, -6.3))):
        obs.append(add_box("LAMP_%d_Base" % i, (0.52, 0.52, 0.18),
                           (lx, ly, PL_TOP + 0.09), col, P("stone")))
        obs.append(add_cyl("LAMP_%d_Shaft" % i, 0.13, 0.86, (lx, ly, PL_TOP + 0.6),
                           col, P("stone"), segments=8))
        obs.append(add_box("LAMP_%d_Box" % i, (0.42, 0.42, 0.42),
                           (lx, ly, PL_TOP + 1.24), col, warm))
        obs.append(add_box("LAMP_%d_Cap" % i, (0.60, 0.60, 0.10),
                           (lx, ly, PL_TOP + 1.50), col, P("stone_d")))
    # vertical banners (shufan)
    for i, (px, py, rz) in enumerate(((-7.3, -3.2, 0.0), (7.3, -3.4, 0.0))):
        obs.append(add_cyl("BAN_%d_Pole" % i, 0.07, 4.0, (px, py, PL_TOP + 2.0),
                           col, P("wood"), segments=8))
        obs.append(add_box("BAN_%d_Arm" % i, (0.75, 0.09, 0.09),
                           (px - math.copysign(0.40, px * 0.0 + 1.0), py,
                            PL_TOP + 3.86), col, P("wood")))
        obs.append(add_box("BAN_%d_Cloth" % i, (0.72, 0.04, 1.55),
                           (px - 0.34, py, PL_TOP + 2.95), col, P("cloth")))
        obs.append(add_box("BAN_%d_Tas" % i, (0.07, 0.07, 0.22),
                           (px - 0.34, py, PL_TOP + 2.05), col, P("red")))
    # A-frame display boards beside the entrance
    for i, (dx, dz) in enumerate(((-3.1, 0.0), (3.0, 0.0))):
        by = BCY - BD * 0.5 - 1.75
        obs.append(add_box("EASEL_%d" % i, (0.86, 0.06, 1.12),
                           (dx, by, PL_TOP + 0.62), col, P("wood_l"), rot_z=0.12))
        obs.append(add_box("EASEL_%d_Leg" % i, (0.07, 0.62, 0.07),
                           (dx, by - 0.20, PL_TOP + 0.10), col, P("wood")))
    return join_objs("V4_STREET_PROPS", obs)


def build_annex(col):
    """Right-hand lean-to with a cream awning (see R03/R08)."""
    obs = []
    x0 = BW * 0.5
    y_lo, y_hi = BCY - 2.3, BCY + 2.0
    width = 1.75
    # lean-to roof: from wall top down to the outer eave
    verts = [(x0, y_lo, F1_TOP - 0.18), (x0 + width, y_lo, F1_TOP - 0.62),
             (x0 + width, y_hi, F1_TOP - 0.62), (x0, y_hi, F1_TOP - 0.18)]
    obs.append(add_mesh("ANNEX_Roof", verts, [(0, 1, 2, 3)], col, P("tile")))
    # fascia + posts
    obs.append(add_box("ANNEX_Fascia", (0.10, y_hi - y_lo, 0.16),
                       (x0 + width, (y_lo + y_hi) * 0.5, F1_TOP - 0.66), col,
                       P("wood")))
    for k, yy in enumerate((y_lo + 0.25, y_hi - 0.25)):
        obs.append(add_cyl("ANNEX_Post%d" % k, 0.11, F1_TOP - F1 - 0.55,
                           (x0 + width - 0.1, yy, (F1 + F1_TOP) * 0.5 - 0.25),
                           col, P("wood"), segments=8))
    # cream awning under the lean-to
    av = [(x0, y_lo + 0.1, F1_TOP - 0.95), (x0 + width - 0.1, y_lo + 0.1, F1_TOP - 1.30),
          (x0 + width - 0.1, y_hi - 0.1, F1_TOP - 1.30), (x0, y_hi - 0.1, F1_TOP - 0.95)]
    obs.append(add_mesh("ANNEX_Awning", av, [(0, 1, 2, 3)], col, P("cloth")))
    # shopfront lattice under the awning
    obs.append(lattice("ANNEX_Lat", 3.9, 1.5, col, 9, 4,
                       loc=(x0 + 0.06, (y_lo + y_hi) * 0.5, F1 + 0.45),
                       rot_z=math.pi * 0.5))
    return join_objs("V4_ANNEX", obs)


def build_interior_v4(cbuild, cint):
    """Curated interiors: display plinths, glass cases, stair, frames, caisson."""
    obs = []
    yf = BCY - BD * 0.5
    yb = BCY + BD * 0.5
    # ---- ground floor carpet + central display table
    obs.append(add_box("F1_Carpet", (4.2, 6.2, 0.03), (0, BCY - 0.4, F1 + 0.075),
                       cint, P("carpet")))
    obs.append(add_box("F1_TableBody", (2.9, 1.35, 0.86), (0, BCY - 0.7, F1 + 0.46),
                       cint, P("wood")))
    obs.append(add_box("F1_TableTop", (3.05, 1.5, 0.07), (0, BCY - 0.7, F1 + 0.92),
                       cint, P("wood_l")))
    obs.append(add_box("F1_TableGlass", (2.6, 1.15, 0.36), (0, BCY - 0.7, F1 + 1.12),
                       cint, P("glass")))
    for k in range(3):
        obs.append(add_cyl("F1_Vase%d" % k, 0.11, 0.30,
                           (-0.8 + k * 0.8, BCY - 0.7, F1 + 1.0), cint,
                           P("stone_l"), segments=10))
    # ---- wall display cases on both sides
    for sx in (-1, 1):
        for k in range(2):
            cy = BCY - 1.5 + k * 2.4
            obs.append(add_box("F1_Case_%d%d" % (sx, k), (0.55, 1.7, 0.85),
                               (sx * 4.3, cy, F1 + 0.45), cint, P("wood")))
            obs.append(add_box("F1_CaseG_%d%d" % (sx, k), (0.48, 1.6, 0.55),
                               (sx * 4.3, cy, F1 + 1.16), cint, P("glass")))
    # ---- stair: straight flight against the back wall, up to the F2 gallery
    st_x = 2.55
    for k in range(16):
        obs.append(add_box("F1_Stair%d" % k, (1.25, 0.27, 0.185),
                           (st_x, yb - 2.55 + k * 0.27,
                            F1 + 0.09 + k * 0.185), cint, P("wood_l")))
    obs.append(add_box("F1_StairRail", (0.08, 4.1, 0.95),
                       (st_x + 0.68, yb - 0.6, F1 + 1.75), cint, P("wood")))
    # ---- picture frames: 6 on the ground floor
    def picture(name, w, h, loc, rot_z=0.0):
        parts = []
        parts.append(add_box(name + "_Frame", (w, 0.07, h), loc, cbuild, P("wood"),
                             rot_z=rot_z))
        parts.append(add_box(name + "_Canvas", (w - 0.16, 0.02, h - 0.16),
                             (loc[0] - math.sin(rot_z) * 0.055,
                              loc[1] - math.cos(rot_z) * 0.055, loc[2]),
                             cbuild, P("cloth"), rot_z=rot_z))
        ob = join_objs(name, parts)
        return ob

    picture("WF_FRAME_01", 1.15, 1.55, (-4.05, yf + 0.22, F1 + 1.75))
    picture("WF_FRAME_02", 1.15, 1.55, (4.05, yf + 0.22, F1 + 1.75))
    picture("WF_FRAME_03", 1.30, 1.70, (0.0, yb - 0.24, F1 + 1.80),
            rot_z=math.pi)
    for k, fx in enumerate((-4.05, 4.05)):
        picture("WF_FRAME_0%d" % (4 + k), 0.95, 1.30,
                (fx, yb - 0.24, F1 + 1.70), rot_z=math.pi)
    # ---- second floor: 9 frames around the gallery walls
    f2z = F2 + 1.75
    ys = BCY + BD * 0.5 - 0.28
    ysf = BCY - BD * 0.5 + 0.28
    for k, fx in enumerate((-4.2, -1.4, 1.4, 4.2)):
        picture("WF_FRAME_%02d" % (6 + k), 1.05, 1.45, (fx, ysf, f2z))
    picture("WF_FRAME_10", 1.35, 1.60, (0.0, ys, f2z), rot_z=math.pi)
    picture("WF_FRAME_11", 1.05, 1.45, (-3.6, ys, f2z), rot_z=math.pi)
    picture("WF_FRAME_12", 1.05, 1.45, (3.6, ys, f2z), rot_z=math.pi)
    for k, sy in enumerate((BCY - 1.6, BCY + 1.4)):
        picture("WF_FRAME_1%d" % (3 + k), 1.0, 1.4,
                (-BW * 0.5 + 0.28, sy, f2z), rot_z=-math.pi * 0.5)
    picture("WF_FRAME_15", 1.0, 1.4,
            (BW * 0.5 - 0.28, BCY - 0.2, f2z), rot_z=math.pi * 0.5)
    # ---- exposed roof structure (che shang ming zao): no ceiling between floors
    under_w = BW + EAVE_OV * 2 - 0.24
    under_d = BD + EAVE_OV * 2 - 0.24
    obs.append(roof_grid("INT_ROOF_UNDER", under_w, under_d, F2_TOP - 0.20,
                         RIDGE - 0.20, cint, P("wood"), nx=30, ny=28, lift=0.18))

    def chord(name, p0, p1, wdt, hgt, mat):
        p0v, p1v = Vector(p0), Vector(p1)
        vec = p1v - p0v
        mid = (p0v + p1v) * 0.5
        rot = vec.to_track_quat("Y", "Z").to_euler()
        return add_box(name, (wdt, vec.length, hgt), tuple(mid), cint, mat, rot=rot)

    # main beams across the hall + secondary joists
    for k, yy in enumerate((BCY - 1.55, BCY + 1.55)):
        obs.append(add_box("INT_BEAM_MAIN%d" % k, (BW + 0.5, 0.30, 0.36),
                           (0, yy, F2_TOP - 0.44), cint, P("wood_l")))
    for k in range(9):
        x = -4.4 + k * 1.1
        obs.append(add_box("INT_BEAM_SUB%d" % k, (0.16, BD + 0.3, 0.22),
                           (x, BCY, F2_TOP - 0.22), cint, P("wood_l")))
    # rafters following the two long slopes and the two hip slopes
    for sign in (-1, 1):
        for i in range(21):
            x = -6.1 + i * 0.61
            obs.append(chord("INT_RAF_F%d_%d" % (sign, i),
                             (x, BCY + sign * (under_d * 0.5 - 0.15), F2_TOP - 0.38),
                             (x, BCY + sign * 0.35, RIDGE - 0.40),
                             0.085, 0.11, P("wood_l")))
        for j in range(15):
            y = BCY - 4.2 + j * 0.6
            obs.append(chord("INT_RAF_L%d_%d" % (sign, j),
                             (sign * (under_w * 0.5 - 0.15), y, F2_TOP - 0.38),
                             (sign * 0.35, y, RIDGE - 0.40),
                             0.085, 0.11, P("wood_l")))

    # ---- gallery display cases + bench
    for sx in (-1, 1):
        for k in range(2):
            cx = sx * (2.9 + k * 1.9)
            cy = BCY + BD * 0.5 - 1.15
            obs.append(add_box("F2_Case_%d%d" % (sx, k), (1.3, 0.6, 0.80),
                               (cx, cy, F2 + 0.62), cint, P("wood")))
            obs.append(add_box("F2_CaseG_%d%d" % (sx, k), (1.16, 0.5, 0.50),
                               (cx, cy, F2 + 1.28), cint, P("glass")))
    obs.append(add_box("F2_Bench", (2.4, 0.5, 0.40), (0, BCY - 2.5, F2 + 0.42),
                       cint, P("wood_l")))

    # purlins (lintiao) running parallel to the ridge, visible from below
    for k, yy in enumerate((BCY - 4.25, BCY - 2.75, BCY - 1.25,
                            BCY + 1.25, BCY + 2.75, BCY + 4.25)):
        px, py, pz = roof_point(0.0, yy - BCY, under_w, under_d,
                                F2_TOP - 0.20, RIDGE - 0.20, lift=0.18)
        obs.append(add_box("INT_PURLIN%d" % k, (under_w - 0.2, 0.20, 0.26),
                           (0, yy, pz - 0.34), cint, P("wood")))
    for k, xx in enumerate((-5.2, -3.6, -2.0, 2.0, 3.6, 5.2)):
        px, py, pz = roof_point(xx, 0.0, under_w, under_d,
                                F2_TOP - 0.20, RIDGE - 0.20, lift=0.18)
        obs.append(add_box("INT_PURLIN_S%d" % k, (0.20, under_d - 0.2, 0.26),
                           (xx, BCY, pz - 0.34), cint, P("wood")))

    # ---- caisson hanging at the roof apex (two-step recess + painted medallion)
    cz = RIDGE - 1.18
    def ring(prefix, span, thick, zz, mat_key):
        h = span * 0.5
        for sx in (-1, 1):
            obs.append(add_box("%s_FB%d" % (prefix, sx), (span, thick, 0.14),
                               (0, BCY + sx * (h - thick * 0.5), zz), cint,
                               P(mat_key)))
            obs.append(add_box("%s_LR%d" % (prefix, sx), (thick, span - thick * 2, 0.14),
                               (sx * (h - thick * 0.5), BCY, zz), cint,
                               P(mat_key)))
    ring("CAISSON_RimOuter", 2.95, 0.20, cz, "gold")
    ring("CAISSON_RimInner", 2.30, 0.16, cz + 0.09, "wood_l")
    obs.append(add_box("CAISSON_PaintedPanel", (1.80, 1.80, 0.05),
                       (0, BCY, cz + 0.15), cint, P("paint")))
    obs.append(add_cyl("CAISSON_Medallion", 0.66, 0.05, (0, BCY, cz + 0.18), cint,
                       P("gold"), segments=24))
    obs.append(add_cyl("CAISSON_Core", 0.30, 0.06, (0, BCY, cz + 0.17), cint,
                       P("lacquer"), segments=20))
    # lotus petals + scroll ring: reads as caihua painting from below
    for k in range(12):
        ang = 2 * math.pi * k / 12
        obs.append(add_box("CAISSON_Petal%d" % k, (0.34, 0.10, 0.10),
                           (math.cos(ang) * 0.50, BCY + math.sin(ang) * 0.50,
                            cz + 0.09), cint, P("gold"), rot_z=ang))
        obs.append(add_box("CAISSON_Scroll%d" % k, (0.22, 0.07, 0.07),
                           (math.cos(ang) * 0.86, BCY + math.sin(ang) * 0.86,
                            cz + 0.08), cint, P("paint"),
                           rot_z=ang + math.pi / 12))
    obs.append(add_cyl("CAISSON_GoldRing", 1.02, 0.06, (0, BCY, cz + 0.11), cint,
                       P("gold"), segments=28))
    for k in range(12):
        ang = 2 * math.pi * k / 12
        obs.append(add_box("CAISSON_Rib%d" % k, (0.70, 0.07, 0.07),
                           (math.cos(ang) * 1.28, BCY + math.sin(ang) * 1.28,
                            cz + 0.02), cint, P("wood"), rot_z=ang))
    # pendant: hexagonal palace lantern hung from the caisson
    obs.append(add_cyl("CEIL_Rod", 0.02, 1.15, (0, BCY, cz - 0.60), cint, P("wood")))
    obs.append(add_cyl("CEIL_Lantern", 0.32, 0.68, (0, BCY, cz - 1.55), cint,
                       glow("ceil_lamp", (1.0, 0.78, 0.48), 1.4), segments=6))
    for sx in (-1, 1):
        for sy in (-1, 1):
            obs.append(add_box("CEIL_Beam_%d%d" % (sx, sy), (0.16, 0.16, 0.30),
                               (sx * 2.2, BCY + sy * 1.8, cz + 0.05), cint,
                               P("wood")))
    return join_objs("V4_INTERIOR", obs)


# ---------------------------------------------------------------- lights / cams
def build_lighting(scene):
    world = bpy.data.worlds.new("V4World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.62, 0.76, 0.92, 1.0)
    bg.inputs[1].default_value = 0.85

    sun_data = bpy.data.lights.new("V4Sun", "SUN")
    sun_data.energy = 2.0
    sun_data.angle = math.radians(6)
    sun_data.color = (1.0, 0.96, 0.90)
    sun = bpy.data.objects.new("V4Sun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(52), 0, math.radians(38))

    for i, (loc, energy) in enumerate((
            ((9.0, -10.0, 12.0), 120.0),
            ((-10.0, -6.0, 8.0), 70.0),
            ((0.0, -12.0, 5.0), 45.0))):
        ad = bpy.data.lights.new("V4Fill%d" % i, "AREA")
        ad.energy = energy
        ad.size = 9.0
        ad.color = (1.0, 0.94, 0.86)
        ob = bpy.data.objects.new("V4Fill%d" % i, ad)
        scene.collection.objects.link(ob)
        ob.location = loc
        d = Vector((0, BCY, 4.0)) - Vector(loc)
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

    # interior practicals (warm, so the rooms read as curated galleries)
    for i, (loc, power) in enumerate((
            ((0.0, BCY - 0.2, F1 + 2.30), 90.0),
            ((-3.2, BCY + 0.6, F1 + 2.20), 40.0),
            ((3.2, BCY + 0.6, F1 + 2.20), 40.0),
            ((0.0, BCY + 0.4, F2 + 1.85), 80.0),
            ((-3.6, BCY + 0.4, F2 + 1.90), 35.0),
            ((3.6, BCY + 0.4, F2 + 1.90), 35.0),
            ((0.0, BCY - 0.4, RIDGE - 2.6), 70.0))):
        pd = bpy.data.lights.new("V4In%d" % i, "POINT")
        pd.energy = power
        pd.color = (1.0, 0.82, 0.60)
        pd.shadow_soft_size = 0.7
        ob = bpy.data.objects.new("V4In%d" % i, pd)
        scene.collection.objects.link(ob)
        ob.location = loc


def add_camera(name, loc, target, lens=50.0, ortho=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    if ortho is not None:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def build_cameras():
    tgt = (0, BCY, 4.4)
    cams = {}
    cams["CAM_V4_Front34"] = add_camera("CAM_V4_Front34", (25.0, -29.0, 16.0), tgt, 60)
    cams["CAM_V4_Front"] = add_camera("CAM_V4_Front", (0.0, -36.0, 7.2), (0, BCY, 4.7), 60)
    cams["CAM_V4_Left"] = add_camera("CAM_V4_Left", (-33.0, -13.0, 10.5), tgt, 60)
    cams["CAM_V4_Right"] = add_camera("CAM_V4_Right", (33.0, -13.0, 10.5), tgt, 60)
    cams["CAM_V4_Back"] = add_camera("CAM_V4_Back", (-9.0, 31.0, 11.0), tgt, 60)
    cams["CAM_V4_Top"] = add_camera("CAM_V4_Top", (15.0, -17.0, 34.0), (0, BCY, 1.6), 60)
    cams["CAM_V4_F1"] = add_camera("CAM_V4_F1", (0.0, BCY - 2.95, F1 + 2.30),
                                   (0.0, BCY + 2.4, F1 + 2.95), 18)
    cams["CAM_V4_F2"] = add_camera("CAM_V4_F2", (-0.8, BCY - 2.65, F2 + 1.55),
                                   (1.0, BCY + 3.0, F2 + 1.15), 20)
    cams["CAM_V4_Ceiling"] = add_camera("CAM_V4_Ceiling", (2.4, BCY - 1.2, F2 + 1.55),
                                        (0.0, BCY + 0.2, RIDGE - 1.20), 24)
    cams["CAM_V4_Eave"] = add_camera("CAM_V4_Eave",
                                     (BW * 0.5 + 3.4, BCY - BD * 0.5 - 3.0, F2_TOP + 0.6),
                                     (BW * 0.5 - 1.2, BCY - BD * 0.5 + 1.4, F2_TOP - 0.3), 85)
    return cams


# ---------------------------------------------------------------- render
VIEWS = (
    ("v4_01_front34", "CAM_V4_Front34", 1500, 1125),
    ("v4_02_front", "CAM_V4_Front", 1500, 1125),
    ("v4_03_left", "CAM_V4_Left", 1500, 1125),
    ("v4_04_right", "CAM_V4_Right", 1500, 1125),
    ("v4_05_back", "CAM_V4_Back", 1500, 1125),
    ("v4_06_top", "CAM_V4_Top", 1400, 1400),
    ("v4_07_floor1", "CAM_V4_F1", 1500, 1000),
    ("v4_08_floor2", "CAM_V4_F2", 1500, 1000),
    ("v4_09_ceiling", "CAM_V4_Ceiling", 1400, 1000),
    ("v4_10_eave", "CAM_V4_Eave", 1400, 1050),
)


def render_views(scene, only=None):
    os.makedirs(RENDER_OUT, exist_ok=True)
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except Exception:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
        scene.view_settings.exposure = -0.15
    except Exception:
        pass
    try:
        scene.eevee.taa_render_samples = 32
    except Exception:
        pass
    for name, cam, w, h in VIEWS:
        if only and name not in only:
            continue
        cam_ob = bpy.data.objects.get(cam)
        if cam_ob is None:
            log("missing camera " + cam)
            continue
        scene.camera = cam_ob
        scene.render.resolution_x = w
        scene.render.resolution_y = h
        scene.render.filepath = os.path.join(RENDER_OUT, name + ".png")
        bpy.ops.render.render(write_still=True)
        log("rendered " + name)


def export_glb():
    out = os.path.join(G3D, "exports", "wenmai_gallery_v4.glb")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=out, export_format="GLB", use_selection=False,
        export_apply=True, export_yup=True, export_cameras=False,
        export_lights=False, export_materials="EXPORT", export_extras=True,
        export_texcoords=True, export_tangents=False, export_animations=False,
    )
    log("exported %s (%d bytes)" % (out, os.path.getsize(out)))
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = "s1"
    if "--stage" in argv:
        stage = argv[argv.index("--stage") + 1]
    do_render = "--no-render" not in argv
    only = None
    if "--only" in argv:
        only = set(argv[argv.index("--only") + 1].split(","))

    scene = reset_scene()
    clay = M()
    cbase = collection("V4_BASE")
    cbuild = collection("V4_BUILDING")
    croof = collection("V4_ROOF")
    if stage == "s1":
        build_base(cbase, clay)
        build_street(cbase, clay)
        build_walls(cbuild, clay)
        build_veranda(cbuild, clay)
        build_balcony_railing(cbuild, clay)
        build_skirt_roof(croof, clay)
        build_main_roof(croof, clay, stage="s1")
    else:
        build_base(cbase, P("stone"))
        build_base_carving(cbase)
        build_street(cbase, P("stone_l"))
        build_street_props(cbase)
        build_walls(cbuild, P("wall"), P("wood"))
        build_veranda(cbuild, P("wood"))
        build_annex(cbuild)
        build_railing_v2(cbuild)
        build_interior_shell(cbuild)
        build_facade(cbuild)
        build_plaque(cbuild)
        build_skirt_roof(croof, P("tile"))
        build_main_roof(croof, P("tile"), stage="s2")
        build_rafters(croof)
        build_lanterns(cbuild)
        build_interior_v4(cbuild, collection("V4_INTERIOR"))
    build_lighting(scene)
    build_cameras()

    os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
    log("saved " + BLEND_OUT)
    export_glb()
    if do_render:
        render_views(scene, only=only)
    log("stage %s done" % stage)


if __name__ == "__main__":
    main()
