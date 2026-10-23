"""Street corner, garden, paving, planting and street furniture.

The plinth is a real urban corner, not a grey slab: an L of irregular 青灰 stone
paving wraps the front and right elevations (the two sides that face the
street), and everything else becomes a planted courtyard - raised beds, gravel,
layered trees, bamboo with actual leaves, bonsai and a stone lantern.

All coordinates are plinth coordinates (base centre at 0,0). The hall itself is
shifted by BUILD_Y, so the front street is deeper than the back yard.
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
    BASE_EDGE_W, BASE_SIZE, BUILD_DEPTH, BUILD_X, BUILD_Y, Z_F1, box,
    bm_to_object, cyl, join_objects, prism, report,
)

HALF = BASE_SIZE / 2.0            # 7.0
INNER = HALF - BASE_EDGE_W - 0.05  # 6.65
BX = BUILD_X / 2.0                # 4.2
BY0 = BUILD_Y - BUILD_DEPTH / 2.0  # -4.30  back face of the hall
BY1 = BUILD_Y + BUILD_DEPTH / 2.0  # 3.20   front face of the hall


def rnd(a: float, b: float = 0.0, c: float = 0.0) -> float:
    v = math.sin(a * 127.1 + b * 311.7 + c * 74.7) * 43758.5453
    return v - math.floor(v)


# ------------------------------------------------------------------- paving

def _paving_region(name, col, x0, x1, y0, y1, seed=0.0):
    """Irregular stone slabs with 18 mm joints and a little height variance."""
    parts = []
    step = 0.58
    ny = max(1, int(round((y1 - y0) / step)))
    nx = max(1, int(round((x1 - x0) / step)))
    dy = (y1 - y0) / ny
    dx = (x1 - x0) / nx
    for j in range(ny):
        for i in range(nx):
            cx = x0 + (i + 0.5) * dx + (rnd(i, j, seed) - 0.5) * 0.05
            cy = y0 + (j + 0.5) * dy + (rnd(i, j, seed + 1) - 0.5) * 0.05
            w = dx - 0.02 - rnd(i, j, seed + 2) * 0.05
            h = dy - 0.02 - rnd(i, j, seed + 3) * 0.05
            t = 0.05 + rnd(i, j, seed + 4) * 0.012
            rot = (rnd(i, j, seed + 5) - 0.5) * 0.03
            key = "paving_b" if rnd(i, j, seed + 6) > 0.62 else "paving"
            parts.append(box(f"{name}_{i}_{j}", col, (w, h, t),
                             (cx, cy, t / 2.0 - 0.004), key,
                             rot_z=rot, chamfer=0.006))
    return parts


def _tree_pit(name, col, x, y, size=0.95):
    """Square stone pit set into the paving, with soil a touch below the curb."""
    parts = []
    h = 0.12
    t = 0.085
    half = size / 2.0
    parts.append(box(f"{name}_Soil", col, (size - 2 * t, size - 2 * t, 0.05),
                     (x, y, 0.025), "timber_dark"))
    for k, (sx, sy, cx, cy) in enumerate((
            (size, t, 0, half),
            (size, t, 0, -half),
            (t, size - 2 * t, half, 0),
            (t, size - 2 * t, -half, 0))):
        parts.append(box(f"{name}_Curb{k}", col, (sx, sy, h),
                         (x + cx, y + cy, h / 2.0), "stone_dark", chamfer=0.01))
    return parts


def _garden_bed(name, col, x0, x1, y0, y1):
    """Raised stone curb filled with soil and ground cover."""
    parts = []
    h = 0.13
    t = 0.10
    parts.append(box(f"{name}_Soil", col, (x1 - x0 - 2 * t, y1 - y0 - 2 * t, h),
                     ((x0 + x1) / 2.0, (y0 + y1) / 2.0, h / 2.0), "plant_dark"))
    for k, (sx, sy, cx, cy) in enumerate((
            (x1 - x0, t, (x0 + x1) / 2.0, y0 + t / 2.0),
            (x1 - x0, t, (x0 + x1) / 2.0, y1 - t / 2.0),
            (t, y1 - y0 - 2 * t, x0 + t / 2.0, (y0 + y1) / 2.0),
            (t, y1 - y0 - 2 * t, x1 - t / 2.0, (y0 + y1) / 2.0))):
        parts.append(box(f"{name}_Curb{k}", col, (sx, sy, h + 0.05),
                         (cx, cy, (h + 0.05) / 2.0), "stone", chamfer=0.008))
    # ground cover tufts
    n = int((x1 - x0) * (y1 - y0) / 0.55)
    for k in range(max(4, n)):
        px = x0 + t + rnd(k, 1, x0) * (x1 - x0 - 2 * t)
        py = y0 + t + rnd(k, 2, y0) * (y1 - y0 - 2 * t)
        r = 0.10 + rnd(k, 3, 0) * 0.10
        parts.append(cyl(f"{name}_Tuft{k}", col, r, 0.07 + rnd(k, 4) * 0.06,
                         (px, py, h * 0.65), "plant" if k % 2 else "plant_light",
                         segments=7))
    return parts


def build_paving(col):
    parts = []
    # L-shaped street: front band plus right band
    parts += _paving_region("PROP_Pave_F", col, -INNER, INNER, BY1 + 0.06, INNER, 3.0)
    parts += _paving_region("PROP_Pave_R", col, BX + 0.06, INNER, -INNER, BY1 + 0.06, 7.0)
    # kerb between paving and garden
    parts.append(box("PROP_Kerb_A", col, (0.10, INNER - BY1, 0.11),
                     (-INNER + 0.05, (BY1 + INNER) / 2.0, 0.055), "stone_dark"))
    parts.append(box("PROP_Kerb_B", col, (INNER - BX - 0.06, 0.10, 0.11),
                     ((BX + 0.06 + INNER) / 2.0, BY1 + 0.06, 0.055), "stone_dark"))

    # garden quarter: left strip + rear strip + front-left bed
    parts += _garden_bed("PROP_Bed_L", col, -INNER, -BX - 0.10, -INNER, BY1 + 0.02)
    parts += _garden_bed("PROP_Bed_B", col, -INNER, BX + 0.06, -INNER, BY0 - 0.10)
    parts += _garden_bed("PROP_Bed_FL", col, -INNER, -BX - 0.95, BY1 + 0.10, INNER)

    # gravel apron directly in front of the entrance steps
    parts.append(box("PROP_Apron", col, (3.4, 0.9, 0.03),
                     (0, BY1 + 0.38, 0.015), "gravel"))

    obj = join_objects(parts, "PROP_Street")
    report(f"street: {len(obj.data.polygons)} faces")
    return obj


def build_stoop(col):
    """Two stone steps from the street up to the 0.25 m podium."""
    parts = []
    parts.append(box("BASE_Stoop0", col, (2.60, 0.42, 0.09),
                     (0, BY1 + 0.44, 0.035), "stone_warm", chamfer=0.012))
    parts.append(box("BASE_Stoop1", col, (2.45, 0.30, 0.09),
                     (0, BY1 + 0.27, 0.125), "stone", chamfer=0.012))
    parts.append(box("BASE_Stoop2", col, (2.32, 0.18, 0.09),
                     (0, BY1 + 0.12, 0.205), "stone_warm", chamfer=0.01))
    # cheek walls
    for sx in (-1, 1):
        parts.append(box(f"BASE_StoopCheek{sx}", col, (0.16, 0.70, 0.22),
                         (sx * 1.30, BY1 + 0.34, 0.11), "stone_dark", chamfer=0.01))
    obj = join_objects(parts, "BASE_Steps")
    return obj


# ------------------------------------------------------------------ planting

def _canopy(name, col, cx, cy, cz, radius, lobes=5, seed=0.0, key="plant"):
    """Clustered lobes instead of one icosphere: reads as foliage, not a ball."""
    parts = []
    for k in range(lobes):
        a = k * 2.399 + seed
        r = radius * (0.42 + rnd(k, seed, 1) * 0.26)
        dist = radius * (0.30 + rnd(k, seed, 2) * 0.42)
        px = cx + math.cos(a) * dist
        py = cy + math.sin(a) * dist * 0.92
        pz = cz + (rnd(k, seed, 3) - 0.35) * radius * 0.45
        parts.append(_blob(f"{name}_L{k}", col, (px, py, pz),
                           (r, r * 0.82, r * 0.74), key))
    return parts


def _blob(name, col, center, radii, key, subdiv=2):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    for v in bm.verts:
        n = 0.82 + 0.30 * rnd(v.co.x * 7.3 + v.co.y * 3.1, v.co.z * 5.7)
        v.co.x *= radii[0] * n
        v.co.y *= radii[1] * n
        v.co.z *= radii[2] * n
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return bm_to_object(bm, name, col, key, shade_smooth=True)


def _tree(name, col, x, y, height, spread=0.95, seed=0.0):
    parts = []
    trunk_h = height * 0.46
    parts.append(cyl(f"{name}_Trunk", col, 0.075 + height * 0.012, trunk_h,
                     (x, y, trunk_h / 2.0), "timber_dark", segments=8))
    for k in range(3):
        a = k * 2.1 + seed
        parts.append(cyl(f"{name}_Root{k}", col, 0.045, 0.16,
                         (x + math.cos(a) * 0.10, y + math.sin(a) * 0.10, 0.08),
                         "timber_dark", segments=6))
    # two branch cylinders angling out from the trunk top
    for k in range(3):
        a = k * 2.4 + seed
        p0 = Vector((x, y, trunk_h * 0.82))
        p1 = Vector((x + math.cos(a) * 0.34, y + math.sin(a) * 0.34,
                     trunk_h + height * 0.18))
        d = p1 - p0
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.045,
                              radius2=0.028, depth=d.length)
        rot = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
        bmesh.ops.translate(bm, vec=(p0 + p1) * 0.5, verts=bm.verts)
        parts.append(bm_to_object(bm, f"{name}_Branch{k}", col, "timber_dark"))
    parts += _canopy(f"{name}_Can", col, x, y, trunk_h + height * 0.34,
                     spread, lobes=6, seed=seed, key="plant")
    parts += _canopy(f"{name}_CanTop", col, x, y + 0.1, trunk_h + height * 0.52,
                     spread * 0.62, lobes=3, seed=seed + 9, key="plant_light")
    return parts


def _bamboo(name, col, x, y, count=7, seed=0.0):
    """Culms with node bands and leaf sprigs."""
    parts = []
    for k in range(count):
        a = rnd(k, seed, 1) * math.tau
        d = rnd(k, seed, 2) * 0.34
        bx = x + math.cos(a) * d
        by = y + math.sin(a) * d
        h = 2.0 + rnd(k, seed, 3) * 1.05
        lean = (rnd(k, seed, 4) - 0.5) * 0.10
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=7, radius1=0.030,
                              radius2=0.023, depth=h)
        bmesh.ops.translate(bm, vec=(0, 0, h / 2.0), verts=bm.verts)
        rot = Matrix.Rotation(lean, 4, "X") @ Matrix.Rotation(lean * 0.7, 4, "Y")
        bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
        bmesh.ops.translate(bm, vec=(bx, by, 0.0), verts=bm.verts)
        parts.append(bm_to_object(bm, f"{name}_Culm{k}", col, "bamboo",
                                 shade_smooth=True))
        # node bands
        nodes = 4
        for n in range(nodes):
            z = h * (0.30 + 0.16 * n)
            parts.append(cyl(f"{name}_Node{k}{n}", col, 0.036, 0.022,
                             (bx + lean * z * 0.6, by, z), "bamboo", segments=7))
        # leaf sprigs: three thin angled blades per node
        for n in range(nodes):
            z = h * (0.34 + 0.17 * n)
            for m in range(3):
                ang = a + n * 1.7 + m * 2.1
                ln = 0.30 + rnd(k, n * 3 + m, seed) * 0.18
                p0 = Vector((bx + lean * z * 0.6, by, z))
                p1 = Vector((p0.x + math.cos(ang) * ln, p0.y + math.sin(ang) * ln,
                             z + 0.10 + rnd(m, n, 3) * 0.12))
                parts.append(_leaf(f"{name}_Leaf{k}{n}{m}", col, p0, p1, 0.085))
    return parts


def _leaf(name, col, p0, p1, width):
    bm = bmesh.new()
    d = Vector(p1) - Vector(p0)
    L = d.length
    v0 = bm.verts.new((0, 0, 0))
    v1 = bm.verts.new((L, -width / 2.0, 0))
    v2 = bm.verts.new((L * 0.62, 0, 0.02))
    v3 = bm.verts.new((L, width / 2.0, 0))
    bm.faces.new((v0, v1, v2))
    bm.faces.new((v0, v2, v3))
    bm.normal_update()
    rot = d.normalized().to_track_quat("X", "Z").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(p0), verts=bm.verts)
    obj = bm_to_object(bm, name, col, "plant_dark")
    return obj


def _bonsai(name, col, x, y, z=0.0, height=0.85, seed=1.0):
    parts = []
    parts.append(box(f"{name}_Stand", col, (0.52, 0.52, 0.16), (x, y, z + 0.08),
                     "stone_dark", chamfer=0.012))
    parts.append(box(f"{name}_Pot", col, (0.40, 0.30, 0.16), (x, y, z + 0.24),
                     "porcelain_bl", chamfer=0.012))
    parts.append(box(f"{name}_PotRim", col, (0.44, 0.34, 0.03), (x, y, z + 0.325),
                     "porcelain"))
    # gnarled trunk: three stacked offset segments
    px, py, pz = x, y, z + 0.33
    for k in range(3):
        nx = px + math.cos(k * 2.0 + seed) * 0.09
        ny = py + math.sin(k * 2.0 + seed) * 0.07
        nz = pz + height * 0.20
        d = Vector((nx - px, ny - py, nz - pz))
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=6,
                              radius1=0.055 - k * 0.008,
                              radius2=0.042 - k * 0.008, depth=d.length)
        rot = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
        bmesh.ops.translate(bm, vec=(Vector((px, py, pz)) + Vector((nx, ny, nz))) * 0.5,
                            verts=bm.verts)
        parts.append(bm_to_object(bm, f"{name}_Trunk{k}", col, "timber_dark"))
        px, py, pz = nx, ny, nz
    parts += _canopy(f"{name}_Pad", col, px, py, pz, 0.36, lobes=4,
                     seed=seed + 3, key="plant")
    parts += _canopy(f"{name}_Pad2", col, x + 0.06, y - 0.05, z + 0.46, 0.22,
                     lobes=3, seed=seed + 7, key="plant_light")
    return parts


def build_plants(col):
    parts = []
    # planting pits: the street trees stand in paving, so each needs a real
    # stone curb and soil pit instead of sprouting straight out of the slabs
    parts += _tree_pit("PROP_PitA", col, 5.35, 5.30)
    parts += _tree_pit("PROP_PitB", col, 5.90, -3.30)
    parts += _tree_pit("PROP_PitC", col, -2.10, 6.10, size=0.86)
    # garden trees
    parts += _tree("PROP_TreeA", col, 5.35, 5.30, 2.55, 1.05, 0.4)
    parts += _tree("PROP_TreeB", col, -5.60, 5.35, 2.15, 0.88, 1.7)
    parts += _tree("PROP_TreeC", col, -5.35, -1.20, 2.40, 0.95, 2.9)
    parts += _tree("PROP_TreeD", col, -3.20, -5.55, 2.30, 0.92, 4.1)
    parts += _tree("PROP_TreeE", col, 2.10, -5.65, 2.10, 0.85, 5.3)
    # bamboo groves
    parts += _bamboo("PROP_BambooA", col, -5.85, 1.90, 8, 0.8)
    parts += _bamboo("PROP_BambooB", col, 5.90, -3.30, 7, 2.2)
    parts += _bamboo("PROP_BambooC", col, -2.10, 6.10, 6, 3.6)
    # bonsai on the garden edge
    parts += _bonsai("PROP_Bonsai", col, -5.60, 3.55, 0.02, 0.80, 1.3)
    obj = join_objects(parts, "PROP_Plants")
    report(f"plants: {len(obj.data.polygons)} faces")
    return obj


# --------------------------------------------------------------- street kit

def build_stone_lantern(col, x, y, name="PROP_StoneLantern"):
    parts = []
    parts.append(box(f"{name}_Base", col, (0.42, 0.42, 0.14), (x, y, 0.07),
                     "stone_dark", chamfer=0.01))
    parts.append(box(f"{name}_Base2", col, (0.30, 0.30, 0.10), (x, y, 0.19),
                     "stone", chamfer=0.008))
    parts.append(cyl(f"{name}_Shaft", col, 0.075, 0.56, (x, y, 0.52),
                     "stone", segments=8))
    parts.append(box(f"{name}_Box", col, (0.34, 0.34, 0.26), (x, y, 0.92),
                     "stone_warm", chamfer=0.01))
    parts.append(box(f"{name}_Glow", col, (0.20, 0.20, 0.14), (x, y, 0.92),
                     "lamp_glow"))
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(box(f"{name}_Post{sx}{sy}", col, (0.055, 0.055, 0.26),
                             (x + sx * 0.14, y + sy * 0.14, 0.92), "stone_dark"))
    # pyramidal roof
    parts.append(prism(f"{name}_Roof", col,
                       [(-0.30, 0), (0.30, 0), (0.20, 0.16), (-0.20, 0.16)],
                       0.30, (x, y - 0.15, 1.05), "stone_dark", axis="y"))
    parts.append(cyl(f"{name}_Finial", col, 0.05, 0.10, (x, y, 1.26),
                     "stone_dark", segments=8))
    return join_objects(parts, name)


def build_lamps(col):
    parts = []
    for i, (x, y) in enumerate(((-6.05, 4.30), (6.05, 1.10), (2.40, 5.75))):
        parts.append(box(f"PROP_Lamp{i}_Base", col, (0.28, 0.28, 0.12),
                         (x, y, 0.06), "stone_dark", chamfer=0.01))
        parts.append(cyl(f"PROP_Lamp{i}_Post", col, 0.045, 1.85,
                         (x, y, 1.04), "timber_dark", segments=8))
        parts.append(box(f"PROP_Lamp{i}_Arm", col, (0.30, 0.05, 0.05),
                         (x, y, 1.95), "timber_dark"))
        parts.append(cyl(f"PROP_Lamp{i}_Cap", col, 0.15, 0.06,
                         (x + 0.13, y, 1.90), "timber_dark", segments=8))
        parts.append(box(f"PROP_Lamp{i}_Glass", col, (0.20, 0.20, 0.24),
                         (x + 0.13, y, 1.76), "lamp_glow"))
        for sx in (-1, 1):
            for sy in (-1, 1):
                parts.append(box(f"PROP_Lamp{i}_Bar{sx}{sy}", col,
                                 (0.028, 0.028, 0.26),
                                 (x + 0.13 + sx * 0.10, y + sy * 0.10, 1.76),
                                 "timber_dark"))
    obj = join_objects(parts, "PROP_StreetLamps")
    return obj


def build_planters(col):
    parts = []
    for i, (x, y, w, d) in enumerate(((-2.55, 3.62, 1.05, 0.55),
                                      (2.55, 3.62, 1.05, 0.55))):
        parts.append(box(f"PROP_Planter{i}", col, (w, d, 0.46), (x, y, 0.23),
                         "stone_warm", chamfer=0.012))
        parts.append(box(f"PROP_Planter{i}_Soil", col, (w - 0.14, d - 0.14, 0.06),
                         (x, y, 0.44), "plant_dark"))
        for k in range(5):
            px = x + (rnd(k, i, 1) - 0.5) * (w - 0.3)
            py = y + (rnd(k, i, 2) - 0.5) * (d - 0.3)
            parts.append(_blob(f"PROP_Planter{i}_S{k}", col,
                               (px, py, 0.52), (0.13, 0.13, 0.11),
                               "plant" if k % 2 else "flower"))
    obj = join_objects(parts, "PROP_Planters")
    return obj


def build_signs(col):
    """Heritage information board facing the street + a small wayfinding post."""
    parts = []
    # info board on the street corner
    x, y = 5.35, 4.55
    parts.append(box("PROP_Board_LegA", col, (0.10, 0.10, 1.35), (x - 0.72, y, 0.67),
                     "timber_dark", chamfer=0.008))
    parts.append(box("PROP_Board_LegB", col, (0.10, 0.10, 1.35), (x + 0.72, y, 0.67),
                     "timber_dark", chamfer=0.008))
    parts.append(box("PROP_Board_Panel", col, (1.66, 0.09, 0.92), (x, y, 1.30),
                     "timber_warm", chamfer=0.01))
    parts.append(box("PROP_Board_Face", col, (1.50, 0.03, 0.76), (x, y + 0.055, 1.30),
                     "paper"))
    parts.append(box("PROP_Board_Roof", col, (1.86, 0.30, 0.07), (x, y, 1.82),
                     "roof_slate", chamfer=0.012))
    parts.append(box("PROP_Board_Cap", col, (1.90, 0.34, 0.04), (x, y, 1.86),
                     "roof_ridge"))

    # wayfinding post
    x2, y2 = -6.15, 5.85
    parts.append(cyl("PROP_Sign_Post", col, 0.055, 2.05, (x2, y2, 1.02),
                     "timber_dark", segments=8))
    for k, (zz, ln) in enumerate(((1.72, 0.72), (1.44, 0.58))):
        parts.append(box(f"PROP_Sign_Plank{k}", col, (ln, 0.05, 0.17),
                         (x2 + ln / 2.0 - 0.06, y2, zz), "timber_warm",
                         rot_z=-0.10, chamfer=0.008))
        parts.append(box(f"PROP_Sign_Ink{k}", col, (ln * 0.62, 0.02, 0.05),
                         (x2 + ln / 2.0 - 0.06, y2 + 0.032, zz), "ink",
                         rot_z=-0.10))
    parts.append(cyl("PROP_Sign_Finial", col, 0.065, 0.10, (x2, y2, 2.09),
                     "gold", segments=8))
    obj = join_objects(parts, "PROP_Signs")
    return obj


def build(col):
    objs = []
    objs.append(build_paving(col))
    objs.append(build_stoop(col))
    objs.append(build_plants(col))
    objs.append(build_stone_lantern(col, 5.95, 0.10))
    objs.append(build_lamps(col))
    objs.append(build_planters(col))
    objs.append(build_signs(col))
    report("street props built")
    return objs