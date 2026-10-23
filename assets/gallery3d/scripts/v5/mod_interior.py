"""V5 interior: gallery fit-out, stair, vitrine and the 15 artwork anchors.

Two things in here are a contract with the web layer and must not drift:

  1. GALWALL_<id> empties - display wall rectangles. Position, rotation and the
     custom props (floor / width / height / label) match
     frontend/src/features/heritage-gallery/data/gallery_layout.json, because the
     curation UI positions artworks in wall space (u/v).
  2. FRAME_F1_### / FRAME_F2_### empties - the 15 artwork anchors, again
     matching the same JSON (position / rotationY / size / u / v / wall_id).

Only one deliberate change is applied to the contract: the second-floor art
centres are lifted to Blender z 5.15 (1.55 m above the 3.60 floor) so the
picture centre sits in the 1.50-1.65 m viewing band.  Floor-1 stays at 1.75.

The rest is the gallery itself:
  * a fit-out layer inside the shell (display walls, skirting, cornices) so the
    picture frames are mounted on real boards and never float;
  * both floor finishes, the exposed second-floor structure and the F1 ceiling;
  * a switchback timber stair in the back-right corner with a real opening in
    the second-floor slab, stringers, handrail and balustrade;
  * a central stone-topped vitrine with a blue-and-white porcelain jar;
  * low display cases, benches and the second-floor L partition;
  * exposed roof timber (2 main beams along X, 7 secondaries along Y and ~48
    rafters) above the attic line, plus the octagonal caisson and its lantern.

The shell models its plinth, storey band, attic band and head beam as solid
boxes that span the whole plan, so from inside they read as floor/ceiling
slabs.  _neutralise_shell() turns each into a perimeter ring with the same
outer footprint: the exterior silhouette is untouched, the interior opens up.

All comments are ASCII on purpose (PowerShell round-trips corrupt non-ASCII
source); the Chinese labels are written as \\u escapes.
"""

from __future__ import annotations

import math

import bmesh
import bpy
from mathutils import Vector

import gal5 as G

# The opening schedule lives in the shell module, so a display wall can never
# be snapped across a window.  Imported defensively.
try:
    import mod_shell as S
except Exception:                                   # pragma: no cover
    S = None


# ============================================================ contract tables
# (id, floor, (x, y, z), rot_z, width, height, label)
WALL_ANCHORS = (
    ("f1-back", 1, (-0.5025, -4.1400, 1.9250), 0.0, 2.885, 3.350, "\u4e00\u5c42 \u00b7 \u540e\u5899"),
    ("f1-front-right", 1, (1.4725, 3.0400, 1.9250), math.pi, 0.945, 3.350, "\u4e00\u5c42 \u00b7 \u524d\u5899\u53f3\u6bb5"),
    ("f1-left-mid", 1, (-4.0400, -0.5500, 1.9250), -math.pi * 0.5, 1.750, 3.350, "\u4e00\u5c42 \u00b7 \u5de6\u5899\u4e2d\u6bb5"),
    ("f1-left-rear", 1, (-4.0400, -3.4575, 1.9250), -math.pi * 0.5, 1.365, 3.350, "\u4e00\u5c42 \u00b7 \u5de6\u5899\u540e\u6bb5"),
    ("f1-right-front", 1, (4.0400, 2.3575, 1.9250), math.pi * 0.5, 1.365, 3.350, "\u4e00\u5c42 \u00b7 \u53f3\u5899\u524d\u6bb5"),
    ("f1-right-mid", 1, (4.0400, -0.5500, 1.9250), math.pi * 0.5, 1.750, 3.350, "\u4e00\u5c42 \u00b7 \u53f3\u5899\u4e2d\u6bb5"),
    ("f2-back", 2, (0.0000, -4.1400, 5.0750), 0.0, 3.890, 2.950, "\u4e8c\u5c42 \u00b7 \u540e\u5899"),
    ("f2-left-front", 2, (-4.0400, 2.3575, 5.0750), -math.pi * 0.5, 1.365, 2.950, "\u4e8c\u5c42 \u00b7 \u5de6\u5899\u524d\u6bb5"),
    ("f2-left-mid", 2, (-4.0400, -0.5500, 5.0750), -math.pi * 0.5, 1.750, 2.950, "\u4e8c\u5c42 \u00b7 \u5de6\u5899\u4e2d\u6bb5"),
    ("f2-left-rear", 2, (-4.0400, -3.4575, 5.0750), -math.pi * 0.5, 1.365, 2.950, "\u4e8c\u5c42 \u00b7 \u5de6\u5899\u540e\u6bb5"),
    ("f2-right-front", 2, (4.0400, 2.3575, 5.0750), math.pi * 0.5, 1.365, 2.950, "\u4e8c\u5c42 \u00b7 \u53f3\u5899\u524d\u6bb5"),
    ("f2-right-mid", 2, (4.0400, -0.3375, 5.0750), math.pi * 0.5, 1.325, 2.950, "\u4e8c\u5c42 \u00b7 \u53f3\u5899\u4e2d\u6bb5"),
)

# (id, floor, index, (x, y, z), rot_z, wall_id, (w, h), u, v, label)
FRAME_ANCHORS = (
    ("FRAME_F1_001", 1, 1, (-1.3025, -4.1400, 1.7500), 0.0, "f1-back", (1.00, 0.80), 0.2227, 0.4478, "\u4e00\u5c42 \u00b7 \u540e\u5899 \u00b7 \u5de6"),
    ("FRAME_F1_002", 1, 2, (-0.0525, -4.1400, 1.7500), 0.0, "f1-back", (1.00, 0.80), 0.6560, 0.4478, "\u4e00\u5c42 \u00b7 \u540e\u5899 \u00b7 \u53f3"),
    ("FRAME_F1_003", 1, 3, (-4.0400, -0.5500, 1.7500), -math.pi * 0.5, "f1-left-mid", (0.86, 1.14), 0.5000, 0.4478, "\u4e00\u5c42 \u00b7 \u5de6\u5899 \u00b7 \u4e2d"),
    ("FRAME_F1_004", 1, 4, (-4.0400, -3.3475, 1.7500), -math.pi * 0.5, "f1-left-rear", (0.86, 1.14), 0.4194, 0.4478, "\u4e00\u5c42 \u00b7 \u5de6\u5899 \u00b7 \u540e"),
    ("FRAME_F1_005", 1, 5, (4.0400, -0.5500, 1.7500), math.pi * 0.5, "f1-right-mid", (0.86, 1.14), 0.5000, 0.4478, "\u4e00\u5c42 \u00b7 \u53f3\u5899 \u00b7 \u4e2d"),
    ("FRAME_F1_006", 1, 6, (4.0400, 2.4675, 1.7500), math.pi * 0.5, "f1-right-front", (0.86, 1.14), 0.5806, 0.4478, "\u4e00\u5c42 \u00b7 \u53f3\u5899 \u00b7 \u524d"),
    ("FRAME_F1_007", 1, 7, (1.4725, 3.0400, 1.7200), math.pi, "f1-front-right", (0.84, 0.68), 0.5000, 0.4388, "\u4e00\u5c42 \u00b7 \u524d\u5899 \u00b7 \u5165\u53e3"),
    ("FRAME_F2_001", 2, 1, (-1.3200, -4.1400, 5.1500), 0.0, "f2-back", (0.82, 0.66), 0.1607, 0.4915, "\u4e8c\u5c42 \u00b7 \u540e\u5899 \u00b7 \u5de6"),
    ("FRAME_F2_002", 2, 2, (0.0000, -4.1400, 5.1500), 0.0, "f2-back", (1.25, 0.92), 0.5000, 0.4915, "\u4e8c\u5c42 \u00b7 \u540e\u5899 \u00b7 \u4e2d"),
    ("FRAME_F2_003", 2, 3, (1.3200, -4.1400, 5.1500), 0.0, "f2-back", (0.82, 0.66), 0.8393, 0.4915, "\u4e8c\u5c42 \u00b7 \u540e\u5899 \u00b7 \u53f3"),
    ("FRAME_F2_004", 2, 4, (-4.0400, -0.5500, 5.1500), -math.pi * 0.5, "f2-left-mid", (0.85, 1.10), 0.5000, 0.4915, "\u4e8c\u5c42 \u00b7 \u5de6\u5899 \u00b7 \u4e2d"),
    ("FRAME_F2_005", 2, 5, (-4.0400, -3.3475, 5.1500), -math.pi * 0.5, "f2-left-rear", (0.85, 1.10), 0.4194, 0.4915, "\u4e8c\u5c42 \u00b7 \u5de6\u5899 \u00b7 \u540e"),
    ("FRAME_F2_006", 2, 6, (-4.0400, 2.2475, 5.1500), -math.pi * 0.5, "f2-left-front", (0.85, 1.10), 0.5806, 0.4915, "\u4e8c\u5c42 \u00b7 \u5de6\u5899 \u00b7 \u524d"),
    ("FRAME_F2_007", 2, 7, (4.0400, -0.4975, 5.1500), math.pi * 0.5, "f2-right-mid", (0.85, 1.10), 0.3792, 0.4915, "\u4e8c\u5c42 \u00b7 \u53f3\u5899 \u00b7 \u4e2d"),
    ("FRAME_F2_008", 2, 8, (4.0400, 2.4675, 5.1500), math.pi * 0.5, "f2-right-front", (0.85, 1.10), 0.5806, 0.4915, "\u4e8c\u5c42 \u00b7 \u53f3\u5899 \u00b7 \u524d"),
)


# ============================================================ shell probes
ROOM = {}
FLOOR1_Z = 0.261        # finish level: 0.25 contract + floor build-up
PANEL_T = 0.045


def _place(cx, cy, rot, lu, lv):
    """Local (u, v) offset of a rotated part -> world (x, y)."""
    ca, sa = math.cos(rot), math.sin(rot)
    return (cx + ca * lu - sa * lv, cy + sa * lu + ca * lv)


