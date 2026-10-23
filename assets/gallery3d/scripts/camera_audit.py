"""Deterministic view audit: ray-cast a grid through every camera.

  blender -b file.blend -P camera_audit.py

For each camera we print an ASCII category map plus the hit breakdown. This is
the objective substitute for looking at the render: it proves what each preset
camera actually sees, and catches cameras buried in geometry or badly framed.
"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

CATS = [
    ("ROOF", "R"), ("TILE", "R"), ("WALL", "W"), ("FLOOR", "F"), ("STAIR", "S"),
    ("BASE", "B"), ("COLUMN", "C"), ("BEAM", "C"), ("WIND", "L"), ("DOOR", "L"),
    ("RAIL", "L"), ("PROP", "P"), ("MERGE", "?"), ("CASE", "P"), ("LANTERN", "P"),
]


def category(name: str) -> str:
    for prefix, ch in CATS:
        if name.startswith(prefix):
            return ch
    return "."


def audit(cam, nx=48, ny=30):
    scene = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    mw = cam.matrix_world
    origin = mw.translation.copy()
    # camera basis
    right = (mw.to_3x3() @ Vector((1, 0, 0))).normalized()
    up = (mw.to_3x3() @ Vector((0, 1, 0))).normalized()
    fwd = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
    lens = cam.data.lens
    sensor = cam.data.sensor_width
    aspect = nx / ny
    half_w = sensor / 2.0 / lens      # tan of half horizontal fov
    half_h = half_w / aspect

    rows = []
    counts = {}
    depths = []
    for j in range(ny):
        line = []
        vy = (1.0 - 2.0 * (j + 0.5) / ny) * half_h
        for i in range(nx):
            vx = (2.0 * (i + 0.5) / nx - 1.0) * half_w
            direction = (fwd + right * vx + up * vy).normalized()
            hit, loc, _n, _idx, obj, _m = scene.ray_cast(dg, origin, direction)
            if not hit:
                line.append(" ")
                continue
            ch = category(obj.name)
            line.append(ch)
            counts[ch] = counts.get(ch, 0) + 1
            depths.append((loc - origin).length)
        rows.append("".join(line))
    total = nx * ny
    hits = sum(counts.values())
    return {
        "camera": cam.name,
        "lens": lens,
        "hit_pct": round(100.0 * hits / total, 1),
        "categories": {k: round(100.0 * v / total, 1)
                       for k, v in sorted(counts.items(), key=lambda kv: -kv[1])},
        "depth_min": round(min(depths), 2) if depths else None,
        "depth_max": round(max(depths), 2) if depths else None,
        "map": rows,
    }


def main():
    out = []
    cams = sorted([o for o in bpy.data.objects if o.type == "CAMERA"],
                  key=lambda o: o.name)
    for cam in cams:
        r = audit(cam)
        out.append(r)
        print(f"\n=== {r['camera']}  lens={r['lens']}  hit={r['hit_pct']}%  "
              f"depth={r['depth_min']}..{r['depth_max']}")
        print("    " + str(r["categories"]))
        for line in r["map"]:
            print("    |" + line + "|")
    dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "renders", "camera_audit.json")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    main()