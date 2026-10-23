"""Core architecture build: plinth, timber frame, walls, floors, stairs, roofs.

Run through build_all.py. Every function appends to its own collection so the
GLB keeps a navigable node hierarchy.

Geometry rules that matter for the web runtime:
  * the eave is a real line at EAVE_Z, not a bowl: only the four corners lift;
  * every roof slope is a ruled surface from eave line to ridge, so the four
    slopes share their hip edges exactly (no cracks, no light leaks);
  * the soffit is a closed second surface 0.22 m under the tiles;
  * the stair is a solid L-shaped switchback whose top step lands exactly on
    the F2 slab edge (see STAIR_* in gal_common).

NOTE: keep this file ASCII-only. Windows PowerShell text round-trips corrupt
UTF-8 Chinese comments, which has already cost one rebuild.
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
    BASE_EDGE_H, BASE_EDGE_W, BASE_SIZE, BASE_THICKNESS, BUILD_DEPTH, BUILD_X,
    COL_R, EAVE_LIFT, EAVE_Z, F1_H, F2_H, IX, IY, OPENINGS, PALETTE,
    PLINTH_DARK_H, PLINTH_FRIEZE_H, PLINTH_TOP_H, RIDGE_Z, ROOF_LOWER_OVERHANG,
    ROOF_LOWER_RISE, ROOF_OVERHANG, ROOF_RIDGE_HALF, ROOF_RISE, ROOF_SLOPE_POW,
    SLAB_T, STAIR_BAND_A, STAIR_BAND_B, STAIR_LANDING_Z, STAIR_RISE, STAIR_TREAD,
    STAIR_W, STAIR_X0, STAIR_X1, STAIR_XM, WALL_T, Z_F1, Z_F2, Z_TOP, bevel,
    bm_to_object, box, cyl, empty, get_collection, join_objects, material,
    opening_centres, piers, prism, report, smooth_curve,
)

HX = BUILD_X / 2.0
HY = BUILD_DEPTH / 2.0
BAY_X = [-HX, -HX / 3.0, HX / 3.0, HX]
SIDE_Y = [-HY, 0.0, HY]


# ------------------------------------------------------------------- helpers

def bar_between(name: str, col, p0, p1, width: float, height: float,
                mat_key: str = "timber", chamfer: float = 0.0):
    """A rectangular timber between two points (used for sloped rails/rafters)."""
    a, b = Vector(p0), Vector(p1)
    d = b - a
    length = d.length
    if length < 1e-5:
        return None
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((length, width, height)), verts=bm.verts)
    rot = d.normalized().to_track_quat("X", "Z").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
    bmesh.ops.translate(bm, vec=(a + b) * 0.5, verts=bm.verts)
    obj = bm_to_object(bm, name, col, mat_key)
    if chamfer:
        bevel(obj, chamfer)
    return obj


def _lerp(a, b, t):
    return a + (b - a) * t


# ------------------------------------------------------------------- plinth

def _meander_unit(col, prefix, cx, cy, z, rot, scale=1.0):
    """One 闂傚倷鐒﹂幃鍫曞磿閹惰棄纾婚柣鏃€鍝?module: three nested square spirals, built from thin bars."""
    parts = []
    u = 0.46 * scale          # unit width
    t = 0.045 * scale         # bar thickness
    d = 0.03                  # relief depth
    # base plate of the module
    parts.append(box(f"{prefix}_P", col, (u, d, u * 0.78), (cx, cy, z),
                     "stone_dark", rot_z=rot))
    # spiral strokes, authored in local (a, b) then rotated into place
    strokes = [
        (0.0, 0.0, u * 0.72, t),          # bottom bar
        (u * 0.31, t * 1.6, t, u * 0.46),
        (-u * 0.05, u * 0.20, u * 0.42, t),
        (u * 0.14, u * 0.29, t, u * 0.20),
    ]
    ca, sa = math.cos(rot), math.sin(rot)
    for k, (a, b, w, h) in enumerate(strokes):
        wx = cx + a * ca - b * sa * 0.0
        # local b is vertical here (z), so no rotation needed for b
        parts.append(box(f"{prefix}_S{k}", col, (w, d * 0.62, h),
                         (cx + a * ca, cy + a * sa * 0.0, z + b), "stone",
                         rot_z=rot))
    return parts


def build_base(col) -> dict:
    """Three-layer square plinth: dark foot, carved frieze, pale deck."""
    parts = []
    s = BASE_SIZE
    z_dark = -BASE_THICKNESS + PLINTH_DARK_H / 2.0
    z_frieze = -BASE_THICKNESS + PLINTH_DARK_H + PLINTH_FRIEZE_H / 2.0
    z_top = -PLINTH_TOP_H / 2.0

    parts.append(box("BASE_Main", col, (s, s, PLINTH_TOP_H), (0, 0, z_top),
                     "stone_warm", chamfer=0.018))
    parts.append(box("BASE_Frieze", col, (s - 0.10, s - 0.10, PLINTH_FRIEZE_H),
                     (0, 0, z_frieze), "stone", chamfer=0.012))
    parts.append(box("BASE_Foot", col, (s - 0.18, s - 0.18, PLINTH_DARK_H),
                     (0, 0, z_dark), "stone_dark", chamfer=0.012))
    # a darker shadow reveal between the layers reads as a moulding
    parts.append(box("BASE_RevealA", col, (s - 0.02, s - 0.02, 0.022),
                     (0, 0, -PLINTH_TOP_H - 0.011), "stone_dark"))
    parts.append(box("BASE_RevealB", col, (s - 0.12, s - 0.12, 0.022),
                     (0, 0, -BASE_THICKNESS + PLINTH_DARK_H + 0.011), "stone_dark"))

    # raised border band on the deck (a real 25 mm step, not a decal)
    b = BASE_EDGE_W
    for i, (sx, sy, cx, cy) in enumerate([
        (s, b, 0, s / 2 - b / 2),
        (s, b, 0, -s / 2 + b / 2),
        (b, s - 2 * b, s / 2 - b / 2, 0),
        (b, s - 2 * b, -s / 2 + b / 2, 0),
    ]):
        parts.append(box(f"BASE_Edge{i}", col, (sx, sy, BASE_EDGE_H * 2),
                         (cx, cy, BASE_EDGE_H / 2), "stone", chamfer=0.008))

    # continuous 闂傚倷鐒﹂幃鍫曞磿閹惰棄纾婚柣鏃€鍝?frieze, modular units marching along every face
    half = s / 2.0 - 0.105
    for side, (nx, ny) in enumerate(((0, 1), (0, -1), (1, 0), (-1, 0))):
        n = 26
        for k in range(n):
            t = (k + 0.5) / n - 0.5
            off = t * (s - 1.15)
            if ny:
                cx, cy = off, ny * half
                rot = 0.0
            else:
                cx, cy = nx * half, off
                rot = math.pi / 2.0
            parts += _meander_unit(col, f"BASE_Meander{side}_{k}", cx, cy,
                                   z_frieze, rot)
        # corner ridge ornament
        for sx in (-1, 1):
            if ny:
                parts.append(box(f"BASE_Corner{side}{sx}", col,
                                 (0.22, 0.16, 0.36),
                                 (sx * (s / 2 - 0.24), ny * (s / 2 - 0.10),
                                  z_frieze), "stone_dark", chamfer=0.02))

    base = join_objects(parts, "BASE_Main")
    base.name = "BASE_Main"
    report(f"base built: {len(base.data.vertices)} verts / {len(base.data.polygons)} faces")
    return {"obj": base}


# -------------------------------------------------------------- timber frame

def _bracket_set(col, name, x, y, z, scale=1.0):
    """Simplified dougong: seat block + two tiers of arms."""
    parts = []
    parts.append(box(f"{name}_Seat", col, (0.34, 0.34, 0.10), (x, y, z + 0.05), "timber_dark"))
    parts.append(box(f"{name}_ArmX", col, (0.86, 0.13, 0.11), (x, y, z + 0.16), "timber"))
    parts.append(box(f"{name}_ArmY", col, (0.13, 0.86, 0.11), (x, y, z + 0.16), "timber"))
    for dx in (-0.32, 0.32):
        parts.append(box(f"{name}_BkX{dx}", col, (0.13, 0.13, 0.13),
                         (x + dx, y, z + 0.26), "timber_warm"))
    for dy in (-0.32, 0.32):
        parts.append(box(f"{name}_BkY{dy}", col, (0.13, 0.13, 0.13),
                         (x, y + dy, z + 0.26), "timber_warm"))
    parts.append(box(f"{name}_Plate", col, (0.62, 0.62, 0.07), (x, y, z + 0.34), "timber_dark"))
    return parts


def build_columns(col) -> bpy.types.Object:
    """Two rings of free-standing columns with stone bases and dougong."""
    parts = []
    spots = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            spots.append((sx * HX, sy * HY))
    for x in BAY_X[1:-1]:
        spots.append((x, HY - 0.05))
        spots.append((x, -HY + 0.05))
    for y in SIDE_Y[1:-1]:
        spots.append((HX - 0.05, y))
        spots.append((-HX + 0.05, y))

    for storey, (z0, z1) in enumerate(((Z_F1, Z_F1 + F1_H), (Z_F2, Z_TOP))):
        for i, (x, y) in enumerate(spots):
            h = z1 - z0
            name = f"COL_{storey + 1}_{i:02d}"
            parts.append(box(f"{name}_Base", col, (0.44, 0.44, 0.14),
                             (x, y, z0 + 0.07), "stone", chamfer=0.014))
            parts.append(cyl(name, col, COL_R, h - 0.16, (x, y, z0 + 0.14 + (h - 0.16) / 2.0),
                             "timber", segments=16))
            # subtle entasis collar
            parts.append(cyl(f"{name}_Collar", col, COL_R * 1.12, 0.05,
                             (x, y, z0 + h * 0.55), "timber_dark", segments=16))
            parts += _bracket_set(col, f"{name}_DG", x, y, z1 - 0.44)

    obj = join_objects(parts, "BUILDING_Columns")
    report(f"columns: {len(spots) * 2} posts")
    return obj


def build_storey_bands(col) -> bpy.types.Object:
    """Belt beams (e-fang) at each storey head plus the F1 dado line."""
    parts = []
    for z, h, depth in ((Z_F1 + F1_H - 0.10, 0.26, 0.20),
                        (Z_TOP - 0.12, 0.28, 0.20),
                        (Z_F1 + 0.02, 0.10, 0.18)):
        for side in ("front", "back", "left", "right"):
            if side in ("front", "back"):
                parts.append(box(f"BAND_{z:.1f}_{side}", col,
                                 (BUILD_X + depth, depth, h),
                                 (0, (HY - WALL_T / 2.0) * (1 if side == "front" else -1),
                                  z + h / 2.0), "timber_dark", chamfer=0.01))
            else:
                parts.append(box(f"BAND_{z:.1f}_{side}", col,
                                 (depth, BUILD_DEPTH + depth, h),
                                 ((HX - WALL_T / 2.0) * (1 if side == "right" else -1),
                                  0, z + h / 2.0), "timber_dark", chamfer=0.01))
    obj = join_objects(parts, "BUILDING_Bands")
    return obj


def _wall_pier(col, name, a, b, z0, z1, wall_x, wall_y, rot, mat="wall"):
    """One solid wall segment between two stations on a facade."""
    length = b - a
    if length <= 0.004:
        return None
    mid = (a + b) / 2.0
    h = z1 - z0
    ca, sa = math.cos(rot), math.sin(rot)
    # local +X runs along the wall, +Y is the wall normal (outwards)
    cx = wall_x + mid * ca
    cy = wall_y + mid * sa
    return box(name, col, (length, WALL_T, h), (cx, cy, z0 + h / 2.0), mat,
               rot_z=rot, chamfer=0.006)


def build_walls(col) -> bpy.types.Object:
    """All four facades: piers, sills, lintels, dado and relief panels."""
    parts = []
    storeys = (
        (Z_F1, F1_H, "f1"),
        (Z_F2, F2_H, "f2"),
    )
    for z_base, height, tag in storeys:
        for side in ("front", "back", "left", "right"):
            key = f"{tag}_{side}"
            length = BUILD_X if side in ("front", "back") else BUILD_DEPTH
            holes = [(o[0], o[1]) for o in OPENINGS[key]]
            (wx, wy, _), rot = G.wall_plane(side, z_base)
            ca, sa = math.cos(rot), math.sin(rot)
            z1 = z_base + height

            def place(name, a, b, zz0, zz1, mat="wall"):
                mid = (a + b) / 2.0
                parts.append(box(name, col, (b - a, WALL_T, zz1 - zz0),
                                 (wx + mid * ca, wy + mid * sa, (zz0 + zz1) / 2.0),
                                 mat, rot_z=rot, chamfer=0.005))

            for i, (a, b) in enumerate(piers(length, holes)):
                place(f"WALL_{key}_P{i}", a, b, z_base, z1)
                # relief panel on wide piers only (kept under ~15% of the area)
                if b - a > 1.25:
                    pw = min(0.62, (b - a) * 0.5)
                    pc = (a + b) / 2.0
                    pz = z_base + height * 0.42
                    for dx in (-pw / 2.0, pw / 2.0):
                        parts.append(box(f"WALL_{key}_R{i}v{dx:.2f}", col,
                                         (0.05, 0.022, height * 0.44),
                                         (wx + (pc + dx) * ca, wy + (pc + dx) * sa,
                                          z_base + height * 0.5), "wall_shadow",
                                         rot_z=rot))
                    for dz in (-height * 0.22, height * 0.22):
                        parts.append(box(f"WALL_{key}_R{i}h{dz:.2f}", col,
                                         (pw, 0.022, 0.05),
                                         (wx + pc * ca, wy + pc * sa, pz + dz),
                                         "wall_shadow", rot_z=rot))
                # dado
                parts.append(box(f"WALL_{key}_Dado{i}", col,
                                 (b - a, WALL_T + 0.02, 0.18),
                                 (wx + (a + b) / 2.0 * ca, wy + (a + b) / 2.0 * sa,
                                  z_base + 0.09), "timber_dark", rot_z=rot))

            for u, w, z0, h, kind, *_ in OPENINGS[key]:
                a, b = u - w / 2.0, u + w / 2.0
                if z0 > 0.02:
                    place(f"WALL_{key}_Sill{a:.2f}", a, b, z_base, z_base + z0)
                top = z_base + z0 + h
                if top < z1 - 0.01:
                    place(f"WALL_{key}_Lintel{a:.2f}", a, b, top, z1)
    obj = join_objects(parts, "BUILDING_Walls")
    report(f"walls: {len(obj.data.polygons)} faces")
    return obj


# ------------------------------------------------------------------- floors

def build_floors(col) -> list:
    """Stone podium, timber ground floor, and the F2 slab around the stair void."""
    parts = []
    # podium: 0.25 m stone deck under the whole hall, edges exposed all round
    parts.append(box("FLOOR_Podium", col, (BUILD_X + 0.9, BUILD_DEPTH + 0.9, 0.25),
                     (0, 0, 0.125), "stone_warm", chamfer=0.015))
    parts.append(box("FLOOR_01", col, (BUILD_X - 0.3, BUILD_DEPTH - 0.3, 0.04),
                     (0, 0, Z_F1 - 0.02), "wood_light"))

    # F2 slab: three rectangles that leave an L-shaped stair void
    zc = Z_F2 - SLAB_T / 2.0
    def slab(name, x0, x1, y0, y1):
        if x1 - x0 < 0.02 or y1 - y0 < 0.02:
            return
        parts.append(box(name, col, (x1 - x0, y1 - y0, SLAB_T),
                         ((x0 + x1) / 2.0, (y0 + y1) / 2.0, zc), "wall_shadow",
                         chamfer=0.008))

    slab("FLOOR_02_A", -IX, STAIR_XM, -IY, STAIR_BAND_A[1])
    slab("FLOOR_02_B", -IX, STAIR_XM, STAIR_BAND_A[1], STAIR_BAND_B[1])
    slab("FLOOR_02_C", STAIR_X1, IX, STAIR_BAND_A[1], STAIR_BAND_B[1])
    slab("FLOOR_02_D", -IX, IX, STAIR_BAND_B[1], IY)

    parts.append(box("FLOOR_02_Finish", col,
                     (BUILD_X - 0.3, BUILD_DEPTH - 0.3 - (STAIR_BAND_B[1] + IY) / 2.0, 0.035),
                     (0, (IY + STAIR_BAND_B[1]) / 2.0, Z_F2 + 0.017), "timber_warm"))
    parts.append(box("FLOOR_02_FinishA", col,
                     (STAIR_XM + IX, STAIR_BAND_B[1] + IY, 0.035),
                     ((-IX + STAIR_XM) / 2.0, (IY + STAIR_BAND_B[1]) / 2.0, Z_F2 + 0.017),
                     "timber_warm"))
    parts.append(box("FLOOR_02_FinishB", col,
                     (IX - STAIR_X1, STAIR_BAND_B[1] + IY, 0.035),
                     ((IX + STAIR_X1) / 2.0, (IY + STAIR_BAND_B[1]) / 2.0, Z_F2 + 0.017),
                     "timber_warm"))

    obj = join_objects(parts, "FLOOR_01")
    report("floors built")
    return [obj]


# ------------------------------------------------------------------- stairs

def build_stairs(col):
    """Solid L-shaped switchback: 8 treads, quarter landing, 8 treads."""
    parts = []
    yA0, yA1 = STAIR_BAND_A
    yB0, yB1 = STAIR_BAND_B

    # flight 1: along -X inside band A
    for i in range(8):
        x1 = STAIR_X1 - i * STAIR_TREAD
        x0 = x1 - STAIR_TREAD
        z = Z_F1 + (i + 1) * STAIR_RISE
        parts.append(box(f"STAIR_F1_{i}", col,
                         (STAIR_TREAD, yA1 - yA0, z - Z_F1),
                         ((x0 + x1) / 2.0, (yA0 + yA1) / 2.0, (Z_F1 + z) / 2.0),
                         "timber_warm"))
        parts.append(box(f"STAIR_F1N_{i}", col,
                         (STAIR_TREAD + 0.02, yA1 - yA0 + 0.02, 0.035),
                         ((x0 + x1) / 2.0, (yA0 + yA1) / 2.0, z - 0.017), "timber"))

    # quarter landing
    parts.append(box("STAIR_Landing", col,
                     (STAIR_X0 - STAIR_XM, yA1 - yA0, STAIR_LANDING_Z - Z_F1),
                     ((STAIR_XM + STAIR_X0) / 2.0, (yA0 + yA1) / 2.0,
                      (Z_F1 + STAIR_LANDING_Z) / 2.0), "timber_warm"))
    parts.append(box("STAIR_LandingTop", col,
                     (STAIR_X0 - STAIR_XM, yA1 - yA0, 0.035),
                     ((STAIR_XM + STAIR_X0) / 2.0, (yA0 + yA1) / 2.0,
                      STAIR_LANDING_Z - 0.017), "timber"))

    # flight 2: along +Y inside band B
    for j in range(8):
        y0 = yB0 + j * STAIR_TREAD
        y1 = y0 + STAIR_TREAD
        z = STAIR_LANDING_Z + (j + 1) * STAIR_RISE
        parts.append(box(f"STAIR_F2_{j}", col,
                         (STAIR_X0 - STAIR_XM, STAIR_TREAD, z - Z_F1),
                         ((STAIR_XM + STAIR_X0) / 2.0, (y0 + y1) / 2.0,
                          (Z_F1 + z) / 2.0), "timber_warm"))
        parts.append(box(f"STAIR_F2N_{j}", col,
                         (STAIR_X0 - STAIR_XM + 0.02, STAIR_TREAD + 0.02, 0.035),
                         ((STAIR_XM + STAIR_X0) / 2.0, (y0 + y1) / 2.0, z - 0.017),
                         "timber"))

    # closed stringer under the open side of flight 1
    parts.append(bar_between("STAIR_Stringer1", col,
                             (STAIR_X1, yA1 - 0.03, Z_F1 + 0.12),
                             (STAIR_X0, yA1 - 0.03, STAIR_LANDING_Z + 0.12),
                             0.07, 0.30, "timber_dark"))
    parts.append(bar_between("STAIR_Stringer2", col,
                             (STAIR_XM + 0.03, yB0, STAIR_LANDING_Z + 0.12),
                             (STAIR_XM + 0.03, yB1, Z_F2 - 0.10),
                             0.07, 0.30, "timber_dark"))

    # handrails: 0.95 above the nosing line
    hr = 0.95
    parts.append(bar_between("RAIL_Stair1", col,
                             (STAIR_X1, yA1 - 0.04, Z_F1 + STAIR_RISE + hr),
                             (STAIR_X0, yA1 - 0.04, STAIR_LANDING_Z + hr),
                             0.055, 0.075, "timber_dark", chamfer=0.008))
    parts.append(bar_between("RAIL_Stair2", col,
                             (STAIR_XM + 0.04, yB0, STAIR_LANDING_Z + hr),
                             (STAIR_XM + 0.04, yB1, Z_F2 + hr - 0.10),
                             0.055, 0.075, "timber_dark", chamfer=0.008))
    for i in range(0, 8, 2):
        x = STAIR_X1 - (i + 0.5) * STAIR_TREAD
        z = Z_F1 + (i + 1) * STAIR_RISE
        parts.append(box(f"RAIL_StairPost1_{i}", col, (0.05, 0.05, hr),
                         (x, yA1 - 0.04, z + hr / 2.0), "timber_dark"))
    for j in range(0, 8, 2):
        y = yB0 + (j + 0.5) * STAIR_TREAD
        z = STAIR_LANDING_Z + (j + 1) * STAIR_RISE
        parts.append(box(f"RAIL_StairPost2_{j}", col, (0.05, 0.05, hr),
                         (STAIR_XM + 0.04, y, z + hr / 2.0), "timber_dark"))
    # newel at the landing corner
    parts.append(box("RAIL_Newel", col, (0.10, 0.10, hr + 0.22),
                     (STAIR_XM + 0.05, yA1 - 0.05, STAIR_LANDING_Z + (hr + 0.22) / 2.0),
                     "timber_dark", chamfer=0.012))
    parts.append(cyl("RAIL_NewelCap", col, 0.075, 0.07,
                     (STAIR_XM + 0.05, yA1 - 0.05, STAIR_LANDING_Z + hr + 0.245),
                     "gold", segments=10))

    obj = join_objects(parts, "STAIR_Main")
    obj["tread_top"] = STAIR_LANDING_Z + 8 * STAIR_RISE
    obj["rail_top"] = Z_F2 + hr
    obj["rise"] = STAIR_RISE
    report("stairs built")
    return obj


# --------------------------------------------------------------------- roof

def _slope_grid(hx0, hy0, hx_end, hy_end, z_eave, rise, lift, side,
                n_u=28, n_v=10):
    """Ruled slope surface from the eave line to the ridge, with corner lift."""
    grid = []
    for iv in range(n_v + 1):
        v = iv / n_v
        row = []
        for iu in range(n_u + 1):
            s = iu / n_u
            if side == "front":
                x0, y0 = _lerp(-hx0, hx0, s), -hy0
                x1, y1 = _lerp(-hx_end, hx_end, s), -hy_end
                corner = abs(2 * s - 1) ** 3.2
            elif side == "back":
                x0, y0 = _lerp(-hx0, hx0, s), hy0
                x1, y1 = _lerp(-hx_end, hx_end, s), hy_end
                corner = abs(2 * s - 1) ** 3.2
            elif side == "right":
                x0, y0 = hx0, _lerp(-hy0, hy0, s)
                x1, y1 = hx_end, _lerp(-hy_end, hy_end, s)
                corner = abs(2 * s - 1) ** 3.2
            else:
                x0, y0 = -hx0, _lerp(-hy0, hy0, s)
                x1, y1 = -hx_end, _lerp(-hy_end, hy_end, s)
                corner = abs(2 * s - 1) ** 3.2
            x = _lerp(x0, x1, v)
            y = _lerp(y0, y1, v)
            z = z_eave + rise * (v ** ROOF_SLOPE_POW) + lift * corner * ((1.0 - v) ** 2)
            row.append(Vector((x, y, z)))
        grid.append(row)
    return grid


def build_side_veranda(col):
    """Covered side porch on the +X elevation.

    Four elevations that are all "wall plus two windows" read as the same
    building from every side. This porch (three posts, a beam and a lean-to
    waist eave) plus its stone platform gives the right elevation its own
    silhouette, so the four camera presets are recognisably different.
    """
    parts = []
    x_in = IX + 0.02          # wall face
    x_post = IX + 1.10        # post centre line
    x_out = IX + 1.54         # outer eave edge
    z_top = Z_F1 + 3.20       # underside of the lean-to at the wall
    z_eave = z_top - 0.30     # underside at the outer edge

    # stone platform the porch stands on
    parts.append(box("VER_Platform", col, (1.62, 6.24, 0.22),
                     (IX + 0.79, 0.0, 0.11), "stone", chamfer=0.02))
    parts.append(box("VER_Step", col, (0.34, 3.10, 0.11),
                     (IX + 1.78, 0.0, 0.055), "stone_warm", chamfer=0.012))

    # three posts + head beam
    for i, y in enumerate((-2.86, 0.0, 2.86)):
        parts.append(cyl(f"VER_Post{i}", col, 0.13, 3.14,
                         (x_post, y, 0.25 + 3.14 / 2.0), "timber", segments=12))
        parts.append(box(f"VER_Foot{i}", col, (0.34, 0.34, 0.12),
                         (x_post, y, 0.31), "stone_dark", chamfer=0.012))
        parts.append(box(f"VER_Brace{i}", col, (0.10, 0.10, 0.52),
                         (x_post, y, 3.16), "timber_dark"))
    parts.append(box("VER_Beam", col, (0.19, 5.94, 0.20),
                     (x_post, 0.0, 3.42), "timber_dark", chamfer=0.01))
    parts.append(box("VER_Purlin", col, (0.13, 6.20, 0.13),
                     (x_out - 0.12, 0.0, z_eave + 0.16), "timber", chamfer=0.008))

    # lean-to roof slab, wall side higher than the eave side
    slab = prism("VER_Roof", col,
                 [(x_in, z_top + 0.26), (x_out, z_eave + 0.26),
                  (x_out, z_eave + 0.08), (x_in, z_top + 0.08)],
                 6.30, (0.0, -3.15, 0.0), "roof_tile", axis="y")
    parts.append(slab)
    parts.append(box("VER_Fascia", col, (0.09, 6.30, 0.22),
                     (x_out - 0.01, 0.0, z_eave + 0.16), "timber_dark",
                     chamfer=0.008))
    # tile ribs so the lean-to reads as tiled rather than a bare slab
    for k in range(9):
        y = -2.80 + k * 0.70
        parts.append(box(f"VER_Tile{k}", col, (1.56, 0.11, 0.07),
                         (IX + 0.78, y, z_top - 0.02 -
                          (IX + 0.78 - x_in) * 0.19), "roof_tile_b",
                         chamfer=0.006))
    obj = join_objects(parts, "VER_Side")
    report("side veranda built")
    return obj


def _grid_mesh(name, col, grid, mat_key, flip=False, thickness=0.0):
    """Turn a (v, u) grid into quads, optionally extruded down into a slab."""
    bm = bmesh.new()
    rows = []
    for row in grid:
        rows.append([bm.verts.new(p) for p in row])
    bm.verts.ensure_lookup_table()
    for iv in range(len(rows) - 1):
        for iu in range(len(rows[0]) - 1):
            quad = (rows[iv][iu], rows[iv][iu + 1],
                    rows[iv + 1][iu + 1], rows[iv + 1][iu])
            try:
                f = bm.faces.new(quad if not flip else tuple(reversed(quad)))
            except ValueError:
                continue
            f.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = bm_to_object(bm, name, col, mat_key)
    if thickness:
        solid = obj.modifiers.new("SOLID", "SOLIDIFY")
        solid.thickness = thickness
        solid.offset = -1.0
    return obj


def _ridge_cap(col, half_len, z, name="ROOF_Ridge"):
    parts = []
    parts.append(box(f"{name}_Beam", col, (half_len * 2 + 0.30, 0.38, 0.30),
                     (0, 0, z + 0.15), "roof_slate", chamfer=0.02))
    parts.append(box(f"{name}_Cap", col, (half_len * 2 + 0.44, 0.46, 0.14),
                     (0, 0, z + 0.36), "roof_ridge", chamfer=0.025))
    parts.append(box(f"{name}_Crest", col, (half_len * 2 + 0.10, 0.20, 0.18),
                     (0, 0, z + 0.50), "roof_slate", chamfer=0.02))
    return parts


def _chiwen(col, x, z, sx, name="ROOF_Chiwen"):
    parts = []
    parts.append(box(f"{name}_Body{sx}", col, (0.28, 0.24, 0.46), (x, 0, z + 0.23),
                     "roof_slate", chamfer=0.02))
    parts.append(box(f"{name}_Tail{sx}", col, (0.14, 0.16, 0.42),
                     (x + sx * 0.13, 0, z + 0.58), "roof_slate",
                     rot_z=sx * 0.0, chamfer=0.015))
    parts.append(box(f"{name}_Horn{sx}", col, (0.10, 0.32, 0.14),
                     (x + sx * 0.02, 0, z + 0.44), "roof_ridge"))
    return parts


def build_main_roof(col):
    """Hip roof: four ruled slopes, 30/28 tile courses, 闂傚倷鑳堕崕闈浳ｉ崟顓犱笉闁瑰濮风粈? tidy eave layers."""
    parts = []
    hx0 = HX + ROOF_OVERHANG
    hy0 = HY + ROOF_OVERHANG
    hx_end = ROOF_RIDGE_HALF
    hy_end = 0.0
    z_eave = EAVE_Z
    lift = EAVE_LIFT

    slopes = {}
    slope_objs = []
    for side in ("front", "back", "left", "right"):
        n_u = 30 if side in ("front", "back") else 26
        grid = _slope_grid(hx0, hy0, hx_end, hy_end, z_eave, ROOF_RISE, lift,
                           side, n_u=n_u, n_v=10)
        slopes[side] = (grid, n_u)
        slope_objs.append(_grid_mesh(f"ROOF_{side}", col, grid, "roof_tile",
                                     thickness=0.20))

    # tile courses: raised barrel strips marching up each slope
    tile_parts = []
    for side, (grid, n_u) in slopes.items():
        n_v = len(grid) - 1
        courses = 30 if side in ("front", "back") else 28
        for k in range(courses):
            s = (k + 0.5) / courses
            base = []
            for iv in range(n_v + 1):
                v = iv / n_v
                a = grid[iv][min(n_u, int(s * n_u))]
                b = grid[iv][min(n_u, int(s * n_u) + 1)]
                base.append(a.lerp(b, s * n_u - int(s * n_u)))
            # perpendicular in plan
            if side in ("front", "back"):
                perp = Vector((1.0, 0.0, 0.0))
            else:
                perp = Vector((0.0, 1.0, 0.0))
            w = 0.085
            up = 0.05
            mat = "roof_tile_b" if k % 2 == 0 else "roof_tile"
            bm = bmesh.new()
            rows = []
            for iv, p in enumerate(base):
                v = iv / n_v
                shrink = 1.0 - 0.25 * v
                prof = [(-w * shrink, 0.0), (-w * 0.5 * shrink, up * 0.72),
                        (0.0, up), (w * 0.5 * shrink, up * 0.72), (w * shrink, 0.0)]
                row = [bm.verts.new(p + perp * a2 + Vector((0, 0, zz + 0.012)))
                       for a2, zz in prof]
                rows.append(row)
            for iv in range(len(rows) - 1):
                for iu in range(4):
                    try:
                        bm.faces.new((rows[iv][iu], rows[iv][iu + 1],
                                      rows[iv + 1][iu + 1], rows[iv + 1][iu]))
                    except ValueError:
                        pass
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            tile_parts.append(bm_to_object(bm, f"TILE_{side}_{k:02d}", col, mat))
            # 闂傚倷鑳堕崕闈浳ｉ崟顓犱笉闁瑰濮风粈?at the eave end of every course
            p = base[0]
            cap = cyl(f"TILE_Cap_{side}_{k:02d}", col, 0.075, 0.045,
                      (p.x, p.y, p.z - 0.02), mat, segments=8,
                      rot_x=math.pi / 2.0)
            tile_parts.append(cap)
    tiles = join_objects(tile_parts, "TILE_Main")

    # eave fascia ribbon following the upswept eave line
    fascia_parts = []
    n = 24
    for side in ("front", "back", "left", "right"):
        grid, n_u = slopes[side]
        pts = []
        for i in range(n_u + 1):
            s = i / n_u
            p = grid[0][i]
            pts.append(p)
        if side == "back":
            pts = list(reversed(pts))
        bm = bmesh.new()
        top = [bm.verts.new((p.x, p.y, p.z + 0.01)) for p in pts]
        bot = [bm.verts.new((p.x, p.y, p.z - 0.20)) for p in pts]
        for i in range(len(pts) - 1):
            bm.faces.new((top[i], top[i + 1], bot[i + 1], bot[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        fascia_parts.append(bm_to_object(bm, f"ROOF_Fascia_{side}", col,
                                         "timber_dark"))
    fascia = join_objects(fascia_parts, "ROOF_Fascia")

    # structural hierarchy under the eave: tie beam -> purlin -> rafter ends
    struct = []
    for side in ("front", "back", "left", "right"):
        along_x = side in ("front", "back")
        wall_line = (HY if side in ("front", "back") else HX) - 0.03
        out = hx0 if along_x else hy0
        sign = 1.0 if side in ("front", "right") else -1.0
        # purlin ring just outside the wall
        if along_x:
            struct.append(box(f"BEAM_Purlin_{side}", col,
                              (BUILD_X + 0.5, 0.17, 0.19),
                              (0, sign * (wall_line + 0.10), z_eave - 0.34),
                              "timber_dark"))
        else:
            struct.append(box(f"BEAM_Purlin_{side}", col,
                              (0.17, BUILD_DEPTH + 0.5, 0.19),
                              (sign * (wall_line + 0.10), 0, z_eave - 0.34),
                              "timber_dark"))
        # rafters: short, evenly spaced, only the visible overhang
        count = int((out * 2) / 0.42)
        for i in range(count):
            s = (i + 0.5) / count
            if along_x:
                x = _lerp(-out + 0.25, out - 0.25, s)
                p0 = Vector((x, sign * (wall_line - 0.05), z_eave - 0.30))
                p1 = Vector((x, sign * (out - 0.06), z_eave - 0.06))
            else:
                y = _lerp(-out + 0.25, out - 0.25, s)
                p0 = Vector((sign * (wall_line - 0.05), y, z_eave - 0.30))
                p1 = Vector((sign * (out - 0.06), y, z_eave - 0.06))
            struct.append(bar_between(f"BEAM_Rafter_{side}_{i:02d}", col,
                                      p0, p1, 0.075, 0.10, "timber"))
    structs = join_objects(struct, "ROOF_Eave")

    ridge = join_objects(_ridge_cap(col, hx_end, RIDGE_Z - 0.02), "ROOF_Ridge_Group")
    chi = join_objects(_chiwen(col, -hx_end - 0.12, RIDGE_Z + 0.20, -1) +
                       _chiwen(col, hx_end + 0.12, RIDGE_Z + 0.20, 1),
                       "ROOF_Chiwen")

    body = join_objects([fascia, structs] + slope_objs, "ROOF_Main")
    report("main roof built")
    return [body, tiles, ridge, chi]


def build_lower_roof(col):
    """Ring eave over the ground storey: shallow, tidy, half the main roof's mass."""
    hx0 = HX + ROOF_LOWER_OVERHANG
    hy0 = HY + ROOF_LOWER_OVERHANG
    z_eave = Z_F2 + 0.10
    parts = []
    slopes = {}
    for side in ("front", "back", "left", "right"):
        grid = _slope_grid(hx0, hy0, HX, HY, z_eave, ROOF_LOWER_RISE, 0.22,
                           side, n_u=26, n_v=5)
        slopes[side] = grid
        _grid_mesh(f"ROOF_Lower_{side}", col, grid, "roof_tile", thickness=0.14)

    tile_parts = []
    for side, grid in slopes.items():
        n_u = len(grid[0]) - 1
        n_v = len(grid) - 1
        courses = 30 if side in ("front", "back") else 28
        for k in range(courses):
            s = (k + 0.5) / courses
            base = []
            for iv in range(n_v + 1):
                a = grid[iv][min(n_u, int(s * n_u))]
                b = grid[iv][min(n_u, int(s * n_u) + 1)]
                base.append(a.lerp(b, s * n_u - int(s * n_u)))
            perp = Vector((1.0, 0, 0)) if side in ("front", "back") else Vector((0, 1.0, 0))
            mat = "roof_tile_b" if k % 2 == 0 else "roof_tile"
            bm = bmesh.new()
            rows = []
            for p in base:
                prof = [(-0.07, 0.0), (-0.035, 0.032), (0.0, 0.044),
                        (0.035, 0.032), (0.07, 0.0)]
                rows.append([bm.verts.new(p + perp * a2 + Vector((0, 0, zz + 0.01)))
                             for a2, zz in prof])
            for iv in range(len(rows) - 1):
                for iu in range(4):
                    try:
                        bm.faces.new((rows[iv][iu], rows[iv][iu + 1],
                                      rows[iv + 1][iu + 1], rows[iv + 1][iu]))
                    except ValueError:
                        pass
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            tile_parts.append(bm_to_object(bm, f"TILE_L_{side}_{k:02d}", col, mat))
    tiles = join_objects(tile_parts, "TILE_Lower")

    # fascia + hanging 闂傚倷绀佸﹢閬嶁€﹂崼銉ョ９濞寸姴顑呯粻?under the skirt eave
    bands = []
    for side in ("front", "back", "left", "right"):
        along_x = side in ("front", "back")
        sign = 1.0 if side in ("front", "right") else -1.0
        out = hx0 if along_x else hy0
        length = (hx0 if along_x else hy0) * 2
        cx = 0.0 if along_x else sign * out
        cy = sign * out if along_x else 0.0
        if along_x:
            bands.append(box(f"ROOF_LowerFascia_{side}", col,
                             (length, 0.10, 0.17), (cx, cy, z_eave - 0.08),
                             "timber_dark"))
            bands.append(box(f"ROOF_LowerLip_{side}", col,
                             (length, 0.16, 0.05), (cx, cy, z_eave + 0.01),
                             "timber"))
        else:
            bands.append(box(f"ROOF_LowerFascia_{side}", col,
                             (0.10, length, 0.17), (cx, cy, z_eave - 0.08),
                             "timber_dark"))
            bands.append(box(f"ROOF_LowerLip_{side}", col,
                             (0.16, length, 0.05), (cx, cy, z_eave + 0.01),
                             "timber"))
        # rafter ends under the skirt eave
        n = int(length / 0.55)
        for i in range(n):
            s = (i + 0.5) / n - 0.5
            if along_x:
                x, y = cx + s * length, cy - sign * 0.28
                bands.append(box(f"ROOF_LRafter_{side}_{i}", col,
                                 (0.07, 0.62, 0.09), (x, y, z_eave - 0.22),
                                 "timber"))
            else:
                x, y = cx - sign * 0.28, cy + s * length
                bands.append(box(f"ROOF_LRafter_{side}_{i}", col,
                                 (0.62, 0.07, 0.09), (x, y, z_eave - 0.22),
                                 "timber"))
    lower = join_objects(bands, "ROOF_Lower")
    report("lower roof built")
    return [lower, tiles]


