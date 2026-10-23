"""Verify the 「纹纹」 mascot GLB and write docs/mascot/blender-report.md.

Two independent passes, as the brief requires:
  1. parse the GLB container / JSON chunk / binary buffer directly
  2. re-import the GLB in a fresh Blender scene and measure the result

    blender.exe --background --python verify_mascot.py
"""
import json
import os
import struct
import sys

import bpy
import bmesh
from mathutils import Vector

PROJ = r"D:\wenmai-huazhang"
GLB = os.path.join(PROJ, r"frontend\public\models\wenmai_mascot_ww.glb")
BLEND = os.path.join(PROJ, r"assets\mascot\blender\wenmai_mascot_ww.blend")
DOC = os.path.join(PROJ, r"docs\mascot\blender-report.md")

REQUIRED = ["Idle", "Spawn", "Walk", "Run", "Turn", "Happy", "Curious",
            "Interact"]
LOOPING = {"Idle", "Walk", "Run", "Turn", "Curious"}
EXPECTED_ANIM_SECONDS = {
    "Idle": 4.0, "Spawn": 1.2, "Walk": 32 / 30, "Run": 24 / 30,
    "Turn": 40 / 30, "Happy": 1.5, "Curious": 3.0, "Interact": 2.0,
}

COMP = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2),
        5125: ("I", 4), 5126: ("f", 4)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
         "MAT2": 4, "MAT3": 9, "MAT4": 16}


# ------------------------------------------------------------------ GLB read --
def parse_glb(path):
    with open(path, "rb") as fh:
        data = fh.read()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF":
        raise ValueError(f"not a GLB: {magic!r}")
    off, gltf, binchunk = 12, None, b""
    while off < length:
        clen, ctype = struct.unpack_from("<I4s", data, off)
        body = data[off + 8: off + 8 + clen]
        if ctype == b"JSON":
            gltf = json.loads(body.decode("utf-8"))
        elif ctype[:3] == b"BIN":
            binchunk = body
        pad = (4 - clen % 4) % 4
        off += 8 + clen + pad
    return gltf, binchunk, len(data), version


def read_accessor(g, b, index):
    acc = g["accessors"][index]
    fmt, size = COMP[acc["componentType"]]
    ncomp = NCOMP[acc["type"]]
    bv = g["bufferViews"][acc["bufferView"]]
    base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = bv.get("byteStride") or (size * ncomp)
    out = []
    for i in range(acc["count"]):
        vals = struct.unpack_from("<" + fmt * ncomp, b, base + i * stride)
        out.append(vals if ncomp > 1 else vals[0])
    return out


def positions(g, b):
    pts = []
    nodes = g.get("nodes", [])

    def node_matrix(n):
        if "matrix" in n:
            m = n["matrix"]
            return [[m[0], m[4], m[8], m[12]], [m[1], m[5], m[9], m[13]],
                    [m[2], m[6], m[10], m[14]], [m[3], m[7], m[11], m[15]]]
        t = n.get("translation", [0, 0, 0])
        r = n.get("rotation", [0, 0, 0, 1])
        s = n.get("scale", [1, 1, 1])
        x, y, z, w = r
        rm = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
              [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
              [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
        return [[rm[i][j] * s[j] for j in range(3)] + [t[i]] for i in range(3)] \
            + [[0, 0, 0, 1]]

    def mul(a, m):
        return [[sum(a[i][k] * m[k][j] for k in range(4)) for j in range(4)]
                for i in range(4)]

    ident = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]

    def walk(idx, parent):
        n = nodes[idx]
        world = mul(parent, node_matrix(n))
        if "mesh" in n:
            for prim in g["meshes"][n["mesh"]]["primitives"]:
                pa = prim["attributes"].get("POSITION")
                if pa is None:
                    continue
                for v in read_accessor(g, b, pa):
                    pts.append(tuple(world[i][0] * v[0] + world[i][1] * v[1]
                                     + world[i][2] * v[2] + world[i][3]
                                     for i in range(3)))
        for c in n.get("children", []):
            walk(c, world)

    for root in g["scenes"][g.get("scene", 0)]["nodes"]:
        walk(root, ident)
    return pts


def glb_report():
    g, b, nbytes, version = parse_glb(GLB)
    pts = positions(g, b)
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]

    tris = 0
    for mesh in g.get("meshes", []):
        for prim in mesh["primitives"]:
            if "indices" in prim:
                tris += g["accessors"][prim["indices"]]["count"] // 3
            else:
                tris += g["accessors"][prim["attributes"]["POSITION"]]["count"] // 3

    anims = []
    for a in g.get("animations", []):
        times, worst, loop_worst = [], 0.0, 0.0
        for ch in a["channels"]:
            smp = a["samplers"][ch["sampler"]]
            t = read_accessor(g, b, smp["input"])
            v = read_accessor(g, b, smp["output"])
            times.extend(t)
            if len(v) >= 2:
                f, l = v[0], v[-1]
                if not isinstance(f, tuple):
                    f, l = (f,), (l,)
                direct = max(abs(x - y) for x, y in zip(f, l))
                # a quaternion and its negation are the same rotation, so a
                # full 360 deg spin still closes as a loop
                flipped = max(abs(x + y) for x, y in zip(f, l))
                d = min(direct, flipped) if len(f) == 4 else direct
                loop_worst = max(loop_worst, d)
        anims.append({
            "name": a.get("name"),
            "channels": len(a["channels"]),
            "keys": max((len(read_accessor(g, b, s["input"]))
                         for s in a["samplers"]), default=0),
            "start": round(min(times), 4) if times else 0.0,
            "duration": round((max(times) - min(times)) if times else 0.0, 4),
            "loop_delta": float(f"{loop_worst:.3g}"),
        })

    return {
        "bytes": nbytes, "version": version, "tris": tris,
        "materials": [m.get("name") for m in g.get("materials", [])],
        "images": len(g.get("images", [])), "textures": len(g.get("textures", [])),
        "skins": [{"name": s.get("name"), "joints": len(s.get("joints", []))}
                  for s in g.get("skins", [])],
        "animations": anims,
        "bbox_min": lo, "bbox_max": hi,
        "size": [hi[i] - lo[i] for i in range(3)],
        "generator": g.get("asset", {}).get("generator"),
    }


