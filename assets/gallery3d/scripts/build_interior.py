"""Interior and facade detail: lattice, doors, gallery walls, railings, framing.

Owns every FRAME_F#_### anchor and every GALWALL_* display-wall record.
Anchor rotation convention: an anchor's local +Y points into the room (towards
the viewer of the artwork), which the web turns into rotationY.

The 15 anchors sit on measured wall piers (see WALLS below); u/v are derived
from the same table so the model and the layout JSON cannot drift.
"""
from __future__ import annotations

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import gal_common as G  # noqa: E402
from gal_common import (  # noqa: E402
    BUILD_DEPTH, BUILD_X, F1_H, F2_H, IX, IY, OPENINGS, SLAB_T,
    STAIR_BAND_A, STAIR_BAND_B, STAIR_X0, STAIR_XM, WALL_T, Z_F1, Z_F2, Z_TOP,
    FRAME_ANCHOR_Z_F1, FRAME_ANCHOR_Z_F2, box, bm_to_object, cyl, empty,
    join_objects, material, prism, report, wall_plane,
)

HX = BUILD_X / 2.0
HY = BUILD_DEPTH / 2.0
INNER_X = IX
INNER_Y = IY


# ------------------------------------------------------------------ helpers

def _mat(x, y, z, rot):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, "Z")


def bar(name, col, p0, p1, w, h, mat_key="timber_dark", rot_z=0.0):
    """Timber between two points in the XY plane (used for diagonals)."""
    a, b = Vector((p0[0], p0[1], p0[2])), Vector((p1[0], p1[1], p1[2]))
    d = b - a
    length = d.length
    if length < 1e-5:
        return None
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((length, w, h)), verts=bm.verts)
    rot = d.normalized().to_track_quat("X", "Z").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
    bmesh.ops.translate(bm, vec=(a + b) * 0.5, verts=bm.verts)
    return bm_to_object(bm, name, col, mat_key)


def lattice(name, col, width, height, x, y, z, rot, pattern="grid",
            cols=None, rows=None, bar_t=0.028, depth=0.06,
            mat_key="timber_dark"):
    """Window / door infill: stile frame plus one of three traditional patterns."""
    parts = []
    fw = 0.075
    # outer frame
    parts.append(box(f"{name}_F0", col, (width, depth, fw),
                     (0, 0, height / 2 - fw / 2), mat_key))
    parts.append(box(f"{name}_F1", col, (width, depth, fw),
                     (0, 0, -height / 2 + fw / 2), mat_key))
    parts.append(box(f"{name}_F2", col, (fw, depth, height),
                     (-width / 2 + fw / 2, 0, 0), mat_key))
    parts.append(box(f"{name}_F3", col, (fw, depth, height),
                     (width / 2 - fw / 2, 0, 0), mat_key))
    iw = width - 2 * fw
    ih = height - 2 * fw

    if pattern == "diamond":
        # a coarse grid of square cells, each with an X brace (diamond lattice)
        cx_n = cols or max(2, round(iw / 0.34))
        cy_n = rows or max(3, round(ih / 0.34))
        for i in range(1, cx_n):
            px = -iw / 2 + iw * i / cx_n
            parts.append(box(f"{name}_V{i}", col, (bar_t, depth * 0.7, ih),
                             (px, 0, 0), mat_key))
        for j in range(1, cy_n):
            pz = -ih / 2 + ih * j / cy_n
            parts.append(box(f"{name}_H{j}", col, (iw, depth * 0.7, bar_t),
                             (0, 0, pz), mat_key))
        cw, ch = iw / cx_n, ih / cy_n
        for i in range(cx_n):
            for j in range(cy_n):
                x0 = -iw / 2 + i * cw
                z0 = -ih / 2 + j * ch
                parts.append(bar(f"{name}_D{i}{j}a", col,
                                 (x0, 0, z0 + (ch if j == 0 else 0.0)),
                                 (x0 + cw, 0, z0), bar_t * 0.8, depth * 0.6,
                                 mat_key))
    elif pattern == "meander":
        # sparse grid with a double border and a meander corner return
        cx_n = cols or max(2, round(iw / 0.40))
        cy_n = rows or max(3, round(ih / 0.40))
        parts.append(box(f"{name}_B0", col, (iw - 0.02, depth * 0.7, bar_t),
                         (0, 0, ih / 2 - 0.06), mat_key))
        parts.append(box(f"{name}_B1", col, (iw - 0.02, depth * 0.7, bar_t),
                         (0, 0, -ih / 2 + 0.06), mat_key))
        for i in range(1, cx_n):
            px = -iw / 2 + iw * i / cx_n
            parts.append(box(f"{name}_V{i}", col, (bar_t, depth * 0.7, ih),
                             (px, 0, 0), mat_key))
        for j in range(1, cy_n):
            pz = -ih / 2 + ih * j / cy_n
            parts.append(box(f"{name}_H{j}", col, (iw, depth * 0.7, bar_t),
                             (0, 0, pz), mat_key))
        # corner hooks
        for sx in (-1, 1):
            for sz in (-1, 1):
                parts.append(box(f"{name}_C{sx}{sz}", col,
                                 (0.10, depth * 0.8, 0.035),
                                 (sx * (iw / 2 - 0.14), 0, sz * (ih / 2 - 0.10)),
                                 mat_key))
                parts.append(box(f"{name}_Cv{sx}{sz}", col,
                                 (0.035, depth * 0.8, 0.10),
                                 (sx * (iw / 2 - 0.10), 0, sz * (ih / 2 - 0.16)),
                                 mat_key))
    else:  # grid
        cx_n = cols or max(2, round(iw / 0.34))
        cy_n = rows or max(3, round(ih / 0.34))
        for i in range(1, cx_n):
            px = -iw / 2 + iw * i / cx_n
            parts.append(box(f"{name}_V{i}", col, (bar_t, depth * 0.7, ih),
                             (px, 0, 0), mat_key))
        for j in range(1, cy_n):
            pz = -ih / 2 + ih * j / cy_n
            parts.append(box(f"{name}_H{j}", col, (iw, depth * 0.7, bar_t),
                             (0, 0, pz), mat_key))

    grp = join_objects(parts, name)
    grp.matrix_world = _mat(x, y, z, rot)
    return grp


