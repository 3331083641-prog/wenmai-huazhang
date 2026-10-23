"""Solve the camera distance that fits the whole plinth in frame.

The brief fixes the hero camera at about (16, 11, -18) but also demands the
plinth be fully visible; at 46 mm those two cannot both hold, because the near
bottom corners of a 14 m plinth project below the frame. This keeps the stated
view direction and pulls the camera back along it until every plinth corner and
the ridge apex sit inside the frame with a small margin.

    blender -b .../wenmai_gallery.blend -P solve_framing.py
"""
from __future__ import annotations

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

S = 7.0
MARGIN = 0.035
EXTERIOR = ("CAM_Front34", "CAM_Front", "CAM_Back", "CAM_Left", "CAM_Right", "CAM_Top")


def points():
    pts = [Vector((sx * S, sy * S, z)) for sx in (-1, 1) for sy in (-1, 1)
           for z in (-0.65, 0.0)]
    pts += [Vector((0, 0, 8.762)), Vector((0, 0, -0.65))]
    return pts


def extent(scn, cam, pts):
    ndc = [world_to_camera_view(scn, cam, p) for p in pts]
    return (min(p.x for p in ndc), max(p.x for p in ndc),
            min(p.y for p in ndc), max(p.y for p in ndc))


def fits(x0, x1, y0, y1):
    return (x0 >= -1 + MARGIN and x1 <= 1 - MARGIN
            and y0 >= MARGIN and y1 <= 1 - MARGIN)


def main():
    scn = bpy.context.scene
    pts = points()
    print("\n%-16s %-8s %-22s %-28s %s"
          % ("camera", "state", "current NDC x/y", "suggested location", "delta"))
    for name in EXTERIOR:
        cam = bpy.data.objects.get(name)
        if cam is None:
            continue
        scn.camera = cam
        prev = extent(scn, cam, pts)
        if fits(*prev):
            print("%-16s %-8s fits already" % (name, "OK"))
            continue
        target = cam.matrix_world.to_translation() + \
            cam.matrix_world.to_quaternion() @ Vector((0, 0, -1)) * 0.0
        # aim point: where the camera looks, taken from its local -Z at 30 m
        aim = cam.matrix_world.to_translation() + \
            cam.matrix_world.to_quaternion() @ Vector((0, 0, -1)) * 30.0
        cur = cam.matrix_world.to_translation()
        if cam.data.type == "ORTHO":
            best, scale = None, cam.data.ortho_scale
            for k in range(1, 40):
                sc = cam.data.ortho_scale * (1.0 + 0.05 * k)
                cam.data.ortho_scale = sc
                if fits(*extent(scn, cam, pts)):
                    best, scale = k, sc
                    break
            cam.data.ortho_scale = cam.data.ortho_scale / (1.0 + 0.05 * (best or 0))
            if best:
                print("%-16s %-8s ortho %-16.2f ortho_scale -> %.2f (x%.2f)"
                      % (name, "ortho", cam.data.ortho_scale, scale, scale / cam.data.ortho_scale))
            else:
                print("%-16s %-8s ortho: no fit within 3x zoom" % (name, "FAIL"))
            continue
        # perspective: march outward along the view ray
        best = None
        d0 = (cur - aim).length
        for k in range(1, 60):
            mult = 1.0 + 0.04 * k
            cam.location = aim + (cur - aim) * mult
            bpy.context.view_layer.update()
            if fits(*extent(scn, cam, pts)):
                best = mult
                break
        cam.location = cur
        bpy.context.view_layer.update()
        if best:
            new = aim + (cur - aim) * best
            print("%-16s %-8s x %5.2f..%5.2f y %5.2f..%5.2f  (%.2f, %.2f, %.2f)  x%.2f  d %.1f->%.1f"
                  % (name, "solve", prev[0], prev[1], prev[2], prev[3],
                     new.x, new.y, new.z, best, d0, d0 * best))
        else:
            print("%-16s %-8s no fit within +240%% distance" % (name, "FAIL"))


main()