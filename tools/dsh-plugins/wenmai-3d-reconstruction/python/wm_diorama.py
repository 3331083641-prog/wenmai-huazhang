"""Plinth (须弥座) + street diorama generator.

Params (docs/CONTRACT.md section 4B): ``baseSize=16, plinthHeight=0.65,
frieze=true, medallion=true, paving=true, props:{trees,bamboo,planters,
lanterns,stoneLamps,banners}, detail``.

Geometry follows the contract's level contract: the walking deck top is z = 0,
the stone base occupies z in [-plinthHeight, 0] as a real 须弥座 (dark foot ->
roll -> recessed waist carrying the carved meander frieze -> body -> top
moulding), and the timber bracket grid below it reaches z = -0.95.

Names: ``BASE_*`` (plinth / paving / kerb / steps / grid), ``PROP_*``
(vegetation, planters, banners), ``LANTERN_*`` (hanging lanterns, stone lamps).
All objects are tagged ``wm_part='diorama'``.
"""
from __future__ import annotations

import math

import bpy
from mathutils import Vector

import wm_common as WC
import wm_mesh as M

DEFAULTS = {
    "baseSize": 16.0,
    "plinthHeight": 0.65,
    "deckZ": 0.0,
    "frieze": True,
    "medallion": True,
    "paving": True,
    "props": {
        "trees": 2, "bamboo": 2, "planters": 4, "lanterns": 2,
        "stoneLamps": 2, "banners": 2,
    },
    "detail": "medium",
    "hallX": 8.4,
    "hallY": 7.5,
    "hallCY": -0.55,
    "seed": 7,
}

DETAIL = {
    "low":    {"seg": 12, "paving": 0.9, "prop": 0.75, "leaf": 9},
    "medium": {"seg": 16, "paving": 1.0, "prop": 1.0, "leaf": 11},
    "high":   {"seg": 24, "paving": 1.0, "prop": 1.15, "leaf": 13},
}


def _num(p, key):
    return WC.safe_float(p.get(key), DEFAULTS[key])


def _props(p):
    raw = p.get("props") or {}
    out = dict(DEFAULTS["props"])
    for key, value in raw.items():
        if key in out:
            out[key] = max(0, WC.safe_int(value, out[key]))
    return out


def _detail(p):
    key = str(p.get("detail") or DEFAULTS["detail"]).lower()
    return DETAIL.get(key, DETAIL["medium"]), (key if key in DETAIL else "medium")


def _taper(geo, half_lo, half_hi, z0, z1):
    """Square frustum: one 须弥座 course whose top face differs in width."""
    h = z1 - z0
    verts = [(-half_lo, -half_lo, z0), (half_lo, -half_lo, z0),
             (half_lo, half_lo, z0), (-half_lo, half_lo, z0),
             (-half_hi, -half_hi, z1), (half_hi, -half_hi, z1),
             (half_hi, half_hi, z1), (-half_hi, half_hi, z1)]
    geo.add(verts, M.BOX_FACES)


def _meander(geo, length, height, depth, loc, axis="x", period=0.42, bar=0.056):
    """Continuous 回纹 key pattern: base rail + per-cell riser, return, drop."""
    n = max(2, int(round(length / period)))
    p = length / n
    half = height * 0.5

    def bar_box(u0, u1, v0, v1):
        du, dv = abs(u1 - u0), abs(v1 - v0)
        if du <= 1e-4 or dv <= 1e-4:
            return
        cu, cv = (u0 + u1) * 0.5, (v0 + v1) * 0.5
        if axis == "x":
            geo.box((loc[0] + cu, loc[1], loc[2] + cv), (du, depth, dv))
        else:
            geo.box((loc[0], loc[1] + cu, loc[2] + cv), (depth, du, dv))

    bar_box(-length * 0.5, length * 0.5, -half, -half + bar)
    for k in range(n):
        u0 = -length * 0.5 + k * p
        ue = u0 + p * 0.74
        ut = ue - p * 0.48
        bar_box(ue - bar * 0.5, ue + bar * 0.5, -half + bar, half)
        bar_box(ut, ue + bar * 0.5, half - bar, half)
        bar_box(ut - bar * 0.5, ut + bar * 0.5, -half * 0.14, half - bar)


