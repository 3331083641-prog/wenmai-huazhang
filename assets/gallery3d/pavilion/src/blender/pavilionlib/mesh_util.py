"""bmesh 几何工具库 —— 所有构件模块共用。

设计原则：
  * 一切几何用 bmesh 手工构建，不依赖 bpy.ops（除必要的字体/曲线转换）。
  * 坐标单位为米（Blender 单位）。调用方负责 mm→m。
  * 提供「真几何」原语：卷杀截面、收分、起翘曲面、榫头、卯口、瓦垄波形。
"""
from __future__ import annotations

import math
from typing import Callable, Iterable, Sequence

import bmesh
import bpy
from mathutils import Matrix, Vector

TAU = math.pi * 2.0


# ============================================================================
# 基础
# ============================================================================
def new_bm() -> bmesh.types.BMesh:
    return bmesh.new()


def v(bm, co) -> bmesh.types.BMVert:
    return bm.verts.new(Vector(co))


def face(bm, verts, mat_index: int = 0):
    try:
        f = bm.faces.new(verts)
    except ValueError:
        return None
    f.material_index = mat_index
    return f


def bm_from_verts_faces(verts: Sequence, faces: Sequence[Sequence[int]]):
    bm = bmesh.new()
    vs = [bm.verts.new(Vector(c)) for c in verts]
    bm.verts.ensure_lookup_table()
    for idx in faces:
        try:
            bm.faces.new([vs[i] for i in idx])
        except ValueError:
            pass
    bm.normal_update()
    return bm


def bridge_rings(bm, ring_a, ring_b, closed=True, flip=False):
    """把两个等长点环连成四边形带。"""
    n = len(ring_a)
    assert n == len(ring_b)
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        j = (i + 1) % n
        quad = [ring_a[i], ring_a[j], ring_b[j], ring_b[i]]
        if flip:
            quad.reverse()
        face(bm, quad)


def cap_ring(bm, ring, flip=False):
    vs = list(ring)
    if flip:
        vs.reverse()
    face(bm, vs)


def recalc_normals(bm, faces=None):
    bmesh.ops.recalc_face_normals(bm, faces=faces or list(bm.faces))


# ============================================================================
# 实体原语
# ============================================================================
def box(bm, center, size, mat_index: int = 0):
    """轴对齐长方体。center/size 均为 3 元组（米）。"""
    cx, cy, cz = center
    sx, sy, sz = (s * 0.5 for s in size)
    corners = [
        (cx - sx, cy - sy, cz - sz), (cx + sx, cy - sy, cz - sz),
        (cx + sx, cy + sy, cz - sz), (cx - sx, cy + sy, cz - sz),
        (cx - sx, cy - sy, cz + sz), (cx + sx, cy - sy, cz + sz),
        (cx + sx, cy + sy, cz + sz), (cx - sx, cy + sy, cz + sz),
    ]
    vs = [bm.verts.new(Vector(c)) for c in corners]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    for q in quads:
        face(bm, [vs[i] for i in q], mat_index)
    return vs


def box_mm(bm, x0, x1, y0, y1, z0, z1, mat_index: int = 0):
    """用极值建盒（米）。"""
    return box(bm, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
               (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)), mat_index)


def prism(bm, profile2d: Sequence[tuple], axis_from, axis_to, mat_index: int = 0,
          cap_start=True, cap_end=True):
    """把 2D 截面沿向量拉伸成柱体。

    profile2d: [(u, w), ...] 逆时针，位于垂直于拉伸方向的平面内。
    axis_from / axis_to: 3 元组端点。u/w 平面由拉伸方向自动构造。
    """
    a = Vector(axis_from)
    b = Vector(axis_to)
    d = (b - a)
    if d.length < 1e-9:
        return []
    n = d.normalized()
    # 构造正交基
    ref = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))
    u_ax = ref.cross(n).normalized()
    w_ax = n.cross(u_ax).normalized()
    ring_a = [bm.verts.new(a + u_ax * p[0] + w_ax * p[1]) for p in profile2d]
    ring_b = [bm.verts.new(b + u_ax * p[0] + w_ax * p[1]) for p in profile2d]
    bridge_rings(bm, ring_a, ring_b, closed=True)
    if cap_start:
        cap_ring(bm, ring_a, flip=True)
    if cap_end:
        cap_ring(bm, ring_b, flip=False)
    return ring_a + ring_b


