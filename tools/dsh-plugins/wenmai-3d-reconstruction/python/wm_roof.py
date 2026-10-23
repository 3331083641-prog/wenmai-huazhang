"""Chinese hipped-roof generator (params: docs/CONTRACT.md section 4B).

Styles
------
``hip``          ​庑殿: four slopes, a real ridge of length 2 * ``ridgeHalf``.
``xieshan``      ​歇山: front/back slopes plus 撒头 end slopes and 山花 gables
                 set in by ``gableInset`` (收山).
``gable``        ​悬山: two slopes only, full-depth vertical gable ends.
``double-eave``  ​重檐: a lower skirt roof at ``eaveZ`` plus the main roof whose
                 eave sits ``mainEaveFactor`` of the rise higher, which is how
                 the v5 build stacks 腰檐 (6.15) and 主檐 (7.95).

Tile courses
------------
Courses are lines of constant parameter (``u`` for the front/back slopes, ``v``
for the end slopes), i.e. they run **straight down the slope, parallel to each
other**, never radially around the plan centre. Each course is real geometry:
a continuous curved pan ribbon (板瓦) with a sawtooth lap line at every tile
joint, plus overlapping curved 筒瓦 ribs on the course centreline, plus a 瓦当
round tile at every rib foot and a 滴水 drip tile at every pan foot. Courses are
clipped exactly at the 戗脊 (hip) line, which is why the corner runs get shorter
instead of leaving the slope.

The plan follows the proven v5 parameterisation (``gal5.apex_z`` + the
``mod_roof.Surface`` eave field): ``s = min(|u|, |v|)`` is 0 at mid-side and 1 at
the plan corner, so one ``s ** liftPower`` term gives the continuous concave
生起 curve, a Gaussian 起翘 kick lifts the very corner, and the plan flare (出翘)
makes the corner read as a wing rather than a tilted rectangle.
"""
from __future__ import annotations

import json
import math

import bpy
from mathutils import Matrix, Vector

import wm_common as WC
import wm_mesh as M

# --------------------------------------------------------------------- defaults
DEFAULTS = {
    "style": "hip",
    "footprintX": 8.4,
    "footprintY": 7.5,
    "eaveZ": 6.15,
    "ridgeZ": 11.3,
    "overhang": 1.55,
    "cornerLift": 0.55,
    "slopePower": 1.75,
    "ridgeHalf": 1.35,
    "tileRows": 28,
    "tileCover": 1.35,
    "tileSegments": 26,
    "tileThickness": 0.045,
    "ridgeOrnament": True,
    "detail": "medium",
    "hallY": -0.55,          # v5 building centre (front is +Y in the shipped blend)
    "gableInset": 1.28,      # 收山, used by xieshan
    "dougong": True,
    "rafterSpacing": 0.42,
    "lap": 0.22,             # tile head-lap as a share of the piece length
}

DETAIL = {
    "low":    {"slab": (30, 26), "samples": 0.55, "raft": 0.55, "tiers": 1,
               "dougong": 1.35, "seg_cap": 12},
    "medium": {"slab": (38, 32), "samples": 0.80, "raft": 1.35, "tiers": 2,
               "dougong": 1.05, "seg_cap": 20},
    "high":   {"slab": (66, 56), "samples": 1.20, "raft": 1.00, "tiers": 3,
               "dougong": 0.70, "seg_cap": 30},
}

RIDGE_W = 0.44
RIDGE_H = 0.26
HIP_W = 0.28
HIP_H = 0.19


def _num(params, key):
    return WC.safe_float(params.get(key), DEFAULTS[key])


def _detail(params):
    key = str(params.get("detail") or DEFAULTS["detail"]).lower()
    return DETAIL.get(key, DETAIL["medium"]), (key if key in DETAIL else "medium")


# --------------------------------------------------------------------- profile
def profile_k(slope_power: float) -> float:
    """Map the contract's ``slopePower`` onto the proven quadratic 举折 weight.

    ``gal5.apex_z``/``mod_roof`` use ``z(t) = eave + rise * (k t + (1 - k) t^2)``
    with t = 0 at the eave and 1 at the ridge. k = 1 is a straight slope, k -> 0
    is the most concave curve. The v5 main roof uses k = 0.44, and the contract
    default is ``slopePower`` = 1.75, so k = 0.77 / slopePower reproduces the
    shipped silhouette exactly at the default and stays monotone either way.
    """
    return M.clamp(0.77 / max(0.35, float(slope_power)), 0.06, 0.96)


# --------------------------------------------------------------------- surface
class Surface:
    """Roof surface in (u, v) in [-1, 1]; u runs along X, v along Y."""

    def __init__(self, w, d, eave_z, ridge_z, k=0.44, gable=0.0, hip=True,
                 cy=0.0, ridge_half=1.35, lift=0.55, lift_p=2.20, kick=0.16,
                 kick_r=1.0, lift_h=2.8, flare=0.105, flare_p=3.0):
        self.w, self.d = float(w), float(d)
        self.hw, self.hd = self.w * 0.5, self.d * 0.5
        self.eave_z, self.ridge_z, self.k = eave_z, ridge_z, k
        self.gable, self.hip = float(gable), bool(hip)
        self.cy = float(cy)
        self.ridge_half = M.clamp(float(ridge_half), 0.0, self.hw - 0.25)
        # 收山: gable plane set in from the plan edge (non-hip only)
        self.ug = M.clamp(1.0 - 2.0 * self.gable / self.w, 0.0, 0.98) if (self.gable and not hip) else 0.0
        if not hip:
            self.ridge_half = self.hw - self.hd
        self.lift, self.lift_p = float(lift), float(lift_p)
        self.kick, self.kick_r, self.lift_h = float(kick), float(kick_r), float(lift_h)
        self.flare, self.flare_p = float(flare), float(flare_p)
        # hip-plane run lengths: front/back span hd in Y, ends span hw-ridge_half
        self.run_y = max(1e-3, self.hd)
        self.run_x = max(1e-3, self.hw - self.ridge_half) if hip else max(1e-3, self.hw)

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

    # -- height ----------------------------------------------------------
    def apex(self, t):
        t = M.clamp(t, 0.0, 1.0)
        return self.eave_z + (self.ridge_z - self.eave_z) * (
            self.k * t + (1.0 - self.k) * t * t)

    def base(self, u, v):
        ty, tx = self.t_pair(u, v)
        if self.hip:
            return self.apex(min(ty, tx))
        gz = self.apex(1.0 - min(1.0, abs(v)))
        if abs(u) <= self.ug:
            return gz
        y = v * self.hd
        x = u * self.hw
        dist = min(self.hd - abs(y), self.hw - abs(x))
        return min(gz, self.apex(max(0.0, dist / self.hd)))

    def t_pair(self, u, v):
        """Normalised run-up to the ridge measured along each slope family.

        ``ty`` grows walking inward from the front/back eave, ``tx`` walking
        inward from an end eave. The 戗脊 (hip) line is exactly ``ty == tx``,
        which is what lets a course be clipped the moment it leaves its slope.
        """
        ty = (self.hd - abs(v) * self.hd) / self.run_y
        tx = (self.hw - abs(u) * self.hw) / self.run_x
        return ty, tx

    def point(self, u, v):
        X, Y = self.plan(u, v)
        zb = self.base(u, v)
        z = zb
        fade = 1.0 - max(0.0, zb - self.eave_z) / max(1e-6, self.lift_h)
        if fade > 0.0 and (self.lift > 0.0 or self.kick > 0.0):
            fade = min(1.0, fade)
            s = min(abs(u), abs(v))
            rise = self.lift * (s ** self.lift_p)
            dc = math.hypot(self.hw - abs(X), self.hd - abs(Y))
            kick = self.kick * math.exp(-(dc / max(1e-6, self.kick_r)) ** 2)
            z = zb + (rise + kick) * (fade ** 1.35)
        return Vector((X, Y + self.cy, z))

    def normal(self, u, v, eps=0.0015):
        u0, u1 = max(-1.0, u - eps), min(1.0, u + eps)
        v0, v1 = max(-1.0, v - eps), min(1.0, v + eps)
        pu = self.point(u1, v) - self.point(u0, v)
        pv = self.point(u, v1) - self.point(u, v0)
        n = pu.cross(pv)
        if n.length < 1e-9:
            n = Vector((0.0, 0.0, 1.0))
        n.normalize()
        return -n if n.z < 0.0 else n

    def eave(self, side, t):
        """Return ``(point, eave tangent, outward)`` at parameter ``t``."""
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