def _bounds(prefix, exact=None):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    found = False
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not ob.name.startswith(prefix):
            continue
        if exact is not None and ob.name != exact:
            continue
        found = True
        for corner in ob.bound_box:
            w = ob.matrix_world @ Vector(corner)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    return (lo, hi) if found else None


def _probe_rooms():
    """Read the actual inner faces of the shell so the fit-out cannot float."""
    f1 = dict(x0=-3.96, x1=3.96, y0=-4.06, y1=2.96)
    f2 = dict(x0=-3.80, x1=3.80, y0=-3.90, y1=2.80)
    for name, room, key, mode in (
            ("WALL_F1_Back", f1, "y0", "max"),
            ("WALL_F1_Front", f1, "y1", "min"),
            ("WALL_F1_Side-1", f1, "x0", "max"),
            ("WALL_F1_Side1", f1, "x1", "min"),
            ("WALL_F2_Back", f2, "y0", "max"),
            ("WALL_F2_Sill", f2, "y1", "min"),
            ("WALL_F2_Side-1", f2, "x0", "max"),
            ("WALL_F2_Side1", f2, "x1", "min")):
        box = _bounds(name, exact="WALL_F2_Sill" if name == "WALL_F2_Sill" else None)
        if not box:
            continue
        axis = 1 if key.startswith("y") else 0
        room[key] = box[1][axis] if mode == "max" else box[0][axis]
    ROOM["f1"] = f1
    ROOM["f2"] = f2
    G.log("interior: room f1 x %.2f..%.2f y %.2f..%.2f" %
          (f1["x0"], f1["x1"], f1["y0"], f1["y1"]))
    G.log("interior: room f2 x %.2f..%.2f y %.2f..%.2f" %
          (f2["x0"], f2["x1"], f2["y0"], f2["y1"]))


def _roof_under(x, y):
    """Underside of the main roof slab at a world (x, y).

    Uses the roof module's own surface so the attic walls, the caisson hangers
    and the soffit keep tracking the 歇山 surface (and its 生起 lift) instead of
    a separate hip profile that drifted away from it.
    """
    try:
        import mod_roof
        z = mod_roof.main_roof_z(x, y)
    except Exception:
        z = G.roof_point(x, y - G.BCY, G.ROOF_W, G.ROOF_D,
                         G.ROOF_MAIN_EAVE, G.RIDGE_Z, lift=0.30, k=0.56)
    return z - 0.22


def _open_roof_interior():
    """Clear the roof faces that close over the attic.

    The skirt-roof tile courses and the roof soffit board are modelled across
    the whole plan, so from below they read as a tent plus a ceiling at z 6.8 /
    6.95 and hide the ridge.  Only faces that sit inside the attic footprint
    and below the main roof slab are dropped: every exterior face, every eave
    and the whole main roof slab stay untouched.

    Returns True once the roof objects exist (even if nothing needed cutting),
    so the caller knows the pass is finished.
    """
    rect = (ATTIC["x"] + 0.02, ATTIC["y0"] + 0.02, ATTIC["y1"] - 0.02)
    # cut a little wider than the attic walls (but inside the shell's wall
    # thickness) so the open ends of the cut tile ribs stay out of sight
    cut = (4.14, -4.24, 3.14)
    seen = False
    for name in ("ROOF_SKIRT", "ROOF_MAIN"):
        ob = bpy.data.objects.get(name)
        if ob is None or ob.type != "MESH":
            continue
        seen = True
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        kill = []
        for face in bm.faces:
            w = ob.matrix_world @ face.calc_center_median()
            if abs(w.x) < cut[0] and cut[1] < w.y < cut[2] and w.z < 7.30:
                kill.append(face)
        if kill:
            bmesh.ops.delete(bm, geom=kill, context="FACES")
            bm.to_mesh(ob.data)
            G.log("interior: cleared %d interior faces of %s" % (len(kill), name))
        bm.free()
    return seen


ROOF_DONE = [False]


def _roof_cleanup(*_args):
    """Handler body: the roof module builds after this module, so the trim has
    to happen just before the file is saved or rendered."""
    if ROOF_DONE[0]:
        return
    try:
        if _open_roof_interior():
            ROOF_DONE[0] = True
    except Exception as exc:                      # pragma: no cover
        G.log("interior: roof clean-up failed (%s)" % exc)


def _install_roof_hooks():
    for tag in ("save_pre", "render_pre"):
        handlers = getattr(bpy.app.handlers, tag, None)
        if handlers is None:
            continue
        if _roof_cleanup not in list(handlers):
            handlers.append(_roof_cleanup)


# ============================================================ small helpers
def free_rects(rect, holes):
    """Split an axis-aligned rectangle around a list of holes."""
    x0, x1, y0, y1 = rect
    if x1 - x0 < 1e-4 or y1 - y0 < 1e-4:
        return []
    xs = {x0, x1}
    for h in holes:
        for v in (h[0], h[1]):
            if x0 + 1e-5 < v < x1 - 1e-5:
                xs.add(v)
    cuts = sorted(xs)
    out = []
    for a, b in zip(cuts, cuts[1:]):
        xm = (a + b) * 0.5
        spans = [(y0, y1)]
        for hx0, hx1, hy0, hy1 in holes:
            if not (hx0 < xm < hx1):
                continue
            nxt = []
            for s0, s1 in spans:
                if hy1 <= s0 + 1e-6 or hy0 >= s1 - 1e-6:
                    nxt.append((s0, s1))
                    continue
                if s0 < hy0:
                    nxt.append((s0, hy0))
                if hy1 < s1:
                    nxt.append((hy1, s1))
            spans = nxt
        for s0, s1 in spans:
            if s1 - s0 > 1e-4:
                out.append((a, b, s0, s1))
    return out


def _slab(name, rect, z0, z1, holes, col, mat):
    obs = []
    for i, (a, b, c, d) in enumerate(free_rects(rect, holes)):
        obs.append(G.add_box("%s_%d" % (name, i), (b - a, d - c, z1 - z0),
                             ((a + b) * 0.5, (c + d) * 0.5, (z0 + z1) * 0.5),
                             col, mat))
    return obs


def _planked(name, rect, z_top, thick, pitch, holes, col, mat):
    obs = []
    idx = 0
    for (a, b, c, d) in free_rects(rect, holes):
        y = c
        while y < d - 1e-4:
            yy = min(y + pitch, d)
            if yy - y > 0.06:
                obs.append(G.add_box(
                    "%s_%d" % (name, idx),
                    (b - a - 0.012, yy - y - 0.012, thick),
                    ((a + b) * 0.5, (y + yy) * 0.5, z_top - thick * 0.5),
                    col, mat))
                idx += 1
            y = yy
    return obs


def _strip(name, axis, at, u0, u1, z_of_u, inward, col, mat, n=14, z0=6.55):
    """Wall strip whose top edge follows a function of u (attic walls)."""
    verts, faces = [], []
    for i in range(n + 1):
        u = u0 + (u1 - u0) * i / n
        zt = max(z_of_u(u), z0 + 0.05)
        if axis == "y":
            verts.append((u, at, z0))
            verts.append((u, at, zt))
        else:
            verts.append((at, u, z0))
            verts.append((at, u, zt))
    for i in range(n):
        a = 2 * i
        if axis == "y":
            quad = (a, a + 1, a + 3, a + 2) if inward > 0 else (a + 2, a + 3, a + 1, a)
        else:
            quad = (a + 2, a + 3, a + 1, a) if inward > 0 else (a, a + 1, a + 3, a + 2)
        faces.append(quad)
    return G.add_mesh(name, verts, faces, col, mat)


def _y_beam(name, x, y0, y1, w, h, gap, col, mat, samples=9):
    """Beam along Y that hugs the roof pitch (rafters and secondaries)."""
    verts, faces = [], []
    for i in range(samples + 1):
        y = y0 + (y1 - y0) * i / samples
        zc = _roof_under(x, y) - gap - h * 0.5
        hw = w * 0.5
        verts.extend([(x - hw, y, zc - h * 0.5), (x + hw, y, zc - h * 0.5),
                      (x + hw, y, zc + h * 0.5), (x - hw, y, zc + h * 0.5)])
    for i in range(samples):
        a = 4 * i
        b = 4 * (i + 1)
        for k in range(4):
            k2 = (k + 1) % 4
            faces.append((a + k, a + k2, b + k2, b + k))
    faces.append((0, 3, 2, 1))
    last = 4 * samples
    faces.append((last, last + 1, last + 2, last + 3))
    return G.add_mesh(name, verts, faces, col, mat)


def _lathe(name, profile, cx, cy, z0, col, mat, seg=24):
    """Revolved profile from stacked (radius, height) pairs."""
    verts, faces = [], []
    rings = []
    for (r, dz) in profile:
        ring = []
        for i in range(seg):
            a = 2.0 * math.pi * i / seg
            ring.append(len(verts))
            verts.append((cx + math.cos(a) * r, cy + math.sin(a) * r, z0 + dz))
        rings.append(ring)
    for j in range(len(rings) - 1):
        ra, rb = rings[j], rings[j + 1]
        for i in range(seg):
            i2 = (i + 1) % seg
            faces.append((ra[i], ra[i2], rb[i2], rb[i]))
    faces.append(tuple(reversed(rings[0])))
    faces.append(tuple(rings[-1]))
    return G.shade_smooth(G.add_mesh(name, verts, faces, col, mat))