def cylinder(bm, center, radius, height, segments=16, mat_index: int = 0,
             axis="Z", radius_top=None, cap=True):
    """圆柱/圆台。"""
    r1 = radius
    r2 = radius if radius_top is None else radius_top
    cx, cy, cz = center
    ring_a, ring_b = [], []
    for i in range(segments):
        ang = TAU * i / segments
        c, s = math.cos(ang), math.sin(ang)
        pa = Vector((c * r1, s * r1, 0))
        pb = Vector((c * r2, s * r2, 0))
        if axis == "Z":
            pa = Vector((cx + pa.x, cy + pa.y, cz))
            pb = Vector((cx + pb.x, cy + pb.y, cz + height))
        elif axis == "X":
            pa = Vector((cx, cy + pa.x, cz + pa.y))
            pb = Vector((cx + height, cy + pb.x, cz + pb.y))
        else:
            pa = Vector((cx + pa.x, cy, cz + pa.y))
            pb = Vector((cx + pb.x, cy + height, cz + pb.y))
        ring_a.append(bm.verts.new(pa))
        ring_b.append(bm.verts.new(pb))
    bridge_rings(bm, ring_a, ring_b, closed=True)
    if cap:
        cap_ring(bm, ring_a, flip=True)
        cap_ring(bm, ring_b, flip=False)
    return ring_a + ring_b


def revolve(bm, profile2d: Sequence[tuple], center, segments=24, mat_index: int = 0,
            sweep=TAU, close_profile=False):
    """绕 Z 轴旋转剖面成回转体。profile2d: [(r, z), ...] 自下而上。"""
    cx, cy, cz = center
    rings = []
    nseg = segments if abs(sweep - TAU) < 1e-6 else segments + 1
    for i in range(nseg):
        ang = sweep * i / segments
        c, s = math.cos(ang), math.sin(ang)
        ring = [bm.verts.new(Vector((cx + r * c, cy + r * s, cz + z)))
                for (r, z) in profile2d]
        rings.append(ring)
    for i in range(len(rings) - 1):
        bridge_rings(bm, rings[i], rings[i + 1], closed=close_profile)
    if abs(sweep - TAU) < 1e-6:
        bridge_rings(bm, rings[-1], rings[0], closed=close_profile)
    return rings


