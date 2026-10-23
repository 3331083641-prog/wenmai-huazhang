"""Shared contract for the 纹脉华章 heritage-gallery Blender build.

Every build module imports this so dimensions, materials and naming stay in one
place. Units are metres; +Z is up; the model is centred on the origin with the
plinth top at z = 0 and the street/garden below it.

The building itself is authored around its own centre (0, 0) and shifted by
BUILD_Y at assemble time, so the plinth keeps a real front street (3.8 m) and a
narrower back yard, exactly as the brief asks.

Naming contract (Three.js relies on these prefixes):
    BASE_*      plinth, steps, carved frieze, paving
    WALL_*      wall panels, dado, lintels
    COLUMN_*    timber columns
    FLOOR_01/02 storey slabs
    STAIR_*     staircase
    RAIL_*      balustrades
    BEAM_*      interior framing, purlins, ceiling
    ROOF_*      roof bodies
    TILE_*      tile strips / ridge caps
    DOOR_* / WIND_*  doors, lattice windows
    LANTERN_*   lanterns
    PROP_*      street furniture, plants, signs
    GALWALL_*   empty carrying a real display-wall plane (size in custom props)
    FRAME_F1_###, FRAME_F2_###   empty anchors for artwork frames
    CAM_*       camera anchor empties
"""
from __future__ import annotations

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

# ----------------------------------------------------------------- dimensions

BASE_SIZE = 14.0          # square plinth, side length
BASE_THICKNESS = 0.65     # plinth height below z = 0
PLINTH_DARK_H = 0.16      # lower dark stone foot
PLINTH_FRIEZE_H = 0.28    # carved middle band
PLINTH_TOP_H = 0.21       # pale stone deck
BASE_EDGE_W = 0.30        # raised border band on the deck
BASE_EDGE_H = 0.025

BUILD_X = 8.4             # hall footprint along X (width)
BUILD_DEPTH = 7.5         # hall footprint along Y (depth); Blender is Z-up,
                          # so the second horizontal axis is Y, not Z.
BUILD_Y = -0.55           # hall centre on the plinth (front street is deeper)
WALL_T = 0.16             # wall thickness
COL_R = 0.15              # main column radius (0.30 m diameter)
F1_H = 3.35               # ground storey clear height
F2_H = 2.95               # upper storey clear height
SLAB_T = 0.20             # floor slab thickness

Z_F1 = 0.25               # ground floor level (stone podium + deck)
Z_F2 = 3.60               # upper floor level
Z_TOP = Z_F2 + F2_H       # 6.55 top plate / wall head
EAVE_Z = 6.80             # main roof eave line
RIDGE_Z = 8.70            # main roof ridge

# roof
ROOF_OVERHANG = 0.90      # eave projection beyond the wall plane
ROOF_LOWER_OVERHANG = 0.70
ROOF_RISE = RIDGE_Z - EAVE_Z      # 1.90
ROOF_LOWER_RISE = 0.55    # skirt roof rise (second-floor ring eave)
ROOF_SLOPE_POW = 1.62     # >1 => concave (steep at ridge, flat at eave)
EAVE_LIFT = 0.40          # corner up-turn amount
ROOF_RIDGE_HALF = 1.55    # half length of the main ridge

# frames
FRAME_ANCHOR_Z_F1 = 1.75
FRAME_ANCHOR_Z_F2 = 5.05

