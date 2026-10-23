"""Move the exterior cameras closer so the building fills the frame like the
references do.

Measured with `verify_web.py` against the ten reference images:
  - our diorama filled 54 % of the frame, the references fill ~65 %;
  - the building also rendered ~2 rows too low with too much plinth at the
    bottom (that aim correction was applied in an earlier pass and is kept).

So this pass only scales the camera distance (and re-derives the rotation so the
existing aim point is preserved). Applied to the authored Blender cameras, so
the web viewer inherits it -- one source of truth.

  blender -b wenmai_gallery.blend -P retarget_cameras.py
"""
from __future__ import annotations

import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import gal_common as G  # noqa: E402

CAMERAS = ["CAM_Front34", "CAM_Front", "CAM_Back", "CAM_Left", "CAM_Right"]
# 3/4 hero shot is already right at 0.83; the straight elevations overshoot
# (they fill 85 % of the top rows vs 19 % in the reference), so they pull back.
SCALE = {
    "CAM_Front34": 1.0,
    "CAM_Front": 1.11,
    "CAM_Back": 1.11,
    "CAM_Left": 1.11,
    "CAM_Right": 1.11,
}
MARKER = "dsh_distance_v2"


def aim_point(cam) -> Vector:
    pos = cam.matrix_world.translation
    fwd = (cam.matrix_world.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()
    centre = Vector((0.0, 0.0, 4.4))
    t = (centre - pos).dot(fwd)
    return pos + fwd * max(t, 1.0)


def main():
    changed = []
    for name in CAMERAS:
        cam = bpy.data.objects.get(name)
        if cam is None or cam.type != "CAMERA":
            continue
        if cam.get(MARKER):
            G.report(f"{name}: already scaled, skipped")
            continue
        factor = SCALE.get(name, 1.0)
        if abs(factor - 1.0) < 1e-6:
            cam[MARKER] = 1
            continue
        pos = cam.matrix_world.translation.copy()
        aim = aim_point(cam)
        new_pos = aim + (pos - aim) * factor
        cam.rotation_mode = "QUATERNION"
        cam.rotation_quaternion = (aim - new_pos).to_track_quat("-Z", "Y")
        cam.location = new_pos
        cam[MARKER] = 1
        changed.append(name)
        G.report(
            f"{name}: {pos.length:.2f} m -> {new_pos.length:.2f} m, aim z={aim.z:.2f}"
        )

    bpy.ops.wm.save_mainfile()
    G.report(f"rescaled {len(changed)} cameras, saved {bpy.data.filepath}")


if __name__ == "__main__":
    main()