"""Interior generator: floors, central void, 2F open corridor, stair, fit-out.

Params (docs/CONTRACT.md section 4B): ``voidX=5.4, voidY=4.6,
corridorWidth=1.9, railingHeight=1.05, stair:{x,y,width,risers},
displayWalls=true, ceilingStyle='coffered'|'beams', lanterns=true, detail``.

The 二层回廊 (level-2 open corridor ringing the central void) is the centrepiece:
a real walkable ring floor with a 寻杖 railing (posts, top rail, mid rail, bottom
rail), a carved 挂落 lattice fascia hanging under the void-edge beam, and a
pilaster/lintel order on the outer side, so the void reads as a two-storey hall
rather than a hole in a slab.

Frame anchors
-------------
The 15 artwork anchors are owned by the web contract and must never be lost:

* anchors already in ``baseBlend`` are adopted verbatim (same name, location,
  rotation, custom props) and only get the ``wm_part`` tag;
* if one is missing it is recreated from ``gallery_layout.json`` using the exact
  inverse of the exporter transform (``build_v5.to_web`` = ``(x, z, -y)``, so
  ``blender = (X, -Z, Y)``), giving an identical name / position / rotation;
* every anchor found or created is snapshotted before the part is deleted and
  restored afterwards, so an incremental re-run can never drop one.

The annex also mirrors the shipped v5 convention: Blender Z-up with **+Y as the
building front** and the hall centred at y = -0.55. The CONTRACT section 1 prose
says "front = -Y / centre +0.55", but the shipped blend, ``gallery_layout.json``
and every ``CAM_*`` are the mirror of that; the anchors win because the web
contract depends on them. ``frontSign``/``hallY`` can flip it if the Lead ever
rebuilds from scratch.
"""
from __future__ import annotations

import json
import math
import os

import bpy
from mathutils import Vector

import wm_common as WC
import wm_mesh as M

DEFAULTS = {
    "voidX": 5.4,
    "voidY": 4.6,
    "corridorWidth": 1.9,
    "railingHeight": 1.05,
    "stair": {"x": 3.1, "y": -3.3, "width": 1.15, "risers": 18, "shape": "L"},
    "displayWalls": True,
    "ceilingStyle": "coffered",
    "lanterns": True,
    "detail": "medium",
    # envelope
    "hallX": 8.4,
    "hallY": 7.5,
    "hallCY": -0.55,
    "wallT": 0.16,
    "f1Z": 0.25,
    "f2Z": 3.60,
    "topZ": 6.55,
    "slabT": 0.20,
    "layoutPath": None,
}

DETAIL = {
    "low":    {"lattice": 0.55, "posts": 0.7, "rails": 20, "cases": 4, "coffer": 3},
    "medium": {"lattice": 1.00, "posts": 1.0, "rails": 34, "cases": 6, "coffer": 4},
    "high":   {"lattice": 1.35, "posts": 1.0, "rails": 46, "cases": 8, "coffer": 5},
}

FRAME_IDS = ([f"FRAME_F1_{i:03d}" for i in range(1, 8)] +
             [f"FRAME_F2_{i:03d}" for i in range(1, 9)])

