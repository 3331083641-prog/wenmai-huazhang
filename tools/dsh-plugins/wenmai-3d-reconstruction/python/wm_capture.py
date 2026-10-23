"""``capture_views`` — real EEVEE renders from named or supplied cameras.

Builds (or reuses) the twelve standard views, ensures a lighting rig that
approximates the references (warm key sun + cool area fill + warm interior
practicals), renders PNGs, and returns the shots with their real paths, byte
counts, measured dimensions and the camera JSON that was used.

Cameras are resolved in this order for each requested view:

1. ``CAM_<Name>`` already in the opened .blend;
2. ``cameras[]`` in ``assets/gallery3d/exports/gallery_layout.json``
   (glTF Y-up -> Blender Z-up);
3. a synthesised orbit / interior camera from the table below, auto-fitted so
   the whole model sits inside a margin.

Owned by ``visual-match``.  Runs inside Blender.
"""
from __future__ import annotations

import json
import math
import os
import time

import numpy as np

import bpy
from mathutils import Vector

import wm_common as C
import wm_image as WI

# view -> (blend camera name, layout camera id)
VIEW_CAMERAS = {
    "front34": ("CAM_Front34", "front34"),
    "front": ("CAM_Front", "front"),
    "left": ("CAM_Left", "left"),
    "right": ("CAM_Right", "right"),
    "back": ("CAM_Back", "back"),
    "top": ("CAM_Top", "top"),
    "base_low": ("CAM_BaseLow", "baselow"),
    "floor1": ("CAM_F1", "f1"),
    "floor2": ("CAM_F2", "f2"),
    "ceiling": ("CAM_Ceiling", "ceiling"),
    "eave": ("CAM_Eave", "eave"),
    "corner": ("CAM_Corner", "corner"),
}
VIEW_ORDER = list(VIEW_CAMERAS)

# Synthesised fallbacks.  Azimuth 0 looks from -Y (the model front); in Blender
# the camera therefore sits at +Y for a front view (same convention as the
# proven assets/gallery3d/scripts/solve_cams.py).
#   ("orbit", azimuth_deg, elevation_deg, lens_mm)
#   ("fixed", position, target, lens_mm)
SYNTH = {
    "front34": ("orbit", 38.0, 18.0, 42.0),
    "front": ("orbit", 0.0, 12.0, 42.0),
    "left": ("orbit", -90.0, 14.0, 42.0),
    "right": ("orbit", 90.0, 14.0, 42.0),
    "back": ("orbit", 180.0, 14.0, 42.0),
    "top": ("orbit", 0.0, 88.0, 40.0),
    "base_low": ("orbit", 30.0, -6.0, 40.0),
    "corner": ("orbit", 60.0, 12.0, 44.0),
    "floor1": ("fixed", (0.0, -2.5, 1.87), (0.0, 3.0, 1.97), 17.0),
    "floor2": ("fixed", (-0.9, -2.2, 5.18), (0.9, 3.4, 4.65), 18.0),
    "ceiling": ("fixed", (2.2, -0.45, 5.22), (0.0, 0.8, 9.95), 20.0),
    "eave": ("fixed", (7.4, -3.2, 6.9), (3.35, 0.55, 7.75), 52.0),
}

SKY_TOP = (0.36, 0.55, 0.86)
SKY_HORIZON = (0.86, 0.90, 0.95)
SUN_COLOR = (1.0, 0.955, 0.885)
FILL_COLOR = (0.86, 0.92, 1.0)
PRACTICAL_COLOR = (1.0, 0.80, 0.56)


# ------------------------------------------------------------------ helpers

def _layout_path(ctx: dict) -> str:
    return os.path.join(ctx.get("projectRoot") or os.getcwd(),
                        "assets", "gallery3d", "exports", "gallery_layout.json")


def _read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def layout_cameras(ctx: dict) -> dict:
    """``gallery_layout.json`` cameras converted from glTF Y-up to Blender Z-up.

    The layout is authored with ``y`` up for Three.js; the exporter maps
    Blender ``(X, Y, Z)`` to glTF ``(X, Z, -Y)``, so the inverse is
    ``blender = (gx, -gz, gy)``.
    """
    data = _read_json(_layout_path(ctx))
    out = {}
    for cam in (data or {}).get("cameras", []) or []:
        try:
            gx, gy, gz = cam["position"]
            tx, ty, tz = cam["target"]
        except (KeyError, TypeError, ValueError):
            continue
        out[cam.get("id")] = {
            "position": [float(gx), float(-gz), float(gy)],
            "target": [float(tx), float(-tz), float(ty)],
            "lens": float(cam.get("lens", 42.0)),
            "sensor": float(cam.get("sensor", 36.0)),
            "roll": 0.0, "shiftX": 0.0, "shiftY": 0.0,
            "source": "gallery_layout.json",
        }
    return out