# ============================================================ shell clean-up
def _neutralise_shell():
    """Turn the shell's full-plan boxes into perimeter rings.

    The plinth, the storey band, the attic band and the head beam are modelled
    as solid boxes across the whole plan; from inside they read as floor and
    ceiling slabs and they would seal the stairwell and the view to the ridge.
    Each keeps its outer footprint, so every exterior view is unchanged.
    """
    hollow = (("WALL_Plinth", 0.34), ("WALL_Band", 0.30),
              ("WALL_Attic", 0.20), ("WALL_HeadBeam", 0.34))
    for name, band in hollow:
        ob = bpy.data.objects.get(name)
        if ob is None or ob.type != "MESH" or len(ob.data.polygons) != 6:
            continue
        lo = Vector((1e9, 1e9, 1e9))
        hi = Vector((-1e9, -1e9, -1e9))
        for vert in ob.data.vertices:
            for i in range(3):
                lo[i] = min(lo[i], vert.co[i])
                hi[i] = max(hi[i], vert.co[i])
        if (hi.x - lo.x) < 5.0 or (hi.y - lo.y) < 4.5:
            continue
        bw = band
        boxes = ((lo.x, lo.x + bw, lo.y, hi.y),
                 (hi.x - bw, hi.x, lo.y, hi.y),
                 (lo.x + bw, hi.x - bw, lo.y, lo.y + bw),
                 (lo.x + bw, hi.x - bw, hi.y - bw, hi.y))
        verts, faces = [], []
        for (x0, x1, y0, y1) in boxes:
            base = len(verts)
            verts.extend([(x0, y0, lo.z), (x1, y0, lo.z), (x1, y1, lo.z),
                          (x0, y1, lo.z), (x0, y0, hi.z), (x1, y0, hi.z),
                          (x1, y1, hi.z), (x0, y1, hi.z)])
            faces.extend([(base, base + 3, base + 2, base + 1),
                          (base + 4, base + 5, base + 6, base + 7),
                          (base, base + 1, base + 5, base + 4),
                          (base + 1, base + 2, base + 6, base + 5),
                          (base + 2, base + 3, base + 7, base + 6),
                          (base + 3, base, base + 4, base + 7)])
        old = ob.data
        new = bpy.data.meshes.new(name + "_Ring")
        new.from_pydata(verts, [], faces)
        new.update()
        for slot in old.materials:
            new.materials.append(slot)
        ob.data = new
        bpy.data.meshes.remove(old)
        G.log("interior: hollowed %s to a %.2f m band" % (name, band))
    ring = bpy.data.objects.get("WALL_F2_Ring")
    if ring is not None:
        bpy.data.objects.remove(ring, do_unlink=True)
        G.log("interior: dropped WALL_F2_Ring (rebuilt with a stair opening)")


# ============================================================ anchors
def _empty(col, name, loc, rot_z, props):
    ob = bpy.data.objects.new(name, None)
    col.objects.link(ob)
    ob.empty_display_type = "PLAIN_AXES"
    ob.empty_display_size = 0.22
    ob.location = Vector(loc)
    ob.rotation_euler = (0.0, 0.0, rot_z)
    for key, val in props.items():
        ob[key] = val
    return ob


def _build_anchors(col):
    obs = []
    for (wid, floor, loc, rot_z, width, height, label) in WALL_ANCHORS:
        obs.append(_empty(col, "GALWALL_" + wid, loc, rot_z,
                          {"floor": floor, "width": float(width),
                           "height": float(height), "label": label}))
    for (fid, floor, _idx, loc, rot_z, wall_id, size, u, v, label) in FRAME_ANCHORS:
        obs.append(_empty(col, fid, loc, rot_z,
                          {"frame_size": [float(size[0]), float(size[1])],
                           "wall_id": wall_id, "u": float(u), "v": float(v),
                           "label": label}))
    G.log("interior: anchors walls=%d frames=%d" %
          (len(WALL_ANCHORS), len(FRAME_ANCHORS)))
    return obs


# ============================================================ wall fit-out
def _windows(floor, wall_id):
    """Opening intervals (u) on a wall, straight from the shell schedule."""
    if S is None:
        return []
    if floor == 1:
        table = S.F1_BACK_W if wall_id == "f1-back" else S.F1_SIDE_W
    else:
        table = S.F2_BACK_W if wall_id == "f2-back" else S.F2_SIDE_W
    return [(uc - uw * 0.5, uc + uw * 0.5) for (uc, uw, _z0, _z1) in table]


def _wall_meta(floor, wall_id):
    room = ROOM["f1"] if floor == 1 else ROOM["f2"]
    if wall_id in ("f1-back", "f2-back"):
        return dict(axis="y", face=room["y0"], inward=1.0,
                    u0=room["x0"], u1=room["x1"],
                    wins=_windows(floor, wall_id))
    if wall_id == "f1-front-right":
        return dict(axis="y", face=room["y1"], inward=-1.0,
                    u0=room["x0"], u1=room["x1"], wins=[])
    side = "left" in wall_id
    return dict(axis="x", face=(room["x0"] if side else room["x1"]),
                inward=(1.0 if side else -1.0),
                u0=room["y0"], u1=room["y1"], wins=_windows(floor, wall_id))


def _panel_extent(meta, u_lo, u_hi):
    """Grow a display panel until it never cuts through a window opening."""
    lo = max(u_lo - 0.10, meta["u0"] + 0.02)
    hi = min(u_hi + 0.10, meta["u1"] - 0.02)
    for _ in range(8):
        changed = False
        for (w0, w1) in meta["wins"]:
            if hi <= w0 + 1e-3 or lo >= w1 - 1e-3:
                continue
            if lo <= w0 + 1e-3 and hi >= w1 - 1e-3:
                continue
            lo = min(lo, w0)
            hi = max(hi, w1)
            changed = True
        if not changed:
            break
    return max(lo, meta["u0"] + 0.02), min(hi, meta["u1"] - 0.02)


def _display_panel(col, name, meta, lo, hi, z0, z1, thick, mat_face):
    """Face board + dark wood border + fine gold line, standing on the wall."""
    obs = []
    axis, face, inward = meta["axis"], meta["face"], meta["inward"]
    cu = (lo + hi) * 0.5
    length = hi - lo
    zc = (z0 + z1) * 0.5
    h = z1 - z0

    def part(tag, du, dn, dz, u, n, z, mat):
        if axis == "y":
            dims, loc = (du, dn, dz), (u, n, z)
        else:
            dims, loc = (dn, du, dz), (n, u, z)
        return G.add_box(name + tag, dims, loc, col, mat)

    obs.append(part("_Face", length, thick, h, cu,
                    face + inward * thick * 0.5, zc, mat_face))
    bw = 0.085
    nb = face + inward * (thick + 0.012)
    for s in (-1, 1):
        obs.append(part("_Stile%d" % s, bw, 0.026, h,
                        cu + s * (length * 0.5 - bw * 0.5), nb, zc, G.P("wood")))
        obs.append(part("_Rail%d" % s, length, 0.026, bw, cu, nb,
                        zc + s * (h * 0.5 - bw * 0.5), G.P("wood")))
    ng = face + inward * (thick + 0.020)
    for s in (-1, 1):
        obs.append(part("_GoldV%d" % s, 0.018, 0.008, h - bw * 2.0 - 0.03,
                        cu + s * (length * 0.5 - bw - 0.016), ng, zc, G.P("gold")))
        obs.append(part("_GoldH%d" % s, length - bw * 2.0 - 0.03, 0.008, 0.018,
                        cu, ng, zc + s * (h * 0.5 - bw - 0.016), G.P("gold")))
    return obs


def _panel_face():
    return G.mat("M_panel_face", (0.800, 0.720, 0.578), rough=0.94)


def _floor_wood(floor):
    if floor == 1:
        return G.mat("M_floor1", (0.238, 0.136, 0.076), rough=0.60)
    return G.mat("M_floor2", (0.300, 0.182, 0.104), rough=0.58)


def _panel_thick(wall_id):
    return 0.12 if wall_id == "f1-front-right" else PANEL_T


def _build_fitout(col):
    """Display walls, skirting boards and cornices on both storeys."""
    obs = []
    frame_span = {}
    for (fid, floor, idx, loc, rot, wall_id, size, u, v, label) in FRAME_ANCHORS:
        meta = _wall_meta(floor, wall_id)
        # u runs along the wall: X on the front/back walls, Y on the side walls
        a = loc[0] if meta["axis"] == "y" else loc[1]
        cur = frame_span.get(wall_id, (1e9, -1e9))
        frame_span[wall_id] = (min(cur[0], a - size[0] * 0.5),
                               max(cur[1], a + size[0] * 0.5))
    for (wid, floor, loc, _rot, width, _height, _label) in WALL_ANCHORS:
        meta = _wall_meta(floor, wid)
        z0 = (G.F1 + 0.15) if floor == 1 else (G.F2 + 0.02)
        z1 = 3.28 if floor == 1 else 6.30
        if meta["axis"] == "y":
            u_lo, u_hi = loc[0] - width * 0.5, loc[0] + width * 0.5
        else:
            u_lo, u_hi = loc[1] - width * 0.5, loc[1] + width * 0.5
        if wid == "f1-front-right":
            lo, hi = loc[0] - 0.46, loc[0] + 0.60
            obs.extend(_display_panel(col, "INT_PANEL_" + wid, meta, lo, hi,
                                      G.F1 + 0.02, 2.92, 0.12, _panel_face()))
            G.log("interior: panel %-16s screen u %.3f..%.3f" % (wid, lo, hi))
            continue
        lo, hi = _panel_extent(meta, u_lo, u_hi)
        span = frame_span.get(wid)
        if span:
            lo = min(lo, span[0] - 0.07)
            hi = max(hi, span[1] + 0.07)
        lo = max(lo, meta["u0"] + 0.02)
        hi = min(hi, meta["u1"] + 0.16)
        obs.extend(_display_panel(col, "INT_PANEL_" + wid, meta, lo, hi,
                                  z0, z1, _panel_thick(wid), _panel_face()))
        G.log("interior: panel %-16s u %.3f..%.3f (rect %.3f..%.3f)"
              % (wid, lo, hi, u_lo, u_hi))

    # continuous skirting and cornice so the panels sit inside a base line
    for floor in (1, 2):
        room = ROOM["f1"] if floor == 1 else ROOM["f2"]
        zf = FLOOR1_Z if floor == 1 else G.F2
        ztop = 3.28 if floor == 1 else 6.30
        for axis, at, inward, u0, u1 in (
                ("y", room["y0"], 1.0, room["x0"], room["x1"]),
                ("y", room["y1"], -1.0, room["x0"], room["x1"]),
                ("x", room["x0"], 1.0, room["y0"], room["y1"]),
                ("x", room["x1"], -1.0, room["y0"], room["y1"])):
            n = at + inward * 0.028
            ln = u1 - u0
            cu = (u0 + u1) * 0.5
            tag = "F%d_%s_%d" % (floor, axis, int(at * 100))
            if axis == "y":
                sdims, sloc = (ln, 0.058, 0.15), (cu, n, zf + 0.075)
                cdims, cloc = (ln, 0.075, 0.10), (cu, at + inward * 0.038, ztop + 0.05)
            else:
                sdims, sloc = (0.058, ln, 0.15), (n, cu, zf + 0.075)
                cdims, cloc = (0.075, ln, 0.10), (at + inward * 0.038, cu, ztop + 0.05)
            obs.append(G.add_box("INT_SKIRT_" + tag, sdims, sloc, col, G.P("stone_d")))
            obs.append(G.add_box("INT_CORNICE_" + tag, cdims, cloc, col, G.P("wood")))
    return obs