def swing_door(name, col, width, height, x, y, z, rot):
    """Two-leaf timber door: solid lower panels, lattice uppers, brass rings."""
    parts = []
    half = width / 2.0
    for sign in (-1, 1):
        cx = sign * half / 2.0
        # stiles / rails
        parts.append(box(f"{name}_Leaf{sign}", col, (half - 0.02, 0.075, height),
                         (cx, 0, height / 2.0), "timber_dark"))
        parts.append(box(f"{name}_Panel{sign}", col, (half - 0.16, 0.10, height * 0.44),
                         (cx, -0.01, height * 0.23), "timber"))
        # three carved panels on the solid part
        for k in range(3):
            parts.append(box(f"{name}_P{sign}{k}", col, (half - 0.28, 0.03, height * 0.105),
                             (cx, -0.065, height * (0.075 + k * 0.135)), "timber_warm"))
        lat = lattice(f"{name}_Lat{sign}", col, half - 0.14, height * 0.46,
                      0, -0.02, 0, 0.0, "grid", cols=3, rows=4,
                      mat_key="timber_warm")
        lat.matrix_world = _mat(cx, 0, height * 0.72, 0.0)
        parts.append(lat)
        # brass ring
        parts.append(cyl(f"{name}_Ring{sign}", col, 0.055, 0.018,
                         (cx * 0.30, -0.075, height * 0.42), "gold", segments=12,
                         rot_x=math.pi / 2.0))
        parts.append(cyl(f"{name}_RingHole{sign}", col, 0.026, 0.022,
                         (cx * 0.30, -0.078, height * 0.42), "ink", segments=10,
                         rot_x=math.pi / 2.0))
        # studs
        for k in range(4):
            parts.append(cyl(f"{name}_Stud{sign}{k}", col, 0.016, 0.02,
                             (cx - half * 0.28 + k * half * 0.18, -0.072,
                              height * 0.58), "gold", segments=6,
                             rot_x=math.pi / 2.0))

    grp = join_objects(parts, name)
    grp.matrix_world = _mat(x, y, z, rot)
    return grp


