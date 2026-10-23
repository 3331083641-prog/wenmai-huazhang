"""Assembler for the gallery V5 build.

    blender.exe -b --factory-startup -P assets/gallery3d/scripts/v5/build_v5.py -- --stage all
    ... -- --only v5_01_front34,v5_06_top --quick        # fast check renders

Stages:
    mass   base + walls only (fast blocking pass)
    all    everything, then export GLB + write the layout contract

The web contract is unchanged: /models/wenmai_gallery.glb plus
gallery_layout.json (schema 2), so the 15 frame anchors, wall rectangles and
camera presets already in the frontend keep working.
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

import gal5 as G                    # noqa: E402
import mod_roof                     # noqa: E402

# HERE = assets/gallery3d/scripts/v5  ->  G3D = assets/gallery3d
G3D = os.path.abspath(os.path.join(HERE, "..", ".."))
PROJECT = os.path.abspath(os.path.join(G3D, "..", ".."))
BLEND_OUT = os.path.join(G3D, "blender", "wenmai_gallery_v5.blend")
GLB_OUT = os.path.join(G3D, "exports", "wenmai_gallery_v5.glb")
RENDER_OUT = os.path.join(G3D, "renders", "v5")


# ------------------------------------------------------------------ lighting
def build_world(scene):
    """Vertical sky gradient: light blue at the horizon, a touch deeper up top.

    No ground plane at all: the base is meant to read as a floating model, and
    the flat grey floor of the earlier renders was the single biggest thing
    killing the collectible look.
    """
    world = bpy.data.worlds.new("V5Sky")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    geo = nt.nodes.new("ShaderNodeNewGeometry")

    # Horizon -> zenith. Driven by the view ray, not by Generated coords:
    # Generated is meaningless for a world shader and produced the flat grey
    # wash of the earlier renders.
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.86, 0.90, 0.94, 1.0)
    ramp.color_ramp.elements[1].position = 0.62
    ramp.color_ramp.elements[1].color = (0.34, 0.55, 0.82, 1.0)
    ramp.color_ramp.elements.new(0.22).color = (0.62, 0.76, 0.92, 1.0)

    nt.links.new(geo.outputs["Incoming"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.50
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def build_lighting(scene):
    sun_data = bpy.data.lights.new("V5Sun", "SUN")
    sun_data.energy = 6.5
    sun_data.angle = math.radians(2.4)
    sun_data.color = (1.0, 0.955, 0.885)
    sun = bpy.data.objects.new("V5Sun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), 0.0, math.radians(-34))

    # soft sky bounce from the front-left, keeps shadow interiors alive
    for i, (loc, energy, size) in enumerate((
            ((14.0, 16.0, 12.0), 620.0, 16.0),
            ((-15.0, 6.0, 7.0), 180.0, 14.0),
            ((0.0, -16.0, 8.0), 210.0, 18.0))):
        ad = bpy.data.lights.new("V5Fill%d" % i, "AREA")
        ad.energy = energy
        ad.size = size
        ad.color = (0.86, 0.92, 1.0) if i == 0 else (1.0, 0.96, 0.90)
        ob = bpy.data.objects.new("V5Fill%d" % i, ad)
        scene.collection.objects.link(ob)
        ob.location = loc
        d = Vector((0.0, G.BCY, 4.0)) - Vector(loc)
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

    # interior practicals
    for i, (loc, power, colour) in enumerate((
            ((0.0, G.BCY - 0.4, G.F1 + 2.30), 140.0, (1.0, 0.80, 0.56)),
            ((-3.0, G.BCY + 1.0, G.F1 + 2.10), 70.0, (1.0, 0.82, 0.60)),
            ((3.0, G.BCY + 1.0, G.F1 + 2.10), 70.0, (1.0, 0.82, 0.60)),
            ((0.0, G.BCY + 0.2, G.F2 + 1.75), 120.0, (1.0, 0.82, 0.58)),
            ((-3.2, G.BCY + 0.4, G.F2 + 1.80), 60.0, (1.0, 0.84, 0.62)),
            ((3.2, G.BCY + 0.4, G.F2 + 1.80), 60.0, (1.0, 0.84, 0.62)),
            ((0.0, G.BCY, G.RIDGE_Z - 2.2), 110.0, (1.0, 0.78, 0.52)))):
        pd = bpy.data.lights.new("V5In%d" % i, "POINT")
        pd.energy = power
        pd.color = colour
        pd.shadow_soft_size = 0.6
        pd.use_shadow = False
        ob = bpy.data.objects.new("V5In%d" % i, pd)
        scene.collection.objects.link(ob)
        ob.location = loc


# ------------------------------------------------------------------ cameras
def add_camera(name, loc, target, lens=50.0, ortho=None, target_prop=True):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_start = 0.05
    cd.clip_end = 400.0
    if ortho is not None:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if target_prop:
        ob["target"] = [round(float(v), 3) for v in target]
    return ob


VIEWS = (
    ("v5_01_front34", "CAM_Front34", 1600, 1200),
    ("v5_02_front",   "CAM_Front",   1600, 1200),
    ("v5_03_left",    "CAM_Left",    1600, 1200),
    ("v5_04_right",   "CAM_Right",   1600, 1200),
    ("v5_05_back",    "CAM_Back",    1600, 1200),
    ("v5_06_top",     "CAM_Top",     1500, 1500),
    ("v5_07_floor1",  "CAM_F1",      1600, 1067),
    ("v5_08_floor2",  "CAM_F2",      1600, 1067),
    ("v5_09_ceiling", "CAM_Ceiling", 1500, 1067),
    ("v5_10_eave",    "CAM_Eave",    1500, 1125),
    ("v5_11_corner",  "CAM_Corner",  1500, 1125),
    ("v5_12_base_low", "CAM_BaseLow", 1500, 1050),
    ("v5_13_low34",    "CAM_Low34",   1600, 1200),
)


def build_cameras():
    """Framing aimed at the model, not at empty sky.

    Camera distances were the second half of the "grey wash" complaint: at 40 m
    with a 60 mm lens the building was a small object in a big void.
    """
    cx, cy = 0.0, G.BCY
    tgt = (0.0, G.BCY + 0.55, 4.60)
    # 50-52 mm at ~26-30 m frames the whole 16 m base with air around it; the
    # earlier 62 mm at closer range cropped the base out of every shot.
    add_camera("CAM_Front34", (20.6, 22.8, 9.4), (0.0, G.BCY + 0.7, 4.0), 42)
    add_camera("CAM_Front", (0.0, 36.0, 7.6), (0.0, G.BCY + 0.4, 4.7), 42)
    add_camera("CAM_Left", (-33.5, G.BCY + 8.5, 8.6), tgt, 42)
    add_camera("CAM_Right", (33.5, G.BCY + 8.5, 8.6), tgt, 42)
    add_camera("CAM_Back", (12.5, G.BCY - 32.0, 9.6), (0.0, G.BCY - 0.4, 4.4), 42)
    add_camera("CAM_Top", (13.0, G.BCY + 14.0, 34.0), (0.0, G.BCY, 1.4), 40)
    add_camera("CAM_F1", (0.0, G.BCY + 3.05, G.F1 + 1.62),
               (0.0, G.BCY - 2.6, G.F1 + 1.72), 17)
    add_camera("CAM_F2", (-0.9, G.BCY + 2.75, G.F2 + 1.58),
               (0.9, G.BCY - 3.0, G.F2 + 1.05), 18)
    add_camera("CAM_Ceiling", (2.2, G.BCY + 1.0, G.F2 + 1.62),
               (0.0, G.BCY - 0.3, G.RIDGE_Z - 1.35), 20)
    # eave close-up: bracket tiers, rafter tails and the corner sweep in one
    # frame.  The old 78 mm from 2.6 m showed two brackets and nothing about
    # the curve, so every eave iteration was judged blind.
    add_camera("CAM_Eave", (9.4, G.BCY + G.ROOF_D * 0.5 + 6.4,
                            G.ROOF_MAIN_EAVE - 1.15),
               (G.ROOF_W * 0.30, G.BCY + G.ROOF_D * 0.5 - 0.35,
                G.ROOF_MAIN_EAVE - 0.30), 52)
    add_camera("CAM_Corner", (9.8, G.BCY + 9.4, 3.6), (4.4, G.BCY + 0.6, 2.4), 44)
    # below the deck, looking slightly up: base courses, meander frieze, roundels
    add_camera("CAM_BaseLow", (6.6, 14.4, -1.35), (0.6, 1.2, 0.55), 40)
    # low three-quarter: keeps roof, street and the whole plinth in one frame
    add_camera("CAM_Low34", (15.2, 17.0, 3.1), (0.0, G.BCY + 0.8, 4.4), 46)


def render_views(scene, only=None, quick=False, tag=None):
    out_dir = RENDER_OUT if not tag else os.path.join(RENDER_OUT, "_" + tag)
    os.makedirs(out_dir, exist_ok=True)
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_percentage = 60 if quick else 100
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
        scene.view_settings.exposure = 0.05
    except Exception:
        pass
    try:
        scene.eevee.taa_render_samples = 16 if quick else 48
        scene.eevee.use_raytracing = True
    except Exception:
        pass
    for name, cam, w, h in VIEWS:
        if only and name not in only:
            continue
        cam_ob = bpy.data.objects.get(cam)
        if cam_ob is None:
            G.log("missing camera " + cam)
            continue
        scene.camera = cam_ob
        scene.render.resolution_x = w
        scene.render.resolution_y = h
        scene.render.filepath = os.path.join(out_dir, name + ".png")
        bpy.ops.render.render(write_still=True)
        G.log("rendered " + name)


# ------------------------------------------------------------------ export
def export_glb():
    os.makedirs(os.path.dirname(GLB_OUT), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=GLB_OUT, export_format="GLB", use_selection=False,
        export_apply=True, export_yup=True, export_cameras=False,
        export_lights=False, export_materials="EXPORT", export_extras=True,
        export_texcoords=True, export_tangents=False, export_animations=False,
    )
    G.log("exported %s (%d bytes)" % (GLB_OUT, os.path.getsize(GLB_OUT)))
    return GLB_OUT


def to_web(v):
    return [round(v[0], 4), round(v[2], 4), round(-v[1], 4)]


def write_layout():
    """Same schema 2 contract the frontend already consumes."""
    walls, frames = [], []
    wall_index = {}
    for ob in bpy.data.objects:
        if ob.type != "EMPTY":
            continue
        if ob.name.startswith("GALWALL_"):
            props = {k: ob[k] for k in ob.keys() if not k.startswith("_")}
            wid = ob.name.replace("GALWALL_", "")
            n = ob.matrix_world.to_3x3() @ Vector((0.0, 1.0, 0.0))
            n.normalize()
            entry = {
                "id": wid,
                "floor": int(props.get("floor", 1)),
                "center": to_web(ob.matrix_world.translation),
                "rotationY": round(math.atan2(n.x, -n.y), 4),
                "size": [round(float(props.get("width", 1.6)), 3),
                         round(float(props.get("height", 2.6)), 3)],
                "label": props.get("label", wid),
            }
            walls.append(entry)
            wall_index[wid] = entry

    for ob in bpy.data.objects:
        if ob.type != "EMPTY" or not ob.name.startswith("FRAME_F"):
            continue
        props = {k: ob[k] for k in ob.keys() if not k.startswith("_")}
        parts = ob.name.split("_")
        floor = int(parts[1][1])
        idx = int(parts[2])
        n = ob.matrix_world.to_3x3() @ Vector((0.0, 1.0, 0.0))
        n.normalize()
        size = props.get("frame_size") or [1.0, 0.85]
        wid = props.get("wall_id", "")
        frames.append({
            "id": ob.name,
            "floor": floor,
            "index": idx,
            "position": to_web(ob.matrix_world.translation),
            "rotationY": round(math.atan2(n.x, -n.y), 4),
            "wallId": wid,
            "group": wid.split("-", 1)[1] if "-" in wid else "wall",
            "size": [round(float(size[0]), 3), round(float(size[1]), 3)],
            "u": round(float(props.get("u", 0.5)), 4),
            "v": round(float(props.get("v", 0.5)), 4),
            "label": props.get("label", ob.name),
            "rotZ": round(float(ob.rotation_euler.z), 4),
            "wallSize": wall_index[wid]["size"] if wid in wall_index else None,
        })

    walls.sort(key=lambda w: w["id"])
    frames.sort(key=lambda f: (f["floor"], f["index"]))

    cams = []
    for ob in bpy.data.objects:
        if ob.type != "CAMERA" or not ob.name.startswith("CAM_"):
            continue
        mw = ob.matrix_world
        if "target" in ob.keys():
            target = Vector([float(v) for v in ob["target"]])
        else:
            fwd = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
            target = mw.translation + fwd * 20.0
        cams.append({
            "id": ob.name.replace("CAM_", "").lower(),
            "position": to_web(mw.translation),
            "target": to_web(target),
            "lens": round(ob.data.lens, 1),
            "sensor": round(ob.data.sensor_width, 1),
            "fov": round(math.degrees(2 * math.atan(ob.data.sensor_width / 2 / ob.data.lens)), 2),
        })
    cams.sort(key=lambda c: c["id"])

    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    tris = 0
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
        ob.data.calc_loop_triangles()
        tris += len(ob.data.loop_triangles)

    doc = {
        "schema": 2,
        "generatedBy": "assets/gallery3d/scripts/v5/build_v5.py",
        "units": "metre",
        "up": "Y (three.js), converted from Blender Z-up",
        "envelope": {
            "min": [round(lo.x, 3), round(lo.z, 3), round(-hi.y, 3)],
            "max": [round(hi.x, 3), round(hi.z, 3), round(-lo.y, 3)],
            "baseSize": G.BASE,
            "baseThickness": round(G.BASE_TOP - G.BASE_BOT, 3),
            "floor1Z": G.F1,
            "floor2Z": G.F2,
            "floor1Height": round(G.F2 - G.F1, 3),
            "floor2Height": round(G.TOP - G.F2, 3),
            "topZ": G.TOP,
            "eaveZ": G.EAVE_Z,
            "ridgeZ": G.RIDGE_Z,
            "footprintX": G.BW,
            "footprintZ": G.BD,
            "hallOffsetZ": round(-G.BCY, 3),
            "triangles": tris,
        },
        "walls": walls,
        "frames": frames,
        "cameras": cams,
        "counts": {
            "floor1": sum(1 for f in frames if f["floor"] == 1),
            "floor2": sum(1 for f in frames if f["floor"] == 2),
        },
    }
    body = json.dumps(doc, indent=1, ensure_ascii=False)
    for dst in (os.path.join(G3D, "exports", "gallery_layout.json"),
                os.path.join(PROJECT, "frontend", "src", "features",
                             "heritage-gallery", "data", "gallery_layout.json")):
        os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(body + "\n")
    G.log("layout: walls=%d frames=%d tris=%d" % (len(walls), len(frames), tris))
    return doc


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = "all"
    if "--stage" in argv:
        stage = argv[argv.index("--stage") + 1]
    only = None
    if "--only" in argv:
        only = set(argv[argv.index("--only") + 1].split(","))
    quick = "--quick" in argv
    no_render = "--no-render" in argv
    preview = "--preview" in argv
    tag = argv[argv.index("--tag") + 1] if "--tag" in argv else None

    scene = G.reset_scene()
    build_world(scene)

    cbase = G.collection("V5_BASE")
    cshell = G.collection("V5_SHELL")
    croof = G.collection("V5_ROOF")

    import mod_interior
    import mod_shell
    import mod_site

    mod_site.build(cbase)
    mod_shell.build(cshell)
    mod_interior.build(G.collection("V5_INTERIOR"))
    mod_roof.build(croof)

    # ---- render-safe pass ---------------------------------------------------
    # EEVEE overflows its shadow buffer past ~2048 potential casters and then
    # silently drops shadows. Tiles, paving and scatter props cost one slot each
    # and contribute nothing readable, so they stop CASTING (they still receive).
    NO_SHADOW = ("TILE_", "PAVE_", "VEG_", "PROP_", "KERB_", "LAT_", "RAIL2_",
                 "PLAQUE_Text", "INT_RAFTER", "WF_FRAME", "CANOPY_")
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.name.startswith(NO_SHADOW):
            try:
                ob.visible_shadow = False
            except AttributeError:
                pass

    # Display-case glass was alpha 0.24 with no thickness cue, so the cases read
    # as solid rosewood boxes. Lift alpha and add transmission so the porcelain
    # inside is visible.
    glass = bpy.data.materials.get("M_glass")
    if glass and glass.use_nodes:
        node = glass.node_tree.nodes.get("Principled BSDF")
        if node:
            node.inputs["Alpha"].default_value = 0.46
            if "Transmission Weight" in node.inputs:
                node.inputs["Transmission Weight"].default_value = 0.55
            if "Roughness" in node.inputs:
                node.inputs["Roughness"].default_value = 0.05
            if "IOR" in node.inputs:
                node.inputs["IOR"].default_value = 1.45
        glass.blend_method = "BLEND"

    build_lighting(scene)
    build_cameras()

    # --preview: never touch the shared .blend / .glb, so several modules can
    # be iterated on at the same time without clobbering each other.
    if preview:
        G.log("preview mode: skipping save + export")
    else:
        os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
        G.log("saved " + BLEND_OUT)
        export_glb()
        write_layout()
    if not no_render:
        render_views(scene, only=only, quick=quick, tag=tag)
    G.log("stage %s done" % stage)


if __name__ == "__main__":
    main()
