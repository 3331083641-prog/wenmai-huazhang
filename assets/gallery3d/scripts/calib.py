"""Calibrate sky / exposure / interior light so nothing clips and the sky stays blue.

    blender -b blender/wenmai_gallery.blend -P calib.py

Renders two small frames per candidate into renders/_calib; measure them with
check_render.py afterwards (Blender's bundled Python has no Pillow).
"""
from __future__ import annotations

import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

OUT = os.path.join(HERE, "..", "renders", "_calib")
os.makedirs(OUT, exist_ok=True)



def render(cam, path, w=520, h=390):
    scene = bpy.context.scene
    scene.camera = bpy.data.objects[cam]
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 16
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    scene = bpy.context.scene
    world = scene.world
    bg = None
    for node in world.node_tree.nodes:
        if node.type == "BACKGROUND":
            bg = node
    sky_node = None
    for node in world.node_tree.nodes:
        if node.type == "TEX_SKY":
            sky_node = node
    if bg is None or sky_node is None:
        print("world nodes missing")
        return

    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.film_transparent = False

    areas = [o for o in bpy.data.objects if o.name.startswith("AREA_")]
    pt = bpy.data.objects.get("PT_Hall")
    base_area = {o.name: o.data.energy for o in areas}
    base_pt = pt.data.energy if pt else 0.0
    sun = bpy.data.objects.get("SUN_Key")
    base_sun = sun.data.energy if sun else 0.0

    cands = [
        # (sky_strength, exposure, area_scale, sun_energy)
        (0.42, 0.0, 1.00, 2.4),
        (0.22, -0.6, 0.45, 2.0),
        (0.16, -0.9, 0.32, 1.8),
        (0.12, -1.1, 0.26, 1.7),
        (0.20, -1.3, 0.30, 1.9),
        (0.10, -0.7, 0.24, 1.8),
    ]
    print("\n=== CALIB ===")
    for i, (strength, expo, ascale, sune) in enumerate(cands):
        bg.inputs[1].default_value = strength
        scene.view_settings.exposure = expo
        for o in areas:
            o.data.energy = base_area[o.name] * ascale
        if pt:
            pt.data.energy = base_pt * ascale
        if sun:
            sun.data.energy = sune
        render("CAM_Front34", os.path.join(OUT, "c%d_ext.png" % i))
        render("CAM_F1", os.path.join(OUT, "c%d_f1.png" % i))
        print("rendered c%d sky=%.2f expo=%.1f area=%.2f sun=%.1f"
              % (i, strength, expo, ascale, sune))
    print("=== END ===\n")


if __name__ == "__main__":
    main()