# ------------------------------------------------------------ facade infill

def build_openings(col):
    """Jambs, sills, lattice and doors for every opening in the shared table."""
    for key, z_base in (("f1_front", Z_F1), ("f1_back", Z_F1),
                        ("f1_left", Z_F1), ("f1_right", Z_F1),
                        ("f2_front", Z_F2), ("f2_back", Z_F2),
                        ("f2_left", Z_F2), ("f2_right", Z_F2)):
        for i, op in enumerate(G.opening_centres(key, z_base)):
            x, y, z0 = op["x"], op["y"], op["z0"]
            w, h, rot = op["w"], op["h"], op["rot"]
            cz = z0 + h / 2.0
            depth = WALL_T + 0.02
            # reveal frame: four sides, standing slightly proud of the wall
            inner_w, inner_h = w, h
            frame = []
            frame.append(box(f"{key}_J{i}a", col, (0.09, depth, h + 0.18),
                             (-w / 2 - 0.045, 0, 0), "timber_dark",
                             chamfer=0.008))
            frame.append(box(f"{key}_J{i}b", col, (0.09, depth, h + 0.18),
                             (w / 2 + 0.045, 0, 0), "timber_dark",
                             chamfer=0.008))
            frame.append(box(f"{key}_J{i}c", col, (w + 0.18, depth, 0.09),
                             (0, 0, h / 2 + 0.045), "timber_dark",
                             chamfer=0.008))
            frame.append(box(f"{key}_Sill{i}", col, (w + 0.26, depth + 0.10, 0.08),
                             (0, -0.04, -h / 2 - 0.04), "stone_warm",
                             chamfer=0.01))
            grp = join_objects(frame, f"OPEN_{key}_{i}")
            grp.matrix_world = _mat(x, y, cz, rot)

            if op["kind"] == "door":
                swing_door(f"DOOR_{key}", col, w - 0.10, h - 0.06,
                           x - math.sin(rot) * 0.02, y + math.cos(rot) * 0.02,
                           z0 + 0.02, rot)
                # threshold stone
                box(f"DOOR_Threshold_{key}", col, (w + 0.30, 0.34, 0.10),
                    (x - math.sin(rot) * 0.10, y + math.cos(rot) * 0.10,
                     z0 - 0.03), "stone", rot_z=rot, chamfer=0.01)
            else:
                lattice(f"WIND_{key}_{i}", col, inner_w - 0.02, inner_h - 0.02,
                        x - math.sin(rot) * 0.035, y + math.cos(rot) * 0.035,
                        cz, rot, op["pattern"])


# ------------------------------------------------------- display wall table
# (id, floor, x, y, z_centre, rot_z, width, height, label)
# Every entry is a measured solid pier or a dedicated display surface; frames
# below only reference these, so u/v are always inside the wall rectangle.

WALLS = [
    ("f1-back", 1, -0.5025, -IY, Z_F1 + F1_H / 2, 0.0, 2.885, F1_H, "一层 · 后墙"),
    ("f1-left-mid", 1, -IX, 0.0, Z_F1 + F1_H / 2, -math.pi / 2, 1.75, F1_H, "一层 · 左墙中段"),
    ("f1-left-rear", 1, -IX, -2.9075, Z_F1 + F1_H / 2, -math.pi / 2, 1.365, F1_H, "一层 · 左墙后段"),
    ("f1-right-mid", 1, IX, 0.0, Z_F1 + F1_H / 2, math.pi / 2, 1.75, F1_H, "一层 · 右墙中段"),
    ("f1-right-front", 1, IX, 2.9075, Z_F1 + F1_H / 2, math.pi / 2, 1.365, F1_H, "一层 · 右墙前段"),
    ("f1-front-right", 1, 1.4725, IY, Z_F1 + F1_H / 2, math.pi, 0.945, F1_H, "一层 · 前墙右段"),
    ("f2-back", 2, 0.0, -IY, Z_F2 + F2_H / 2, 0.0, 3.89, F2_H, "二层 · 后墙"),
    ("f2-left-mid", 2, -IX, 0.0, Z_F2 + F2_H / 2, -math.pi / 2, 1.75, F2_H, "二层 · 左墙中段"),
    ("f2-left-rear", 2, -IX, -2.9075, Z_F2 + F2_H / 2, -math.pi / 2, 1.365, F2_H, "二层 · 左墙后段"),
    ("f2-left-front", 2, -IX, 2.9075, Z_F2 + F2_H / 2, -math.pi / 2, 1.365, F2_H, "二层 · 左墙前段"),
    ("f2-right-mid", 2, IX, 0.2125, Z_F2 + F2_H / 2, math.pi / 2, 1.325, F2_H, "二层 · 右墙中段"),
    ("f2-right-front", 2, IX, 2.9075, Z_F2 + F2_H / 2, math.pi / 2, 1.365, F2_H, "二层 · 右墙前段"),
]

