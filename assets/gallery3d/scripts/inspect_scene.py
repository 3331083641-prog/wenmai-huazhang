"""Structural audit of the built .blend, run inside Blender.

  blender -b file.blend -P inspect_scene.py
"""
from __future__ import annotations

import json
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def bounds(objs):
    mn = Vector((1e9, 1e9, 1e9))
    mx = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        for corner in o.bound_box:
            w = o.matrix_world @ Vector(corner)
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
    return [round(v, 3) for v in mn], [round(v, 3) for v in mx]


def nonmanifold(obj) -> tuple[int, int]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bad = sum(1 for e in bm.edges if not e.is_manifold)
    loose = sum(1 for v in bm.verts if not v.link_edges)
    bm.free()
    return bad, loose


def main():
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    empties = [o for o in bpy.data.objects if o.type == "EMPTY"]
    cams = [o for o in bpy.data.objects if o.type == "CAMERA"]
    tris = sum(len(o.data.polygons) for o in meshes)
    verts = sum(len(o.data.vertices) for o in meshes)
    mn, mx = bounds(meshes) if meshes else ([0] * 3, [0] * 3)

    per_col = {}
    for o in meshes:
        for c in o.users_collection:
            per_col.setdefault(c.name, {"objs": 0, "faces": 0})
            per_col[c.name]["objs"] += 1
            per_col[c.name]["faces"] += len(o.data.polygons)

    worst = []
    for o in meshes:
        bad, loose = nonmanifold(o)
        if bad:
            worst.append({"obj": o.name, "nonmanifold_edges": bad, "loose_verts": loose})
    worst.sort(key=lambda d: -d["nonmanifold_edges"])

    mats = sorted({m.name for o in meshes for m in o.data.materials if m})
    frames = sorted(o.name for o in empties if o.name.startswith("FRAME_"))
    cam_names = sorted(o.name for o in cams)

    stats = {
        "meshes": len(meshes),
        "empties": len(empties),
        "cameras": len(cams),
        "faces": tris,
        "verts": verts,
        "bounds_min": mn,
        "bounds_max": mx,
        "size": [round(mx[i] - mn[i], 3) for i in range(3)],
        "collections": per_col,
        "materials": mats,
        "frame_anchors": {"count": len(frames), "names": frames},
        "camera_names": cam_names,
        "nonmanifold_top": worst[:8],
        "nonmanifold_objects": len(worst),
    }
    print("SCENE_JSON " + json.dumps(stats))
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "renders", "scene_stats.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=1)


if __name__ == "__main__":
    main()