# ------------------------------------------------------------------ mid-sides
SIDES = ("F", "B", "R", "L")


def _surface(style, p, eave_z, ridge_z):
    """Build the main (or the single) roof surface for a style."""
    w = _num(p, "footprintX") + 2.0 * _num(p, "overhang")
    d = _num(p, "footprintY") + 2.0 * _num(p, "overhang")
    k = profile_k(_num(p, "slopePower"))
    cy = _num(p, "hallY")
    lift = _num(p, "cornerLift")
    rh = _num(p, "ridgeHalf")
    common = dict(k=k, cy=cy, ridge_half=rh, lift=lift, lift_p=2.20,
                  kick=0.16 * (lift / 0.55), lift_h=2.8)
    if style in ("gable", "xieshan"):
        g = _num(p, "gableInset") if style == "xieshan" else 0.0
        return Surface(w, d, eave_z, ridge_z, gable=g, hip=False, **common)
    return Surface(w, d, eave_z, ridge_z, hip=True, **common)


def _skirt_surface(p, eave_z, skirt_in):
    w = _num(p, "footprintX") + 2.0 * 1.38
    d = _num(p, "footprintY") + 2.0 * 1.38
    return Surface(w, d, eave_z, skirt_in, k=0.62, hip=True,
                   cy=_num(p, "hallY"), ridge_half=0.0,
                   lift=0.18, lift_p=2.4, kick=0.06, kick_r=0.9, lift_h=1.05)


# ----------------------------------------------------------------- run records
def _run_records(surf, rows, gable_span_only, stop_rect=None):
    """Enumerate every tile course as an ordered list of (u, v) stations.

    Front/back slopes: constant u, v walking from the eave (|v| = 1) inward.
    End slopes: constant v, u walking from the eave (|u| = 1) inward.
    A run stops at the 戗脊/ridge line so it never leaves its own slope, and at
    ``stop_rect`` = (half_u, half_v) when a course would run into a region that
    is hidden (the skirt roof's hole for the upper storey).

    ``rows`` is the course count across the full plan width, so the centre to
    centre spacing is a constant ``surf.w / rows`` on every slope.
    """
    runs = []
    hw, hd = surf.hw, surf.hd
    rows = max(4, int(rows))
    spacing = surf.w / rows
    # path resolution only (the ribbon is resampled later); it has to be fine
    # enough that a course reaches its 戗脊 line instead of stopping short
    n_step = 30
    n_v = n_step
    su, sv = (stop_rect or (0.0, 0.0))

    def hidden(u, v):
        return su > 0.0 and abs(u) < su and abs(v) < sv
    # ---- front / back slopes (courses spaced along X) -------------------
    if surf.hip:
        u_lo, u_hi = -1.0, 1.0
        n_x = max(2, int(round(2.0 * hw / spacing)))
    else:
        u_lo, u_hi = -surf.ug, surf.ug
        n_x = max(2, int(round(2.0 * surf.ug * hw / spacing)))
    for i in range(n_x + 1):
        u = u_lo + (u_hi - u_lo) * i / n_x
        for sgn in (-1.0, 1.0):
            pts = []
            for k in range(n_v + 1):
                vk = sgn * (1.0 - k / float(n_v))
                pts.append((u, vk))
                if surf.hip:
                    ty, tx = surf.t_pair(u, vk)
                    if ty > tx + 1e-9:            # left the front/back slope
                        break
                elif abs(vk) <= 1e-9:
                    break
                if hidden(u, vk):
                    pts.pop()                     # do not start a run inside the hole
                    break
            if len(pts) >= 2:
                runs.append({"family": "FB", "eave_side": "F" if sgn > 0 else "B",
                             "t": u if sgn > 0 else -u, "uv": pts})
    # ---- end slopes (courses spaced along Y) ----------------------------
    if surf.ug < 0.999:
        n_y = max(2, int(round(2.0 * hd / spacing)))
        n_u = n_step
        for j in range(n_y + 1):
            v = -1.0 + 2.0 * j / n_y
            for sgn in (-1.0, 1.0):
                pts = []
                for k in range(n_u + 1):
                    uk = sgn * (1.0 - k / float(n_u))
                    pts.append((uk, v))
                    if surf.hip:
                        ty, tx = surf.t_pair(uk, v)
                        if tx > ty + 1e-9:        # left the end slope
                            break
                    elif abs(uk) <= surf.ug + 1e-6:
                        break
                    if hidden(uk, v):
                        pts.pop()
                        break
                if len(pts) >= 2:
                    runs.append({"family": "RL",
                                 "eave_side": "R" if sgn > 0 else "L",
                                 "t": -v if sgn > 0 else v, "uv": pts})
    return runs


def _run_len(surf, uv):
    return sum((surf.point(*uv[i + 1]) - surf.point(*uv[i])).length
               for i in range(len(uv) - 1))