# (id, wall_id, along, z, w, h, label)  along = local X on the wall plane
FRAMES = [
    ("FRAME_F1_001", "f1-back", -0.80, 1.75, 1.00, 0.80, "一层 · 后墙 · 左"),
    ("FRAME_F1_002", "f1-back", 0.45, 1.75, 1.00, 0.80, "一层 · 后墙 · 右"),
    ("FRAME_F1_003", "f1-left-mid", 0.0, 1.75, 0.86, 1.14, "一层 · 左墙 · 中"),
    ("FRAME_F1_004", "f1-left-rear", -0.11, 1.75, 0.86, 1.14, "一层 · 左墙 · 后"),
    ("FRAME_F1_005", "f1-right-mid", 0.0, 1.75, 0.86, 1.14, "一层 · 右墙 · 中"),
    ("FRAME_F1_006", "f1-right-front", 0.11, 1.75, 0.86, 1.14, "一层 · 右墙 · 前"),
    ("FRAME_F1_007", "f1-front-right", 0.0, 1.72, 0.84, 0.68, "一层 · 前墙 · 入口"),
    ("FRAME_F2_001", "f2-back", -1.32, 5.05, 0.82, 0.66, "二层 · 后墙 · 左"),
    ("FRAME_F2_002", "f2-back", 0.0, 5.05, 1.25, 0.92, "二层 · 后墙 · 中"),
    ("FRAME_F2_003", "f2-back", 1.32, 5.05, 0.82, 0.66, "二层 · 后墙 · 右"),
    ("FRAME_F2_004", "f2-left-mid", 0.0, 5.05, 0.85, 1.10, "二层 · 左墙 · 中"),
    ("FRAME_F2_005", "f2-left-rear", -0.11, 5.05, 0.85, 1.10, "二层 · 左墙 · 后"),
    ("FRAME_F2_006", "f2-left-front", 0.11, 5.05, 0.85, 1.10, "二层 · 左墙 · 前"),
    ("FRAME_F2_007", "f2-right-mid", -0.16, 5.05, 0.85, 1.10, "二层 · 右墙 · 中"),
    ("FRAME_F2_008", "f2-right-front", 0.11, 5.05, 0.85, 1.10, "二层 · 右墙 · 前"),
]


def build_gallery_walls(col) -> list:
    """Emit GALWALL_* empties carrying the real wall rectangles."""
    made = []
    for wid, floor, x, y, z, rot, w, h, label in WALLS:
        obj = empty(f"GALWALL_{wid}", col, (x, y, z), rot, size=0.2,
                    floor=floor, width=w, height=h, label=label,
                    gallery_layer="wall")
        made.append(obj)
    report(f"display walls: {len(made)}")
    return made


def build_frame_anchors(col) -> list:
    wall_by_id = {w[0]: w for w in WALLS}
    names = []
    for fid, wid, along, z, fw, fh, label in FRAMES:
        _, floor, cx, cy, cz, rot, w, h, _ = wall_by_id[wid]
        u = along / w + 0.5
        v = (z - (cz - h / 2.0)) / h
        px = cx + along * math.cos(rot)
        py = cy + along * math.sin(rot)
        obj = empty(fid, col, (px, py, z), rot, size=0.16,
                    floor=floor, wall_id=wid, u=round(u, 4), v=round(v, 4),
                    frame_size=[fw, fh], label=label, gallery_layer="frame")
        names.append(obj.name)
    report(f"frame anchors: {len(names)} (f1=7 f2=8)")
    return names


