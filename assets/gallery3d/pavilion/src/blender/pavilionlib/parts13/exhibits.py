"""v13 展陈构件：30 组挂画框 + 5 面门匾 + 案台/地面吸附锚点（FRAME_* / SNAP_*）。

分工：本文件只建"展陈骨架"，不含家具本体——
  · 画框/门匾 = 几何（挂在各馆墙内表面）；
  · FRAME_*  = 挂画锚点（Empty，局部 -Y 朝室内）；
  · SNAP_*   = 吸附锚点（Empty，道具底面落在锚点上，局部 +Z 朝上）。

坐标口径：全部从 dim13.DIM13 与 parts13/halls.py 的 INTERIOR / DESKS 读，
不写死总尺寸；halls.py 尚未导出这两个表时退回 dim13 推算值。
"""
from __future__ import annotations

import os

import bpy
from mathutils import Matrix, Vector

import bmesh

from .. import mesh_util as mu
from ..dim13 import DIM13 as D

try:                                    # halls.py 的室内净空契约
    from .halls import INTERIOR, DESKS
except Exception:                       # 还没写好时用 dim13 推算
    INTERIOR, DESKS = {}, []

try:                                    # crafts.py 的五馆主案（真实顶面高度）
    from .crafts import HERO_DESKS as _HERO_DESKS
except Exception:
    _HERO_DESKS = []

# ---------------------------------------------------------------- 画框几何
BAR_W = 0.09
BAR_OUT = 0.030
WALL_GAP = 0.002
LIP = 0.020
LIP_D0, LIP_D1 = 0.004, 0.018
CANVAS_D0, CANVAS_D1 = 0.008, 0.012
ANCHOR_FLOAT = 0.003

CLASSES = D.FRAME_CLASSES          # A(1.20,1.60,1.70) B(1.50,0.90,1.55) C(0.90,0.90,1.55)
SLOT_ORDER = {"A": 1, "B": 3, "C": 5}

HALL_CN = {"bianxiu": "针经阁", "songhua": "澄怀轩", "qinghua": "素肌堂",
           "zhuxianzhen": "刊木堂", "jianzhi": "镂金坊"}

PLAQUE_TEXT = {"bianxiu": "针经阁", "songhua": "澄怀轩", "qinghua": "素肌堂",
               "zhuxianzhen": "刊木堂", "jianzhi": "镂金坊"}

DOOR_H = {"bianxiu": D.SIDE_DOOR_H, "songhua": D.SIDE_DOOR_H,
          "qinghua": D.SIDE_DOOR_H, "zhuxianzhen": D.SIDE_DOOR_H,
          "jianzhi": D.JP_DOOR_H}


# ---------------------------------------------------------------- 室内净空
def _fallback_interior():
    """halls.py 未导出 INTERIOR 时，按 dim13 的配殿/水榭尺寸推算墙内表面。"""
    out = {}
    t = D.SIDE_WALL_T
    for (key, cy, door) in (("bianxiu", D.SIDE_CY_F, "-X"),
                            ("qinghua", D.SIDE_CY_B, "-X"),
                            ("songhua", D.SIDE_CY_F, "+X"),
                            ("zhuxianzhen", D.SIDE_CY_B, "+X")):
        cx = D.SIDE_CX if door == "-X" else -D.SIDE_CX
        out[key] = dict(x0=cx - (D.SIDE_HX - t), x1=cx + (D.SIDE_HX - t),
                        y0=cy - (D.SIDE_HY - t), y1=cy + (D.SIDE_HY - t),
                        floor=0.00, door_axis=door)
    out["jianzhi"] = dict(x0=D.JP_CX - (D.JP_HX - D.SIDE_WALL_T),
                          x1=D.JP_CX + (D.JP_HX - D.SIDE_WALL_T),
                          y0=D.JP_CY - (D.JP_HY - D.SIDE_WALL_T),
                          y1=D.JP_CY + (D.JP_HY - D.SIDE_WALL_T),
                          floor=D.JP_FLOOR, door_axis="+Y")
    return out


_INTERIOR = dict(_fallback_interior())
_INTERIOR.update({k: v for k, v in INTERIOR.items() if k in HALL_CN})


