"""Project the plinth and roof through every camera to prove the framing.

    blender -b .../wenmai_gallery.blend -P check_framing.py

For each camera it reports the NDC extent of the whole model: every value must
sit inside [-1, 1] for the plinth to be fully in shot ("完整看到底座"), and the
margin tells us whether the framing is too loose or about to crop.
"""
from __future__ import annotations

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

S = 7.0                     # plinth half side
CORNERS = [Vector((sx * S, sy * S, z))
           for sx in (-1, 1) for sy in (-1, 1) for z in (-0.65, 0.0)]
EXTRA = [Vector((0, 0, 8.762)),      # ridge apex
         Vector((0, 0, 0)),          # hall centre at deck level
         Vector((0, 0, 6.55))]       # wall head


SCN = bpy.context.scene
# Only the six exterior presets are required to hold the whole plinth; the
# interior presets deliberately sit inside the room and see a few square metres.
EXTERIOR = ("CAM_Front34", "CAM_Front", "CAM_Back", "CAM_Left", "CAM_Right", "CAM_Top")


def main():
    print("\n%-16s %-9s %-22s %-22s %s"
          % ("camera", "verdict", "x range (NDC)", "y range (NDC)", "margin"))
    bad = 0
    for ob in sorted((o for o in bpy.data.objects if o.type == "CAMERA"),
                     key=lambda o: o.name):
        SCN.camera = ob
        pts = CORNERS + EXTRA
        ndc = [world_to_camera_view(SCN, ob, p) for p in pts]
        px = [p.x for p in ndc[:8]]
        py = [p.y for p in ndc[:8]]
        xs = [p.x for p in ndc]
        ys = [p.y for p in ndc]
        margin = min(min(px) + 1.0, 1.0 - max(px), min(py), 1.0 - max(py))
        if ob.name in EXTERIOR:
            inside = margin >= 0.0
            verdict = "OK" if inside else "CROPPED"
            if not inside:
                bad += 1
        else:
            inside = True
            verdict = "interior"
        print("%-16s %-9s %6.2f .. %6.2f        %6.2f .. %6.2f       %+.3f"
              % (ob.name, verdict, min(xs), max(xs), min(ys), max(ys), margin))
    print("\nexterior cameras cropping the plinth: %d" % bad)


main()