# ============================================================ floors
def _case_glass():
    return G.mat("M_case_glass", (0.90, 0.94, 0.94), rough=0.05, alpha=0.10)


def _canvas_mat():
    return G.mat("M_canvas", (0.430, 0.386, 0.318), rough=0.92)


def _build_f1_floor(col):
    room = ROOM["f1"]
    rect = (room["x0"], room["x1"], room["y0"], room["y1"])
    obs = _planked("INT_F1_BOARD", rect, FLOOR1_Z, 0.016, 0.36, [], col,
                   _floor_wood(1))
    obs.append(G.add_box("INT_F1_CarpetEdge", (3.10, 2.30, 0.006),
                         (0.0, G.BCY, FLOOR1_Z + 0.003), col, G.P("wood")))
    obs.append(G.add_box("INT_F1_Carpet", (2.96, 2.16, 0.006),
                         (0.0, G.BCY, FLOOR1_Z + 0.009), col,
                         G.mat("M_carpet2", (0.318, 0.098, 0.086), rough=0.96)))
    return obs


def _build_f2_floor(col):
    """Floor plate with the stair opening, exposed joists, F1 ceiling."""
    obs = []
    room = ROOM["f2"]
    room1 = ROOM["f1"]
    holes = [(0.56, room["x1"], -2.86, -1.76),
             (2.00, room["x1"], room["y0"], -2.86)]
    rect = (room["x0"], room["x1"], room["y0"], room["y1"])
    hole1 = [(0.29, room1["x1"], room1["y0"], -1.76)]

    # slab build-up: exposed joists / plaster soffit / deck / boards
    y = room1["y0"] + 0.20
    idx = 0
    while y < room1["y1"] - 0.10:
        for (a, b, c, d) in free_rects((room1["x0"], room1["x1"], y - 0.055, y + 0.055),
                                       hole1):
            obs.append(G.add_box("INT_F1_JOIST_%d" % idx, (b - a, d - c, 0.16),
                                 ((a + b) * 0.5, (c + d) * 0.5, G.F2 - 0.200),
                                 col, G.P("wood")))
            idx += 1
        y += 0.55
    # 彻上明造：不抹平顶。二层楼板底只保留外露的搁栅与铺板底面，
    # 一层抬头看到的是木构而不是一块白色天花（用户明确要求不要天花）。
    # 之前这里有一层 plaster_d 的 INT_F1_SOFFIT，正是那层白顶把梁架全挡住了。
    obs += _slab("INT_F2_SLAB", rect, G.F2 - 0.030, G.F2 - 0.014, holes, col,
                 G.P("wood_m"))
    obs += _planked("INT_F2_BOARD", rect, G.F2, 0.014, 0.36, holes, col,
                 _floor_wood(2))

    # finished edge of the opening, and of the F1 ceiling opening
    for (name, x0, y0, x1, y1, z0, z1) in (
            ("INT_F2_EDGE_S", 0.56, -1.79, room["x1"], -1.76, G.F2 - 0.20, G.F2),
            ("INT_F2_EDGE_W", 0.53, -2.86, 0.56, -1.79, G.F2 - 0.20, G.F2),
            ("INT_F2_EDGE_M", 0.56, -2.89, 2.00, -2.86, G.F2 - 0.20, G.F2),
            ("INT_F2_EDGE_E", 1.97, room["y0"], 2.00, -2.86, G.F2 - 0.20, G.F2),
            ("INT_F1_EDGE_W", 0.26, room1["y0"], 0.29, -1.76, G.F2 - 0.21, G.F2 - 0.18),
            ("INT_F1_EDGE_S", 0.26, -1.76, room1["x1"], -1.73, G.F2 - 0.21, G.F2 - 0.18)):
        obs.append(G.add_box(name, (x1 - x0, y1 - y0, z1 - z0),
                             ((x0 + x1) * 0.5, (y0 + y1) * 0.5, (z0 + z1) * 0.5),
                             col, G.P("wood")))
    return obs


# ============================================================ stair
SR = (G.F2 - G.F1) / 18.0
ST = 0.27
N1 = 9
N2 = 8
ST_X0 = 0.29
ST_LAND0 = ST_X0 + N1 * ST
ST_LAND1 = 3.72
ST_Z = G.F1 + N1 * SR
LANE1 = (-3.96, -2.86)
LANE2 = (-2.86, -1.76)
ST_XTOP = ST_LAND0 - N2 * ST


def _balustrade(col, name, p0, p1, z0, slope=None):
    """Posts, top rail and bottom rail along a straight run.

    With `slope` = (x_a, z_a, x_b, z_b) the posts stand on the stair line and
    the top rail follows it 0.95 m above.
    """
    obs = []
    x0, y0 = p0
    x1, y1 = p1
    ln = math.hypot(x1 - x0, y1 - y0)
    if ln < 0.05:
        return obs
    n = max(2, int(round(ln / 0.58)))
    H = 0.95
    if slope:
        ax, az, bx, bz = slope
        for i in range(n + 1):
            t = i / n
            zz = az + (bz - az) * t
            if i == 0 or i == n:
                pass
            obs.append(G.add_box("%s_P%d" % (name, i), (0.055, 0.055, H),
                                 (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t,
                                  zz + H * 0.5), col, G.P("wood")))
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            xa = x0 + (x1 - x0) * t0
            xb = x0 + (x1 - x0) * t1
            za = az + (bz - az) * t0 + H
            zb = az + (bz - az) * t1 + H
            seg = math.hypot(xb - xa, zb - za) + 0.04
            sang = math.atan2(zb - za, xb - xa)
            obs.append(G.add_box("%s_RT%d" % (name, i), (seg, 0.06, 0.06),
                                 ((xa + xb) * 0.5, (y0 + y1) * 0.5,
                                  (za + zb) * 0.5), col, G.P("wood_m"),
                                 rot=(0.0, -sang, 0.0)))
        return obs
    ang = math.atan2(y1 - y0, x1 - x0)
    cx, cy = (x0 + x1) * 0.5, (y0 + y1) * 0.5
    for i in range(n + 1):
        t = i / n
        obs.append(G.add_box("%s_P%d" % (name, i), (0.06, 0.06, H),
                             (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z0 + H * 0.5),
                             col, G.P("wood")))
    obs.append(G.add_box(name + "_RT", (ln, 0.06, 0.06), (cx, cy, z0 + H), col,
                         G.P("wood_m"), rot_z=ang))
    obs.append(G.add_box(name + "_RM", (ln, 0.035, 0.035), (cx, cy, z0 + H * 0.45),
                         col, G.P("wood_l"), rot_z=ang))
    obs.append(G.add_box(name + "_RB", (ln, 0.045, 0.045), (cx, cy, z0 + 0.12), col,
                         G.P("wood_m"), rot_z=ang))
    return obs


