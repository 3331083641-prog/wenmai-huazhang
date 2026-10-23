"""Detail-level assertions for the pieces touched in this refinement pass.

Run against the audit build (collections still separate):

    blender -b .../wenmai_gallery_audit.blend -P audit_details.py

Everything is measured from the mesh, not from object names, because several
props are joined into a single object at the end of their builder.
"""
from __future__ import annotations

import bpy
from mathutils import Vector


def bbox(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def say(label, lo, hi):
    print("  %-22s x[%6.3f,%6.3f] y[%6.3f,%6.3f] z[%6.3f,%6.3f]"
          % (label, lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))


def world_verts(obj):
    m = obj.matrix_world
    return [m @ v.co for v in obj.data.vertices]


def near(pts, x, y, r=0.55):
    return [p for p in pts if abs(p.x - x) < r and abs(p.y - y) < r]


def main():
    print("\n== side veranda ==")
    obj = bpy.data.objects.get("VER_Side")
    if obj is None:
        print("  MISSING VER_Side")
    else:
        lo, hi = bbox(obj)
        say("VER_Side", lo, hi)
        print("  faces %d | +X only: %s | inside plinth: %s"
              % (len(obj.data.polygons), lo.x > 4.0,
                 hi.x < 7.0 and abs(hi.y) < 7.0 and abs(lo.y) < 7.0))

    print("\n== plaque ==")
    board = bpy.data.objects.get("PROP_Plaque")
    if board is None:
        print("  MISSING PROP_Plaque")
    else:
        lo, hi = bbox(board)
        say("PROP_Plaque", lo, hi)
        mats = [s.material.name for s in board.material_slots if s.material]
        print("  size %.2f x %.2f x %.2f | slots: %s"
              % (hi.x - lo.x, hi.z - lo.z, hi.y - lo.y, ", ".join(mats)))
        print("  red field present:", any("red_deep" in m for m in mats))
        print("  gold glyphs present:", any("gold_light" in m for m in mats))
        gate = bpy.data.objects.get("LANTERN_Gate")
        if gate is not None:
            gl, gh = bbox(gate)
            say("LANTERN_Gate", gl, gh)
            print("  lantern clear of plaque:", gh.z <= lo.z + 1e-4,
                  "(gap %.3f m)" % (lo.z - gh.z))

    print("\n== planting pits ==")
    plants = bpy.data.objects.get("PROP_Plants")
    spots = ((5.35, 5.30), (5.90, -3.30), (-2.10, 6.10 - 0.55))
    if plants is None:
        print("  MISSING PROP_Plants")
    else:
        pts = world_verts(plants)
        for sx, sy in spots:
            local = near(pts, sx, sy)
            curbs = [p for p in local if 0.05 < p.z < 0.13]
            print("  pit at (%5.2f,%5.2f): %3d verts, %3d in curb band %s"
                  % (sx, sy, len(local), len(curbs), "OK" if len(curbs) > 20 else "CHECK"))

    print("\n== left elevation ==")
    lfx = bpy.data.objects.get("PROP_LeftFacade")
    if lfx is None:
        print("  MISSING PROP_LeftFacade")
    else:
        lo, hi = bbox(lfx)
        say("PROP_LeftFacade", lo, hi)
        mats = sorted({s.material.name for s in lfx.material_slots if s.material})
        print("  faces %d | slots: %s" % (len(lfx.data.polygons), ", ".join(mats)))
        print("  -X side only: %s | protrudes past wall plane (%.2f): %s"
              % (hi.x < -4.04, lo.x, lo.x < -4.24))
        print("  inside plinth: %s" % (lo.x > -7.0 and abs(lo.y) < 7.0 and abs(hi.y) < 7.0))
        # the blind window must not break through into the interior
        print("  stays out of the room (inner face -4.04): %s" % (hi.x <= -4.04 + 1e-6))

    print("\n== roof tiles ==")
    for name in ("TILE_Main", "TILE_Lower"):
        obj = bpy.data.objects.get(name)
        if obj is None:
            print("  MISSING", name)
            continue
        lo, hi = bbox(obj)
        say(name, lo, hi)
        print("  verts %d faces %d" % (len(obj.data.vertices), len(obj.data.polygons)))
    print()


if __name__ == "__main__":
    main()