def swept_tube(bm, path: Sequence, radius, segments=8, mat_index: int = 0,
               caps=True, radius_end=None, up_hint=(0, 0, 1)):
    """沿 3D 折线扫掠圆管（用于檩、椽、寻杖、角脊）。"""
    pts = [Vector(p) for p in path]
    if len(pts) < 2:
        return []
    r_end = radius if radius_end is None else radius_end
    rings = []
    for i, p in enumerate(pts):
        if i == 0:
            t = (pts[1] - pts[0])
        elif i == len(pts) - 1:
            t = (pts[-1] - pts[-2])
        else:
            t = (pts[i + 1] - pts[i - 1])
        t.normalize()
        ref = Vector(up_hint)
        if abs(t.dot(ref)) > 0.98:
            ref = Vector((1, 0, 0))
        u_ax = ref.cross(t).normalized()
        w_ax = t.cross(u_ax).normalized()
        tt = i / max(1, len(pts) - 1)
        r = radius * (1 - tt) + r_end * tt
        ring = []
        for k in range(segments):
            ang = TAU * k / segments
            ring.append(bm.verts.new(p + u_ax * (math.cos(ang) * r) + w_ax * (math.sin(ang) * r)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        bridge_rings(bm, rings[i], rings[i + 1], closed=True)
    if caps:
        cap_ring(bm, rings[0], flip=True)
        cap_ring(bm, rings[-1], flip=False)
    return rings


def swept_profile_along(bm, path: Sequence, profile2d: Sequence[tuple],
                        mat_index: int = 0, caps=True, up_hint=(0, 0, 1),
                        closed_profile=True, scale_fn: Callable[[float], tuple] = None):
    """沿折线扫掠任意 2D 截面。profile2d 在 (u,w) 平面内，u 为侧向、w 为法向。"""
    pts = [Vector(p) for p in path]
    if len(pts) < 2:
        return []
    rings = []
    for i, p in enumerate(pts):
        if i == 0:
            t = (pts[1] - pts[0])
        elif i == len(pts) - 1:
            t = (pts[-1] - pts[-2])
        else:
            t = (pts[i + 1] - pts[i - 1])
        t.normalize()
        ref = Vector(up_hint)
        if abs(t.dot(ref)) > 0.98:
            ref = Vector((1, 0, 0))
        u_ax = ref.cross(t).normalized()
        w_ax = t.cross(u_ax).normalized()
        sc = (1.0, 1.0) if scale_fn is None else scale_fn(i / max(1, len(pts) - 1))
        ring = [bm.verts.new(p + u_ax * (pu * sc[0]) + w_ax * (pw * sc[1]))
                for (pu, pw) in profile2d]
        rings.append(ring)
    for i in range(len(rings) - 1):
        bridge_rings(bm, rings[i], rings[i + 1], closed=closed_profile)
    if caps and closed_profile:
        cap_ring(bm, rings[0], flip=True)
        cap_ring(bm, rings[-1], flip=False)
    return rings


# ============================================================================
# 曲面（屋面、栏板浮雕、拱眼壁）
# ============================================================================
def surface(bm, fn: Callable[[float, float], Vector], nu: int, nv: int,
            mat_index: int = 0, close_v=False, flip=False):
    """参数曲面。fn(u,v)->Vector，u,v∈[0,1]。返回 (grid_verts, vert_index_map)。"""
    grid = [[None] * (nv + 1) for _ in range(nu + 1)]
    for i in range(nu + 1):
        u = i / nu
        for j in range(nv + 1):
            vv = j / nv
            grid[i][j] = bm.verts.new(fn(u, vv))
    def _f(a, b, c, d):
        quad = [a, b, c, d]
        if flip:
            quad.reverse()
        face(bm, quad, mat_index)
    for i in range(nu):
        for j in range(nv):
            _f(grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])
    return grid


def shell(bm, fn: Callable[[float, float], Vector], nu: int, nv: int,
          thickness: float, mat_index: int = 0, flip=False):
    """带厚度的参数壳（沿法向下偏 thickness）。返回 (top_grid, bottom_grid)。"""
    eps_u, eps_v = 1e-3, 1e-3
    def _normal(u, vv):
        du = fn(min(1, u + eps_u), vv) - fn(max(0, u - eps_u), vv)
        dv = fn(u, min(1, vv + eps_v)) - fn(u, max(0, vv - eps_v))
        n = du.cross(dv)
        if n.length < 1e-9:
            return Vector((0, 0, 1))
        n.normalize()
        if n.z < 0:
            n = -n
        return n
    top = [[None] * (nv + 1) for _ in range(nu + 1)]
    bot = [[None] * (nv + 1) for _ in range(nu + 1)]
    for i in range(nu + 1):
        u = i / nu
        for j in range(nv + 1):
            vv = j / nv
            p = fn(u, vv)
            n = _normal(u, vv)
            top[i][j] = bm.verts.new(p)
            bot[i][j] = bm.verts.new(p - n * thickness)
    def quad(a, b, c, d):
        q = [a, b, c, d]
        if flip:
            q.reverse()
        face(bm, q, mat_index)
    for i in range(nu):
        for j in range(nv):
            quad(top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1])
            quad(bot[i][j], bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j])
    # 四周封边
    for j in range(nv):
        quad(top[0][j], top[0][j + 1], bot[0][j + 1], bot[0][j])
        quad(top[nu][j], bot[nu][j], bot[nu][j + 1], top[nu][j + 1])
    for i in range(nu):
        quad(top[i][0], bot[i][0], bot[i + 1][0], top[i + 1][0])
        quad(top[i][nv], top[i + 1][nv], bot[i + 1][nv], bot[i][nv])
    return top, bot


# ============================================================================
# 截面构造器
# ============================================================================
def rect_profile(w, h, cx=0.0, cy=0.0):
    w2, h2 = w / 2, h / 2
    return [(cx - w2, cy - h2), (cx + w2, cy - h2),
            (cx + w2, cy + h2), (cx - w2, cy + h2)]


