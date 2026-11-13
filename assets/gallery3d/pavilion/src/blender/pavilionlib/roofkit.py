"""屋面原语 roofkit —— 主殿与副展阁共用的唯一屋面算法。

为什么要共用：宋式大屋顶的比例、举折曲线、翼角起翘、瓦垄间距必须全场景一致，
否则主殿与副展阁会「不是一套工匠做的」。

四个原语
--------
1. corrugated_skirt : 四面裙檐（撒头/腰檐）—— 从檐口矩形放样到内圈矩形，
   自带生起+翼角起翘、筒瓦瓦垄、**平整的檐下底棚**，闭合壳体。
2. gable_body       : 上部两坡（悬山体）—— 含山花板与博风板。
3. ridge_along_path : 脊 —— 沿任意折线扫掠的三级剖面（脊座+瓦条+脊帽），
   因此正脊（直线）与垂脊（随翼角上翘的曲线）用同一套语言。
4. eave_course      : 檐口滴水/瓦当连续带。

坐标系与约定
------------
* 瓦垄相位一律取 **世界坐标**（南/北面用 x，东/西面用 y），
  这样裙檐与上部两坡在接缝处瓦垄严格对齐，不会出现"错缝台阶"。
* 所有法线最后统一 recalc_face_normals（见 Context.bm_obj）。
* 起翘只作用于檐口附近，到内缘(v=1)衰减为 0，保证与上部两坡零错台。
"""
from __future__ import annotations

import math

import bmesh
from mathutils import Vector

from .dim import DIM
from . import mesh_util as mu

TAU = math.pi * 2.0


# ---------------------------------------------------------------- 工具
def _f_juzhe(v: float, k: float = 1.45) -> float:
    """宋式举折：檐口平缓、近脊陡峻（凸函数）。"""
    return v ** k


def _clamp01(x):
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def _corner_factor(s: float, side_len: float, run: float) -> float:
    """s 距两端越近 → 越大（0..1）。用于翼角起翘。"""
    d = min(s, 1.0 - s) * side_len
    return _clamp01(1.0 - d / max(run, 1e-6)) ** 2


def _cf_dist(d: float, run: float) -> float:
    """按距端点的距离算起翘权重（0..1）。"""
    return _clamp01(1.0 - d / max(run, 1e-6)) ** 2


def _corner_pair_dirs(SD, ends):
    """相邻两边共用同一个外角点：起翘的推出方向必须取两法向的角平分线。

    否则南面往 -Y 冲、西面往 -X 冲，同一个角会算出两个不同位置，
    转角处就裂开成一道"V 形缺口"（早期版本的实际症状）。
    """
    pair = {}
    for i, (si, e, pp, o) in enumerate(ends):
        for j, (sj, f, pq, o2) in enumerate(ends):
            if si != sj and abs(pp[0] - pq[0]) < 1e-6 and abs(pp[1] - pq[1]) < 1e-6:
                dx, dy = o[0] + o2[0], o[1] + o2[1]
                n = math.hypot(dx, dy) or 1.0
                pair[(si, e)] = (dx / n, dy / n)
    return pair


def _tile_wave(ph: float) -> float:
    """筒瓦 + 板瓦剖面（周期 1）。返回 -0.45 .. 1.0。

    * ph ∈ [0.00, 0.58)：筒瓦（窄而凸起的半圆脊，峰值 1.0）
    * ph ∈ [0.58, 1.00)：板瓦（宽而浅的凹沟，谷值 -0.45）
    纯 sin 波形会被看成"波纹钢板"，这个非对称剖面才有瓦的读感。
    """
    ph = ph - math.floor(ph)
    if ph < 0.58:
        u = (ph - 0.29) / 0.29           # -1 .. 1
        c = math.cos(u * math.pi * 0.5)
        return c ** 1.25 if c > 0 else 0.0
    u = (ph - 0.58) / 0.42               # 0 .. 1
    return -0.45 * math.sin(math.pi * u)


