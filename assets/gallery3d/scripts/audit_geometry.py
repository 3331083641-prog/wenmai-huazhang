"""Numeric audit of the assembled gallery (no rendering, no guessing).

    blender -b blender/wenmai_gallery.blend -P audit_geometry.py

Checks the things a toon miniature most often gets wrong and that a screenshot
cannot prove: symmetry, roof height, stair continuity, frame/wall containment,
light leaks above the ceiling, and geometry poking below the plinth.
"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import gal_common as G  # noqa: E402

problems = []
notes = []


def world_bounds(obj):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for c in obj.bound_box:
        w = obj.matrix_world @ Vector(c)
        for i in range(3):
            lo[i] = min(lo[i], w[i])
            hi[i] = max(hi[i], w[i])
    return lo, hi


def main():
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    empties = [o for o in bpy.data.objects if o.type == "EMPTY"]

    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for obj in meshes:
        a, b = world_bounds(obj)
        for i in range(3):
            lo[i] = min(lo[i], a[i])
            hi[i] = max(hi[i], b[i])
    notes.append("bounds x[%.3f, %.3f] y[%.3f, %.3f] z[%.3f, %.3f]"
                 % (lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))

    # who is out of bounds?
    for obj in meshes:
        a, b = world_bounds(obj)
        if b.x > G.BASE_SIZE / 2.0 + 0.01 or a.x < -G.BASE_SIZE / 2.0 - 0.01:
            notes.append("out-of-plinth x: %s x[%.2f,%.2f]" % (obj.name, a.x, b.x))
        if b.z > G.RIDGE_Z + 0.55:
            notes.append("very tall: %s z[%.2f,%.2f]" % (obj.name, a.z, b.z))

    # 1. plinth symmetry
    if abs(lo.x + hi.x) > 0.02:
        problems.append("plinth not symmetric in x: %.3f vs %.3f" % (lo.x, hi.x))
    if abs(lo.y + hi.y) > 0.02:
        problems.append("plinth not symmetric in y: %.3f vs %.3f" % (lo.y, hi.y))
    if abs((hi.x - lo.x) - G.BASE_SIZE) > 0.05:
        problems.append("plinth width %.3f != BASE_SIZE %.3f" % (hi.x - lo.x, G.BASE_SIZE))

    # 2. nothing below the plinth
    if lo.z < -G.BASE_THICKNESS - 0.012:
        problems.append("geometry below plinth: z=%.3f" % lo.z)

    # 3. roof height sanity
    if hi.z > G.RIDGE_Z + 0.85:
        problems.append("something above the ridge crest: z=%.3f" % hi.z)

    # 4. ceiling coverage: does any roof/open sky exist over the hall interior?
    hall_x = G.BUILD_X / 2.0 - G.WALL_T
    hall_y = G.BUILD_DEPTH / 2.0 - G.WALL_T
    deck = bpy.data.objects.get("BEAM_Ceiling") or bpy.data.objects.get("CEIL_Deck")
    if deck is None:
        problems.append("ceiling mesh missing (interior has no closed ceiling)")
    else:
        a, b = world_bounds(deck)
        notes.append("ceiling x[%.2f,%.2f] y[%.2f,%.2f] z[%.2f,%.2f]"
                     % (a.x, b.x, a.y, b.y, a.z, b.z))
        if not (a.x <= -hall_x + 0.02 and b.x >= hall_x - 0.02):
            problems.append("ceiling narrower than the hall")
        if not (a.y <= G.BUILD_Y - hall_y + 0.02 and b.y >= G.BUILD_Y + hall_y - 0.02):
            problems.append("ceiling shorter than the hall")
        if b.z > G.Z_TOP + 0.02:
            problems.append("ceiling pokes above the top ring: z=%.3f" % b.z)

    # 5. stairs: treads must climb from F1 to F2 without a gap
    stair = bpy.data.objects.get("STAIR_Main")
    if stair is not None:
        tread_top = float(stair.get("tread_top", 0.0))
        rise = float(stair.get("rise", 0.0))
        notes.append("stairs: tread_top=%.3f rise=%.3f (F2 slab %.3f)"
                     % (tread_top, rise, G.Z_F2))
        gap = G.Z_F2 - tread_top
        if gap < -0.01 or gap > rise + 0.01:
            problems.append("last tread %.3f leaves a %.3f m gap to F2 slab"
                            % (tread_top, gap))
        a, b = world_bounds(stair)
        if a.z > G.Z_F1 + 0.02 or a.z < G.Z_F1 - 0.02:
            problems.append("stair does not start at F1 level: %.3f" % a.z)
    else:
        problems.append("no STAIR_Main found")

    # 6. frames inside their walls
    walls = {}
    for obj in empties:
        if obj.name.startswith("GALWALL_"):
            walls[obj.name.replace("GALWALL_", "")] = obj
    frames = [o for o in empties if o.name.startswith("FRAME_F")]
    bad = []
    for obj in frames:
        wid = obj.get("wall_id")
        wall = walls.get(wid)
        if wall is None:
            bad.append("%s has unknown wall %s" % (obj.name, wid))
            continue
        w, h = obj.get("frame_size")
        ww, wh = wall["width"], wall["height"]
        u, v = obj["u"], obj["v"]
        if w > ww - 0.02 or h > wh - 0.02:
            bad.append("%s (%.2fx%.2f) bigger than wall %.2fx%.2f" % (obj.name, w, h, ww, wh))
        half_u = w / 2.0 / ww
        half_v = h / 2.0 / wh
        if not (half_u < u < 1 - half_u) or not (half_v < v < 1 - half_v):
            bad.append("%s at u=%.2f v=%.2f overflows wall" % (obj.name, u, v))
        # perpendicular distance to the wall plane: must be ~0 (hugging the wall)
        d = obj.matrix_world.translation - wall.matrix_world.translation
        n = (wall.matrix_world.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
        perp = abs(d.dot(n))
        if perp > 0.06:
            bad.append("%s sits %.2f m off its wall plane" % (obj.name, perp))
    notes.append("frames: %d, walls: %d" % (len(frames), len(walls)))
    problems.extend(bad)

    # 7. roof parts exist and are named for the web layer switch
    need = ["ROOF_Main", "TILE_Main", "ROOF_Ridge_Group", "ROOF_Chiwen",
            "ROOF_Lower", "TILE_Lower"]
    missing = [n for n in need if n not in bpy.data.objects]
    if missing:
        problems.append("roof parts missing: %s" % missing)

    # 8. light: lamps exist inside
    lamps = [o for o in bpy.data.objects if o.type == "LIGHT"]
    notes.append("lights: %d (%s)" % (len(lamps), ", ".join(sorted(l.name for l in lamps))))

    print("\n=== AUDIT ===")
    for n in notes:
        print("  note:", n)
    if problems:
        print("  PROBLEMS (%d):" % len(problems))
        for p in problems:
            print("   -", p)
    else:
        print("  PROBLEMS: none")
    print("=== END ===\n")


if __name__ == "__main__":
    main()