def _sides(it):
    """返回 (front, back, s0, s1)，每项 = (axis, plane, s, tang_axis)：
    axis 是墙面法向所在的轴；s = 由墙面指向室内的 ±1；tang_axis 是墙面内的横向轴。"""
    da = it.get("door_axis", "-X")
    if "X" in da:
        sx = 1 if "+X" in da else -1
        front = ("x", it["x0"] if sx < 0 else it["x1"], -sx, "y")
        back = ("x", it["x1"] if sx < 0 else it["x0"], sx, "y")
        return (front, back,
                ("y", it["y0"], 1.0, "x"), ("y", it["y1"], -1.0, "x"))
    sy = 1 if "+Y" in da else -1
    front = ("y", it["y0"] if sy < 0 else it["y1"], -sy, "x")
    back = ("y", it["y1"] if sy < 0 else it["y0"], sy, "x")
    return (front, back,
            ("x", it["x0"], 1.0, "y"), ("x", it["x1"], -1.0, "y"))


def _tang_range(it, axis):
    """axis='x' 表示法向沿 X，则横向是 Y；反之横向是 X。"""
    if axis == "x":
        return it["y0"], it["y1"]
    return it["x0"], it["x1"]


def _layout():
    """每馆 6 框：背墙 A/C/A，两山墙各 1 个 B，门侧墙返 1 个 B。"""
    out = []
    counts = {}
    for style in ("bianxiu", "songhua", "qinghua", "zhuxianzhen", "jianzhi"):
        it = _INTERIOR[style]
        (front, back, s0, s1) = _sides(it)
        fz = it["floor"]

        # 背墙三框：A / C / A
        bax, bplane, bs, _ = back
        b0, b1 = _tang_range(it, bax)
        bc = 0.5 * (b0 + b1)
        for (cls, off) in (("A", -1.60), ("C", 0.0), ("A", 1.60)):
            w, h, zc = CLASSES[cls]
            k = (style, cls)
            i = counts.get(k, 0)
            counts[k] = i + 1
            out.append((style, cls, f"{SLOT_ORDER[cls] + i:02d}",
                        bax, bplane, bc + off, fz + zc, w, h, bs))

        # 两山墙各 1 个 B（横向居中）
        for (sax, splane, ss, _) in (s0, s1):
            a0, a1 = _tang_range(it, sax)
            ac = 0.5 * (a0 + a1)
            w, h, zc = CLASSES["B"]
            k = (style, "B")
            i = counts.get(k, 0)
            counts[k] = i + 1
            out.append((style, "B", f"{SLOT_ORDER['B'] + i:02d}",
                        sax, splane, ac, fz + zc, w, h, ss))

        # 门侧墙返：避开门洞，贴在外侧余量里
        fax, fplane, fs, _ = front
        a0, a1 = _tang_range(it, fax)
        ac = 0.5 * (a0 + a1)
        half_door = 0.5 * (D.SIDE_DOOR_W if style != "jianzhi" else D.JP_DOOR_W)
        w, h, zc = CLASSES["B"]
        k = (style, "B")
        i = counts.get(k, 0)
        counts[k] = i + 1
        off = half_door + 0.35 + 0.5 * w
        limit = 0.5 * (a1 - a0) - 0.5 * w - 0.10
        off = min(off, max(limit, half_door + 0.35 + 0.5 * w))
        out.append((style, "B", f"{SLOT_ORDER['B'] + i:02d}",
                    fax, fplane, ac + off, fz + zc, w, h, fs))
    return out


LAYOUT = _layout()


# ---------------------------------------------------------------- 门匾
def _plaques():
    out = []
    for style in ("bianxiu", "songhua", "qinghua", "zhuxianzhen", "jianzhi"):
        it = _INTERIOR[style]
        front = _sides(it)[0]
        fax, fplane, fs, _ = front
        a0, a1 = _tang_range(it, fax)
        ac = 0.5 * (a0 + a1)
        pz = it["floor"] + DOOR_H[style] + 0.52
        w = 2.10 if style != "jianzhi" else 2.30
        # Approach-side sign, on the exterior face of the entrance lintel.
        column_radius = 0.24 if style == "jianzhi" else 0.28
        outside = fplane - fs * (column_radius + D.SIDE_WALL_T / 2)
        out.append((style, PLAQUE_TEXT[style], fax, outside, ac, pz, -fs,
                    w, 0.74))
    return out


