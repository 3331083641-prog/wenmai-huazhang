"""《纹脉华章》展馆吉祥物「纹纹」— 卷云灵猫.

  blender.exe --background --python build_mascot.py -- --stage blockout
  blender.exe --background --python build_mascot.py -- --stage final

stage=blockout  : only the primary volumes, for checking proportion/silhouette
stage=final     : full detail + rig + 8 actions + GLB export

Contract:
  height 1.0 m, origin between the feet on the ground (z=0), front faces -Z
  <= 18k triangles, <= 8 materials, no textures
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from mlib import (  # noqa: E402
    MeshBuilder, box, cylinder, ellipsoid, loft, tube_along,
    make_material, reset_scene, export_glb, smoothstep, lerp, TAU,
    object_bounds, scene_bounds, ring_pts, fit_height, tri_count,
)

PROJ = r"D:\wenmai-huazhang"
BLEND_OUT = os.path.join(PROJ, r"assets\mascot\blender\wenmai_mascot_ww.blend")
GLB_OUT = os.path.join(PROJ, r"frontend\public\models\wenmai_mascot_ww.glb")

# ---------------------------------------------------------------- palette --
PAL = {
    "fur":      "#F3E7CF",   # 主体毛色 米白
    "fur_dark": "#D8C6A6",   # 暗部 暖灰
    "red":      "#B5322C",   # 耳内 / 尾尖卷云 / 鼻
    "gold":     "#C9A24B",   # 祥云印描边 / 金链 / 项圈金线
    "teal":     "#2F6F66",   # 祥云填充 / 项圈青绿 / 青花牌纹样
    "iris":     "#3E7F72",   # 青绿虹膜
    "dark":     "#3A2A1C",   # 线稿色：瞳孔 / 眼圈 / 耳缘 / 嘴
    "white":    "#FBF8F2",   # 高光 / 瓷白
}
ROUGH = {"fur": 0.72, "fur_dark": 0.76, "red": 0.55, "gold": 0.34,
         "teal": 0.5, "iris": 0.28, "dark": 0.45, "white": 0.22}
MATS = {}


def mats():
    global MATS
    if MATS:
        try:
            for m in MATS.values():
                m.name
            return MATS
        except ReferenceError:
            MATS = {}
    for k, hx in PAL.items():
        MATS[k] = make_material(f"M_ww_{k}", hx, ROUGH[k],
                                metal=0.85 if k == "gold" else 0.0)
    return MATS


# ------------------------------------------------------------- proportions --
H_TOTAL = 1.00
# head+ears 0.575..1.000 (0.425) : body 0..0.575 (0.575)  ->  1 : 1.35
HEAD_C = Vector((0.0, 0.018, 0.7525))
HEAD_R = Vector((0.207, 0.192, 0.1775))      # 0.575 .. 0.930
HEAD_TOP = HEAD_C.z + HEAD_R.z
EAR_TIP_Z = 1.000
EYE_R = 0.058
EYE_C = Vector((0.084, 0.163, 0.768))
NECK_Z = 0.575

# torso: a round egg with a short neck stub so the head does not pinch off
TORSO_PROF = [
    (0.150, 0.052), (0.175, 0.104), (0.212, 0.140), (0.262, 0.160),
    (0.320, 0.168), (0.380, 0.166), (0.440, 0.156), (0.495, 0.138),
    (0.545, 0.112), (0.585, 0.078), (0.610, 0.048),
]
LEG_X, LEG_FRONT_Y, LEG_BACK_Y = 0.088, 0.060, -0.056
PAW_Z = 0.034


def ear_geo(sgn, tip_z=EAR_TIP_Z, base_r=(0.088, 0.032), n=10, rings=6):
    """Flattened cat ear: a big elliptical cone leaning outward."""
    base = Vector((sgn * 0.095, 0.026, 0.845))
    tip = Vector((sgn * 0.206, 0.012, tip_z))
    out = []
    for k in range(rings + 1):
        t = k / rings
        c = base + (tip - base) * t
        # stay wide most of the way up, then taper fast -> a proper ear blade
        k2 = max(0.0, 1.0 - t) ** 0.85
        rx = max(base_r[0] * k2, 0.004)
        ry = max(base_r[1] * k2, 0.004)
        out.append([(c.x + math.cos(TAU * i / n) * rx,
                     c.y + math.sin(TAU * i / n) * ry, c.z) for i in range(n)])
    return loft(out)


# --------------------------------------------------------------- blockout --
def build_blockout():
    """Primary volumes only: judge proportion and silhouette first."""
    reset_scene()
    m = mats()
    mb = MeshBuilder("WW_body")

    # torso
    rings = []
    for z, r in TORSO_PROF:
        rings.append(ring_pts((0, 0, 0), r, r * 0.92, n=18, z=z))
    mb.add(loft(rings), m["fur"], smooth=True)

    # head
    mb.add(ellipsoid(tuple(HEAD_C), tuple(HEAD_R), nu=22, nv=15),
           m["fur"], smooth=True)

    # ears
    for sgn in (-1, 1):
        mb.add(ear_geo(sgn), m["fur"], smooth=True)

    # muzzle: sits BELOW the eye line, blending into the head
    mb.add(ellipsoid((0, 0.196, 0.702), (0.064, 0.046, 0.040), nu=16, nv=11),
           m["fur"], smooth=True)
    # cheeks widen the lower face so it is not a bare sphere
    for sgn in (-1, 1):
        mb.add(ellipsoid((sgn * 0.104, 0.130, 0.714), (0.078, 0.074, 0.062),
                         nu=14, nv=10), m["fur"], smooth=True)

    # eyes: round, well separated
    for sgn in (-1, 1):
        mb.add(ellipsoid((sgn * EYE_C.x, EYE_C.y, EYE_C.z),
                         (EYE_R, EYE_R * 0.66, EYE_R), nu=16, nv=11),
               m["dark"], smooth=True)

    # legs + paws (legs must read as separate volumes below the torso)
    for sgn in (-1, 1):
        for y, x in ((LEG_FRONT_Y, LEG_X), (LEG_BACK_Y, LEG_X + 0.012)):
            mb.add(cylinder((sgn * x, y, 0.230), (sgn * x, y + 0.008, 0.052),
                            0.050, 0.044, n=9), m["fur"], smooth=True)
            mb.add(ellipsoid((sgn * x, y + 0.016, PAW_Z),
                             (0.060, 0.080, 0.034), nu=14, nv=9),
                   m["fur"], smooth=True)

    # tail
    pts, radii = tail_path()
    mb.add(tube_along(pts, radii, n=9), m["fur"], smooth=True)

    ob = mb.build()
    lo, hi = object_bounds(ob)
    tris = tri_count(ob)
    print(f"[blockout] tris={tris} size={hi.x-lo.x:.3f} x {hi.y-lo.y:.3f} x {hi.z-lo.z:.3f}")
    print(f"[blockout] z {lo.z:.4f}..{hi.z:.4f}")
    return ob


# -------------------------------------------------------------------- tail --
def tail_path(turns=1.15, sp_n=28, smooth_passes=4, smooth_alpha=0.4):
    """Rump -> arc out to the side -> 卷云 spiral, as ONE relaxed polyline.

    The coil is swept out past the hip and its plane faces front-right, so the
    spiral reads as a silhouette cue from the front and the 3/4 view.  Parked
    straight behind the body it was only visible edge-on.
    """
    arc = [(0.030, -0.110, 0.292),
           (0.072, -0.170, 0.322),
           (0.126, -0.196, 0.374),
           (0.172, -0.196, 0.442),
           (0.196, -0.184, 0.512)]
    arc_r = [0.064, 0.057, 0.051, 0.046, 0.042]

    cx, cy, cz = 0.214, -0.166, 0.596
    r0, r1 = 0.078, 0.019
    ux, uy = -0.83, 0.55            # in-plane horizontal axis
    sp_pts, sp_r = [], []
    for i in range(sp_n + 1):
        t = i / sp_n
        a = math.radians(268.0) + TAU * turns * t     # entry at the bottom
        r = lerp(r0, r1, t ** 0.82)
        ca, sa = math.cos(a), math.sin(a)
        sp_pts.append((cx + r * ca * ux, cy + r * ca * uy, cz + r * sa))
        sp_r.append(lerp(0.042, 0.010, t ** 0.75))

    pts = arc + sp_pts
    radii = arc_r + sp_r
    for _ in range(smooth_passes):
        new = [pts[0]]
        for i in range(1, len(pts) - 1):
            px, py, pz = pts[i]
            ax, ay, az = pts[i - 1]
            bx, by, bz = pts[i + 1]
            mx, my, mz = (ax + bx) * 0.5, (ay + by) * 0.5, (az + bz) * 0.5
            new.append((px + (mx - px) * smooth_alpha,
                        py + (my - py) * smooth_alpha,
                        pz + (mz - pz) * smooth_alpha))
        new.append(pts[-1])
        pts = new
    return pts, radii


# -------------------------------------------------------------------- main --
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="final", choices=["blockout", "final"])
    args = ap.parse_args(argv)

    mats()
    if args.stage == "blockout":
        build_blockout()
    else:
        build_final()

    os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)
    blend = BLEND_OUT if args.stage == "final" else \
        os.path.join(os.path.dirname(BLEND_OUT), "wenmai_mascot_ww_blockout.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    print(f"[blend] {blend}")

    if args.stage == "final":
        os.makedirs(os.path.dirname(GLB_OUT), exist_ok=True)
        export_glb(GLB_OUT)
        size = os.path.getsize(GLB_OUT)
        print(f"[glb] {GLB_OUT}  {size} bytes  ({size / 1024 / 1024:.2f} MB)")
        if size > 3 * 1024 * 1024:
            raise RuntimeError(f"GLB exceeds the 3 MB budget ({size} bytes)")


def head_surface(x, z, out=0.0):
    """Point on the FRONT of the head ellipsoid at the given x/z, pushed out."""
    t = 1.0 - (x / HEAD_R.x) ** 2 - ((z - HEAD_C.z) / HEAD_R.z) ** 2
    t = max(t, 0.0)
    return Vector((x, HEAD_C.y + (HEAD_R.y + out) * math.sqrt(t), z))


def ribbon_on_head(mb, pts2d, width, out, mat, closed=False):
    """Lay a flat ribbon on the forehead following a 2D (x,z) centreline."""
    left, right = [], []
    n = len(pts2d)
    for i in range(n):
        x, z = pts2d[i]
        j0 = max(0, i - 1)
        j1 = min(n - 1, i + 1)
        dx = pts2d[j1][0] - pts2d[j0][0]
        dz = pts2d[j1][1] - pts2d[j0][1]
        L = math.hypot(dx, dz) or 1.0
        nx, nz = -dz / L, dx / L
        for lst, s in ((left, 1.0), (right, -1.0)):
            px, pz = x + nx * width * 0.5 * s, z + nz * width * 0.5 * s
            lst.append(tuple(head_surface(px, pz, out)))
    verts = left + right
    faces = []
    for i in range(n - 1):
        faces.append((i, i + 1, n + i + 1, n + i))
    mb.add((verts, faces), mat, smooth=False)


def sphere_cap(center, r, theta_max, thick=0.006, n=14, rings=3):
    """A hollow spherical cap (used as the eyelid)."""
    cx, cy, cz = center
    outer, inner = [], []
    for j in range(rings + 1):
        phi = theta_max * j / rings
        sp, cp = math.sin(phi), math.cos(phi)
        for i in range(n):
            th = TAU * i / n
            outer.append((cx + r * sp * math.cos(th), cy + r * sp * math.sin(th),
                          cz + r * cp))
            r2 = r - thick
            inner.append((cx + r2 * sp * math.cos(th), cy + r2 * sp * math.sin(th),
                          cz + r2 * cp))
    verts = outer + inner
    faces = []
    for j in range(rings):
        for i in range(n):
            a = j * n + i
            b = j * n + (i + 1) % n
            c = (j + 1) * n + (i + 1) % n
            d = (j + 1) * n + i
            faces.append((a, b, c, d))
            faces.append((len(outer) + a, len(outer) + d,
                          len(outer) + c, len(outer) + b))
    # rim
    o = rings * n
    for i in range(n):
        a = o + i
        b = o + (i + 1) % n
        faces.append((a, b, len(outer) + b, len(outer) + a))
    return verts, faces


def ear_geo_detailed(sgn, n=12, rings=8, notches=(0.30, 0.52, 0.74),
                     notch_depth=0.16, notch_w=0.10):
    """Cat ear with shallow woodcut-like notches on the OUTER edge."""
    base = Vector((sgn * 0.095, 0.026, 0.845))
    tip = Vector((sgn * 0.206, 0.012, EAR_TIP_Z))
    out = []
    for k in range(rings + 1):
        t = k / rings
        c = base + (tip - base) * t
        k2 = max(0.0, 1.0 - t) ** 0.85
        rx = max(0.088 * k2, 0.0035)
        ry = max(0.032 * k2, 0.0030)
        ring = []
        for i in range(n):
            a = TAU * i / n
            ca, sa = math.cos(a), math.sin(a)
            # outward-facing vertices (the sgn side) carry the cut marks
            outward = max(0.0, ca * sgn)
            cut = 0.0
            for tn in notches:
                cut += math.exp(-((t - tn) / notch_w) ** 2)
            cut = min(cut, 1.0) * notch_depth * (outward ** 2)
            ring.append((c.x + ca * rx * (1.0 - cut),
                         c.y + sa * ry * (1.0 - cut * 0.5), c.z))
        out.append(ring)
    return loft(out)


def ear_inner(sgn, n=10, rings=5):
    """Inner-ear blade: the ear's own cone, shrunk and sat just in front."""
    base = Vector((sgn * 0.098, 0.026 + 0.030, 0.852))
    tip = Vector((sgn * 0.198, 0.012 + 0.030, EAR_TIP_Z - 0.055))
    out = []
    for k in range(rings + 1):
        t = k / rings
        c = base + (tip - base) * t
        k2 = max(0.0, 1.0 - t) ** 0.85
        rx = max(0.088 * 0.60 * k2, 0.003)
        ry = max(0.032 * 0.30 * k2, 0.0060)
        out.append([(c.x + math.cos(TAU * i / n) * rx,
                     c.y + math.sin(TAU * i / n) * ry, c.z) for i in range(n)])
    return loft(out)