def _build_stair(col):
    obs = []
    pitch = math.atan2(SR, ST)
    y1 = (LANE1[0] + LANE1[1]) * 0.5
    y2 = (LANE2[0] + LANE2[1]) * 0.5

    for k in range(1, N1 + 1):
        xa = ST_X0 + (k - 1) * ST
        top = G.F1 + k * SR
        obs.append(G.add_box("INT_ST_A_T%d" % k,
                             (ST - 0.006, LANE1[1] - LANE1[0], 0.05),
                             (xa + ST * 0.5, y1, top - 0.025), col, G.P("wood_l")))
        obs.append(G.add_box("INT_ST_A_R%d" % k,
                             (0.03, LANE1[1] - LANE1[0], SR + 0.02),
                             (xa + 0.015, y1, top - SR * 0.5), col, G.P("wood_m")))
    for j in range(1, N2 + 1):
        xb = ST_LAND0 - (j - 1) * ST
        top = G.F1 + (N1 + j) * SR
        obs.append(G.add_box("INT_ST_B_T%d" % j,
                             (ST - 0.006, LANE2[1] - LANE2[0], 0.05),
                             (xb - ST * 0.5, y2, top - 0.025), col, G.P("wood_l")))
        obs.append(G.add_box("INT_ST_B_R%d" % j,
                             (0.03, LANE2[1] - LANE2[0], SR + 0.02),
                             (xb - 0.015, y2, top - SR * 0.5), col, G.P("wood_m")))
    obs.append(G.add_box("INT_ST_TOP_R", (0.03, LANE2[1] - LANE2[0], SR + 0.02),
                         (ST_XTOP + 0.015, y2, G.F2 - SR * 0.5), col, G.P("wood_m")))

    # stringers: one on each side of both flights
    for tag, xc, zc, ang, lane, run in (
            ("A", (ST_X0 + ST_LAND0) * 0.5, (G.F1 + ST_Z) * 0.5, -pitch, LANE1,
             math.hypot(N1 * ST, ST_Z - G.F1)),
            ("B", (ST_XTOP + ST_LAND0) * 0.5,
             (G.F1 + (N1 + N2) * SR + G.F2) * 0.5 - 0.02, pitch, LANE2,
             math.hypot(N2 * ST, G.F2 - (G.F1 + N1 * SR)))):
        for s, yy in ((1, lane[0] + 0.055), (2, lane[1] - 0.055)):
            obs.append(G.add_box("INT_ST_STR_%s%d" % (tag, s), (run + 0.34, 0.08, 0.26),
                                 (xc, yy, zc - 0.145), col, G.P("wood"),
                                 rot=(0.0, ang, 0.0)))

    # landing platform
    ly = (LANE1[0] + LANE2[1]) * 0.5
    obs.append(G.add_box("INT_ST_LAND", (ST_LAND1 - ST_LAND0, LANE2[1] - LANE1[0], 0.10),
                         ((ST_LAND0 + ST_LAND1) * 0.5, ly, ST_Z - 0.05), col,
                         G.P("wood_l")))
    obs.append(G.add_box("INT_ST_LAND_F", (ST_LAND1 - ST_LAND0, 0.05, 0.20),
                         ((ST_LAND0 + ST_LAND1) * 0.5, -1.78, ST_Z - 0.15), col,
                         G.P("wood")))
    for sx in (ST_LAND0 + 0.07, ST_LAND1 - 0.07):
        obs.append(G.add_box("INT_ST_LAND_P%d" % int(sx * 100),
                             (0.09, 0.09, ST_Z - 0.10 - G.F1),
                             (sx, -1.83, (ST_Z - 0.10 + G.F1) * 0.5), col,
                             G.P("wood")))

    # balustrades: landing, floor opening, flight A handrail
    obs += _balustrade(col, "INT_ST_LANDRAIL", (ST_LAND0 + 0.06, -1.80),
                       (ST_LAND1 - 0.04, -1.80), ST_Z)
    obs += _balustrade(col, "INT_F2_RAIL_S", (0.58, -1.745),
                       (ROOM["f2"]["x1"] - 0.03, -1.745), G.F2)
    obs += _balustrade(col, "INT_F2_RAIL_M", (0.58, -2.875), (2.00, -2.875), G.F2)
    obs += _balustrade(col, "INT_F2_RAIL_E", (1.985, -2.88),
                       (1.985, ROOM["f2"]["y0"] + 0.05), G.F2)
    obs += _balustrade(col, "INT_ST_RAIL_A", (ST_X0 + 0.12, LANE1[1] - 0.035),
                       (ST_LAND0 - 0.02, LANE1[1] - 0.035), G.F1,
                       slope=(ST_X0 + 0.12, G.F1 + SR, ST_LAND0 - 0.02, ST_Z))
    # 上跑（B 段）靠大厅一侧原来没有栏杆：从二层回廊看是一段悬空的踏步。
    obs += _balustrade(col, "INT_ST_RAIL_B", (ST_XTOP + 0.02, LANE2[1] - 0.035),
                       (ST_LAND0 - 0.12, LANE2[1] - 0.035), G.F2,
                       slope=(ST_XTOP + 0.02, G.F2 - SR, ST_LAND0 - 0.12, ST_Z))
    # 望柱头：栏杆端部加柱帽，避免木杆直接断在空中
    for (name, x, y, z) in (
            ("INT_ST_NEWEL_A0", ST_X0 + 0.12, LANE1[1] - 0.035, G.F1 + 0.95),
            ("INT_ST_NEWEL_A1", ST_LAND0 - 0.02, LANE1[1] - 0.035, ST_Z + 0.95),
            ("INT_ST_NEWEL_B0", ST_XTOP + 0.02, LANE2[1] - 0.035, G.F2 - SR + 0.95),
            ("INT_ST_NEWEL_B1", ST_LAND0 - 0.12, LANE2[1] - 0.035, ST_Z + 0.95)):
        obs.append(G.add_box(name, (0.10, 0.10, 0.10), (x, y, z + 0.05), col,
                             G.P("wood_l")))
        obs.append(G.add_box(name + "_Bot", (0.10, 0.10, 0.06), (x, y, z - 0.90), col,
                             G.P("wood_m")))
    return obs


# ============================================================ vitrine
def _porcelain_jar(col, name, cx, cy, z0, scale=1.0):
    """Blue-and-white jar: revolved profile + painted bands."""
    body = [(0.092, 0.000), (0.106, 0.012), (0.138, 0.040), (0.172, 0.085),
            (0.196, 0.130), (0.198, 0.162), (0.186, 0.202), (0.160, 0.242),
            (0.128, 0.276), (0.100, 0.300), (0.082, 0.320), (0.076, 0.338),
            (0.090, 0.352), (0.100, 0.362)]
    prof = [(r * scale, dz * scale) for (r, dz) in body]
    obs = [_lathe(name + "_Body", prof, cx, cy, z0, col,
                  G.mat("M_porcelain", (0.918, 0.918, 0.892), rough=0.16), seg=26)]
    blue = G.mat("M_cobalt", (0.128, 0.208, 0.408), rough=0.20)
    for i, (dz, rr) in enumerate(((0.062, 0.176), (0.120, 0.199), (0.190, 0.192),
                                  (0.262, 0.150), (0.330, 0.082))):
        ob = G.add_cyl(name + "_Band%d" % i, rr * scale, 0.018 * scale,
                       (cx, cy, z0 + dz * scale), col, blue, segments=26)
        obs.append(ob)
    # lid
    obs.append(G.add_cyl(name + "_Lid", 0.108 * scale, 0.022 * scale,
                         (cx, cy, z0 + 0.372 * scale), col,
                         G.mat("M_porcelain", (0.918, 0.918, 0.892), rough=0.16),
                         segments=26))
    obs.append(G.add_sphere(name + "_Knob", 0.032 * scale,
                            (cx, cy, z0 + 0.400 * scale), col, blue,
                            segments=12, rings=8))
    return obs


def _build_vitrine(col):
    """Central stone-topped vitrine with a glazed case and a jar inside."""
    obs = []
    cx, cy = 0.0, G.BCY
    W = 1.20
    z = FLOOR1_Z
    obs.append(G.add_box("INT_VIT_Plith", (W - 0.10, W - 0.10, 0.08),
                         (cx, cy, z + 0.04), col, G.P("wood")))
    obs.append(G.add_box("INT_VIT_Body", (W, W, 0.62), (cx, cy, z + 0.08 + 0.31),
                         col, G.P("wood")))
    # lacquer panels with gold edging on the four faces
    for sx, sy, rot in ((0, -1, 0.0), (0, 1, 0.0), (-1, 0, math.pi * 0.5),
                        (1, 0, math.pi * 0.5)):
        ex = cx + sx * (W * 0.5 + 0.004)
        ey = cy + sy * (W * 0.5 + 0.004)
        pdims = (W - 0.16, 0.014, 0.40) if rot == 0.0 else (0.014, W - 0.16, 0.40)
        obs.append(G.add_box("INT_VIT_P%d%d" % (sx, sy), pdims,
                             (ex, ey, z + 0.42), col, G.P("lacquer"),
                             rot_z=rot))
        gdims = (W - 0.12, 0.010, 0.02) if rot == 0.0 else (0.010, W - 0.12, 0.02)
        for s in (-1, 1):
            obs.append(G.add_box("INT_VIT_G%d%d_%d" % (sx, sy, s), gdims,
                                 (ex, ey, z + 0.42 + s * 0.215), col, G.P("gold"),
                                 rot_z=rot))
    # stone top with a thin gold edge under it
    obs.append(G.add_box("INT_VIT_GoldEdge", (W + 0.09, W + 0.09, 0.018),
                         (cx, cy, z + 0.712), col, G.P("gold")))
    obs.append(G.add_box("INT_VIT_Top", (W + 0.10, W + 0.10, 0.055),
                         (cx, cy, z + 0.748), col, G.P("stone_l")))
    # glazed case
    zc = z + 0.776
    glass = _case_glass()
    h = 0.52
    for sx, sy, rot in ((0, -1, 0.0), (0, 1, 0.0), (-1, 0, math.pi * 0.5),
                        (1, 0, math.pi * 0.5)):
        ex = cx + sx * (W * 0.5 - 0.03)
        ey = cy + sy * (W * 0.5 - 0.03)
        gdims = (W - 0.06, 0.012, h) if rot == 0.0 else (0.012, W - 0.06, h)
        obs.append(G.add_box("INT_VIT_Glass%d%d" % (sx, sy), gdims,
                             (ex, ey, zc + h * 0.5), col, glass, rot_z=rot))
    for sx in (-1, 1):
        for sy in (-1, 1):
            obs.append(G.add_box("INT_VIT_Post%d%d" % (sx, sy), (0.03, 0.03, h),
                                 (cx + sx * (W * 0.5 - 0.03),
                                  cy + sy * (W * 0.5 - 0.03), zc + h * 0.5),
                                 col, G.P("gold")))
    obs.append(G.add_box("INT_VIT_CapFrame", (W + 0.02, W + 0.02, 0.035),
                         (cx, cy, zc + h + 0.017), col, G.P("wood")))
    obs.append(G.add_box("INT_VIT_CapTop", (W + 0.06, W + 0.06, 0.02),
                         (cx, cy, zc + h + 0.044), col, G.P("gold")))
    # display object: a low plinth and the jar
    obs.append(G.add_box("INT_VIT_JarBase", (0.34, 0.34, 0.03),
                         (cx, cy, zc + 0.015), col, G.P("stone_d")))
    obs.extend(_porcelain_jar(col, "INT_VIT_Jar", cx, cy, zc + 0.03, scale=1.28))
    return obs