def rounded_rect_profile(w, h, r, n=4):
    """圆角矩形截面（用于梁、枋的抹角）。"""
    pts = []
    r = min(r, w / 2 - 1e-6, h / 2 - 1e-6)
    corners = [
        (w / 2 - r, h / 2 - r, 0),
        (-(w / 2 - r), h / 2 - r, math.pi / 2),
        (-(w / 2 - r), -(h / 2 - r), math.pi),
        (w / 2 - r, -(h / 2 - r), math.pi * 1.5),
    ]
    for cx, cy, a0 in corners:
        for k in range(n + 1):
            a = a0 + (math.pi / 2) * k / n
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


def circle_profile(r, n=16, cy=0.0):
    return [(math.cos(TAU * i / n) * r, cy + math.sin(TAU * i / n) * r) for i in range(n)]


def gong_profile(length, height, tao=0.0, juan=4, juan_step=0.02, angle_cut=True):
    """拱（单材/足材）侧视截面 —— 两端卷杀、下缘微拱。

    坐标系：u = 沿拱长，w = 高度。返回逆时针点列。
    卷杀：两端底部做 4 瓣内凹，形成宋式「卷杀」曲线。
    """
    h = height
    half = length / 2
    pts = []
    # 下缘：自左端至右端，中部略微上拱
    nseg = 10
    for i in range(nseg + 1):
        u = -half + length * i / nseg
        t = abs(u) / half
        w = tao * (1 - t * t) if tao else 0.0
        pts.append((u, w))
    # 右端卷杀（自下而上）
    if angle_cut:
        for k in range(juan + 1):
            f = k / max(1, juan)
            # 每瓣内收，形成阶梯曲线
            inset = juan_step * length * (1 - f) * 0.5
            pts.append((half - inset, (h * 0.15) * f + h * 0.15))
        for k in range(juan, -1, -1):
            f = k / max(1, juan)
            inset = juan_step * length * f * 0.5
            pts.append((half - inset, h * 0.5 + (h * 0.35) * (1 - f)))
        pts.append((half - juan_step * length * 0.5, h))
    else:
        pts.append((half, h))
    # 上缘
    for i in range(nseg, -1, -1):
        u = -half + length * i / nseg
        pts.append((u, h))
    if angle_cut:
        for k in range(juan + 1):
            f = k / max(1, juan)
            inset = juan_step * length * f * 0.5
            pts.append((-half + inset, h * 0.5 + (h * 0.35) * (1 - f)))
        for k in range(juan, -1, -1):
            f = k / max(1, juan)
            inset = juan_step * length * (1 - f) * 0.5
            pts.append((-half + inset, (h * 0.15) * f + h * 0.15))
    else:
        pts.append((-half, h))
    return pts


def dou_profile(w_bottom, w_top, h, qi=0.25):
    """斗（坐斗/散斗）侧视截面：底部收分（斗欹），上部直身。

    清式斗：下半 1/4 为斗欹，四面斜收；上部 3/4 直。
    """
    hb = h * qi
    wb, wt = w_bottom / 2, w_top / 2
    return [
        (-wb, 0), (wb, 0),
        (wt, hb), (wt, h),
        (-wt, h), (-wt, hb),
    ]


def L_shape_profile(w, h, t):
    t = min(t, w / 2, h / 2)
    return [(0, 0), (w, 0), (w, t), (t, t), (t, h), (0, h)]


# ============================================================================
# 变形 / 修改
# ============================================================================
def transform(bm, verts, matrix: Matrix):
    for vt in verts:
        vt.co = matrix @ vt.co


def translate_verts(verts, offset):
    off = Vector(offset)
    for vt in verts:
        vt.co += off


def bevel_edges(bm, edges, offset, segments=1, profile=0.5):
    try:
        bmesh.ops.bevel(bm, geom=list(edges), offset=offset, segments=segments,
                        affect="EDGES", profile=profile, clamp_overlap=True)
    except Exception:
        pass


def bevel_all(bm, offset, segments=1, min_angle_deg=30.0):
    """只倒尖锐边，避免破坏曲面。"""
    thresh = math.radians(min_angle_deg)
    edges = []
    for e in bm.edges:
        if len(e.link_faces) == 2:
            a = e.link_faces[0].normal
            b = e.link_faces[1].normal
            if a.length > 0 and b.length > 0:
                if a.angle(b) > thresh:
                    edges.append(e)
    if edges:
        bevel_edges(bm, edges, offset, segments)