PLAQUES = _plaques()


# ---------------------------------------------------------------- 吸附锚点
def _snaps():
    out = []
    for style in ("bianxiu", "songhua", "qinghua", "zhuxianzhen", "jianzhi"):
        it = _INTERIOR[style]
        fz = it["floor"]
        cx = 0.5 * (it["x0"] + it["x1"])
        cy = 0.5 * (it["y0"] + it["y1"])
        hw = 0.5 * (it["x1"] - it["x0"])
        hh = 0.5 * (it["y1"] - it["y0"])
        # 案台：优先用 crafts.py 的 Hero 工位（每馆主案，顶面 top_z 各不相同），
        # 其次退回 halls.py 的 DESKS（顶面 z=D.DESK_H）。
        hero = [d for d in _HERO_DESKS if d.get("hall") == style]
        dk = [d for d in DESKS if d.get("hall") == style]
        if hero:
            for i, d in enumerate(hero, start=1):
                out.append(dict(name=f"SNAP_{style}_desk_{i:02d}",
                                cn=f"{HALL_CN[style]}·{d.get('cn', '案台')}",
                                hall=style, kind="desk", limit=style,
                                loc=(float(d["x"]), float(d["y"]),
                                     float(d["top_z"]) + 0.002)))
        elif dk:
            for i, d in enumerate(dk, start=1):
                out.append(dict(name=f"SNAP_{style}_desk_{i:02d}",
                                cn=f"{HALL_CN[style]}·{d.get('cn', '案台')}",
                                hall=style, kind="desk", limit=style,
                                loc=(float(d["x"]), float(d["y"]),
                                     fz + D.DESK_H)))
        else:
            for i, (ox, oy) in enumerate(((-0.34, 0.0), (0.34, 0.0)), start=1):
                out.append(dict(name=f"SNAP_{style}_desk_{i:02d}",
                                cn=f"{HALL_CN[style]}·案台 {i:02d}",
                                hall=style, kind="desk", limit=style,
                                loc=(cx + ox * hw, cy + oy * hh,
                                     fz + D.DESK_H)))
        # 地面：3 处，避开案台与门口
        for i, (fx, fy) in enumerate(((-0.45, -0.40), (0.45, -0.40), (0.0, 0.45)),
                                     start=1):
            out.append(dict(name=f"SNAP_{style}_floor_{i:02d}",
                            cn=f"{HALL_CN[style]}·室内地面 {i:02d}",
                            hall=style, kind="floor", limit=style,
                            loc=(cx + fx * hw, cy + fy * hh, fz + 0.002)))
    # 庭院台面：4 处（台基 z=0，避开御道与水池）
    for i, (gx, gy) in enumerate(((16.0, -8.0), (-16.0, -8.0),
                                  (16.0, 24.0), (-16.0, 24.0)), start=1):
        out.append(dict(name=f"SNAP_garden_floor_{i:02d}",
                        cn=f"庭院·台面 {i:02d}", hall="garden",
                        kind="floor", limit="garden", loc=(gx, gy, 0.002)))
    return out


SNAPS = _snaps()


# ---------------------------------------------------------------- 几何工具
def _plane_box(axis, plane, tang, zb, u0, u1, v0, v1, d0, d1, s):
    if axis == "x":
        x0, x1 = plane + s * d0, plane + s * d1
        return (min(x0, x1), max(x0, x1), tang + u0, tang + u1,
                zb + v0, zb + v1)
    y0, y1 = plane + s * d0, plane + s * d1
    return (tang + u0, tang + u1, min(y0, y1), max(y0, y1),
            zb + v0, zb + v1)