# ----------------------------------------------------------------- tile parts
def _ccw(pts):
    area = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        area += x0 * y1 - x1 * y0
    return pts if area >= 0.0 else list(reversed(pts))


def _stations(surf, uv, n_seg, centre_shift, section_fn, offset_fn=None):
    """Frames along a course: ``side = normal x tangent`` (CCW about tangent).

    ``uv`` is resampled to ``n_seg + 1`` stations along its own length, so
    ``tileSegments`` really controls how finely the concave profile is followed.
    """
    path = [_uv_at(uv, i / float(max(1, n_seg))) for i in range(n_seg + 1)]
    path = _dedup(path)
    n = len(path)
    if n < 2:
        return []
    section = _ccw([(float(a), float(b)) for (a, b) in section_fn()])
    out = []
    for i in range(n):
        u, v = path[i]
        p = surf.point(u, v)
        nrm = surf.normal(u, v)
        j0 = max(0, i - 1)
        j1 = min(n - 1, i + 1)
        tan = surf.point(*path[j1]) - surf.point(*path[j0])
        if tan.length < 1e-9:
            continue
        tan.normalize()
        side = nrm.cross(tan).normalized()
        off = offset_fn(i / float(max(1, n - 1))) if offset_fn else 0.0
        c = p + nrm * (centre_shift + off)
        out.append([tuple(c + side * a + nrm * b) for (a, b) in section])
    return out


def _pan_section(half_w, lip, thick):
    """板瓦 cross-section: a thin tray with a raised lip on each side."""
    return lambda: [(-half_w - lip, 0.0), (half_w + lip, 0.0),
                    (half_w + lip, lip), (half_w + lip, lip - thick),
                    (-half_w - lip, lip - thick), (-half_w - lip, lip)]


def _rib_section(radius, base_h, seg=3):
    """筒瓦 cross-section: a half-round cap sitting on the pan.

    The arc endpoints are *not* repeated: a duplicated vertex makes the two
    faces that touch it zero-area (the shipped double-eave build carried 2016
    degenerate faces in TILE_Rib before this was fixed). With ``base_h`` 0 the
    arc feet already lie on the pan floor, so the polygon closes on itself.
    """
    def fn():
        return [(radius * math.cos(math.pi * (1.0 - i / seg)),
                 base_h + radius * math.sin(math.pi * (1.0 - i / seg)))
                for i in range(seg + 1)]
    return fn


def _lap_offset(piece_count, lap):
    """Sawtooth: every tile piece sits a little above the one downhill of it."""
    def fn(s):
        if piece_count <= 1:
            return 0.0
        k = math.floor(s * piece_count + 1e-6)
        return (k / float(piece_count)) * lap
    return fn


def _build_tiles(params, surf, runs, detail, geo_pan, geo_rib, geo_drip):
    """Course geometry; returns (tileCount, wadang list)."""
    spacing = max(0.10, float(surf.w / max(2, int(_num(params, "tileRows")))))
    pieces_nom = max(0.35, _num(params, "tileCover"))
    thick = max(0.012, _num(params, "tileThickness"))
    seg_hint = max(6, int(_num(params, "tileSegments") * detail["samples"]))
    lap = max(0.0, _num(params, "lap"))
    lip = min(0.055, spacing * 0.14)
    # The pan has to cover the full course pitch (plus a small lap) or the bare
    # roof slab shows as a gap between every pair of courses -- which is what
    # reads as "thin ridges floating over a board".
    pan_half = spacing * 0.5 + lip
    radius = min(0.115, spacing * 0.30)
    plate = 0.0
    tile_count = 0
    wadang = []
    for run in runs:
        uv = run["uv"]
        length = _run_len(surf, uv)
        if length < 0.12:
            continue
        # ---- 板瓦 pan: continuous curved ribbon with lap sawtooth --------
        npiece = max(2, int(round(length / pieces_nom)))
        nseg = int(M.clamp(round(length * 1.5 * detail["samples"]), 6,
                           max(8, detail["seg_cap"] - 8)))
        st = _stations(surf, uv, nseg, 0.010,
                       _pan_section(pan_half, lip, thick),
                       _lap_offset(npiece, 0.014))
        geo_pan.sweep(st, caps=True)
        # ---- 筒瓦 ribs: overlapping curved boxes on the centreline ------
        for k in range(npiece):
            a = max(0.0, (k - lap) / float(npiece))
            b = (k + 1.0) / float(npiece)
            seg = _dedup([_uv_at(uv, a + (b - a) * s / 4.0) for s in range(5)])
            if len(seg) < 2:
                continue
            st = _stations(surf, seg, 3, lip + 0.012,
                           _rib_section(radius, 0.0))
            if len(st) >= 2:
                geo_rib.sweep(st, caps=True)
        tile_count += npiece
        # ---- 瓦当 + 滴水 at the eave end ---------------------------------
        p0, T, O = surf.eave(run["eave_side"], M.clamp(run["t"], -1.0, 1.0))
        u0, v0 = uv[0]
        nrm = surf.normal(u0, v0)
        cen = surf.point(u0, v0) + nrm * (lip + 0.012 + radius * 0.45) + O * 0.048
        wadang.append((cen, nrm, O))
        _drip(geo_drip, p0, T, O, nrm, spacing + 0.02, thick)
    return tile_count, wadang


def _uv_at(uv, f):
    """Linear interpolation along a (u, v) station list."""
    if f <= 0.0:
        return uv[0]
    if f >= 1.0:
        return uv[-1]
    x = f * (len(uv) - 1)
    i = int(math.floor(x))
    t = x - i
    a, b = uv[i], uv[min(len(uv) - 1, i + 1)]
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _dedup(uv, eps=1e-4):
    out = []
    for p in uv:
        if not out or abs(p[0] - out[-1][0]) > eps or abs(p[1] - out[-1][1]) > eps:
            out.append(p)
    return out


def _drip(geo, p, T, O, nrm, width, thick):
    """滴水: the hanging drip plate at a pan-tile foot."""
    Mx = M.frame(p + O * 0.028 + Vector((0.0, 0.0, -0.030)), T, O)
    geo.box_m(Mx, (0.0, 0.010, 0.0), (width * 0.86, thick * 0.9, 0.075))
    geo.box_m(Mx, (0.0, 0.020, -0.052), (width * 0.62, thick * 0.7, 0.030))


def _build_wadang(geo, items, radius):
    for cen, nrm, out in items:
        geo.disc(cen, nrm, out, radius, 0.030, seg=10)


# --------------------------------------------------------------------- ridges
WIDTH = 0.5