# ============================================================ cases / benches
def _low_case(col, name, cx, cy, length, depth, rot, jar=True):
    obs = []
    z = FLOOR1_Z if cx is not None else 0.0
    z = G.F2 if name.startswith("INT_CASE_F2") else FLOOR1_Z
    obs.append(G.add_box(name + "_Plinth", (length - 0.10, depth - 0.08, 0.07),
                         (cx, cy, z + 0.035), col, G.P("wood")))
    obs.append(G.add_box(name + "_Body", (length, depth, 0.54),
                         (cx, cy, z + 0.07 + 0.27), col, G.P("wood"),
                         rot_z=rot))
    obs.append(G.add_box(name + "_Gold", (length + 0.02, depth + 0.02, 0.012),
                         (cx, cy, z + 0.615), col, G.P("gold"), rot_z=rot))
    obs.append(G.add_box(name + "_Top", (length + 0.03, depth + 0.03, 0.045),
                         (cx, cy, z + 0.645), col, G.P("stone_l"), rot_z=rot))
    glass = _case_glass()
    gz = z + 0.668
    gh = 0.40
    obs.append(G.add_box(name + "_GlassF", (length - 0.04, 0.012, gh),
                         (cx, cy - depth * 0.5 + 0.02, gz + gh * 0.5), col, glass,
                         rot_z=rot))
    obs.append(G.add_box(name + "_GlassB", (length - 0.04, 0.012, gh),
                         (cx, cy + depth * 0.5 - 0.02, gz + gh * 0.5), col, glass,
                         rot_z=rot))
    for s in (-1, 1):
        ox, oy = _place(cx, cy, rot, s * (length * 0.5 - 0.02), 0.0)
        obs.append(G.add_box("%s_GlassS%d" % (name, s), (0.012, depth - 0.04, gh),
                             (ox, oy, gz + gh * 0.5), col, glass, rot_z=rot))
    obs.append(G.add_box(name + "_Cap", (length + 0.02, depth + 0.02, 0.035),
                         (cx, cy, gz + gh + 0.017), col, G.P("wood"), rot_z=rot))
    obs.append(G.add_box(name + "_CapGold", (length + 0.05, depth + 0.05, 0.014),
                         (cx, cy, gz + gh + 0.041), col, G.P("gold"), rot_z=rot))
    if jar:
        obs.extend(_porcelain_jar(col, name + "_Jar", cx, cy, gz, scale=0.62))
    # small label plaque on the front face
    ox, oy = _place(cx, cy, rot, 0.0, -(depth * 0.5 + 0.006))
    obs.append(G.add_box(name + "_Label", (0.20, 0.006, 0.10),
                         (ox, oy, z + 0.40), col, G.P("ink"), rot_z=rot))
    return obs


def _bench(col, name, cx, cy, length, floor):
    obs = []
    z = G.F2 if floor == 2 else FLOOR1_Z
    obs.append(G.add_box(name + "_Seat", (length, 0.42, 0.075),
                         (cx, cy, z + 0.44), col, G.P("wood_l")))
    obs.append(G.add_box(name + "_Rail", (length - 0.20, 0.10, 0.16),
                         (cx, cy, z + 0.32), col, G.P("wood")))
    for s in (-1, 1):
        for t in (-1, 1):
            obs.append(G.add_box("%s_Leg%d%d" % (name, s, t), (0.07, 0.07, 0.40),
                                 (cx + s * (length * 0.5 - 0.16),
                                  cy + t * 0.16, z + 0.20), col, G.P("wood")))
    return obs


def _build_furniture(col):
    obs = []
    obs += _build_vitrine(col)
    # floor 1
    obs += _low_case(col, "INT_CASE_F1_A", -2.70, 0.70, 1.50, 0.52, 0.0)
    obs += _low_case(col, "INT_CASE_F1_B", 2.55, 0.95, 1.40, 0.52, 0.0)
    obs += _bench(col, "INT_BENCH_F1", -2.45, -2.55, 1.70, 1)
    # floor 2
    obs += _low_case(col, "INT_CASE_F2_A", -2.60, 0.00, 1.60, 0.52, 0.0)
    obs += _low_case(col, "INT_CASE_F2_B", 1.60, 2.10, 1.40, 0.52, 0.0)
    obs += _bench(col, "INT_BENCH_F2", -1.85, -2.10, 2.50, 2)
    obs.append(G.add_box("INT_F2_CarpetEdge", (2.90, 2.10, 0.006),
                         (-1.75, -2.15, G.F2 + 0.003), col, G.P("wood")))
    obs.append(G.add_box("INT_F2_Carpet", (2.76, 1.96, 0.006),
                         (-1.75, -2.15, G.F2 + 0.009), col,
                         G.mat("M_carpet2", (0.318, 0.098, 0.086), rough=0.96)))
    return obs


def _build_partitions(col):
    """Second-floor L arrangement: a low display screen, clear of every window,
    the stair opening and the railing."""
    obs = []
    z0, z1 = G.F2, 4.86
    h = z1 - z0
    for (name, cx, cy, length, rot) in (
            ("INT_PART_F2_A", -2.40, 0.55, 2.10, 0.0),
            ("INT_PART_F2_B", -1.35, 0.00, 1.10, math.pi * 0.5)):
        obs.append(G.add_box(name + "_Body", (length, 0.12, h),
                             (cx, cy, z0 + h * 0.5), col, G.P("plaster"),
                             rot_z=rot))
        obs.append(G.add_box(name + "_Base", (length, 0.17, 0.16),
                             (cx, cy, z0 + 0.08), col, G.P("stone_d"), rot_z=rot))
        obs.append(G.add_box(name + "_Cap", (length + 0.05, 0.18, 0.07),
                             (cx, cy, z1 + 0.035), col, G.P("wood"), rot_z=rot))
        obs.append(G.add_box(name + "_CapGold", (length + 0.07, 0.19, 0.014),
                             (cx, cy, z1 + 0.077), col, G.P("gold"), rot_z=rot))
        # dark wood surround so the screen reads as furniture, not a wall
        for s in (-1, 1):
            ox, oy = _place(cx, cy, rot, s * (length * 0.5 - 0.035), 0.0)
            obs.append(G.add_box("%s_Stile%d" % (name, s), (0.07, 0.145, h),
                                 (ox, oy, z0 + h * 0.5), col, G.P("wood"),
                                 rot_z=rot))
        for s in (-1, 1):
            ox, oy = _place(cx, cy, rot, 0.0, s * 0.068)
            obs.append(G.add_box("%s_Panel%d" % (name, s),
                                 (length - 0.26, 0.012, h - 0.56),
                                 (ox, oy, z0 + h * 0.50), col, G.P("paper"),
                                 rot_z=rot))
    return obs


# ============================================================ picture frames
def _frame_mesh(col, fname, anchor, rot, d0, size):
    """Dark wood moulding + gold liner + cream mat + recessed canvas."""
    ax, ay, az = anchor
    W, H = size
    short = min(W, H)
    mould = min(0.055, short * 0.09)
    mat = min(0.075, short * 0.11)
    img_w = max(0.10, W - 2.0 * (mould + mat))
    img_h = max(0.10, H - 2.0 * (mould + mat))
    ca, sa = math.cos(rot), math.sin(rot)

    def part(tag, du, dn, dz, u, n, z, mat_key):
        wx = ax + ca * u - sa * n
        wy = ay + sa * u + ca * n
        return G.add_box("%s_%s" % (fname, tag), (du, dn, dz), (wx, wy, az + z),
                         col, mat_key, rot_z=rot)

    obs = []
    obs.append(part("back", W - 0.02, 0.012, H - 0.02, 0.0, d0 + 0.008, 0.0,
                    G.P("wood")))
    obs.append(part("canvas", img_w, 0.010, img_h, 0.0, d0 + 0.019, 0.0,
                    _canvas_mat()))
    for s in (-1, 1):
        obs.append(part("MatT%d" % s, img_w + 2.0 * mat, 0.014, mat, 0.0,
                        d0 + 0.031, s * (img_h * 0.5 + mat * 0.5), G.P("paper")))
        obs.append(part("MatS%d" % s, mat, 0.014, img_h, s * (img_w * 0.5 + mat * 0.5),
                        d0 + 0.031, 0.0, G.P("paper")))
        obs.append(part("MouldT%d" % s, W, 0.075, mould, 0.0, d0 + 0.0395,
                        s * (H * 0.5 - mould * 0.5), G.P("wood")))
        obs.append(part("MouldS%d" % s, mould, 0.075, H - 2.0 * mould,
                        s * (W * 0.5 - mould * 0.5), d0 + 0.0395, 0.0, G.P("wood")))
        obs.append(part("GoldT%d" % s, img_w + 2.0 * mat + 0.012, 0.010, 0.012, 0.0,
                        d0 + 0.074,
                        s * (img_h * 0.5 + mat + 0.006), G.P("gold")))
        obs.append(part("GoldS%d" % s, 0.012, 0.010, img_h + 2.0 * mat + 0.012,
                        s * (img_w * 0.5 + mat + 0.006), d0 + 0.074, 0.0, G.P("gold")))
    return obs


def _build_frames(col):
    obs = []
    for (fid, floor, idx, loc, rot, wall_id, size, _u, _v, _label) in FRAME_ANCHORS:
        meta = _wall_meta(floor, wall_id)
        a = loc[1] if meta["axis"] == "y" else loc[0]
        d0 = (meta["face"] - a) * meta["inward"] + _panel_thick(wall_id) + 0.002
        name = "WF_FRAME_%02d" % (idx if floor == 1 else 7 + idx)
        parts = _frame_mesh(col, name, loc, rot, d0, size)
        ob = G.join_objs(name, parts)
        obs.append(ob)
        G.log("interior: %s wall %-16s d0 %.3f size %.2f x %.2f"
              % (name, wall_id, d0, size[0], size[1]))
    return obs


# ============================================================ roof timber
SECONDARY_X = (-3.30, -2.20, -1.10, 0.0, 1.10, 2.20, 3.30)
ATTIC = dict(x=3.62, y0=-3.71, y1=2.61)


def _roof_boarding(col):
    """Wood boarding (wangban) under the roof slab, following the pitch.

    Without it the tiled roof slab underside reads as a cold blue-grey sky and
    the attic stops looking like timber construction.
    """
    x0, x1 = -ATTIC["x"], ATTIC["x"]
    y0, y1 = ATTIC["y0"], ATTIC["y1"]
    nx, ny = 28, 24
    verts, faces = [], []
    for j in range(ny + 1):
        y = y0 + (y1 - y0) * j / ny
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            verts.append((x, y, _roof_under(x, y) - 0.200))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + nx + 1, a + nx + 2, a + 1))
    ob = G.add_mesh("INT_ROOF_BOARD", verts, faces, col,
                    G.mat("M_roof_board", (0.352, 0.216, 0.118), rough=0.80))
    return [ob]