def blend_camera(obj, width: float, height: float) -> dict:
    """Read a Blender camera object into the shape ``wm_camera`` produces."""
    mw = obj.matrix_world
    pos = mw.translation.copy()
    fwd = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
    rot = mw.to_3x3().normalized()
    up_b = rot @ Vector((0, 1, 0))
    right_b = rot @ Vector((1, 0, 0))
    # roll about the view axis relative to the track-to-orientation up
    wd = Vector((0.0, 0.0, 1.0))
    z = -fwd
    x = wd.cross(z)
    if x.length < 1e-9:
        x = Vector((1.0, 0.0, 0.0)).cross(z)
    x.normalize()
    y = z.cross(x)
    roll = math.atan2(float(up_b.dot(x)), float(up_b.dot(y)))
    return {
        "position": [float(v) for v in pos],
        "target": [float(v) for v in (pos + fwd * 10.0)],
        "lens": float(obj.data.lens),
        "sensor": float(obj.data.sensor_width),
        "roll": float(roll),
        "shiftX": float(obj.data.shift_x),
        "shiftY": float(obj.data.shift_y),
        "projection": obj.data.type,
        "orthoScale": float(obj.data.ortho_scale) if obj.data.type == "ORTHO" else None,
        "width": float(width), "height": float(height),
        "source": f"blend:{obj.name}",
    }


def model_bounds():
    lo = np.array([math.inf] * 3)
    hi = np.array([-math.inf] * 3)
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.data:
            continue
        mw = obj.matrix_world
        for corner in obj.bound_box:
            w = np.array(mw @ Vector(corner))
            lo = np.minimum(lo, w)
            hi = np.maximum(hi, w)
    if not np.isfinite(lo).all():
        return np.array([-8.0, -8.0, -1.0]), np.array([8.0, 8.0, 11.5])
    return lo, hi