def _boxes_for_frame(axis, plane, tang, zb, w, h, s):
    hw, hh = w * 0.5, h * 0.5

    def conv(u0, u1, v0, v1, d0, d1):
        return _plane_box(axis, plane, tang, zb, u0, u1, v0, v1, d0, d1, s)

    d_back, d_face = WALL_GAP, BAR_OUT
    bars = [
        conv(-hw, hw, -hh, -hh + BAR_W, d_back, d_face),
        conv(-hw, hw, hh - BAR_W, hh, d_back, d_face),
        conv(-hw, -hw + BAR_W, -hh + BAR_W, hh - BAR_W, d_back, d_face),
        conv(hw - BAR_W, hw, -hh + BAR_W, hh - BAR_W, d_back, d_face),
    ]
    lips = [
        conv(-hw + BAR_W, hw - BAR_W, -hh + BAR_W, -hh + BAR_W + LIP,
             LIP_D0, LIP_D1),
        conv(-hw + BAR_W, hw - BAR_W, hh - BAR_W - LIP, hh - BAR_W,
             LIP_D0, LIP_D1),
        conv(-hw + BAR_W, -hw + BAR_W + LIP, -hh + BAR_W + LIP, hh - BAR_W - LIP,
             LIP_D0, LIP_D1),
        conv(hw - BAR_W - LIP, hw - BAR_W, -hh + BAR_W + LIP, hh - BAR_W - LIP,
             LIP_D0, LIP_D1),
    ]
    inset = BAR_W + LIP + 0.0002
    canvas = conv(-hw + inset, hw - inset, -hh + inset, hh - inset,
                  CANVAS_D0, CANVAS_D1)
    return bars, lips, canvas


def _append_bm(dst, src):
    vmap = {}
    for v in src.verts:
        vmap[v] = dst.verts.new(v.co)
    dst.verts.index_update()
    for f in src.faces:
        try:
            nf = dst.faces.new([vmap[v] for v in f.verts])
            nf.material_index = f.material_index
            nf.smooth = f.smooth
        except ValueError:
            pass
    dst.faces.index_update()


def _text_bm(dst, text, size, center, right, up, normal, extrude=0.010):
    cu = bpy.data.curves.new("tmp_txt", "FONT")
    cu.body = text
    cu.size = size
    cu.extrude = extrude
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.resolution_u = 2
    try:
        fp = None
        for cand in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf",
                     r"C:\Windows\Fonts\simsun.ttc"):
            if os.path.exists(cand):
                fp = cand
                break
        if fp:
            cu.font = bpy.data.fonts.load(fp, check_existing=True)
    except Exception:
        pass
    ob = bpy.data.objects.new("tmp_txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    M = Matrix((
        (right[0], up[0], normal[0], center[0]),
        (right[1], up[1], normal[1], center[1]),
        (right[2], up[2], normal[2], center[2]),
        (0.0, 0.0, 0.0, 1.0),
    ))
    ob.matrix_world = M
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    tmp = bmesh.new()
    tmp.from_mesh(me)
    bmesh.ops.transform(tmp, verts=tmp.verts, matrix=M)
    _append_bm(dst, tmp)
    tmp.free()
    bpy.data.meshes.remove(me)
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.curves.remove(cu)


# ---------------------------------------------------------------- 构建
def _frames(C, coll):
    bm_f = bmesh.new()
    bm_c = bmesh.new()
    for (style, cls, slot, axis, plane, tang, zb, w, h, s) in LAYOUT:
        bars, lips, canvas = _boxes_for_frame(axis, plane, tang, zb, w, h, s)
        for b in bars + lips:
            mu.box_mm(bm_f, b[0], b[1], b[2], b[3], b[4], b[5])
        mu.box_mm(bm_c, canvas[0], canvas[1], canvas[2], canvas[3],
                  canvas[4], canvas[5])
    C.bm_obj(bm_f, "ex13_frame_wood", "detail", coll,
             cn="挂画框（金丝楠细边 + 内凹子口）", mat="wood_dark",
             smooth=30.0, uv=0.8, flat=True)
    C.bm_obj(bm_c, "ex13_frame_canvas", "screen", coll,
             cn="画心（旧宣纸绢本 · 待展）", mat="xuan", smooth=0.0,
             uv=0.8, flat=True)