# ------------------------------------------------------------------- stairs
# L-shaped switchback in the back-right corner. Two flights of 8 treads share
# one quarter landing; the upper flight lands on the front edge of the opening.
IX = BUILD_X / 2.0 - WALL_T       # 4.04 inner face of the side walls
IY = BUILD_DEPTH / 2.0 - WALL_T   # 3.59 inner face of the end walls
STAIR_W = 1.10
STAIR_TREAD = 0.27
STAIR_RISERS = 18
STAIR_RISE = (Z_F2 - Z_F1) / STAIR_RISERS
STAIR_BAND_A = (-(IY - 0.04), -(IY - 0.04) + STAIR_W)   # -3.55 .. -2.45
STAIR_BAND_B = (STAIR_BAND_A[1], STAIR_BAND_A[1] + 2.00)  # -2.45 .. -0.45
STAIR_X1 = IX                                             # foot of flight 1
STAIR_X0 = STAIR_X1 - 8 * STAIR_TREAD                     # landing right edge
STAIR_XM = STAIR_X0 - STAIR_W                             # landing left edge
STAIR_LANDING_Z = Z_F1 + 9 * STAIR_RISE

# ------------------------------------------------------------------- palette
# Colours sampled from the ten references and re-balanced for a lit toon scene.
PALETTE = {
    "roof_tile":    (0.330, 0.376, 0.418),
    "roof_tile_b":  (0.372, 0.412, 0.448),
    "roof_slate":   (0.212, 0.243, 0.278),
    "roof_ridge":   (0.259, 0.290, 0.325),
    "timber":       (0.545, 0.353, 0.235),
    "timber_dark":  (0.290, 0.180, 0.125),
    "timber_warm":  (0.639, 0.427, 0.271),
    "wood_light":   (0.706, 0.514, 0.337),
    "wall":         (0.937, 0.902, 0.831),
    "wall_shadow":  (0.851, 0.812, 0.741),
    "stone":        (0.725, 0.706, 0.655),
    "stone_dark":   (0.545, 0.529, 0.490),
    "stone_warm":   (0.784, 0.753, 0.690),
    "paving":       (0.659, 0.643, 0.604),
    "paving_b":     (0.706, 0.678, 0.628),
    "gravel":       (0.760, 0.735, 0.678),
    "red":          (0.698, 0.227, 0.173),
    "red_deep":     (0.478, 0.145, 0.114),
    "gold":         (0.710, 0.545, 0.216),
    "gold_light":   (0.847, 0.702, 0.365),
    "plant":        (0.310, 0.478, 0.227),
    "plant_dark":   (0.212, 0.345, 0.161),
    "plant_light":  (0.408, 0.565, 0.259),
    "bamboo":       (0.435, 0.545, 0.239),
    "flower":       (0.792, 0.400, 0.412),
    "porcelain":    (0.855, 0.888, 0.871),
    "porcelain_bl": (0.235, 0.353, 0.545),
    "ink":          (0.125, 0.110, 0.106),
    "paper":        (0.965, 0.945, 0.902),
    "lamp_glow":    (1.000, 0.800, 0.520),
}

EMISSIVE = {"lamp_glow"}


# ------------------------------------------------------------------- helpers

def reset_scene() -> bpy.types.Scene:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.engine = "BLENDER_EEVEE"
    return scene


def get_collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    return col


