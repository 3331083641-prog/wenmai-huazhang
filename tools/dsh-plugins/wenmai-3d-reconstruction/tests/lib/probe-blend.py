"""Harness-owned Blender probe: report what is really inside a .blend.

Used by tests/run-e2e.mjs to verify cross-part preservation independently of
what the plugin's own tools report. It never modifies the file.

    blender.exe -b -noaudio --python tests/lib/probe-blend.py -- <blend>

Prints one line `WMPROBE {json}` on stdout; everything else is Blender noise.
"""
from __future__ import annotations

import json
import sys

import bpy


def main() -> int:
    argv = sys.argv
    if "--" not in argv or len(argv) < argv.index("--") + 2:
        print("WMPROBE " + json.dumps({"ok": False, "error": "usage: -- <blend>"}))
        return 2
    blend = argv[argv.index("--") + 1]

    bpy.ops.wm.open_mainfile(filepath=blend)

    parts: dict[str, int] = {}
    tagged = 0
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    triangles = 0
    for obj in meshes:
        part = obj.get("wm_part") or "(untagged)"
        parts[part] = parts.get(part, 0) + 1
        if obj.get("wm_part"):
            tagged += 1
        try:
            for poly in obj.data.polygons:
                triangles += max(1, len(poly.vertices) - 2)
        except Exception:
            pass

    frames = sorted(o.name for o in bpy.data.objects if o.name.startswith("FRAME_"))
    names = sorted(o.name for o in meshes)

    payload = {
        "ok": True,
        "blend": blend,
        "objects": len(bpy.data.objects),
        "meshes": len(meshes),
        "taggedMeshes": tagged,
        "triangles": triangles,
        "parts": parts,
        "frameAnchors": frames,
        "frameAnchorObjects": len([o for o in bpy.data.objects if o.name.startswith("FRAME_")]),
        "nameCounts": {
            "ROOF": len([n for n in names if n.startswith("ROOF_")]),
            "TILE": len([n for n in names if n.startswith("TILE_")]),
            "COLUMN": len([n for n in names if n.startswith("COLUMN_")]),
            "BEAM": len([n for n in names if n.startswith("BEAM_")]),
            "BASE": len([n for n in names if n.startswith("BASE_")]),
            "PROP": len([n for n in names if n.startswith("PROP_")]),
            "GALWALL": len([n for n in names if n.startswith("GALWALL_")]),
            "SHOWCASE": len([n for n in names if n.startswith("SHOWCASE_")]),
        },
        "materials": len(bpy.data.materials),
    }
    print("WMPROBE " + json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
