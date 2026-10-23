"""V5 roof system: hip-and-gable (歇山) roof with real tile courses, wadang,
ridges, a continuous 生起 eave curve and a three-tier 斗拱 under the eave.

Stack, from the roof surface outwards:

    斗拱 (three tiers, 青绿彩画) -> 撩檐枋-> 檐椽 / 飞椽 tails -> 瓦口
        -> tile bed (solid slab) -> 半圆筒瓦 caps -> 瓦当 at every cap end
        -> 正脊 / 戗脊 / 山花.

The eave is NOT a straight line that kinks at the corners. In (u, v)
parameter space s = min(|u|, |v|) is 0 at the middle of every side and 1 at
the plan corner, so one s**p term produces the continuous concave
"flat in the middle, sweeping up at the corners" profile of the concept art,
and the same field twists the whole corner panel (翼角) rather than only its
edge.  The plan is flared at the corners too (出翘), which is what makes the
corner silhouette read as a wing instead of a tilted rectangle.

Geometry is generated in parameter space so the surface, the tile ribs, the
ridges, the gable ends and the eave assembly all share one definition and
cannot drift apart.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Matrix, Vector

import gal5 as G


# ------------------------------------------------------------------ tuning
GABLE_G = 1.28          # 收山: how far the gable plane is set in from the edge
GABLE_Z = 8.78          # 撒头 ridge / bottom of the 山花 face

LIFT_SQ = 0.46          # 生起: rise at the plan corner (m)
LIFT_P = 2.20           # concave exponent: 0 at mid-side, 1 at the corner
KICK = 0.14             # extra 起翘 right at the corner
KICK_R = 1.00           # radius of the corner kick (m)
LIFT_H = 2.60           # how far up the slope the lift dies out (m)
FLARE = 0.105           # 翼角出翘: plan flare at the corner, share of half-span
FLARE_P = 3.0           # flare falloff exponent

TILE_SP = 0.285         # 瓦垄 spacing (m)
TILE_R = 0.095          # 筒瓦 radius


# ------------------------------------------------------------------ geo buf
class _Geo(object):
    """Accumulate boxes/tubes into one mesh so a whole eave is 4 objects."""

    __slots__ = ("v", "f")

    def __init__(self):
        self.v = []
        self.f = []

    def add(self, verts, faces):
        o = len(self.v)
        self.v.extend(tuple(p) for p in verts)
        self.f.extend(tuple(i + o for i in fc) for fc in faces)

    def box(self, M, c, s):
        hx, hy, hz = s[0] * 0.5, s[1] * 0.5, s[2] * 0.5
        loc = []
        for sz in (-1.0, 1.0):
            for sy in (-1.0, 1.0):
                for sx in (-1.0, 1.0):
                    loc.append(Vector((c[0] + sx * hx, c[1] + sy * hy,
                                       c[2] + sz * hz)))
        verts = [tuple(M @ p) for p in loc]
        faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4),
                 (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
        self.add(verts, faces)

    def tube(self, p0, p1, r, seg=8, cap=True):
        a = Vector(p0)
        b = Vector(p1)
        d = b - a
        if d.length < 1e-6:
            return
        d.normalize()
        up = Vector((0.0, 0.0, 1.0))
        if abs(d.z) > 0.94:
            up = Vector((0.0, 1.0, 0.0))
        e1 = d.cross(up).normalized()
        e2 = d.cross(e1).normalized()
        rings = []
        for c in (a, b):
            ring = []
            for i in range(seg):
                t = 2.0 * math.pi * i / seg
                ring.append(tuple(c + e1 * (r * math.cos(t)) +
                                  e2 * (r * math.sin(t))))
            rings.append(ring)
        verts = rings[0] + rings[1]
        faces = []
        for i in range(seg):
            j = (i + 1) % seg
            faces.append((i, j, j + seg, i + seg))
        if cap:
            faces.append(tuple(range(seg - 1, -1, -1)))
            faces.append(tuple(range(seg, 2 * seg)))
        self.add(verts, faces)

    def obj(self, name, col, material):
        if not self.f:
            return None
        return G.add_mesh(name, self.v, self.f, col, material)


def _frame(origin, ex, ey):
    """Matrix with local +X = ex, +Y = ey, +Z = world up."""
    ex = Vector((ex[0], ex[1], 0.0))
    ey = Vector((ey[0], ey[1], 0.0))
    if ex.length < 1e-9:
        ex = Vector((1.0, 0.0, 0.0))
    if ey.length < 1e-9:
        ey = Vector((0.0, 1.0, 0.0))
    ex.normalize()
    ey.normalize()
    return Matrix(((ex.x, ey.x, 0.0, origin[0]),
                   (ex.y, ey.y, 0.0, origin[1]),
                   (0.0, 0.0, 1.0, origin[2]),
                   (0.0, 0.0, 0.0, 1.0)))


# ------------------------------------------------------------------ surface
class Surface(object):
    """Roof surface in (u, v) in [-1, 1]; u along X, v along Y."""

    def __init__(self, w, d, eave_z, ridge_z, k=0.44, g=0.0, hip=True,
                 cy=0.0, lift=LIFT_SQ, lift_p=LIFT_P, kick=KICK,
                 kick_r=KICK_R, lift_h=LIFT_H, flare=FLARE, flare_p=FLARE_P):
        self.w, self.d = w, d
        self.hw, self.hd = w * 0.5, d * 0.5
        self.eave_z, self.ridge_z, self.k = eave_z, ridge_z, k
        self.g, self.hip = g, hip
        self.cy = cy
        self.ug = (1.0 - 2.0 * g / w) if (g and not hip) else 0.0
        self.lift, self.lift_p = lift, lift_p
        self.kick, self.kick_r, self.lift_h = kick, kick_r, lift_h
        self.flare, self.flare_p = flare, flare_p

    # -- plan ------------------------------------------------------------
    def plan(self, u, v):
        if self.flare <= 0.0:
            return u * self.hw, v * self.hd
        if self.hip:
            r = abs(u)
        else:
            r = max(0.0, (abs(u) - self.ug) / max(1e-6, 1.0 - self.ug))
        X = u * self.hw * (1.0 + self.flare * r * abs(v) ** self.flare_p)
        Y = v * self.hd * (1.0 + self.flare * r * abs(u) ** self.flare_p)
        return X, Y

    # -- height before the eave lift --------------------------------------
    def base(self, u, v):
        ty = min(1.0, abs(v))
        gz = G.apex_z(1.0 - ty, self.eave_z, self.ridge_z, self.k)
        if self.hip:
            y = v * self.hd
            x = u * self.hw
            dist = min(self.hd - abs(y), self.hw - abs(x))
            t = max(0.0, min(1.0, dist / self.hd))
            return G.apex_z(t, self.eave_z, self.ridge_z, self.k)
        if abs(u) <= self.ug:
            return gz
        y = v * self.hd
        x = u * self.hw
        dist = min(self.hd - abs(y), self.hw - abs(x))
        t = max(0.0, min(1.0, dist / self.hd))
        return min(gz, G.apex_z(t, self.eave_z, self.ridge_z, self.k))

    # -- height with 生起 / 起翘 -------------------------------------------
    def point(self, u, v):
        X, Y = self.plan(u, v)
        zb = self.base(u, v)
        z = zb
        fade = 1.0 - max(0.0, zb - self.eave_z) / self.lift_h
        if fade > 0.0:
            fade = min(1.0, fade)
            s = min(abs(u), abs(v))
            rise = self.lift * (s ** self.lift_p)
            dc = math.hypot(self.hw - abs(X), self.hd - abs(Y))
            kick = self.kick * math.exp(-(dc / self.kick_r) ** 2)
            z = zb + (rise + kick) * (fade ** 1.35)
        return Vector((X, Y + self.cy, z))

    def normal(self, u, v, eps=0.0015):
        u0, u1 = max(-1.0, u - eps), min(1.0, u + eps)
        v0, v1 = max(-1.0, v - eps), min(1.0, v + eps)
        pu = self.point(u1, v) - self.point(u0, v)
        pv = self.point(u, v1) - self.point(u, v0)
        n = pu.cross(pv)
        if n.length < 1e-9:
            return Vector((0.0, 0.0, 1.0))
        n.normalize()
        if n.z < 0.0:
            n = -n
        return n

    # -- eave frame: point + tangent + outward ---------------------------
    def eave(self, side, t):
        """side in F/B/R/L, t in [-1, 1]; returns (P, T, O)."""
        if side == "F":
            u, v, du, dv = t, 1.0, 1.0, 0.0
        elif side == "B":
            u, v, du, dv = -t, -1.0, -1.0, 0.0
        elif side == "R":
            u, v, du, dv = 1.0, -t, 0.0, -1.0
        else:
            u, v, du, dv = -1.0, t, 0.0, 1.0
        p = self.point(u, v)
        eps = 0.004
        a = self.point(u + du * eps, v + dv * eps)
        b = self.point(u - du * eps, v - dv * eps)
        T = Vector((a.x - b.x, a.y - b.y, 0.0))
        if T.length < 1e-9:
            T = Vector((1.0, 0.0, 0.0))
        T.normalize()
        O = Vector((-T.y, T.x, 0.0))
        if O.x * p.x + O.y * (p.y - self.cy) < 0.0:
            O = -O
        return p, T, O


def _main_surface():
    return Surface(G.ROOF_W, G.ROOF_D, G.ROOF_MAIN_EAVE, G.RIDGE_Z,
                   k=0.44, g=GABLE_G, hip=False, cy=G.BCY)


def _skirt_surface():
    return Surface(G.BW + G.SKIRT_OV * 2.0, G.BD + G.SKIRT_OV * 2.0,
                   G.EAVE_Z, G.SKIRT_IN, k=0.62, hip=True, cy=G.BCY,
                   lift=0.16, lift_p=2.4, kick=0.06, kick_r=0.9,
                   lift_h=0.95)


def main_roof_z(x, y):
    """World (x, y) -> top of the main roof surface. Used by the interior."""
    s = _main_surface()
    u, v = x / s.hw, (y - s.cy) / s.hd
    for _ in range(4):
        X, Y = s.plan(u, v)
        u += (x - X) / s.hw
        v += (y - s.cy - Y) / s.hd
    u = max(-1.0, min(1.0, u))
    v = max(-1.0, min(1.0, v))
    return s.point(u, v).z


# ------------------------------------------------------------------ shells
def shell(name, surf, col, material, nu=96, nv=84, thickness=0.17, hole=None):
    top, bot = [], []
    for j in range(nv + 1):
        v = -1.0 + 2.0 * j / nv
        r0, r1 = [], []
        for i in range(nu + 1):
            u = -1.0 + 2.0 * i / nu
            p = surf.point(u, v)
            r0.append((p.x, p.y, p.z))
            r1.append((p.x, p.y, p.z - thickness))
        top.append(r0)
        bot.append(r1)
    verts = [q for r in top for q in r] + [q for r in bot for q in r]
    n = (nu + 1) * (nv + 1)
    faces = []
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            q = (a, a + 1, a + nu + 2, a + nu + 1)
            if hole is not None:
                uc = -1.0 + 2.0 * (i + 0.5) / nu
                vc = -1.0 + 2.0 * (j + 0.5) / nv
                if abs(uc) < hole[0] and abs(vc) < hole[1]:
                    continue
            faces.append(q)
            faces.append(tuple(reversed(tuple(x + n for x in q))))
    for j in range(nv):
        for i in (0, nu):
            a = j * (nu + 1) + i
            b = (j + 1) * (nu + 1) + i
            faces.append((a, b, b + n, a + n) if i == 0 else (b, a, a + n, b + n))
    for i in range(nu):
        for j in (0, nv):
            a = j * (nu + 1) + i
            b = j * (nu + 1) + i + 1
            faces.append((b, a, a + n, b + n) if j == 0 else (a, b, b + n, a + n))
    ob = G.add_mesh(name, verts, faces, col, material)
    G.shade_smooth(ob)
    return ob


def _rib(geo, surf, uv_pts, radius, eave_cap=None):
    """Half-round tile cap running along a course of (u, v) points."""
    rings = []
    for (u, v) in uv_pts:
        p = surf.point(u, v)
        nrm = surf.normal(u, v)
        pu = surf.point(min(1.0, u + 0.004), v) - surf.point(max(-1.0, u - 0.004), v)
        pv = surf.point(u, min(1.0, v + 0.004)) - surf.point(u, max(-1.0, v - 0.004))
        tan = pu if pu.length > pv.length else pv
        if tan.length < 1e-9:
            continue
        tan.normalize()
        side = tan.cross(nrm)
        if side.length < 1e-9:
            continue
        side.normalize()
        c = p + nrm * 0.012
        ring = []
        for a in range(5):
            ang = math.pi * a / 4.0
            ring.append(c + side * (radius * math.cos(ang)) +
                        nrm * (radius * math.sin(ang)))
        rings.append(ring)
    if len(rings) < 2:
        return
    start = len(geo.v)
    for ring in rings:
        geo.v.extend(tuple(q) for q in ring)
    span = 5
    for i in range(len(rings) - 1):
        for a in range(span - 1):
            v0 = start + i * span + a
            geo.f.append((v0, v0 + 1, v0 + span + 1, v0 + span))
    geo.f.append(tuple(start + a for a in range(span - 1, -1, -1)))
    last = start + (len(rings) - 1) * span
    geo.f.append(tuple(last + a for a in range(span - 1, -1, -1)))
    if eave_cap is not None:
        p = surf.point(*uv_pts[0])
        nrm = surf.normal(*uv_pts[0])
        out = eave_cap
        _disc(geo, p + nrm * 0.01, nrm, out, radius * 1.12, radius * 0.30)


def _disc(geo, centre, nrm, out, radius, thick):
    """Round tile end (瓦当) standing proud of the eave."""
    e1 = nrm.cross(out)
    if e1.length < 1e-6:
        e1 = nrm.cross(Vector((1.0, 0.0, 0.0)))
    e1.normalize()
    e2 = nrm.copy()
    a = centre - out * thick * 0.5
    b = centre + out * thick * 0.5
    seg = 12
    start = len(geo.v)
    for c in (a, b):
        for i in range(seg):
            t = 2.0 * math.pi * i / seg
            geo.v.append(tuple(c + e1 * (radius * math.cos(t)) +
                               e2 * (radius * math.sin(t))))
    for i in range(seg):
        j = (i + 1) % seg
        geo.f.append((i, j, j + seg, i + seg))
    geo.f.append(tuple(range(seg - 1, -1, -1)))
    geo.f.append(tuple(range(seg, 2 * seg)))


def tiles(name, surf, col, material, spacing=TILE_SP, radius=TILE_R,
          step=0.52, cap_wadang=True):
    geo = _Geo()
    ug = surf.ug
    hw, hd = surf.hw, surf.hd
    # ---- front / back courses (gable span only on a 歇山) ----------------
    if surf.hip:
        n_x = max(2, int(round(2.0 * hw / spacing)))
        u_lo, u_hi = -1.0, 1.0
    else:
        n_x = max(2, int(round(2.0 * ug * hw / spacing)))
        u_lo, u_hi = -ug, ug
    n_v = max(8, int(round(hd * 1.7 / step)))
    for i in range(n_x + 1):
        u = u_lo + (u_hi - u_lo) * i / n_x
        for sgn in (-1.0, 1.0):
            pts = []
            for k in range(n_v + 1):
                vk = sgn * (1.0 - k / float(n_v))
                pts.append((u, vk))
                if surf.hip:
                    if hd * (1.0 - abs(vk)) >= hw * (1.0 - abs(u)) - 1e-6:
                        break
                elif abs(vk) <= 1e-9:
                    break
            if len(pts) >= 3:
                out = None
                if cap_wadang:
                    _, _, out = surf.eave("F" if sgn > 0 else "B",
                                          u if sgn > 0 else -u)
                _rib(geo, surf, pts, radius, out)
    # ---- side courses ----------------------------------------------------
    n_y = max(2, int(round(2.0 * hd / spacing)))
    n_u = max(8, int(round(hw * 1.7 / step)))
    for j in range(n_y + 1):
        v = -1.0 + 2.0 * j / n_y
        for sgn in (-1.0, 1.0):
            pts = []
            for k in range(n_u + 1):
                uk = sgn * (1.0 - k / float(n_u))
                pts.append((uk, v))
                if surf.hip:
                    if hd * (1.0 - abs(v)) >= hw * (1.0 - abs(uk)) - 1e-6:
                        break
                elif abs(uk) <= ug + 1e-6:
                    break
            if len(pts) >= 3:
                out = None
                if cap_wadang:
                    _, _, out = surf.eave("R" if sgn > 0 else "L",
                                          -v if sgn > 0 else v)
                _rib(geo, surf, pts, radius, out)
    return geo.obj(name, col, material)


# ------------------------------------------------------------------ ridges
def swept_ridge(name, pts, col, material, width=0.34, height=0.24, layers=3,
                taper=0.16):
    """Solid ridge: trapezoid section swept along the ridge line.

    The first pass stacked three flat ribbons with air between them; from any
    distance that read as three thin wires floating over the tiles.  A single
    closed prism plus a thin cap reads as masonry.
    """
    if len(pts) < 2:
        return []
    side_lo, side_hi = [], []
    for idx, p in enumerate(pts):
        p_prev = pts[max(0, idx - 1)]
        p_next = pts[min(len(pts) - 1, idx + 1)]
        tan = Vector(p_next) - Vector(p_prev)
        if tan.length < 1e-6:
            tan = Vector((1, 0, 0))
        tan.normalize()
        side = tan.cross(Vector((0, 0, 1)))
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        base = Vector(p)
        side_lo.append(base - side * (width * 0.5))
        side_hi.append(base + side * (width * 0.5))
    verts, faces = [], []
    h = height
    for i in range(len(pts)):
        p = Vector(pts[i])
        lo, hi = side_lo[i], side_hi[i]
        # four rings per station: base lo/hi and top lo/hi (inset)
        mid = (lo + hi) * 0.5
        top_lo = mid + (lo - mid) * 0.58 + Vector((0, 0, h))
        top_hi = mid + (hi - mid) * 0.58 + Vector((0, 0, h))
        verts.extend([tuple(lo), tuple(hi), tuple(top_lo), tuple(top_hi)])
    for i in range(len(pts) - 1):
        a = i * 4
        faces.append((a, a + 1, a + 5, a + 4))
        faces.append((a + 4, a + 5, a + 7, a + 6))
        faces.append((a + 2, a + 6, a + 7, a + 3))
        faces.append((a, a + 2, a + 3, a + 1))
    faces.append((0, 1, 3, 2))
    last = (len(pts) - 1) * 4
    faces.append((last, last + 2, last + 3, last + 1))
    return [G.add_mesh(name, verts, faces, col, material)]


def chiwen(name, loc, col, material, facing=1.0, scale=1.0):
    """Ridge-end ornament: a curled fin, extruded from a styled profile."""
    profile = [(0.00, 0.00), (0.16, 0.02), (0.34, 0.20), (0.46, 0.52),
               (0.40, 0.78), (0.24, 0.84), (0.14, 0.68), (0.20, 0.50),
               (0.30, 0.40), (0.22, 0.30), (0.05, 0.24)]
    thick = 0.10 * scale
    verts, faces = [], []
    for (u, v) in profile:
        verts.append((u * scale, -thick * 0.5, v * scale))
        verts.append((u * scale, thick * 0.5, v * scale))
    n = len(profile)
    for i in range(n):
        a = i * 2
        b = ((i + 1) % n) * 2
        faces.append((a, a + 1, b + 1, b))
    faces.append(tuple(i * 2 for i in range(n)))
    faces.append(tuple(reversed([i * 2 + 1 for i in range(n)])))
    ob = G.add_mesh(name, verts, faces, col, material, loc=loc)
    if facing < 0:
        ob.scale = (-1.0, 1.0, 1.0)
    return ob


# ------------------------------------------------------------------ bracket
CL_H = 0.44             # 三踩斗拱 total height at scale 1.0


def _dougong(wood, gold, teal, M, tiers=3, s=1.0):
    """One 斗拱 cluster in the local frame of its eave point.

    Local +X runs along the eave, +Y points out of the roof, +Z is up; the
    origin sits at the bottom centre of the 栌斗.  Deliberately slim: the first
    pass used 0.74 m arms at 0.66 m spacing, so neighbouring clusters merged
    into one brown shelf and swallowed the whole eave.
    """
    w, g, t = wood, gold, teal
    w.box(M, (0.0, 0.0, 0.040 * s), (0.225 * s, 0.225 * s, 0.080 * s))
    w.box(M, (0.0, 0.0, 0.096 * s), (0.180 * s, 0.180 * s, 0.032 * s))
    z = 0.108 * s
    for i in range(max(1, tiers)):
        arm = (0.44 - 0.085 * i) * s
        yoff = (0.014 * i) * s
        w.box(M, (0.0, yoff, z + 0.026 * s), (arm, 0.058 * s, 0.052 * s))
        for sx in (-1.0, 1.0):
            w.box(M, (sx * arm * 0.44, yoff, z + 0.075 * s),
                  (0.072 * s, 0.082 * s, 0.046 * s))
        w.box(M, (0.0, yoff, z + 0.073 * s), (0.085 * s, 0.085 * s, 0.044 * s))
        t.box(M, (0.0, yoff + 0.030 * s, z + 0.026 * s),
              (arm * 0.80, 0.005 * s, 0.030 * s))
        z += 0.095 * s
    # 昂 slim beak angled down and out from the top tier
    Ma = M @ Matrix.Rotation(math.radians(-18.0), 4, 'X')
    w.box(Ma, (0.0, 0.085 * s, z - 0.040 * s), (0.058 * s, 0.21 * s, 0.040 * s))
    g.box(Ma, (0.0, 0.185 * s, z - 0.040 * s), (0.052 * s, 0.020 * s, 0.034 * s))
    # 耍头 at the very top, projecting a little further than the tiers
    w.box(M, (0.0, 0.036 * s, z + 0.020 * s), (0.10 * s, 0.15 * s, 0.046 * s))
    g.box(M, (0.0, 0.036 * s, z + 0.045 * s), (0.098 * s, 0.148 * s, 0.008 * s))


def _eave_beam(geo, surf, side, n, y_off, z_off, thick, height):
    """Continuous 撩檐枋following the curved eave line."""
    prev = None
    for i in range(n + 1):
        t = -1.0 + 2.0 * i / n
        p, T, O = surf.eave(side, t)
        cur = (p, T, O)
        if prev is not None:
            pm = (prev[0] + p) * 0.5
            Tm = prev[1] + T
            Om = prev[2] + O
            M = _frame((pm.x + Om.x * y_off, pm.y + Om.y * y_off,
                        pm.z + z_off), Tm, Om)
            seg = max(0.02, (p - prev[0]).length + 0.012)
            geo.box(M, (0.0, 0.0, 0.0), (seg, thick, height))
        prev = cur


def eave_assembly(name, surf, col, mats, tiers=3, spacing=0.66, scale=1.0,
                  n_seg=80):
    """瓦口 + 檐椽 + 飞椽 + 撩檐枋+ 斗拱, all below the eave line.

    `scale` shrinks the whole stack together so the main roof can carry a
    three-tier 斗拱 while the lower (腰檐) roof only shows rafter ends and a
    thin beam, which is what the concept art does —a deep bracket band on the
    lower roof covers the second-floor windows.
    """
    wood = _Geo()
    brack = _Geo()
    beam = _Geo()
    gold = _Geo()
    teal = _Geo()
    pale = _Geo()
    m_wood, m_gold, m_teal, m_pale = mats
    obs = []
    s = scale

    # 瓦口板 thin band right under the tile ends
    for side in ("F", "B", "R", "L"):
        _eave_beam(pale, surf, side, n_seg, -0.030 * s, -0.055 * s,
                   0.070 * s, 0.078 * s)

    # 撩檐枋 sits proud of the bracket line so the band reads in two layers
    for side in ("F", "B", "R", "L"):
        _eave_beam(beam, surf, side, n_seg, -0.520 * s, -0.255 * s,
                   0.160 * s, 0.170 * s)
        _eave_beam(gold, surf, side, n_seg, -0.520 * s, -0.172 * s,
                   0.165 * s, 0.016 * s)
        _eave_beam(teal, surf, side, n_seg, -0.596 * s, -0.255 * s,
                   0.008 * s, 0.120 * s)
    # 拱眼壁 painted panel behind the brackets, keeps the band from reading as
    # a row of floating blocks against white plaster
    # 拱眼壁 + 檐下垫板: painted panel behind the brackets, plus a boarded band
    # that closes the slot between the beam and the roof soffit.  Without the
    # band the white attic wall shows straight through the eave from below.
    for side in ("F", "B", "R", "L"):
        _eave_beam(teal, surf, side, n_seg, -0.345 * s, -0.520 * s,
                   0.022 * s, 0.330 * s)
        # 望板: solid boarded soffit from the slab down to the beam, so the
        # plaster wall behind cannot show through the rafter gaps
        _eave_beam(beam, surf, side, n_seg, -0.320 * s, -0.205 * s,
                   0.045 * s, 0.310 * s)

    for side in ("F", "B", "R", "L"):
        half = surf.hw if side in "FB" else surf.hd
        n_raf = max(8, int(round(2.0 * half / (0.27 * s))))
        for i in range(n_raf + 1):
            t = -1.0 + 2.0 * i / n_raf
            p, T, O = surf.eave(side, t)
            # 飞椽 (square, upper/outer row)
            a = p + O * (-0.010 * s) + Vector((0.0, 0.0, -0.155 * s))
            b = p + O * (-0.500 * s) + Vector((0.0, 0.0, -0.060 * s))
            wood.tube(a, b, 0.036 * s, seg=4, cap=True)
            # 檐椽 (round, lower/inner row), offset half a pitch
            t2 = t + 1.0 / n_raf
            if -1.0 <= t2 <= 1.0:
                p2, T2, O2 = surf.eave(side, t2)
                a2 = p2 + O2 * (-0.130 * s) + Vector((0.0, 0.0, -0.262 * s))
                b2 = p2 + O2 * (-0.620 * s) + Vector((0.0, 0.0, -0.150 * s))
                wood.tube(a2, b2, 0.042 * s, seg=7, cap=True)

    # 斗拱 clusters (or a plain 斗row on the lower roof)
    y_cl = -0.440 * s
    z_top = -0.382 * s
    if tiers >= 1:
        for side in ("F", "B", "R", "L"):
            half = surf.hw if side in "FB" else surf.hd
            n = max(2, int(round(2.0 * half / (spacing * s))))
            for i in range(n + 1):
                t = -1.0 + 2.0 * i / n
                # the corner owns a diagonal 角科; a normal cluster there would
                # cross its 昂 with the neighbouring side's cluster
                if abs(t) > 0.97:
                    continue
                p, T, O = surf.eave(side, t)
                z0 = p.z + z_top - CL_H * s
                M = _frame((p.x + O.x * y_cl, p.y + O.y * y_cl, z0), T, O)
                _dougong(brack, gold, teal, M, tiers=tiers, s=s)
        # 角科已删除：在翼角起翘区，斜角斗拱的昂与耍头会穿出瓦面，
        # 从俯视/斜上方看就是两个悬在屋面上的小木块（用户标注的「多余物件」）。
        # 两侧常规斗拱在角部本来就已收头，去掉角科后屋面干净且左右对称。
    else:
        for side in ("F", "B", "R", "L"):
            half = surf.hw if side in "FB" else surf.hd
            n = max(2, int(round(2.0 * half / (0.60 * s))))
            for i in range(n + 1):
                t = -1.0 + 2.0 * i / n
                p, T, O = surf.eave(side, t)
                z0 = p.z + z_top - 0.13 * s
                M = _frame((p.x + O.x * y_cl, p.y + O.y * y_cl, z0), T, O)
                wood.box(M, (0.0, 0.0, 0.065 * s),
                         (0.19 * s, 0.19 * s, 0.13 * s))
                gold.box(M, (0.0, 0.035 * s, 0.100 * s),
                         (0.175 * s, 0.10 * s, 0.014 * s))

    for geo, mat, suffix in ((wood, m_wood, "Wood"),
                             (brack, G.P("wood_m"), "Brack"),
                             (beam, G.P("wood_d") if "wood_d" in G.PALETTE
                              else G.P("wood"), "Beam"),
                             (gold, m_gold, "Gold"), (teal, m_teal, "Teal"),
                             (pale, m_pale, "Wakou")):
        ob = geo.obj("%s_%s" % (name, suffix), col, mat)
        if ob is not None:
            obs.append(ob)
    return obs


# ------------------------------------------------------------------ gables
def _bargeboard(name, line, col, drop=0.17, thick=0.09):
    verts, faces = [], []
    for p in line:
        verts.append((p[0], p[1], p[2]))
        verts.append((p[0], p[1], p[2] - drop))
    for k in range(len(line) - 1):
        a = k * 2
        faces.append((a, a + 1, a + 3, a + 2))
    return G.add_mesh(name, verts, faces, col, G.P("wood_l"))


def build_gable_end(surf, sx, col):
    x = sx * (surf.hw - surf.g)
    y_s = 0.53
    obs = []
    prof = []
    n = 18
    for k in range(n + 1):
        v = -y_s + 2.0 * y_s * k / n
        p = surf.point(surf.ug * sx, v)
        prof.append((p.x, p.y, p.z))
    z0 = surf.point(surf.ug * sx, -y_s).z
    z1 = surf.point(surf.ug * sx, y_s).z
    verts = [(x, -y_s * surf.hd + surf.cy, z0)] + prof + \
            [(x, y_s * surf.hd + surf.cy, z1)]
    faces = [(0, 1 + k, 2 + k) for k in range(len(verts) - 2)]
    obs.append(G.add_mesh("ROOF_Gable%d" % sx, verts, faces, col,
                          G.P("plaster")))

    apex = (x, surf.cy, surf.ridge_z - 0.10)
    bl = (x, -y_s * surf.hd + 0.30 + surf.cy, z0 + 0.12)
    br = (x, y_s * surf.hd - 0.30 + surf.cy, z1 + 0.12)
    cx = (bl[0] + br[0] + apex[0]) / 3.0
    cy = (bl[1] + br[1] + apex[1]) / 3.0
    cz = (bl[2] + br[2] + apex[2]) / 3.0
    tri = [(cx + (p[0] - cx) * 0.64 + sx * 0.05,
            cy + (p[1] - cy) * 0.64,
            cz + (p[2] - cz) * 0.64) for p in (bl, br, apex)]
    obs.append(G.add_mesh("ROOF_GablePanel%d" % sx, tri, [(0, 1, 2)], col,
                          G.P("wood")))
    for sign in (-1, 1):
        line = []
        for k in range(n + 1):
            v = sign * (y_s - 2.0 * y_s * k / n)
            p = surf.point(surf.ug * sx, v)
            line.append((p.x + sx * 0.09, p.y, p.z + 0.01))
        obs.append(_bargeboard("ROOF_GableTrim%d%d" % (sx, sign), line, col,
                               drop=0.07, thick=0.05))
        line = []
        for k in range(n + 1):
            v = sign * (y_s - 2.0 * y_s * k / n)
            p = surf.point(surf.ug * sx, v)
            line.append((p.x + sx * 0.05, p.y, p.z + 0.02))
        obs.append(_bargeboard("ROOF_Barge%d%d" % (sx, sign), line, col))
    obs.append(G.add_cone("ROOF_Xuanyu%d" % sx, 0.14, 0.015, 0.52,
                          (x + sx * 0.10, surf.cy, surf.ridge_z - 0.42), col,
                          G.P("gold"), segments=10, rot=(math.pi, 0, 0)))
    obs.append(G.add_cyl("ROOF_XuanyuCap%d" % sx, 0.11, 0.06,
                         (x + sx * 0.10, surf.cy, surf.ridge_z - 0.14), col,
                         G.P("gold"), segments=10))
    return obs


# ------------------------------------------------------------------ builds
def build_main_roof(col, name="ROOF_MAIN"):
    surf = _main_surface()
    obs = []
    obs.append(shell(name + "Slab", surf, col, G.P("tile_d"), nu=78, nv=68,
                     thickness=0.17))
    obs.append(tiles("TILE_Tongwa", surf, col, G.P("tile")))
    rx = surf.hw - surf.g
    obs.extend(swept_ridge(name + "Ridge",
                           [(-rx, surf.cy, surf.ridge_z + 0.02),
                            (0.0, surf.cy, surf.ridge_z + 0.10),
                            (rx, surf.cy, surf.ridge_z + 0.02)],
                           col, G.P("tile"), width=0.44, height=0.30,
                           layers=3))
    obs.append(chiwen(name + "ChiwenL", (-rx - 0.12, surf.cy, surf.ridge_z + 0.16),
                      col, G.P("tile"), facing=1.0, scale=1.0))
    obs.append(chiwen(name + "ChiwenR", (rx + 0.12, surf.cy, surf.ridge_z + 0.16),
                      col, G.P("tile"), facing=-1.0, scale=1.0))
    # 戗脊 from the gable foot down to the lifted plan corner
    for sx in (-1, 1):
        for sy in (-1, 1):
            pts = []
            n = 8
            for s in range(n + 1):
                f = s / float(n)
                u = surf.ug + (1.0 - surf.ug) * f
                v = sy * (0.53 + (1.0 - 0.53) * f)
                p = surf.point(u * sx, v)
                pts.append((p.x, p.y, p.z + 0.05))
            obs.extend(swept_ridge("%sHip_%d%d" % (name, sx, sy), pts, col,
                                   G.P("tile_d"), width=0.28, height=0.20,
                                   layers=3, taper=0.18))
    for sx in (-1, 1):
        obs.extend(build_gable_end(surf, sx, col))
    obs.extend(eave_assembly(name + "Eave", surf, col,
                             (G.P("wood_l"), G.P("gold"), G.P("chap"),
                              G.P("plaster_d")), tiers=3, spacing=0.48,
                             scale=1.0))
    return G.join_objs(name, obs)


def build_skirt_roof(col, name="ROOF_SKIRT"):
    surf = _skirt_surface()
    hut = (G.BW / (G.BW + 2 * G.SKIRT_OV), G.BD / (G.BD + 2 * G.SKIRT_OV))
    obs = [shell(name + "Slab", surf, col, G.P("tile_d"), nu=66, nv=66,
                 thickness=0.18, hole=hut)]
    obs.append(tiles("TILE_SkirtTongwa", surf, col, G.P("tile"),
                     spacing=0.27, radius=0.088))
    obs.extend(eave_assembly(name + "Eave", surf, col,
                             (G.P("wood_l"), G.P("gold"), G.P("chap"),
                              G.P("plaster_d")), tiers=0, spacing=0.58,
                             scale=0.86))
    return G.join_objs(name, obs)


def build(col_roof):
    build_skirt_roof(col_roof)
    build_main_roof(col_roof)
    return G.LOG