# ---------------------------------------------------------------- railings

def _balustrade(name, col, p0, p1, height=1.0, mat_key="timber_dark"):
    """Top rail, bottom rail, panel and newel posts along a straight run."""
    a, b = Vector(p0), Vector(p1)
    d = b - a
    length = d.length
    if length < 0.1:
        return None
    parts = []
    dirn = d.normalized()
    parts.append(bar(f"{name}_Top", col, (a.x, a.y, a.z + height),
                     (b.x, b.y, b.z + height), 0.075, 0.075, mat_key))
    parts.append(bar(f"{name}_Mid", col, (a.x, a.y, a.z + height * 0.52),
                     (b.x, b.y, b.z + height * 0.52), 0.05, 0.05, mat_key))
    panels = max(1, int(length / 0.55))
    for i in range(panels):
        t0 = i / panels
        t1 = (i + 1) / panels
        pa = a.lerp(b, t0)
        pb = a.lerp(b, t1)
        parts.append(bar(f"{name}_P{i}", col,
                         (pa.x, pa.y, pa.z + height * 0.52),
                         (pb.x, pb.y, pb.z + height * 0.52),
                         0.035, height * 0.42, mat_key))
    posts = max(1, round(length / 1.1))
    for i in range(posts + 1):
        p = a.lerp(b, i / posts)
        parts.append(box(f"{name}_Post{i}", col, (0.07, 0.07, height + 0.06),
                         (p.x, p.y, p.z + (height + 0.06) / 2.0), mat_key))
        if i in (0, posts):
            parts.append(cyl(f"{name}_Cap{i}", col, 0.055, 0.06,
                             (p.x, p.y, p.z + height + 0.09), "gold",
                             segments=10))
    return join_objects(parts, name)


def build_railings(col):
    parts = []
    z = Z_F2
    y0, y1 = STAIR_BAND_A[1], STAIR_BAND_B[1]
    parts.append(_balustrade("RAIL_Void_A", col, (STAIR_XM, y1, z),
                             (STAIR_XM, y0, z), 1.0))
    parts.append(_balustrade("RAIL_Void_B", col, (STAIR_X0, y0, z),
                             (STAIR_X0, y1, z), 1.0))
    parts.append(_balustrade("RAIL_Void_C", col, (STAIR_X0, y0, z),
                             (IX - 0.06, y0, z), 1.0))
    # handrail down the first flight is already in build_core (STAIR_Main)
    obj = join_objects(parts, "RAIL_Gallery")
    report("gallery railings built")
    return obj


# ------------------------------------------------------------------- ceiling

def _octagon_ring(name, col, r_out, r_in, z, thick, mat_key):
    parts = []
    seg = 2.0 * r_out * math.tan(math.pi / 8.0)
    for i in range(8):
        a = i * math.pi / 4.0
        cx = math.cos(a + math.pi / 8.0) * (r_out + r_in) / 2.0
        cy = math.sin(a + math.pi / 8.0) * (r_out + r_in) / 2.0
        parts.append(box(f"{name}_{i}", col, (r_out - r_in, seg, thick),
                         (cx, cy, z), mat_key, rot_z=a + math.pi / 2.0))
    return parts