def _sides(outer, inner):
    ax0, ay0, ax1, ay1 = outer
    bx0, by0, bx1, by1 = inner
    return [
        ((ax0, ay0), (ax1, ay0), (bx0, by0), (bx1, by0), (0.0, -1.0)),   # 南
        ((ax1, ay1), (ax0, ay1), (bx1, by1), (bx0, by1), (0.0, 1.0)),    # 北
        ((ax0, ay1), (ax0, ay0), (bx0, by1), (bx0, by0), (-1.0, 0.0)),   # 西
        ((ax1, ay0), (ax1, ay1), (bx1, by0), (bx1, by1), (1.0, 0.0)),    # 东
    ]


def _q(bm, pts, mat):
    try:
        f = bm.faces.new(pts)
        f.material_index = mat
        return f
    except ValueError:
        return None


# ---------------------------------------------------------------- 裙檐
def _weld(bm, n0, dist=1.2e-4):
    """只焊接「本次调用新建」的顶点：把转角两侧各自算出的重合点并成一条边。

    这是「翼角豁口」的根因修复：四面裙檐各沿自身法线外冲，相邻两面在角部
    算出的点虽然重合，却是两套互不相连的顶点 → 每条翼角边留下一条
    ~0.55m 高的通缝（从外面能看进屋面内腔，表现为转角处莫名一大块暗面）。
    """
    bm.verts.ensure_lookup_table()
    n = len(bm.verts)
    if n <= n0 + 1:
        return 0
    sel = [bm.verts[i] for i in range(n0, n)]
    bmesh.ops.remove_doubles(bm, verts=sel, dist=dist)
    return len(sel) - len(bm.verts)