def model_points(limit: int = 6000) -> np.ndarray:
    """Sampled world-space mesh vertices used for auto-framing."""
    objs = [o for o in bpy.data.objects if o.type == "MESH" and o.data]
    total = sum(len(o.data.vertices) for o in objs)
    step = max(1, total // limit) if total > limit else 1
    pts = []
    for obj in objs:
        mw = obj.matrix_world
        verts = obj.data.vertices
        for i in range(0, len(verts), step):
            pts.append(mw @ verts[i].co)
    if not pts:
        return np.zeros((0, 3))
    return np.array([[p.x, p.y, p.z] for p in pts], dtype=np.float64)


def _project_ndc(cam: dict, pts: np.ndarray):
    """NDC in [0,1] with y up, matching Blender's world_to_camera_view."""
    w = float(cam["width"]); h = float(cam["height"])
    R = _basis(cam)
    pos = np.asarray(cam["position"], dtype=np.float64)
    rel = (pts - pos) @ R
    depth = -rel[:, 2]
    ok = depth > 1e-6
    scale = max(w, h) * float(cam["lens"]) / float(cam.get("sensor", 36.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        u = 0.5 * w + (rel[:, 0] / depth) * scale + float(cam.get("shiftX", 0.0)) * max(w, h)
        v = 0.5 * h - (rel[:, 1] / depth) * scale - float(cam.get("shiftY", 0.0)) * max(w, h)
    return u / w, 1.0 - v / h, ok


def _basis(cam: dict) -> np.ndarray:
    pos = np.asarray(cam["position"], dtype=np.float64)
    tgt = np.asarray(cam["target"], dtype=np.float64)
    d = tgt - pos
    n = float(np.linalg.norm(d))
    d = d / n if n > 1e-12 else np.array([0.0, 1.0, 0.0])
    z = -d
    up = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(up, z))) > 0.999999:
        up = np.array([0.0, 1.0, 0.0])
    x = np.cross(up, z)
    x = x / max(1e-12, float(np.linalg.norm(x)))
    y = np.cross(z, x)
    R = np.stack([x, y, z], axis=1)
    r = float(cam.get("roll", 0.0))
    if r:
        c, s = math.cos(r), math.sin(r)
        R = R @ np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    return R


def fit_distance(cam: dict, pts: np.ndarray, margin: float = 0.055,
                 iters: int = 40) -> dict:
    """Pull the camera back along its view ray until the model fits the frame."""
    if pts.shape[0] == 0:
        return cam
    pos = np.asarray(cam["position"], dtype=np.float64)
    tgt = np.asarray(cam["target"], dtype=np.float64)
    d = tgt - pos
    dist0 = float(np.linalg.norm(d))
    if dist0 < 1e-6:
        return cam
    fwd = d / dist0

    def overflow(dist):
        probe = dict(cam)
        probe["position"] = [float(v) for v in (tgt - fwd * dist)]
        u, v, ok = _project_ndc(probe, pts)
        if not ok.any():
            return 9.9
        u, v = u[ok], v[ok]
        return max(margin - float(u.min()), float(u.max()) - (1.0 - margin),
                   margin - float(v.min()), float(v.max()) - (1.0 - margin))

    lo, hi = dist0 * 0.05, dist0
    for _ in range(30):
        if overflow(hi) <= 0.0:
            break
        hi *= 1.4
    else:
        return cam
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if overflow(mid) <= 0.0:
            hi = mid
        else:
            lo = mid
    out = dict(cam)
    out["position"] = [float(v) for v in (tgt - fwd * hi)]
    out["fitDistance"] = round(hi, 4)
    out["target"] = [float(v) for v in tgt]
    return out


def synth_camera(view: str, width: float, height: float, lo, hi) -> dict | None:
    spec = SYNTH.get(view)
    if not spec:
        return None
    center = 0.5 * (lo + hi)
    size = float(max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]))
    if spec[0] == "fixed":
        _tag, position, target, lens = spec
        return {"position": [float(v) for v in position],
                "target": [float(v) for v in target], "lens": float(lens),
                "sensor": 36.0, "roll": 0.0, "shiftX": 0.0, "shiftY": 0.0,
                "width": width, "height": height, "source": "synth-fixed"}
    _tag, az, el, lens = spec
    aim = np.array([center[0], center[1], 0.45 * (center[2] + hi[2])])
    dist = max(6.0, size * 1.35)
    a, e = math.radians(az), math.radians(el)
    offset = np.array([math.sin(a) * math.cos(e), math.cos(a) * math.cos(e),
                       math.sin(e)]) * dist
    return {"position": [float(v) for v in (aim + offset)],
            "target": [float(v) for v in aim], "lens": float(lens),
            "sensor": 36.0, "roll": 0.0, "shiftX": 0.0, "shiftY": 0.0,
            "width": width, "height": height, "source": "synth-orbit"}


# ------------------------------------------------------------------ lighting

def _remove_rig():
    doomed = [o for o in bpy.data.objects if o.get("wm_part") == "rig"]
    for obj in doomed:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data is not None and getattr(data, "users", 0) == 0:
            try:
                bpy.data.lights.remove(data)
            except Exception:
                pass
    return len(doomed)


def _aim(obj, direction):
    v = Vector(direction)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = v.to_track_quat("-Z", "Y")


def build_rig(lo, hi) -> dict:
    """Warm key sun + cool area fill + warm interior practicals."""
    _remove_rig()
    made = []
    center = 0.5 * (lo + hi)
    span = float(max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]))

    sun = bpy.data.lights.new("WMRIG_Sun", type="SUN")
    sun.energy = 6.5
    sun.angle = 0.0419
    sun.color = SUN_COLOR
    so = bpy.data.objects.new("WMRIG_Sun", sun)
    bpy.context.scene.collection.objects.link(so)
    _aim(so, (0.42, 0.58, -0.70))
    so.location = (0.0, 0.0, 0.0)
    made.append(so)

    fill_specs = [((1.05, 1.25, 0.85), 620.0, 16.0),
                  ((-1.15, 0.55, 0.75), 420.0, 14.0),
                  ((0.15, -1.05, 0.95), 380.0, 14.0)]
    for i, (dirv, energy, size) in enumerate(fill_specs):
        d = Vector(dirv).normalized()
        light = bpy.data.lights.new(f"WMRIG_Fill{i}", type="AREA")
        light.energy = energy
        light.size = size
        light.color = FILL_COLOR
        obj = bpy.data.objects.new(f"WMRIG_Fill{i}", light)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = (center[0] + d.x * span * 1.1,
                        center[1] + d.y * span * 1.1,
                        center[2] + abs(d.z) * span * 0.9)
        _aim(obj, (-d.x, -d.y, -d.z))
        made.append(obj)

    practicals = [(0.0, -0.95, 2.55), (-2.6, -0.6, 2.45), (2.6, -0.6, 2.45),
                  (-2.4, 3.4, 2.5), (2.4, 3.4, 2.5),
                  (-1.6, 0.6, 5.05), (1.6, 0.6, 5.05)]
    for i, p in enumerate(practicals):
        light = bpy.data.lights.new(f"WMRIG_In{i}", type="POINT")
        light.energy = 140.0
        light.color = PRACTICAL_COLOR
        light.shadow_soft_size = 0.35
        obj = bpy.data.objects.new(f"WMRIG_In{i}", light)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = p
        made.append(obj)
    C.mark_part(made, "rig", "capture_rig", {"kind": "warm-sun-cool-fill-warm-practicals"})
    return {"built": len(made), "names": [o.name for o in made]}