def _swept_ridge(geo, pts, width, height, taper=0.58):
    """Solid trapezoid ridge swept along a 3-D polyline.

    Built with :meth:`wm_mesh.Geo.sweep` (a closed prism with two end caps)
    rather than the hand-written quad set of the v5 module, which left 238
    boundary edges and 66 non-manifold edges in the shipped ROOF_Ridge.
    """
    if len(pts) < 2:
        return 0.0
    path = [Vector(p) for p in pts]
    stations = []
    length = 0.0
    for idx, p in enumerate(path):
        p_prev = path[max(0, idx - 1)]
        p_next = path[min(len(path) - 1, idx + 1)]
        tan = (p_next - p_prev)
        if tan.length < 1e-6:
            tan = Vector((1.0, 0.0, 0.0))
        tan.normalize()
        up = Vector((0.0, 0.0, 1.0))
        side = up.cross(tan).normalized()
        nrm = tan.cross(side).normalized()
        hw, tw = width * 0.5, width * 0.5 * taper
        section = [(-hw, 0.0), (hw, 0.0), (tw, height), (-tw, height)]
        stations.append([tuple(p + side * a + nrm * b) for (a, b) in section])
        if idx:
            length += (path[idx] - path[idx - 1]).length
    geo.sweep(stations, caps=True)
    return length


def _chiwen(geo, origin, scale=1.0, facing=1.0):
    """正吻: a curled fin extruded from a styled profile (proven v5 outline)."""
    prof = [(0.00, 0.00), (0.16, 0.02), (0.34, 0.20), (0.46, 0.52),
            (0.40, 0.78), (0.24, 0.84), (0.14, 0.68), (0.20, 0.50),
            (0.30, 0.40), (0.22, 0.30), (0.05, 0.24)]
    if facing < 0:
        prof = [(-x, y) for (x, y) in reversed(prof)]
    geo.prism_xz(origin, [(x * scale, y * scale) for (x, y) in prof], 0.10 * scale)


def _hip_line(surf, u_end, v_sign, f):
    u = u_end + (1.0 - u_end) * f
    v = v_sign * (1.0 - f)
    return u, v


def _xieshan_line(surf, sx, sy, f):
    u = sx * (surf.ug + (1.0 - surf.ug) * f)
    v = sy * (0.53 + 0.47 * f)
    return u, v


def _build_ridges(params, style, surf, geo_ridge, geo_orn):
    """正脊 + hip/垂脊 + 正吻; returns total ridge length in metres."""
    extra = {"ridgeLen": 0.0}
    orn = bool(params.get("ridgeOrnament", DEFAULTS["ridgeOrnament"]))
    if style == "gable":
        # 悬山: a full-width 正脊 plus a 垂脊/博风 along each gable edge
        pts = [(-surf.hw, surf.cy, surf.ridge_z + 0.02),
               (0.0, surf.cy, surf.ridge_z + 0.10),
               (surf.hw, surf.cy, surf.ridge_z + 0.02)]
        extra["ridgeLen"] += _swept_ridge(geo_ridge, pts, RIDGE_W, RIDGE_H)
        for sx in (-1, 1):
            line = [surf.point(sx * 1.0, -1.0 + 2.0 * i / 10.0) for i in range(11)]
            line = [tuple(p + Vector((0.0, 0.0, 0.04))) for p in line]
            extra["ridgeLen"] += _swept_ridge(geo_ridge, line, 0.24, 0.16, taper=0.5)
            if orn:
                top = surf.point(sx * 1.0, 0.0)
                _chiwen(geo_orn, (top.x + sx * 0.05, surf.cy, surf.ridge_z + 0.06),
                        0.9, facing=sx)
        return extra
    if style == "xieshan":
        rx = surf.hw - surf.gable
        pts = [(-rx, surf.cy, surf.ridge_z + 0.02),
               (0.0, surf.cy, surf.ridge_z + 0.10),
               (rx, surf.cy, surf.ridge_z + 0.02)]
        extra["ridgeLen"] += _swept_ridge(geo_ridge, pts, RIDGE_W, RIDGE_H)
        for sx in (-1, 1):
            for sy in (-1, 1):
                line = []
                for i in range(9):
                    p = surf.point(*_xieshan_line(surf, sx, sy, i / 8.0))
                    line.append(tuple(p + Vector((0.0, 0.0, 0.05))))
                extra["ridgeLen"] += _swept_ridge(geo_ridge, line, HIP_W, HIP_H, 0.62)
        if orn:
            for sx in (-1, 1):
                _chiwen(geo_orn, (sx * (rx + 0.10), surf.cy, surf.ridge_z + 0.14),
                        1.0, facing=-sx)
        return extra
    # ---- hip (and the main roof of double-eave) --------------------------
    rh = surf.ridge_half
    pts = []
    for i in range(7):
        f = -1.0 + 2.0 * i / 6.0
        pts.append((rh * f, surf.cy, surf.ridge_z + 0.02 + 0.08 * (1.0 - abs(f))))
    extra["ridgeLen"] += _swept_ridge(geo_ridge, pts, RIDGE_W, RIDGE_H)
    u_end = rh / surf.hw
    for sx in (-1, 1):
        for sy in (-1, 1):
            line = []
            for i in range(9):
                p = surf.point(*_hip_line(surf, sx * u_end, sy, i / 8.0))
                line.append(tuple(p + Vector((0.0, 0.0, 0.05))))
            extra["ridgeLen"] += _swept_ridge(geo_ridge, line, HIP_W, HIP_H, 0.62)
    if orn:
        for sx in (-1, 1):
            _chiwen(geo_orn, (sx * (rh + 0.10), surf.cy, surf.ridge_z + 0.14),
                    1.0, facing=-sx)
    return extra


