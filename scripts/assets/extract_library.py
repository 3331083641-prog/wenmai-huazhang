"""从 5.html 精确抽取 14 件允许器物的建模代码，生成 TS 模块（UTF-8 无 BOM）。"""
import argparse
import io
import re
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path, help="用户提供的原始器物 HTML（原 5.html）")
parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[2] / "frontend/src/features/heritage-gallery/props/assets/library.gen.ts", help="生成的 TS 模块路径")
args = parser.parse_args()
SRC = args.source
OUT = args.output

src = io.open(SRC, encoding="utf-8", errors="replace").read().split("\n")

def block(a, b):
    """1-based inclusive line range，并去掉尾部的空行 / 对象收尾 / 注释。"""
    lines = list(src[a - 1:b])
    while lines:
        t = lines[-1].strip()
        if not t or t == "};" or t.startswith("//") or t.startswith("/*"):
            lines.pop()
            continue
        break
    return "\n".join(lines)

# 571..765 = 纹理生成器 + MAT + box/cyl/addFlushSpandrel
shared = block(571, 765)

ALLOWED = ["DIY_A01", "DIY_A02", "DIY_A04", "DIY_A05", "DIY_A07", "DIY_A09",
           "DIY_B02", "DIY_C02", "DIY_D01", "DIY_D04", "DIY_E01", "DIY_E02",
           "DIY_E05", "DIY_F05"]

# 每个 builder 的行区间（含结尾 "},"）
RANGES = {
    "DIY_A06": (768, 797), "DIY_A07": (798, 844), "DIY_A10": (845, 893),
    "DIY_B02": (894, 935), "DIY_B05": (936, 957), "DIY_C02": (958, 994),
    "DIY_C03": (995, 1021), "DIY_D04": (1022, 1055), "DIY_D05": (1056, 1084),
    "DIY_E02": (1085, 1118), "DIY_E05": (1119, 1151), "DIY_F05": (1152, 1197),
    "DIY_A01": (1198, 1239), "DIY_A02": (1240, 1265), "DIY_A04": (1266, 1296),
    "DIY_A05": (1297, 1325), "DIY_A09": (1326, 1342), "DIY_D01": (1343, 1377),
    "DIY_E01": (1378, 1406),
}

parts = []
for aid in ALLOWED:
    a, b = RANGES[aid]
    body = block(a, b).rstrip()
    if not body.endswith(","):
        body += ","
    parts.append("  " + body.lstrip())

header = '''// @ts-nocheck
/**
 * 器物资产库（由 Gemini 的 5.html 精确移植）
 *
 * 来源：用户提供的器物原型 HTML 中的 MAT / 纹理生成器 / box / cyl /
 * addFlushSpandrel / BUILDERS。只保留用户白名单里的 14 件，另外五件
 * （DIY_A06 / A10 / B05 / C03 / D05）的构建代码根本没有抽进来。
 *
 * 为什么不用原 HTML 的 GLB 导出：那个导出器把手写几何展开成大量独立节点，
 * 且不保证 CanvasTexture / 透明 / 父子关系完整。这里直接把原始构建函数接进
 * Three.js 运行时构建，纹理由 canvas 现场生成，节点名与父子层级与原始一致，
 * 交互控制器按节点名找零件。
 */

import * as THREE from 'three';

'''

out = header + shared + "\n\nexport const PROP_BUILDERS: Record<string, () => THREE.Group> = {\n" + "\n".join(parts) + "\n};\n"

# ---- fixups：原 HTML 里的浮点越界会算出 NaN（负数的 1.6 次幂），必须钳住
out = out.replace(
    "const u = (0.17 - pos.getX(i)) / 0.34;",
    "const u = Math.max(0, (0.17 - pos.getX(i)) / 0.34);")

io.open(OUT, "w", encoding="utf-8", newline="\n").write(out)

# 统计
print("wrote", OUT, len(out), "bytes")
print("builders:", len(ALLOWED))
for aid in ALLOWED:
    a, b = RANGES[aid]
    print("  %s lines %d-%d" % (aid, a, b))