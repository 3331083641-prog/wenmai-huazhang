"""Render the mascot's action previews as 2x2 contact sheets (800x800).

Each sheet shows four key frames of one action, which says far more about the
motion than a single pose would.

    blender.exe --background --python render_anim.py -- --blend <file>
"""
import argparse
import os
import sys

import bpy
from mathutils import Vector

PROJ = r"D:\wenmai-huazhang"
OUT_DIR = os.path.join(PROJ, "docs", "mascot", "previews")
TMP = os.path.join(OUT_DIR, "_anim_raw")

# action -> the four frames that best show its range
SHEETS = {
    "Idle": [0, 30, 60, 76],
    "Walk": [0, 8, 16, 24],
    "Happy": [0, 11, 22, 34],
    "Curious": [0, 22, 45, 68],
}


def pick_engine(scene):
    avail = {e.identifier for e in
             bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    for cand in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if cand in avail:
            scene.render.engine = cand
            return cand
    return scene.render.engine


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


def setup(scene, target, radius):
    w = bpy.data.worlds.get("WWW") or bpy.data.worlds.new("WWW")
    scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.66, 0.65, 0.63, 1.0)
    bg.inputs[1].default_value = 1.0
    for name, loc, energy, color in (
            ("Key", (1.0, 1.1, 1.4), 2.7, (1.0, 0.98, 0.94)),
            ("Fill", (-1.4, 0.9, 0.5), 0.75, (0.94, 0.96, 1.0)),
            ("Rim", (0.1, -1.5, 0.9), 0.85, (1.0, 0.96, 0.9))):
        d = bpy.data.lights.new(name, "SUN")
        d.energy = energy
        d.color = color
        d.angle = 0.21
        ob = bpy.data.objects.new(name, d)
        ob.location = target + Vector(loc) * radius
        scene.collection.objects.link(ob)
        ob.rotation_euler = (target - ob.location).normalized().to_track_quat(
            "-Z", "Y").to_euler()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    args = ap.parse_args(argv)

    bpy.ops.wm.open_mainfile(filepath=args.blend)
    os.makedirs(TMP, exist_ok=True)
    sc = bpy.context.scene
    arm = next(o for o in sc.objects if o.type == "ARMATURE")

    # fixed framing across all frames so the sheets are comparable
    lo, hi = subject_bbox()
    centre = (lo + hi) * 0.5
    radius = max((hi - lo).length * 0.5, 0.3)
    # a 3/4 view reads the pose best
    view = Vector((0.80, 0.92, 0.22)).normalized()

    cd = bpy.data.cameras.new("Cam")
    cd.type = "ORTHO"
    cd.ortho_scale = radius * 2.35
    cam = bpy.data.objects.new("Cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.location = centre + view * (radius * 6.0)
    cam.rotation_euler = (-view).to_track_quat("-Z", "Y").to_euler()

    pick_engine(sc)
    sc.render.resolution_x = sc.render.resolution_y = 400
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.film_transparent = True
    try:
        sc.eevee.taa_render_samples = 40
    except Exception:
        pass
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    setup(sc, centre, radius)

    for act_name, frames in SHEETS.items():
        act = bpy.data.actions.get(act_name)
        if act is None:
            print(f"!! missing action {act_name}")
            continue
        if arm.animation_data is None:
            arm.animation_data_create()
        arm.animation_data.action = act
        try:
            if hasattr(act, "slots") and len(act.slots):
                arm.animation_data.action_slot = act.slots[0]
        except Exception as exc:
            print("  slot note:", exc)
        for i, f in enumerate(frames):
            sc.frame_set(f)
            bpy.context.view_layer.update()
            sc.render.filepath = os.path.join(TMP, f"{act_name}-{i}.png")
            bpy.ops.render.render(write_still=True)
        print(f"[anim-sheet] {act_name} frames {frames}")


if __name__ == "__main__":
    main()