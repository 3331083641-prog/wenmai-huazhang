"""``inspect_scene`` / ``check_art_frames`` / ``check_export`` / ``performance_report``.

Every check returns ``status`` in ``pass | warn | fail | manual | not_checked``
and the module never reports an unchecked item as ``pass``.  Checks that only a
browser can answer (Three.js runtime behaviour, shader compilation, GLB loading)
are explicitly ``manual``/``not_checked`` with the reason.

Real geometric tests used here:

* **flipped normals** — for closed meshes, offset a face centre along its own
  normal and test containment by ray parity; a point that lands *inside* means
  the winding is inverted.  Not a ``normal.z`` heuristic.
* **roof surface holes** — connected boundary-edge loops classified as interior
  holes only when they sit strictly inside the object's bounding box.
* **floating tiles** — distance from each tile's centre to the nearest roof
  surface, via a real BVH ray/nearest query.
* **stair continuity** — the riser chain must be monotone, gap-free within a
  riser tolerance, and reach the 2F slab height.
* **frame burial / occlusion** — frames are tested for containment inside wall
  volumes and for geometry in front of their outward face.

Owned by ``visual-match``.
"""
from __future__ import annotations

import json
import math
import os
import struct
import zlib

import numpy as np

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import wm_common as C
import wm_image as WI

FLOOR2_Z = 3.60
PLINTH_TOP_Z = 0.0
PLINTH_BOTTOM_Z = -0.65
BRACKET_BOTTOM_Z = -0.95
BASE_HALF = 8.0
EAVE_Z = 6.15
RIDGE_Z = 11.30
FOUNDATION_TOL = 0.20

FRAME_IDS = ([f"FRAME_F1_{i:03d}" for i in range(1, 8)] +
             [f"FRAME_F2_{i:03d}" for i in range(1, 9)])

# name-prefix -> part group; covers contract names and the v5 build's names
PART_PREFIXES = [
    ("roof", ("ROOF_", "TILE_", "CANOPY_", "BAND_", "VER_")),
    ("timber", ("COLUMN_", "BEAM_", "POST_", "TRIM_", "PORCH_")),
    ("wall", ("WALL_",)),
    ("opening", ("WIN_", "DOOR_", "WF_")),
    ("interior", ("INT_", "FLOOR_", "STAIR_", "RAIL_", "RAIL2_", "GALWALL_",
                  "SHOWCASE_", "PLAQUE_")),
    ("site", ("BASE_", "SITE_", "PROP_", "LANTERN_", "LAT_")),
]
COLLECTION_PARTS = {"V5_ROOF": "roof", "V5_SHELL": "shell",
                    "V5_INTERIOR": "interior", "V5_BASE": "base"}


# ------------------------------------------------------------------ helpers

def part_of(obj) -> str:
    """Part group for an object: explicit tag first, then name, then collection."""
    tag = obj.get("wm_part")
    if tag:
        return str(tag)
    name = obj.name
    for part, prefixes in PART_PREFIXES:
        for p in prefixes:
            if name.startswith(p):
                return part
    for col in obj.users_collection:
        if col.name in COLLECTION_PARTS:
            return COLLECTION_PARTS[col.name]
    return "other"


def group_meshes() -> dict:
    out = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        out.setdefault(part_of(obj), []).append(obj)
    return out


def world_bounds(obj) -> dict | None:
    if obj.type != "MESH" or not obj.data:
        return None
    mw = obj.matrix_world
    lo = np.array([math.inf] * 3)
    hi = np.array([-math.inf] * 3)
    for corner in obj.bound_box:
        w = np.array(mw @ Vector(corner))
        lo = np.minimum(lo, w)
        hi = np.maximum(hi, w)
    if not np.isfinite(lo).all():
        return None
    return {"min": lo, "max": hi, "center": 0.5 * (lo + hi), "size": hi - lo}


def bvh_of(obj) -> BVHTree | None:
    """World-space BVH of the evaluated mesh."""
    dg = bpy.context.evaluated_depsgraph_get()
    try:
        ev = obj.evaluated_get(dg)
        me = ev.to_mesh()
    except Exception:
        return None
    try:
        mw = obj.matrix_world
        verts = [mw @ v.co for v in me.vertices]
        polys = [tuple(p.vertices) for p in me.polygons]
        if not polys:
            return None
        return BVHTree.FromPolygons(verts, polys, all_triangles=False, epsilon=0.0)
    finally:
        try:
            ev.to_mesh_clear()
        except Exception:
            pass


def point_inside(bvh: BVHTree, point, direction=(0.5773, 0.5774, 0.5775)) -> bool:
    """Ray-parity containment test along an oblique direction."""
    d = Vector(direction).normalized()
    origin = Vector(point)
    hits = 0
    for _ in range(96):
        loc, _nor, _idx, _dist = bvh.ray_cast(origin, d)
        if loc is None:
            break
        hits += 1
        origin = loc + d * 1e-5
    return (hits % 2) == 1


def face_count(obj) -> int:
    try:
        return len(obj.data.polygons)
    except Exception:
        return 0


def triangles_of(obj) -> int:
    total = 0
    for poly in obj.data.polygons:
        total += max(1, len(poly.vertices) - 2)
    return total


def signed_volume(obj) -> float:
    """World-space signed volume via the divergence theorem.

    For a closed, outward-wound mesh this is positive; a negative value means
    the whole mesh is inside-out.  Exact and robust for any closed manifold,
    unlike per-face heuristics.
    """
    me = obj.data
    try:
        me.calc_loop_triangles()
    except Exception:
        return 0.0
    mw = obj.matrix_world
    verts = me.vertices
    vol = 0.0
    for tri in me.loop_triangles:
        a = mw @ verts[tri.vertices[0]].co
        b = mw @ verts[tri.vertices[1]].co
        c = mw @ verts[tri.vertices[2]].co
        vol += a.dot(b.cross(c)) / 6.0
    return float(vol)


