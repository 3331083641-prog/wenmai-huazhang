"""V5 site: floating sumeru base, L-shaped street, planting and street props.

What this module is trying to do (the renders are the only judge):
    * the base has to read as carved stone, not a slab: five courses with real
      insets between them, a meander (huiwen) frieze carved into the recessed
      waist, lotus roundels on the body, block joints on the faces and four
      corner pilasters that break the horizontal banding;
    * underneath it a dark stepped timber bracket grid (rim + cross beams), so
      the model floats on joinery instead of a closed box;
    * the street is an L on the +Y front: a wide apron outside the eave shadow
      that turns into a 2.1 m walk down +X, laid in running bond with 3 cm
      joints, two slab directions, a dark threshold court and a dark border
      course so the turn reads, edged by a raised kerb at the deck rim;
    * planting is shaped, not scattered: two forked trees with layered canopies
      (one closing the +X walk, one on the narrow -X band), two bamboo clumps
      with ringed nodes and real leaf blades, four bonsai and one rock group.

Layout rules taken from the shell contract:
    FRONT_Y = BCY + BD/2 = 3.20 (front wall, street side), BACK_Y = -4.30.
    The strip 3.20..~4.40 sits under the skirt / main eave, so it stays plain
    deck; the apron proper starts at 4.40. Nothing taller than 0.5 m near the
    +Y rim, so the front eave stays readable from the front camera.

Every stone tone is created locally through gal5.mat: the site needs a wider
value range than the shared palette has, otherwise the five courses and the
paving all wash out to the same pale grey in the renders.

All comments are ASCII on purpose: these files round-trip through PowerShell on
Windows and non-ASCII source has been corrupted before.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

import gal5 as G

# ------------------------------------------------------------------ layout
HALF = G.BASE * 0.5          # 8.0: half of the 16 x 16 plan
TOP = G.BASE_TOP             # 0.25: walking level, every prop sits exactly here
Z_BOT = G.BASE_BOT           # -0.40: underside of the floating bracket grid

FRONT_Y = G.BCY + G.BD * 0.5     # 3.20 front wall (street side)
BACK_Y = G.BCY - G.BD * 0.5      # -4.30

# street plan (deck coordinates, metres)
KERB_IN = HALF - 0.30        # 7.70 inner face of the kerb band
KERB_OUT = HALF - 0.06       # 7.94 outer face
APRON_Y0 = 4.40              # just outside the main eave shadow (eave ~4.15)
APRON_Y1 = KERB_IN
WALK_X0 = 5.60
WALK_B = 0.20                # dark border course along the walk's inner edge
WALK_X1 = KERB_IN
WALK_Y0 = -0.85              # south end of the side walk (tree bed closes it)
WALK_Y1 = APRON_Y0

SLAB_H = 0.028               # paving thickness measured down from BASE_TOP
BED_TOP = TOP - SLAB_H       # top of the dark paving bed

# sumeru profile: (z0, z1, width at z0, width at z1, tone key, groove)
# The waist is three rows: the frieze panel (15.20) is recessed 0.05 per side
# inside the waist (15.30) so the meander sits in its own shadow.
COURSES = (
    (-0.312, -0.240, 15.16, 15.62, "chamfer", False),   # bottom chamfer
    (-0.240, -0.170, 15.90, 15.72, "roll", True),       # lower roll moulding
    (-0.170, -0.158, 15.30, 15.30, "waist", False),     # waist, below panel
    (-0.158, 0.028, 15.20, 15.20, None, False),         # frieze recess panel
    (0.028, 0.040, 15.30, 15.30, "waist", False),       # waist, above panel
    (0.040, 0.150, 15.66, 15.66, "body", True),         # body + roundels
    (0.150, 0.205, 15.98, 15.88, "mould", True),        # top moulding
)
GROOVE_H = 0.030             # height of the shadow groove at a course foot
GROOVE_D = 0.025             # how far the groove sinks in, per side

FRIEZE_Z = -0.065            # centre of the meander band
FRIEZE_H = 0.170             # band height: rails 0.050 each, 0.070 left open
FRIEZE_BAR = 0.050
FRIEZE_FACE = 7.60           # face of the recessed panel
FRIEZE_OUT = 7.68            # outer face of the carved bars

# planting beds, all with a job: two raised planters on the deck edge and one
# back corner bed. Form: (x, y, width_x, depth_y, height).
BED_RIGHT = (6.55, -1.75, 1.45, 1.70, 0.40)   # closes the side walk, +X edge
BED_LEFT = (-6.55, 1.65, 1.72, 1.72, 0.44)    # narrow -X planting band
BED_BACK = (-5.85, -6.55, 2.90, 1.55, 0.30)   # back corner bed

# street furniture, front street (+Y) and the +X turn
LANTERN_AT = (2.95, 4.98)     # beside the door, at the head of the apron
GUIDE_AT = (4.72, 5.72)       # guide board on two posts, front street
EASEL_AT = (-3.72, 5.72)      # display easel, front street
STAND_AT = (4.95, 2.15)       # display stand in the veranda shade, +X side
BONSAI_AT = (
    (6.96, 5.62, 0.90),       # corner of the walk, on a stone pad
    (1.52, 6.28, 0.90),       # front street, inboard of the rim
    (-2.55, -5.45, 0.94),     # back courtyard beside the rear steps
)
TREE_A = (6.55, -1.75)        # in BED_RIGHT
TREE_B = (-6.55, 1.65)        # in BED_LEFT
BAMBOO_A = (-7.02, -2.05)
BAMBOO_B = (6.90, -5.15)
ROCKS_AT = (6.52, -3.55)


# ------------------------------------------------------------------ materials
def _st(name, v, warm=True, rough=0.92):
    """Local stone tone, cached through gal5.mat."""
    key = "M_site_%s_%03d" % (name, int(round(v * 100)))
    if key in G.MATS:
        return G.MATS[key]
    if warm:
        rgb = (v, v * 0.980, v * 0.932)
    else:
        rgb = (v * 0.950, v * 0.968, v)
    return G.mat(key, rgb, rough=rough)


# Values are deliberately low: the deck is a horizontal plane in full sun, so
# an albedo of 0.4 already clips to white under this exposure. The ladder below
# is what keeps five courses and two paving tones apart in the render.
def _stw(name, v, rough=0.90):
    """Warm paving stone: the street has to read warmer than the cool deck
    field, because hue survives the roof shadow that covers half the apron."""
    key = "M_site_%s_%03d" % (name, int(round(v * 100)))
    if key in G.MATS:
        return G.MATS[key]
    return G.mat(key, (v, v * 0.958, v * 0.888), rough=rough)


# The five courses are read from below in v5_12, where only ambient light
# reaches them: the ladder has to be wide, and every course foot needs a dark
# groove, or the whole plinth flattens into one grey band.
ST_CHAMFER = _st("chamfer", 0.300)     # lowest course (gui jiao)
ST_ROLL = _st("roll", 0.550)           # lower roll moulding (xia fang)
ST_WAIST = _st("waist", 0.340)         # waist, darkest: lets the meander float
ST_BODY = _st("body", 0.620)           # body course (shang fang)
ST_MOULD = _st("mould", 0.720)         # top moulding, brightest
ST_GROOVE = _st("groove", 0.105)       # shadow groove between courses
ST_CARVE = _st("carve", 0.680)         # meander bars against the dark waist
ST_MED = _st("med", 0.800)             # roundels sit on the lighter body face
ST_PIL = _st("pil", 0.560)
ST_JOINT = _st("joint", 0.300)
ST_BED = _st("bed", 0.135, warm=False)
ST_KERB = _st("kerb", 0.400)
ST_KERB2 = _st("kerb2", 0.345)
ST_GRID_RIM = _st("grid_rim", 0.170, rough=0.80)
ST_GRID_X = _st("grid_x", 0.105, rough=0.80)
ST_GRID_Y = _st("grid_y", 0.135, rough=0.80)
ST_PLANTER = _st("planter", 0.420)
ST_PLANTER_RIM = _st("planter_rim", 0.500)
ST_PLANTER_BASE = _st("planter_base", 0.320)
STREET = (_stw("st1", 0.330), _stw("st2", 0.400), _stw("st3", 0.290))
FIELD = (_st("f1", 0.190, warm=False), _st("f2", 0.245, warm=False),
         _st("f3", 0.165, warm=False))
DARK_COURSE = (_st("thr1", 0.150, warm=False), _st("thr2", 0.195, warm=False))


# ------------------------------------------------------------------ helpers
def _rnd(i, j, k=0):
    """Deterministic pseudo random in [0, 1): no dependency on random module."""
    n = (int(i) * 73856093) ^ (int(j) * 19349663) ^ (int(k) * 83492791)
    n &= 0x7FFFFFFF
    return (n % 10007) / 10007.0


def _lerp(p0, p1, t):
    return Vector(p0) + (Vector(p1) - Vector(p0)) * t


def _limb(name, p0, p1, r0, r1, col, mat, seg=8):
    """Tapered limb between two points (trunk / branch / bamboo stalk)."""
    p0, p1 = Vector(p0), Vector(p1)
    v = p1 - p0
    length = v.length
    if length < 1e-5:
        return None
    ob = G.add_cone(name, r0, r1, length, tuple((p0 + p1) * 0.5), col, mat,
                    segments=seg)
    ob.rotation_euler = v.to_track_quat("Z", "Y").to_euler()
    return ob


def _taper(name, w0, w1, z0, z1, col, mat):
    """Square frustum: a course whose top and bottom faces differ in width."""
    h0, h1 = w0 * 0.5, w1 * 0.5
    h = z1 - z0
    verts = (
        (-h0, -h0, 0.0), (h0, -h0, 0.0), (h0, h0, 0.0), (-h0, h0, 0.0),
        (-h1, -h1, h), (h1, -h1, h), (h1, h1, h), (-h1, h1, h),
    )
    faces = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
    return G.add_mesh(name, verts, faces, col, mat, loc=(0.0, 0.0, z0))


def _inside(x, y, rect):
    return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]


def _tris(objs):
    n = 0
    for ob in objs:
        if ob is None or getattr(ob, "type", "") != "MESH":
            continue
        ob.data.calc_loop_triangles()
        n += len(ob.data.loop_triangles)
    return n


def _bake(ob):
    """Flatten rotation/scale into the mesh.

    Joined group objects inherit the transform of their first member (a leaning
    trunk, a rotated roof tile), which would inflate the object bounding box the
    layout exporter reads and tilt the node in the exported GLB. Baking keeps
    the site envelope exact.
    """
    if ob is None:
        return ob
    try:
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    except Exception as exc:                       # pragma: no cover
        G.log("site: bake skipped on %s (%s)" % (ob.name, exc))
    return ob


def _join(name, objs):
    objs = [o for o in objs if o is not None]
    if not objs:
        return []
    return [_bake(G.join_objs(name, objs))]


# ------------------------------------------------------------------ base
def _bracket_grid(col):
    """Dark stepped timber bracket grid under the plinth.

    From the low camera the underside is lit only by sky ambient, so the beams
    have to sit clearly below the plate in value, and the cross/longitudinal
    layers need a real 0.06 step or the whole soffit reads as one flat sheet.
    """
    obs = []
    rim_z0, rim_z1 = -0.348, -0.300      # rim: tucked up against the stone
    xz0, xz1 = Z_BOT, -0.330             # cross beams: hang lowest
    yz0, yz1 = Z_BOT + 0.060, -0.288     # longitudinal beams: one step higher
    rim_out = 14.60
    rim_w = 0.34
    h = rim_out * 0.5
    for sy in (-1, 1):
        obs.append(G.add_box("SITE_GRID_RimY%d" % sy,
                             (rim_out, rim_w, rim_z1 - rim_z0),
                             (0.0, sy * (h - rim_w * 0.5),
                              (rim_z0 + rim_z1) * 0.5), col, ST_GRID_RIM))
    for sx in (-1, 1):
        obs.append(G.add_box("SITE_GRID_RimX%d" % sx,
                             (rim_w, rim_out - rim_w * 2, rim_z1 - rim_z0),
                             (sx * (h - rim_w * 0.5), 0.0,
                              (rim_z0 + rim_z1) * 0.5), col, ST_GRID_RIM))
    for i, yy in enumerate((-5.35, -2.68, 0.0, 2.68, 5.35)):
        obs.append(G.add_box("SITE_GRID_BeamX%d" % i,
                             (13.62, 0.30, xz1 - xz0),
                             (0.0, yy, (xz0 + xz1) * 0.5), col, ST_GRID_X))
    for i, xx in enumerate((-4.80, 0.0, 4.80)):
        obs.append(G.add_box("SITE_GRID_BeamY%d" % i,
                             (0.26, 13.10, yz1 - yz0),
                             (xx, 0.0, (yz0 + yz1) * 0.5), col, ST_GRID_Y))
    for sx in (-1, 1):
        for sy in (-1, 1):
            obs.append(G.add_box("SITE_GRID_Br%d%d" % (sx, sy),
                                 (0.62, 0.62, 0.050),
                                 (sx * (h - 0.55), sy * (h - 0.55),
                                  -0.352), col, ST_GRID_RIM))
    return obs


def _course_blocks(col):
    """Thin recessed joints on the body course: reads as laid stone blocks."""
    obs = []
    z0, z1 = 0.040, 0.150
    for face in (-1, 1):
        for i in range(-4, 5):
            if i == 0:
                continue
            u = i * 1.62
            obs.append(G.add_box("SITE_BLK_Y%d_%d" % (face, i),
                                 (0.016, 0.013, z1 - z0 - 0.006),
                                 (u, face * 7.833, (z0 + z1) * 0.5), col,
                                 ST_JOINT))
            obs.append(G.add_box("SITE_BLK_X%d_%d" % (face, i),
                                 (0.013, 0.016, z1 - z0 - 0.006),
                                 (face * 7.833, u, (z0 + z1) * 0.5), col,
                                 ST_JOINT))
    return obs


def _medallion(name, radius, loc, col, mat, axis):
    """Eight petal lotus roundel, turned onto an X face when asked."""
    ob = G.lotus_medallion(name, radius, 0.05, (0.0, 0.0, 0.0), col, mat,
                           petals=8)
    if axis == "x":
        ob.rotation_euler = (0.0, 0.0, math.pi * 0.5)
    ob.location = Vector(loc)
    return ob


def _band_box(name, u0, u1, v0, v1, depth, loc, col, mat, axis):
    """One bar of a frieze, in face coordinates (u along, v up), centred on loc."""
    du = abs(u1 - u0)
    dv = abs(v1 - v0)
    cu = (u0 + u1) * 0.5
    cv = (v0 + v1) * 0.5
    if du <= 1e-4 or dv <= 1e-4:
        return None
    if axis == "x":
        return G.add_box(name, (du, depth, dv),
                         (loc[0] + cu, loc[1], loc[2] + cv), col, mat)
    return G.add_box(name, (depth, du, dv),
                     (loc[0], loc[1] + cu, loc[2] + cv), col, mat)


def _meander(name, length, height, depth, loc, col, mat, axis="x",
             period=0.32, bar=0.050):
    """Continuous huiwen meander.

    The shared huiwen_band helper puts one stub plus one short rail per cell,
    which reads as a row of dashes. This one is genuinely connected: a single
    base rail runs the whole face, and every cell carries a full height riser,
    an upper return and a drop, so the line never breaks. Each cell is a squared
    spiral, which is what makes it recognisable instead of decorative noise.
    """
    obs = []
    n = max(2, int(round(length / period)))
    p = length / n
    half = height * 0.5
    # continuous base rail: this is what keeps the pattern unbroken
    obs.append(_band_box(name + "_rail", -length * 0.5, length * 0.5,
                         -half, -half + bar, depth, loc, col, mat, axis))
    for k in range(n):
        u0 = -length * 0.5 + k * p
        ue = u0 + p * 0.74                 # riser centre line
        ut = ue - p * 0.48                 # far end of the upper return
        # riser: from the base rail up to the top of the band
        obs.append(_band_box("%s_v%d" % (name, k), ue - bar * 0.5, ue + bar * 0.5,
                             -half + bar, half, depth, loc, col, mat, axis))
        # upper return
        obs.append(_band_box("%s_t%d" % (name, k), ut, ue + bar * 0.5,
                             half - bar, half, depth, loc, col, mat, axis))
        # drop at the far end: stops short of the base rail so the cell keeps
        # an open hole, which is what makes the key pattern read
        obs.append(_band_box("%s_d%d" % (name, k), ut - bar * 0.5, ut + bar * 0.5,
                             -half * 0.14, half - bar, depth, loc, col,
                             mat, axis))
    return [o for o in obs if o is not None]


def build_base(col):
    out = []
    out.extend(_join("SITE_BASE_GRID", _bracket_grid(col)))

    tone_of = {"chamfer": ST_CHAMFER, "roll": ST_ROLL, "waist": ST_WAIST,
               "body": ST_BODY, "mould": ST_MOULD}
    courses = []
    for i, (z0, z1, w0, w1, key, groove) in enumerate(COURSES):
        if key is None:
            # recessed frieze panel: dark, so the carved bars read against it
            courses.append(_taper("SITE_BASE_P%d" % i, w0, w1, z0, z1, col,
                                  ST_WAIST))
            continue
        tone = tone_of[key]
        gz = z0
        if groove and z1 - z0 > GROOVE_H * 2.0:
            gz = z0 + GROOVE_H
            courses.append(_taper("SITE_BASE_G%d" % i, w0 - GROOVE_D * 2.0,
                                  w0 - GROOVE_D * 2.0, z0, gz, col, ST_GROOVE))
        courses.append(_taper("SITE_BASE_C%d" % i, w0, w1, gz, z1, col, tone))
    # corner pilasters on the body: break the horizontal banding at the corners
    for sx in (-1, 1):
        for sy in (-1, 1):
            courses.append(G.add_box("SITE_BASE_PilY%d%d" % (sx, sy),
                                     (0.36, 0.062, 0.118),
                                     (sx * 7.65, sy * 7.848, 0.094), col, ST_PIL))
            courses.append(G.add_box("SITE_BASE_PilX%d%d" % (sx, sy),
                                     (0.062, 0.34, 0.118),
                                     (sx * 7.848, sy * 7.65, 0.094), col, ST_PIL))
    courses.extend(_course_blocks(col))
    # dark paving bed: joints between slabs show this, not a hole in the world
    courses.append(G.add_box("SITE_BASE_Bed", (15.62, 15.62, BED_TOP - 0.205),
                             (0.0, 0.0, (0.205 + BED_TOP) * 0.5), col, ST_BED))
    out.extend(_join("SITE_BASE_COURSES", courses))

    frieze = []
    fdepth = FRIEZE_OUT - FRIEZE_FACE
    floc = (FRIEZE_FACE + FRIEZE_OUT) * 0.5
    for sy in (-1, 1):
        frieze.extend(_meander("SITE_BASE_HuiY%d" % sy, 14.10, FRIEZE_H, fdepth,
                               (0.0, sy * floc, FRIEZE_Z), col, ST_CARVE,
                               axis="x", bar=FRIEZE_BAR))
    for sx in (-1, 1):
        frieze.extend(_meander("SITE_BASE_HuiX%d" % sx, 14.10, FRIEZE_H, fdepth,
                               (sx * floc, 0.0, FRIEZE_Z), col, ST_CARVE,
                               axis="y", bar=FRIEZE_BAR))
    out.extend(_join("SITE_BASE_FRIEZE", frieze))

    meds = []
    r = 0.054
    for sx in (-1, 1):
        for sy in (-1, 1):
            meds.append(_medallion("SITE_BASE_MedY%d%d" % (sx, sy), r,
                                   (sx * 7.28, sy * 7.833, 0.095), col,
                                   ST_MED, "y"))
            meds.append(_medallion("SITE_BASE_MedX%d%d" % (sx, sy), r,
                                   (sx * 7.833, sy * 7.28, 0.095), col,
                                   ST_MED, "x"))
    for sy in (-1, 1):
        meds.append(_medallion("SITE_BASE_MedYm%d" % sy, r,
                               (0.0, sy * 7.833, 0.095), col, ST_MED, "y"))
    for sx in (-1, 1):
        meds.append(_medallion("SITE_BASE_MedXm%d" % sx, r,
                               (sx * 7.833, 0.0, 0.095), col, ST_MED, "x"))
    out.extend(_join("SITE_BASE_MEDALLIONS", meds))
    return out


# ------------------------------------------------------------------ paving
def _bond(tag, x0, y0, x1, y1, along, slab, row, mats, col, seed=0, skip=None):
    """Running bond paving inside an axis aligned rect.

    along="x": slabs run along X, courses advance in +Y.
    along="y": slabs run along Y, courses advance in +X.
    Joints are 30 mm; every other course starts on a short slab so the bond
    actually breaks instead of lining up into a grid.
    """
    obs = []
    gap = 0.030
    if along == "x":
        nrow = max(1, int(round((y1 - y0) / row)))
        rh = (y1 - y0) / nrow
        for r in range(nrow):
            cy = y0 + rh * (r + 0.5)
            jy = (_rnd(r, 3, seed) - 0.5) * 0.012
            x = x0
            i = 0
            guard = 0
            while x < x1 - 0.07 and guard < 400:
                guard += 1
                ln = slab * (0.80 + 0.42 * _rnd(r, i, seed + 5))
                if i == 0 and r % 2:
                    ln *= 0.55
                if x + ln > x1 - 0.018:
                    ln = x1 - 0.018 - x
                if ln < 0.10:
                    break
                cx = x + ln * 0.5
                if skip is None or not _inside(cx, cy + jy, skip):
                    obs.append(G.add_box("%s_%d_%d" % (tag, r, i),
                                         (ln - gap, rh - gap, SLAB_H),
                                         (cx, cy + jy, TOP - SLAB_H * 0.5),
                                         col, mats[(r * 3 + i) % len(mats)]))
                x += ln
                i += 1
    else:
        nrow = max(1, int(round((x1 - x0) / row)))
        rw = (x1 - x0) / nrow
        for c in range(nrow):
            cx = x0 + rw * (c + 0.5)
            jx = (_rnd(c, 7, seed) - 0.5) * 0.012
            y = y0
            i = 0
            guard = 0
            while y < y1 - 0.07 and guard < 400:
                guard += 1
                ln = slab * (0.80 + 0.42 * _rnd(c, i, seed + 9))
                if i == 0 and c % 2:
                    ln *= 0.55
                if y + ln > y1 - 0.018:
                    ln = y1 - 0.018 - y
                if ln < 0.10:
                    break
                cy = y + ln * 0.5
                if skip is None or not _inside(cx + jx, cy, skip):
                    obs.append(G.add_box("%s_%d_%d" % (tag, c, i),
                                         (rw - gap, ln - gap, SLAB_H),
                                         (cx + jx, cy, TOP - SLAB_H * 0.5),
                                         col, mats[(c * 3 + i) % len(mats)]))
                y += ln
                i += 1
    return obs


def build_street(col):
    """L street: wide apron on +Y, 2.1 m walk turning down +X, raised kerb."""
    out = []
    # dark threshold course across the head of the apron: reads as the edge of
    # the street and as the line where the walk turns
    out.extend(_join("SITE_PAVE_THRESHOLD",
                     _bond("SITE_PAVE_Thr", -KERB_IN, APRON_Y0, KERB_IN,
                           APRON_Y0 + 0.47, "y", 0.46, 0.44, DARK_COURSE, col,
                           seed=31)))
    # front apron
    out.extend(_join("SITE_PAVE_APRON",
                     _bond("SITE_PAVE_Apr", -KERB_IN, APRON_Y0 + 0.47, KERB_IN,
                           APRON_Y1, "x", 0.82, 0.44, STREET, col, seed=11)))
    # dark border course along the walk's inner edge
    out.extend(_join("SITE_PAVE_WBORDER",
                     _bond("SITE_PAVE_WB", WALK_X0, WALK_Y0, WALK_X0 + WALK_B,
                           WALK_Y1, "x", 0.30, 0.58, DARK_COURSE, col, seed=37)))
    # side walk down +X, slabs turned 90 degrees against the apron
    out.extend(_join("SITE_PAVE_WALK",
                     _bond("SITE_PAVE_Walk", WALK_X0 + WALK_B, WALK_Y0, WALK_X1,
                           WALK_Y1, "y", 0.92, 0.46, STREET, col, seed=23)))
    # plain deck field: big quiet flagstones, darker than the street; nothing
    # is laid under the hall where it could not be seen
    hole = (-4.62, -4.64, 4.62, 3.58)
    fld = _bond("SITE_PAVE_FldA", -KERB_IN, -KERB_IN, WALK_X0, APRON_Y0,
                "x", 1.52, 0.80, FIELD, col, seed=41, skip=hole)
    fld += _bond("SITE_PAVE_FldB", WALK_X0, -KERB_IN, KERB_IN, WALK_Y0,
                 "x", 1.52, 0.80, FIELD, col, seed=47, skip=hole)
    out.extend(_join("SITE_PAVE_FIELD", fld))

    # raised kerb at the deck rim: individual stones with joints, not one band,
    # because this edge is the only part of the base the high cameras see
    kerb = []
    kw = KERB_OUT - KERB_IN
    at = KERB_IN + kw * 0.5
    kz = 0.125
    run = at - (kw + 0.02) * 0.5
    for sy in (-1, 1):
        n = max(2, int(round((run * 2.0) / 0.95)))
        w = (run * 2.0) / n
        for i in range(n):
            kerb.append(G.add_box("SITE_KERB_Y%d_%d" % (sy, i),
                                  (w - 0.026, kw, kz),
                                  (-run + w * (i + 0.5), sy * at, TOP + 0.0175),
                                  col, ST_KERB if i % 2 == 0 else ST_KERB2))
    for sx in (-1, 1):
        n = max(2, int(round((run * 2.0) / 0.95)))
        w = (run * 2.0) / n
        for i in range(n):
            kerb.append(G.add_box("SITE_KERB_X%d_%d" % (sx, i),
                                  (kw, w - 0.026, kz),
                                  (sx * at, -run + w * (i + 0.5), TOP + 0.0175),
                                  col, ST_KERB2 if i % 2 == 0 else ST_KERB))
    for sx in (-1, 1):
        for sy in (-1, 1):
            kerb.append(G.add_box("SITE_KERB_C%d%d" % (sx, sy),
                                  (kw + 0.02, kw + 0.02, kz + 0.012),
                                  (sx * at, sy * at, TOP + 0.0175), col, ST_KERB))
    out.extend(_join("SITE_KERB", kerb))
    return out


# ------------------------------------------------------------------ beds
def _planter(tag, x, y, w, d, h, col, light=False):
    """Raised stone planter with an open top: four walls, rim ring, real soil."""
    obs = []
    wall = ST_PLANTER_RIM if light else ST_PLANTER
    rim = ST_KERB if light else ST_PLANTER_RIM
    t = 0.11
    base_h = 0.07
    obs.append(G.add_box(tag + "_base", (w, d, base_h),
                         (x, y, TOP + base_h * 0.5), col, ST_PLANTER_BASE))
    hh = h - base_h
    for sy in (-1, 1):
        obs.append(G.add_box("%s_wy%d" % (tag, sy), (w, t, hh),
                             (x, y + sy * (d * 0.5 - t * 0.5),
                              TOP + base_h + hh * 0.5), col, wall))
    for sx in (-1, 1):
        obs.append(G.add_box("%s_wx%d" % (tag, sx), (t, d - t * 2, hh),
                             (x + sx * (w * 0.5 - t * 0.5), y,
                              TOP + base_h + hh * 0.5), col, wall))
    # rim ring one course proud of the wall: catches a highlight along the top
    top = TOP + h
    rw = 0.078
    for sy in (-1, 1):
        obs.append(G.add_box("%s_ry%d" % (tag, sy), (w + 0.05, rw, 0.05),
                             (x, y + sy * (d * 0.5 - rw * 0.5 + 0.012),
                              top - 0.013), col, rim))
    for sx in (-1, 1):
        obs.append(G.add_box("%s_rx%d" % (tag, sx), (rw, d + 0.05 - rw * 2, 0.05),
                             (x + sx * (w * 0.5 - rw * 0.5 + 0.012), y,
                              top - 0.013), col, rim))
    obs.append(G.add_box(tag + "_soil", (w - t * 2 - 0.01, d - t * 2 - 0.01, 0.055),
                         (x, y, top - 0.048), col, G.P("bark")))
    return obs


# ------------------------------------------------------------------ planting
def _tree(tag, x, y, z0, s, seed, col):
    """Forked trunk, four visible branches, layered canopy of squashed spheres."""
    obs = []
    bark = G.P("bark")
    leaf = (G.P("leaf"), G.P("leaf"), G.P("leaf"), G.P("leaf_l"))
    p0 = Vector((x, y, z0))
    p1 = p0 + Vector((0.09 * s, -0.05 * s, 1.06 * s))
    p2 = p1 + Vector((0.15 * s, 0.08 * s, 0.56 * s))
    obs.append(_limb(tag + "_trunk0", p0, p1, 0.148 * s, 0.104 * s, col, bark, 9))
    obs.append(_limb(tag + "_trunk1", p1, p2, 0.104 * s, 0.080 * s, col, bark, 8))

    branches = (
        (0.60, 0.26, 0.62, 0.070, 0.036),
        (-0.64, -0.28, 0.74, 0.062, 0.031),
        (0.06, -0.70, 0.46, 0.048, 0.025),
        (-0.26, 0.54, 0.36, 0.032, 0.019),
    )
    tips = []
    for i, (dx, dy, dz, r0, r1) in enumerate(branches):
        p = p2 + Vector((dx, dy, dz)) * s
        obs.append(_limb("%s_br%d" % (tag, i), p2, p, r0 * s, r1 * s, col, bark, 6))
        tips.append(p)
        if i < 3:
            q = p + Vector((0.10 * (1 if i % 2 else -1), 0.10 * (i - 1),
                            0.20)) * s
            obs.append(_limb("%s_br%db" % (tag, i), p, q, r1 * s, r1 * 0.7 * s,
                             col, bark, 5))
            tips.append(q)

    # radii pulled in and offsets spread out on purpose: the canopy has to show
    # gaps between the pads so the branch silhouettes read through, instead of
    # fusing into one green mass
    clusters = (
        (tips[0], 0.54, 0),
        (tips[1], 0.47, 1),
        (tips[2], 0.40, 0),
        (tips[3], 0.30, 3),
        (tips[4], 0.26, 0),
        (p2 + Vector((0.06, 0.04, 0.98)) * s, 0.38, 1),
        (p2 + Vector((0.48, -0.20, 0.66)) * s, 0.28, 0),
        (p2 + Vector((-0.42, 0.30, 0.52)) * s, 0.25, 2),
    )
    for i, (c, r, m) in enumerate(clusters):
        ob = G.add_sphere("%s_can%d" % (tag, i), r * s, tuple(c), col, leaf[m],
                          segments=12, rings=8)
        # nearly circular in plan so the object bbox stays honest and the
        # canopy cannot fool the exported envelope
        ob.scale = (1.16, 1.10, 0.54 + 0.06 * _rnd(i, 1, seed))
        obs.append(ob)
    return obs


def _bamboo(tag, x, y, z0, n, seed, col):
    """Clump of stalks with ringed nodes, side branches and leaf blades."""
    obs = []
    stalk = G.P("bamboo")
    ring = G.P("leaf")
    leaf = (G.P("leaf_l"), G.P("leaf"), G.P("bamboo"))
    for i in range(n):
        ang = 2.0 * math.pi * i / n + 0.9 * _rnd(i, seed)
        rr = 0.07 + 0.30 * _rnd(i, seed, 3)
        sx = x + math.cos(ang) * rr
        sy = y + math.sin(ang) * rr
        h = 1.70 + 1.05 * _rnd(i, seed, 7)
        lean = 0.10 + 0.13 * _rnd(i, seed, 11)
        p0 = Vector((sx, sy, z0))
        p1 = p0 + Vector((math.cos(ang + 1.1) * lean,
                          math.sin(ang + 1.1) * lean, h))
        r = 0.024 + 0.009 * _rnd(i, seed, 17)
        obs.append(_limb("%s_st%d" % (tag, i), p0, p1, r, r * 0.60, col, stalk, 6))
        nn = max(3, int(h / 0.30))
        for k in range(1, nn):
            t = k / float(nn)
            obs.append(_limb("%s_nd%d_%d" % (tag, i, k),
                             _lerp(p0, p1, t - 0.007), _lerp(p0, p1, t + 0.007),
                             r * 1.26, r * 1.26, col, ring, 6))
        for b in range(3):
            tb = 0.54 + 0.16 * b
            bp = _lerp(p0, p1, tb)
            ba = ang + 2.0 * b + 0.55
            bl = 0.26 + 0.15 * _rnd(i, b, seed)
            tip = bp + Vector((math.cos(ba) * bl, math.sin(ba) * bl, 0.075))
            obs.append(_limb("%s_br%d_%d" % (tag, i, b), bp, tip,
                             r * 0.55, r * 0.26, col, stalk, 5))
            for lf in range(5):
                q = _lerp(bp, tip, 0.38 + 0.16 * lf)
                yaw = ba + (lf - 2.0) * 0.46 + 0.30 * _rnd(i, lf, seed + 2)
                pitch = 0.24 + 0.40 * _rnd(i, lf, seed + 3)
                roll = (_rnd(i, lf, seed + 4) - 0.5) * 0.7
                ln = 0.27 + 0.15 * _rnd(i, lf, seed + 5)
                ca, sa = math.cos(pitch), math.sin(pitch)
                cy_, sy_ = math.cos(yaw), math.sin(yaw)
                centre = q + Vector((ca * cy_, ca * sy_, -sa)) * (ln * 0.42)
                obs.append(G.add_box("%s_lf%d_%d_%d" % (tag, i, b, lf),
                                     (ln, 0.078, 0.009), tuple(centre), col,
                                     leaf[(i + lf) % 3],
                                     rot=(roll, pitch, yaw)))
    return obs


def _bonsai(tag, x, y, s, seed, col, z0=None):
    """Shallow pot, twisted trunk, flat cloud canopy."""
    obs = []
    z = TOP if z0 is None else z0
    w, d, h = 0.42 * s, 0.32 * s, 0.115 * s
    obs.append(G.add_box(tag + "_pot", (w, d, h), (x, y, z + h * 0.5), col,
                         ST_PLANTER_BASE))
    obs.append(G.add_box(tag + "_rim", (w * 1.07, d * 1.07, 0.020 * s),
                         (x, y, z + h * 0.98), col, ST_KERB))
    obs.append(G.add_box(tag + "_soil", (w * 0.84, d * 0.84, 0.022 * s),
                         (x, y, z + h * 1.03), col, G.P("bark")))
    base = Vector((x, y, z + h * 1.02))
    pts = (base,
           base + Vector((0.055, 0.030, 0.13)) * s,
           base + Vector((-0.020, 0.070, 0.26)) * s,
           base + Vector((0.070, 0.030, 0.38)) * s)
    rads = (0.040, 0.030, 0.022, 0.014)
    for i in range(3):
        obs.append(_limb("%s_tw%d" % (tag, i), pts[i], pts[i + 1],
                         rads[i] * s, rads[i + 1] * s, col, G.P("bark"), 6))
    pads = ((0.00, 0.00, 0.40, 0.150), (0.145, 0.075, 0.365, 0.105),
            (-0.130, 0.075, 0.355, 0.098), (0.035, -0.115, 0.375, 0.090),
            (0.055, 0.145, 0.330, 0.082))
    for i, (dx, dy, dz, r) in enumerate(pads):
        ob = G.add_sphere("%s_pad%d" % (tag, i), r * s,
                          tuple(base + Vector((dx, dy, dz)) * s), col,
                          G.P("leaf_l") if i % 2 else G.P("leaf"),
                          segments=10, rings=6)
        ob.scale = (1.30, 1.10, 0.42)
        ob.rotation_euler = (0.0, 0.0, _rnd(i, 5, seed) * math.pi)
        obs.append(ob)
    return obs


def _rocks(tag, x, y, col):
    """Small taihu style rock group: a few upright, half buried boulders."""
    obs = []
    body = (_st("rk1", 0.300), _st("rk2", 0.180), _st("rk3", 0.395))
    spec = ((0.00, 0.00, 0.26, 0.52, 0.72, 0.52, 0.62),
            (0.40, 0.14, 0.18, 0.34, 0.66, 0.58, 0.95),
            (-0.36, 0.18, 0.15, 0.28, 0.82, 0.62, 1.40),
            (0.14, -0.36, 0.13, 0.24, 0.64, 0.82, 0.70),
            (-0.20, -0.30, 0.11, 0.19, 0.78, 0.68, 1.90))
    for i, (dx, dy, dz, r, sx, sy, sz) in enumerate(spec):
        ob = G.add_sphere("%s_r%d" % (tag, i), r, (x + dx, y + dy, TOP + dz),
                          col, body[i % 3], segments=9, rings=6)
        ob.scale = (sx, sy, sz)
        ob.rotation_euler = (0.2 * i, 0.15 * i, 0.8 * i)
        obs.append(ob)
    for i, (dx, dy, r) in enumerate(((0.10, 0.30, 0.30), (-0.30, -0.12, 0.24))):
        ob = G.add_sphere("%s_moss%d" % (tag, i), r, (x + dx, y + dy, TOP + 0.016),
                          col, G.P("leaf"), segments=8, rings=4)
        ob.scale = (1.0, 1.0, 0.16)
        obs.append(ob)
    return obs


def build_vegetation(col):
    out = []
    # three beds: two raised planters on the deck edge, one back corner bed
    beds = _planter("SITE_BED_A", BED_RIGHT[0], BED_RIGHT[1],
                    BED_RIGHT[2], BED_RIGHT[3], BED_RIGHT[4], col)
    beds += _planter("SITE_BED_B", BED_LEFT[0], BED_LEFT[1],
                     BED_LEFT[2], BED_LEFT[3], BED_LEFT[4], col)
    beds += _planter("SITE_BED_C", BED_BACK[0], BED_BACK[1],
                     BED_BACK[2], BED_BACK[3], BED_BACK[4], col, light=True)
    out.extend(_join("SITE_BEDS", beds))
    soil_a = TOP + BED_RIGHT[4] - 0.020
    soil_b = TOP + BED_LEFT[4] - 0.020
    soil_c = TOP + BED_BACK[4] - 0.020

    ta = _join("SITE_TREE_A", _tree("SITE_TREE_A", TREE_A[0], TREE_A[1],
                                    soil_a - 0.02, 0.96, 3, col))
    tb = _join("SITE_TREE_B", _tree("SITE_TREE_B", TREE_B[0], TREE_B[1],
                                    soil_b - 0.02, 0.92, 8, col))
    for ob in ta + tb:
        G.shade_smooth(ob, math.radians(46))
    out.extend(ta)
    out.extend(tb)

    out.extend(_join("SITE_BAMBOO_A", _bamboo("SITE_BAMB_A", BAMBOO_A[0],
                                              BAMBOO_A[1], TOP, 10, 4, col)))
    out.extend(_join("SITE_BAMBOO_B", _bamboo("SITE_BAMB_B", BAMBOO_B[0],
                                              BAMBOO_B[1], TOP, 9, 12, col)))

    rocks = _rocks("SITE_ROCK", ROCKS_AT[0], ROCKS_AT[1], col)
    rj = _join("SITE_ROCKS", rocks)
    for ob in rj:
        G.shade_smooth(ob, math.radians(52))
    out.extend(rj)

    # back corner bed: a small bonsai plus ground cover
    back = _bonsai("SITE_BON_BED", BED_BACK[0] + 0.55, BED_BACK[1] + 0.10,
                   0.90, 21, col, z0=soil_c)
    for i, (dx, dy, r) in enumerate(((-0.55, 0.24, 0.26), (0.30, -0.28, 0.22))):
        ob = G.add_sphere("SITE_BEDC_moss%d" % i, r,
                          (BED_BACK[0] + dx, BED_BACK[1] + dy, soil_c + 0.01),
                          col, G.P("leaf_l"), segments=8, rings=4)
        ob.scale = (1.0, 1.0, 0.20)
        back.append(ob)
    out.extend(_join("SITE_BON_BED", back))

    for i, (bx, by, bs) in enumerate(BONSAI_AT):
        obs = [G.add_box("SITE_BON_PAD%d" % i, (0.60, 0.50, 0.052),
                         (bx, by, TOP + 0.026), col, ST_KERB)]
        obs.extend(_bonsai("SITE_BON_%d" % i, bx, by, bs, 30 + i, col))
        j = _join("SITE_BONSAI_%d" % i, obs)
        for ob in j:
            G.shade_smooth(ob, math.radians(52))
        out.extend(j)
    return out


# ------------------------------------------------------------------ props
def _lantern(tag, x, y, col):
    """Stone lantern: plinth, shaft, light housing with emissive glass, roof."""
    obs = []
    st = G.P("stone_l")
    dk = _st("lant_dk", 0.240)
    z = TOP
    obs.append(G.add_box(tag + "_b0", (0.58, 0.58, 0.09), (x, y, z + 0.045), col, dk))
    obs.append(G.add_box(tag + "_b1", (0.44, 0.44, 0.07), (x, y, z + 0.125), col, st))
    obs.append(_limb(tag + "_shaft", (x, y, z + 0.16), (x, y, z + 0.78),
                     0.075, 0.058, col, st, 8))
    obs.append(G.add_cyl(tag + "_mid", 0.19, 0.055, (x, y, z + 0.805), col, st,
                         segments=8))
    for i in range(4):
        a = math.pi * 0.25 + i * math.pi * 0.5
        obs.append(G.add_box("%s_p%d" % (tag, i), (0.055, 0.055, 0.30),
                             (x + math.cos(a) * 0.145, y + math.sin(a) * 0.145,
                              z + 0.985), col, st, rot_z=a))
        obs.append(G.add_box("%s_g%d" % (tag, i), (0.20, 0.014, 0.24),
                             (x + math.cos(a) * 0.140, y + math.sin(a) * 0.140,
                              z + 0.985), col, G.E("lamp_glass"),
                             rot_z=a + math.pi * 0.5))
    obs.append(G.add_box(tag + "_cap", (0.30, 0.30, 0.035), (x, y, z + 1.152), col, st))
    obs.append(G.add_cone(tag + "_roof", 0.36, 0.05, 0.20, (x, y, z + 1.27), col, dk,
                          segments=4))
    obs.append(G.add_sphere(tag + "_fin", 0.045, (x, y, z + 1.40), col, st,
                            segments=8, rings=6))
    return obs


def _guide_board(tag, x, y, col):
    """导览牌：双柱落地 + 木框纸面 + 小瓦顶，正面朝街道（+Y）。

    旧版只有两根柱子挑一块板，没有压顶，从侧面看像要倒；现在按真正的告示牌做：
    柱脚石垫、上压顶、纸面内嵌深色边框。

    2026-10-22：按要求去掉两根后斜撑（从侧面看像两根斜插的棍子，破坏立面整洁）。
    """
    obs = []
    z = TOP
    wood = G.P("wood")
    wood_m = G.P("wood_m")
    board_z = z + 1.10
    for i, dx in enumerate((-0.56, 0.56)):
        obs.append(G.add_box("%s_post%d" % (tag, i), (0.10, 0.10, 1.72),
                             (x + dx, y, z + 0.86), col, wood))
        obs.append(G.add_box("%s_foot%d" % (tag, i), (0.18, 0.18, 0.06),
                             (x + dx, y, z + 0.03), col, _st("prop_foot", 0.20)))
    # 板框（深色木） + 纸面（略内缩） + 墨线
    obs.append(G.add_box(tag + "_frame", (1.40, 0.085, 0.86),
                         (x, y, board_z), col, wood_m))
    obs.append(G.add_box(tag + "_paper", (1.24, 0.020, 0.70),
                         (x, y + 0.052, board_z), col, G.P("paper")))
    for i, (w, dz, dx) in enumerate(((0.62, 0.22, -0.16), (0.50, 0.02, -0.18),
                                     (0.66, -0.18, -0.14))):
        obs.append(G.add_box("%s_line%d" % (tag, i), (w, 0.014, 0.030),
                             (x + dx, y + 0.064, board_z + dz), col,
                             G.P("ink")))
    # 上压顶：一块小瓦檐，遮雨也把牌子压住
    obs.append(G.add_box(tag + "_cap", (1.56, 0.20, 0.07),
                         (x, y + 0.01, z + 1.60), col, wood_m))
    obs.append(G.add_box(tag + "_capTile", (1.60, 0.26, 0.05),
                         (x, y + 0.02, z + 1.655), col, G.P("tile_d")))
    return obs


def _easel(tag, x, y, col):
    """三脚画架，正面朝向街道（+Y）。

    旧版腿和画板都朝 +Y 前倾、后撑腿又往前顶，看起来像散架；现在按真实的
    画架受力来：两条前腿落地、上端向 -Y 后仰，后撑腿向后撑开，画板贴在前腿
    上、下沿有托木，纸面朝 +Y 面对观者。
    """
    obs = []
    z = TOP
    wood = G.P("wood")
    wood_m = G.P("wood_m")
    tilt = math.radians(9.0)
    leg_h = 1.30
    for i, dx in enumerate((-0.36, 0.36)):
        ob = G.add_box("%s_leg%d" % (tag, i), (0.06, 0.06, leg_h),
                       (x + dx, y + 0.10, z + leg_h * 0.5), col, wood)
        ob.rotation_euler = (tilt, 0.0, 0.0)
        obs.append(ob)
        # 脚垫，让画架确实站在地上
        obs.append(G.add_box("%s_foot%d" % (tag, i), (0.11, 0.16, 0.04),
                             (x + dx, y + 0.19, z + 0.02), col, wood_m))
    # 后撑腿：上端朝 -Y 撑开，与前腿在 1.05 m 处相交
    back = G.add_box(tag + "_back", (0.05, 0.05, 1.16), (x, y - 0.30, z + 0.55),
                     col, wood)
    back.rotation_euler = (math.radians(26.0), 0.0, 0.0)
    obs.append(back)
    # 横撑 + 斜撑
    obs.append(G.add_box(tag + "_bar", (0.80, 0.05, 0.05), (x, y - 0.02, z + 0.46),
                         col, wood_m))
    # 画板：面法线 +Y
    board = G.add_box(tag + "_board", (0.84, 0.035, 0.98),
                      (x, y + 0.055, z + 0.92), col, G.P("paper"))
    board.rotation_euler = (tilt, 0.0, 0.0)
    obs.append(board)
    # 画板下沿托木（挡住画纸往下滑）
    ledge = G.add_box(tag + "_ledge", (0.92, 0.12, 0.05),
                      (x, y + 0.075, z + 0.44), col, wood_m)
    ledge.rotation_euler = (tilt, 0.0, 0.0)
    obs.append(ledge)
    # 上压条
    top = G.add_box(tag + "_topclamp", (0.90, 0.07, 0.045),
                    (x, y + 0.055, z + 1.40), col, wood_m)
    top.rotation_euler = (tilt, 0.0, 0.0)
    obs.append(top)
    # 纸面墨迹：三笔，长短错落
    for k, (w, dz, dx) in enumerate(((0.44, 1.10, -0.02), (0.30, 0.94, 0.06),
                                     (0.38, 0.78, -0.04))):
        ob = G.add_box("%s_ink%d" % (tag, k), (w, 0.012, 0.055),
                       (x + dx, y + 0.078, z + dz), col, G.P("ink"))
        ob.rotation_euler = (tilt, 0.0, 0.0)
        obs.append(ob)
    return obs


def _display_stand(tag, x, y, col):
    """Small antique display stand (xiang ji): top, legs, stretcher frame."""
    obs = []
    z = TOP
    lac = G.P("lacquer")
    wood = G.P("wood_m")
    obs.append(G.add_box(tag + "_top", (0.56, 1.00, 0.055), (x, y, z + 0.605),
                         col, lac))
    obs.append(G.add_box(tag + "_apron", (0.44, 0.86, 0.05), (x, y, z + 0.552),
                         col, wood))
    for sx in (-1, 1):
        for sy in (-1, 1):
            obs.append(G.add_box("%s_leg%d%d" % (tag, sx, sy), (0.062, 0.062, 0.53),
                                 (x + sx * 0.225, y + sy * 0.42, z + 0.265),
                                 col, lac))
    for sy in (-1, 1):
        obs.append(G.add_box("%s_str%d" % (tag, sy), (0.46, 0.045, 0.045),
                             (x, y + sy * 0.42, z + 0.16), col, wood))
    for sx in (-1, 1):
        obs.append(G.add_box("%s_strs%d" % (tag, sx), (0.045, 0.80, 0.040),
                             (x + sx * 0.225, y, z + 0.13), col, wood))
    return obs


def build_street_props(col):
    out = []
    out.extend(_join("SITE_LANTERN",
                     _lantern("SITE_LANTERN", LANTERN_AT[0], LANTERN_AT[1], col)))
    # 导览牌（左侧、面向街道）保留；用户明确要删的是右侧那台画架。
    out.extend(_join("SITE_GUIDE",
                     _guide_board("SITE_GUIDE", GUIDE_AT[0], GUIDE_AT[1], col)))
    # out.extend(_join("SITE_EASEL",
    #                  _easel("SITE_EASEL", EASEL_AT[0], EASEL_AT[1], col)))
    out.extend(_join("SITE_STAND",
                     _display_stand("SITE_STAND", STAND_AT[0], STAND_AT[1], col)))
    # a bonsai on the stand ties the piece of furniture to a purpose
    j = _join("SITE_BON_STAND",
              _bonsai("SITE_BON_STAND", STAND_AT[0], STAND_AT[1], 0.86, 51, col,
                      z0=TOP + 0.632))
    for ob in j:
        G.shade_smooth(ob, math.radians(52))
    out.extend(j)
    return out


# ------------------------------------------------------------------ build
def build(col):
    base = build_base(col)
    street = build_street(col)
    veg = build_vegetation(col)
    props = build_street_props(col)
    obs = []
    obs.extend(base)
    obs.extend(street)
    obs.extend(veg)
    obs.extend(props)
    G.log("site tris: base=%d street=%d veg=%d props=%d total=%d"
          % (_tris(base), _tris(street), _tris(veg), _tris(props), _tris(obs)))
    G.log("site objects: %d" % len(obs))
    # audit: the plate must stay inside the 16 x 16 plan and inside
    # [BASE_BOT, deck + tallest planting]; props must touch BASE_TOP
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in obs:
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    G.log("site bbox x[%.3f %.3f] y[%.3f %.3f] z[%.3f %.3f]"
          % (lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))
    return obs