def corrugated_skirt(bm, outer, z_a, inner, z_b, sides=(0, 1, 2, 3),
                     lift=None, run_out=None, gauge=None, amp=None,
                     thick=None, nv=12, juzhe=1.45, mat=0, soffit=True):
    """四面裙檐放样。返回檐口折线（供滴水带使用）。"""
    D = DIM
    _n0 = len(bm.verts)
    lift = D.YIJIAO_RISE if lift is None else lift
    run_out = D.YIJIAO_OUT if run_out is None else run_out
    gauge = D.TILE_GAUGE if gauge is None else gauge
    amp = D.TILE_AMP if amp is None else amp
    thick = D.ROOF_THICK if thick is None else thick
    SD = _sides(outer, inner)
    ends = []
    for _si, (_p0, _p1, _q0, _q1, _o) in enumerate(SD):
        ends.append((_si, 0, _p0, _o))
        ends.append((_si, 1, _p1, _o))
    cpair = _corner_pair_dirs(SD, ends)
    eave_paths = {}

    for si in sides:
        p0, p1, q0, q1, out = SD[si]
        vx0, vy0 = p0
        vx1, vy1 = p1
        side_len = math.hypot(vx1 - vx0, vy1 - vy0)
        nu = max(20, int(side_len / max(gauge, 0.05) * 2.6))
        outv = Vector((out[0], out[1], 0.0))
        d0 = cpair.get((si, 0), (out[0], out[1]))
        d1 = cpair.get((si, 1), (out[0], out[1]))
        horiz = si in (0, 1)          # 南/北面沿 x 方向铺瓦

        def base(s, v):
            """无瓦垄的光顺屋面（也是底棚用的面）。返回 (x, y, z, c)。"""
            px = vx0 + (vx1 - vx0) * s
            py = vy0 + (vy1 - vy0) * s
            qx = q0[0] + (q1[0] - q0[0]) * s
            qy = q0[1] + (q1[1] - q0[1]) * s
            c_lo = _cf_dist(s * side_len, D.YIJIAO_RUN)
            c_hi = _cf_dist((1.0 - s) * side_len, D.YIJIAO_RUN)
            c = max(c_lo, c_hi)
            # 推出方向：角部取相邻两面法向的角平分线 → 共享角点两侧严格重合
            wi = max(0.0, 1.0 - c_lo - c_hi)
            dx = outv.x * wi + d0[0] * c_lo + d1[0] * c_hi
            dy = outv.y * wi + d0[1] * c_lo + d1[1] * c_hi
            n = math.hypot(dx, dy)
            if n > 1e-9:
                dx, dy = dx / n, dy / n
            push = run_out * (c ** 1.6) * (1.0 - v) ** 1.5
            x = px + (qx - px) * v + dx * push
            y = py + (qy - py) * v + dy * push
            z = z_a + (z_b - z_a) * _f_juzhe(v, juzhe)
            # 生起（整条檐口缓缓上扬）+ 翼角起翘（转角急起），到内缘衰减为 0
            z += lift * (0.18 * abs(2.0 * s - 1.0) ** 3 + c ** 2) * (1.0 - v) ** 1.6
            return x, y, z, c

        def phase(s):
            w = (vx0 + (vx1 - vx0) * s) if horiz else (vy0 + (vy1 - vy0) * s)
            return w / max(gauge, 0.05)

        def pt(s, v):
            x, y, z, c = base(s, v)
            # 翼角处瓦垄逐渐收敛，避免两面瓦垄在转角交叉成网格
            z += amp * (1.0 - c) * _tile_wave(phase(s))
            return Vector((x, y, z))

        top = [[pt(i / nu, j / nv) for j in range(nv + 1)] for i in range(nu + 1)]
        nvb = 3
        bot = [[Vector((0, 0, 0))] * (nvb + 1) for _ in range(nu + 1)]
        for i in range(nu + 1):
            for j in range(nvb + 1):
                # 底棚：光顺面（不带瓦垄），整体下移 thick —— 这才是"檐下"该有的样子
                x, y, z, _c = base(i / nu, j / nvb)
                bot[i][j] = Vector((x, y, z - thick))

        vt = [[bm.verts.new(top[i][j]) for j in range(nv + 1)] for i in range(nu + 1)]
        vb = [[bm.verts.new(bot[i][j]) for j in range(nvb + 1)] for i in range(nu + 1)]
        for i in range(nu):
            for j in range(nv):
                _q(bm, [vt[i][j], vt[i + 1][j], vt[i + 1][j + 1], vt[i][j + 1]], mat)
        if soffit:
            for i in range(nu):
                for j in range(nvb):
                    _q(bm, [vb[i][j], vb[i][j + 1], vb[i + 1][j + 1], vb[i + 1][j]], mat)
            # 檐口封边（瓦口）
            for i in range(nu):
                _q(bm, [vt[i][0], vb[i][0], vb[i + 1][0], vt[i + 1][0]], mat)
            # 内缘封边
            for i in range(nu):
                _q(bm, [vt[i][nv], vt[i + 1][nv], vb[i + 1][nvb], vb[i][nvb]], mat)
            # Adjacent slopes already share the welded hip. A closing wall
            # belongs only on an exposed edge of a partial skirt.
            for i, end_xy in ((0, p0), (nu, p1)):
                if any(other != si and other in sides and end_xy in SD[other][:2]
                       for other in range(4)):
                    continue
                j = k = 0
                while j < nv or k < nvb:
                    if k == nvb or (j < nv and (j+1)*nvb <= (k+1)*nv):
                        vertices = [vt[i][j], vt[i][j+1], vb[i][k]]
                        j += 1
                    else:
                        vertices = [vt[i][j], vb[i][k+1], vb[i][k]]
                        k += 1
                    _q(bm, vertices if i == 0 else vertices[::-1], mat)
        eave_paths[si] = [top[i][0] for i in range(nu + 1)]
    _weld(bm, _n0)
    return eave_paths