def _medallion(geo, centre, radius, depth, axis="y", petals=8, seg=16):
    """Eight-petal lotus roundel (real petals, not a decal).

    ``axis='y'`` faces the ±Y street faces, ``axis='x'`` the ±X faces; the
    flattening scale is applied on the axis normal to the carved face.
    """
    cx, cy, cz = centre
    flat = (1.0, 0.42, 1.0) if axis == "y" else (0.42, 1.0, 1.0)
    core = (1.0, 0.45, 1.0) if axis == "y" else (0.45, 1.0, 1.0)
    for i in range(petals):
        a = 2.0 * math.pi * i / petals
        pr = radius * 0.60
        if axis == "y":
            pos = (cx + math.cos(a) * pr, cy, cz + math.sin(a) * pr)
        else:
            pos = (cx, cy + math.cos(a) * pr, cz + math.sin(a) * pr)
        geo.sphere(pos, radius * 0.30, seg=6, rings=4, scale=flat)
    geo.sphere((cx, cy, cz), radius * 0.40, seg=max(8, seg // 2), rings=5, scale=core)


def _tree(geo, x, y, z, s, seed, leaf_key=0):
    """Forked trunk + layered canopy pads (same construction as the v5 site)."""
    p0 = Vector((x, y, z))
    p1 = p0 + Vector((0.09 * s, -0.05 * s, 1.06 * s))
    p2 = p1 + Vector((0.15 * s, 0.08 * s, 0.56 * s))
    geo.limb(p0, p1, 0.148 * s, 0.104 * s, seg=8)
    geo.limb(p1, p2, 0.104 * s, 0.080 * s, seg=7)
    branches = ((0.60, 0.26, 0.62, 0.070, 0.036), (-0.64, -0.28, 0.74, 0.062, 0.031),
                (0.06, -0.70, 0.46, 0.048, 0.025), (-0.26, 0.54, 0.36, 0.032, 0.019))
    tips = []
    for i, (dx, dy, dz, r0, r1) in enumerate(branches):
        p = p2 + Vector((dx, dy, dz)) * s
        geo.limb(p2, p, r0 * s, r1 * s, seg=5)
        tips.append(p)
        if i < 3:
            q = p + Vector((0.10 * (1 if i % 2 else -1), 0.10 * (i - 1), 0.20)) * s
            geo.limb(p, q, r1 * s, r1 * 0.7 * s, seg=4)
            tips.append(q)
    clusters = ((tips[0], 0.54), (tips[1], 0.47), (tips[2], 0.40), (tips[3], 0.30),
                (tips[4], 0.26), (p2 + Vector((0.06, 0.04, 0.98)) * s, 0.38),
                (p2 + Vector((0.48, -0.20, 0.66)) * s, 0.28),
                (p2 + Vector((-0.42, 0.30, 0.52)) * s, 0.25))
    for i, (c, r) in enumerate(clusters):
        geo.sphere(tuple(c), r * s, seg=9, rings=6,
                   scale=(1.16, 1.10, 0.54 + 0.06 * M.rnd(i, 1, seed)))


def _bamboo(geo, x, y, z, n, seed, leaf_geo):
    for i in range(n):
        ang = 2.0 * math.pi * i / n + 0.9 * M.rnd(i, seed)
        rr = 0.07 + 0.30 * M.rnd(i, seed, 3)
        sx, sy = x + math.cos(ang) * rr, y + math.sin(ang) * rr
        h = 1.70 + 1.05 * M.rnd(i, seed, 7)
        lean = 0.10 + 0.13 * M.rnd(i, seed, 11)
        p0 = Vector((sx, sy, z))
        p1 = p0 + Vector((math.cos(ang + 1.1) * lean, math.sin(ang + 1.1) * lean, h))
        r = 0.024 + 0.009 * M.rnd(i, seed, 17)
        geo.limb(p0, p1, r, r * 0.6, seg=5)
        nn = max(3, int(h / 0.30))
        for k in range(1, nn):
            t = k / float(nn)
            geo.limb(M.lerp(p0, p1, t - 0.007), M.lerp(p0, p1, t + 0.007),
                     r * 1.26, r * 1.26, seg=5)
        for b in range(3):
            bp = M.lerp(p0, p1, 0.54 + 0.16 * b)
            ba = ang + 2.0 * b + 0.55
            bl = 0.26 + 0.15 * M.rnd(i, b, seed)
            tip = bp + Vector((math.cos(ba) * bl, math.sin(ba) * bl, 0.075))
            geo.limb(bp, tip, r * 0.55, r * 0.26, seg=4)
            for lf in range(4):
                q = M.lerp(bp, tip, 0.38 + 0.16 * lf)
                yaw = ba + (lf - 2.0) * 0.46 + 0.30 * M.rnd(i, lf, seed + 2)
                pitch = 0.24 + 0.40 * M.rnd(i, lf, seed + 3)
                roll = (M.rnd(i, lf, seed + 4) - 0.5) * 0.7
                ln = 0.27 + 0.15 * M.rnd(i, lf, seed + 5)
                cy_ = math.cos(pitch)
                centre = q + Vector((cy_ * math.cos(yaw), cy_ * math.sin(yaw),
                                     -math.sin(pitch))) * (ln * 0.42)
                leaf_geo.box(tuple(centre), (ln, 0.078, 0.009),
                             rot=(roll, pitch, yaw))


def _planter(geo_stone, geo_plant, x, y, z, half, h, plants=0, seed=0):
    geo_stone.box((x, y, z + h * 0.5), (half * 2.0, half * 2.0, h))
    geo_stone.box((x, y, z + h * 0.97), (half * 2.18, half * 2.18, 0.06))
    geo_stone.box((x, y, z + 0.03), (half * 2.2, half * 2.2, 0.06))
    geo_plant.box((x, y, z + h * 0.92), (half * 1.7, half * 1.7, 0.05))
    for i in range(plants):
        a = 2.0 * math.pi * i / max(1, plants) + seed
        rr = half * 0.55
        px, py = x + math.cos(a) * rr, y + math.sin(a) * rr
        r = half * 0.34 + 0.05 * M.rnd(i, seed, 5)
        geo_plant.sphere((px, py, z + h * 0.92 + r * 0.75), r, seg=7, rings=5,
                         scale=(1.0, 1.0, 0.85))


def _hanging_lantern(geo_wood, geo_glow, geo_gold, x, y, z, h=2.55):
    """Red paper lantern on a wooden post (street lantern)."""
    geo_wood.box((x, y, z + h * 0.5), (0.13, 0.13, h))
    geo_wood.box((x, y, z + 0.05), (0.46, 0.46, 0.10))
    geo_wood.box((x + 0.30, y, z + h - 0.05), (0.70, 0.10, 0.10))
    lx = x + 0.62
    geo_gold.limb((lx, y, z + h - 0.10), (lx, y, z + h - 0.40), 0.012, 0.012, seg=5)
    geo_glow.sphere((lx, y, z + h - 0.62), 0.20, seg=8, rings=5, scale=(1.0, 1.0, 0.82))
    for i in range(6):
        a = math.pi / 6.0 + 2.0 * math.pi * i / 6.0
        geo_wood.box((lx + math.cos(a) * 0.205, y + math.sin(a) * 0.205, z + h - 0.62),
                     (0.026, 0.026, 0.30), rot=(0.0, 0.0, a))
    geo_gold.box((lx, y, z + h - 0.86), (0.10, 0.10, 0.05))
    geo_glow.sphere((lx, y, z + h - 0.94), 0.045, seg=6, rings=4)


def _stone_lamp(geo, x, y, z):
    geo.box((x, y, z + 0.045), (0.58, 0.58, 0.09))
    geo.box((x, y, z + 0.125), (0.44, 0.44, 0.07))
    geo.limb((x, y, z + 0.16), (x, y, z + 0.78), 0.075, 0.058, seg=8)
    geo.box((x, y, z + 0.805), (0.38, 0.38, 0.055))
    for i in range(4):
        a = math.pi * 0.25 + i * math.pi * 0.5
        geo.box((x + math.cos(a) * 0.145, y + math.sin(a) * 0.145, z + 0.985),
                (0.055, 0.055, 0.30), rot=(0.0, 0.0, a))
    geo.box((x, y, z + 1.152), (0.30, 0.30, 0.035))
    geo.box((x, y, z + 1.27), (0.62, 0.62, 0.20), rot=(0.0, 0.0, math.pi * 0.25))
    geo.sphere((x, y, z + 1.40), 0.045, seg=7, rings=4)


def _banner(geo, glow, x, y, z, h=4.2, facing=1.0):
    """Street banner (幡) on a mast with a cross-arm and a hanging cloth."""
    geo.limb((x, y, z), (x, y, z + h), 0.075, 0.045, seg=8)
    geo.box((x, y, z + h - 0.10), (1.30, 1.30, 0.09))
    geo.box((x, y, z + h - 0.34), (0.95, 0.95, 0.07))
    cy = y + facing * 0.30
    geo.box((x, cy, z + h - 0.95), (0.62, 0.030, 1.05))
    glow.box((x, cy + facing * 0.02, z + h - 0.95), (0.50, 0.020, 0.88))
    for i in range(3):
        geo.box((x - 0.22 + i * 0.22, cy + facing * 0.035, z + h - 0.62),
                (0.075, 0.020, 0.075))


def generate_diorama(params: dict, ctx: dict) -> dict:
    params = dict(params or {})
    detail, detail_key = _detail(params)
    info = M.open_base(params, ctx, "diorama")
    warnings = list(info["warnings"])
    checks = []
    col = M.collection(M.PART_COLLECTIONS["diorama"])

    base = _num(params, "baseSize")
    ph = _num(params, "plinthHeight")
    deck = _num(params, "deckZ")
    half = base * 0.5
    pr = _props(params)
    seg = int(detail["seg"])
    seed = WC.safe_int(params.get("seed"), DEFAULTS["seed"])

    g_stone = M.Geo()
    g_planter = M.Geo()
    g_dark = M.Geo()
    g_carve = M.Geo()
    g_med = M.Geo()
    g_pave = M.Geo()
    g_grid = M.Geo()
    g_step = M.Geo()
    g_prop = M.Geo()
    g_leaf = M.Geo()
    g_lantern = M.Geo()
    g_glow = M.Geo()
    g_gold = M.Geo()

    # ------------------------------------------------------------- plinth
    z_bot = deck - ph
    courses = (
        (z_bot, z_bot + 0.12, half, half - 0.06, "dark"),      # 圭角 dark foot
        (z_bot + 0.12, z_bot + 0.21, half - 0.06, half - 0.02, "stone"),   # 下枋
        (z_bot + 0.21, z_bot + 0.41, half - 0.02, half - 0.16, "dark"),    # 束腰 waist
        (z_bot + 0.41, z_bot + 0.56, half - 0.16, half - 0.03, "stone"),   # 上枋
        (z_bot + 0.56, deck, half - 0.03, half, "stone"),                   # 上枭顶部
    )
    for (z0, z1, h0, h1, tone) in courses:
        _taper(g_dark if tone == "dark" else g_stone, h0, h1, z0, z1)
    # the recessed waist face carries the frieze; keep a joint line top and bottom
    g_carve.box((0.0, 0.0, z_bot + 0.21), (2 * half - 0.30, 2 * half - 0.30, 0.018))
    g_carve.box((0.0, 0.0, z_bot + 0.41), (2 * half - 0.30, 2 * half - 0.30, 0.018))
    # bed under the paving so the joints show stone, not a hole
    g_dark.box((0.0, 0.0, deck - 0.075), (base - 0.34, base - 0.34, ph - 0.09))

    if params.get("frieze", DEFAULTS["frieze"]):
        fl = base - 0.36
        fz = z_bot + 0.31
        fh, fd = 0.15, 0.18
        face = half - 0.10
        for sy in (-1, 1):
            _meander(g_carve, fl, fh, fd, (0.0, sy * face, fz), axis="x")
        for sx in (-1, 1):
            _meander(g_carve, fl, fh, fd, (sx * face, 0.0, fz), axis="y")
    else:
        WC.check(checks, "diorama_frieze", "warn", "frieze disabled by params")

    if params.get("medallion", DEFAULTS["medallion"]):
        r = 0.13
        bz = z_bot + 0.50
        for sx in (-1, 1):
            for sy in (-1, 1):
                _medallion(g_med, (sx * (half - 0.62), sy * (half - 0.03), bz), r, 0.06, "y")
                _medallion(g_med, (sx * (half - 0.03), sy * (half - 0.62), bz), r, 0.06, "x")
        for sy in (-1, 1):
            _medallion(g_med, (0.0, sy * (half - 0.03), bz), r * 1.25, 0.06, "y")
        for sx in (-1, 1):
            _medallion(g_med, (sx * (half - 0.03), 0.0, bz), r * 1.25, 0.06, "x")

    # --------------------------------------------------------- bracket grid
    rim = base - 1.4
    grid_top = z_bot
    for sy in (-1, 1):
        g_grid.box((0.0, sy * (rim * 0.5 - 0.17), grid_top - 0.024),
                   (rim, 0.34, 0.048))
    for sx in (-1, 1):
        g_grid.box((sx * (rim * 0.5 - 0.17), 0.0, grid_top - 0.024),
                   (0.34, rim - 0.68, 0.048))
    n_beam = 4
    for i in range(n_beam):
        yy = -rim * 0.4 + rim * 0.8 * i / (n_beam - 1)
        g_grid.box((0.0, yy, grid_top - 0.075), (rim - 0.9, 0.30, 0.055))
    for i in range(n_beam - 1):
        xx = -rim * 0.32 + rim * 0.64 * i / max(1, n_beam - 2)
        g_grid.box((xx, 0.0, grid_top - 0.123), (0.26, rim - 1.3, 0.050))

    # -------------------------------------------------------------- paving
    if params.get("paving", DEFAULTS["paving"]):
        slab_t = 0.030
        pitch = 1.15 * detail["paving"]
        inner = half - 0.34
        rows = max(2, int(round((2 * inner) / pitch)))
        step = (2 * inner) / rows
        for j in range(rows):
            y0 = -inner + step * j
            off = (0.5 * step) if (j % 2) else 0.0
            n = max(1, int(round((2 * inner) / (step * 1.5))))
            wslab = (2 * inner) / n
            for i in range(n):
                x0 = -inner + wslab * i + off
                x1 = min(inner, x0 + wslab - 0.028)
                if x1 - x0 < 0.10:
                    continue
                y1 = min(inner, y0 + step - 0.028)
                g_pave.box(((x0 + x1) * 0.5, (y0 + y1) * 0.5, deck - slab_t * 0.5),
                           (x1 - x0, y1 - y0, slab_t))
        # kerb border
        for sy in (-1, 1):
            g_pave.box((0.0, sy * (half - 0.17), deck - 0.022), (base, 0.34, 0.044))
        for sx in (-1, 1):
            g_pave.box((sx * (half - 0.17), 0.0, deck - 0.022), (0.34, base, 0.044))

    # --------------------------------------------------------------- steps
    n_step = 4
    rise = ph / n_step
    y_front = half + 0.0
    for k in range(n_step):
        z1 = z_bot + rise * (k + 1)
        depth = 0.34
        g_step.box((0.0, y_front + 0.24 + depth * (n_step - 1 - k) * 0.5,
                    z1 - rise * 0.5 + 0.001),
                   (3.30, depth * (n_step - k), rise))
    for sx in (-1, 1):
        g_step.box((sx * 1.85, y_front + 0.55, deck - 0.30), (0.36, 1.4, 0.62))

    # --------------------------------------------------------------- props
    beds = [(-half + 1.35, half - 1.35), (half - 1.35, -half + 1.35)]
    tree_at = [(-half + 1.5, -half + 2.2), (half - 1.5, half - 2.2),
               (-half + 1.4, half - 1.4), (half - 1.4, -half + 1.4)]
    for i in range(min(pr["trees"], len(tree_at))):
        tx, ty = tree_at[i]
        _planter(g_planter, g_leaf, tx, ty, deck, 0.62, 0.30, plants=0, seed=seed + i)
        _tree(g_prop, tx, ty, deck + 0.30, 1.0 + 0.12 * ((i % 3) - 1), seed + i)
    bamboo_at = [(half - 1.6, -half + 1.2), (-half + 1.5, half - 1.2),
                 (half - 2.6, half - 1.6)]
    for i in range(min(pr["bamboo"], len(bamboo_at))):
        bx, by = bamboo_at[i]
        _planter(g_planter, g_leaf, bx, by, deck, 0.52, 0.26, plants=0, seed=seed + 40 + i)
        _bamboo(g_prop, bx, by, deck + 0.26, 5, seed + 40 + i, g_leaf)
    planter_at = [(-3.1, half - 1.0), (3.1, half - 1.0),
                  (-half + 1.0, -1.2), (half - 1.0, 1.2),
                  (-half + 1.0, -3.4), (half - 1.0, -3.4)]
    for i in range(min(pr["planters"], len(planter_at))):
        px, py = planter_at[i]
        _planter(g_planter, g_leaf, px, py, deck, 0.46, 0.50, plants=3, seed=seed + 60 + i)
    lamp_at = [(half - 1.0, half - 1.0), (-half + 1.0, -half + 1.0),
               (half - 1.0, -half + 1.0), (2.6, half - 0.9)]
    for i in range(min(pr["stoneLamps"], len(lamp_at))):
        _stone_lamp(g_lantern, lamp_at[i][0], lamp_at[i][1], deck)
    banner_at = [(3.5, half - 0.8), (-3.5, half - 0.8), (5.4, 1.2)]
    for i in range(min(pr["banners"], len(banner_at))):
        _banner(g_prop, g_gold, banner_at[i][0], banner_at[i][1], deck)
    lantern_at = [(2.35, half - 0.65), (-2.35, half - 0.65), (half - 0.9, 2.4)]
    for i in range(min(pr["lanterns"], len(lantern_at))):
        _hanging_lantern(g_lantern, g_glow, g_gold, lantern_at[i][0],
                         lantern_at[i][1], deck)

    objs = []

    def emit(name, g, mat, comp, smooth=False):
        ob = M.finish(g, name, "diorama", comp, mat, col, params, smooth=smooth)
        if ob is not None:
            objs.append(ob)

    emit("BASE_Plinth", g_stone, "stone", "base_plinth")
    emit("BASE_Foot", g_dark, "stone_dark", "base_foot")
    emit("BASE_Frieze", g_carve, "stone_warm", "base_frieze")
    emit("BASE_Medallion", g_med, "stone_warm", "base_medallion")
    emit("BASE_Grid", g_grid, "timber_dark", "base_grid")
    emit("BASE_Paving", g_pave, "paving", "base_paving")
    emit("BASE_Steps", g_step, "stone_warm", "base_steps")
    emit("PROP_Vegetation", g_prop, "plant_dark", "prop_vegetation", smooth=True)
    emit("PROP_Foliage", g_leaf, "plant", "prop_foliage", smooth=True)
    emit("PROP_Planter", g_planter, "stone", "prop_planter")
    emit("LANTERN_Frame", g_lantern, "timber_dark", "lantern_frame")
    emit("LANTERN_Glow", g_glow, "lamp_glow", "lantern_glow", smooth=True)
    emit("PROP_Gold", g_gold, "gold", "prop_gold")

    out = M.save_out(info["out"])
    arts = [WC.artifact("blend", out)]
    tris = M.tri_count(objs)
    rep = M.mesh_report(objs)
    # the plinth check measures the *stone* plinth, not the props standing on it
    stone = [o for o in objs if o is not None and
             (o.get("wm_component") or "").startswith(("base_plinth", "base_foot",
                                                       "base_paving", "base_grid"))]
    bounds = WC.scene_bounds(stone) if stone else None
    envelope = WC.scene_bounds([o for o in objs if o.type == "MESH"])
    size_x = bounds["size"][0] if bounds else 0.0
    size_y = bounds["size"][1] if bounds else 0.0
    top_z = bounds["max"][2] if bounds else deck
    env_x = envelope["size"][0] if envelope else 0.0
    env_y = envelope["size"][1] if envelope else 0.0
    WC.check(checks, "diorama_plinth_size",
             "pass" if abs(size_x - base) < 0.02 and abs(size_y - base) < 0.02 else "warn",
             f"stone plinth bounding box {size_x:.3f} x {size_y:.3f} m "
             f"(baseSize={base}), deck z={deck:.3f}, measured plinth top z={top_z:.3f}")
    WC.check(checks, "diorama_envelope",
             "pass" if env_x <= base + 0.2 and env_y <= base + 1.6 else "warn",
             f"full envelope including the front steps and props: {env_x:.2f} x "
             f"{env_y:.2f} x {envelope['size'][2]:.2f} m; the front 踏跺 projects "
             f"{max(0.0, (env_y - base) * 0.5):.2f} m past the plinth face, which "
             f"grows the web envelope beyond the 16 m plan")
    WC.check(checks, "diorama_band_structure",
             "pass" if len(courses) >= 5 else "fail",
             "courses: " + ", ".join(
                 f"{tone} {z0 - z_bot:.2f}..{z1 - z_bot:.2f}" for (z0, z1, _, _, tone) in courses))
    WC.check(checks, "diorama_frieze",
             "pass" if params.get("frieze", True) else "warn",
             "real 回纹 meander bars on all four faces" if params.get("frieze", True)
             else "disabled")
    WC.check(checks, "diorama_medallion",
             "pass" if params.get("medallion", True) else "warn",
             "8-petal lotus roundels at corners and mid-faces"
             if params.get("medallion", True) else "disabled")
    WC.check(checks, "diorama_props",
             "pass" if (pr["trees"] + pr["bamboo"] + pr["planters"]) > 0 else "warn",
             f"trees={pr['trees']} bamboo={pr['bamboo']} planters={pr['planters']} "
             f"lanterns={pr['lanterns']} stoneLamps={pr['stoneLamps']} banners={pr['banners']}")
    WC.check(checks, "diorama_topology",
             "pass" if rep["degenerateFaces"] == 0 else "fail",
             f"boundaryEdges={rep['boundaryEdges']} degenerate={rep['degenerateFaces']}")
    WC.check(checks, "diorama_triangle_budget",
             "pass" if tris <= 60000 else ("warn" if tris <= 90000 else "fail"),
             f"triangles={tris} objects={len(objs)}")
    metrics = {
        "baseSize": base,
        "plinthHeight": round(ph, 3),
        "plinthTopZ": round(top_z, 3),
        "deckZ": deck,
        "sizeX": round(size_x, 3),
        "sizeY": round(size_y, 3),
        "steps": n_step,
        "props": pr,
        "triangles": tris,
        "objects": len(objs),
        "detail": detail_key,
    }
    notes = (f"plinth {base:.1f} x {base:.1f} m, top z={deck:.2f}, {len(courses)} carved "
             f"courses over {ph:.2f} m; meander frieze + lotus roundels; "
             f"{n_step} front steps; props trees={pr['trees']} bamboo={pr['bamboo']} "
             f"planters={pr['planters']} lanterns={pr['lanterns']} "
             f"stoneLamps={pr['stoneLamps']} banners={pr['banners']}; {tris} triangles. "
             f"Replaced {info['deleted']} previous diorama objects.")
    return M.result("generate_diorama", ctx, params, objs, arts, metrics, checks,
                    warnings, notes)