# ------------------------------------------------------------------ gable ends
def _gable_end(surf, sx, geo_wall, geo_trim, orn_geo, y_s, style):
    """山花/博风板 at one end; ``y_s`` is the covered share of the half depth.

    The gable plane sits at ``u = ug`` for a 歇山 (收山 set-in) and at the plan
    edge ``u = 1`` for a 悬山, where the whole end is a vertical wall.
    """
    u_g = surf.ug if style == "xieshan" else 1.0
    edge = surf.point(u_g * sx, 0.0)
    x = edge.x
    n = 16
    prof = []
    for k in range(n + 1):
        v = -y_s + 2.0 * y_s * k / n
        prof.append(surf.point(u_g * sx, v))
    z0 = prof[0].z
    z1 = prof[-1].z
    y0 = prof[0].y
    y1 = prof[-1].y
    poly = [(y0, min(z0, z1) - 0.16)] + [(p.y, p.z) for p in prof] + [(y1, min(z0, z1) - 0.16)]
    # solid extruded panel in the (y, z) plane
    thick = 0.14
    verts, faces = [], []
    for xo in (x - thick * 0.5, x + thick * 0.5):
        for (py, pz) in poly:
            verts.append((xo, py, pz))
    m = len(poly)
    for i in range(m):
        j = (i + 1) % m
        faces.append((i, j, m + j, m + i))
    faces.append(tuple(range(m - 1, -1, -1)))
    faces.append(tuple(range(m, 2 * m)))
    geo_wall.add(verts, faces)
    # 博风板 along both sloped edges
    for sign in (-1, 1):
        line = []
        for k in range(n + 1):
            v = sign * (y_s - 2.0 * y_s * k / n)
            p = surf.point(u_g * sx, v)
            line.append(tuple(p + Vector((sx * 0.05, 0.0, 0.02))))
        _swept_ridge(geo_trim, line, 0.16, 0.20, taper=0.42)
    if orn_geo is not None:
        # 悬鱼惹草 hanging at the gable apex
        _ornament_ball(orn_geo, (x + sx * 0.12, surf.cy, surf.ridge_z - 0.34), sx)


def _ornament_ball(geo, origin, sx):
    cx, cy, cz = origin
    rings = [(0.10, 0.0), (0.16, -0.12), (0.12, -0.30), (0.05, -0.46), (0.02, -0.56)]
    pts = [(cx + sx * (r * 0.5), cy, cz + dz) for (r, dz) in rings]
    for i in range(len(pts) - 1):
        _swept_ridge(geo, [pts[i], pts[i + 1]], 0.10, 0.10, taper=0.5)


# ----------------------------------------------------------------- eave stack
def _eave_beam(geo, surf, side, n, y_off, z_off, thick, height):
    """Continuous 瓦口/撩檐枋 following the curved eave line."""
    prev = None
    for i in range(n + 1):
        t = -1.0 + 2.0 * i / n
        p, T, O = surf.eave(side, t)
        if prev is not None:
            pm = (prev[0] + p) * 0.5
            Tm = prev[1] + T
            Om = prev[2] + O
            Mx = M.frame((pm.x + Om.x * y_off, pm.y + Om.y * y_off, pm.z + z_off),
                         Tm, Om)
            seg = max(0.02, (p - prev[0]).length + 0.012)
            geo.box_m(Mx, (0.0, 0.0, 0.0), (seg, thick, height))
        prev = (p, T, O)


def _dougong(geo_wood, geo_gold, Mx, tiers=2, s=1.0):
    """One 斗拱 cluster in its eave frame: 栌斗 + 拱 + 斗 + 昂 + 耍头."""
    geo_wood.box_m(Mx, (0.0, 0.0, 0.040 * s), (0.225 * s, 0.225 * s, 0.080 * s))
    geo_wood.box_m(Mx, (0.0, 0.0, 0.096 * s), (0.180 * s, 0.180 * s, 0.032 * s))
    z = 0.108 * s
    for i in range(max(1, tiers)):
        arm = (0.44 - 0.085 * i) * s
        yoff = 0.014 * i * s
        geo_wood.box_m(Mx, (0.0, yoff, z + 0.026 * s), (arm, 0.058 * s, 0.052 * s))
        for sx in (-1.0, 1.0):
            geo_wood.box_m(Mx, (sx * arm * 0.44, yoff, z + 0.075 * s),
                           (0.072 * s, 0.082 * s, 0.046 * s))
        geo_wood.box_m(Mx, (0.0, yoff, z + 0.073 * s), (0.085 * s, 0.085 * s, 0.044 * s))
        geo_gold.box_m(Mx, (0.0, yoff + 0.030 * s, z + 0.026 * s),
                       (arm * 0.80, 0.006 * s, 0.030 * s))
        z += 0.095 * s
    Ma = Mx @ Matrix.Rotation(math.radians(-18.0), 4, "X")
    geo_wood.box_m(Ma, (0.0, 0.085 * s, z - 0.040 * s), (0.058 * s, 0.21 * s, 0.040 * s))
    geo_gold.box_m(Ma, (0.0, 0.185 * s, z - 0.040 * s), (0.052 * s, 0.020 * s, 0.034 * s))
    geo_wood.box_m(Mx, (0.0, 0.036 * s, z + 0.020 * s), (0.10 * s, 0.15 * s, 0.046 * s))
    geo_gold.box_m(Mx, (0.0, 0.036 * s, z + 0.045 * s), (0.098 * s, 0.148 * s, 0.008 * s))


CL_H = 0.44


def _build_eave(params, surf, detail, geo_wood, geo_beam, geo_bracket,
                geo_gold, geo_pale, tiers=2, scale=1.0):
    """瓦口 + 檐椽 + 飞椽 + 撩檐枋 + 斗拱 band under the eave line."""
    s = scale
    n_seg = 56
    for side in SIDES:
        _eave_beam(geo_pale, surf, side, n_seg, -0.030 * s, -0.055 * s,
                   0.070 * s, 0.078 * s)
        _eave_beam(geo_beam, surf, side, n_seg, -0.520 * s, -0.255 * s,
                   0.160 * s, 0.170 * s)
        _eave_beam(geo_gold, surf, side, n_seg, -0.520 * s, -0.162 * s,
                   0.120 * s, 0.010 * s)
        _eave_beam(geo_bracket, surf, side, n_seg, -0.345 * s, -0.500 * s,
                   0.024 * s, 0.320 * s)
        _eave_beam(geo_wood, surf, side, n_seg, -0.300 * s, -0.205 * s,
                   0.045 * s, 0.310 * s)
    spacing = max(0.24, _num(params, "rafterSpacing") * detail["raft"])
    for side in SIDES:
        half = surf.hw if side in "FB" else surf.hd
        n_raf = max(8, int(round(2.0 * half / (spacing * s))))
        for i in range(n_raf + 1):
            t = -1.0 + 2.0 * i / n_raf
            p, T, O = surf.eave(side, t)
            a = p + O * (-0.010 * s) + Vector((0.0, 0.0, -0.155 * s))
            b = p + O * (-0.500 * s) + Vector((0.0, 0.0, -0.060 * s))
            geo_wood.limb(a, b, 0.036 * s, 0.036 * s, seg=4)
            t2 = t + 1.0 / n_raf
            if -1.0 <= t2 <= 1.0:
                p2, T2, O2 = surf.eave(side, t2)
                a2 = p2 + O2 * (-0.130 * s) + Vector((0.0, 0.0, -0.262 * s))
                b2 = p2 + O2 * (-0.620 * s) + Vector((0.0, 0.0, -0.150 * s))
                geo_wood.limb(a2, b2, 0.042 * s, 0.042 * s, seg=6)
    if tiers < 1:
        return
    y_cl, z_top = -0.440 * s, -0.382 * s
    for side in SIDES:
        half = surf.hw if side in "FB" else surf.hd
        n = max(2, int(round(2.0 * half / (detail.get("dougong", 0.80) * s))))
        for i in range(n + 1):
            t = -1.0 + 2.0 * i / n
            if abs(t) > 0.97:
                continue                      # corner owns the diagonal 角科
            p, T, O = surf.eave(side, t)
            Mx = M.frame((p.x + O.x * y_cl, p.y + O.y * y_cl, p.z + z_top - CL_H * s),
                         T, O)
            _dougong(geo_bracket, geo_gold, Mx, tiers=tiers, s=s)
    for sx in (-1, 1):
        for sy in (-1, 1):
            pv, Tv, Ov = surf.eave("F" if sy > 0 else "B", sx)
            pu, Tu, Ou = surf.eave("R" if sx > 0 else "L", sy)
            p = (pv + pu) * 0.5
            O = Ov + Ou
            T = Tv + Tu
            if T.length < 1e-9 or O.length < 1e-9:
                continue
            Mx = M.frame((p.x + O.normalized().x * y_cl, p.y + O.normalized().y * y_cl,
                          p.z + z_top - CL_H * s), T, O)
            _dougong(geo_bracket, geo_gold, Mx, tiers=tiers, s=s)