def build_ceiling(col):
    """Closed plaster ceiling, three-tier beams, octagonal coffer, small pendant."""
    parts = []
    w, d = BUILD_X - 0.26, BUILD_DEPTH - 0.26
    # closed deck (this is what stops the sky showing between beams)
    parts.append(box("CEIL_Deck", col, (w, d, 0.06), (0, 0, Z_TOP - 0.06),
                     "wall_shadow"))
    parts.append(box("CEIL_Trim", col, (w + 0.02, d + 0.02, 0.05),
                     (0, 0, Z_TOP - 0.015), "timber_dark"))

    # rafters (highest), secondary beams, primary beams (lowest)
    n = int(w / 0.46)
    for i in range(n + 1):
        x = -w / 2 + i * w / n
        parts.append(box(f"CEIL_Rafter{i}", col, (0.06, d - 0.1, 0.10),
                         (x, 0, Z_TOP - 0.15), "timber_warm"))
    for j, y in enumerate((-2.4, -0.8, 0.8, 2.4)):
        parts.append(box(f"BEAM_Main{j}", col, (w - 0.1, 0.24, 0.30),
                         (0, y, Z_TOP - 0.32), "timber_dark", chamfer=0.01))
    for j, x in enumerate((-2.7, 0.0, 2.7)):
        parts.append(box(f"BEAM_Sub{j}", col, (0.17, d - 0.1, 0.20),
                         (x, 0, Z_TOP - 0.24), "timber", chamfer=0.008))

    # coffer: three stepped octagons hanging below the deck so they are visible
    # from the room. (Recessing them into the roof would hide them behind the
    # closed deck, which is how the earlier flat "orange disc" ceiling read.)
    # The brief asks for a 1.0-1.3 m coffer. The octagon boxes are placed on an
    # apothem, so their tangential corners overshoot the nominal radius; measured
    # across X the old stack came out at 1.975 m. COFFER_S brings the measured
    # width back to ~1.25 m without touching the stepped profile.
    COFFER_S = 0.632
    parts.append(box("CEIL_CofferBase", col, (1.62 * COFFER_S, 1.62 * COFFER_S, 0.10),
                     (0, 0, Z_TOP - 0.14), "timber_dark"))
    for k, (ro, ri, zz, th) in enumerate((
            (0.80, 0.62, Z_TOP - 0.22, 0.09),
            (0.58, 0.42, Z_TOP - 0.32, 0.09),
            (0.40, 0.26, Z_TOP - 0.42, 0.09))):
        parts += _octagon_ring(f"CEIL_Coffer{k}", col,
                               ro * COFFER_S, ri * COFFER_S, zz, th, "timber")
    parts.append(box("CEIL_CofferTop", col, (0.36 * COFFER_S, 0.36 * COFFER_S, 0.06),
                     (0, 0, Z_TOP - 0.49), "timber_dark"))
    # flower boss, hanging under the innermost plate
    parts.append(cyl("CEIL_Boss", col, 0.11 * COFFER_S, 0.06, (0, 0, Z_TOP - 0.55),
                     "gold", segments=16))
    for i in range(8):
        a = i * math.pi / 4.0
        parts.append(cyl(f"CEIL_Petal{i}", col, 0.055 * COFFER_S, 0.05,
                         (math.cos(a) * 0.16 * COFFER_S,
                          math.sin(a) * 0.16 * COFFER_S, Z_TOP - 0.53),
                         "gold_light", segments=8))

    # pendant lamp: deliberately small (0.28 m across), warm, above head height
    parts.append(cyl("LAMP_PendantRod", col, 0.014, 0.22, (0, 0, Z_TOP - 0.68),
                     "ink", segments=6))
    parts.append(cyl("LAMP_PendantCap", col, 0.10, 0.05, (0, 0, Z_TOP - 0.81),
                     "gold", segments=12))
    parts.append(cyl("LAMP_Pendant", col, 0.145, 0.20, (0, 0, Z_TOP - 0.94),
                     "red", segments=14))
    parts.append(cyl("LAMP_PendantGlow", col, 0.115, 0.03, (0, 0, Z_TOP - 1.04),
                     "lamp_glow", segments=14))

    # track lights along the two main beams
    for i, y in enumerate((-2.4, 2.4)):
        parts.append(box(f"LAMP_Track{i}", col, (1.9, 0.07, 0.05),
                         (0, y, Z_TOP - 0.50), "ink"))
        for dx in (-0.6, 0.0, 0.6):
            parts.append(cyl(f"LAMP_Can{i}{dx}", col, 0.055, 0.13,
                             (dx, y, Z_TOP - 0.58), "lamp_glow", segments=10))
    obj = join_objects(parts, "BEAM_Ceiling")
    report("ceiling + coffer built")
    return obj


# ------------------------------------------------------------------- lanterns

