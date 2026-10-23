"""Auto-fit every preset camera so the whole model sits inside the frame.

  blender -b file.blend -P fit_cameras.py

Keeps each camera's look direction and solves for the distance that puts the
projected bounding box inside a fixed margin. Prints the final locations so they
can be baked back into build_core.build_cameras, and rewrites the .blend.
"""
from __future__ import annotations

import json
import os
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

MARGIN = 0.055          # normalised NDC margin kept on every side
SHOTS = {
    "CAM_Front34": (1200, 900),
    "CAM_Front": (1000, 900),
    "CAM_Left": (1000, 900),
    "CAM_Right": (1000, 900),
    "CAM_Back": (1000, 900),
    "CAM_Top": (1000, 900),
    "CAM_F1": (1000, 750),
    "CAM_F2": (1000, 750),
    "CAM_Ceiling": (1000, 750),
    "CAM_Detail_Eave": (1000, 750),
}


def world_points(limit=40000):
    """Sample world-space points across every mesh in the scene."""
    pts = []
    step = 1
    total = sum(len(o.data.vertices) for o in bpy.data.objects
                if o.type == "MESH" and o.data)
    if total > limit:
        step = max(1, total // limit)
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.data:
            continue
        mw = obj.matrix_world
        for v in obj.data.vertices[::step]:
            pts.append(mw @ v.co)
    return pts


def extent(scene, cam, pts):
    xs, ys = [], []
    for p in pts:
        co = world_to_camera_view(scene, cam, p)
        if co.z <= 0.01:
            continue
        xs.append(co.x)
        ys.append(co.y)
    if not xs:
        return None
    return min(xs), max(xs), min(ys), max(ys)


def fit(scene, cam, pts, target):
    """Binary-search the distance along the current view direction."""
    fwd = (cam.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized()
    origin = cam.matrix_world.translation.copy()
    d0 = (origin - target).length

    def place(d):
        cam.location = target - fwd * d
        bpy.context.view_layer.update()

    def fits(d):
        place(d)
        e = extent(scene, cam, pts)
        if e is None:
            return 99.0
        x0, x1, y0, y1 = e
        return max(MARGIN - x0, x1 - (1.0 - MARGIN),
                   MARGIN - y0, y1 - (1.0 - MARGIN))

    lo, hi = d0 * 0.4, d0 * 5.0
    # find a hi that fits
    for _ in range(40):
        if fits(hi) <= 0.0:
            break
        hi *= 1.25
    else:
        return d0
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if fits(mid) <= 0.0:
            hi = mid
        else:
            lo = mid
    place(hi)
    return hi


def main():
    scene = bpy.context.scene
    pts = world_points()
    print(f"sampled {len(pts)} world points")

    out = []
    for cam_name, (w, h) in SHOTS.items():
        cam_obj = bpy.data.objects.get(cam_name)
        if cam_obj is None:
            continue
        scene.render.resolution_x = w
        scene.render.resolution_y = h
        scene.render.resolution_percentage = 100
        cam = cam_obj
        target = cam.matrix_world.translation + (
            cam.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized() * 10.0
        # keep the existing aim point: use the stored look-at by projecting
        # forward 10 m from the original position, then re-aim at the model core
        target = Vector((0.0, 0.0, 4.4)) if cam_name != "CAM_Top" else Vector((0.0, 0.0, 1.0))
        if cam_name.startswith("CAM_F") or cam_name in ("CAM_Ceiling", "CAM_Detail_Eave"):
            target = cam.matrix_world.translation + (
                cam.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized() * 5.0
        d = fit(scene, cam, pts, target)
        e = extent(scene, cam, pts)
        loc = tuple(round(v, 2) for v in cam.location)
        print(f"{cam_name:>16} dist={d:6.2f} loc={loc} ndc=({e[0]:.3f},{e[1]:.3f},"
              f"{e[2]:.3f},{e[3]:.3f}) lens={cam.data.lens}")
        out.append({"camera": cam_name, "loc": loc, "lens": cam.data.lens,
                    "target": tuple(round(v, 2) for v in target), "dist": round(d, 2)})

    dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "renders", "camera_fit.json")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print("saved", bpy.data.filepath)


if __name__ == "__main__":
    main()