# ---------------------------------------------------------------------- checks
def _check_coverage(surf, runs, spacing, gable_span_only):
    """Worst-case plan distance from any point of the tile field to a course."""
    samples = []
    nu, nv = 22, 20
    for j in range(nv + 1):
        v = -1.0 + 2.0 * j / nv
        for i in range(nu + 1):
            u = -1.0 + 2.0 * i / nu
            if gable_span_only and not surf.hip and abs(u) > surf.ug:
                continue
            p = surf.point(u, v)
            samples.append(Vector((p.x, p.y, 0.0)))
    if not samples:
        return 0.0
    centres = []
    for run in runs:
        uv = run["uv"]
        for i in range(41):
            p = surf.point(*_uv_at(uv, i / 40.0))
            centres.append(Vector((p.x, p.y, 0.0)))
    if not centres:
        return 99.0
    worst = 0.0
    for s in samples:
        best = min((s - c).length for c in centres)
        worst = max(worst, best)
    return worst


def _check_parallel(surf, runs):
    """Course travel direction vs the slope axis; detects radial/umbrella rows."""
    devs = []
    for run in runs:
        uv = run["uv"]
        if len(uv) < 4:
            continue
        a, b = surf.point(*uv[0]), surf.point(*uv[-1])
        d = Vector((b.x - a.x, b.y - a.y, 0.0))
        if d.length < 0.15:
            continue
        d.normalize()
        axis = Vector((0.0, 1.0, 0.0)) if run["family"] == "FB" else Vector((1.0, 0.0, 0.0))
        c = abs(d.dot(axis))
        c = M.clamp(c, 0.0, 1.0)
        devs.append(math.degrees(math.acos(c)))
    if not devs:
        return 90.0, 90.0
    devs.sort()
    mean = sum(devs) / len(devs)
    p95 = devs[min(len(devs) - 1, int(0.95 * len(devs)))]
    return mean, p95


# ---------------------------------------------------------------------- build
def _one_roof(params, style, surf, detail, geo):
    """Build one roof body (slab, tiles, ridges, eave stack) into ``geo``."""
    slab_nu, slab_nv = detail["slab"]
    M.surface_shell(geo["slab"], surf, slab_nu, slab_nv, 0.17)
    rows = max(4, int(_num(params, "tileRows")))
    runs = _run_records(surf, rows, gable_span_only=not surf.hip)
    tile_count, wadang = _build_tiles(params, surf, runs, detail,
                                      geo["pan"], geo["rib"], geo["drip"])
    row_pitch = surf.w / rows
    _build_wadang(geo["wadang"], wadang, min(0.115, 0.30 * row_pitch))
    rl = _build_ridges(params, style, surf, geo["ridge"], geo["orn"])
    tiers = detail["tiers"] if params.get("dougong", DEFAULTS["dougong"]) else 0
    _build_eave(params, surf, detail, geo["wood"], geo["beam"], geo["bracket"],
                geo["gold"], geo["pale"], tiers=tiers, scale=1.0)
    if style in ("xieshan", "gable"):
        y_s = 0.53 if style == "xieshan" else 1.0
        for sx in (-1, 1):
            _gable_end(surf, sx, geo["wall"], geo["trim"], geo["orn"], y_s, style)
    return {"tileCount": tile_count, "ridgeLen": rl["ridgeLen"],
            "courseCount": len(runs), "wadang": len(wadang),
            "spacing": surf.w / rows}


