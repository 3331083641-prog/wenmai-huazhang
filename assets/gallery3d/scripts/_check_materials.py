"""Cross-check the GLB material names against the shared PALETTE keys."""
from __future__ import annotations

import json
import re
import struct

GLB = "../exports/wenmai_gallery.glb"

data = open(GLB, "rb").read()
clen = struct.unpack("<I", data[12:16])[0]
gltf = json.loads(data[20:20 + clen].decode("utf-8"))
names = [m.get("name") for m in gltf["materials"]]

src = open("gal_common.py", encoding="utf-8").read()
block = src[src.index("PALETTE"):]
block = block[:block.index("}")]
keys = set(re.findall(r'"([a-z_]+)":', block))

print("nodes", len(gltf["nodes"]), "meshes", len(gltf["meshes"]),
      "materials", len(names))
print("glb-only:", sorted(set(names) - keys))
print("palette-only:", sorted(keys - set(names)))
print("palette keys:", len(keys))