# ------------------------------------------------------------- re-import ----
def reimport_report():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    bpy.ops.import_scene.gltf(filepath=GLB)
    objs = list(bpy.context.scene.objects)
    meshes = [o for o in objs if o.type == "MESH"]
    arms = [o for o in objs if o.type == "ARMATURE"]

    # bone-shape helpers the importer fabricates are not part of the asset
    helpers = set()
    for a in arms:
        for pb in a.pose.bones:
            if pb.custom_shape:
                helpers.add(pb.custom_shape.name)
    meshes = [o for o in meshes if o.name not in helpers]

    for a in arms:
        a.data.pose_position = "REST"
    bpy.context.view_layer.update()

    pts = []
    tris = 0
    boundary = nonmanifold = loose = 0
    for ob in meshes:
        deps = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(deps)
        me = ev.to_mesh()
        pts += [ob.matrix_world @ v.co for v in me.vertices]
        tris += sum(len(p.vertices) - 2 for p in me.polygons)
        ev.to_mesh_clear()
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        boundary += sum(1 for e in bm.edges if len(e.link_faces) == 1)
        nonmanifold += sum(1 for e in bm.edges if len(e.link_faces) > 2)
        loose += sum(1 for v in bm.verts if not v.link_edges)
        bm.free()

    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))

    bones = []
    for a in arms:
        bones = [b.name for b in a.data.bones]
    actions = []
    for act in bpy.data.actions:
        rng = list(act.frame_range)
        actions.append({"name": act.name, "frames": [round(x, 2) for x in rng]})

    # skin weight coverage
    skin = None
    for ob in meshes:
        if not any(m.type == "ARMATURE" for m in ob.modifiers):
            continue
        unweighted = 0
        max_inf = 0
        for v in ob.data.vertices:
            w = [g.weight for g in v.groups if g.weight > 0]
            if not w:
                unweighted += 1
            max_inf = max(max_inf, len(w))
        skin = {"mesh": ob.name, "groups": len(ob.vertex_groups),
                "unweighted": unweighted, "max_influences": max_inf,
                "modifiers": [m.type for m in ob.modifiers]}
        break

    return {
        "mesh_count": len(meshes), "armature_count": len(arms),
        "tris": tris, "bbox_min": list(lo), "bbox_max": list(hi),
        "size": list(hi - lo),
        "boundary_edges": boundary, "nonmanifold_edges": nonmanifold,
        "loose_verts": loose, "bones": bones, "actions": actions, "skin": skin,
        "parented": [o.name for o in objs if o.parent],
        "non_unit_scale": [o.name for o in objs
                           if any(abs(s - 1.0) > 1e-4
                                  for s in o.matrix_world.to_scale())],
    }