def build_lanterns(col, roof_col=None):
    """Gate lanterns flanking the door; the pair under the ring eave belongs to
    the roof collection so it disappears together with the roof in interior
    presets (otherwise they would float in mid-air)."""
    parts = []
    spots = [
        (-1.62, IY + 0.30, 2.28, 0.175),
        (1.62, IY + 0.30, 2.28, 0.175),
    ]
    for i, (x, y, z, r) in enumerate(spots):
        parts.append(cyl(f"LANTERN_Rod{i}", col, 0.012, 0.22, (x, y, z + 0.11),
                         "ink", segments=6))
        parts.append(cyl(f"LANTERN_Cap{i}", col, r * 0.62, 0.05, (x, y, z),
                         "gold", segments=12))
        parts.append(cyl(f"LANTERN_Body{i}", col, r, r * 1.05, (x, y, z - r * 0.6),
                         "red", segments=14))
        parts.append(cyl(f"LANTERN_Top{i}", col, r * 0.55, 0.05, (x, y, z - r * 1.14),
                         "gold", segments=10))
        parts.append(cyl(f"LANTERN_Tassel{i}", col, 0.018, 0.24,
                         (x, y, z - r * 1.30), "gold", segments=6))
    gate = join_objects(parts, "LANTERN_Gate")

    eave = None
    if roof_col is not None:
        parts = []
        spots = [(-3.55, IY + 0.42, Z_F2 / 1.0 + 0.02, 0.145),
                 (3.55, IY + 0.42, Z_F2 + 0.02, 0.145)]
        for i, (x, y, z, r) in enumerate(spots):
            parts.append(cyl(f"LANTERN_ERod{i}", roof_col, 0.010, 0.30,
                             (x, y, z + 0.15), "ink", segments=6))
            parts.append(cyl(f"LANTERN_ECap{i}", roof_col, r * 0.62, 0.045,
                             (x, y, z), "gold", segments=12))
            parts.append(cyl(f"LANTERN_EBody{i}", roof_col, r, r * 1.0,
                             (x, y, z - r * 0.62), "red", segments=14))
            parts.append(cyl(f"LANTERN_ETop{i}", roof_col, r * 0.55, 0.045,
                             (x, y, z - r * 1.16), "gold", segments=10))
            parts.append(cyl(f"LANTERN_ETassel{i}", roof_col, 0.016, 0.20,
                             (x, y, z - r * 1.32), "gold", segments=6))
        eave = join_objects(parts, "LANTERN_Eave")
    return gate, eave


# --------------------------------------------------------------------- cases

def _vase(name, col, x, y, z):
    """Porcelain meiping: stacked rings, blue rim - reads as a real object."""
    parts = []
    prof = [(0.10, 0.02), (0.15, 0.10), (0.17, 0.22), (0.14, 0.36),
            (0.09, 0.46), (0.075, 0.56), (0.10, 0.60), (0.105, 0.63)]
    for i, (r, h) in enumerate(prof):
        parts.append(cyl(f"{name}_B{i}", col, r, 0.075, (x, y, z + h),
                         "porcelain", segments=18))
    parts.append(cyl(f"{name}_Band", col, 0.152, 0.035, (x, y, z + 0.22),
                     "porcelain_bl", segments=18))
    parts.append(cyl(f"{name}_Mouth", col, 0.105, 0.02, (x, y, z + 0.655),
                     "porcelain_bl", segments=18))
    return join_objects(parts, name)


