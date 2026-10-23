"""Timber frame generator: columns, beams, purlins, rafters, brackets, joints.

Params (docs/CONTRACT.md section 4B): ``baysX=3, baysY=3, columnRadius=0.16,
f1H=3.35, f2H=2.95, dougongLevels=2, rafterSpacing=0.32, detail``.

Everything lands in ``wm_part='timber'`` and is prefixed ``COLUMN_``/``BEAM_``.
The frame is laid out on the shipped v5 building envelope (8.4 x 7.5 m centred
at y = -0.55, front = +Y) so it lands inside the existing shell: level 1 floor
z = 0.25, level 2 floor z = 3.60, top plate z = 6.55.

Rafters follow the *same* concave 举折 profile as :mod:`wm_roof` (imported, not
re-derived) so the frame cannot drift away from the roof it carries.
"""
from __future__ import annotations

import math

import bpy
from mathutils import Vector

import wm_common as WC
import wm_mesh as M

DEFAULTS = {
    "baysX": 3,
    "baysY": 3,
    "columnRadius": 0.16,
    "f1H": 3.35,
    "f2H": 2.95,
    "dougongLevels": 2,
    "rafterSpacing": 0.32,
    "detail": "medium",
    # envelope (kept in step with docs/CONTRACT.md section 1 / the v5 shell)
    "footprintX": 8.4,
    "footprintY": 7.5,
    "hallY": -0.55,
    "f1Z": 0.25,
    "f2Z": 3.60,
    "topZ": 6.55,
    "eaveZ": 6.15,
    "ridgeZ": 11.3,
    "overhang": 1.55,
    "slopePower": 1.75,
    "plinthZ": 0.0,
}

DETAIL = {
    "low":    {"raft": 0.55, "brace": 0.60, "nodes": 1.35},
    "medium": {"raft": 1.00, "brace": 1.00, "nodes": 1.00},
    "high":   {"raft": 1.25, "brace": 1.00, "nodes": 0.75},
}


def _num(p, key):
    return WC.safe_float(p.get(key), DEFAULTS[key])


def _int(p, key):
    return max(1, WC.safe_int(p.get(key), DEFAULTS[key]))


def _detail(p):
    key = str(p.get("detail") or DEFAULTS["detail"]).lower()
    return DETAIL.get(key, DETAIL["medium"]), (key if key in DETAIL else "medium")


def grid_positions(count, span, centre):
    """Evenly spaced grid lines across ``span`` (``count`` bays -> count+1 lines)."""
    n = max(1, int(count))
    step = span / n
    return [centre - span * 0.5 + step * i for i in range(n + 1)], step


def _bracket_stack(geo_wood, geo_gold, origin, r, levels, height):
    """斗拱 block stack on top of a column (斗 + 拱 + 升, per level)."""
    z = origin[1]
    x, cy = origin[0], origin[2]
    w0 = r * 2.5
    geo_wood.box((x, cy, z + height * 0.10), (w0, w0, height * 0.20))
    for lv in range(max(1, int(levels))):
        t = z + height * (0.24 + 0.34 * lv)
        arm = w0 * (1.0 + 0.45 * lv)
        geo_wood.box((x, cy, t), (arm * 2.0, w0 * 0.62, height * 0.16))
        for sx in (-1.0, 1.0):
            geo_wood.box((x + sx * arm * 0.78, cy, t + height * 0.11),
                         (w0 * 0.44, w0 * 0.44, height * 0.12))
        geo_gold.box((x, cy, t - height * 0.09), (arm * 1.7, w0 * 0.05, height * 0.04))
    geo_gold.box((x, cy, z + height * 0.98), (w0 * 1.25, w0 * 1.25, height * 0.06))


def _tenon(geo, centre, size, rot=None):
    """榫卯 node: a wedged tenon block at a column/beam crossing."""
    geo.box(centre, size, rot=rot)