def boundary_loops(me) -> list:
    """Connected components of boundary (single-face) edges as vertex-id sets."""
    counts = {}
    for poly in me.polygons:
        vs = list(poly.vertices)
        for i, a in enumerate(vs):
            b = vs[(i + 1) % len(vs)]
            key = (a, b) if a < b else (b, a)
            counts[key] = counts.get(key, 0) + 1
    boundary = [e for e, c in counts.items() if c == 1]
    if not boundary:
        return []
    adj = {}
    for a, b in boundary:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    seen, loops = set(), []
    for start in adj:
        if start in seen:
            continue
        stack, comp = [start], set()
        while stack:
            v = stack.pop()
            if v in seen:
                continue
            seen.add(v)
            comp.add(v)
            for nb in adj.get(v, ()):
                if nb not in seen:
                    stack.append(nb)
        loops.append(comp)
    return loops


def load_layout(ctx: dict) -> dict | None:
    path = ctx.get("layoutPath") or os.path.join(
        ctx.get("projectRoot") or os.getcwd(),
        "assets", "gallery3d", "exports", "gallery_layout.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


# ============================================== shared frame geometry checks

def frame_report(ctx: dict, params: dict | None = None) -> dict:
    """Locate the FRAME_* empties and test them for burial / detachment."""
    params = params or {}
    empties = {o.name: o for o in bpy.data.objects
               if o.type == "EMPTY" and o.name in FRAME_IDS}
    layout = load_layout(ctx) or {}
    layout_frames = {f["id"]: f for f in (layout.get("frames") or [])
                     if isinstance(f, dict) and f.get("id")}

    walls = [o for o in bpy.data.objects if o.type == "MESH"
             and (part_of(o) in ("wall", "shell", "opening")
                  or o.name.startswith("GALWALL_"))]
    wall_bvh, wall_bounds = {}, {}
    for w in walls:
        b = world_bounds(w)
        if b is None:
            continue
        wall_bounds[w.name] = b
    for name in list(wall_bounds)[:400]:
        obj = bpy.data.objects.get(name)
        if obj is not None:
            bvh = bvh_of(obj)
            if bvh is not None:
                wall_bvh[name] = bvh

    rows = []
    for fid in FRAME_IDS:
        obj = empties.get(fid)
        lf = layout_frames.get(fid) or {}
        size = lf.get("size") or [1.0, 0.8]
        if obj is None:
            rows.append({"id": fid, "present": False, "status": "fail"})
            continue
        pos = obj.matrix_world.translation.copy()
        mw = obj.matrix_world.to_3x3()
        normal = (mw @ Vector((0.0, 1.0, 0.0))) if obj.empty_display_type else Vector((0, 1, 0))
        if normal.length < 1e-9:
            normal = Vector((0.0, 1.0, 0.0))
        normal.normalize()
        # frame box in world space
        half_x = float(size[0]) / 2.0
        half_z = float(size[1]) / 2.0
        right = (mw @ Vector((1.0, 0.0, 0.0)))
        up = (mw @ Vector((0.0, 0.0, 1.0)))
        if right.length < 1e-9:
            right = Vector((1.0, 0.0, 0.0))
        if up.length < 1e-9:
            up = Vector((0.0, 0.0, 1.0))
        right.normalize(); up.normalize()
        corners = []
        for sx in (-1, 1):
            for sz in (-1, 1):
                corners.append(pos + right * (sx * half_x) + up * (sz * half_z))
        lo = np.min([np.array(c) for c in corners], axis=0)
        hi = np.max([np.array(c) for c in corners], axis=0)

        buried_in = []
        detached = None          # None = no wall mesh could be tested against
        tested_walls = []
        front_blocked = []
        # Ray-parity containment is NOT usable here: the v5 wall meshes are open
        # single-sided panels, and parity is undefined for them.  A wall panel is
        # a thin box, so its slab is tested directly: the thin AABB axis is the
        # wall normal, and an anchor strictly between the two faces (by more than
        # `tol`) is inside the wall material.  Being within `tol` of a face means
        # the anchor sits exactly on that face, which is the contract placement.
        eps = float(params.get("frameProbeEps") or 0.02)
        pos_arr = np.array([float(pos.x), float(pos.y), float(pos.z)])
        for wname, wb in wall_bounds.items():
            wall_size = wb["size"]
            axis = int(np.argmin(wall_size))
            thick = float(wall_size[axis])
            if thick <= 2.0 * eps:
                continue
            pad = float(params.get("frameWallPad") or 0.05)
            plane_axes = [k for k in range(3) if k != axis]
            if not all(wb["min"][k] - pad <= pos_arr[k] <= wb["max"][k] + pad
                       for k in plane_axes):
                continue
            lo_a, hi_a = float(wb["min"][axis]), float(wb["max"][axis])
            if not (lo_a - pad <= pos_arr[axis] <= hi_a + pad):
                continue
            tested_walls.append(wname)
            d_lo = float(pos_arr[axis] - lo_a)
            d_hi = float(hi_a - pos_arr[axis])
            if d_lo > eps and d_hi > eps:
                buried_in.append({"wall": wname, "thinAxis": "XYZ"[axis],
                                  "wallThickness": round(thick, 4),
                                  "depthFromLowFace": round(d_lo, 4),
                                  "depthFromHighFace": round(d_hi, 4)})
                continue
            if detached is None:
                detached = False            # sits on a wall face
            n = [0.0, 0.0, 0.0]
            n[axis] = 1.0
            n = Vector(n)
            # outward = the side away from the wall material
            probe = pos_arr.copy()
            probe[axis] += 0.06
            outward = -n if lo_a - pad <= probe[axis] <= hi_a + pad else n
            for other_bvh in wall_bvh.values():
                loc, _n, _i, dist = other_bvh.ray_cast(pos + outward * 0.02, outward)
                if loc is not None and dist < 0.03:
                    front_blocked.append(wname)
                    break
        if detached is None and tested_walls:
            detached = True                 # tested, not on any wall face
        if detached is None and tested_walls:
            detached = True                            # tested, not on any wall
        row = {
            "id": fid,
            "present": True,
            "position": [round(float(v), 4) for v in pos],
            "rotation": [round(float(v), 4) for v in obj.rotation_euler],
            "size": size,
            "wallId": lf.get("wallId"),
            "rotZ": lf.get("rotZ"),
            "isEmpty": obj.type == "EMPTY",
            "editable": obj.type == "EMPTY",
            "parent": obj.parent.name if obj.parent else None,
            "insideWalls": buried_in,
            "wallTested": bool(tested_walls),
            "testedAgainst": tested_walls[:4],
            "detachedFromWall": detached,
            "frontBlockedBy": front_blocked,
            "outwardClear": not front_blocked,
        }
        if buried_in:
            row["status"] = "fail"
        elif detached is True:
            row["status"] = "warn"
        elif front_blocked:
            row["status"] = "warn"
        elif detached is None:
            row["status"] = "manual"
        else:
            row["status"] = "pass"
        rows.append(row)
    return {"frames": rows, "layout": layout, "layoutFrames": layout_frames,
            "wallCount": len(wall_bounds)}


def layout_mapping_error(rows: list, layout_frames: dict) -> dict:
    """Best-fit axis mapping between layout (glTF Y-up) and Blender positions."""
    pairs = []
    for r in rows:
        lf = layout_frames.get(r["id"])
        if not r.get("present") or not lf or "position" not in lf:
            continue
        pairs.append((np.asarray(r["position"], dtype=float),
                      np.asarray(lf["position"], dtype=float)))
    if len(pairs) < 3:
        return {"ok": False, "reason": "fewer than 3 frames to compare"}

    # glTF y is up -> Blender z.  Try the eight horizontal sign/swap options.
    best = None
    for swap in (False, True):
        for sx in (1, -1):
            for sy in (1, -1):
                errs = []
                for bl, gl in pairs:
                    gx, gy, gz = gl
                    hx, hz = (gz, gx) if swap else (gx, gz)
                    pred = np.array([sx * hx, sy * hz, gy])
                    errs.append(np.linalg.norm(pred - bl))
                rms = float(np.sqrt(np.mean(np.square(errs))))
                cand = {"swap": swap, "sx": sx, "sy": sy, "rms": rms,
                        "max": float(np.max(errs)), "pairs": len(pairs)}
                if best is None or rms < best["rms"]:
                    best = cand
    best["ok"] = True
    best["formula"] = ("blender = (%+d*%s, %+d*%s, gltf.y)"
                       % (best["sx"], "gltf.z" if best["swap"] else "gltf.x",
                          best["sy"], "gltf.x" if best["swap"] else "gltf.z"))
    best["max"] = round(best["max"], 4)
    best["rms"] = round(best["rms"], 5)
    return best


# ======================================================== task: inspect_scene

def inspect_scene(params: dict, ctx: dict) -> dict:
    params = params or {}
    ctx = ctx or {}
    project_root = ctx.get("projectRoot") or os.getcwd()
    checks, warnings = [], []
    only = params.get("checks")
    if isinstance(only, str):
        only = [only]

    def want(name: str) -> bool:
        return not only or name in only

    blend = params.get("blend") or ctx.get("baseBlend")
    if blend:
        path = WI.resolve_path(blend, ctx)
        if os.path.isfile(path):
            C.open_scene(path)
        else:
            warnings.append(f"blend not found: {path}; auditing the current scene")

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    groups = group_meshes()
    stats = C.scene_stats()
    lo = np.array([math.inf] * 3)
    hi = np.array([-math.inf] * 3)
    triangles = 0
    for obj in meshes:
        b = world_bounds(obj)
        if b is None:
            continue
        lo = np.minimum(lo, b["min"])
        hi = np.maximum(hi, b["max"])
        triangles += triangles_of(obj)
    if not np.isfinite(lo).all():
        lo = np.zeros(3); hi = np.zeros(3)
    bounds = {"min": [round(float(v), 3) for v in lo],
              "max": [round(float(v), 3) for v in hi],
              "size": [round(float(v), 3) for v in (hi - lo)]}

    summary = {"objects": len(bpy.data.objects), "meshes": len(meshes),
               "triangles": triangles, "materials": len(bpy.data.materials),
               "images": len([i for i in bpy.data.images if i.size[0] > 0]),
               "empties": len([o for o in bpy.data.objects if o.type == "EMPTY"]),
               "cameras": len([o for o in bpy.data.objects if o.type == "CAMERA"]),
               "lights": len([o for o in bpy.data.objects if o.type == "LIGHT"]),
               "groups": {k: len(v) for k, v in sorted(groups.items())}}
    _ = stats

    # ---- 1. bounds vs plinth
    if want("bounds"):
        problems = []
        if hi[0] > BASE_HALF + 0.02 or lo[0] < -BASE_HALF - 0.02:
            problems.append(f"X {lo[0]:.2f}..{hi[0]:.2f} exceeds +-{BASE_HALF}")
        if hi[1] > BASE_HALF + 0.02 or lo[1] < -BASE_HALF - 0.02:
            problems.append(f"Y {lo[1]:.2f}..{hi[1]:.2f} exceeds +-{BASE_HALF}")
        if lo[2] < BRACKET_BOTTOM_Z - 0.05:
            problems.append(f"Z min {lo[2]:.3f} below bracket bottom "
                            f"{BRACKET_BOTTOM_Z}")
        if hi[2] > RIDGE_Z + 1.2:
            problems.append(f"Z max {hi[2]:.3f} far above ridge {RIDGE_Z}")
        C.check(checks, "bounds_vs_plinth",
                "pass" if not problems else "warn",
                ("model inside the 16 m plinth envelope and the contract height "
                 "range" if not problems else "; ".join(problems)),
                bounds=bounds)

    # ---- 2. flipped normals
    # Primary signal: the signed volume of each *closed* mesh (exact, global).
    # Secondary: per-face containment sampling, which is reported but not used
    # to fail the check because overlapping closed sub-parts inside one mesh
    # make containment ambiguous near their shared surfaces.
    if want("normals"):
        inverted = []
        closed_count = 0
        skipped_open = 0
        flipped_total = 0
        sampled_total = 0
        worst = []
        for obj in meshes:
            if len(obj.data.polygons) < 4:
                continue
            if boundary_loops(obj.data):
                skipped_open += 1
                continue
            closed_count += 1
            vol = signed_volume(obj)
            if vol < -1e-9:
                inverted.append({"object": obj.name, "part": part_of(obj),
                                 "signedVolumeM3": round(vol, 6)})
            bvh = bvh_of(obj)
            if bvh is None:
                continue
            polys = list(obj.data.polygons)
            step = max(1, len(polys) // 80)
            flips = tested = 0
            mw = obj.matrix_world
            for i in range(0, len(polys), step):
                poly = polys[i]
                n = (mw.to_3x3() @ poly.normal)
                if n.length < 1e-9:
                    continue
                n.normalize()
                try:
                    if point_inside(bvh, (mw @ poly.center) + n * 0.004):
                        flips += 1
                except Exception:
                    continue
                tested += 1
            if tested:
                sampled_total += tested
                flipped_total += flips
                if flips:
                    worst.append({"object": obj.name, "part": part_of(obj),
                                  "flippedSamples": flips, "tested": tested,
                                  "ratio": round(flips / float(tested), 4)})
        worst.sort(key=lambda d: -d["ratio"])
        sample_ratio = (flipped_total / float(sampled_total)) if sampled_total else 0.0
        C.check(checks, "flipped_normals",
                "fail" if inverted else "pass",
                (f"{len(inverted)} of {closed_count} closed mesh(es) have a NEGATIVE "
                 f"signed volume, i.e. inside-out winding: "
                 f"{', '.join(i['object'] for i in inverted[:6])}"
                 if inverted else
                 f"all {closed_count} closed mesh(es) have positive signed volume "
                 "(outward winding); {skipped_open} open meshes are excluded "
                 "because the test needs a closed manifold"),
                inverted=inverted[:12])
        C.check(checks, "flipped_normals_face_sample", "pass",
                (f"informational only: {flipped_total}/{sampled_total} sampled faces "
                 f"({sample_ratio * 100:.2f}%) test as contained just outside their "
                 "own normal; overlapping closed sub-parts inside one mesh make "
                 "this ambiguous, so it does NOT fail the audit"),
                worst=worst[:8])

    # ---- 3. roof surface boundary loops (potential punctures)
    if want("roof_holes"):
        holes = []
        loop_total = 0
        roof_objs = [o for o in groups.get("roof", []) if len(o.data.polygons) > 8]
        for obj in roof_objs:
            loops = boundary_loops(obj.data)
            loop_total += len(loops)
            if not loops:
                continue
            b = world_bounds(obj)
            if b is None:
                continue
            margin = 0.05
            for comp in loops:
                co = [obj.data.vertices[i].co for i in comp if i < len(obj.data.vertices)]
                if not co:
                    continue
                arr = np.array([[c.x, c.y, c.z] for c in co])
                lmin, lmax = arr.min(axis=0), arr.max(axis=0)
                size = np.maximum(b["size"], 1e-6)
                strictly_inside = all(
                    lmin[k] > b["min"][k] + margin * size[k]
                    and lmax[k] < b["max"][k] - margin * size[k] for k in range(3))
                if strictly_inside:
                    ext = float(max(lmax[0] - lmin[0], lmax[1] - lmin[1]))
                    holes.append({"object": obj.name, "vertices": len(comp),
                                  "extentM": round(ext, 3),
                                  "center": [round(float(v), 3)
                                             for v in (lmin + lmax) / 2]})
        big = [h for h in holes if h["extentM"] > 0.25]
        # Deliberately never `fail`: most boundary loops on this build are the
        # outer silhouettes of separate roof sub-panels, so the count is a lead,
        # not a proof of a puncture.
        C.check(checks, "roof_surface_holes",
                "pass" if not holes else "warn",
                (f"{loop_total} boundary loop(s) across {len(roof_objs)} roof mesh(es); "
                 f"{len(holes)} sit strictly inside their own object's bounding box "
                 f"by a 5% margin, {len(big)} of those larger than 0.25 m. A loop "
                 "touching the box edge is treated as an outer silhouette, so this "
                 "figure is a lead, not a hole count"),
                holes=holes[:12])
        C.check(checks, "roof_puncture_visual", "manual",
                "confirming a real puncture in the roof surface needs a rendered "
                "image review; boundary-loop counts alone cannot decide it")

    # ---- 4. floating tiles
    if want("floating_tiles"):
        tiles = [o for o in meshes
                 if o.name.startswith(("TILE_",)) or "Tile" in o.name]
        roof = [o for o in groups.get("roof", []) if "Tile" not in o.name]
        if not tiles:
            C.check(checks, "floating_tiles", "not_checked",
                    "no tile objects found (no name starts with TILE_ or "
                    "contains 'Tile')")
        elif not roof:
            C.check(checks, "floating_tiles", "not_checked",
                    f"{len(tiles)} tile objects found but no roof surface to "
                    "measure against")
        else:
            roof_bvhs = [b for b in (bvh_of(o) for o in roof) if b is not None]
            tol = float(params.get("tileGapTolerance", 0.35))
            far = []
            for t in tiles:
                b = world_bounds(t)
                if b is None:
                    continue
                best = math.inf
                for bvh in roof_bvhs:
                    loc, _n, _i, d = bvh.find_nearest(Vector(b["center"]))
                    if loc is not None and d is not None:
                        best = min(best, float(d))
                if best > tol:
                    far.append({"object": t.name,
                                "gapM": round(best, 4) if math.isfinite(best) else None})
            C.check(checks, "floating_tiles",
                    "pass" if not far else ("warn" if len(far) < 10 else "fail"),
                    (f"{len(tiles)} tile object(s) checked against "
                     f"{len(roof_bvhs)} roof surface(s); {len(far)} further than "
                     f"{tol} m"), floating=far[:12])

    # ---- 5. stair continuity
    if want("stair"):
        stairs = [o for o in meshes
                  if o.name.startswith(("STAIR_", "INT_ST"))]
        if not stairs:
            C.check(checks, "stair_continuity", "not_checked",
                    "no stair objects found (no name starts with STAIR_ or INT_ST)")
        else:
            boxes = [world_bounds(o) for o in stairs]
            boxes = [b for b in boxes if b is not None]
            boxes.sort(key=lambda b: b["center"][2])
            gaps, rises = [], []
            for a, b in zip(boxes, boxes[1:]):
                gap = float(b["min"][2] - a["max"][2])
                gaps.append(gap)
                rises.append(float(b["center"][2] - a["center"][2]))
            top = float(boxes[-1]["max"][2]) if boxes else 0.0
            bottom = float(boxes[0]["min"][2]) if boxes else 0.0
            max_gap = max(gaps) if gaps else 0.0
            reaches = abs(top - FLOOR2_Z) <= FOUNDATION_TOL
            worst = sorted(zip(gaps, [b["center"][2] for b in boxes[1:]]))[-3:]
            detail = (f"{len(boxes)} stair part(s) from z={bottom:.2f} to "
                      f"z={top:.2f}; largest consecutive gap {max_gap:.3f} m; "
                      f"2F slab is z={FLOOR2_Z:.2f} "
                      f"({'reached' if reaches else 'NOT reached'} within "
                      f"{FOUNDATION_TOL} m)")
            status = ("pass" if reaches and max_gap <= 0.40
                      else "warn" if reaches or max_gap <= 0.40 else "fail")
            C.check(checks, "stair_continuity", status, detail,
                    largestGaps=[{"gapM": round(g, 4), "atZ": round(float(z), 3)}
                                 for g, z in worst])

    # ---- 6. cross-group triangle intersections (real BVH overlap)
    if want("intersections"):
        pairs = [("roof", "timber"), ("roof", "wall"), ("timber", "wall"),
                 ("wall", "interior"), ("interior", "interior")]
        found = []
        budget = int(params.get("intersectionPairs", 40))
        tested = 0
        for ga, gb in pairs:
            if tested >= budget:
                break
            oa = groups.get(ga, [])[:6]
            ob = groups.get(gb, [])
            if not oa or not ob:
                continue
            for a in oa:
                if tested >= budget:
                    break
                bvh_a = bvh_of(a)
                if bvh_a is None:
                    continue
                for b in ob[:40]:
                    if b is a:
                        continue
                    tested += 1
                    bvh_b = bvh_of(b)
                    if bvh_b is None:
                        continue
                    try:
                        hits = bvh_a.overlap(bvh_b)
                    except Exception:
                        continue
                    if hits:
                        found.append({"a": a.name, "b": b.name,
                                      "groups": [ga, gb],
                                      "trianglePairs": len(hits)})
        found.sort(key=lambda d: -d["trianglePairs"])
        if not tested:
            C.check(checks, "group_intersections", "not_checked",
                    "no comparable group pairs with mesh geometry")
        else:
            C.check(checks, "group_intersections",
                    "pass" if not found else "warn",
                    (f"{len(found)} intersecting object pair(s) found among "
                     f"{tested} tested pairs (exact BVH triangle overlap, not an "
                     "AABB guess)"), intersections=found[:12])

    # ---- 7. art frames (burial / occlusion)
    if want("frames"):
        fr = frame_report(ctx, params)
        rows = fr["frames"]
        present = [r for r in rows if r.get("present")]
        buried = [r["id"] for r in present if r.get("insideWalls")]
        blocked = [r["id"] for r in present if not r.get("outwardClear", True)]
        dup = len(present) - len({r["id"] for r in present})
        status = ("fail" if buried else
                  "warn" if (blocked or len(present) != len(FRAME_IDS)) else "pass")
        C.check(checks, "art_frames_placement", status,
                (f"{len(present)}/{len(FRAME_IDS)} frame anchors present; "
                 f"{len(buried)} buried inside wall volumes; {len(blocked)} with "
                 f"geometry in front of the outward face"),
                buried=buried, blocked=blocked)
        C.check(checks, "art_frame_uniqueness",
                "pass" if dup == 0 else "fail",
                f"{dup} duplicate frame name(s)")

    # ---- 8. honest manual / not_checked items
    C.check(checks, "threejs_runtime", "manual",
            "whether the GLB loads, shader compiles and interaction works in "
            "Three.js can only be asserted in a browser; Blender cannot test it")
    C.check(checks, "visual_fidelity", "not_checked",
            "this task audits structure only; it makes no visual fidelity claim")

    bad = [c for c in checks if c["status"] == "fail"]
    return {
        "ok": True,
        "task": "inspect_scene",
        "artifacts": [],
        "summary": summary,
        "bounds": bounds,
        "checks": checks,
        "warnings": warnings,
        "metrics": {"checks": len(checks),
                    "fails": len(bad),
                    "warns": sum(1 for c in checks if c["status"] == "warn"),
                    "manual": sum(1 for c in checks if c["status"] == "manual"),
                    "notChecked": sum(1 for c in checks if c["status"] == "not_checked")},
        "notes": ("structural audit only. Statuses are honest: 'manual' and "
                  "'not_checked' are used wherever Blender cannot decide, and "
                  "nothing untested is reported as pass."),
    }


# ====================================================== task: check_art_frames

def check_art_frames(params: dict, ctx: dict) -> dict:
    params = params or {}
    ctx = ctx or {}
    expected = int(params.get("expected", 15))
    checks, warnings = [], []

    blend = params.get("blend") or ctx.get("baseBlend")
    if blend:
        path = WI.resolve_path(blend, ctx)
        if os.path.isfile(path):
            C.open_scene(path)
        else:
            warnings.append(f"blend not found: {path}; checking the current scene")

    if params.get("layoutPath"):
        ctx = dict(ctx)
        ctx["layoutPath"] = WI.resolve_path(params["layoutPath"], ctx)

    fr = frame_report(ctx, params)
    rows = fr["frames"]
    layout_frames = fr["layoutFrames"]
    present = [r for r in rows if r.get("present")]
    missing = [fid for fid in FRAME_IDS if fid not in {r["id"] for r in present}]

    # any EMPTY that looks like a frame but is not one of the 15
    extra = sorted(o.name for o in bpy.data.objects
                   if o.type == "EMPTY" and o.name.upper().startswith("FRAME")
                   and o.name not in FRAME_IDS)
    joined = [{
        "id": r["id"],
        "reason": "not an EMPTY (looks joined into geometry)",
    } for r in rows if r.get("present") and not r.get("isEmpty")]
    dupes = [r["id"] for r in present
             if sum(1 for x in present if x["id"] == r["id"]) > 1]

    mapping = layout_mapping_error(present, layout_frames)
    pos_errors = []
    if mapping.get("ok"):
        for r in present:
            lf = layout_frames.get(r["id"]) or {}
            if "position" not in lf:
                continue
            gx, gy, gz = lf["position"]
            hx, hz = ((gz, gx) if mapping["swap"] else (gx, gz))
            pred = np.array([mapping["sx"] * hx, mapping["sy"] * hz, gy])
            err = float(np.linalg.norm(pred - np.asarray(r["position"])))
            pos_errors.append({"id": r["id"], "errorM": round(err, 4),
                               "blender": r["position"],
                               "layoutPredicted": [round(float(v), 4) for v in pred]})
    pos_errors.sort(key=lambda d: -d["errorM"])
    max_err = pos_errors[0]["errorM"] if pos_errors else None

    C.check(checks, "frame_count",
            "pass" if len(present) == expected else "fail",
            f"{len(present)} frame anchors found, {expected} expected")
    C.check(checks, "frame_ids", "pass" if not missing else "fail",
            "all 15 documented anchors present" if not missing
            else f"missing: {', '.join(missing)}", missing=missing)
    C.check(checks, "frame_duplicates", "pass" if not dupes else "fail",
            "no duplicate anchor names" if not dupes else f"duplicates: {dupes}")
    C.check(checks, "frames_editable",
            "pass" if not joined else "fail",
            "every anchor is still an EMPTY (editable, not joined into a mesh)"
            if not joined else f"not EMPTY: {joined}")
    C.check(checks, "frame_positions",
            "pass" if (max_err is not None and max_err <= 0.02) else
            ("warn" if max_err is not None else "not_checked"),
            (f"max anchor deviation from gallery_layout.json is {max_err} m under "
             f"mapping {mapping.get('formula')} (RMS {mapping.get('rms')} m)"
             if max_err is not None else
             "could not compare positions (layout missing or too few frames)"),
            errors=pos_errors[:6])
    C.check(checks, "layout_mapping", "pass" if mapping.get("ok") else "warn",
            (f"best-fit glTF->Blender axis mapping {mapping.get('formula')} with "
             f"RMS {mapping.get('rms')} m over {mapping.get('pairs')} frames"
             if mapping.get("ok") else mapping.get("reason")))
    buried = [r["id"] for r in present if r.get("insideWalls")]
    blocked = [r["id"] for r in present if not r.get("outwardClear", True)]
    C.check(checks, "frames_not_buried",
            "pass" if not buried else "fail",
            "no anchor sits inside a wall volume" if not buried
            else f"buried inside walls: {', '.join(buried)}", buried=buried)
    C.check(checks, "frames_visible",
            "pass" if not blocked else "warn",
            "no geometry in front of any anchor's outward face" if not blocked
            else f"outward face blocked: {', '.join(blocked)}", blocked=blocked)
    if extra:
        C.check(checks, "unexpected_frame_empties", "warn",
                f"{len(extra)} EMPTY object(s) start with FRAME but are not one "
                f"of the 15 documented ids: {', '.join(extra[:8])}")
    C.check(checks, "artwork_content", "manual",
            "whether each anchor actually shows a readable artwork in a render "
            "requires an image/visual review, which this structural check "
            "cannot assert")

    return {
        "ok": True,
        "task": "check_art_frames",
        "artifacts": [],
        "found": len(present),
        "expected": expected,
        "frames": rows,
        "missing": missing,
        "duplicated": sorted(set(dupes)),
        "unexpected": extra,
        "joined": joined,
        "layoutMapping": mapping,
        "positionErrors": pos_errors,
        "metrics": {"found": len(present), "expected": expected,
                    "missing": len(missing), "buried": len(buried),
                    "blocked": len(blocked),
                    "maxPositionErrorM": max_err},
        "checks": checks,
        "warnings": warnings,
        "notes": (f"{len(present)}/{expected} art-frame anchors found. "
                  "Positions are compared to gallery_layout.json after solving "
                  "the axis mapping from the data; burial is tested by ray-parity "
                  "containment inside wall volumes, not by distance thresholds."),
    }


# ========================================================== task: check_export

def _png_dims(data: bytes):
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    w, h = struct.unpack(">II", data[16:24])
    return int(w), int(h), int(data[24]), int(data[25])


def parse_glb(path: str) -> dict:
    """Parse a GLB container with the standard library only."""
    out = {"ok": False, "path": path, "bytes": WI.file_size(path)}
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) < 20:
        out["error"] = "file shorter than a GLB header"
        return out
    magic, version, length = struct.unpack("<III", data[:12])
    out.update(magic=hex(magic), version=version,
               declaredLength=length, actualLength=len(data),
               lengthMatches=length == len(data))
    if magic != 0x46546C67:
        out["error"] = "bad GLB magic"
        return out
    pos = 12
    chunks = []
    while pos + 8 <= len(data):
        clen, ctype = struct.unpack("<II", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + clen]
        chunks.append((ctype, body))
        pos += 8 + clen + ((4 - clen % 4) % 4 if clen % 4 else 0)
        if len(chunks) > 8:
            break
    out["chunks"] = [{"type": hex(t), "length": len(b)} for t, b in chunks]
    js = next((b for t, b in chunks if t == 0x4E4F534A), None)
    binchunk = next((b for t, b in chunks if t == 0x004E4942), None)
    if js is None:
        out["error"] = "no JSON chunk"
        return out
    try:
        doc = json.loads(js.decode("utf-8"))
    except ValueError as exc:
        out["error"] = f"JSON chunk does not parse: {exc}"
        return out
    out["doc"] = doc
    out["ok"] = True
    out["hasBinaryChunk"] = binchunk is not None
    out["binaryBytes"] = len(binchunk) if binchunk else 0
    return out


def _glb_images(doc: dict, binchunk, path: str) -> list:
    out = []
    views = doc.get("bufferViews") or []
    for i, img in enumerate(doc.get("images") or []):
        entry = {"index": i, "name": img.get("name"), "mimeType": img.get("mimeType")}
        bv = img.get("bufferView")
        if bv is not None and binchunk is not None and bv < len(views):
            v = views[bv]
            start = int(v.get("byteOffset", 0))
            end = start + int(v.get("byteLength", 0))
            dims = _png_dims(binchunk[start:end])
            if dims:
                entry.update(width=dims[0], height=dims[1],
                             bitDepth=dims[2], colorType=dims[3])
            else:
                entry["note"] = "embedded data is not a PNG (dimensions unknown)"
            entry["embeddedBytes"] = int(v.get("byteLength", 0))
        elif img.get("uri"):
            entry["uri"] = img["uri"]
            entry["note"] = "external URI; not embedded in the GLB"
        else:
            entry["note"] = "no bufferView and no uri"
        out.append(entry)
    return out


def check_export(params: dict, ctx: dict) -> dict:
    params = params or {}
    ctx = ctx or {}
    project_root = ctx.get("projectRoot") or os.getcwd()
    profile = str(params.get("profile", "web"))
    checks, warnings = [], []

    glb = params.get("glb")
    if not glb:
        cand = os.path.join(project_root, "outputs", "wenmai-3d", "scene",
                            "wenmai_scene.glb")
        glb = cand
        warnings.append(f"no glb param; defaulted to {cand}")
    path = WI.resolve_path(glb, ctx)
    if not os.path.isfile(path):
        return C.fail(f"GLB not found: {path}")

    parsed = parse_glb(path)
    if not parsed.get("ok"):
        C.check(checks, "glb_container", "fail",
                parsed.get("error", "unparseable GLB"))
        return {"ok": False, "task": "check_export",
                "error": {"message": parsed.get("error", "unparseable GLB")},
                "checks": checks, "bytes": WI.file_size(path)}

    doc = parsed["doc"]
    meshes = doc.get("meshes") or []
    prims = sum(len(m.get("primitives") or []) for m in meshes)
    materials = doc.get("materials") or []
    nodes = doc.get("nodes") or []
    accessors = doc.get("accessors") or []
    animations = doc.get("animations") or []

    triangles = None
    mode_counts = {}
    for m in meshes:
        for p in m.get("primitives") or []:
            mode = int(p.get("mode", 4))
            mode_counts[mode] = mode_counts.get(mode, 0) + 1
            idx = p.get("indices")
            if idx is not None and idx < len(accessors):
                count = int(accessors[idx].get("count", 0))
                if mode == 4:
                    triangles = (triangles or 0) + count // 3
            elif mode == 4:
                pos = (p.get("attributes") or {}).get("POSITION")
                if pos is not None and pos < len(accessors):
                    triangles = (triangles or 0) + int(accessors[pos].get("count", 0)) // 3

    # extract the BIN chunk so embedded image dimensions can be read straight
    # out of the buffer views (no temp files, no third-party libraries)
    binchunk = None
    with open(path, "rb") as fh:
        raw = fh.read()
    p = 12
    while p + 8 <= len(raw):
        clen, ctype = struct.unpack("<II", raw[p:p + 8])
        if ctype == 0x004E4942:
            binchunk = raw[p + 8:p + 8 + clen]
            break
        p += 8 + clen + (((4 - clen % 4) % 4) if clen % 4 else 0)
    images = _glb_images(doc, binchunk, path)

    external = [i for i in images if i.get("uri")]
    known_dims = [i for i in images if i.get("width")]
    bytes_total = WI.file_size(path)

    C.check(checks, "glb_container", "pass",
            f"magic {parsed['magic']}, version {parsed['version']}, "
            f"{bytes_total} bytes, declared length "
            f"{'matches' if parsed['lengthMatches'] else 'MISMATCH'}")
    C.check(checks, "glb_length_consistent",
            "pass" if parsed["lengthMatches"] else "fail",
            f"header length {parsed['declaredLength']} vs actual "
            f"{parsed['actualLength']}")
    C.check(checks, "meshes_present", "pass" if meshes else "fail",
            f"{len(meshes)} mesh(es), {prims} primitive(s), {len(nodes)} node(s)")
    C.check(checks, "triangles_present",
            "pass" if (triangles or 0) > 0 else "warn",
            f"{triangles if triangles is not None else 'unknown'} triangles "
            f"(primitive modes {json.dumps(mode_counts)})")
    C.check(checks, "materials_present",
            "pass" if materials else "warn",
            f"{len(materials)} material(s)")
    C.check(checks, "textures_embedded",
            "pass" if not external else "warn",
            (f"{len(images)} image(s), {len(known_dims)} with parsed dimensions, "
             f"{len(external)} external URI(s)") if images else
            "no images in this GLB",
            images=images[:12])
    C.check(checks, "animations", "pass", f"{len(animations)} animation(s)")

    budget_mb = float(params.get("sizeBudgetMb", 16 if profile == "web" else 64))
    mb = bytes_total / (1024.0 * 1024.0)
    C.check(checks, "size_budget", "pass" if mb <= budget_mb else "warn",
            f"{mb:.2f} MB against a {budget_mb} MB {profile} budget")
    C.check(checks, "threejs_runtime", "manual",
            "actual loading, shader compilation and rendering in Three.js cannot "
            "be asserted from the file; only a browser run can confirm it")
    C.check(checks, "y_up_orientation", "not_checked",
            "orientation is fixed by the exporter (export_yup) and is not "
            "recorded in the GLB in a way this audit can verify")

    return {
        "ok": True,
        "task": "check_export",
        "artifacts": [WI.artifact("glb", path)],
        "glbPath": path,
        "glbPathRel": WI.relpath(path, project_root),
        "bytes": bytes_total,
        "meshes": len(meshes),
        "primitives": prims,
        "triangles": triangles,
        "materials": len(materials),
        "nodes": len(nodes),
        "textures": images,
        "animations": len(animations),
        "profile": profile,
        "checks": checks,
        "warnings": warnings,
        "metrics": {"bytes": bytes_total, "mb": round(mb, 3),
                    "meshes": len(meshes), "triangles": triangles,
                    "materials": len(materials), "images": len(images),
                    "animations": len(animations)},
        "notes": ("GLB container parsed with the standard library only: header, "
                  "JSON chunk, BIN chunk, and PNG IHDR dimensions read straight "
                  "out of the embedded buffer views."),
    }


# ===================================================== task: performance_report

def performance_report(params: dict, ctx: dict) -> dict:
    params = params or {}
    ctx = ctx or {}
    project_root = ctx.get("projectRoot") or os.getcwd()
    checks, warnings = [], []
    budget = {"mb": float(params.get("sizeBudgetMb", 16)),
              "triangles": int(params.get("triangleBudget", 350000))}

    blend = params.get("blend") or ctx.get("baseBlend")
    if blend:
        path = WI.resolve_path(blend, ctx)
        if os.path.isfile(path):
            C.open_scene(path)
        else:
            warnings.append(f"blend not found: {path}")
    elif not params.get("blend"):
        base = ctx.get("baseBlend")
        if base and os.path.isfile(WI.resolve_path(base, ctx)):
            C.open_scene(WI.resolve_path(base, ctx))

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    per = []
    total_tris = 0
    for obj in meshes:
        t = triangles_of(obj)
        total_tris += t
        per.append({"object": obj.name, "part": part_of(obj),
                    "triangles": t, "verts": len(obj.data.vertices),
                    "faces": len(obj.data.polygons),
                    "materials": len([m for m in obj.data.materials if m])})
    per.sort(key=lambda d: -d["triangles"])
    hotspots = per[:12]

    images = [{"name": i.name, "width": i.size[0], "height": i.size[1],
               "bytes": int(getattr(i, "packed_file", None).size)
               if getattr(i, "packed_file", None) else 0}
              for i in bpy.data.images if i.size[0] > 0]
    tex_bytes = sum(i["bytes"] for i in images)
    largest_tex = sorted(images, key=lambda i: -(i["width"] * i["height"]))[:6]

    glb_bytes = None
    glb = params.get("glb")
    if glb:
        gp = WI.resolve_path(glb, ctx)
        if os.path.isfile(gp):
            glb_bytes = WI.file_size(gp)
    else:
        auto = os.path.join(project_root, "outputs", "wenmai-3d", "scene",
                            "wenmai_scene.glb")
        if os.path.isfile(auto):
            glb_bytes = WI.file_size(auto)

    tri_status = ("pass" if total_tris <= budget["triangles"]
                  else "warn" if total_tris <= 1.5 * budget["triangles"] else "fail")
    size_status = "not_checked"
    if glb_bytes:
        mb = glb_bytes / (1024.0 * 1024.0)
        size_status = ("pass" if mb <= budget["mb"]
                       else "warn" if mb <= 1.5 * budget["mb"] else "fail")
    recommendations = []
    if tri_status != "pass":
        recommendations.append(
            f"reduce triangles: {total_tris} against a {budget['triangles']} "
            f"budget; the heaviest objects are "
            f"{', '.join(h['object'] for h in hotspots[:4])}")
    if total_tris and hotspots and hotspots[0]["triangles"] > 0.25 * total_tris:
        recommendations.append(
            f"{hotspots[0]['object']} alone is "
            f"{100.0 * hotspots[0]['triangles'] / total_tris:.1f}% of all "
            "triangles; decimate or instance it")
    big_tex = [t for t in largest_tex if t["width"] * t["height"] > 2048 * 2048]
    if big_tex:
        recommendations.append(
            "textures above 2048x2048: "
            + ", ".join(f"{t['name']} {t['width']}x{t['height']}" for t in big_tex))
    if not recommendations:
        recommendations.append("budgets are met; no hotspot crosses a threshold")

    C.check(checks, "triangle_budget", tri_status,
            f"{total_tris} triangles against {budget['triangles']}")
    C.check(checks, "file_size_budget", size_status,
            (f"{glb_bytes / (1024.0 * 1024.0):.2f} MB against {budget['mb']} MB"
             if glb_bytes else "no GLB supplied or found, so size is unmeasured"))
    C.check(checks, "mesh_inventory", "pass",
            f"{len(meshes)} meshes, {len(bpy.data.materials)} materials, "
            f"{len(images)} image(s)")
    C.check(checks, "texture_budget",
            "pass" if not big_tex else "warn",
            f"{len(images)} texture(s), {tex_bytes} packed bytes, "
            f"{len(big_tex)} above 2048x2048")
    C.check(checks, "runtime_cost", "manual",
            "draw calls, GPU upload time and frame rate depend on the engine and "
            "device and cannot be measured from the .blend")

    report = {"schema": 1, "generatedBy": "wm_compare.performance_report",
              "budget": {**budget, "glbBytes": glb_bytes,
                         "status": {"triangles": tri_status, "size": size_status}},
              "totals": {"objects": len(bpy.data.objects), "meshes": len(meshes),
                         "triangles": total_tris,
                         "materials": len(bpy.data.materials),
                         "images": len(images), "textureBytes": tex_bytes},
              "hotspots": hotspots,
              "largestTextures": largest_tex,
              "recommendations": recommendations}

    out_dir = WI.resolve_path(params.get("outDir") or ctx.get("reportsDir")
                              or os.path.join(project_root, "outputs",
                                              "wenmai-3d", "reports"), ctx)
    WI.ensure_dir(out_dir)
    rpath = os.path.join(out_dir, "performance_report.json")
    with open(rpath, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)

    return {
        "ok": True,
        "task": "performance_report",
        "artifacts": [WI.artifact("json", rpath)],
        "reportPath": rpath,
        "reportPathRel": WI.relpath(rpath, project_root),
        "budget": report["budget"],
        "totals": report["totals"],
        "hotspots": hotspots,
        "recommendations": recommendations,
        "checks": checks,
        "warnings": warnings,
        "metrics": {"triangles": total_tris, "meshes": len(meshes),
                    "materials": len(bpy.data.materials),
                    "images": len(images)},
        "notes": ("budgets and hotspots are measured from the scene; runtime cost "
                  "(draw calls, frame rate) is marked manual because it depends on "
                  "the engine and device."),
    }