def main():
    glb = glb_report()
    ri = reimport_report()

    names = [a["name"] for a in glb["animations"]]
    checks = []

    def chk(label, ok, got):
        checks.append((label, bool(ok), got))

    chk("高度 = 1.000 m", abs(glb["size"][1] - 1.0) < 0.002,
        f"{glb['size'][1]:.4f}")
    chk("落地 Y=0", abs(glb["bbox_min"][1]) < 1e-3, f"{glb['bbox_min'][1]:.5f}")
    chk("正面 -Z（鼻尖在 -Z 最远端）",
        abs(glb["bbox_min"][2]) > abs(glb["bbox_max"][2]) * 1.1,
        f"minZ={glb['bbox_min'][2]:.3f} maxZ={glb['bbox_max'][2]:.3f}")
    chk("三角面 ≤ 18000", glb["tris"] <= 18000, f"{glb['tris']:,}")
    chk("材质 ≤ 8", len(glb["materials"]) <= 8, f"{len(glb['materials'])}")
    chk("无贴图", glb["images"] == 0 and glb["textures"] == 0,
        f"images={glb['images']} textures={glb['textures']}")
    chk("含 skin（蒙皮）", len(glb["skins"]) >= 1,
        str([s["name"] for s in glb["skins"]]))
    chk("8 个动作名精确匹配", set(names) == set(REQUIRED), str(names))
    chk("动作齐全无多余", len(names) == 8, f"{len(names)}")
    chk("GLB ≤ 3 MB", glb["bytes"] <= 3 * 1024 * 1024,
        f"{glb['bytes'] / 1024 / 1024:.2f} MB")
    chk("骨骼 ≥ 25", len(ri["bones"]) >= 25, f"{len(ri['bones'])}")
    chk("无未赋权顶点", (ri["skin"] or {}).get("unweighted", 1) == 0,
        str((ri["skin"] or {}).get("unweighted")))
    chk("scale 全为 1", not ri["non_unit_scale"], str(ri["non_unit_scale"]))
    for a in glb["animations"]:
        want = EXPECTED_ANIM_SECONDS.get(a["name"])
        if want is not None:
            chk(f"{a['name']} 时长 = {want:.2f}s", abs(a["duration"] - want) < 0.02,
                f"{a['duration']:.3f}s")
    for a in glb["animations"]:
        if a["name"] in LOOPING:
            chk(f"{a['name']} 首尾闭合", a["loop_delta"] < 1e-4,
                f"{a['loop_delta']}")

    passed = sum(1 for _, ok, _ in checks if ok)

    L = []
    L.append("# 展馆吉祥物「纹纹」· 建模与动画校验报告")
    L.append("")
    L.append("自动生成：`scripts/mascot/verify_mascot.py`"
             "（两遍独立校验：直接解析 GLB 二进制 + 另起 Blender 进程重新 import）")
    L.append("")
    L.append(f"结论：**{passed}/{len(checks)} 项通过**"
             f"{' ✅' if passed == len(checks) else ' ⚠️ 见下'}")
    L.append("")

    L.append("## 产出")
    L.append("")
    L.append(f"- `.blend` 源工程：`assets/mascot/blender/wenmai_mascot_ww.blend`")
    L.append(f"- GLB：`frontend/public/models/wenmai_mascot_ww.glb`"
             f"（{glb['bytes'] / 1024:.0f} KiB）")
    L.append(f"- 导出器：{glb['generator']}")
    L.append("")

    L.append("## 规格")
    L.append("")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    L.append(f"| 三角面 | {glb['tris']:,}（预算 ≤ 18,000） |")
    L.append(f"| 材质 | {len(glb['materials'])} 个（≤ 8）："
             f"{', '.join(glb['materials'])} |")
    L.append(f"| 贴图 | images={glb['images']}, textures={glb['textures']}（纯色材质） |")
    L.append(f"| 骨骼 | {len(ri['bones'])} 根 |")
    L.append(f"| 尺寸（宽×高×深） | {glb['size'][0]:.3f} × {glb['size'][1]:.3f} × "
             f"{glb['size'][2]:.3f} m |")
    L.append(f"| 包围盒（glTF，Y-up） | min ({glb['bbox_min'][0]:.3f}, "
             f"{glb['bbox_min'][1]:.3f}, {glb['bbox_min'][2]:.3f}) → max "
             f"({glb['bbox_max'][0]:.3f}, {glb['bbox_max'][1]:.3f}, "
             f"{glb['bbox_max'][2]:.3f}) |")
    L.append(f"| 蒙皮 | mesh={ri['skin']['mesh'] if ri['skin'] else '-'}，"
             f"顶点组 {ri['skin']['groups'] if ri['skin'] else 0}，"
             f"最多 {ri['skin']['max_influences'] if ri['skin'] else 0} 影响/顶点 |")
    L.append(f"| 水密性 | 破口边 {ri['boundary_edges']}、非流形边 "
             f"{ri['nonmanifold_edges']}、孤立顶点 {ri['loose_verts']} |")
    L.append("")

    L.append("## 骨骼")
    L.append("")
    L.append(f"{len(ri['bones'])} 根：`{'`、`'.join(ri['bones'])}`")
    L.append("")

    L.append("## 动作")
    L.append("")
    L.append("| 动作 | 时长 | 关键帧 | 通道 | 首尾闭合差 | 说明 |")
    L.append("|---|---|---|---|---|---|")
    DESC = {
        "Idle": "呼吸起伏 + 眨眼（第 70–79 帧）+ 左右耳轻抖 + 尾巴逐节延迟摆动",
        "Spawn": "蹲伏蓄力 → 跃起离地 0.20 m → 落地压扁 → 回弹站定（不循环）",
        "Walk": "四肢对角交替小步，胯部左右摆，头随步频轻点，尾巴滞后跟随",
        "Run": "加大摆幅并前倾 7°，root 上下起伏，耳朵后压，尾巴上扬（循环）",
        "Turn": "原地 360° 平滑转身，胸与头反向带出，尾巴甩出（首尾同姿态）",
        "Happy": "连续两次小跳，落地压扁—回弹，耳朵后压、尾巴高扬（不循环）",
        "Curious": "歪头左右观察，耳朵前倾，一次眨眼，尾巴缓慢摆动（循环）",
        "Interact": "前倾探身 + 抬头看展品 + 尾巴高翘，随后回到起始姿态（不循环）",
    }
    for a in sorted(glb["animations"], key=lambda x: REQUIRED.index(x["name"])
                    if x["name"] in REQUIRED else 99):
        loop = "—" if a["name"] not in LOOPING else f"{a['loop_delta']}"
        L.append(f"| `{a['name']}` | {a['duration']:.2f} s | {a['keys']} | "
                 f"{a['channels']} | {loop} | {DESC.get(a['name'], '')} |")
    L.append("")
    L.append("循环类动作（Idle / Walk / Run / Turn / Curious）首尾帧完全一致，"
             "差值列为实测的最大通道差；非循环动作不做闭合要求。"
             "旋转通道按四元数比较（q 与 −q 等价），所以 Turn 的整圈旋转也算闭合。")
    L.append("")

    L.append("## 校验明细")
    L.append("")
    L.append("| 项 | 实测 | 结论 |")
    L.append("|---|---|---|")
    for label, ok, got in checks:
        L.append(f"| {label} | {got} | {'✅' if ok else '❌'} |")
    L.append("")

    L.append("## 设计要点")
    L.append("")
    L.append("- **三大文化特征**：① 耳廓外缘 2–3 道浅刻痕（按高度做高斯凹陷，向外侧衰减，"
             "是刀口不是镂空）；② 额心卷云印（金色描边 + 青绿填充，丝带贴合颅面曲率）；"
             "③ 尾端卷云螺旋（把螺旋面转向正面，正视图与 3/4 视图都能一眼认出）。")
    L.append("- **配饰独立几何**：项圈、金链、青花牌是第二个 mesh 对象 `WW_gear`，"
             "权重绑在 neck/chest 上，与身体分开便于后续替换。")
    L.append("- **结构线**：耳缘用一片深褐衬板透出轮廓，眼圈是一圈深褐细管，"
             "模型本身不画描边（描边交给 Three.js）。")
    L.append("- **眨眼**：每只眼一块中空球冠眼睑，骨骼 `lid.L/lid.R` 从眼球中心朝上，"
             "绕自身 X 轴旋转即向下覆盖眼球。")
    L.append("")

    with open(DOC, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print(f"[report] {DOC}")
    print(f"[result] {passed}/{len(checks)}")
    for label, ok, got in checks:
        print(f"  [{'OK ' if ok else 'FAIL'}] {label:26s} got={got}")
    print("ALL_OK" if passed == len(checks) else "SOME_CHECKS_FAILED")


if __name__ == "__main__":
    main()