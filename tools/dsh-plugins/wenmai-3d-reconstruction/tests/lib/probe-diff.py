"""Harness-owned Blender probe: diff the mesh inventories of two .blend files.

    blender.exe -b -noaudio --python tests/lib/probe-diff.py -- <blendA> <blendB>

Prints one line `WMPROBE {json}` with what B removed from / added to A, grouped
by the leading name token (ROOF_, TILE_, FRAME_, ...). Read-only.
"""
from __future__ import annotations

import json
import sys

import bpy


def inventory(path: str):
    bpy.ops.wm.open_mainfile(filepath=path)
    out = {}
    for obj in bpy.data.objects:
        out[obj.name] = {"type": obj.type, "part": obj.get("wm_part")}
    return out


def prefix(name: str) -> str:
    head = name.split("_")[0]
    return head + ("_" if "_" in name else "")


def main() -> int:
    argv = sys.argv
    if "--" not in argv or len(argv) < argv.index("--") + 3:
        print("WMPROBE " + json.dumps({"ok": False, "error": "usage: -- <blendA> <blendB>"}))
        return 2
    rest = argv[argv.index("--") + 1:]
    a_path, b_path = rest[0], rest[1]

    a = inventory(a_path)
    b = inventory(b_path)

    a_names, b_names = set(a), set(b)
    removed = sorted(a_names - b_names)
    added = sorted(b_names - a_names)

    def group(names):
        counts: dict[str, int] = {}
        for name in names:
            counts[prefix(name)] = counts.get(prefix(name), 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    payload = {
        "ok": True,
        "blendA": a_path,
        "blendB": b_path,
        "objectsA": len(a_names),
        "objectsB": len(b_names),
        "removedCount": len(removed),
        "addedCount": len(added),
        "removedByPrefix": group(removed),
        "addedByPrefix": group(added),
        "removedSample": removed[:40],
        "addedSample": added[:40],
        "removedUntagged": len([n for n in removed if not a[n].get("part")]),
    }
    print("WMPROBE " + json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