def _plaques(C, coll):
    bm_b = bmesh.new()
    bm_r = bmesh.new()
    bm_t = bmesh.new()
    for (style, text, axis, plane, tang, pz, s, w, h) in PLAQUES:
        hw, hh = w * 0.5, h * 0.5
        mu.box_mm(bm_b, *_plane_box(axis, plane, tang, pz, -hw, hw, -hh, hh,
                                    WALL_GAP, 0.055, s))
        rw, rd0, rd1 = 0.10, 0.0552, 0.095
        for rib in ((-hw, hw, -hh, -hh + rw), (-hw, hw, hh - rw, hh),
                    (-hw, -hw + rw, -hh + rw, hh - rw), (hw - rw, hw, -hh + rw, hh - rw)):
            mu.box_mm(bm_r, *_plane_box(axis, plane, tang, pz,
                                        rib[0], rib[1], rib[2], rib[3],
                                        rd0, rd1, s))
        nx, ny = (s, 0.0) if axis == "x" else (0.0, s)
        n = Vector((nx, ny, 0.0)).normalized()
        up = Vector((0.0, 0.0, 1.0))
        right = up.cross(n).normalized()
        center = (Vector((plane, tang, pz)) if axis == "x"
                  else Vector((tang, plane, pz))) + n * 0.0642
        _text_bm(bm_t, text, h * 0.46, center, right, up, n, extrude=0.009)
    C.bm_obj(bm_b, "ex13_plaque_board", "detail", coll,
             cn="门匾（黑漆底）", mat="lacquer", smooth=0.0, uv=0.6, flat=True)
    C.bm_obj(bm_r, "ex13_plaque_rim", "detail", coll, cn="门匾铜框",
             mat="bronze", smooth=25.0, uv=0.6)
    C.bm_obj(bm_t, "ex13_plaque_text", "detail", coll, cn="门匾铜字",
             mat="bronze", smooth=35.0, uv=0.6)


def build(C):
    coll = C.coll("展陈", "画框与门匾")
    _frames(C, coll)
    _plaques(C, coll)
    print(f"[exhibits] 画框 {len(LAYOUT)} 组 / 门匾 {len(PLAQUES)} 面 / "
          f"吸附锚点 {len(SNAPS)} 个")


# ---------------------------------------------------------------- 锚点
def frame_specs():
    out = []
    for (style, cls, slot, axis, plane, tang, zb, w, h, s) in LAYOUT:
        nx, ny = (s, 0.0) if axis == "x" else (0.0, s)
        n = Vector((nx, ny, 0.0)).normalized()
        pos = (Vector((plane, tang, zb)) if axis == "x"
               else Vector((tang, plane, zb))) + n * (CANVAS_D1 + ANCHOR_FLOAT)
        out.append({
            "name": f"FRAME_{style}_{slot}",
            "cn": f"{HALL_CN[style]}·{cls} 类画框 {slot}",
            "style": style, "slot": slot, "cls": cls,
            "aspect": round(h / w, 4), "size": [w, h],
            "frame_size": [round(w + 2 * BAR_W, 3), round(h + 2 * BAR_W, 3)],
            "loc": tuple(pos), "normal": (n.x, n.y, 0.0),
        })
    return out


def add_anchors(sc):
    nf = 0
    for s in frame_specs():
        ob = bpy.data.objects.new(s["name"], None)
        ob.empty_display_type = "PLAIN_AXES"
        ob.empty_display_size = 0.12
        ob.location = s["loc"]
        d = Vector(s["normal"])
        if d.length < 1e-6:
            d = Vector((0.0, -1.0, 0.0))
        ob.rotation_euler = d.to_track_quat("-Y", "Z").to_euler()
        ob["cn"] = s["cn"]
        ob["style"] = s["style"]
        ob["slot"] = s["slot"]
        ob["cls"] = s["cls"]
        ob["aspect"] = float(s["aspect"])
        ob["size"] = list(s["size"])
        ob["frame_size"] = list(s["frame_size"])
        ob["mount"] = "wall"
        ob["facing"] = "-Y"
        ob["zfight"] = ANCHOR_FLOAT
        sc.collection.objects.link(ob)
        nf += 1

    ns = 0
    for s in SNAPS:
        ob = bpy.data.objects.new(s["name"], None)
        ob.empty_display_type = "PLAIN_AXES"
        ob.empty_display_size = 0.10
        ob.location = s["loc"]
        ob.rotation_euler = Vector((0.0, -1.0, 0.0)).to_track_quat(
            "-Y", "Z").to_euler()
        ob["cn"] = s["cn"]
        ob["hall"] = s["hall"]
        ob["kind"] = s["kind"]
        ob["limit"] = s["limit"]
        sc.collection.objects.link(ob)
        ns += 1

    print(f"[exhibits] 锚点：FRAME {nf} 个 / SNAP {ns} 个")
    return nf + ns
