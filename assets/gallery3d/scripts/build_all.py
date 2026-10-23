"""Assemble the whole gallery, export GLB + layout, render review stills.

Usage:
    blender.exe -b --factory-startup -P build_all.py -- [--no-render]

Outputs (all under assets/gallery3d):
    blender/wenmai_gallery.blend
    exports/wenmai_gallery.glb
    exports/gallery_layout.json
    renders/*.png

Coordinate contract reminder: the hall and its interior are authored around
their own centre (0, 0) and shifted by BUILD_Y at assembly time, so the plinth
keeps a proper front street. Cameras are authored in final plinth coordinates
and are never shifted.
"""
from __future__ import annotations

import math
import os
import sys
import time

import bpy

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import gal_common as G  # noqa: E402
import build_core as core  # noqa: E402
import build_interior as interior  # noqa: E402
import build_props as props  # noqa: E402
import build_details2 as details2  # noqa: E402
from gal_common import BUILD_Y, ensure_dirs, get_collection, join_objects, report  # noqa: E402

STAGES = ("core", "interior", "props", "details2")

# Meshes the web addresses by name must never be merged away.
KEEP_SEPARATE = {
    "ROOF_Main", "ROOF_Lower", "ROOF_Ridge_Group", "ROOF_Chiwen",
    "TILE_Main", "TILE_Lower", "LANTERN_Eave",
}

COL_NAMES = ("base", "building", "roof", "interior", "anchors", "cam")


def scene_collections():
    return {name: get_collection(f"COL_{name.upper()}") for name in COL_NAMES}


def shift_collections(cols, dy):
    """Move the hall (and everything that lives in it) onto its plinth slot."""
    for name in ("building", "roof", "interior", "anchors"):
        col = cols[name]
        for obj in list(col.all_objects):
            obj.location.y += dy
    # area/point lights were authored around the hall centre too
    for obj in bpy.context.scene.objects:
        if obj.type == "LIGHT" and obj.data.type in ("AREA", "POINT"):
            obj.location.y += dy


def consolidate(cols):
    """Merge static meshes per collection; keep named roof parts + empties."""
    merged = 0
    for name in ("base", "building", "roof", "interior"):
        col = cols[name]
        objs = [o for o in col.objects
                if o.type == "MESH" and o.name not in KEEP_SEPARATE]
        if len(objs) < 2:
            continue
        target = join_objects(objs, f"MERGE_{name.upper()}")
        target["gallery_layer"] = name
        merged += 1
    report(f"consolidated into {merged} merged meshes")


def build(do_render=True, do_consolidate=True):
    t0 = time.time()
    scene = G.reset_scene()
    scene.render.engine = "BLENDER_EEVEE"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.render.film_transparent = False
    cols = scene_collections()

    core.build_base(cols["base"])
    core.build_columns(cols["building"])
    core.build_storey_bands(cols["building"])
    core.build_walls(cols["building"])
    core.build_floors(cols["building"])
    core.build_stairs(cols["building"])
    core.build_side_veranda(cols["building"])
    roofs = []
    roofs += core.build_main_roof(cols["roof"])
    roofs += core.build_lower_roof(cols["roof"])
    report(f"roof parts: {[o.name for o in roofs if o]}")

    interior.build(cols["interior"], cols["anchors"], cols["roof"])
    props.build(cols["base"])
    details2.build(cols["building"])

    core.build_cameras(cols["cam"])
    core.build_lighting(scene)

    shift_collections(cols, BUILD_Y)
    if do_consolidate:
        consolidate(cols)

    blend_name = "wenmai_gallery.blend" if do_consolidate else "wenmai_gallery_audit.blend"
    blend = os.path.join(ensure_dirs("blender"), blend_name)
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    report(f"saved {blend}")

    export(blend)
    if do_render:
        render(blend, cols)
    report(f"build finished in {time.time() - t0:.1f}s")
    return blend


def export(blend):
    out_dir = ensure_dirs("exports")
    glb = os.path.join(out_dir, "wenmai_gallery.glb")
    bpy.ops.export_scene.gltf(
        filepath=glb,
        export_format="GLB",
        use_selection=False,
        export_apply=True,
        export_yup=True,
        export_cameras=False,
        export_lights=False,
        export_materials="EXPORT",
        export_extras=True,
        export_texcoords=False,
        export_tangents=False,
        export_animations=False,
        export_skins=False,
    )
    report(f"exported {glb} ({os.path.getsize(glb):,} bytes)")
    return glb


RENDER_VIEWS = (
    ("01_front34", "CAM_Front34", 1500, 1125),
    ("02_front", "CAM_Front", 1500, 1125),
    ("03_left", "CAM_Left", 1500, 1125),
    ("04_right", "CAM_Right", 1500, 1125),
    ("05_back", "CAM_Back", 1500, 1125),
    ("06_top", "CAM_Top", 1400, 1400),
    ("07_floor1", "CAM_F1", 1500, 1000),
    ("08_floor2", "CAM_F2", 1500, 1000),
    ("09_ceiling", "CAM_Ceiling", 1400, 1000),
    ("10_eave", "CAM_Detail_Eave", 1400, 1050),
)


def render(blend, cols):
    out_dir = ensure_dirs("renders")
    scene = bpy.context.scene
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.engine = "BLENDER_EEVEE"
    try:
        scene.eevee.taa_render_samples = 48
        scene.eevee.shadow_pool_size = "1024"
    except Exception:
        pass
    for name, cam_name, w, h in RENDER_VIEWS:
        cam = bpy.data.objects.get(cam_name)
        if cam is None:
            report(f"missing camera {cam_name}")
            continue
        scene.camera = cam
        scene.render.resolution_x = w
        scene.render.resolution_y = h
        scene.render.filepath = os.path.join(out_dir, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        report(f"rendered {name}")
    scene.camera = bpy.data.objects.get("CAM_Front34")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_render = "--no-render" not in argv
    do_consolidate = "--no-consolidate" not in argv
    build(do_render=do_render, do_consolidate=do_consolidate)


if __name__ == "__main__":
    main()