# ---------------------------------------------------------------- 上部两坡
def gable_body(bm, plan, z_base, ridge_y, z_ridge, gable_x,
               gauge=None, amp=None, thick=None, mat=0, nu=None,
               barge=True, mat_barge=0):
    """上部两坡（歇山主体）。plan=(x0,y0,x1,y1)，山花在 x=±gable_x。"""
    D = DIM
    gauge = D.TILE_GAUGE if gauge is None else gauge
    amp = D.TILE_AMP if amp is None else amp
    thick = D.ROOF_THICK if thick is None else thick
    x0, y0, x1, y1 = plan
    w = x1 - x0
    nu = nu or max(28, int(w / max(gauge, 0.05) * 2.4))
    nv = 16

    def z_at(v):
        return z_base + (z_ridge - z_base) * _f_juzhe(v, 1.35)

    def surf(sign):
        """sign=-1 南坡, +1 北坡。v:0 檐底 → 1 脊。"""
        edge_y = y0 if sign < 0 else y1
        grid = []
        for i in range(nu + 1):
            x = x0 + w * i / nu
            row = []
            for j in range(nv + 1):
                v = j / nv
                y = edge_y + (ridge_y - edge_y) * v
                z = z_at(v) + amp * (1.0 - 0.62 * v) * _tile_wave(x / max(gauge, 0.05))
                row.append(Vector((x, y, z)))
            grid.append(row)
        return grid

    for sign in (-1, 1):
        g = surf(sign)
        vt = [[bm.verts.new(g[i][j]) for j in range(nv + 1)] for i in range(nu + 1)]
        vb = [[bm.verts.new(Vector((g[i][j].x, g[i][j].y, g[i][j].z - thick)))
               for j in range(nv + 1)] for i in range(nu + 1)]
        for i in range(nu):
            for j in range(nv):
                if sign < 0:
                    _q(bm, [vt[i][j], vt[i + 1][j], vt[i + 1][j + 1], vt[i][j + 1]], mat)
                    _q(bm, [vb[i][j], vb[i][j + 1], vb[i + 1][j + 1], vb[i + 1][j]], mat)
                else:
                    _q(bm, [vt[i + 1][j], vt[i][j], vt[i][j + 1], vt[i + 1][j + 1]], mat)
                    _q(bm, [vb[i + 1][j], vb[i + 1][j + 1], vb[i][j + 1], vb[i][j]], mat)
        # 脊线封口
        for i in range(nu):
            _q(bm, [vt[i][nv], vb[i][nv], vb[i + 1][nv], vt[i + 1][nv]], mat)
        # 两侧山花封边（博风板下方的那道厚度）
        for j in range(nv):
            _q(bm, [vt[0][j], vb[0][j], vb[0][j + 1], vt[0][j + 1]], mat)
            _q(bm, [vt[nu][j + 1], vb[nu][j + 1], vb[nu][j], vt[nu][j]], mat)

    # 山花板（两端竖直三角面）
    for sx in (-1, 1):
        gx = gable_x * sx
        inset = -0.05 * sx
        a = bm.verts.new(Vector((gx + inset, y0, z_base - 0.02)))
        b = bm.verts.new(Vector((gx + inset, ridge_y, z_ridge - 0.06)))
        c = bm.verts.new(Vector((gx + inset, y1, z_base - 0.02)))
        if sx > 0:
            _q(bm, [a, b, c], mat)
        else:
            _q(bm, [c, b, a], mat)

    # 博风板（沿两侧山面坡边扫掠，压住山花上缘）
    if barge:
        prof = mu.rect_profile(0.18, 0.34)
        for sx in (-1, 1):
            gx = gable_x * sx
            for sign in (-1, 1):
                edge_y = y0 if sign < 0 else y1
                path = []
                for j in range(0, nv + 1):
                    v = j / nv
                    y = edge_y + (ridge_y - edge_y) * v
                    path.append(Vector((gx, y, z_at(v) + 0.03)))
                mu.swept_profile_along(bm, path, prof, mat_index=mat_barge,
                                       up_hint=(1, 0, 0), closed_profile=True)
    return True


# ---------------------------------------------------------------- 脊
def ridge_bar(bm, p0, p1, w=0.46, h=0.62, mat=0):
    """正脊/垂脊（直线）：脊座 + 瓦条 + 脊帽 三级剖面。"""
    prof = _ridge_profile(w, h)
    mu.swept_profile_along(bm, [Vector(p0), Vector(p1)], prof, mat_index=mat,
                           up_hint=(0, 0, 1), closed_profile=True)
    return True


def _ridge_profile(w, h):
    """三级脊剖面：(u=侧宽, w=竖向)。座—收腰—瓦条—脊帽。"""
    return [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, h * 0.30),
            (w * 0.35, h * 0.30), (w * 0.35, h * 0.66), (w * 0.44, h * 0.66),
            (w * 0.44, h * 0.88), (w * 0.30, h), (-w * 0.30, h),
            (-w * 0.44, h * 0.88), (-w * 0.44, h * 0.66), (-w * 0.35, h * 0.66),
            (-w * 0.35, h * 0.30), (-w / 2, h * 0.30)]


def ridge_along_path(bm, path, w=0.32, h=0.40, mat=0):
    """沿折线（含翼角上翘曲线）扫掠脊 —— 垂脊/戗脊用这个，才不会"架空的直杆"。"""
    pts = [Vector(p) for p in path]
    if len(pts) < 2:
        return False
    mu.swept_profile_along(bm, pts, _ridge_profile(w, h), mat_index=mat,
                           up_hint=(0, 0, 1), closed_profile=True)
    return True