def srgb_to_linear(c: float) -> float:
    """PALETTE holds sRGB hex-derived values; shader sockets want linear."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def material(key: str, rough: float = 0.72, metal: float = 0.0) -> bpy.types.Material:
    """Flat-colour preview material; the web maps these by name to toon shaders."""
    name = f"M_{key}"
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    srgb = PALETTE[key]
    rgb = tuple(srgb_to_linear(c) for c in srgb)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nx = mat.node_tree.nodes
    bsdf = nx.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if key in EMISSIVE:
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 1.4
    mat.diffuse_color = (*rgb, 1.0)
    mat["toon_key"] = key
    mat["srgb"] = list(srgb)
    return mat


def link(obj: bpy.types.Object, col: bpy.types.Collection, name: str | None = None) -> bpy.types.Object:
    if name:
        obj.name = name
        obj.data.name = name
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def bm_to_object(bm: bmesh.types.BMesh, name: str, col: bpy.types.Collection,
                 mat_key: str | None = None, shade_smooth: bool = False) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    col.objects.link(obj)
    if mat_key:
        obj.data.materials.append(material(mat_key))
    if shade_smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj


def bevel(obj: bpy.types.Object, width: float = 0.012, segments: int = 1,
          angle: float = math.radians(40)) -> bpy.types.Object:
    """Small edge chamfer so timber/stone silhouettes catch a highlight."""
    mod = obj.modifiers.new("BEV", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = angle
    mod.harden_normals = False
    return obj


def box(name: str, col, size, center, mat_key="stone", rot_z: float = 0.0,
        chamfer: float = 0.0):
    sx, sy, sz = size
    cx, cy, cz = center
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((sx, sy, sz)), verts=bm.verts)
    if rot_z:
        bmesh.ops.rotate(bm, verts=bm.verts,
                         cent=Vector((0.0, 0.0, 0.0)),
                         matrix=Matrix.Rotation(rot_z, 3, "Z"))
    bmesh.ops.translate(bm, vec=Vector((cx, cy, cz)), verts=bm.verts)
    obj = bm_to_object(bm, name, col, mat_key)
    if chamfer:
        bevel(obj, chamfer)
    return obj


def cyl(name: str, col, radius: float, height: float, center, mat_key="timber",
        segments: int = 16, cap: bool = True, rot_x: float = 0.0):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=segments,
                          radius1=radius, radius2=radius, depth=height)
    if rot_x:
        bmesh.ops.rotate(bm, verts=bm.verts, cent=Vector((0.0, 0.0, 0.0)),
                         matrix=Matrix.Rotation(rot_x, 3, "X"))
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return bm_to_object(bm, name, col, mat_key, shade_smooth=True)


def prism(name: str, col, profile, extrusion: float, center, mat_key="stone",
          axis: str = "z"):
    """Extrude a 2-D polygon (list of (a, b)) along `axis` by `extrusion`."""
    bm = bmesh.new()
    verts = []
    for a, b in profile:
        if axis == "z":
            verts.append(bm.verts.new((a, b, 0.0)))
        elif axis == "y":
            verts.append(bm.verts.new((a, 0.0, b)))
        else:
            verts.append(bm.verts.new((0.0, a, b)))
    face = bm.faces.new(verts)
    bm.normal_update()
    axis_vec = {"z": Vector((0, 0, 1)), "y": Vector((0, 1, 0)),
                "x": Vector((1, 0, 0))}[axis]
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    moved = [e for e in res["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=axis_vec * extrusion, verts=moved)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return bm_to_object(bm, name, col, mat_key)


def join_objects(objs, name: str) -> bpy.types.Object:
    objs = [o for o in objs if o is not None]
    if not objs:
        raise ValueError(f"join_objects: nothing to join into {name}")
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = name
    joined.data.name = name
    return joined


def empty(name: str, col, location=(0, 0, 0), rot_z: float = 0.0,
          display: str = "PLAIN_AXES", size: float = 0.3, **props):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = display
    obj.empty_display_size = size
    obj.location = location
    obj.rotation_euler = (0.0, 0.0, rot_z)
    col.objects.link(obj)
    for key, value in props.items():
        obj[key] = value
    return obj


def smooth_curve(points, samples: int = 16):
    """Catmull-Rom through 2-D points -> denser polyline."""
    pts = [Vector((p[0], p[1], 0.0)) for p in points]
    if len(pts) < 3:
        return [(p.x, p.y) for p in pts]
    ext = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        for s in range(samples):
            t = s / samples
            t2, t3 = t * t, t * t * t
            v = 0.5 * ((2 * p1) + (-p0 + p2) * t
                       + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                       + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            out.append((v.x, v.y))
    out.append((pts[-1].x, pts[-1].y))
    return out


# ------------------------------------------------------------------- layout
# One source of truth for every facade opening. `u` is measured along the wall
# from its centre; `z0`/`h` are storey-local. build_core cuts the holes and
# build_interior fills them with doors and lattice, so the two can never drift.
#
# Piers are sized so the 15 frame anchors land on solid wall (see FRAME_TABLE in
# build_interior): every gap used by a frame is wider than the frame + 0.25 m.

OPENINGS = {
    # key: [(u_centre, width, z0, height, kind, pattern)]
    "f1_front": [(0.0, 2.00, 0.00, 2.50, "door", "door"),
                 (-2.62, 1.35, 0.85, 1.70, "window", "diamond"),
                 (2.62, 1.35, 0.85, 1.70, "window", "diamond")],
    "f1_back": [(-2.62, 1.35, 0.85, 1.70, "window", "grid"),
                (2.62, 1.35, 0.85, 1.70, "window", "grid")],
    "f1_left": [(-1.55, 1.35, 0.85, 1.70, "window", "grid"),
                (1.55, 1.35, 0.85, 1.70, "window", "grid")],
    "f1_right": [(-1.55, 1.35, 0.85, 1.70, "window", "meander"),
                 (1.55, 1.35, 0.85, 1.70, "window", "meander")],
    "f2_front": [(-2.62, 1.35, 0.72, 1.62, "window", "meander"),
                 (0.0, 1.35, 0.72, 1.62, "window", "diamond"),
                 (2.62, 1.35, 0.72, 1.62, "window", "meander")],
    "f2_back": [(-2.62, 1.35, 0.72, 1.62, "window", "grid"),
                (2.62, 1.35, 0.72, 1.62, "window", "grid")],
    "f2_left": [(-1.55, 1.35, 0.72, 1.62, "window", "diamond"),
                (1.55, 1.35, 0.72, 1.62, "window", "diamond")],
    "f2_right": [(-1.55, 1.35, 0.72, 1.62, "window", "grid"),
                 (1.55, 1.35, 0.72, 1.62, "window", "grid")],
}

WALL_LENGTH = {
    "front": BUILD_X, "back": BUILD_X, "left": BUILD_DEPTH, "right": BUILD_DEPTH,
}


def wall_plane(side: str, z_base: float):
    """Return ((x, y, z), rot_z) for the centre of a wall plane."""
    if side == "front":
        return (0.0, BUILD_DEPTH / 2.0 - WALL_T / 2.0, z_base), 0.0
    if side == "back":
        return (0.0, -BUILD_DEPTH / 2.0 + WALL_T / 2.0, z_base), math.pi
    if side == "right":
        return (BUILD_X / 2.0 - WALL_T / 2.0, 0.0, z_base), math.pi / 2.0
    return (-BUILD_X / 2.0 + WALL_T / 2.0, 0.0, z_base), -math.pi / 2.0


def opening_centres(key: str, z_base: float):
    """World placement for every opening of a facade key."""
    side = key.split("_", 1)[1]
    (ox, oy, _), rot = wall_plane(side, z_base)
    out = []
    ca, sa = math.cos(rot), math.sin(rot)
    for entry in OPENINGS[key]:
        u, w, z0, h, kind = entry[:5]
        pattern = entry[5] if len(entry) > 5 else "grid"
        out.append({
            "u": u, "x": ox + u * ca, "y": oy + u * sa, "w": w,
            "z0": z_base + z0, "h": h, "kind": kind, "pattern": pattern,
            "rot": rot, "wall": key,
        })
    return out


def piers(length: float, holes) -> list[tuple[float, float]]:
    """Solid wall intervals along a wall of `length`, given (u, w) holes."""
    spans = sorted((u - w / 2.0, u + w / 2.0) for u, w in holes)
    out = []
    cursor = -length / 2.0
    for a, b in spans:
        if a > cursor:
            out.append((cursor, a))
        cursor = max(cursor, b)
    if cursor < length / 2.0:
        out.append((cursor, length / 2.0))
    return out


def build_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ensure_dirs(*parts: str) -> str:
    p = os.path.join(build_dir(), *parts)
    os.makedirs(p, exist_ok=True)
    return p


def report(msg: str) -> None:
    print(f"[gallery] {msg}", flush=True)