def ear_weights(sgn):
    bone = "ear.L" if sgn < 0 else "ear.R"

    def w(co):
        t = smoothstep(0.855, 0.930, co.z)
        return {bone: t, "head": 1.0 - t}
    return w


def build_final():
    sc = reset_scene(fps=30)
    m = mats()
    mb = MeshBuilder("WW_body")
    gear = MeshBuilder("WW_gear")

    # ---------------- torso ----------------
    def torso_w(co):
        z = co.z
        if z < 0.30:
            return {"hips": 1.0}
        if z < 0.40:
            t = smoothstep(0.30, 0.40, z)
            return {"hips": 1 - t, "spine": t}
        if z < 0.50:
            t = smoothstep(0.40, 0.50, z)
            return {"spine": 1 - t, "chest": t}
        t = smoothstep(0.50, 0.60, z)
        return {"chest": 1 - t, "neck": t}

    rings = [ring_pts((0, 0, 0), r, r * 0.92, n=20, z=z) for z, r in TORSO_PROF]
    mb.add(loft(rings), m["fur"], smooth=True, weights=torso_w)

    # ---------------- head ----------------
    def head_w(co):
        t = smoothstep(0.575, 0.650, co.z)
        return {"head": t, "neck": 1.0 - t}

    mb.add(ellipsoid(tuple(HEAD_C), tuple(HEAD_R), nu=24, nv=16),
           m["fur"], smooth=True, weights=head_w)
    for sgn in (-1, 1):
        mb.add(ellipsoid((sgn * 0.104, 0.130, 0.714), (0.078, 0.074, 0.062),
                         nu=16, nv=11), m["fur"], smooth=True,
               weights={"head": 1.0})
    # muzzle
    mb.add(ellipsoid((0, 0.196, 0.702), (0.064, 0.046, 0.040), nu=18, nv=12),
           m["fur"], smooth=True, weights={"head": 1.0})

    # ---------------- ears ----------------
    for sgn in (-1, 1):
        w = ear_weights(sgn)
        # dark backing plate gives the woodcut ear rim structure line
        dark = ear_geo_detailed(sgn * 1.0, n=12, rings=8)
        dv = [(x + sgn * 0.004, y - 0.004, z) for (x, y, z) in dark[0]]
        mb.add((dv, dark[1]), m["dark"], smooth=True, weights=w)
        mb.add(ear_geo_detailed(sgn), m["fur"], smooth=True, weights=w)
        # inner ear: a smaller red blade set inside the fur one
        mb.add(ear_inner(sgn), m["red"], smooth=True, weights=w)

    # ---------------- eyes + lids ----------------
    for sgn in (-1, 1):
        ex, ey, ez = sgn * EYE_C.x, EYE_C.y, EYE_C.z
        bone = "lid.L" if sgn < 0 else "lid.R"
        # eye socket rim (structure line)
        rim = []
        for i in range(18):
            a = TAU * i / 18
            rr = EYE_R * 1.03
            rim.append((ex + math.cos(a) * rr, ey + 0.004,
                        ez + math.sin(a) * rr * 1.06))
        mb.add(tube_along(rim + [rim[0]], [0.0040] * (len(rim) + 1), n=5),
               m["dark"], smooth=True, weights={"head": 1.0})
        # iris
        mb.add(ellipsoid((ex, ey, ez), (EYE_R, EYE_R * 0.62, EYE_R * 1.04),
                         nu=18, nv=12), m["iris"], smooth=True,
               weights={"head": 1.0})
        # pupil
        mb.add(ellipsoid((ex, ey + 0.020, ez - 0.002),
                         (EYE_R * 0.46, EYE_R * 0.34, EYE_R * 0.54),
                         nu=14, nv=10), m["dark"], smooth=True,
               weights={"head": 1.0})
        # two highlights (big upper-left, small lower-right)
        mb.add(ellipsoid((ex - sgn * 0.019, ey + 0.036, ez + 0.023),
                         (0.0155, 0.011, 0.0155), nu=10, nv=8),
               m["white"], smooth=True, weights={"head": 1.0})
        mb.add(ellipsoid((ex + sgn * 0.020, ey + 0.034, ez - 0.024),
                         (0.0072, 0.006, 0.0072), nu=8, nv=6),
               m["white"], smooth=True, weights={"head": 1.0})
        # eyelid: hollow cap parked just above the eye; rotating it about the
        # eye's X axis sweeps it down to blink
        mb.add(sphere_cap((ex, ey - 0.004, ez), EYE_R * 1.10,
                          math.radians(26.0), thick=0.007, n=16, rings=2),
               m["fur"], smooth=True, weights={bone: 1.0})

    # ---------------- nose + mouth ----------------
    mb.add(ellipsoid((0, 0.228, 0.716), (0.020, 0.014, 0.013), nu=10, nv=7),
           m["red"], smooth=True, weights={"head": 1.0})
    # 浅浅的 omega 嘴: two small arcs below the nose
    for sgn in (-1, 1):
        arc = []
        for i in range(7):
            t = i / 6
            a = math.radians(lerp(8.0, 150.0, t))
            arc.append((sgn * (0.004 + 0.032 * (1 - math.cos(a))),
                        0.224 - 0.004 * t,
                        0.702 - 0.024 * math.sin(a)))
        mb.add(tube_along(arc, [0.0052] * len(arc), n=5),
               m["dark"], smooth=True, weights={"head": 1.0})

    # ---------------- forehead 祥云 mark ----------------
    cz2 = 0.868
    spiral2d = []
    for i in range(26):
        t = i / 25
        a = math.radians(200.0) + TAU * 1.25 * t
        r = lerp(0.034, 0.007, t ** 0.8)
        spiral2d.append((r * math.cos(a) * 1.20, cz2 + r * math.sin(a)))
    # centre the seal on the head's midline (the curl alone is asymmetric)
    mx = sum(p[0] for p in spiral2d) / len(spiral2d)
    spiral2d = [(x - mx, z) for x, z in spiral2d]
    ribbon_on_head(mb, spiral2d, 0.030, 0.0022, m["gold"])
    ribbon_on_head(mb, spiral2d, 0.017, 0.0042, m["teal"])

    # ---------------- tail ----------------
    tpts, trad = tail_path()
    n_t = len(tpts)
    # split: last 40% of the path is the red 卷云 tip
    split = 5   # arc -> coil boundary: the coil itself is 朱红

    def tail_w(lo, hi):
        def w(co):
            # nearest path parameter for this vertex
            best, bi = 1e9, 0
            for i, p in enumerate(tpts):
                d = (co - Vector(p)).length_squared
                if d < best:
                    best, bi = d, i
            u = bi / (n_t - 1)
            seg = min(4, int(u * 5))
            names = [f"tail.{k + 1:02d}" for k in range(5)]
            w2 = 0.5
            if seg == 0:
                return {"hips": 0.35, names[0]: 0.65}
            return {names[seg]: 1.0 - w2 * 0.5, names[max(0, seg - 1)]: w2 * 0.5}
        return w

    body_pts = tpts[:split + 1]
    body_r = trad[:split + 1]
    tip_pts = tpts[split:]
    tip_r = trad[split:]
    mb.add(tube_along(body_pts, body_r, n=10), m["fur"], smooth=True,
           weights=tail_w(0, split))
    mb.add(tube_along(tip_pts, tip_r, n=10), m["red"], smooth=True,
           weights=tail_w(split, n_t))

    # ---------------- legs ----------------
    for sgn in (-1, 1):
        for tag, y, x in (("front", LEG_FRONT_Y, LEG_X),
                          ("back", LEG_BACK_Y, LEG_X + 0.012)):
            up = f"{tag}_upper." + ("L" if sgn < 0 else "R")
            lo = f"{tag}_lower." + ("L" if sgn < 0 else "R")
            pw = f"{tag}_paw." + ("L" if sgn < 0 else "R")

            def leg_w(co, up=up, lo=lo, pw=pw):
                z = co.z
                if z > 0.150:
                    t = smoothstep(0.150, 0.230, z)
                    return {up: 1 - t, "hips": t}
                if z > 0.070:
                    t = smoothstep(0.070, 0.150, z)
                    return {lo: 1 - t, up: t}
                t = smoothstep(0.030, 0.070, z)
                return {pw: 1 - t, lo: t}

            mb.add(cylinder((sgn * x, y, 0.230), (sgn * x, y + 0.008, 0.052),
                            0.050, 0.044, n=10), m["fur"], smooth=True,
                   weights=leg_w)
            mb.add(ellipsoid((sgn * x, y + 0.016, PAW_Z),
                             (0.060, 0.080, 0.034), nu=16, nv=10),
                   m["fur"], smooth=True, weights={pw: 1.0})

    # ---------------- 项圈 + 挂饰 (separate object) ----------------
    collar_z, collar_r = 0.605, 0.108
    for i in range(28):
        a0 = TAU * i / 28
        a1 = TAU * (i + 1) / 28
        col = m["teal"] if i % 2 == 0 else m["gold"]
        p0 = (math.cos(a0) * collar_r, math.sin(a0) * collar_r * 0.92, collar_z)
        p1 = (math.cos(a1) * collar_r, math.sin(a1) * collar_r * 0.92, collar_z)
        gear.add(cylinder(p0, p1, 0.013, 0.013, n=6), col, smooth=True,
                 weights={"neck": 0.7, "chest": 0.3})
    # gold thread ring on the collar
    ring = [(math.cos(TAU * i / 32) * (collar_r + 0.004),
             math.sin(TAU * i / 32) * (collar_r + 0.004) * 0.92, collar_z)
            for i in range(33)]
    gear.add(tube_along(ring, [0.0038] * 33, n=4), m["gold"], smooth=True,
             weights={"neck": 0.7, "chest": 0.3})

    # chain: two strands down to the pendant
    for sgn in (-1, 1):
        chain = []
        for i in range(6):
            t = i / 5
            chain.append((sgn * lerp(0.030, 0.006, t),
                          lerp(0.098, 0.140, t),
                          lerp(0.598, 0.516, t)))
        gear.add(tube_along(chain, [0.0035] * 6, n=4), m["gold"], smooth=True,
                 weights={"chest": 1.0})
    # 青花瓷小圆牌 (disc facing +Y)
    pz, py = 0.508, 0.150
    gear.add(cylinder((0, py - 0.006, pz), (0, py + 0.006, pz), 0.030, 0.030,
                      n=20), m["white"], smooth=True, weights={"chest": 1.0})
    for sgn in (-1, 1):
        gear.add(cylinder((sgn * 0.016, py + 0.0065, pz + 0.012),
                          (sgn * 0.016, py + 0.0085, pz + 0.012),
                          0.0105, 0.0105, n=12), m["teal"], smooth=True,
                 weights={"chest": 1.0})
    gear.add(cylinder((0, py + 0.0065, pz - 0.010), (0, py + 0.0085, pz - 0.010),
                      0.0125, 0.0125, n=12), m["teal"], smooth=True,
             weights={"chest": 1.0})
    # gold hanger loop above the disc
    gear.add(tube_along([(0, py - 0.002, pz + 0.030), (0, py - 0.002, pz + 0.044)],
                        [0.0045, 0.0045], n=5), m["gold"], smooth=True,
             weights={"chest": 1.0})

    body_ob = mb.build()
    gear_ob = gear.build()
    print(f"[final] body tris={tri_count(body_ob)} gear tris={tri_count(gear_ob)}")

    # ---- rig + the 8 actions ---- #
    import rig_anim
    tpts, _ = tail_path()
    arm = rig_anim.build_rig(body_ob, gear_ob, [tuple(p) for p in tpts])
    order = rig_anim.build_actions(arm)

    tr = tri_count(body_ob) + tri_count(gear_ob)
    mats_used = {m.name for o in (body_ob, gear_ob) for m in o.data.materials if m}
    lo, hi = scene_bounds()
    print(f"[final] TOTAL tris={tr}  materials={len(mats_used)}  bones={len(arm.data.bones)}")
    print(f"[final] size = {hi.x - lo.x:.3f} x {hi.y - lo.y:.3f} x {hi.z - lo.z:.3f}"
          f"   z={lo.z:.4f}..{hi.z:.4f}")
    print(f"[final] actions={'/'.join(order)}")
    return body_ob, gear_ob, arm


if __name__ == "__main__":
    main()