# v5 facade opening schedule (gal_common.OPENINGS). Kept here so the interior
# doors/windows line up with the shell built by the base blend.
OPENINGS = {
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


def _num(p, key):
    return WC.safe_float(p.get(key), DEFAULTS[key])


def _detail(p):
    key = str(p.get("detail") or DEFAULTS["detail"]).lower()
    return DETAIL.get(key, DETAIL["medium"]), (key if key in DETAIL else "medium")


def _stair(p):
    raw = p.get("stair") or {}
    out = dict(DEFAULTS["stair"])
    for k, v in raw.items():
        if k in out:
            out[k] = v
    out["x"] = WC.safe_float(out["x"], DEFAULTS["stair"]["x"])
    out["y"] = WC.safe_float(out["y"], DEFAULTS["stair"]["y"])
    out["width"] = max(0.8, WC.safe_float(out["width"], 1.15))
    out["risers"] = max(6, WC.safe_int(out["risers"], 18))
    out["shape"] = str(out.get("shape") or "L").upper()
    return out


# --------------------------------------------------------------------- anchors
def _layout_path(params, ctx):
    if params.get("layoutPath"):
        return params["layoutPath"]
    root = ctx.get("projectRoot") or r"D:\wenmai-huazhang"
    return os.path.join(root, "assets", "gallery3d", "exports", "gallery_layout.json")


def _frame_anchor_table(params, ctx):
    """Build the 15-anchor table from the shipped layout contract.

    ``build_v5.to_web`` is ``(x, z, -y)``, so the inverse is
    ``blender = (X, -Z, Y)``. The layout's ``rotationY`` is a *derived* facing
    angle (``atan2(n.x, -n.y)``), not the object's ``rotation_euler.z``; the
    frame entries carry the raw ``rotZ`` and it is used first. For wall entries
    (which only carry ``rotationY``) the relation ``rotationY = rotZ + pi`` is
    inverted, which reproduces the shipped v5 wall rotations exactly.
    """
    rows = []
    walls = []
    path = _layout_path(params, ctx)
    doc = None
    if path and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except Exception:
            doc = None
    if not doc:
        return rows, walls, f"layout contract unreadable: {path}"
    for entry in doc.get("frames", []):
        web = entry.get("position") or [0, 0, 0]
        pos = (float(web[0]), -float(web[2]), float(web[1]))
        if entry.get("rotZ") is not None:
            rot = float(entry["rotZ"])
        else:
            rot = float(entry.get("rotationY") or 0.0) - math.pi
        size = entry.get("size") or [1.0, 0.85]
        rows.append({
            "id": entry.get("id"),
            "floor": WC.safe_int(entry.get("floor"), 1),
            "position": pos,
            "rotZ": rot,
            "wallId": entry.get("wallId") or "",
            "size": [WC.safe_float(size[0], 1.0), WC.safe_float(size[1], 0.85)],
            "u": WC.safe_float(entry.get("u"), 0.5),
            "v": WC.safe_float(entry.get("v"), 0.5),
            "label": entry.get("label") or entry.get("id"),
        })
    walls = []
    for entry in doc.get("walls", []):
        web = entry.get("center") or [0, 0, 0]
        size = entry.get("size") or [1.8, 3.0]
        walls.append({
            "id": entry.get("id"),
            "floor": WC.safe_int(entry.get("floor"), 1),
            "position": (float(web[0]), -float(web[2]), float(web[1])),
            "rotZ": float(entry.get("rotationY") or 0.0) - math.pi,
            "width": WC.safe_float(size[0], 1.8),
            "height": WC.safe_float(size[1], 3.0),
            "label": entry.get("label") or entry.get("id"),
        })
    return rows, walls, \
        f"{len(rows)} frame + {len(walls)} wall anchors read from {path}"


def _ensure_galwalls(params, ctx, table):
    """Create the GALWALL_* display-wall anchors if the base blend lacks them."""
    created, adopted = [], []
    for row in table:
        ident = "GALWALL_" + str(row["id"])
        obj = bpy.data.objects.get(ident)
        if obj is not None:
            adopted.append(ident)
            continue
        obj = bpy.data.objects.new(ident, None)
        obj.empty_display_type = "PLAIN_AXES"
        obj.empty_display_size = 0.3
        obj.location = Vector(row["position"])
        obj.rotation_euler = (0.0, 0.0, row["rotZ"])
        bpy.context.scene.collection.objects.link(obj)
        obj["width"] = row["width"]
        obj["height"] = row["height"]
        obj["floor"] = row["floor"]
        obj["label"] = row["label"]
        created.append(ident)
    return created, adopted


def _ensure_frames(params, ctx, table) -> tuple:
    """Adopt existing anchors, recreate missing ones, tag them all."""
    by_id = {row["id"]: row for row in table}
    created, adopted = [], []
    for ident in FRAME_IDS:
        obj = bpy.data.objects.get(ident)
        if obj is None:
            row = by_id.get(ident)
            if not row:
                continue
            obj = bpy.data.objects.new(ident, None)
            obj.empty_display_type = "PLAIN_AXES"
            obj.empty_display_size = 0.3
            obj.location = Vector(row["position"])
            obj.rotation_euler = (0.0, 0.0, row["rotZ"])
            bpy.context.scene.collection.objects.link(obj)
            obj["frame_size"] = row["size"]
            obj["wall_id"] = row["wallId"]
            obj["u"] = row["u"]
            obj["v"] = row["v"]
            obj["label"] = row["label"]
            obj["floor"] = row["floor"]
            obj["index"] = WC.safe_int(ident[-3:], 0)
            created.append(ident)
        else:
            adopted.append(ident)
        obj["wm_part"] = "interior"
        obj["wm_component"] = "frame_anchor"
        obj["wm_anchor"] = "frame"
    found = [i for i in FRAME_IDS if bpy.data.objects.get(i) is not None]
    return found, created, adopted


# ------------------------------------------------------------------- geometry
def _free_rects(rect, holes):
    """Split an axis-aligned rectangle around a list of (x0, x1, y0, y1) holes."""
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


def _slab(geo, rect, z0, z1, holes):
    for (a, b, c, d) in _free_rects(rect, holes):
        geo.box(((a + b) * 0.5, (c + d) * 0.5, (z0 + z1) * 0.5),
                (b - a, d - c, z1 - z0))


def _planked(geo, rect, z_top, thick, pitch, holes, inset=0.012):
    idx = 0
    for (a, b, c, d) in _free_rects(rect, holes):
        y = c
        while y < d - 1e-4:
            yy = min(y + pitch, d)
            if yy - y > 0.06:
                geo.box(((a + b) * 0.5, (y + yy) * 0.5, z_top - thick * 0.5),
                        (b - a - inset, yy - y - inset, thick))
                idx += 1
            y = yy
    return idx


def _ring_rects(rect, hole_x, hole_y):
    """Four rectangles forming a ring around the void."""
    x0, x1, y0, y1 = rect
    hx0, hx1, hy0, hy1 = hole_x[0], hole_x[1], hole_y[0], hole_y[1]
    out = [(x0, x1, y0, hy0), (x0, x1, hy1, y1),
           (x0, hx0, hy0, hy1), (hx1, x1, hy0, hy1)]
    return [r for r in out if r[1] - r[0] > 1e-4 and r[3] - r[2] > 1e-4]


def _legacy_f2_plates(void_rect, z_band):
    """Untagged flat plates at level-2 that cover the whole void footprint."""
    x0, x1, y0, y1 = void_rect
    z0, z1 = z_band
    found = []
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.get("wm_part"):
            continue
        lo, hi = M.world_bbox(obj)
        if hi[2] - lo[2] > 0.45:                     # a plate, not a wall
            continue
        if not (z0 < (lo[2] + hi[2]) * 0.5 < z1):
            continue
        if lo[0] <= x0 and hi[0] >= x1 and lo[1] <= y0 and hi[1] >= y1:
            found.append(obj.name)
    return found


def _lattice(geo, x0, y0, x1, y1, z, height, pitch, bar=0.030, diag=True):
    """花格 lattice panel in a vertical plane; real bars, two diagonal families."""
    ln = math.hypot(x1 - x0, y1 - y0)
    if ln < 0.15 or height < 0.15:
        return 0
    ang = math.atan2(y1 - y0, x1 - x0)
    n = max(2, int(round(ln / max(0.12, pitch))))
    step = ln / n
    cx, cy = (x0 + x1) * 0.5, (y0 + y1) * 0.5
    ca, sa = math.cos(ang), math.sin(ang)
    count = 0
    # frame
    for zz in (z + bar * 0.5, z + height - bar * 0.5):
        geo.box((cx, cy, zz), (ln, bar * 1.2, bar), rot=(0.0, 0.0, ang))
        count += 1
    for i in range(n + 1):
        u = -ln * 0.5 + step * i
        geo.box((cx + u * ca, cy + u * sa, z + height * 0.5),
                (bar, bar, height), rot=(0.0, 0.0, ang))
        count += 1
    if diag:
        d = math.hypot(step, height)
        dang = math.atan2(height, step)
        for i in range(n):
            u = -ln * 0.5 + step * (i + 0.5)
            for sgn in (1.0, -1.0):
                geo.box((cx + u * ca, cy + u * sa, z + height * 0.5),
                        (d * 0.92, bar * 0.8, bar * 0.8),
                        rot=(0.0, sgn * dang, ang))
                count += 1
    return count


def _railing(geo_post, geo_rail, geo_fascia, p0, p1, z, height, detail,
             lattice=True, facing=1.0, geo_accent=None):
    """寻杖栏杆 + 挂落 fascia along one straight run of the void edge."""
    x0, y0 = p0
    x1, y1 = p1
    ln = math.hypot(x1 - x0, y1 - y0)
    if ln < 0.25:
        return 0, 0
    ang = math.atan2(y1 - y0, x1 - x0)
    cx, cy = (x0 + x1) * 0.5, (y0 + y1) * 0.5
    n = max(2, int(round(ln / (0.62 * detail["posts"]))))
    step = ln / n
    posts = 0
    for i in range(n + 1):
        u = -ln * 0.5 + step * i
        px, py = cx + u * math.cos(ang), cy + u * math.sin(ang)
        geo_post.box((px, py, z + height * 0.5), (0.075, 0.075, height),
                     rot=(0.0, 0.0, ang))
        geo_post.box((px, py, z + height + 0.025), (0.11, 0.11, 0.05),
                     rot=(0.0, 0.0, ang))
        posts += 1
    # 寻杖 (top rail), 中枋 (mid rail), 地栿 (sole)
    geo_rail.box((cx, cy, z + height), (ln, 0.085, 0.075), rot=(0.0, 0.0, ang))
    geo_rail.box((cx, cy, z + height * 0.52), (ln, 0.055, 0.050), rot=(0.0, 0.0, ang))
    geo_rail.box((cx, cy, z + 0.07), (ln, 0.070, 0.075), rot=(0.0, 0.0, ang))
    # 蜀柱 stub posts between the rails
    for i in range(n):
        u = -ln * 0.5 + step * (i + 0.5)
        px, py = cx + u * math.cos(ang), cy + u * math.sin(ang)
        geo_rail.box((px, py, z + height * 0.55), (0.045, 0.045, height * 0.42),
                     rot=(0.0, 0.0, ang))
    # 挂落 carved fascia hanging *below* the sole, offset outward from the void
    fx = cx - math.sin(ang) * 0.10 * facing
    fy = cy + math.cos(ang) * 0.10 * facing
    fh = 0.30
    geo_fascia.box((fx, fy, z - fh * 0.5 - 0.02), (ln, 0.045, 0.05),
                   rot=(0.0, 0.0, ang))
    geo_fascia.box((fx, fy, z - fh - 0.03), (ln, 0.045, 0.05),
                   rot=(0.0, 0.0, ang))
    cells = max(2, int(round(ln / (0.30 / detail["lattice"]))))
    cell = ln / cells
    for i in range(cells):
        u = -ln * 0.5 + cell * (i + 0.5)
        px, py = fx + u * math.cos(ang), fy + u * math.sin(ang)
        geo_fascia.box((px, py, z - fh * 0.5 - 0.02), (0.035, 0.035, fh - 0.05),
                       rot=(0.0, 0.0, ang))
        # 回纹 hook inside each cell: short arm + return, painted (青绿彩画)
        geo_fascia.box((px + cell * 0.25 * math.cos(ang),
                        py + cell * 0.25 * math.sin(ang), z - fh * 0.52),
                       (cell * 0.42, 0.028, 0.035), rot=(0.0, 0.0, ang))
        acc = geo_accent if geo_accent is not None else geo_fascia
        acc.box((px + cell * 0.45 * math.cos(ang),
                 py + cell * 0.45 * math.sin(ang), z - fh * 0.30),
                (0.030, 0.030, fh * 0.42), rot=(0.0, 0.0, ang))
    return posts, cells


def _stair_case(geo_step, geo_rail, geo_side, sx, sy, width, risers, f1, f2, shape):
    """Straight or L-shaped stair with real treads, risers and stringers."""
    total_rise = f2 - f1
    rise = total_rise / risers
    tread = 0.27
    obs_posts = 0
    if shape == "L":
        n1 = (risers + 1) // 2
        n2 = risers - n1
    else:
        n1, n2 = risers, 0
    x = sx
    z = f1
    # flight 1: runs in -X from the foot
    for k in range(n1):
        x0 = x - tread * (k + 1)
        top = f1 + rise * (k + 1)
        geo_step.box((x0 + tread * 0.5, sy, top - 0.026), (tread - 0.008, width, 0.052))
        geo_step.box((x0 + 0.016, sy, top - rise * 0.5), (0.032, width, rise + 0.02))
    geo_side.limb((sx, sy - width * 0.5, f1), (sx - tread * n1, sy - width * 0.5,
                                               f1 + rise * n1), 0.055, 0.075, seg=6)
    geo_side.limb((sx, sy + width * 0.5, f1), (sx - tread * n1, sy + width * 0.5,
                                               f1 + rise * n1), 0.055, 0.075, seg=6)
    if n2 > 0:
        lx = sx - tread * n1
        land_z = f1 + rise * n1
        geo_step.box((lx - width * 0.5, sy, land_z - 0.05), (width, width, 0.10))
        geo_side.limb((lx, sy - width * 0.5, land_z - 0.10), (lx, sy + width * 0.5,
                                                              land_z - 0.10),
                      0.05, 0.05, seg=6)
        for k in range(n2):
            zz = land_z + rise * (k + 1)
            yy = sy + tread * (k + 1)
            geo_step.box((lx - width * 0.5, yy - tread * 0.5, zz - 0.026),
                         (width, tread - 0.008, 0.052))
            geo_step.box((lx - width * 0.5, yy - 0.016, zz - rise * 0.5),
                         (width, 0.032, rise + 0.02))
        top_y = sy + tread * n2
        geo_side.limb((lx - width * 0.5, sy, land_z), (lx - width * 0.5, top_y,
                                                       land_z + rise * n2),
                      0.06, 0.08, seg=6)
        geo_side.limb((lx + width * 0.5, sy, land_z), (lx + width * 0.5, top_y,
                                                       land_z + rise * n2),
                      0.06, 0.08, seg=6)
        # railing on the open side of the second flight
        px = lx + width * 0.5
        for k in range(n2 + 1):
            zz = land_z + rise * k
            yy = sy + tread * k
            geo_rail.box((px + 0.06, yy, zz + 0.50), (0.055, 0.055, 1.00))
        geo_rail.limb((px + 0.06, sy, land_z + 1.00), (px + 0.06, top_y,
                                                       land_z + rise * n2 + 1.00),
                      0.04, 0.04, seg=6)
    return obs_posts


def _lantern(geo_frame, geo_glow, geo_gold, cx, cy, z_top, name_seed=0):
    """六角宫灯: chain, cap, emissive hexagon body, ribs, bead, tassel."""
    geo_gold.limb((cx, cy, z_top - 0.17), (cx, cy, z_top), 0.011, 0.011, seg=5)
    z = z_top - 0.40
    r = 0.19
    rings = []
    for zz in (z + 0.02, z + 0.26):
        rings.append([(cx + math.cos(math.pi / 6.0 + 2.0 * math.pi * i / 6.0) * r,
                       cy + math.sin(math.pi / 6.0 + 2.0 * math.pi * i / 6.0) * r, zz)
                      for i in range(6)])
    geo_glow.sweep(rings, caps=True)
    for i in range(6):
        a = math.pi / 6.0 + 2.0 * math.pi * i / 6.0
        geo_frame.box((cx + math.cos(a) * (r + 0.007), cy + math.sin(a) * (r + 0.007),
                       z + 0.14), (0.026, 0.026, 0.26), rot=(0.0, 0.0, a))
    geo_gold.box((cx, cy, z + 0.31), (0.30, 0.30, 0.075))
    geo_gold.box((cx, cy, z - 0.03), (0.30, 0.30, 0.075))
    geo_gold.sphere((cx, cy, z - 0.085), 0.038, seg=8, rings=5)
    geo_frame.box((cx, cy, z - 0.20), (0.075, 0.075, 0.22))


def generate_interior(params: dict, ctx: dict) -> dict:
    params = dict(params or {})
    detail, detail_key = _detail(params)
    snapshot = M.snapshot_anchors(("FRAME_", "GALWALL_"))
    info = M.open_base(params, ctx, "interior")
    before = len(bpy.data.objects)
    legacy = M.replace_legacy(params, "interior")
    before += len(legacy)
    warnings = list(info["warnings"])
    checks = []
    col = M.collection(M.PART_COLLECTIONS["interior"])
    restored = M.restore_anchors(snapshot)
    frame_rows, wall_rows, layout_msg = _frame_anchor_table(params, ctx)

    hx = _num(params, "hallX")
    hy = _num(params, "hallY")
    cy = _num(params, "hallCY")
    wt = _num(params, "wallT")
    f1 = _num(params, "f1Z")
    f2 = _num(params, "f2Z")
    top = _num(params, "topZ")
    slab_t = _num(params, "slabT")
    ix = hx * 0.5 - wt
    iy0, iy1 = cy - hy * 0.5 + wt, cy + hy * 0.5 - wt
    void_x = min(_num(params, "voidX"), 2 * ix - 1.6)
    void_y = min(_num(params, "voidY"), (iy1 - iy0) - 1.6)
    cw = max(0.9, min(_num(params, "corridorWidth"), min(ix, (iy1 - iy0) * 0.5) - 0.6))
    rail_h = _num(params, "railingHeight")
    st = _stair(params)
    vx0, vx1 = -void_x * 0.5, void_x * 0.5
    vy0, vy1 = cy - void_y * 0.5, cy + void_y * 0.5

    g_slab = M.Geo()
    g_board = M.Geo()
    g_post = M.Geo()
    g_rail = M.Geo()
    g_fascia = M.Geo()
    g_stair = M.Geo()
    g_case = M.Geo()
    g_glass = M.Geo()
    g_ceil = M.Geo()
    g_beam = M.Geo()
    g_wall = M.Geo()
    g_win = M.Geo()
    g_glow = M.Geo()
    g_gold = M.Geo()
    g_porcelain = M.Geo()
    g_accent = M.Geo()
    g_carpet = M.Geo()

    # ------------------------------------------------------- level-1 floor
    room1 = (ix * -1.0, ix, iy0, iy1)
    g_slab.box((0.0, cy, (0.0 + f1) * 0.5 - 0.02), (hx - 0.1, hy - 0.1, f1 + 0.02))
    n_boards = _planked(g_board, room1, f1, 0.018, 0.36, [])
    g_board.box((0.0, cy, f1 + 0.004), (2.96, 2.16, 0.008))
    # ------------------------------------------- legacy level-2 floor plates
    # The v5 shell carries TWO full-footprint plates at level-2: VER_Slab
    # (z 3.44..3.60, also the exterior veranda) and WALL_Band (3.52..3.72, the
    # floor band). Together they close the central void, which is why the 2F
    # camera saw "floor continuing past the railing". Cutting the interior
    # footprint out of them keeps the veranda ring and opens the void.
    legacy_cut = {"objects": 0, "faces": 0, "names": []}
    legacy_plates = _legacy_f2_plates((vx0, vx1, vy0, vy1), (f2 - 0.30, f2 + 0.30))
    if legacy_plates and params.get("cutLegacySlabs", True):
        legacy_cut = M.cut_faces_in_rect(names=legacy_plates,
                                         rect=(-ix + 0.01, ix - 0.01, iy0 + 0.01, iy1 - 0.01),
                                         z_band=(f2 - 0.32, f2 + 0.32))
        for nm in legacy_cut["names"]:
            warnings.append(f"cut the legacy level-2 floor plate {nm} out of the "
                            f"interior footprint to open the central void "
                            f"({legacy_cut['faces']} faces)")
    # ------------------------------------------------------- level-2 plate
    void_hole = [(vx0, vx1, vy0, vy1)]
    stair_hole = [(st["x"] - 3.2, st["x"] - 0.2, st["y"] - 1.6, st["y"] + 1.6)]
    holes = void_hole + (stair_hole if st["shape"] == "L" else [])
    ring = (ix * -1.0, ix, iy0, iy1)
    # exposed joists + soffit under the F1 ceiling, then the F2 plate
    n_joist = 0
    y = iy0 + 0.25
    while y < iy1 - 0.15:
        for (a, b, c, d) in _free_rects((ix * -1.0, ix, y - 0.05, y + 0.05), stair_hole if st["shape"] == "L" else []):
            g_beam.box(((a + b) * 0.5, (c + d) * 0.5, f2 - 0.20), (b - a, d - c, 0.16))
            n_joist += 1
        y += 0.55
    _slab(g_beam, ring, f2 - 0.205, f2 - 0.188, holes)
    _slab(g_slab, ring, f2 - 0.034, f2 - 0.016, holes)
    n_boards2 = _planked(g_board, ring, f2, 0.016, 0.36, holes)
    # open void edge trim
    for (a, b, c, d) in ((vx0 - 0.04, vx1 + 0.04, vy0 - 0.04, vy0 + 0.02),
                         (vx0 - 0.04, vx1 + 0.04, vy1 - 0.02, vy1 + 0.04),
                         (vx0 - 0.04, vx0 + 0.02, vy0, vy1),
                         (vx1 - 0.02, vx1 + 0.04, vy0, vy1)):
        g_beam.box(((a + b) * 0.5, (c + d) * 0.5, f2 - 0.10), (b - a, d - c, 0.22))

    # ------------------------------------------------- 2F open corridor ring
    railing_runs = (
        ((vx0, vy0), (vx0, vy1)),
        ((vx1, vy0), (vx1, vy1)),
        ((vx0, vy0), (vx1, vy0)),
        ((vx0, vy1), (vx1, vy1)),
    )
    posts = cells = 0
    for (p0, p1) in railing_runs:
        a, b = _railing(g_post, g_rail, g_fascia, p0, p1, f2, rail_h, detail,
                        g_accent)
        posts += a
        cells += b
    # 红栏 lacquer caps along the void edge: v5 paints its rails, and the flat
    # all-timber railing was reading colder than the model it replaces
    for (p0, p1) in railing_runs:
        x0, y0 = p0
        x1, y1 = p1
        ln = math.hypot(x1 - x0, y1 - y0)
        if ln < 0.25:
            continue
        ang = math.atan2(y1 - y0, x1 - x0)
        g_accent.box(((x0 + x1) * 0.5, (y0 + y1) * 0.5, f2 + rail_h + 0.010),
                     (ln, 0.105, 0.028), rot=(0.0, 0.0, ang))
        g_accent.box(((x0 + x1) * 0.5, (y0 + y1) * 0.5, f2 + rail_h * 0.52),
                     (ln, 0.070, 0.016), rot=(0.0, 0.0, ang))
    # 1F carpet: the v5 interior read warm largely because of the deep-red rug
    g_carpet.box((0.0, cy, f1 + 0.012), (3.10, 2.30, 0.010))
    g_carpet.box((0.0, cy, f1 + 0.019), (2.96, 2.16, 0.006))
    # corridor deck boards + outer pilaster order
    corridor_rects = [(ix * -1.0, ix, iy0, vy0), (ix * -1.0, ix, vy1, iy1),
                      (ix * -1.0, vx0, vy0, vy1), (vx1, ix, vy0, vy1)]
    n_corridor = 0
    for rect in corridor_rects:
        n_corridor += _planked(g_board, rect, f2 + 0.010, 0.014, 0.30, [])
    px = ix - 0.22
    for i in range(max(3, int(round((iy1 - iy0) / 1.35)))):
        yy = iy0 + (iy1 - iy0) * (i + 0.5) / max(1, int(round((iy1 - iy0) / 1.35)))
        for sx in (-1, 1):
            g_post.box((sx * px, yy, f2 + 1.30), (0.20, 0.20, 2.60))
            g_rail.box((sx * px, yy, f2 + 2.62), (0.30, 0.34, 0.10))
    for sy in (iy0 + 0.20, iy1 - 0.20):
        for sx in (-1, 1):
            g_post.box((sx * (ix - 0.34), sy, f2 + 1.30), (0.20, 0.20, 2.60))
    # 额枋 lintels over the corridor opening
    g_beam.box((0.0, vy0, f2 + 2.52), (2 * ix, 0.26, 0.30))
    g_beam.box((0.0, vy1, f2 + 2.52), (2 * ix, 0.26, 0.30))
    g_beam.box((vx0, cy, f2 + 2.52), (0.26, void_y, 0.30))
    g_beam.box((vx1, cy, f2 + 2.52), (0.26, void_y, 0.30))

    # ------------------------------------------------------------- stair
    _stair_case(g_stair, g_rail, g_beam, st["x"], st["y"], st["width"],
                st["risers"], f1, f2, st["shape"])

    # -------------------------------------------------------- display walls
    gal_count = 0
    panel_objs = []
    if params.get("displayWalls", DEFAULTS["displayWalls"]):
        _ensure_galwalls(params, ctx, wall_rows)
        for obj in list(bpy.data.objects):
            if obj.type != "EMPTY" or not obj.name.startswith("GALWALL_"):
                continue
            wid = obj.name.replace("GALWALL_", "")
            w = WC.safe_float(obj.get("width"), 1.8)
            h = WC.safe_float(obj.get("height"), 3.0)
            floor = WC.safe_int(obj.get("floor"), 1)
            z0 = f1 if floor == 1 else f2
            rot = obj.rotation_euler.z
            panel = M.Geo()
            # 展墙: body + dado + cornice + a recessed inset for the artwork
            panel.box((0.0, 0.0, h * 0.5), (w, 0.10, h))
            panel.box((0.0, 0.0, 0.09), (w + 0.06, 0.16, 0.18))
            panel.box((0.0, 0.0, h - 0.09), (w + 0.10, 0.18, 0.18))
            panel.box((0.0, -0.03, h * 0.5), (w - 0.22, 0.05, h - 0.42))
            ob = M.finish(panel, f"GALWALL_{wid}_Panel", "interior",
                          "galwall_panel", "wall", col, params)
            if ob:
                ob.location = (obj.location.x, obj.location.y, z0)
                ob.rotation_euler = (0.0, 0.0, rot)
                panel_objs.append(ob)
            reb = M.Geo()
            reb.box((w * 0.5 + 0.05, 0.0, h * 0.5), (0.12, 0.14, h))
            reb.box((-w * 0.5 - 0.05, 0.0, h * 0.5), (0.12, 0.14, h))
            ob = M.finish(reb, f"GALWALL_{wid}_Pilaster", "interior",
                          "galwall_pilaster", "timber_warm", col, params)
            if ob:
                ob.location = (obj.location.x, obj.location.y, z0)
                ob.rotation_euler = (0.0, 0.0, rot)
                panel_objs.append(ob)
            gal_count += 1

    # -------------------------------------------------------- doors/windows
    def opening_pos(side, u):
        if side == "front":
            return (u, cy + hy * 0.5 - wt * 0.5), 0.0
        if side == "back":
            return (u, cy - hy * 0.5 + wt * 0.5), math.pi
        if side == "right":
            return (hx * 0.5 - wt * 0.5, cy + u), math.pi * 0.5
        return (-hx * 0.5 + wt * 0.5, cy + u), -math.pi * 0.5

    win_count = 0
    door_count = 0

    def out_sign(side, rot):
        """+1 when the opening's local +Y points out of the building."""
        out_world = {"front": (0.0, 1.0), "back": (0.0, -1.0),
                     "right": (1.0, 0.0), "left": (-1.0, 0.0)}[side]
        ly = (-math.sin(rot), math.cos(rot))
        return 1.0 if (ly[0] * out_world[0] + ly[1] * out_world[1]) >= 0.0 else -1.0

    for key, entries in OPENINGS.items():
        floor = 1 if key.startswith("f1") else 2
        side = key.split("_", 1)[1]
        z0_base = f1 if floor == 1 else f2
        for entry in entries:
            u, w, z0, h, kind = entry[:5]
            pattern = entry[5] if len(entry) > 5 else "grid"
            (ox, oy), rot = opening_pos(side, u)
            tag = f"{'m' if u < 0 else 'p'}{abs(int(round(u * 100))):03d}"
            os_ = out_sign(side, rot)
            if kind == "door":
                door_count += 1
                d = M.Geo()
                d.box((0.0, 0.0, h * 0.5), (w + 0.16, 0.24, h + 0.10))
                for sgn in (-1, 1):
                    d.box((sgn * w * 0.25, 0.07 * os_, h * 0.5), (w * 0.47, 0.06, h * 0.94))
                    d.box((sgn * w * 0.25, 0.115 * os_, h * 0.5), (w * 0.40, 0.02, h * 0.82))
                    d.box((sgn * w * 0.25, 0.13 * os_, h * 0.30), (w * 0.36, 0.02, h * 0.24))
                d.box((0.0, 0.14 * os_, h * 0.28), (w * 0.94, 0.03, 0.06))
                d.box((0.0, 0.14 * os_, h * 0.72), (w * 0.94, 0.03, 0.06))
                ob = M.finish(d, f"DOOR_F{floor}_{side}_{tag}",
                              "interior", "door", "timber", col, params)
                if ob:
                    ob.location = (ox, oy, z0_base + z0)
                    ob.rotation_euler = (0.0, 0.0, rot)
            else:
                win_count += 1
                # 窗框: four border bars plus a sill. The opening stays OPEN --
                # the previous version filled it with a solid box, which is
                # exactly why the 2F openings read as big unlit dark rectangles.
                g = M.Geo()
                fw = 0.11
                g.box((0.0, 0.0, h + fw * 0.5), (w + fw * 2.0, 0.17, fw))
                g.box((0.0, 0.0, -fw * 0.5), (w + fw * 2.0, 0.17, fw))
                for sgn in (-1, 1):
                    g.box((sgn * (w * 0.5 + fw * 0.5), 0.0, h * 0.5), (fw, 0.17, h))
                g.box((0.0, 0.04 * os_, -fw * 1.4), (w + fw * 2.6, 0.26, fw * 0.8))
                ob = M.finish(g, f"WIND_F{floor}_{side}_{tag}",
                              "interior", "window_frame", "timber_dark", col, params)
                if ob:
                    ob.location = (ox, oy, z0_base + z0)
                    ob.rotation_euler = (0.0, 0.0, rot)
                # 窗纸 + warm glow band behind the lattice
                back = M.Geo()
                low = h * 0.60
                back.box((0.0, 0.05 * os_, low * 0.5), (w, 0.02, low))
                glow = M.Geo()
                glow.box((0.0, 0.045 * os_, low + (h - low) * 0.5),
                         (w, 0.02, (h - low) * 0.96))
                ob = M.finish(back, f"WIND_F{floor}_{side}_{tag}_Paper",
                              "interior", "window_paper", "paper", col, params)
                if ob:
                    ob.location = (ox, oy, z0_base + z0)
                    ob.rotation_euler = (0.0, 0.0, rot)
                ob = M.finish(glow, f"WIND_F{floor}_{side}_{tag}_Glow",
                              "interior", "window_glow", "lamp_glow", col, params)
                if ob:
                    ob.location = (ox, oy, z0_base + z0)
                    ob.rotation_euler = (0.0, 0.0, rot)
                lat = M.Geo()
                _lattice(lat, -w * 0.5, 0.0, w * 0.5, 0.0, 0.0, h,
                         0.24 / detail["lattice"], bar=0.030,
                         diag=(pattern == "diamond"))
                ob2 = M.finish(lat, f"WIND_F{floor}_{side}_{tag}_Lattice",
                               "interior", "window_lattice", "wood_light", col, params)
                if ob2:
                    ob2.location = (ox, oy, z0_base + z0)
                    ob2.rotation_euler = (0.0, 0.0, rot)

    # ---------------------------------------------------------- showcases
    case_positions = [(-2.6, iy0 + 1.4), (2.6, iy0 + 1.4),
                      (-2.6, cy + 1.9), (2.6, cy + 1.9),
                      (0.0, iy0 + 0.95), (0.0, iy1 - 1.2),
                      (-3.3, cy + 0.2), (3.3, cy + 0.2)]
    n_cases = min(detail["cases"], len(case_positions))
    for i in range(n_cases):
        cx0, cy0 = case_positions[i]
        long_case = abs(cx0) > 2.0
        lw, ld = (2.30, 0.66) if long_case else (1.10, 0.66)
        z0 = f1
        g_case.box((cx0, cy0, z0 + 0.44), (lw, ld, 0.88))
        g_case.box((cx0, cy0, z0 + 0.90), (lw + 0.08, ld + 0.08, 0.06))
        g_case.box((cx0, cy0, z0 + 0.03), (lw + 0.10, ld + 0.10, 0.06))
        g_glass.box((cx0, cy0, z0 + 1.26), (lw - 0.06, ld - 0.06, 0.66))
        g_case.box((cx0, cy0, z0 + 1.62), (lw + 0.06, ld + 0.06, 0.06))
        g_gold.box((cx0, cy0, z0 + 1.13), (lw - 0.02, ld - 0.02, 0.03))
        n_jar = 3 if long_case else 1
        for k in range(n_jar):
            jx = cx0 + (k - (n_jar - 1) * 0.5) * (lw / (n_jar + 0.4))
            _porcelain(g_porcelain, jx, cy0, z0 + 0.93, 0.16 + 0.03 * (k % 2))
    # benches
    for (bx, by) in ((-1.4, cy - 2.5), (1.4, cy - 2.5)):
        g_case.box((bx, by, f1 + 0.22), (1.70, 0.52, 0.08))
        for sx in (-1, 1):
            for sy in (-1, 1):
                g_case.box((bx + sx * 0.72, by + sy * 0.18, f1 + 0.10),
                           (0.10, 0.10, 0.20))

    # ------------------------------------------------------------- ceiling
    style = str(params.get("ceilingStyle") or DEFAULTS["ceilingStyle"]).lower()
    n_coffer = 0
    head_room = f2 + 2.95                      # 2F head height (contract 6.55)
    if style == "coffered":
        # 天花背板: a solid board over the whole interior with the void cut out.
        # Without it the 0.16 m gaps between coffers let the tilted skirt-roof
        # underside show through as a pale plane across the upper view.
        board_rect = (ix * -1.0, ix, iy0, iy1)
        _slab(g_ceil, board_rect, top - 0.10, top - 0.055,
              [(vx0, vx1, vy0, vy1)])
        nx = max(2, detail["coffer"])
        ny = max(2, int(round(detail["coffer"] * (hy / hx))))
        stepx = (2 * ix) / nx
        stepy = (iy1 - iy0) / ny
        for i in range(nx):
            for j in range(ny):
                cx0 = -ix + stepx * (i + 0.5)
                cy0 = iy0 + stepy * (j + 0.5)
                # 藻井 coffer: recessed panel, raised rim, painted boss
                g_ceil.box((cx0, cy0, top - 0.26), (stepx - 0.10, stepy - 0.10, 0.22))
                g_ceil.box((cx0, cy0, top - 0.13), (stepx - 0.01, 0.09, 0.09))
                g_ceil.box((cx0, cy0, top - 0.13), (0.09, stepy - 0.01, 0.09))
                g_gold.box((cx0, cy0, top - 0.38), (stepx * 0.30, stepy * 0.30, 0.05))
                n_coffer += 1
        # central octagonal 藻井 hanging in the *void*, above 2F head height:
        # at top-0.62..top-1.18 it crossed CAM_F2 (z 5.18) as a pale diagonal
        # plane. It now spans top+0.20 .. top+0.60, i.e. 6.75..7.15 for the v5
        # stack, which clears the 6.55 head height and stays under the skirt
        # roof's inner edge.
        ocx, ocy = 0.0, cy
        r = min(void_x, void_y) * 0.34
        z_a, z_b, z_c = top + 0.60, top + 0.40, top + 0.20
        ring_a = [(ocx + math.cos(math.pi / 8.0 + 2 * math.pi * i / 8) * r,
                   ocy + math.sin(math.pi / 8.0 + 2 * math.pi * i / 8) * r, z_a)
                  for i in range(8)]
        ring_b = [(ocx + math.cos(math.pi / 8.0 + 2 * math.pi * i / 8) * r * 0.55,
                   ocy + math.sin(math.pi / 8.0 + 2 * math.pi * i / 8) * r * 0.55, z_b)
                  for i in range(8)]
        ring_c = [(ocx + math.cos(math.pi / 8.0 + 2 * math.pi * i / 8) * r * 0.24,
                   ocy + math.sin(math.pi / 8.0 + 2 * math.pi * i / 8) * r * 0.24, z_c)
                  for i in range(8)]
        g_ceil.sweep([ring_a, ring_b, ring_c], caps=True)
        g_gold.box((ocx, ocy, z_b), (r * 0.36, r * 0.36, 0.06),
                   rot=(0.0, 0.0, math.pi / 8.0))
        for i in range(4):
            a = math.pi / 4.0 + 2.0 * math.pi * i / 4.0
            g_gold.limb((ocx + math.cos(a) * r * 0.42, ocy + math.sin(a) * r * 0.42, z_a),
                        (ocx + math.cos(a) * r * 0.42, ocy + math.sin(a) * r * 0.42,
                         top + 0.92), 0.016, 0.016, seg=5)
        if z_c < head_room:
            warnings.append(f"caisson hangs to z={z_c:.2f}, below the 2F head "
                            f"height {head_room:.2f}")
    else:
        for i in range(max(3, detail["coffer"])):
            yy = iy0 + (iy1 - iy0) * (i + 0.5) / max(3, detail["coffer"])
            g_beam.box((0.0, yy, top - 0.24), (2 * ix, 0.30, 0.34))
        g_beam.box((0.0, cy, top - 0.52), (2 * ix, 0.20, 0.24))

    # ------------------------------------------------------------- lanterns
    n_lantern = 0
    if params.get("lanterns", DEFAULTS["lanterns"]):
        for (lx, ly) in ((-1.85, cy - 0.75), (1.85, cy - 0.75),
                         (0.0, cy + 1.2)):
            _lantern(g_case, g_glow, g_gold, lx, ly, f2 - 0.16)
            n_lantern += 1
        for (lx, ly) in ((-2.9, cy - 1.6), (2.9, cy - 1.6)):
            _lantern(g_case, g_glow, g_gold, lx, ly, top - 0.70)
            n_lantern += 1

    # -------------------------------------------------------------- anchors
    found, created, adopted = _ensure_frames(params, ctx, frame_rows)
    # Display backing board per artwork anchor. The board is a *separate* object
    # (GALWALL_AnchorBoards), never the anchor itself: the 15 FRAME_* empties
    # keep their name / position / rotation / props untouched, so the web
    # contract and the anchor inventory are unaffected.
    board_geo = M.Geo()
    n_boards_anchor = 0
    for row in frame_rows:
        obj = bpy.data.objects.get(row["id"])
        if obj is None:
            continue
        size = obj.get("frame_size") or row.get("size") or [1.0, 0.85]
        fw = WC.safe_float(size[0], 1.0) + 0.18
        fh = WC.safe_float(size[1], 0.85) + 0.18
        loc = obj.matrix_world.translation
        rot = obj.rotation_euler.z
        nx, ny = loc.x - 0.0, loc.y - cy
        nl = math.hypot(nx, ny) or 1.0
        nx, ny = nx / nl, ny / nl
        bx, by = loc.x - nx * 0.045, loc.y - ny * 0.045
        board_geo.box((bx, by, loc.z), (fw, 0.04, fh), rot=(0.0, 0.0, rot))
        board_geo.box((bx, by, loc.z + fh * 0.5 + 0.035), (fw + 0.07, 0.06, 0.06),
                      rot=(0.0, 0.0, rot))
        board_geo.box((bx, by, loc.z - fh * 0.5 - 0.035), (fw + 0.07, 0.06, 0.06),
                      rot=(0.0, 0.0, rot))
        n_boards_anchor += 1

    objs = []
    ob = M.finish(board_geo, "GALWALL_AnchorBoards", "interior",
                  "anchor_board", "paper", col, params)
    if ob is not None:
        objs.append(ob)

    def emit(name, g, mat, comp, smooth=False):
        ob = M.finish(g, name, "interior", comp, mat, col, params, smooth=smooth)
        if ob is not None:
            objs.append(ob)
        return ob

    emit("FLOOR_01", g_slab, "stone_warm", "floor_01")
    emit("FLOOR_01_Boards", g_board, "wood_light", "floor_boards")
    emit("FLOOR_02", g_slab, "stone_warm", "floor_02", smooth=False)
    emit("RAIL_Posts", g_post, "timber", "corridor_posts")
    emit("RAIL_寻杖", g_rail, "wood_light", "corridor_rail")
    emit("RAIL_Lacquer", g_accent, "red", "corridor_lacquer")
    emit("RAIL_Fascia", g_fascia, "timber_warm", "corridor_fascia")
    emit("FLOOR_01_Carpet", g_carpet, "red_deep", "floor_carpet")
    emit("STAIR_Steps", g_stair, "wood_light", "stair_steps")
    emit("STAIR_Stringer", g_beam, "timber_dark", "stair_stringer", smooth=True)
    emit("SHOWCASE_Case", g_case, "timber_dark", "showcase_case")
    emit("SHOWCASE_Glass", g_glass, "porcelain", "showcase_glass")
    emit("SHOWCASE_Object", g_porcelain, "porcelain_bl", "showcase_object", smooth=True)
    emit("BEAM_Ceiling", g_ceil, "timber", "ceiling_coffer")
    emit("GALWALL_PanelBase", g_wall, "wall", "galwall_base")
    emit("WIND_Lattice", g_win, "wood_light", "window_lattice")
    emit("LANTERN_Glow", g_glow, "lamp_glow", "lantern_glow", smooth=True)
    emit("BEAM_Ceiling_Gold", g_gold, "gold", "interior_gold")
    objs.extend([o for o in panel_objs if o not in objs])

    out = M.save_out(info["out"])
    arts = [WC.artifact("blend", out)]
    tris = M.tri_count(objs)
    rep = M.mesh_report(objs)
    present = [i for i in FRAME_IDS if bpy.data.objects.get(i) is not None]
    missing = [i for i in FRAME_IDS if bpy.data.objects.get(i) is None]

    by_id = {row["id"]: row for row in frame_rows}
    worst_pos = worst_rot = 0.0
    for ident in present:
        row = by_id.get(ident)
        obj = bpy.data.objects.get(ident)
        if not row or obj is None:
            continue
        worst_pos = max(worst_pos, (Vector(row["position"]) -
                                    obj.matrix_world.translation).length)
        d = (row["rotZ"] - obj.rotation_euler.z) % (2.0 * math.pi)
        worst_rot = max(worst_rot, min(d, 2.0 * math.pi - d))
    WC.check(checks, "interior_frame_anchors",
             "pass" if len(present) == 15 and not missing else "fail",
             f"frameAnchors={len(present)}/15 created={len(created)} "
             f"adoptedFromBase={len(adopted)} restored={len(restored)}; {layout_msg}")
    WC.check(checks, "interior_frame_transform_matches_layout",
             "pass" if (worst_pos < 1e-3 and worst_rot < 1e-3) else
             ("warn" if worst_pos < 0.02 and worst_rot < 0.02 else "fail"),
             f"max |position| delta {worst_pos:.6f} m, max rotation delta "
             f"{math.degrees(worst_rot):.6f} deg against gallery_layout.json "
             f"(inverse of build_v5.to_web; frame rotZ taken from the layout, "
             f"wall rotZ = rotationY - pi)")
    if restored:
        warnings.append("frame anchors were recreated after delete_part: " + ", ".join(restored))
    if legacy:
        WC.check(checks, "interior_legacy_replaced", "pass",
                 f"{len(legacy)} untagged v5 interior objects removed "
                 f"({', '.join(sorted(set(n.split('_')[0] for n in legacy)))} prefixes); "
                 f"scene objects {before} -> {len(bpy.data.objects)}")
        warnings.append("replaced untagged legacy v5 objects: "
                        + ", ".join(sorted(set(n.split("_")[0] for n in legacy)))
                        + " (pass legacyReplace=false to keep them)")
    WC.check(checks, "interior_void",
             "pass" if void_x > 2.0 and void_y > 2.0 else "warn",
             f"central void {void_x:.2f} x {void_y:.2f} m at (0, {cy:.2f}); "
             f"F2 plate is a ring with the void + stair openings cut out")
    WC.check(checks, "interior_legacy_floor_cut",
             "pass" if (not legacy_plates or legacy_cut["faces"] > 0) else "warn",
             f"legacy level-2 plates detected: {legacy_plates or 'none'}; cut "
             f"{legacy_cut['faces']} faces out of {legacy_cut['objects']} of them "
             f"over the interior footprint so the void is genuinely open "
             f"(the v5 shell carries VER_Slab + WALL_Band as full-footprint "
             f"plates at z {f2 - 0.30:.2f}..{f2 + 0.30:.2f})")
    WC.check(checks, "interior_ceiling_above_head",
             "pass" if (style != "coffered" or top + 0.20 >= f2 + 2.95) else "fail",
             f"ceilingStyle={style}; ceiling board at z={top - 0.08:.2f}, caisson "
             f"spans {(top + 0.20) if style == 'coffered' else 0:.2f}.."
             f"{(top + 0.60) if style == 'coffered' else 0:.2f} — 2F head height "
             f"{f2 + 2.95:.2f}, so nothing crosses CAM_F2 (z 5.18) any more")
    WC.check(checks, "interior_corridor",
             "pass" if posts >= 8 else "warn",
             f"2F open corridor ring {cw:.2f} m wide, {posts} railing posts, "
             f"{cells} 挂落 lattice cells, rail height {rail_h:.2f} m")
    WC.check(checks, "interior_railing_reaches_2F",
             "pass" if abs(f2 - 3.60) < 0.01 else "warn",
             f"railing sole at z={f2:.2f} (F2 level), top rail z={f2 + rail_h:.2f}")
    WC.check(checks, "interior_stair_geometry",
             "pass" if st["risers"] >= 10 else "warn",
             f"{st['shape']} stair {st['risers']} risers of "
             f"{(f2 - f1) / st['risers']:.3f} m, width {st['width']:.2f} m, "
             f"tread 0.27 m, reaching z={f2:.2f}")
    WC.check(checks, "interior_stair_reaches_F2",
             "pass" if f1 + (f2 - f1) <= f2 + 1e-6 else "fail",
             f"top riser z={f2:.3f} = F2 plate")
    WC.check(checks, "interior_display_walls",
             "pass" if gal_count >= 6 else ("warn" if gal_count else "fail"),
             f"{gal_count} GALWALL anchors given a real panel + pilasters")
    WC.check(checks, "interior_doors_windows",
             "pass" if win_count >= 6 and door_count >= 1 else "warn",
             f"{door_count} doors, {win_count} windows on the v5 opening schedule, "
             f"each an OPEN frame (4 border bars + sill) with 花格 lattice, a "
             f"窗纸 paper panel and a warm lamp_glow band behind it")
    WC.check(checks, "interior_anchor_boards",
             "pass" if n_boards_anchor == len(present) else "warn",
             f"{n_boards_anchor} display backing boards for {len(present)} anchors "
             f"(one GALWALL_AnchorBoards object; the FRAME_* empties themselves are "
             f"untouched)")
    WC.check(checks, "interior_showcases",
             "pass" if n_cases >= 3 else "warn",
             f"{n_cases} showcases with glass and porcelain contents")
    WC.check(checks, "interior_ceiling",
             "pass", f"ceilingStyle={style}, {n_coffer} coffers, "
                     f"{n_lantern} lanterns")
    WC.check(checks, "interior_topology",
             "pass" if rep["degenerateFaces"] == 0 else "fail",
             f"boundaryEdges={rep['boundaryEdges']} nonManifold={rep['nonManifoldEdges']} "
             f"degenerate={rep['degenerateFaces']}")
    WC.check(checks, "interior_triangle_budget",
             "pass" if tris <= 90000 else ("warn" if tris <= 140000 else "fail"),
             f"triangles={tris} objects={len(objs)}")

    metrics = {
        "frameAnchors": len(present),
        "frameAnchorIds": present,
        "frameAnchorsCreated": created,
        "frameAnchorsAdopted": adopted,
        "voidX": round(void_x, 3),
        "voidY": round(void_y, 3),
        "corridorWidth": round(cw, 3),
        "railingHeight": rail_h,
        "railingPosts": posts,
        "fasciaCells": cells,
        "stairRisers": st["risers"],
        "stairShape": st["shape"],
        "stairTopZ": round(f2, 3),
        "doors": door_count,
        "windows": win_count,
        "displayWalls": gal_count,
        "showcases": n_cases,
        "boards": n_boards + n_boards2 + n_corridor,
        "joists": n_joist,
        "coffers": n_coffer,
        "lanterns": n_lantern,
        "triangles": tris,
        "objects": len(objs),
        "detail": detail_key,
        "legacyReplaced": legacy,
        "legacyPlatesDetected": legacy_plates,
        "legacyPlateFacesCut": legacy_cut["faces"],
        "anchorBoards": n_boards_anchor,
        "windowGlow": win_count,
        "ceilingCaissonZ": [round(top + 0.20, 3), round(top + 0.60, 3)]
        if style == "coffered" else None,
        "objectsBeforeReplacement": before,
        "frameTransformMaxDeltaM": round(worst_pos, 6),
        "frameTransformMaxDeltaDeg": round(math.degrees(worst_rot), 6),
        "layoutPath": _layout_path(params, ctx),
    }
    notes = (f"interior: L1 floor {n_boards} boards, L2 ring plate around a "
             f"{void_x:.1f} x {void_y:.1f} m void, {cw:.1f} m open corridor with "
             f"{posts} railing posts and {cells} 挂落 cells, {st['shape']} stair "
             f"({st['risers']} risers) to z={f2:.2f}, {gal_count} display walls, "
             f"{win_count} windows / {door_count} doors, {n_cases} showcases, "
             f"{style} ceiling, {n_lantern} lanterns; frame anchors "
             f"{len(present)}/15 (adopted {len(adopted)}, created {len(created)}). "
             f"{tris} triangles. Replaced {info['deleted']} previous interior objects.")
    return M.result("generate_interior", ctx, params, objs, arts, metrics, checks,
                    warnings, notes)


def _porcelain(geo, cx, cy, z0, r):
    """Blue-and-white jar for a showcase (lathe-like stacked profile)."""
    profile = ((0.62, 0.00), (0.86, 0.05), (1.00, 0.16), (0.94, 0.30),
               (0.72, 0.40), (0.44, 0.46), (0.40, 0.52), (0.52, 0.56), (0.46, 0.60))
    seg = 10
    rings = []
    for (rf, dz) in profile:
        rings.append([(cx + math.cos(2 * math.pi * i / seg) * r * rf,
                       cy + math.sin(2 * math.pi * i / seg) * r * rf,
                       z0 + dz * r * 3.0) for i in range(seg)])
    geo.sweep(rings, caps=True)
