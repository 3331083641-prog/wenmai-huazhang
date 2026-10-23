"""Render the mascot from orthographic views on a neutral light-grey backdrop.

    blender.exe --background --python render_mascot.py -- --blend <file> --tag blockout
    blender.exe --background --python render_mascot.py -- --blend <file> --tag final
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector

PROJ = r"D:\wenmai-huazhang"
OUT_DIR = os.path.join(PROJ, "docs", "mascot", "previews")
BG = (0.855, 0.865, 0.880)          # neutral light grey (not warm white)

DEFAULT_HEIGHT = 1.0


def pick_engine(scene):
    avail = {e.identifier for e in
             bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    for cand in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if cand in avail:
            scene.render.engine = cand
            return cand
    return scene.render.engine


def clear_scene_keep_meshes():
    for o in list(bpy.context.scene.objects):
        if o.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(o, do_unlink=True)


def subject_bbox():
    pts = []
    deps = bpy.context.evaluated_depsgraph_get()
    for o in bpy.context.scene.objects:
        if o.type != "MESH":
            continue
        ev = o.evaluated_get(deps)
        me = ev.to_mesh()
        pts += [o.matrix_world @ v.co for v in me.vertices]
        ev.to_mesh_clear()
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def setup_world(scene):
    w = bpy.data.worlds.get("WWWorld") or bpy.data.worlds.new("WWWorld")
    scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.66, 0.65, 0.63, 1.0)
    bg.inputs[1].default_value = 1.0


def add_lights(scene, target, radius):
    def lamp(name, loc, energy, color=(1, 1, 1), angle=12.0):
        d = bpy.data.lights.new(name, "SUN")
        d.energy = energy
        d.color = color
        d.angle = math.radians(angle)
        ob = bpy.data.objects.new(name, d)
        ob.location = loc
        scene.collection.objects.link(ob)
        ob.rotation_euler = (target - Vector(loc)).normalized().to_track_quat("-Z", "Y").to_euler()
        return ob
    k = radius
    lamp("Key", target + Vector((1.0, 1.1, 1.4)) * k, 2.7, (1.0, 0.98, 0.94))
    lamp("Fill", target + Vector((-1.4, 0.9, 0.5)) * k, 0.75, (0.94, 0.96, 1.0))
    lamp("Rim", target + Vector((0.1, -1.5, 0.9)) * k, 0.75, (1.0, 0.96, 0.9))


def make_camera(scene, direction, lo, hi, ortho=True, margin=1.14):
    target = (lo + hi) * 0.5
    radius = max((hi - lo).length * 0.5, 0.2)
    cd = bpy.data.cameras.new("Cam")
    cd.type = "ORTHO" if ortho else "PERSP"
    if not ortho:
        cd.lens = 85.0
    cam = bpy.data.objects.new("Cam", cd)
    scene.collection.objects.link(cam)
    scene.camera = cam
    d = Vector(direction).normalized()
    cam.location = target + d * (radius * 6.0)
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cd.clip_start = 0.01
    cd.clip_end = radius * 60.0
    if ortho:
        bpy.context.view_layer.update()
        inv = cam.matrix_world.inverted()
        corners = [Vector((x, y, z)) for x in (lo.x, hi.x)
                   for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
        proj = [inv @ c for c in corners]
        cam.data.ortho_scale = max(max(abs(p.x) for p in proj),
                                   max(abs(p.y) for p in proj)) * 2.0 * margin
    return cam


VIEWS = {
    "front":         (0.0, 1.0, 0.0),      # front faces +Y in Blender (=-Z glTF)
    "side":          (1.0, 0.0, 0.0),
    "back":          (0.0, -1.0, 0.0),
    "three-quarter": (0.86, 0.92, 0.30),
    "top":           (0.0, 0.001, 1.0),
}


def render(blend, tag, views, width=800, height=800, samples=48):
    bpy.ops.wm.open_mainfile(filepath=blend)
    os.makedirs(OUT_DIR, exist_ok=True)
    made = []
    for name in views:
        clear_scene_keep_meshes()
        sc = bpy.context.scene
        pick_engine(sc)
        sc.render.resolution_x = width
        sc.render.resolution_y = height
        sc.render.resolution_percentage = 100
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_mode = "RGBA"
        sc.render.film_transparent = True
        try:
            sc.eevee.taa_render_samples = samples
        except Exception:
            pass
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"

        lo, hi = subject_bbox()
        target = (lo + hi) * 0.5
        radius = max((hi - lo).length * 0.5, 0.2)
        setup_world(sc)
        add_lights(sc, target, radius)
        make_camera(sc, VIEWS[name], lo, hi)

        path = os.path.join(OUT_DIR, f"_flat-{name}{'-' + tag if tag else ''}.png")
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        made.append(path)
        print(f"[preview] {name} -> {path}")
    return made


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    ap.add_argument("--tag", default="")
    ap.add_argument("--views", default="front,side,back,three-quarter")
    args = ap.parse_args(argv)
    views = [v.strip() for v in args.views.split(",") if v.strip()]
    render(args.blend, args.tag, views)


if __name__ == "__main__":
    main()