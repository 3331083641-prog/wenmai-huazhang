"""GLB export with a Blender-free structural check of the emitted file.

Params (docs/CONTRACT.md section 4B): ``blend, out?, copyTo?, draco?: false,
yUp?: true``.

The report does not take Blender's word for the result: it re-opens the written
GLB with pure Python (12-byte header, then the JSON chunk) and counts meshes,
primitives, materials, textures and accessors from the container itself, and it
captures any warning the exporter emits through the ``io_scene_gltf2`` logger.
A temporary re-import into a clean scene is also run so that a file the
exporter *claims* to have written is proven loadable by Blender itself.
"""
from __future__ import annotations

import json
import logging
import os
import struct

import bpy

import wm_common as WC
import wm_mesh as M

DEFAULTS = {"draco": False, "yUp": True}


class _Collect(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.records = []

    def emit(self, record):
        try:
            self.records.append(f"{record.levelname}: {record.name}: {record.getMessage()}")
        except Exception:
            pass


def parse_glb(path: str) -> dict:
    """Read the GLB container directly (no Blender, no third-party library)."""
    out = {"ok": False, "bytes": 0, "version": None, "chunks": 0, "json": None,
            "errors": []}
    try:
        out["bytes"] = os.path.getsize(path)
        with open(path, "rb") as fh:
            head = fh.read(12)
            if len(head) < 12:
                out["errors"].append("file shorter than the 12-byte GLB header")
                return out
            magic, version, length = struct.unpack("<III", head)
            out["version"] = version
            if magic != 0x46546C67:
                out["errors"].append(f"bad magic 0x{magic:08x} (expected glTF)")
            if length != out["bytes"]:
                out["errors"].append(f"header length {length} != file size {out['bytes']}")
            while fh.tell() < min(length, out["bytes"]):
                chunk_head = fh.read(8)
                if len(chunk_head) < 8:
                    break
                clen, ctype = struct.unpack("<II", chunk_head)
                data = fh.read(clen)
                out["chunks"] += 1
                if ctype == 0x4E4F534A and out["json"] is None:
                    out["json"] = json.loads(data.decode("utf-8"))
    except Exception as exc:                     # pragma: no cover
        out["errors"].append(repr(exc))
    out["ok"] = not out["errors"] and out["json"] is not None
    return out


def _glb_summary(doc: dict, size: int) -> dict:
    meshes = doc.get("meshes") or []
    prims = sum(len(m.get("primitives") or []) for m in meshes)
    images = doc.get("images") or []
    textures = doc.get("textures") or []
    materials = doc.get("materials") or []
    nodes = doc.get("nodes") or []
    accessors = doc.get("accessors") or []
    triangles = 0
    for m in meshes:
        for p in (m.get("primitives") or []):
            idx = p.get("indices")
            mode = p.get("mode", 4)
            if idx is None or mode != 4:
                continue
            count = (accessors[idx].get("count") or 0) if idx < len(accessors) else 0
            triangles += count // 3
    return {
        "meshes": len(meshes),
        "primitives": prims,
        "materials": len(materials),
        "textures": len(textures),
        "images": [{"name": im.get("name") or im.get("uri") or f"image{i}",
                    "mimeType": im.get("mimeType")} for i, im in enumerate(images)],
        "nodes": len(nodes),
        "accessors": len(accessors),
        "triangles": triangles,
        "extensionsUsed": doc.get("extensionsUsed") or [],
        "generator": (doc.get("asset") or {}).get("generator"),
        "bytes": size,
    }


def export_glb(params: dict, ctx: dict) -> dict:
    params = dict(params or {})
    blend = params.get("blend") or params.get("baseBlend") or ctx.get("baseBlend")
    if not blend or not os.path.isfile(blend):
        return WC.fail(f"export_glb: blend not found: {blend}")
    yup = bool(params.get("yUp", DEFAULTS["yUp"]))
    draco = bool(params.get("draco", DEFAULTS["draco"]))
    scene = WC.open_scene(blend)
    checks = []
    warnings = []

    scene_dir = ctx.get("sceneDir") or os.path.dirname(blend)
    out = params.get("out") or os.path.join(scene_dir, "wenmai_scene.glb")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

    stats_before = WC.scene_stats()
    root = logging.getLogger()
    collector = _Collect()
    old_level = root.level
    root.addHandler(collector)
    root.setLevel(logging.WARNING)
    try:
        WC.export_glb(out, yup=yup)
    finally:
        root.removeHandler(collector)
        root.setLevel(old_level)

    if not os.path.isfile(out) or os.path.getsize(out) == 0:
        return WC.fail("export_glb: exporter produced no file",
                       artifacts=[WC.artifact("blend", blend)],
                       glbPath=out)

    blob = parse_glb(out)
    summary = _glb_summary(blob["json"] or {}, blob["bytes"]) if blob["json"] else {}
    warnings.extend(collector.records)

    copied = None
    copy_to = params.get("copyTo")
    if copy_to:
        project_root = os.path.abspath(ctx.get("projectRoot") or r"D:\wenmai-huazhang")
        target = os.path.abspath(copy_to)
        if not target.startswith(project_root):
            warnings.append(f"copyTo outside the project root ignored: {copy_to}")
        else:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(out, "rb") as src, open(target, "wb") as dst:
                dst.write(src.read())
            copied = target

    # ---- independent re-import into a clean scene -------------------------
    reimport = {"ok": False, "meshes": 0, "triangles": 0, "materials": 0}
    try:
        WC.reset_scene()
        bpy.ops.import_scene.gltf(filepath=out)
        meshes = [o for o in bpy.data.objects if o.type == "MESH"]
        reimport = {
            "ok": len(meshes) > 0,
            "meshes": len(meshes),
            "triangles": sum(
                (len(o.data.loop_triangles) if o.data.loop_triangles else 0)
                or max(0, len(o.data.polygons)) for o in meshes),
            "materials": len(bpy.data.materials),
        }
        for o in meshes:
            o.data.calc_loop_triangles()
        reimport["triangles"] = sum(len(o.data.loop_triangles) for o in meshes)
    except Exception as exc:
        warnings.append(f"re-import check failed: {exc!r}")

    WC.check(checks, "glb_container", "pass" if blob["ok"] else "fail",
             f"GLB v{blob['version']} {blob['bytes']} bytes, {blob['chunks']} chunks, "
             f"header self-consistent" if blob["ok"]
             else f"container errors: {blob['errors']}")
    WC.check(checks, "glb_contents",
             "pass" if summary.get("meshes", 0) > 0 else "fail",
             f"meshes={summary.get('meshes')} primitives={summary.get('primitives')} "
             f"materials={summary.get('materials')} textures={summary.get('textures')} "
             f"nodes={summary.get('nodes')}")
    WC.check(checks, "glb_triangles",
             "pass" if 0 < summary.get("triangles", 0) <= 350000 else "warn",
             f"triangles={summary.get('triangles')} (web budget 350000)")
    WC.check(checks, "glb_reimport_loadable",
             "pass" if reimport["ok"] else "fail",
             f"re-imported into a clean scene: {reimport['meshes']} meshes, "
             f"{reimport['triangles']} triangles, {reimport['materials']} materials")
    WC.check(checks, "glb_no_export_warnings",
             "pass" if not collector.records else "warn",
             f"exporter logger warnings: {len(collector.records)}"
             + ("; first: " + collector.records[0][:180] if collector.records else ""))
    if draco:
        WC.check(checks, "glb_draco",
                 "pass" if "KHR_draco_mesh_compression" in (summary.get("extensionsUsed") or [])
                 else "warn",
                 "draco requested but the exporter reports extensionsUsed="
                 f"{summary.get('extensionsUsed')}")
    else:
        WC.check(checks, "glb_draco", "pass", "not requested (draco=False)")

    metrics = {
        "bytes": blob["bytes"],
        "meshes": summary.get("meshes"),
        "primitives": summary.get("primitives"),
        "triangles": summary.get("triangles"),
        "materials": summary.get("materials"),
        "textures": summary.get("textures"),
        "nodes": summary.get("nodes"),
        "sceneObjects": stats_before["objects"],
        "sceneTriangles": stats_before["triangles"],
        "yUp": yup,
        "draco": draco,
        "generator": summary.get("generator"),
        "reimportTriangles": reimport["triangles"],
    }
    notes = (f"exported {blob['bytes']} bytes from {os.path.basename(blend)}: "
             f"{summary.get('meshes')} meshes / {summary.get('primitives')} primitives, "
             f"{summary.get('triangles')} triangles, {summary.get('materials')} materials, "
             f"{summary.get('textures')} textures, yUp={yup}"
             + (f", copied to {copied}" if copied else "")
             + (f", {len(collector.records)} exporter warnings" if collector.records else
                ", no exporter warnings"))
    return M.result("export_glb", ctx, params, [o for o in bpy.data.objects if o.type == "MESH"],
                    [WC.artifact("glb", out)] + ([WC.artifact("glb", copied)] if copied else []),
                    metrics, checks, warnings, notes)
