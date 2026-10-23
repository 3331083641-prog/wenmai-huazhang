"""Fit every exterior camera to the whole plinth with the closest framing.

Pure pull-back along the spec ray needs 47 m for the hero view, which turns the
hall into a speck. This instead keeps each camera's azimuth and searches
(elevation, distance, aim height) for the nearest position whose frustum still
contains all eight plinth corners plus the ridge apex. Prints ready-to-paste
(tx, ty, tz) / (ax, ay, az) / focal triples.

    blender -b .../wenmai_gallery.blend -P solve_cams.py
"""
from __future__ import annotations

import math

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

S = 7.0
MARGIN = 0.030
TARGETS = {
    # name: (azimuth deg in web XY plane, current focal)
    "CAM_Front34": (41.5, 46.0),
    "CAM_Front": (0.0, 42.0),
    "CAM_Back": (180.0, 42.0),
    "CAM_Left": (-90.0, 42.0),
    "CAM_Right": (90.0, 42.0),
    "CAM_Top": (0.0, 42.0),
}


def pts():
    p = [Vector((sx * S, sy * S, z)) for sx in (-1, 1) for sy in (-1, 1)
         for z in (-0.65, 0.0)]
    p += [Vector((0, 0, 8.762)), Vector((0, 0, -0.65))]
    return p


def place(cam, dist, elev_deg, azim_deg, aim, focal):
    """Camera sits on a sphere around `aim` in Blender orientation."""
    a = math.radians(azim_deg)
    e = math.radians(elev_deg)
    # web azimuth 0 = looking from -Z (front). In Blender the front is +Y, so
    # the camera body sits at +Y for a front view.
    dx = math.sin(a) * math.cos(e)
    dy = math.cos(a) * math.cos(e)
    dz = math.sin(e)
    cam.location = aim + Vector((dx, dy, dz)) * dist
    cam.data.lens = focal
    d = (aim - cam.location)
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = d.to_track_quat("-Z", "Y")
    bpy.context.view_layer.update()


def extent(scn, cam, points):
    ndc = [world_to_camera_view(scn, cam, p) for p in points]
    return (min(p.x for p in ndc), max(p.x for p in ndc),
            min(p.y for p in ndc), max(p.y for p in ndc))


def fits(ex):
    x0, x1, y0, y1 = ex
    return (x0 >= -1 + MARGIN and x1 <= 1 - MARGIN
            and y0 >= MARGIN and y1 <= 1 - MARGIN)


def main():
    scn = bpy.context.scene
    points = pts()
    print("\nminimal-distance framing that contains the whole plinth")
    for name, (azim, focal) in TARGETS.items():
        cam = bpy.data.objects.get(name)
        if cam is None:
            continue
        scn.camera = cam
        best = None
        if name == "CAM_Top":
            cam.data.type = "ORTHO"
            for sc in [x * 0.25 for x in range(48, 90)]:
                cam.data.ortho_scale = sc
                cam.location = Vector((0.0, 0.0, 40.0))
                cam.rotation_mode = "QUATERNION"
                cam.rotation_quaternion = Vector((0, 0, -1)).to_track_quat("-Z", "Y")
                bpy.context.view_layer.update()
                if fits(extent(scn, cam, points)):
                    best = ("ortho", sc)
                    break
            if best:
                print("%-13s ortho_scale=%.2f  location=(0,0,40)" % (name, best[1]))
            continue
        for elev in (14, 16, 18, 20, 22, 24, 26):
            for aim_z in (1.2, 1.5, 1.8, 2.1, 2.4, 2.7):
                for focal in (40.0, 42.0, 46.0):
                    for dist in [16 + 0.5 * i for i in range(0, 70)]:
                        place(cam, dist, elev, azim, Vector((0.0, 0.0, aim_z)), focal)
                        ex = extent(scn, cam, points)
                        if fits(ex):
                            if best is None or dist < best[1]:
                                loc = tuple(round(v, 2) for v in cam.location)
                                best = (focal, dist, elev, aim_z, loc,
                                        (ex[0], ex[1], ex[2], ex[3]))
                            break
        if best:
            focal, dist, elev, aim_z, loc, ex = best
            print("%-13s dist=%5.1f elev=%2d aim_z=%.1f f=%2.0f  loc=(%.2f, %.2f, %.2f)  "
                  "aim=(0, 0, %.1f)  x %.2f..%.2f y %.2f..%.2f"
                  % (name, dist, elev, aim_z, focal, loc[0], loc[1], loc[2], aim_z,
                     ex[0], ex[1], ex[2], ex[3]))
        else:
            print("%-13s FAIL no fit" % name)


main()