def generate_roof(params: dict, ctx: dict) -> dict:
    params = dict(params or {})
    style = str(params.get("style") or DEFAULTS["style"]).lower()
    if style not in ("hip", "xieshan", "gable", "double-eave"):
        style = "hip"
    detail, detail_key = _detail(params)
    info = M.open_base(params, ctx, "roof")
    before = len(bpy.data.objects) + 0
    legacy = M.replace_legacy(params, "roof")
    before += len(legacy)
    warnings = list(info["warnings"])
    checks = []
    col = M.collection(M.PART_COLLECTIONS["roof"])

    eave_z = _num(params, "eaveZ")
    ridge_z = _num(params, "ridgeZ")
    rise = ridge_z - eave_z
    # 重檐: the main eave can be placed explicitly (``mainEaveZ``) or derived
    # from the rise. The v5 build stacks 腰檐 6.15 / 主檐 7.95, which is
    # mainEaveFactor 0.35; the Lead's integration target is ~7.2 -> 0.20.
    if params.get("mainEaveZ") is not None:
        main_eave = WC.safe_float(params.get("mainEaveZ"), eave_z + rise * 0.35)
        main_eave = M.clamp(main_eave, eave_z + 0.4, ridge_z - 0.4)
    else:
        main_eave = eave_z + rise * M.clamp(
            WC.safe_float(params.get("mainEaveFactor"), 0.35), 0.10, 0.7)
    style_main = "hip" if style == "double-eave" else style
    surf = _surface(style_main, params, eave_z if style != "double-eave" else main_eave,
                    ridge_z)
    geo = {k: M.Geo() for k in ("slab", "pan", "rib", "drip", "wadang", "ridge",
                                "orn", "wood", "beam", "bracket", "gold",
                                "pale", "wall", "trim")}
    stats = _one_roof(params, style_main, surf, detail, geo)
    objs = []

    def emit(name, key, mat, comp, smooth=False):
        ob = M.finish(geo[key], name, "roof", comp, mat, col, params, smooth=smooth)
        if ob is not None:
            objs.append(ob)

    emit("ROOF_Slab", "slab", "roof_slate", "roof_slab", smooth=True)
    emit("TILE_Pan", "pan", "roof_tile", "roof_pan", smooth=True)
    emit("TILE_Rib", "rib", "roof_tile_b", "roof_rib", smooth=True)
    emit("TILE_Dishui", "drip", "roof_tile", "roof_dishui")
    emit("TILE_Wadang", "wadang", "roof_tile", "roof_wadang")
    emit("ROOF_Ridge", "ridge", "roof_ridge", "roof_ridge", smooth=True)
    emit("ROOF_Ornament", "orn", "roof_ridge", "roof_chiwen")
    emit("ROOF_Rafter", "wood", "timber", "roof_rafter")
    emit("BEAM_Eave", "beam", "timber_dark", "roof_eave_beam")
    emit("ROOF_Bracket", "bracket", "timber_warm", "roof_dougong")
    emit("ROOF_Gold", "gold", "gold", "roof_gold")
    emit("ROOF_Wakou", "pale", "wall_shadow", "roof_wakou")
    emit("ROOF_Gable", "wall", "wall", "roof_gable")
    emit("ROOF_Barge", "trim", "wood_light", "roof_barge")

    # ---- lower skirt roof (重檐) -----------------------------------------
    skirt_span = None
    if style == "double-eave":
        skirt = _skirt_surface(params, eave_z, main_eave - 0.55)
        gw = M.Geo()
        hut = (_num(params, "footprintX") / skirt.w, _num(params, "footprintY") / skirt.d)
        # four closed ring strips instead of one slab with a cut hole: a cut
        # hole leaves an open rim (boundary edges), a ring of strips does not
        snu = max(20, detail["slab"][0] // 2)
        snv = max(18, detail["slab"][1] // 2)
        for strip in ((-1.0, 1.0, -1.0, -hut[1]), (-1.0, 1.0, hut[1], 1.0),
                      (-1.0, -hut[0], -hut[1], hut[1]), (hut[0], 1.0, -hut[1], hut[1])):
            M.surface_shell(gw, skirt, snu, snv, 0.18, strip=strip)
        ob = M.finish(gw, "ROOF_Skirt_Slab", "roof", "skirt_slab", "roof_slate",
                      col, params, smooth=True)
        if ob:
            objs.append(ob)
        pan, rib, drip, wad = M.Geo(), M.Geo(), M.Geo(), M.Geo()
        # stop the skirt courses at the hole for the upper storey: the hidden
        # middle is ~50% of the skirt tile field and contributes nothing
        sruns = _run_records(skirt, max(4, int(_num(params, "tileRows"))), False,
                             stop_rect=hut)
        tc, wd = _build_tiles(params, skirt, sruns, detail, pan, rib, drip)
        _build_wadang(wad, wd, min(0.095, 0.26 * (skirt.w / max(2, int(_num(params, "tileRows"))))))
        stats = dict(stats)
        stats["tileCount"] += tc
        stats["wadang"] += len(wd)
        skirt_span = (skirt.w, skirt.d)
        for nm, g, mat, comp, sm in (("TILE_Skirt_Pan", pan, "roof_tile", "skirt_pan", True),
                                     ("TILE_Skirt_Rib", rib, "roof_tile_b", "skirt_rib", True),
                                     ("TILE_Skirt_Dishui", drip, "roof_tile", "skirt_dishui", False),
                                     ("TILE_Skirt_Wadang", wad, "roof_tile", "skirt_wadang", False)):
            ob = M.finish(g, nm, "roof", comp, mat, col, params, smooth=sm)
            if ob:
                objs.append(ob)
        ew, eb, ebk, eg, ep = (M.Geo() for _ in range(5))
        _build_eave(params, skirt, detail, ew, eb, ebk, eg, ep, tiers=0, scale=0.86)
        for nm, g, mat, comp in (("ROOF_Skirt_Rafter", ew, "timber", "skirt_rafter"),
                                 ("BEAM_Skirt_Eave", eb, "timber_dark", "skirt_beam"),
                                 ("ROOF_Skirt_Bracket", ebk, "timber_warm", "skirt_bracket"),
                                 ("ROOF_Skirt_Gold", eg, "gold", "skirt_gold"),
                                 ("ROOF_Skirt_Wakou", ep, "wall_shadow", "skirt_wakou")):
            ob = M.finish(g, nm, "roof", comp, mat, col, params)
            if ob:
                objs.append(ob)

    # ---- save ------------------------------------------------------------
    out = M.save_out(info["out"])
    arts = [WC.artifact("blend", out)]

    # ---- metrics + checks -------------------------------------------------
    row_count = max(2, int(_num(params, "tileRows")))
    eave_span_x = surf.w
    eave_span_y = surf.d
    height = ridge_z - (eave_z - 0.6)
    tris = M.tri_count(objs)
    rep = M.mesh_report(objs)
    spacing = surf.w / row_count
    worst = _check_coverage(surf, _run_records(surf, row_count, not surf.hip),
                            spacing, not surf.hip)
    pmean, pp95 = _check_parallel(surf, _run_records(surf, row_count, not surf.hip))
    corner = surf.point(1.0, 1.0)
    mid = surf.point(0.0, 1.0)
    concave = surf.apex(0.5) < (surf.eave_z + surf.ridge_z) * 0.5
    budget = int(params.get("triangleBudget") or
                 (110000 if style == "double-eave" else 60000))

    WC.check(checks, "roof_style", "pass",
             f"style={style} detail={detail_key} rows={row_count} courses={stats['courseCount']}")
    WC.check(checks, "roof_tiles_present",
             "pass" if stats["tileCount"] > 0 else "fail",
             f"tileCount={stats['tileCount']} wadang={stats['wadang']} objects={len(objs)}")
    WC.check(checks, "roof_courses_parallel",
             "pass" if pmean <= 6.0 and pp95 <= 14.0 else ("warn" if pmean <= 12.0 else "fail"),
             f"course travel vs slope axis: mean={pmean:.2f}deg p95={pp95:.2f}deg "
             f"(radial rows would read ~45deg)")
    WC.check(checks, "roof_slope_coverage",
             "pass" if worst <= spacing * 0.75 else "warn",
             f"worst plan gap from a sample to a course centreline={worst:.3f}m "
             f"(course spacing {spacing:.3f}m)")
    WC.check(checks, "roof_watertight_slopes",
             "pass" if rep["boundaryEdges"] == 0 else "warn",
             f"boundaryEdges={rep['boundaryEdges']} nonManifold={rep['nonManifoldEdges']} "
             f"degenerate={rep['degenerateFaces']}")
    WC.check(checks, "roof_no_degenerate_faces",
             "pass" if rep["degenerateFaces"] == 0 else "fail",
             f"degenerateFaces={rep['degenerateFaces']} of {rep['faces']} faces")
    WC.check(checks, "roof_corner_lift",
             "pass" if corner.z - mid.z > 0.5 * _num(params, "cornerLift") else "warn",
             f"corner z={corner.z:.3f} vs mid-eave z={mid.z:.3f} "
             f"(lift {corner.z - mid.z:.3f}m, cornerLift param {_num(params, 'cornerLift'):.3f})")
    WC.check(checks, "roof_concave_profile",
             "pass" if concave else "fail",
             f"slopePower={_num(params, 'slopePower'):.2f} -> k={profile_k(_num(params, 'slopePower')):.3f}; "
             f"mid slope z={surf.apex(0.5):.3f} below the straight line "
             f"{(surf.eave_z + surf.ridge_z) * 0.5:.3f}")
    WC.check(checks, "roof_triangle_budget",
             "pass" if tris <= budget else ("warn" if tris <= budget * 1.5 else "fail"),
             f"triangles={tris} objects={len(objs)}; budget {budget} for {style} at "
             f"detail={detail_key} (a 重檐 carries two whole roofs, hence the "
             f"larger budget than a single {60000}-triangle roof)")
    wall_head = WC.safe_float(params.get("wallHeadZ"), 6.55)
    if style in ("hip", "xieshan", "gable"):
        ok_single = eave_z >= wall_head - 0.02
        WC.check(checks, "roof_eave_vs_wallhead",
                 "pass" if ok_single else "warn",
                 f"single-eave roof: eaveZ={eave_z:.2f} vs wall head {wall_head:.2f}. "
                 + ("eave sits at or above the wall head, so the roof clears the "
                    "upper storey."
                    if ok_single else
                    "an eave below the wall head belongs to the LOWER roof of a "
                    "double-eave hall; either use style=double-eave (lower skirt "
                    "eave at eaveZ, main eave via mainEaveZ, e.g. 7.20) or raise "
                    "eaveZ above the wall head. This run's roof is a valid lower "
                    "eave, it is just not a standalone single-eave roof."))
    if style == "double-eave":
        WC.check(checks, "roof_double_eave",
                 "pass" if main_eave > eave_z + 0.4 else "fail",
                 f"双层重檐: lower skirt eave z={eave_z:.2f} span "
                 f"{skirt_span[0]:.2f}x{skirt_span[1]:.2f}; main roof eave "
                 f"z={main_eave:.2f} (above the {wall_head:.2f} wall head) ridge "
                 f"z={ridge_z:.2f}; upper rise {ridge_z - main_eave:.2f} m")
    WC.check(checks, "roof_ridge_length",
             "pass" if stats["ridgeLen"] > 0.5 else "fail",
             f"ridgeLen={stats['ridgeLen']:.2f}m ridgeHalf={surf.ridge_half:.2f} "
             f"ornament={'yes' if params.get('ridgeOrnament', True) else 'no'}")

    metrics = {
        "tileCount": stats["tileCount"],
        "ridgeLen": round(stats["ridgeLen"], 3),
        "eaveSpanX": round(eave_span_x, 3),
        "eaveSpanY": round(eave_span_y, 3),
        "height": round(height, 3),
        "courseCount": stats["courseCount"],
        "wadangCount": stats["wadang"],
        "triangles": tris,
        "objects": len(objs),
        "faces": rep["faces"],
        "style": style,
        "detail": detail_key,
        "eaveZ": eave_z,
        "ridgeZ": ridge_z,
        "triangleBudget": budget,
        "mainEaveZ": round(main_eave, 3) if style == "double-eave" else eave_z,
    }
    notes = (f"{style} roof: {stats['tileCount']} tile pieces on {stats['courseCount']} "
             f"parallel courses, ridge {stats['ridgeLen']:.1f} m, "
             f"plan {eave_span_x:.2f} x {eave_span_y:.2f} m, eave z={eave_z:.2f} "
             f"ridge z={ridge_z:.2f}, {tris} triangles in {len(objs)} objects. "
             f"Replaced {info['deleted']} tagged + {len(legacy)} legacy roof objects"
             + (f" ({', '.join(legacy[:4])}{'...' if len(legacy) > 4 else ''})"
                if legacy else "")
             + f"; base={info['base'] or 'empty scene'}.")
    result = M.result("generate_roof", ctx, params, objs, arts, metrics, checks,
                      warnings, notes)
    result["metrics"]["slabGrid"] = list(detail["slab"])
    result["metrics"]["legacyReplaced"] = legacy
    result["metrics"]["objectsBeforeReplacement"] = before
    if legacy:
        WC.check(checks, "roof_legacy_replaced", "pass",
                 f"{len(legacy)} untagged v5 roof/attic objects removed "
                 f"({', '.join(sorted(set(n.split('_')[0] for n in legacy)))} prefixes); "
                 f"scene objects {before} -> {len(bpy.data.objects)}")
    # audit what is still above the eave line: any surviving old-roof family is
    # the "pale triangle through the upper slope" defect
    above = M.objects_above(eave_z - 0.02)
    swept = ("INT_ATTIC", "INT_ROOF_BOARD", "INT_RAFTER", "INT_BEAM_SEC",
             "INT_BEAM_RIDGE", "INT_CAISSON", "INT_LANTERN_CAISSON",
             "ROOF_MAIN", "ROOF_SKIRT", "TILE_")
    surviving = {k: v for k, v in above.items() if k in swept}
    WC.check(checks, "roof_no_legacy_above_eave",
             "pass" if not surviving else "fail",
             f"untagged objects above eaveZ={eave_z:.2f} by prefix: "
             f"{json.dumps(above, ensure_ascii=False)}; surviving old-roof families: "
             f"{json.dumps(surviving, ensure_ascii=False) or 'none'}")
    attic = [o for o in bpy.data.objects
             if o.name.startswith(("WALL_Attic", "WALL_HeadBeam"))]
    if attic and style == "double-eave":
        top = max(M.world_bbox(o)[1][2] for o in attic)
        WC.check(checks, "roof_attic_clearance",
                 "pass" if top <= main_eave + 0.02 else "warn",
                 f"legacy shell attic band top z={top:.2f} vs main roof eave "
                 f"z={main_eave:.2f}; keep mainEaveZ at or above {top + 0.05:.2f} "
                 f"(the v5 stack uses 7.95) or the attic band pokes through the "
                 f"upper roof")
    result["metrics"]["aboveEaveByPrefix"] = above
    return result