def _build_attic_walls(col):
    """Attic walls from the window head to the roof underside, plus wall plates."""
    obs = []
    x = ATTIC["x"]
    y0, y1 = ATTIC["y0"], ATTIC["y1"]
    obs.append(_strip("INT_ATTIC_L", "x", -x, y0, y1,
                      lambda u: _roof_under(-x, u) - 0.044, 1.0, col,
                      G.P("plaster_d"), n=18))
    obs.append(_strip("INT_ATTIC_R", "x", x, y0, y1,
                      lambda u: _roof_under(x, u) - 0.044, -1.0, col,
                      G.P("plaster_d"), n=18))
    obs.append(_strip("INT_ATTIC_B", "y", y0, -x, x,
                      lambda u: _roof_under(u, y0) - 0.044, 1.0, col,
                      G.P("plaster_d"), n=18))
    obs.append(_strip("INT_ATTIC_F", "y", y1, -x, x,
                      lambda u: _roof_under(u, y1) - 0.044, -1.0, col,
                      G.P("plaster_d"), n=18))
    # wall plates: one at the window head (hides the step from the F2 wall),
    # one at the attic top where the rafters land
    for axis, at, inward, ln, cu in (
            ("x", -x, 1.0, y1 - y0, (y0 + y1) * 0.5),
            ("x", x, -1.0, y1 - y0, (y0 + y1) * 0.5),
            ("y", y0, 1.0, 2.0 * x, 0.0),
            ("y", y1, -1.0, 2.0 * x, 0.0)):
        if axis == "x":
            obs.append(G.add_box("INT_ATTIC_PLATE_%d" % int(at * 100),
                                 (0.22, ln, 0.16), (at - inward * 0.02, cu, 6.63),
                                 col, G.P("wood_m")))
        else:
            obs.append(G.add_box("INT_ATTIC_PLATEY_%d" % int(at * 100),
                                 (ln, 0.22, 0.16), (cu, at - inward * 0.02, 6.63),
                                 col, G.P("wood_m")))
    return obs


def _build_roof_timber(col):
    obs = []
    # 2 main beams along X, deep and low
    for i, yy in enumerate((G.BCY - 1.55, G.BCY + 1.55)):
        obs.append(G.add_box("INT_BEAM_MAIN%d" % i, (7.44, 0.26, 0.24),
                             (0.0, yy, 7.90), col, G.P("wood")))
        for s in (-1, 1):
            obs.append(G.add_box("INT_BEAM_MAIN_G%d%d" % (i, s),
                                 (7.44, 0.012, 0.024),
                                 (0.0, yy + s * 0.134, 7.790), col, G.P("gold")))
    # 7 secondary beams along Y following the pitch, split at the ridge
    for i, sx in enumerate(SECONDARY_X):
        for s, (ya, yb) in enumerate(((ATTIC["y0"] - 0.05, G.BCY),
                                      (G.BCY, ATTIC["y1"] + 0.05))):
            obs.append(_y_beam("INT_BEAM_SEC%d_%d" % (i, s), sx, ya, yb,
                               0.14, 0.18, 0.211, col, G.P("wood_m"), samples=9))
    # ~48 rafters, 24 positions each split at the ridge
    n = 24
    made = 0
    for i in range(n):
        sx = -3.45 + 7.0 * i / (n - 1)
        if any(abs(sx - q) < 0.10 for q in SECONDARY_X):
            continue
        for s, (ya, yb) in enumerate(((ATTIC["y0"] - 0.05, G.BCY),
                                      (G.BCY, ATTIC["y1"] + 0.05))):
            obs.append(_y_beam("INT_RAFTER_%d_%d" % (i, s), sx, ya, yb,
                               0.075, 0.095, 0.211, col, G.P("wood_l"), samples=9))
            made += 1
    G.log("interior: roof timber rafters=%d secondaries=%d main=2"
          % (made, len(SECONDARY_X) * 2))
    return obs


# ============================================================ joinery (榫卯)
JOIN_BEAM_TOP = 7.90 + 0.12


def _build_joinery(col):
    """梁架上的榫卯节点：瓜柱、斗、木销、梁头出榫、雀替、丁头拱。

    一层中庭是全通高的，抬头看到的就是这套节点。做法上不追求真实的
    「半榫/透榫」结构计算，而是把古建里最容易辨认的几个特征放大到能读出来：
      · 瓜柱坐在大梁上、柱头一斗托住次梁，柱身横向穿一根木销；
      · 大梁两端做出梁头，榫头继续伸进墙里，梁下两侧各一组雀替；
      · 大梁上按间距排一列斗拱，斗上承拱，形成连续的「斗拱图案」。
    """
    obs = []
    for bi, by in enumerate((G.BCY - 1.55, G.BCY + 1.55)):
        # ---- 梁头 + 榫头 + 雀替 -------------------------------------
        for sx in (-1, 1):
            x_end = sx * 3.72
            tag = "%d%d" % (bi, 1 if sx > 0 else 0)
            obs.append(G.add_box("INT_JOIN_HEAD_%s" % tag, (0.22, 0.30, 0.30),
                                 (x_end + sx * 0.05, by, 7.90), col,
                                 G.P("wood_l")))
            # 榫头：比梁身细一圈，从梁头继续伸出去
            obs.append(G.add_box("INT_JOIN_TENON_%s" % tag, (0.20, 0.13, 0.13),
                                 (x_end + sx * 0.24, by, 7.90), col,
                                 G.P("wood")))
            # 雀替：梁下两侧三段收分的托木
            for sy in (-1, 1):
                for k in range(3):
                    obs.append(G.add_box(
                        "INT_JOIN_QUETI_%s%d%d" % (tag, 1 if sy > 0 else 0, k),
                        (0.30 - 0.07 * k, 0.055, 0.075),
                        (x_end - sx * (0.02 + 0.10 * k),
                         by + sy * (0.15 + 0.05 * k), 7.70 - 0.06 * k),
                        col, G.P("wood_l" if k == 0 else "wood_m")))
            # 梁头下的丁头拱
            obs.append(G.add_box("INT_JOIN_TIP_%s" % tag, (0.12, 0.24, 0.10),
                                 (x_end - sx * 0.16, by, 7.66), col,
                                 G.P("wood_m")))

        # ---- 瓜柱 + 斗 + 木销 + 丁头拱 -------------------------------
        for xi, sx in enumerate(SECONDARY_X):
            z_sec_bottom = _roof_under(sx, by) - 0.211 - 0.18
            h = z_sec_bottom - JOIN_BEAM_TOP
            if h < 0.20:
                continue
            key = "%d_%d" % (bi, xi)
            obs.append(G.add_box("INT_JOIN_POST_%s" % key, (0.125, 0.125, h),
                                 (sx, by, JOIN_BEAM_TOP + h * 0.5), col,
                                 G.P("wood_m")))
            # 柱头斗：垫在次梁底面
            obs.append(G.add_box("INT_JOIN_CAP_%s" % key, (0.23, 0.23, 0.085),
                                 (sx, by, z_sec_bottom - 0.042), col,
                                 G.P("wood_l")))
            # 木销：横穿柱身，两端露头
            obs.append(G.add_cyl("INT_JOIN_PIN_%s" % key, 0.017, 0.20,
                                 (sx, by, JOIN_BEAM_TOP + h - 0.15), col,
                                 G.P("gold"), segments=8,
                                 rot=(0.0, math.pi * 0.5, 0.0)))
            # 柱脚两侧的丁头拱，让柱与大梁的交接有过渡
            for sy in (-1, 1):
                obs.append(G.add_box(
                    "INT_JOIN_ARM_%s%d" % (key, 1 if sy > 0 else 0),
                    (0.10, 0.26, 0.09),
                    (sx, by + sy * 0.16, JOIN_BEAM_TOP + 0.04), col,
                    G.P("wood_l")))

        # ---- 大梁上的连续斗拱 ---------------------------------------
        n = 12
        for i in range(n + 1):
            x = -3.40 + 6.80 * i / n
            obs.append(G.add_box("INT_JOIN_DOU_%d_%d" % (bi, i),
                                 (0.15, 0.20, 0.09), (x, by, JOIN_BEAM_TOP + 0.045),
                                 col, G.P("wood_l")))
            obs.append(G.add_box("INT_JOIN_GONG_%d_%d" % (bi, i),
                                 (0.40, 0.09, 0.065), (x, by, JOIN_BEAM_TOP + 0.12),
                                 col, G.P("wood_m")))
            for s in (-1, 1):
                obs.append(G.add_box(
                    "INT_JOIN_SHENG_%d_%d_%d" % (bi, i, 1 if s > 0 else 0),
                    (0.075, 0.10, 0.055),
                    (x + s * 0.17, by, JOIN_BEAM_TOP + 0.175), col,
                    G.P("wood_l")))
    return obs


# ============================================================ caisson + lantern
def _oct(pt, r, z, n=8, rot=math.pi / 8.0):
    return [(pt[0] + math.cos(rot + 2.0 * math.pi * i / n) * r,
             pt[1] + math.sin(rot + 2.0 * math.pi * i / n) * r, z) for i in range(n)]


