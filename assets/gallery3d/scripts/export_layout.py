"""Write the web-facing layout contract for the gallery.

  blender -b blender/wenmai_gallery.blend -P export_layout.py

Everything here is read out of the built .blend, so the web never duplicates
hand-typed numbers:

  GALWALL_<id> empties  -> display-wall rectangles (centre, normal, size)
  FRAME_F1/F2_###       -> artwork anchors (wall id, u/v, frame size)
  CAM_*                 -> camera presets (position, target, lens)
  mesh bounds           -> building envelope

Writes the canonical copy under exports/ and the import copy under
frontend/src/features/heritage-gallery/data/.
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


def to_web(v) -> list:
    """Blender (x, y, z) -> three.js (x, z, -y)."""
    return [round(v[0], 4), round(v[2], 4), round(-v[1], 4)]


def facing_of(obj) -> tuple:
    d = obj.matrix_world.to_3x3() @ Vector((0.0, 1.0, 0.0))
    d.normalize()
    return (d.x, d.z, -d.y)


def rotation_of(obj) -> float:
    """Anchor/wall rotationY in web convention: plane faces +Z at rotation 0."""
    nx, _, nz = facing_of(obj)
    return round(math.atan2(nx, nz), 4)


def empty_props(obj) -> dict:
    return {k: obj[k] for k in obj.keys() if not k.startswith("_")}


def walls():
    out = []
    for obj in bpy.data.objects:
        if obj.type != "EMPTY" or not obj.name.startswith("GALWALL_"):
            continue
        props = empty_props(obj)
        wid = obj.name.replace("GALWALL_", "")
        out.append({
            "id": wid,
            "floor": int(props.get("floor", 1)),
            "center": to_web(obj.matrix_world.translation),
            "rotationY": rotation_of(obj),
            "size": [round(float(props.get("width", 1.6)), 3),
                     round(float(props.get("height", 2.6)), 3)],
            "label": props.get("label", wid),
        })
    out.sort(key=lambda w: w["id"])
    return out


def frames(wall_index):
    out = []
    for obj in bpy.data.objects:
        if obj.type != "EMPTY" or not obj.name.startswith("FRAME_F"):
            continue
        props = empty_props(obj)
        parts = obj.name.split("_")
        floor = int(parts[1][1])
        idx = int(parts[2])
        size = props.get("frame_size") or [1.0, 0.85]
        wid = props.get("wall_id", "")
        wall = wall_index.get(wid)
        out.append({
            "id": obj.name,
            "floor": floor,
            "index": idx,
            "position": to_web(obj.matrix_world.translation),
            "rotationY": rotation_of(obj),
            "wallId": wid,
            "group": wid.split("-", 1)[1] if "-" in wid else "wall",
            "size": [round(float(size[0]), 3), round(float(size[1]), 3)],
            "u": round(float(props.get("u", 0.5)), 4),
            "v": round(float(props.get("v", 0.5)), 4),
            "label": props.get("label", obj.name),
            "rotZ": round(float(obj.rotation_euler.z), 4),
            "wallSize": wall["size"] if wall else None,
        })
    out.sort(key=lambda f: (f["floor"], f["index"]))
    return out


def cameras():
    out = []
    for obj in bpy.data.objects:
        if obj.type != "CAMERA" or not obj.name.startswith("CAM_"):
            continue
        mw = obj.matrix_world
        props = empty_props(obj)
        if "target" in props:
            target = Vector([float(v) for v in props["target"]])
        else:
            fwd = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
            target = mw.translation + fwd * ((Vector((0, 0, 4.0)) - mw.translation).dot(fwd))
        out.append({
            "id": obj.name.replace("CAM_", "").lower(),
            "position": to_web(mw.translation),
            "target": to_web(target),
            "lens": round(obj.data.lens, 1),
            "sensor": round(obj.data.sensor_width, 1),
            "fov": round(math.degrees(2 * math.atan(obj.data.sensor_width / 2 / obj.data.lens)), 2),
        })
    out.sort(key=lambda c: c["id"])
    return out


def envelope():
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        for c in obj.bound_box:
            w = obj.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    tris = 0
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.data.calc_loop_triangles()
            tris += len(obj.data.loop_triangles)
    return {
        "min": [round(lo.x, 3), round(lo.z, 3), round(-hi.y, 3)],
        "max": [round(hi.x, 3), round(hi.z, 3), round(-lo.y, 3)],
        "baseSize": G.BASE_SIZE,
        "baseThickness": G.BASE_THICKNESS,
        "floor1Z": G.Z_F1,
        "floor2Z": G.Z_F2,
        "floor1Height": G.F1_H,
        "floor2Height": G.F2_H,
        "topZ": G.Z_TOP,
        "eaveZ": G.EAVE_Z,
        "ridgeZ": G.RIDGE_Z,
        "footprintX": G.BUILD_X,
        "footprintZ": G.BUILD_DEPTH,
        "hallOffsetZ": round(-G.BUILD_Y, 3),
        "triangles": tris,
    }


def main():
    wall_list = walls()
    wall_index = {w["id"]: w for w in wall_list}
    frame_list = frames(wall_index)
    doc = {
        "schema": 2,
        "generatedBy": "assets/gallery3d/scripts/export_layout.py",
        "units": "metre",
        "up": "Y (three.js), converted from Blender Z-up",
        "envelope": envelope(),
        "walls": wall_list,
        "frames": frame_list,
        "cameras": cameras(),
        "counts": {"floor1": 0, "floor2": 0},
    }
    for f in frame_list:
        doc["counts"][f"floor{f['floor']}"] += 1

    dst = os.path.join(G.build_dir(), "exports", "gallery_layout.json")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    body = json.dumps(doc, indent=1, ensure_ascii=False)
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(body + "\n")

    web_dir = os.path.abspath(os.path.join(
        G.build_dir(), "..", "..", "frontend", "src", "features",
        "heritage-gallery", "data"))
    os.makedirs(web_dir, exist_ok=True)
    with open(os.path.join(web_dir, "gallery_layout.json"), "w", encoding="utf-8") as fh:
        fh.write(body + "\n")
    G.report(f"layout written: walls={len(wall_list)} "
             f"frames f1={doc['counts']['floor1']} f2={doc['counts']['floor2']} "
             f"cameras={len(doc['cameras'])} tris={doc['envelope']['triangles']}")


if __name__ == "__main__":
    main()