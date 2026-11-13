"""v13 零穿模审计：在合并（join_by_material）之前，对逐构件做真实三角面相交检测。

原理：每个对象用 world 坐标建 BVHTree，先以 AABB 预筛，再做
`bvh_a.overlap(bvh_b)`（mathutils 的 BVH overlap 是精确三角-三角相交测试），
命中即真实三角面相交，不是包围盒误报。

v15：所有命中均未审核。cross/coplanar 是缺陷候选，tenon/joint/embed 只是
按名称生成的复核提示，不再视为结构许可。零 cross/coplanar 不等于零缺陷。
本检查不覆盖同一对象内部相交、完整包容或有间距的近平行面，需另做几何与视觉QA。

用法：
  · 模块：from .overlap13 import audit; audit(C.objects, out_json=...)
  · 装配：加 --audit-overlap，自动写 <out>/v13_overlap.json
"""
from __future__ import annotations

import json
import os

from mathutils.bvhtree import BVHTree

# 展陈装饰（画框/门匾）按设计嵌入墙面 10mm，不参与判决
DECOR_PREFIX = ("ex13_frame", "ex13_plaque")
COPLANAR_N_DOT = 0.999
COPLANAR_DIST = 0.0025


def _part_of(name):
    """部件前缀：hall_xxx → hall，site13_xxx → site13。"""
    return name.split("_")[0]


# ---------------------------------------------------------------- 结构性相交
# 建筑不是「零件互不相碰」的机械件：梁头要插进柱身（榫卯），柱础/夹杆石要嵌进
# 铺装（嵌固）。这两类在三角面层面必然相交，但任何一侧的面都埋在对方体内，
# 从外面看不见，也不产生 Z-fighting —— 与「屋檐捅进墙体」是两回事。
# 这里按构件语义显式放行，并在报告里单独计数，绝不混进 cross 里充数。
FRAME_KW = ("beam", "band", "dou", "gong", "puzuo", "fang", "pai",
            "purlin", "rafter", "lintel", "arch")
COL_KW = ("col", "post", "pillar", "zhu")
EMBED_BASE = ("site13_paving", "site13_edge_band", "site13_daolong",
              "site13_plate", "site13_terrace", "gallery_slab")
EMBED_FOOT = ("gate_stone", "gate_plinth", "_taiming", "_step", "_found")
SLAB_KW = ("slab", "plinth", "taiming", "platform", "floor")
EMBED_ZMAX = 1.10          # 嵌固件只在台基高度内，超出就不是嵌固而是穿透


def _world_geom(ob):
    me = ob.data
    me.calc_loop_triangles()
    mw = ob.matrix_world
    rot = mw.to_3x3()
    normal_matrix = rot.inverted_safe().transposed()
    verts = [mw @ v.co for v in me.vertices]
    tris = [tuple(t.vertices) for t in me.loop_triangles]
    centers = [rot @ t.center + mw.translation for t in me.loop_triangles]
    normals = [(normal_matrix @ t.normal).normalized() for t in me.loop_triangles]
    return verts, tris, centers, normals


def _bbox(verts):
    xs = [v.x for v in verts]
    ys = [v.y for v in verts]
    zs = [v.z for v in verts]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def _hit(a, b, pad=0.0):
    return not (a[3] + pad < b[0] or b[3] + pad < a[0]
                or a[4] + pad < b[1] or b[4] + pad < a[1]
                or a[5] + pad < b[2] or b[5] + pad < a[2])


def _is_joint(a, b):
    """梁枋/斗拱 × 柱：榫卯做法，埋入对方体内，不算穿模。"""
    def has(n, kws):
        n = n.lower()
        return any(k in n for k in kws)
    return ((has(a, FRAME_KW) and has(b, COL_KW))
            or (has(b, FRAME_KW) and has(a, COL_KW)))


def _is_embed(ai, bj):
    """铺装 / 台明 × 落在其上的石作与柱脚：嵌固，切面埋在台基体内。"""
    a, b = ai["name"], bj["name"]
    base_a = any(a.startswith(k) for k in EMBED_BASE)
    base_b = any(b.startswith(k) for k in EMBED_BASE)
    foot_a = any(k in a for k in EMBED_FOOT)
    foot_b = any(k in b for k in EMBED_FOOT)
    if (base_a and foot_b) or (base_b and foot_a):
        return True
    # 柱脚沉进连廊/馆的台明板内（柱子必须生根，不是穿模）
    slab_a = any(k in a.lower() for k in SLAB_KW)
    slab_b = any(k in b.lower() for k in SLAB_KW)

    def is_col(n):
        n = n.lower()
        return any(k in n for k in COL_KW)
    return (slab_a and is_col(b)) or (slab_b and is_col(a))