# -------------------------------------------------------------------- cameras

def _camera(col, name, loc, target, lens=42.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_data.sensor_width = 36.0
    cam = bpy.data.objects.new(name, cam_data)
    col.objects.link(cam)
    cam.location = loc
    direction = Vector(target) - Vector(loc)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam["target"] = [round(v, 3) for v in target]
    return cam


def build_cameras(col):
    """Exterior orbit + interior presets; the web reads these from the layout."""
    cy = -0.55
    # Exterior framings are solved, not eyeballed: solve_cams.py searches
    # (elevation, distance, aim height, focal) for the nearest position whose
    # frustum still contains all eight plinth corners plus the ridge apex, so
    # "完整看到底座" holds instead of the base being cropped at the bottom edge.
    cams = [
        ("CAM_Front34", (19.61, 22.16, 9.18), (0.0, 0.0, 1.80), 40.0),
        ("CAM_Front", (0.0, 26.20, 9.23), (0.0, 0.0, 2.70), 40.0),
        ("CAM_Back", (0.0, -26.20, 9.23), (0.0, 0.0, 2.70), 40.0),
        ("CAM_Left", (-26.20, 0.0, 9.23), (0.0, 0.0, 2.70), 40.0),
        ("CAM_Right", (26.20, 0.0, 9.23), (0.0, 0.0, 2.70), 40.0),
        ("CAM_Top", (0.0, cy, 36.0), (0.0, cy, 0.0), 46.0),
        # interior presets: inside the room, looking at the framed back wall
        ("CAM_F1", (0.30, 1.25, 1.58), (0.0, -3.95, 1.55), 22.0),
        ("CAM_F2", (0.30, 1.05, 5.00), (0.0, -3.95, 5.00), 22.0),
        ("CAM_Ceiling", (0.0, 2.55, 5.15), (0.0, -0.9, 6.45), 16.0),
        ("CAM_Detail_Eave", (6.06, 5.58, 7.20), (4.20, 4.40, 6.80), 85.0),
    ]
    for name, loc, target, lens in cams:
        _camera(col, name, loc, target, lens)
    report(f"cameras: {len(cams)}")


# ------------------------------------------------------------------- lighting

def _sun(scene, name, rot, energy, color=(1.0, 0.95, 0.86), angle=0.16):
    data = bpy.data.lights.new(name, type="SUN")
    data.energy = energy
    data.color = color
    data.angle = angle
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.rotation_euler = rot
    return obj


def _point_light(name, loc, energy, radius, color, scene):
    data = bpy.data.lights.new(name, type="POINT")
    data.use_shadow = False
    data.energy = energy
    data.shadow_soft_size = radius
    data.color = color
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = loc
    return obj


def _area_light(name, loc, target, energy, size, color, scene):
    data = bpy.data.lights.new(name, type="AREA")
    data.use_shadow = False
    data.energy = energy
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = loc
    direction = Vector(target) - Vector(loc)
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return obj


def build_lighting(scene):
    """Soft daylight from the front-left plus warm interior fill."""
    sun = _sun(scene, "SUN_Key", (math.radians(52), 0.0, math.radians(38)),
               2.60, (1.0, 0.955, 0.885), 0.10)
    fill = _sun(scene, "SUN_Fill", (math.radians(64), 0.0, math.radians(-125)),
                0.90, (0.94, 0.95, 0.98), 0.35)
    fill.data.use_shadow = False
    for i, (x, y) in enumerate(((-1.8, -0.6), (1.8, -0.6), (0.0, 1.9))):
        _area_light(f"AREA_F1_{i}", (x, y, Z_F1 + F2_H + 0.05), (x, y, Z_F1),
                    60.0, 2.2, (1.0, 0.90, 0.76), scene)
    for i, (x, y) in enumerate(((-2.0, -0.4), (2.0, -0.4))):
        _area_light(f"AREA_F2_{i}", (x, y, Z_TOP - 0.25), (x, y, Z_F2),
                    42.0, 1.8, (1.0, 0.91, 0.78), scene)
    _point_light("PT_Hall", (0, -0.4, Z_TOP - 0.55), 26.0, 0.45,
                 (1.0, 0.80, 0.55), scene)
    # wash the coffered ceiling from below: without it the coffer steps read as
    # a black hole in every upward-looking view
    _area_light("AREA_Coffer", (0, -0.4, Z_TOP - 0.85), (0, -0.4, Z_TOP),
                34.0, 1.30, (1.0, 0.90, 0.75), scene)

    # Clear sky. A physical sky texture gets desaturated to neutral grey by the
    # AgX view transform, and a flat Background colour has no gradient at all,
    # so the sky is authored as an explicit three-stop vertical ramp: pale at the
    # horizon, mid blue overhead. Values stay below 1.0, so Standard view
    # transform shows the authored colour instead of clipping it to white.
    #
    # A saturated blue world also *lights* the scene, which turns every neutral
    # cream wall cyan, so camera rays see the blue ramp while indirect lighting
    # uses a neutral grey environment (Light Path > Is Camera Ray).
    world = bpy.data.worlds.new("W_Sky")
    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputWorld")
    bg_sky = tree.nodes.new("ShaderNodeBackground")
    bg_amb = tree.nodes.new("ShaderNodeBackground")
    lp = tree.nodes.new("ShaderNodeLightPath")
    mix = tree.nodes.new("ShaderNodeMixShader")
    geo = tree.nodes.new("ShaderNodeNewGeometry")
    sep = tree.nodes.new("ShaderNodeSeparateXYZ")
    ramp_in = tree.nodes.new("ShaderNodeMapRange")
    ramp = tree.nodes.new("ShaderNodeValToRGB")

    ramp_in.inputs["From Min"].default_value = -1.0
    ramp_in.inputs["From Max"].default_value = 1.0
    ramp_in.inputs["To Min"].default_value = 0.0
    ramp_in.inputs["To Max"].default_value = 1.0

    stops = ramp.color_ramp.elements
    stops[0].position = 0.40
    stops[0].color = (0.300, 0.480, 0.780, 1.0)   # horizon
    stops[1].position = 0.52
    stops[1].color = (0.140, 0.330, 0.700, 1.0)   # low sky
    mid = ramp.color_ramp.elements.new(0.82)
    mid.color = (0.045, 0.170, 0.520, 1.0)        # zenith blue

    tree.links.new(geo.outputs["Incoming"], sep.inputs[0])
    tree.links.new(sep.outputs["Z"], ramp_in.inputs["Value"])
    tree.links.new(ramp_in.outputs[0], ramp.inputs[0])
    tree.links.new(ramp.outputs["Color"], bg_sky.inputs[0])
    bg_sky.inputs[1].default_value = 1.0

    bg_amb.inputs[0].default_value = (0.62, 0.64, 0.68, 1.0)
    bg_amb.inputs[1].default_value = 0.72

    tree.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    tree.links.new(bg_amb.outputs[0], mix.inputs[1])
    tree.links.new(bg_sky.outputs[0], mix.inputs[2])
    tree.links.new(mix.outputs[0], out.inputs[0])
    scene.world = world

    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    return sun, fill