def hip_ridge_path(outer, z_eave, inner, z_top, corner, lift=None, n=8):
    """垂脊/戗脊路径：外角(起翘后) → 内角，带分段。corner: 0..3 = 西南/东南/西北/东北。"""
    D = DIM
    lift = D.YIJIAO_RISE if lift is None else lift
    ax0, ay0, ax1, ay1 = outer
    bx0, by0, bx1, by1 = inner
    pts_c = [(ax0, ay0, bx0, by0), (ax1, ay0, bx1, by0),
             (ax0, ay1, bx0, by1), (ax1, ay1, bx1, by1)]
    ax, ay, bx, by = pts_c[corner]
    path = []
    for i in range(n + 1):
        t = i / n
        x = ax + (bx - ax) * t
        y = ay + (by - ay) * t
        z = z_eave + lift * (1.0 - t) ** 2.2 + (z_top - z_eave) * _f_juzhe(t, 1.45)
        path.append(Vector((x, y, z)))
    return path


def eave_course(bm, eave_paths, radius=0.12, seg=6, mat=0, rise=0.02):
    """檐口滴水/瓦当连续带 —— 沿檐口折线的细管。"""
    for si, path in eave_paths.items():
        if len(path) < 2:
            continue
        pts = [Vector((p.x, p.y, p.z - rise)) for p in path]
        mu.swept_tube(bm, pts, radius, segments=seg, mat_index=mat,
                      caps=True, up_hint=(0, 0, 1))
    return True


# ---------------------------------------------------------------- 成品屋顶
def xieshan_roof(bm, outer, z_eave, inner, z_break, gable_x, ridge_y, z_ridge,
                 mat=0, mat_ridge=0, lift=None, add_ridges=True, nu_ridge=1,
                 nv=12):
    """重檐歇山的一个屋面 = 四面裙檐 + 上部两坡 + 正脊 + 4 垂脊 + 滴水带。

    nv：檐口起翘曲线的采样率（v14 起主殿取 16，飞檐更昂扬）。
    """
    D = DIM
    _n0 = len(bm.verts)
    eave = corrugated_skirt(bm, outer, z_eave, inner, z_break,
                            lift=lift, mat=mat, nv=nv)
    gable_body(bm, inner, z_break, ridge_y, z_ridge, gable_x,
               mat=mat, mat_barge=mat)
    eave_course(bm, eave, mat=mat)
    if add_ridges:
        x0, y0, x1, y1 = inner
        # 正脊：骑在两条坡顶的交线上，脊座略陷入屋面
        ridge_bar(bm, Vector((x0 - 0.12, ridge_y, z_ridge - 0.10)),
                  Vector((x1 + 0.12, ridge_y, z_ridge - 0.10)),
                  w=0.62, h=0.94, mat=mat_ridge)
        for ci in range(4):
            p = hip_ridge_path(outer, z_eave, inner, z_break, ci, lift=lift)
            ridge_along_path(bm, p, w=0.34, h=0.42, mat=mat_ridge)
    _weld(bm, _n0, 3.0e-4)
    return eave


def hip_roof(bm, outer, z_eave, ridge_a, ridge_b, z_ridge, mat=0,
             lift=None, mat_ridge=0, add_ridges=True):
    """庑殿顶（副展阁）：inner 退化为一条脊线。"""
    xa, ya = ridge_a
    xb, yb = ridge_b
    inner = (min(xa, xb), ya, max(xa, xb), yb)
    _n0 = len(bm.verts)
    eave = corrugated_skirt(bm, outer, z_eave, inner, z_ridge, mat=mat, lift=lift)
    eave_course(bm, eave, mat=mat)
    if add_ridges:
        ridge_bar(bm, Vector((xa - 0.10, ya, z_ridge - 0.08)),
                  Vector((xb + 0.10, yb, z_ridge - 0.08)),
                  w=0.50, h=0.76, mat=mat_ridge)
        for ci in range(4):
            p = hip_ridge_path(outer, z_eave, inner, z_ridge, ci, lift=lift)
            ridge_along_path(bm, p, w=0.30, h=0.36, mat=mat_ridge)
    _weld(bm, _n0, 3.0e-4)
    return eave
