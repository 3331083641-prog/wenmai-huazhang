"""Shared helpers for every 纹脉华章 Blender job.

Owned by the plugin Lead. Modules may import it, but must not edit it; if a
helper is missing, ask the Lead so the change stays in one place.

All jobs run inside Blender's bundled Python (3.13 / numpy 2.3) via
``wm_job.py``. Units are metres, Z is up, the plinth top is z = 0 and the model
is centred on the origin (see docs/CONTRACT.md).
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
import traceback

import bpy
from mathutils import Euler, Matrix, Vector

# --------------------------------------------------------------------- colours
# sRGB values sampled from the ten references (same family as the v5 build, so
# the web toon pass keeps working). Keys are shared with Three.js by material
# name only, so the values can be tuned freely.
PALETTE = {
    "roof_tile":    (0.330, 0.376, 0.418),
    "roof_tile_b":  (0.372, 0.412, 0.448),
    "roof_slate":   (0.212, 0.243, 0.278),
    "roof_ridge":   (0.259, 0.290, 0.325),
    "timber":       (0.545, 0.353, 0.235),
    "timber_dark":  (0.290, 0.180, 0.125),
    "timber_warm":  (0.639, 0.427, 0.271),
    "wood_light":   (0.706, 0.514, 0.337),
    "wall":         (0.937, 0.902, 0.831),
    "wall_shadow":  (0.851, 0.812, 0.741),
    "stone":        (0.725, 0.706, 0.655),
    "stone_dark":   (0.545, 0.529, 0.490),
    "stone_warm":   (0.784, 0.753, 0.690),
    "paving":       (0.659, 0.643, 0.604),
    "paving_b":     (0.706, 0.678, 0.628),
    "gravel":       (0.760, 0.735, 0.678),
    "red":          (0.698, 0.227, 0.173),
    "red_deep":     (0.478, 0.145, 0.114),
    "gold":         (0.710, 0.545, 0.216),
    "gold_light":   (0.847, 0.702, 0.365),
    "plant":        (0.310, 0.478, 0.227),
    "plant_dark":   (0.212, 0.345, 0.161),
    "plant_light":  (0.408, 0.565, 0.259),
    "bamboo":       (0.435, 0.545, 0.239),
    "flower":       (0.792, 0.400, 0.412),
    "porcelain":    (0.855, 0.888, 0.871),
    "porcelain_bl": (0.235, 0.353, 0.545),
    "ink":          (0.110, 0.096, 0.090),
    "paper":        (0.965, 0.945, 0.902),
    "lamp_glow":    (1.000, 0.800, 0.520),
}
EMISSIVE = {"lamp_glow"}


# ----------------------------------------------------------------- job plumbing

def project_root() -> str | None:
    """Authorized root, injected by the Node runner as WM_PROJECT_ROOT."""
    return os.environ.get("WM_PROJECT_ROOT") or None


def assert_inside_project(path: str, label: str = "path") -> str:
    """Refuse to write outside the authorized project root.

    The Node side already validates every path, but a task parameter could still
    smuggle a relative path that Blender would resolve against its own working
    directory. This is the last line of defence before a file is written.
    """
    root = project_root()
    resolved = os.path.abspath(path)
    if root is None:
        return resolved
    root_abs = os.path.abspath(root)
    try:
        common = os.path.commonpath([root_abs, resolved])
    except ValueError:
        common = ""
    if common != root_abs:
        raise PermissionError(
            f"{label} is outside the authorized project root: {resolved} (root: {root_abs})"
        )
    return resolved


def read_job() -> dict:
    """Read the job JSON path handed over after ``--`` and return the object."""
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit("wm_job.py: missing job path after --")
    job_path = argv[argv.index("--") + 1]
    with open(job_path, "r", encoding="utf-8") as fh:
        job = json.load(fh)
    job["_jobPath"] = job_path
    return job


def ensure_dirs(ctx: dict, *keys: str) -> None:
    for key in ("workDir", "sceneDir", "rendersDir", "reportsDir", *keys):
        path = ctx.get(key)
        if path:
            os.makedirs(path, exist_ok=True)


def write_result(job: dict, result: dict) -> None:
    """Always write the result file, even on failure, so Node never guesses."""
    path = job.get("context", {}).get("resultPath")
    if not path:
        raise SystemExit("wm_job.py: job.context.resultPath is required")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = dict(result)
    payload.setdefault("ok", True)
    payload.setdefault("task", job.get("task"))
    payload["jobId"] = job.get("jobId")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def check(checks: list, ident: str, status: str, detail: str, **extra) -> dict:
    """Append one structured check (pass | warn | fail | manual | not_checked)."""
    item = {"id": ident, "status": status, "detail": detail}
    item.update({k: v for k, v in extra.items() if v is not None})
    checks.append(item)
    return item


def log(*args) -> None:
    print("[WM]", *args, flush=True)


def now_id(prefix: str = "job") -> str:
    return f"{prefix}-{time.strftime('%Y%m%d-%H%M%S')}"


def safe_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def jsonable(obj):
    """Convert Blender/numpy values into JSON-safe data (best effort)."""
    try:
        import numpy as np
        if isinstance(obj, (np.floating, np.integer)):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except Exception:
        pass
    if isinstance(obj, (Vector, Euler, Matrix)):
        return list(obj)
    if isinstance(obj, (set, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, list):
        return [jsonable(v) for v in obj]
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    return obj


# --------------------------------------------------------------------- scenes

def reset_scene() -> bpy.types.Scene:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.engine = "BLENDER_EEVEE"
    return scene


def open_scene(path: str | None, reset_if_missing: bool = True) -> bpy.types.Scene:
    """Open ``path`` if it exists; otherwise start from an empty scene."""
    if path and os.path.isfile(path):
        bpy.ops.wm.open_mainfile(filepath=path)
        scene = bpy.context.scene
        scene.unit_settings.system = "METRIC"
        scene.unit_settings.scale_length = 1.0
        try:
            scene.render.engine = "BLENDER_EEVEE"
        except Exception:
            pass
        return scene
    if reset_if_missing:
        return reset_scene()
    raise FileNotFoundError(path or "<none>")


def save_blend(path: str) -> str:
    path = assert_inside_project(path, "blend output")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    return path


def get_collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    return col


# ------------------------------------------------------------------ materials

def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def material(key: str, rough: float = 0.72, metal: float = 0.0) -> bpy.types.Material:
    """Flat-colour PBR material named ``M_<key>``; cached per scene."""
    name = f"M_{key}"
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    srgb = PALETTE.get(key, (0.6, 0.6, 0.6))
    rgb = tuple(_srgb_to_linear(c) for c in srgb)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        if key in EMISSIVE:
            bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
            bsdf.inputs["Emission Strength"].default_value = 1.6
    mat.diffuse_color = (*rgb, 1.0)
    mat["toon_key"] = key
    mat["srgb"] = list(srgb)
    return mat


# --------------------------------------------------------------------- meshes

def mark_part(objects, part: str, component: str | None = None, params: dict | None = None) -> None:
    """Tag objects so a later run can replace exactly this component group."""
    payload = json.dumps(params or {}, ensure_ascii=False, sort_keys=True)[:8000]
    for obj in objects:
        if obj is None:
            continue
        obj["wm_part"] = part
        if component:
            obj["wm_component"] = component
        obj["wm_params"] = payload


def delete_part(part: str) -> int:
    """Delete every object previously tagged with ``part``; returns the count."""
    doomed = [o for o in bpy.data.objects if o.get("wm_part") == part]
    for obj in doomed:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data is not None and getattr(data, "users", 0) == 0:
            try:
                if isinstance(data, bpy.types.Mesh):
                    bpy.data.meshes.remove(data)
                elif isinstance(data, bpy.types.Curve):
                    bpy.data.curves.remove(data)
            except Exception:
                pass
    return len(doomed)


def link_only(obj: bpy.types.Object, col: bpy.types.Collection) -> None:
    for other in list(obj.users_collection):
        other.objects.unlink(obj)
    col.objects.link(obj)


def mesh_object(name: str, verts, faces, mat_key: str | None = None,
                col: bpy.types.Collection | None = None,
                smooth: bool = False) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.validate(verbose=False)
    me.update()
    obj = bpy.data.objects.new(name, me)
    (col or bpy.context.scene.collection).objects.link(obj)
    if mat_key:
        obj.data.materials.append(material(mat_key))
    if smooth:
        for poly in me.polygons:
            poly.use_smooth = True
    return obj


def box(name: str, size, location, mat_key: str | None = None,
        col: bpy.types.Collection | None = None,
        rotation=None) -> bpy.types.Object:
    """Axis-aligned box helper; ``rotation`` is optional Euler XYZ radians."""
    sx, sy, sz = (float(v) for v in size)
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    verts = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
             (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    obj = mesh_object(name, verts, faces, mat_key, col)
    obj.location = Vector(location)
    if rotation:
        obj.rotation_euler = Euler(tuple(rotation), "XYZ")
    return obj


def cylinder(name: str, radius: float, depth: float, location,
             mat_key: str | None = None, col: bpy.types.Collection | None = None,
             segments: int = 16, radius_top: float | None = None,
             rotation=None) -> bpy.types.Object:
    """Closed cylinder/frustum built by hand (no bpy.ops, so it is deterministic)."""
    r0 = float(radius)
    r1 = r0 if radius_top is None else float(radius_top)
    dz = float(depth) / 2.0
    verts = []
    for z, r in ((-dz, r0), (dz, r1)):
        for i in range(segments):
            a = 2.0 * math.pi * i / segments
            verts.append((math.cos(a) * r, math.sin(a) * r, z))
    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((i, j, segments + j, segments + i))
    faces.append(tuple(range(segments - 1, -1, -1)))
    faces.append(tuple(range(segments, 2 * segments)))
    obj = mesh_object(name, verts, faces, mat_key, col)
    obj.location = Vector(location)
    if rotation:
        obj.rotation_euler = Euler(tuple(rotation), "XYZ")
    return obj


# --------------------------------------------------------------- measurements

def scene_bounds(objects=None) -> dict:
    objs = objects if objects is not None else [o for o in bpy.data.objects if o.type == "MESH"]
    lo = [math.inf, math.inf, math.inf]
    hi = [-math.inf, -math.inf, -math.inf]
    for obj in objs:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            for i in range(3):
                lo[i] = min(lo[i], world[i])
                hi[i] = max(hi[i], world[i])
    if not math.isfinite(lo[0]):
        return {"min": [0, 0, 0], "max": [0, 0, 0], "size": [0, 0, 0]}
    return {"min": lo, "max": hi, "size": [hi[i] - lo[i] for i in range(3)]}


def object_inventory(objects=None) -> list:
    objs = objects if objects is not None else list(bpy.data.objects)
    out = []
    for obj in objs:
        if obj.type != "MESH":
            continue
        me = obj.data
        out.append({
            "name": obj.name,
            "part": obj.get("wm_part"),
            "component": obj.get("wm_component"),
            "verts": len(me.vertices),
            "faces": len(me.polygons),
            "materials": [m.name for m in me.materials if m],
        })
    return out


def scene_stats() -> dict:
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    triangles = 0
    for obj in meshes:
        me = obj.data
        for poly in me.polygons:
            triangles += max(1, len(poly.vertices) - 2)
    images = [{"name": im.name, "width": im.size[0], "height": im.size[1]} for im in bpy.data.images
              if im.size[0] > 0]
    return {
        "objects": len(bpy.data.objects),
        "meshes": len(meshes),
        "triangles": triangles,
        "materials": len(bpy.data.materials),
        "collections": len(bpy.data.collections),
        "images": images,
    }


def audit_mesh(obj: bpy.types.Object) -> dict:
    """Cheap topology audit used by the inspector."""
    me = obj.data
    edge_faces: dict = {}
    for poly in me.polygons:
        verts = list(poly.vertices)
        for i, a in enumerate(verts):
            b = verts[(i + 1) % len(verts)]
            key = (a, b) if a < b else (b, a)
            edge_faces[key] = edge_faces.get(key, 0) + 1
    boundary = sum(1 for count in edge_faces.values() if count == 1)
    non_manifold = sum(1 for count in edge_faces.values() if count > 2)
    degenerate = sum(1 for poly in me.polygons if poly.area <= 1e-9)
    flipped = 0
    for poly in me.polygons:
        if poly.normal.z < -0.999 and poly.center.z < 0:
            flipped += 1
    return {
        "name": obj.name,
        "verts": len(me.vertices),
        "faces": len(me.polygons),
        "boundaryEdges": boundary,
        "nonManifoldEdges": non_manifold,
        "degenerateFaces": degenerate,
        "suspiciousNormals": flipped,
    }


# -------------------------------------------------------------------- export

def export_glb(path: str, yup: bool = True, selection_only: bool = False) -> str:
    path = assert_inside_project(path, "glb output")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    kwargs = dict(
        filepath=path,
        export_format="GLB",
        export_yup=bool(yup),
        use_selection=bool(selection_only),
        export_apply=True,
        export_cameras=False,
        export_lights=False,
    )
    try:
        bpy.ops.export_scene.gltf(**kwargs)
    except TypeError:
        # Older/newer operator signatures: retry with the minimal set.
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=bool(selection_only))
    return path


def file_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def artifact(kind: str, path: str) -> dict:
    return {"kind": kind, "path": path, "bytes": file_size(path)}


def fail(message: str, **extra) -> dict:
    result = {"ok": False, "error": {"message": message}}
    result.update(extra)
    return result


def guard(fn):
    """Wrap a task function so an exception still produces a JSON result."""
    def wrapper(params: dict, ctx: dict) -> dict:
        try:
            return fn(params or {}, ctx or {})
        except Exception:
            return fail(traceback.format_exc(limit=8))
    return wrapper