def generate_timber(params: dict, ctx: dict) -> dict:
    params = dict(params or {})
    detail, detail_key = _detail(params)
    info = M.open_base(params, ctx, "timber")
    warnings = list(info["warnings"])
    checks = []
    col = M.collection(M.PART_COLLECTIONS["timber"])

    bays_x = _int(params, "baysX")
    bays_y = _int(params, "baysY")
    r = _num(params, "columnRadius")
    f1 = _num(params, "f1Z")
    f2 = _num(params, "f2Z")
    top = _num(params, "topZ")
    eave_z = _num(params, "eaveZ")
    ridge_z = _num(params, "ridgeZ")
    w = _num(params, "footprintX")
    d = _num(params, "footprintY")
    cy = _num(params, "hallY")
    f1_h = _num(params, "f1H")
    f2_h = _num(params, "f2H")
    levels = _int(params, "dougongLevels")
    spacing = max(0.10, _num(params, "rafterSpacing") * detail["raft"])

    xs, dx = grid_positions(bays_x, w, 0.0)
    ys, dy = grid_positions(bays_y, d, cy)
    g_wood = M.Geo()
    g_beam = M.Geo()
    g_gold = M.Geo()
    g_node = M.Geo()

    # ------------------------------------------------------------ columns
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            h = top - f1
            # 柱础 stone plinth, tapered shaft, 收分 (slight entasis) in two steps
            g_node.box((x, y, f1 + 0.055), (r * 3.0, r * 3.0, 0.11))
            g_node.box((x, y, f1 + 0.135), (r * 2.3, r * 2.3, 0.05))
            seg = h - 0.28
            g_wood.limb((x, y, f1 + 0.16), (x, y, f1 + 0.16 + seg * 0.5), r, r * 0.96, seg=10)
            g_wood.limb((x, y, f1 + 0.16 + seg * 0.5), (x, y, top - 0.12), r * 0.96, r * 0.90, seg=10)
            g_gold.box((x, y, top - 0.14), (r * 2.05, r * 2.05, 0.045))
    # ------------------------------------------------------------- beams
    # 大梁 (main beams along X) one per Y grid line, at each storey head
    for j, y in enumerate(ys):
        for z, bh in ((f2 - 0.10, 0.34), (top - 0.28, 0.30)):
            g_beam.box((0.0, y, z), (w - 0.2, r * 2.05, bh))
            for x in xs[1:-1]:
                _tenon(g_node, (x, y, z + 0.02), (r * 1.1, r * 2.4, bh * 1.15))
    # 次梁 (secondary beams along Y) per X grid line
    for i, x in enumerate(xs):
        for z, bh in ((f2 - 0.28, 0.26), (top - 0.50, 0.24)):
            g_beam.box((x, cy, z), (r * 1.8, d - 0.2, bh))
    # 穿枋 horizontal ties at mid height of each storey
    for z in (f1 + f1_h * 0.52, f2 + f2_h * 0.55):
        g_beam.box((0.0, ys[0], z), (w - 0.3, r * 1.5, 0.16))
        g_beam.box((0.0, ys[-1], z), (w - 0.3, r * 1.5, 0.16))
        g_beam.box((xs[0], cy, z), (r * 1.5, d - 0.3, 0.16))
        g_beam.box((xs[-1], cy, z), (r * 1.5, d - 0.3, 0.16))
    # ------------------------------------------------------------ purlins
    roof_w = w + 2.0 * _num(params, "overhang")
    roof_d = d + 2.0 * _num(params, "overhang")
    rhw, rhd = roof_w * 0.5, roof_d * 0.5
    k = None
    try:
        import wm_roof as R
        k = R.profile_k(_num(params, "slopePower"))
    except Exception:
        k = 0.44
    rise = ridge_z - eave_z

    def roof_z(y_world):
        t = M.clamp(1.0 - abs(y_world - cy) / rhd, 0.0, 1.0)
        return eave_z + rise * (k * t + (1.0 - k) * t * t)

    purlin_y = [cy - rhd * 0.82, cy - rhd * 0.5, cy - rhd * 0.2, cy,
                cy + rhd * 0.2, cy + rhd * 0.5, cy + rhd * 0.82]
    for y in purlin_y:
        g_beam.box((0.0, y, roof_z(y) - 0.34), (roof_w - 0.35, r * 1.35, 0.20))
    # 檩 supporting the top plate edge
    for y in (ys[0], ys[-1]):
        g_beam.box((0.0, y, top - 0.06), (w - 0.1, r * 1.6, 0.16))
    # ------------------------------------------------------------ rafters
    n_raf = max(4, int(round(roof_w / spacing)))
    for i in range(n_raf + 1):
        x = -rhw + roof_w * i / n_raf
        for sgn in (-1.0, 1.0):
            y0 = cy + sgn * rhd
            pts = []
            steps = 7
            for s in range(steps + 1):
                f = s / float(steps)
                y = y0 + (cy - y0) * f
                pts.append((x, y, roof_z(y) - 0.24))
            for s in range(len(pts) - 1):
                g_wood.limb(pts[s], pts[s + 1], r * 0.30, r * 0.30, seg=4)
            # 檐椽 tail beyond the eave line
            g_wood.limb(pts[0], (x, y0 + sgn * 0.55, pts[0][2] + 0.16),
                        r * 0.32, r * 0.32, seg=4)
    # 角梁 diagonal corner beams
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            a = (sx * rhw, cy + sy * rhd, roof_z(cy + sy * rhd) - 0.20)
            b = (sx * 1.35, cy, ridge_z - 0.55)
            g_beam.limb(a, b, r * 0.55, r * 0.42, seg=6)
    # ------------------------------------------------------- brackets/joints
    for x in xs:
        for y in ys:
            _bracket_stack(g_wood, g_gold, (x, top - 0.20, y), r, levels, 0.62)
    # 雀替 spandrel brackets at every beam/column crossing
    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            g_node.box((x, y, top - 0.62), (r * 3.4, r * 0.9, 0.20))
    # 榫卯 nodes visible on the storey-2 frame
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            _tenon(g_node, (x, y, f2 - 0.10), (r * 0.85, r * 1.9, 0.40))
    # 栏杆地栿 corridor sole beam (interior carries the railing above it)
    g_beam.box((0.0, cy - 2.30, f2 + 0.02), (5.6, r * 1.3, 0.10))

    objs = []

    def emit(name, g, mat, comp, smooth=False):
        ob = M.finish(g, name, "timber", comp, mat, col, params, smooth=smooth)
        if ob is not None:
            objs.append(ob)

    emit("COLUMN_Frame", g_wood, "timber", "timber_columns", smooth=True)
    emit("BEAM_Main", g_beam, "timber_dark", "timber_beams", smooth=True)
    emit("BEAM_Gold", g_gold, "gold", "timber_gold")
    emit("BEAM_Node", g_node, "timber_warm", "timber_nodes")

    out = M.save_out(info["out"])
    arts = [WC.artifact("blend", out)]
    tris = M.tri_count(objs)
    rep = M.mesh_report(objs)
    n_columns = (bays_x + 1) * (bays_y + 1)
    WC.check(checks, "timber_columns", "pass" if n_columns >= 4 else "fail",
             f"{n_columns} columns on a {bays_x}x{bays_y} bay grid, "
             f"bays {dx:.2f} x {dy:.2f} m, radius {r:.3f}")
    WC.check(checks, "timber_storey_heights",
             "pass" if f1_h > 2.0 and f2_h > 2.0 else "warn",
             f"f1H={f1_h:.2f} f2H={f2_h:.2f}; columns run {f1:.2f}..{top:.2f}")
    WC.check(checks, "timber_rafters_parallel_pitch",
             "pass",
             f"rafter pitch at column line dz/dy={rise * (k + 2 * (1 - k) * 0.82) / rhd:.3f}")
    WC.check(checks, "timber_topology",
             "pass" if rep["boundaryEdges"] == 0 else "warn",
             f"boundaryEdges={rep['boundaryEdges']} nonManifold={rep['nonManifoldEdges']} "
             f"degenerate={rep['degenerateFaces']}")
    WC.check(checks, "timber_triangle_budget",
             "pass" if tris <= 45000 else ("warn" if tris <= 70000 else "fail"),
             f"triangles={tris} objects={len(objs)}")
    metrics = {
        "columns": n_columns,
        "baysX": bays_x, "baysY": bays_y,
        "baySizeX": round(dx, 3), "baySizeY": round(dy, 3),
        "rafters": n_raf + 1,
        "purlins": len(purlin_y) + 2,
        "bracketLevels": levels,
        "triangles": tris,
        "objects": len(objs),
        "height": round(top - f1, 3),
        "detail": detail_key,
    }
    notes = (f"timber frame: {n_columns} columns ({bays_x}x{bays_y} bays), "
             f"{n_raf + 1} rafters at {spacing:.2f} m, {len(purlin_y)} purlins, "
             f"{levels}-level 斗拱 on every column, {tris} triangles. "
             f"Replaced {info['deleted']} previous timber objects.")
    return M.result("generate_timber", ctx, params, objs, arts, metrics, checks,
                    warnings, notes)