def _geo_normal(f) -> Vector:
    """由顶点坐标直接算法线，不依赖 f.normal（bmesh 未 normal_update 时它可能是零）。"""
    vs = f.verts
    if len(vs) >= 3:
        n = (vs[1].co - vs[0].co).cross(vs[2].co - vs[0].co)
        if n.length > 1e-9:
            return n.normalized()
    n = f.normal
    return n if n.length > 1e-9 else Vector((0.0, 0.0, 1.0))


def uv_box_project(bm, scale=1.0, offset=(0.0, 0.0)):
    """按面法线主轴做盒式 UV 投影（木纹/石材平铺足够）。"""
    uv_layer = bm.loops.layers.uv.verify()
    for f in bm.faces:
        n = _geo_normal(f)
        ax = max(range(3), key=lambda i: abs(n[i]))
        for loop in f.loops:
            co = loop.vert.co
            if ax == 0:
                u, vv = co.y, co.z
            elif ax == 1:
                u, vv = co.x, co.z
            else:
                u, vv = co.x, co.y
            loop[uv_layer].uv = (u * scale + offset[0], vv * scale + offset[1])


def uv_cylindrical(bm, center=(0, 0), scale=1.0, vscale=1.0, swap=False):
    """柱面 UV。swap=True 时把纹路方向转到竖直（木纹顺柱身走）。"""
    uv_layer = bm.loops.layers.uv.verify()
    cx, cy = center
    for f in bm.faces:
        for loop in f.loops:
            co = loop.vert.co
            ang = math.atan2(co.y - cy, co.x - cx) / TAU + 0.5
            if swap:
                loop[uv_layer].uv = (co.z * vscale, ang * scale)
            else:
                loop[uv_layer].uv = (ang * scale, co.z * vscale)


def mirror_x(bm, verts=None):
    """沿 X=0 镜像（就地复制）。"""
    src = list(verts) if verts else list(bm.verts)
    faces = set()
    for vt in src:
        for f in vt.link_faces:
            faces.add(f)
    geom = list(faces) + [e for f in faces for e in f.edges] + src
    ret = bmesh.ops.duplicate(bm, geom=list(set(geom)))
    new_verts = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
    for vt in new_verts:
        vt.co.x = -vt.co.x
    new_faces = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace)]
    bmesh.ops.reverse_faces(bm, faces=new_faces)
    return new_verts


# ============================================================================
# 榫卯专用
# ============================================================================
def tenon(bm, base_center, size, length, direction=(1, 0, 0), taper=1.0, mat_index=0):
    """凸榫：从 base_center 沿 direction 伸出 length 的锥台/棱台。"""
    cx, cy, cz = base_center
    sx, sy = size
    d = Vector(direction).normalized()
    if abs(d.z) > 0.9:
        u_ax = Vector((sx, 0, 0)).normalized()
        w_ax = Vector((0, sy, 0)).normalized()
    else:
        u_ax = d.cross(Vector((0, 0, 1))).normalized()
        w_ax = d.cross(u_ax).normalized()
    a = Vector(base_center)
    b = a + d * length
    f2 = taper
    ring_a = [bm.verts.new(a + u_ax * (sx / 2) + w_ax * (sy / 2)),
              bm.verts.new(a - u_ax * (sx / 2) + w_ax * (sy / 2)),
              bm.verts.new(a - u_ax * (sx / 2) - w_ax * (sy / 2)),
              bm.verts.new(a + u_ax * (sx / 2) - w_ax * (sy / 2))]
    ring_b = [bm.verts.new(b + u_ax * (sx / 2 * f2) + w_ax * (sy / 2 * f2)),
              bm.verts.new(b - u_ax * (sx / 2 * f2) + w_ax * (sy / 2 * f2)),
              bm.verts.new(b - u_ax * (sx / 2 * f2) - w_ax * (sy / 2 * f2)),
              bm.verts.new(b + u_ax * (sx / 2 * f2) - w_ax * (sy / 2 * f2))]
    bridge_rings(bm, ring_a, ring_b, closed=True)
    cap_ring(bm, ring_b, flip=False)
    return ring_a + ring_b