def audit(objects, out_json=None, limit=30):
    items = []
    for ob in objects:
        if ob.type != "MESH" or len(ob.data.polygons) == 0:
            continue
        verts, tris, centers, normals = _world_geom(ob)
        if not tris:
            continue
        items.append({
            "name": ob.name, "part": _part_of(ob.name),
            "cat": ob.get("cat", ""), "cn": ob.get("cn", ""),
            "bb": _bbox(verts), "centers": centers, "normals": normals,
            "bvh": BVHTree.FromPolygons(verts, tris, all_triangles=True,
                                        epsilon=0.0),
        })

    cross, coplanar, tenon = [], [], []
    joint, embed = [], []
    n_bbox_pairs = 0
    for i in range(len(items)):
        ai = items[i]
        for j in range(i + 1, len(items)):
            bj = items[j]
            if not _hit(ai["bb"], bj["bb"]):
                continue
            n_bbox_pairs += 1
            hits = ai["bvh"].overlap(bj["bvh"])
            if not hits:
                continue
            nc = 0
            for (ia, ib) in hits:
                n1 = ai["normals"][ia]
                n2 = bj["normals"][ib]
                if abs(n1.dot(n2)) < COPLANAR_N_DOT:
                    continue
                d = (bj["centers"][ib] - ai["centers"][ia]).dot(n1)
                if abs(d) < COPLANAR_DIST:
                    nc += 1
            rec = {"a": ai["name"], "b": bj["name"],
                   "part_a": ai["part"], "part_b": bj["part"],
                   "cn_a": ai["cn"], "cn_b": bj["cn"],
                   "face_pairs": len(hits), "coplanar": nc}
            rec["status"] = "unreviewed"
            rec["bbox_intersection_extent"] = [round(min(ai["bb"][k+3], bj["bb"][k+3]) - max(ai["bb"][k], bj["bb"][k]), 6) for k in range(3)]
            rec["sample_triangle_pairs"] = [list(pair) for pair in hits[:8]]
            # Naming is a review hint, never proof that an intersection is safe.
            if _is_joint(ai["name"], bj["name"]):
                rec["review_hint"] = "beam_column_candidate"
            elif _is_embed(ai, bj):
                rec["review_hint"] = "foundation_candidate"
            else:
                rec["review_hint"] = "same_part_candidate" if ai["part"] == bj["part"] else "cross_part"
            # Do not hide coplanar pairs inside structural classifications.
            if nc:
                coplanar.append(rec)
            if ai["part"] != bj["part"]:
                if rec["review_hint"] == "beam_column_candidate":
                    joint.append(rec)
                elif rec["review_hint"] == "foundation_candidate":
                    embed.append(rec)
                else:
                    cross.append(rec)
            elif not nc:
                tenon.append(rec)

    for lst in (cross, coplanar, tenon, joint, embed):
        lst.sort(key=lambda p: -p["face_pairs"])
    cross.sort(key=lambda p: -p["coplanar"])

    print(f"[overlap] 构件 {len(items)} / 包围盒初筛 {n_bbox_pairs} 对")
    print(f"[overlap] 跨部件穿模 {len(cross)} 对 ｜ 同部件共面重叠 {len(coplanar)} 对 ｜ "
          f"同部件榫卯 {len(tenon)} 对 ｜ 梁柱榫卯 {len(joint)} 对 ｜ 石作嵌固 {len(embed)} 对")

    for title, lst in (("跨部件", cross), ("共面重叠", coplanar)):
        for p in lst[:limit]:
            print(f"[overlap] [{title}] {p['face_pairs']:5d} 面"
                  f"（共面 {p['coplanar']}）  {p['a']} × {p['b']}")
        if len(lst) > limit:
            print(f"[overlap] [{title}] ……另有 {len(lst) - limit} 对")

    unique_pairs = {(p["a"], p["b"]): p for group in (cross, coplanar, tenon, joint, embed) for p in group}
    result = {"schema": "v15-contact-review-1", "objects": len(items), "bbox_pairs": n_bbox_pairs,
              "cross": cross, "coplanar": coplanar, "tenon": tenon,
              "joint": joint, "embed": embed,
              "review_required": len(unique_pairs), "accepted_contacts": 0,
              "verified_zero_intersections": not unique_pairs,
              "limitations": ["Surface triangle overlap only; enclosed volumes may not intersect surfaces.",
                              "Intra-object disconnected components and near-but-separated coplanar surfaces need separate QA.",
                              "Name-based joint/embed/tenon labels are review hints, not acceptance."]}
    print(f"[overlap] 待人工/几何复核 {len(unique_pairs)} 对；分类计数不代表零缺陷")
    if out_json:
        os.makedirs(os.path.dirname(out_json), exist_ok=True)
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
        print(f"[overlap] 报告 {out_json}")
    return result