def _build_caisson(col):
    """Octagonal three-tier caisson under the ridge, with a palace lantern."""
    obs = []
    cx, cy = 0.0, G.BCY
    radii = (0.70, 0.53, 0.36, 0.20)
    zs = (8.55, 8.86, 9.14, 9.38)
    verts, faces = [], []
    for k in range(3):
        r_out, r_in = radii[k], radii[k + 1]
        z0, z1 = zs[k], zs[k + 1]
        o = _oct((cx, cy), r_out, z0)
        n = _oct((cx, cy), r_in, z0)
        base = len(verts)
        verts.extend(o)
        verts.extend(n)
        for i in range(8):
            j = (i + 1) % 8
            faces.append((base + i, base + j, base + 8 + j, base + 8 + i))
        # recessed skirt from this tier's inner ring up to the next level
        b2 = len(verts)
        ia = _oct((cx, cy), r_in, z0)
        ib = _oct((cx, cy), r_in, z1)
        verts.extend(ia)
        verts.extend(ib)
        for i in range(8):
            j = (i + 1) % 8
            faces.append((b2 + i, b2 + 8 + i, b2 + 8 + j, b2 + j))
    # top cap, facing down into the room
    cap = _oct((cx, cy), radii[3], zs[3])
    b3 = len(verts)
    verts.extend(cap)
    faces.append(tuple(reversed(tuple(b3 + i for i in range(8)))))
    obs.append(G.add_mesh("INT_CAISSON", verts, faces, col, G.P("wood_m")))
    # gold rings on the tier edges
    for k in range(3):
        z0 = zs[k] + 0.004
        r_out, r_in = radii[k] - 0.012, radii[k + 1] + 0.012
        verts, faces = [], []
        o = _oct((cx, cy), r_out, z0)
        n = _oct((cx, cy), r_in, z0)
        verts.extend(o)
        verts.extend(n)
        for i in range(8):
            j = (i + 1) % 8
            faces.append((i, j, 8 + j, 8 + i))
        obs.append(G.add_mesh("INT_CAISSON_GOLD%d" % k, verts, faces, col,
                              G.P("gold")))
    # painted centre medallion + bracket blocks around the rim
    obs.append(G.add_cyl("INT_CAISSON_MED", 0.115, 0.018,
                         (cx, cy, zs[3] - 0.012), col, G.P("gold"), segments=8,
                         rot=(0.0, 0.0, math.pi / 8.0)))
    for i in range(8):
        a = math.pi / 8.0 + 2.0 * math.pi * i / 8.0
        obs.append(G.add_box("INT_CAISSON_BRK%d" % i, (0.10, 0.10, 0.13),
                             (cx + math.cos(a) * 0.64, cy + math.sin(a) * 0.64,
                              zs[0] + 0.045), col, G.P("wood"),
                             rot_z=a))
    # suspension rods up to the ridge
    for sx in (-1, 1):
        for sy in (-1, 1):
            obs.append(G.add_cyl("INT_CAISSON_ROD%d%d" % (sx, sy), 0.014, 0.70,
                                 (cx + sx * 0.47, cy + sy * 0.47, zs[0] + 0.35),
                                 col, G.P("gold"), segments=6))
    obs += _palace_lantern(col, "INT_LANTERN_CAISSON", cx, cy, zs[0])
    return obs


def _build_hall_lanterns(col):
    """Two practical lanterns hung under the first-floor ceiling."""
    obs = []
    for i, (lx, ly) in enumerate(((-1.85, -0.75), (1.85, -0.75))):
        obs += _palace_lantern(col, "INT_LANTERN_F1_%d" % i, lx, ly, G.F2 - 0.20)
    return obs


def _palace_lantern(col, name, cx, cy, z_top):
    obs = []
    obs.append(G.add_cyl(name + "_Chain", 0.011, 0.34,
                         (cx, cy, z_top - 0.17), col, G.P("gold"), segments=6))
    z = z_top - 0.40
    emiss = G.E("caisson_lantern", (1.0, 0.62, 0.30), 4.2)
    obs.append(G.add_cone(name + "_CapT", 0.105, 0.190, 0.10, (cx, cy, z + 0.29),
                          col, G.P("gold"), segments=6))
    # hex body: six paper panels between six corner ribs
    verts, faces = [], []
    r, hz0, hz1 = 0.190, z + 0.02, z + 0.26
    for zz in (hz0, hz1):
        for i in range(6):
            a = math.pi / 6.0 + 2.0 * math.pi * i / 6.0
            verts.append((cx + math.cos(a) * r, cy + math.sin(a) * r, zz))
    for i in range(6):
        j = (i + 1) % 6
        faces.append((i, j, 6 + j, 6 + i))
    obs.append(G.add_mesh(name + "_Body", verts, faces, col, emiss))
    for i in range(6):
        a = math.pi / 6.0 + 2.0 * math.pi * i / 6.0
        obs.append(G.add_box("%s_Rib%d" % (name, i), (0.026, 0.026, 0.26),
                             (cx + math.cos(a) * (r + 0.007),
                              cy + math.sin(a) * (r + 0.007), (hz0 + hz1) * 0.5),
                             col, G.P("wood"), rot_z=a))
    obs.append(G.add_cone(name + "_CapB", 0.190, 0.082, 0.09, (cx, cy, z - 0.02),
                          col, G.P("gold"), segments=6))
    obs.append(G.add_sphere(name + "_Bead", 0.038, (cx, cy, z - 0.085), col,
                            G.P("gold"), segments=10, rings=6))
    obs.append(G.add_cone(name + "_Tassel", 0.048, 0.010, 0.24,
                          (cx, cy, z - 0.21), col, G.P("red"), segments=6,
                          rot=(math.pi, 0.0, 0.0)))
    obs.append(G.add_cyl(name + "_RodTop", 0.008, 0.18, (cx, cy, z_top - 0.09),
                         col, G.P("wood"), segments=6))
    return obs


# ============================================================ hanging scrolls
def _scroll(col, name, face_y, u, z_top, w, h, inward=1.0, inset=0.05):
    """Hanging scroll on a back wall: lacquer silk mount, paper, two rollers."""
    n = face_y + inward * inset
    obs = []
    obs.append(G.add_box(name + "_Mount", (w + 0.11, 0.010, h + 0.15),
                         (u, n, z_top - h * 0.5 - 0.01), col, G.P("wood")))
    obs.append(G.add_box(name + "_Paper", (w, 0.008, h),
                         (u, n + inward * 0.009, z_top - h * 0.5 - 0.01), col,
                         G.P("paper")))
    for s in (0, 1):
        z = z_top + 0.055 if s == 0 else z_top - h - 0.065
        obs.append(G.add_cyl("%s_Rod%d" % (name, s), 0.015, w + 0.16,
                             (u, n + inward * 0.012, z), col, G.P("wood"),
                             segments=8, rot=(0.0, math.pi * 0.5, 0.0)))
    obs.append(G.add_box(name + "_Cord", (0.012, 0.006, 0.14),
                         (u, n + inward * 0.006, z_top + 0.14), col,
                         G.P("gold")))
    return obs


# ============================================================ title plaques
def _build_plaques(col):
    obs = []
    # floor-1 theme wall title
    z = 2.94
    obs.append(G.add_box("INT_PLAQUE_F1_Board", (1.70, 0.05, 0.44),
                         (-1.05, -4.015, z), col, G.P("ink")))
    obs.append(G.add_box("INT_PLAQUE_F1_Gold", (1.78, 0.03, 0.06),
                         (-1.05, -4.030, z + 0.22), col, G.P("gold")))
    try:
        obs.append(G.text_mesh("INT_PLAQUE_F1_Text", "\u7eb9\u8109\u534e\u7ae0",
                               0.22, (-1.05, -3.985, z), col, G.P("gold"),
                               font_path=G.cjk_font(), extrude=0.010,
                               rot=(math.pi * 0.5, 0.0, math.pi)))
    except Exception:
        G.log("interior: title text skipped")
    # floor-2 title on the back display wall
    z2 = 6.05
    obs.append(G.add_box("INT_PLAQUE_F2_Board", (1.50, 0.05, 0.40),
                         (0.0, -3.855, z2), col, G.P("ink")))
    obs.append(G.add_box("INT_PLAQUE_F2_Gold", (1.58, 0.03, 0.05),
                         (0.0, -3.870, z2 + 0.20), col, G.P("gold")))
    try:
        obs.append(G.text_mesh("INT_PLAQUE_F2_Text", "\u5320\u5fc3\u4f20\u97f5",
                               0.19, (0.0, -3.825, z2), col, G.P("gold"),
                               font_path=G.cjk_font(), extrude=0.010,
                               rot=(math.pi * 0.5, 0.0, math.pi)))
    except Exception:
        G.log("interior: title text skipped")
    obs += _scroll(col, "INT_SCROLL_F1", -4.06, 0.62, 2.52, 0.42, 1.00)
    obs += _scroll(col, "INT_SCROLL_F2", -3.90, -2.40, 5.58, 0.38, 0.90)
    return obs


# ============================================================ build
def build(col):
    """Entry point: build the whole interior and return every object created."""
    obs = []
    _probe_rooms()
    _neutralise_shell()
    _install_roof_hooks()
    _open_roof_interior()
    obs += _build_anchors(col)
    obs += _build_fitout(col)
    obs += _build_f1_floor(col)
    obs += _build_f2_floor(col)
    obs += _build_stair(col)
    obs += _build_furniture(col)
    obs += _build_partitions(col)
    obs += _build_frames(col)
    obs += _build_attic_walls(col)
    obs += _roof_boarding(col)
    obs += _build_roof_timber(col)
    obs += _build_joinery(col)
    obs += _build_caisson(col)
    obs += _build_hall_lanterns(col)
    obs += _build_plaques(col)

    tris = 0
    for ob in obs:
        if ob is None or ob.type != "MESH":
            continue
        ob.data.calc_loop_triangles()
        tris += len(ob.data.loop_triangles)
    # cheap self-check: the pieces the render judges most often go missing
    for nm in ("INT_CAISSON", "INT_LANTERN_CAISSON_Body", "INT_ATTIC_L",
               "INT_RAFTER_0_0", "INT_BEAM_MAIN0", "INT_ST_LAND"):
        ob = bpy.data.objects.get(nm)
        if ob is None:
            G.log("interior: MISSING " + nm)
            continue
        lo = Vector((1e9, 1e9, 1e9))
        hi = Vector((-1e9, -1e9, -1e9))
        for corner in ob.bound_box:
            w = ob.matrix_world @ Vector(corner)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
        G.log("interior: %-24s x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f"
              % (nm, lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))
    G.log("interior objects: %d, triangles: %d" % (len(obs), tris))
    return obs