def dovetail(bm, center, width, height, length, depth_ratio=0.75,
             direction=(1, 0, 0), mat_index=0):
    """燕尾榫（银锭榫）：端部放大成梯形。"""
    cx, cy, cz = center
    d = Vector(direction).normalized()
    if abs(d.z) > 0.9:
        u_ax = Vector((1, 0, 0))
        w_ax = Vector((0, 1, 0))
    else:
        u_ax = d.cross(Vector((0, 0, 1))).normalized()
        w_ax = d.cross(u_ax).normalized()
    a = Vector(center)
    b = a + d * length
    w0, w1 = width / 2, width / 2 / depth_ratio
    h0, h1 = height / 2, height / 2 / depth_ratio
    def ring(p, w_, h_):
        return [bm.verts.new(p + u_ax * w_ + w_ax * h_),
                bm.verts.new(p - u_ax * w_ + w_ax * h_),
                bm.verts.new(p - u_ax * w_ - w_ax * h_),
                bm.verts.new(p + u_ax * w_ - w_ax * h_)]
    ra, rb = ring(a, w0, h0), ring(b, w1, h1)
    bridge_rings(bm, ra, rb, closed=True)
    cap_ring(bm, rb, flip=False)
    return ra + rb


def mortise_cut(bm, center, size, direction, depth, mat_index=0):
    """卯口：在实体面上切出矩形凹槽（用 boolean 近似：内嵌一个暗色内壁壳）。"""
    from mathutils import Matrix as M
    cx, cy, cz = center
    sx, sy = size
    d = Vector(direction).normalized()
    return box(bm, (cx - d.x * depth / 2, cy - d.y * depth / 2, cz - d.z * depth / 2),
               (abs(sx) if abs(d.x) < 0.9 else depth,
                abs(sy) if abs(d.y) < 0.9 else depth,
                abs(sy) if abs(d.z) < 0.9 else depth), mat_index)


# ============================================================================
# 对象创建 / 收尾
# ============================================================================
def bm_to_mesh(bm, name="mesh"):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    me.update()
    return me


def smooth_by_angle(obj, angle_deg=35.0, all_smooth=True):
    """平滑着色 + 按角度标硬边（Blender 4.1+ 无 auto smooth，用 sharp edge 实现）。"""
    me = obj.data
    if all_smooth:
        for p in me.polygons:
            p.use_smooth = True
    bm = bmesh.new()
    bm.from_mesh(me)
    thresh = math.radians(angle_deg)
    for e in bm.edges:
        if len(e.link_faces) == 2:
            a, b = e.link_faces[0].normal, e.link_faces[1].normal
            if a.length > 1e-9 and b.length > 1e-9 and a.angle(b) > thresh:
                e.smooth = False
        else:
            e.smooth = False
    bm.to_mesh(me)
    bm.free()
    me.update()


def flat_shade(obj):
    for p in obj.data.polygons:
        p.use_smooth = False


def add_bevel_modifier(obj, width=0.01, segments=2, angle=40.0):
    md = obj.modifiers.new("Bevel", "BEVEL")
    md.width = width
    md.segments = segments
    md.limit_method = "ANGLE"
    md.angle_limit = math.radians(angle)
    md.harden_normals = False
    return md


def add_solidify(obj, thickness=0.02, offset=-1.0):
    md = obj.modifiers.new("Solidify", "SOLIDIFY")
    md.thickness = thickness
    md.offset = offset
    return md


def apply_modifiers(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(eval_obj)
    old = obj.data
    obj.modifiers.clear()
    obj.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)


def tri_count(obj) -> int:
    me = obj.data
    n = 0
    for p in me.polygons:
        n += max(1, len(p.vertices) - 2)
    return n


def text_to_mesh(text: str, font_path: str, size: float, extrude: float = 0.02,
                 align="CENTER", name="text"):
    """生成中文字 mesh（用于匾额题字）。"""
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = text
    cu.size = size
    cu.extrude = extrude
    cu.align_x = align
    cu.align_y = "CENTER"
    try:
        fnt = bpy.data.fonts.load(font_path, check_existing=True)
        cu.font = fnt
    except Exception:
        pass
    ob = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob, do_unlink=True)
    out = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(out)
    return out


CN_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simsun.ttc",
    r"C:\Windows\Fonts\simkai.ttf",
    r"D:\Codex\blender-5.2.2\blender-5.2.2-windows-x64\5.2\datafiles\fonts\NotoSansSC-Regular.otf",
]


def find_cn_font() -> str | None:
    import os
    for p in CN_FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    return None