def build_cases(col):
    """Central plinth, two side vitrines, reception desk, bench."""
    parts = []
    # central plinth 1.2 x 1.2 x 0.9
    parts.append(box("CASE_Central", col, (1.20, 1.20, 0.78), (0, 0, Z_F1 + 0.39),
                     "timber_dark", chamfer=0.012))
    parts.append(box("CASE_CentralTop", col, (1.26, 1.26, 0.12), (0, 0, Z_F1 + 0.84),
                     "stone_warm", chamfer=0.012))
    parts.append(box("CASE_CentralTrim", col, (1.30, 1.30, 0.025), (0, 0, Z_F1 + 0.775),
                     "gold_light"))
    _vase("CASE_Vase", col, 0, 0, Z_F1 + 0.90)
    parts.append(box("CASE_CentralLabel", col, (0.34, 0.02, 0.12), (0, 0.62, Z_F1 + 0.55),
                     "paper"))

    # left vitrine 1.8 x 0.75 x 0.9 along Y
    parts.append(box("CASE_Left", col, (0.75, 1.80, 0.86), (-3.42, 1.55, Z_F1 + 0.43),
                     "timber_dark", chamfer=0.01))
    parts.append(box("CASE_LeftTop", col, (0.80, 1.86, 0.09), (-3.42, 1.55, Z_F1 + 0.905),
                     "stone_warm"))
    parts.append(box("CASE_LeftGlass", col, (0.62, 1.62, 0.34), (-3.42, 1.55, Z_F1 + 1.10),
                     "porcelain"))
    for k, y in enumerate((1.05, 1.55, 2.05)):
        parts.append(box(f"CASE_LeftShelf{k}", col, (0.64, 0.02, 0.02),
                         (-3.42, y, Z_F1 + 0.94), "gold_light"))

    # right vitrine 1.5 x 0.75 x 0.9
    parts.append(box("CASE_Right", col, (0.75, 1.50, 0.86), (3.42, 1.85, Z_F1 + 0.43),
                     "timber_dark", chamfer=0.01))
    parts.append(box("CASE_RightTop", col, (0.80, 1.56, 0.09), (3.42, 1.85, Z_F1 + 0.905),
                     "stone_warm"))
    parts.append(box("CASE_RightGlass", col, (0.62, 1.32, 0.34), (3.42, 1.85, Z_F1 + 1.10),
                     "porcelain"))

    # reception desk near the entrance, left of the door
    parts.append(box("CASE_Desk", col, (1.70, 0.55, 0.98), (-2.45, 2.75, Z_F1 + 0.49),
                     "timber_warm", chamfer=0.012))
    parts.append(box("CASE_DeskTop", col, (1.82, 0.63, 0.07), (-2.45, 2.75, Z_F1 + 1.015),
                     "stone_warm", chamfer=0.01))
    parts.append(box("CASE_DeskSign", col, (0.52, 0.02, 0.20), (-2.45, 3.02, Z_F1 + 0.66),
                     "paper"))

    # bench on the upper floor
    parts.append(box("CASE_Bench", col, (1.30, 0.38, 0.08), (-2.2, -0.1, Z_F2 + 0.44),
                     "timber_warm", chamfer=0.01))
    for sx in (-1, 1):
        parts.append(box(f"CASE_BenchLeg{sx}", col, (0.09, 0.30, 0.42),
                         (-2.2 + sx * 0.55, -0.1, Z_F2 + 0.21), "timber_dark"))
    obj = join_objects(parts, "PROP_Cases")
    report("display cases built")
    return obj


def build_plants(col):
    """Interior potted plants: two palm pots and one low planter."""
    parts = []
    for i, (x, y, r) in enumerate(((-3.35, -2.95, 0.22), (3.45, -3.0, 0.22))):
        parts.append(cyl(f"PROP_Pot{i}", col, r, 0.40, (x, y, Z_F1 + 0.20),
                         "timber_dark", segments=12))
        parts.append(cyl(f"PROP_PotSoil{i}", col, r * 0.9, 0.05, (x, y, Z_F1 + 0.41),
                         "ink", segments=12))
        for k in range(6):
            a = k * math.pi / 3.0
            parts.append(bar(f"PROP_Leaf{i}{k}", col,
                             (x, y, Z_F1 + 0.44),
                             (x + math.cos(a) * 0.42, y + math.sin(a) * 0.42,
                              Z_F1 + 0.92 + (k % 2) * 0.16),
                             0.10, 0.02, "plant"))
    obj = join_objects(parts, "PROP_InteriorPlants")
    return obj


def build(col, anchor_col, roof_col=None):
    """Entry point used by build_all."""
    build_openings(col)
    build_gallery_walls(anchor_col)
    build_railings(col)
    build_ceiling(col)
    build_lanterns(col, roof_col)
    build_cases(col)
    build_plants(col)
    names = build_frame_anchors(anchor_col)
    report("interior built")
    return names