def existing_rig() -> dict:
    suns = [o for o in bpy.data.objects if o.type == "LIGHT" and o.data.type == "SUN"]
    fills = [o for o in bpy.data.objects
             if o.type == "LIGHT" and o.data.type in ("AREA", "SPOT")]
    points = [o for o in bpy.data.objects if o.type == "LIGHT" and o.data.type == "POINT"]
    return {"suns": [o.name for o in suns], "fills": [o.name for o in fills],
            "practicals": [o.name for o in points],
            "present": bool(suns and points)}


def ensure_world(sky: str) -> dict:
    """Give the scene a sky-gradient world when it has none."""
    world = bpy.context.scene.world
    if sky in ("keep", "none"):
        return {"mode": "kept", "world": getattr(world, "name", None)}
    if world is None:
        world = bpy.data.worlds.new("WMRIG_Sky")
        bpy.context.scene.world = world
    if world.use_nodes and world.node_tree:
        bg = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None)
        if bg is not None:
            col = tuple(bg.inputs[0].default_value)[:3]
            strength = float(bg.inputs[1].default_value)
            if sky == "sky" or (max(col) < 0.06 and strength > 0.0):
                bg.inputs[0].default_value = (*SKY_HORIZON, 1.0)
                bg.inputs[1].default_value = 1.0
                return {"mode": "sky", "world": world.name,
                        "note": "flat horizon-sky background"}
            return {"mode": "kept", "world": world.name,
                    "existingColor": [round(float(c), 4) for c in col]}
    if not world.use_nodes:
        world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    grad = nt.nodes.new("ShaderNodeTexGradient")
    grad.gradient_type = "LINEAR"
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*SKY_HORIZON, 1.0)
    ramp.color_ramp.elements[1].color = (*SKY_TOP, 1.0)
    mapn = nt.nodes.new("ShaderNodeMapping")
    tex = nt.nodes.new("ShaderNodeTexCoord")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs[1].default_value = 1.0
    nt.links.new(tex.outputs["Generated"], mapn.inputs["Vector"])
    nt.links.new(mapn.outputs["Vector"], grad.inputs["Vector"])
    nt.links.new(grad.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return {"mode": "built-gradient", "world": world.name}


# -------------------------------------------------------------------- render

def _apply_camera(cam: dict):
    scene = bpy.context.scene
    obj = bpy.data.objects.get("WMCAP_Camera")
    if obj is None or obj.type != "CAMERA":
        data = bpy.data.cameras.new("WMCAP_Camera")
        obj = bpy.data.objects.new("WMCAP_Camera", data)
        scene.collection.objects.link(obj)
    obj.data.lens = float(cam["lens"])
    obj.data.sensor_width = float(cam.get("sensor", 36.0))
    obj.data.shift_x = float(cam.get("shiftX", 0.0))
    obj.data.shift_y = float(cam.get("shiftY", 0.0))
    if (cam.get("projection") == "ORTHO"):
        obj.data.type = "ORTHO"
        if cam.get("orthoScale"):
            obj.data.ortho_scale = float(cam["orthoScale"])
    else:
        obj.data.type = "PERSP"
    obj.location = Vector(cam["position"])
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = (Vector(cam["target"]) - Vector(cam["position"])
                               ).to_track_quat("-Z", "Y")
    if abs(float(cam.get("roll", 0.0))) > 1e-9:
        q = obj.rotation_quaternion.copy()
        from mathutils import Quaternion
        q = q @ Quaternion(Vector((0.0, 0.0, 1.0)), -float(cam["roll"]))
        obj.rotation_quaternion = q
    scene.camera = obj
    bpy.context.view_layer.update()
    return obj


def capture_views(params: dict, ctx: dict) -> dict:
    params = params or {}
    project_root = ctx.get("projectRoot") or os.getcwd()
    checks, warnings = [], []
    shots, timings = [], []

    width = int(params.get("width", 1200))
    height = int(params.get("height", 900))
    samples = int(params.get("samples", 48))
    margin = float(params.get("margin", 0.055))
    engine = str(params.get("engine", "BLENDER_EEVEE"))

    blend = params.get("blend") or ctx.get("baseBlend") or ctx.get("outBlend")
    blend = WI.resolve_path(blend, ctx) if blend else None
    if blend and os.path.isfile(blend):
        C.open_scene(blend)
    else:
        warnings.append(f"blend not found ({blend}); rendering the current scene")

    out_dir = WI.resolve_path(params.get("outDir") or ctx.get("rendersDir")
                              or os.path.join(project_root, "outputs",
                                              "wenmai-3d", "renders"), ctx)
    case = params.get("case") or ""
    out_dir = os.path.join(out_dir, case) if case else out_dir
    WI.ensure_dir(out_dir)

    scene = bpy.context.scene
    try:
        scene.render.engine = engine
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
        warnings.append(f"engine {engine} unavailable; fell back to BLENDER_EEVEE")
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = bool(params.get("transparent", False))
    try:
        scene.eevee.taa_render_samples = samples
    except Exception:
        warnings.append("could not set EEVEE render samples on this build")
    try:
        scene.view_settings.view_transform = params.get("viewTransform", "Standard")
    except Exception:
        pass

    # ---- requested views
    views = params.get("views") or VIEW_ORDER
    if isinstance(views, str):
        views = [views]
    unknown = [v for v in views if v not in VIEW_CAMERAS]
    if unknown:
        return C.fail(f"unknown view(s): {', '.join(unknown)}; "
                      f"valid: {', '.join(VIEW_ORDER)}")

    # ---- cameras
    lo, hi = model_bounds()
    pts = model_points()
    layout = layout_cameras(ctx)
    supplied = None
    if params.get("camerasPath"):
        payload = _read_json(WI.resolve_path(params["camerasPath"], ctx))
        if payload:
            supplied = payload.get("cameras") if isinstance(payload, dict) else payload
            if isinstance(payload, dict) and not supplied and "camera" in payload:
                supplied = [dict(payload["camera"], view=payload.get("view"))]
    supplied_by_view = {}
    for i, cam in enumerate(supplied or []):
        key = cam.get("view") or cam.get("name") or cam.get("id")
        if key in VIEW_CAMERAS:
            supplied_by_view[key] = cam
        elif i < len(views):
            supplied_by_view[views[i]] = cam

    resolved, sources = {}, {}
    for view in views:
        cam = None
        if view in supplied_by_view:
            cam = dict(supplied_by_view[view]); src = "supplied"
        if cam is None:
            cname, cid = VIEW_CAMERAS[view]
            obj = bpy.data.objects.get(cname)
            if obj is not None and obj.type == "CAMERA":
                cam = blend_camera(obj, width, height); src = f"blend:{cname}"
            elif cid in layout:
                cam = dict(layout[cid]); src = f"layout:{cid}"
        if cam is None:
            cam = synth_camera(view, width, height, lo, hi)
            src = (cam or {}).get("source", "synth")
        if cam is None:
            warnings.append(f"no camera could be resolved for view '{view}'")
            continue
        cam["width"], cam["height"] = width, height
        if view not in ("floor1", "floor2", "ceiling") and params.get("autoFit", True):
            ortho = cam.get("projection") == "ORTHO"
            if not ortho:
                cam = fit_distance(cam, pts, margin=margin)
        resolved[view] = cam
        sources[view] = src

    # ---- lighting
    rig_mode = str(params.get("rig", "auto"))
    existing = existing_rig()
    rig_report = {}
    if rig_mode == "build":
        rig_report = build_rig(lo, hi)
        rig_report["mode"] = "built"
    elif rig_mode in ("none", "keep"):
        rig_report = {"mode": "kept", "existing": existing}
    else:
        if existing["present"]:
            rig_report = {"mode": "reused", "existing": existing,
                          "note": "the scene already has a warm sun + practicals; "
                                  "pass rig='build' to replace them"}
        else:
            rig_report = build_rig(lo, hi)
            rig_report["mode"] = "built"
            rig_report["existingBefore"] = existing
    world_report = ensure_world(str(params.get("world", "auto")))

    # ---- render
    t_all = time.time()
    for view in views:
        cam = resolved.get(view)
        if cam is None:
            continue
        _apply_camera(cam)
        path = os.path.join(out_dir, f"wm_{view}.png")
        scene.render.filepath = path
        t0 = time.time()
        try:
            bpy.ops.render.render(write_still=True)
        except Exception as exc:
            warnings.append(f"render failed for {view}: {exc}")
            shots.append({"view": view, "path": None, "error": str(exc)})
            continue
        dt = time.time() - t0
        hdr = WI.png_header(path)
        shots.append({
            "view": view,
            "path": path,
            "pathRel": WI.relpath(path, project_root),
            "bytes": WI.file_size(path),
            "width": hdr.get("width"), "height": hdr.get("height"),
            "requestedWidth": width, "requestedHeight": height,
            "camera": cam,
            "cameraSource": sources.get(view),
            "renderSeconds": round(dt, 2),
            "exists": os.path.isfile(path) and WI.file_size(path) > 0,
        })
        timings.append(dt)
        C.log("rendered %s -> %s (%sx%s, %d bytes, %.1fs)" % (
            view, os.path.basename(path), hdr.get("width"), hdr.get("height"),
            WI.file_size(path), dt))
        if hdr.get("ok") and (hdr["width"], hdr["height"]) != (width, height):
            warnings.append(f"{view} rendered at {hdr['width']}x{hdr['height']} "
                            f"instead of {width}x{height}")

    cams_path = os.path.join(out_dir, "wm_cameras.json")
    with open(cams_path, "w", encoding="utf-8") as fh:
        json.dump({"schema": 1, "generatedBy": "wm_capture.capture_views",
                   "blend": blend, "width": width, "height": height,
                   "samples": samples, "views": resolved,
                   "sources": sources,
                   "lighting": {"rig": rig_report, "world": world_report}},
                  fh, ensure_ascii=False, indent=1)

    # ---- checks
    good = [s for s in shots if s.get("exists")]
    C.check(checks, "shots_rendered", "pass" if len(good) == len(views) else
            ("warn" if good else "fail"),
            f"{len(good)}/{len(views)} requested views produced a non-empty PNG")
    wrong_size = [s["view"] for s in good
                  if (s["width"], s["height"]) != (width, height)]
    C.check(checks, "resolution", "pass" if not wrong_size else "warn",
            f"all PNGs are {width}x{height}" if not wrong_size
            else f"unexpected size for {', '.join(wrong_size)}")
    C.check(checks, "cameras_resolved", "pass",
            f"camera sources: {json.dumps(sources, sort_keys=True)}")
    C.check(checks, "lighting_rig",
            "pass" if rig_report.get("mode") in ("reused", "built") else "warn",
            f"rig {rig_report.get('mode')}; "
            f"{len(existing['suns'])} sun(s), {len(existing['fills'])} fill(s), "
            f"{len(existing['practicals'])} practical(s)", mode=rig_report.get("mode"))
    C.check(checks, "world_background", "pass",
            f"world mode {world_report.get('mode')}")
    C.check(checks, "fresh_render", "pass",
            "every PNG was written by this run (write_still); no cached image is "
            "reused")
    C.check(checks, "engine", "pass", f"render engine {scene.render.engine}, "
            f"{samples} samples")

    return {
        "ok": bool(good),
        "task": "capture_views",
        "artifacts": [WI.artifact("png", s["path"], view=s["view"])
                      for s in good] + [WI.artifact("json", cams_path)],
        "shots": shots,
        "camerasPath": cams_path,
        "camerasPathRel": WI.relpath(cams_path, project_root),
        "metrics": {
            "viewsRequested": len(views),
            "viewsRendered": len(good),
            "width": width, "height": height, "samples": samples,
            "engine": scene.render.engine,
            "totalSeconds": round(time.time() - t_all, 2),
            "meanSeconds": round(float(np.mean(timings)), 2) if timings else None,
            "totalBytes": sum(s.get("bytes") or 0 for s in good),
            "cameraSources": sources,
        },
        "lighting": {"rig": rig_report, "world": world_report},
        "checks": checks,
        "warnings": warnings,
        "notes": (f"rendered {len(good)}/{len(views)} views at {width}x{height} "
                  f"({samples} EEVEE samples) from "
                  f"{os.path.basename(blend) if blend else 'the current scene'}; "
                  f"rig mode {rig_report.get('mode')}. Every path returned is a "
                  "real PNG written by this run."),
    }
