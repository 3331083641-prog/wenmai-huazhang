"""主殿 hall（v11）—— 面宽 26 / 进深 18，重檐歇山，正脊 16.50（全场景主角）。

坐标（照抄 dim11.py，不得自创）
    x[-13,13] y[-12,6]，南立面在 y=-12，门洞中心 (0,-12) 的 x=0。
    z=0 = 须弥座顶面 = 世界原点；殿内台明 0 → D.TAIJI_H=0.45（本件自己做）。
    室内净高（藻井天光口）12.00；檐口下 6.40 / 上檐 10.90 / 正脊 16.50。

构造次序（宋式：台明→柱础→柱→阑额→普拍枋→斗拱→墙身→檐→屋面→脊→藻井）
    _taiji     殿内台明 z 0→0.45（stone_lite）+ 四边台阶 + 石勒脚 + 门槛门枕
    _columns   24 根柱（R0.42→0.38、1% 侧脚）+ 24 个 stone_lite 覆盆柱础 R0.52
    _beams     阑额 8.90…9.15（0.42×0.25）+ 普拍枋 9.15…9.40（0.55×0.25）
    _dougong   斗拱带 9.40…10.55：按 0.90 一攒排布 + 四角转角铺作
               （wood_dark 栱身 / crimson 斗心 0.18 见方 / celadon 昂嘴拱头 0.05 线）
               南东西三面每攒另有耍头 + 令拱上 3 散斗，转角另有角华拱 + 由昂；
               北面省略（不可见），栱眼壁上下各一道 celadon 0.06 线脚
    _walls     南立面 6 扇格扇门（wood_dark 框 + glass 芯 + bronze 门钉铺首）
               + 次梢间槛窗 + 两山 3 樘 + 后墙 4.2m 内门
    _lower_eave 下檐 corrugated_skirt  (x±16.2, y −15.2…9.2) 6.40 → 8.80
    _upper_roof 上檐 xieshan_roof      (x±15.4, y −13.6…7.6) 檐 10.90 / 折 13.60 / 脊 16.50
    _eave_detail 封檐板 + 方椽头 + 瓦当滴水
    _gables    山花四件套（wood_lite 板 / wall_white 压边 / bronze 悬鱼惹草）
    _chiwen    正脊两端 bronze 卧式鸱吻（吻顶 ≤ 16.50）
    _caisson   8×8m 十一层逐层内收藻井 + 1.8×1.8 天光口（全部 ≤ 12.00）

硬约束（自检口径）
    · tri ≤ 110 000
    · max(z) = 16.500 ± 0.02 —— 正脊帽顶 = z_ridge(15.66) + 0.84，鸱吻不得越过它
    · min(z) = 0.000 —— 台明坐落在须弥座顶面，本件不得向下挖

工程坑（都是渲图反推出来的，别重复踩）
    1. mu.prism 的挤出轴向会换基
       沿 +X 挤出：u→+y, w→+z
       沿 +Y 挤出：u→**−x**, w→+z   ← 最坑的一条，世界 (x,z) 剖面必须先取负
       沿 +Z 挤出：u→**−y**, w→**+x** ← 四角 45° 铺作就是踩这个坑飞出去的
       本文件的对策：所有镜像风险走 _ccw 规整绕序 + 显式取负，
       _prism_xz_y / _prism_yz_x 封装好了，新代码请用它们，不要直接调 mu.prism。
    2. 栱眼壁顶不能超过 10.92
       x=±13 一带已在歇山撒头斜面上，屋面标高从中脊向外一路掉；
       板顶写到 11.30 就会从瓦面捅出来，渲成屋面上一条斜的木色虚线。
       定位技巧：用"只保留 roof_upper 的隔离渲染"反证，线消失即说明是别的对象。
    3. 局部坐标做门窗/器具时，y 一定要加基准
       _door 的门扇曾忘加 HY0，整扇门站在殿中央 x=0。
       凡"以墙面为 0 起算"的写法，落世界坐标时必须显式 +HY0 / +HY1 / ±HX。
    4. mu.revolve 的侧面绕序朝内
       剖面要倒过来喂才朝外；补盖时底盖取 rings[i][-1]、顶盖取 [i][0]。
"""
from __future__ import annotations

import math
import bmesh
import bpy

from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from ..dim13 import DIM13 as D
from .. import mesh_util as mu
from .. import roofkit as rk

TAU = math.pi * 2.0

# ============================================================ 派生常量
HX = D.HALL_HX                        # 13.0  半宽
HY0 = D.HALL_Y0                       # -12.0 南立面
HY1 = D.HALL_Y1                       # 6.0   北墙
HJ = D.TAIJI_H                        # 0.45  殿内台明顶（室内地面）
WT = 0.36                             # 墙厚
HW = WT * 0.5                         # 0.18
ARCH0, ARCH1 = D.ARCH_Z0, D.ARCH_Z1   # 8.90 / 9.15 阑额
PUT1 = ARCH1 + D.PUPai_H              # 9.40 普拍枋顶
DG0, DG1 = PUT1, D.DOUGONG_Z0 + D.DOUGONG_H     # 9.40 / 10.55 斗拱带
COL_TOP = D.COL_H                     # 9.60 柱顶（顶端埋进斗拱带）
WALL_TOP = D.LOWER_ROOF_TOP_Z         # 8.80 外墙止于下檐内缘
LOW_Z = D.LOWER_EAVE_Z                # 6.40 下檐檐口
UP_Z = D.UPPER_EAVE_Z                 # 10.90 上檐檐口
Z_RIDGE_IN = D.RIDGE_Z - 0.84         # 15.66 → ridge_bar 脊帽顶 = 16.50
GABLE_X = D.GABLE_X                   # 7.80
RIDGE_Y = D.HALL_CY                   # -3.0 脊线
CWALL_TOP = UP_Z + 0.02               # 10.92 栱眼壁顶
#   只能停在 10.92：上檐是歇山，x=±13 一带己经进入"撒头"斜面，屋面标高
#   从中脊一路往下掉，11.30 会在四角附近捅穿屋壳，渲出来就是屋面上一道
#   木色虚线（踩过这个坑）。10.92 与上檐檐口 10.90 齐平，稳在屋壳之下。
DGW = 0.90                            # 斗拱攒档

# 台明（比柱网外扩 1.20，四边留台阶位）
TJX = HX + 1.20                       # 14.20
TJY0 = HY0 - 1.20                     # -13.20
TJY1 = HY1 + 1.20                     # 7.20
STEP_R, STEP_T = 0.15, 0.33           # 台明台阶踢/踏

# 柱网：16 根檐柱 + 8 根内部柱
CXS = (-HX, -D.COL_X[2], -D.COL_X[1], D.COL_X[1], D.COL_X[2], HX)
CYS = tuple(D.COL_Y)

# 南立面开间（明间 6.5 / 次间 4.9 / 梢间 4.85）
BAY_MING = (-D.COL_X[1], D.COL_X[1])
BAY_CI = (D.COL_X[1], D.COL_X[2])
BAY_SHAO = (D.COL_X[2], HX)

# 藻井
CAIS = D.CAISSON_SIZE * 0.5           # 4.0  井口半宽
CAIS_TOP = D.CAISSON_TOP              # 12.00
CAIS_BOT = WALL_TOP + 0.80            # 9.60 天花板标高
CAIS_N = D.CAISSON_LAYERS             # 11
SKY = D.SKYLIGHT * 0.5                # 0.90 天光口半宽


# ============================================================ 小工具
def _box(bm, x0, x1, y0, y1, z0, z1):
    """轴对齐盒（自动排序端点）。"""
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    if z1 < z0:
        z0, z1 = z1, z0
    return mu.box_mm(bm, x0, x1, y0, y1, z0, z1)


def _ccw(pts):
    """把 (u,w) 剖面规整为逆时针（prism 要求逆时针 → 侧法线朝外）。"""
    a = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        a += x0 * y1 - x1 * y0
    return pts if a > 0.0 else list(reversed(pts))


def _prism_xz_y(bm, prof_xz, y0, y1):
    """世界 (x,z) 剖面沿 **+Y** 挤出。

    prism 在 |n.z|<0.9 时取 ref=(0,0,1)、u_ax=ref×n：
      沿 +Y 挤出 → u→−x；沿 −Y 挤出 → u→+x。
    挤出方向一翻 u 轴就镜像 —— 端点必须先排序，剖面绕序再交给 _ccw 兜底。
    """
    if y1 < y0:
        y0, y1 = y1, y0
    mu.prism(bm, _ccw([(-p[0], p[1]) for p in prof_xz]),
             (0.0, y0, 0.0), (0.0, y1, 0.0))


def _prism_yz_x(bm, prof_yz, x0, x1):
    """世界 (y,z) 剖面沿 **+X** 挤出（沿 +X 挤出时 u_ax=(0,1,0)，u 即世界 y）。"""
    if x1 < x0:
        x0, x1 = x1, x0
    mu.prism(bm, _ccw([tuple(p) for p in prof_yz]),
             (x0, 0.0, 0.0), (x1, 0.0, 0.0))


def _taper_box(bm, c, t, n, bu, bv, tu, tv, z0, z1):
    """局部正交系下的收分方盒（下口 bu×bv、上口 tu×tv）。

    t = 沿墙方向、n = 朝外方向，两者均为轴对齐单位向量（±1,0）。
    斗拱的"斗"要下小上大，所以不能直接用 _box。
    """
    ring0, ring1 = [], []
    for (su, sv) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        ring0.append(bm.verts.new((c[0] + t[0] * bu * su + n[0] * bv * sv,
                                   c[1] + t[1] * bu * su + n[1] * bv * sv, z0)))
        ring1.append(bm.verts.new((c[0] + t[0] * tu * su + n[0] * tv * sv,
                                   c[1] + t[1] * tu * su + n[1] * tv * sv, z1)))
    mu.bridge_rings(bm, ring0, ring1, closed=True)
    mu.cap_ring(bm, ring0, flip=True)
    mu.cap_ring(bm, ring1, flip=False)


def _lbox(bm, c, t, n, u0, u1, v0, v1, z0, z1):
    """Oriented solid, retaining the true local basis at 45-degree corners."""
    rings = []
    for z in (z0, z1):
        rings.append([bm.verts.new((c[0]+t[0]*u+n[0]*v,
                                    c[1]+t[1]*u+n[1]*v, z))
                      for u, v in ((u0,v0),(u1,v0),(u1,v1),(u0,v1))])
    mu.bridge_rings(bm, rings[0], rings[1], closed=True)
    mu.cap_ring(bm, rings[0], flip=True)
    mu.cap_ring(bm, rings[1], flip=False)


def _ring_solid(bm, x0, x1, y0, y1, ix0, ix1, iy0, iy1, z0, z1):
    """Closed rectangular ring between z0..z1, mitred at its four corners.

    四块板拼接会在角部互相插入；栱眼壁与天花板压边都用整环，角部由环体自身闭合。
    """
    outer0 = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    inner0 = [(ix0, iy0), (ix1, iy0), (ix1, iy1), (ix0, iy1)]
    lo = [bm.verts.new((x, y, z0)) for x, y in outer0]
    hi = [bm.verts.new((x, y, z1)) for x, y in outer0]
    li = [bm.verts.new((x, y, z0)) for x, y in inner0]
    hi2 = [bm.verts.new((x, y, z1)) for x, y in inner0]
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))       # 外壁
        bm.faces.new((li[j], li[i], hi2[i], hi2[j]))     # 内壁
        bm.faces.new((hi[i], hi[j], hi2[j], hi2[i]))     # 顶环
        bm.faces.new((li[i], li[j], lo[j], lo[i]))       # 底环
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def _spread(a, b, step, inset=0.30):
    """在 [a+inset, b-inset] 内等距排 n 份，返回各份中心。"""
    lo, hi = a + inset, b - inset
    n = max(1, int(round((hi - lo) / step)))
    return [lo + (hi - lo) * (i + 0.5) / n for i in range(n)]


def _column(bm, cx, cy, z0, z1, r0, r1, lean=(0.0, 0.0), seg=16):
    """带收分与侧脚的圆柱。"""
    ring0, ring1 = [], []
    for i in range(seg):
        a = TAU * i / seg
        c, s = math.cos(a), math.sin(a)
        ring0.append(bm.verts.new((cx + c * r0, cy + s * r0, z0)))
        ring1.append(bm.verts.new((cx + lean[0] + c * r1,
                                   cy + lean[1] + s * r1, z1)))
    mu.bridge_rings(bm, ring0, ring1, closed=True)
    mu.cap_ring(bm, ring0, flip=True)
    mu.cap_ring(bm, ring1, flip=False)


def _revolve_solid(bm, cx, cy, prof, z0=0.0, segments=12):
    """绕 Z 轴回转成闭合实体（底/顶各补一个 n 边形）。

    坑：mesh_util.revolve 的侧面绕序在"自下而上"喂剖面时朝内，
    所以这里把剖面倒过来喂，侧面才朝外；补盖时底盖取 rings[i][-1]、顶盖取 [i][0]。
    """
    rings = mu.revolve(bm, list(reversed(list(prof))), (cx, cy, z0),
                       segments=segments)
    n = len(rings)
    mu.face(bm, list(reversed([rings[i][-1] for i in range(n)])))
    mu.face(bm, [rings[i][0] for i in range(n)])


def _wall_course(bm, c, d, za, zb, t0, t1, axis):
    """Fit masonry between adjacent polygonal shafts and their two stone bases."""
    stations = CXS if axis == "y" else CYS
    fixed = (t0+t1)/2
    foot = HJ+.185
    stone = [(HJ+.02,.52),(HJ+.065,.518),(HJ+.105,.500),
             (HJ+.14,.470),(HJ+.17,.435),(foot,.420)]
    zs = sorted({za,zb} | {z for z,_ in stone if za < z < zb}
                | {foot+.5*i for i in range(1,18) if za<foot+.5*i<zb})

    def polygon(u,z,mid):
        if mid < HJ+.02:
            return [(u+du,fixed+dt) for du,dt in
                    ((-.53,-.53),(.53,-.53),(.53,.53),(-.53,.53))]
        if mid < foot:
            k = next(i for i in range(len(stone)-1) if stone[i][0] <= mid <= stone[i+1][0])
            a,r = stone[k]
            b,q = stone[k+1]
            radius = r+(q-r)*(z-a)/(b-a)
            if k==len(stone)-2:
                radius += .016*(z-a)/(b-a)
            ct,cu,n = fixed,u,12
        else:
            px,py = (u,fixed) if axis=="y" else (fixed,u)
            head,lean,_ = _column_head(px,py)
            f = (z-foot)/(head-foot)
            radius = D.COL_R+(D.COL_R_TOP-D.COL_R)*f
            cu = u+f*(lean.x if axis=="y" else lean.y)
            ct = fixed+f*(lean.y if axis=="y" else lean.x)
            n = 32
        return [(cu+radius*math.cos(TAU*i/n),ct+radius*math.sin(TAU*i/n)) for i in range(n)]

    def side(poly,t,right):
        xs = [a+(x-a)*(t-b)/(y-b) for (a,b),(x,y) in zip(poly,poly[1:]+poly[:1])
              if abs(y-b)>1e-9 and min(b,y)-1e-8 <= t <= max(b,y)+1e-8]
        return max(xs)+.0035 if right else min(xs)-.0035

    for col0,col1 in zip(stations,stations[1:]):
        if col0>=d or col1<=c: continue
        for zlo,zhi in zip(zs,zs[1:]):
            profiles = [(polygon(col0,z,(zlo+zhi)/2),polygon(col1,z,(zlo+zhi)/2)) for z in (zlo,zhi)]
            ts = sorted({t0,t1} | {round(t,6) for pair in profiles for poly in pair for _,t in poly
                                    if t0+.00002<t<t1-.00002})
            sections=[]
            for t in ts:
                pairs=[]
                for z,(left,right) in zip((zlo,zhi),profiles):
                    a,b=max(c,side(left,t,True)),min(d,side(right,t,False))
                    if b<=a: break
                    pairs.extend([(a,t,z),(b,t,z)])
                if len(pairs)!=4: break
                sections.append([bm.verts.new((u,t,z) if axis=="y" else (t,u,z))
                                 for u,t,z in (pairs[0],pairs[1],pairs[3],pairs[2])])
            if len(sections)!=len(ts):
                if sections: raise ValueError("Partial wall bay, check its aperture")
                continue
            for a,b in zip(sections,sections[1:]): mu.bridge_rings(bm,a,b,closed=True)
            mu.cap_ring(bm,sections[0],flip=True)
            mu.cap_ring(bm,sections[-1])
    mu.recalc_normals(bm)


def _wall_panels(bm, u0, u1, z0, z1, t0, t1, holes, axis="y"):
    """把一片墙按矩形洞口切成若干实心块。

    axis='y'：墙面法线沿 Y（u=x, t=y）；axis='x'：法线沿 X（u=y, t=x）。
    holes: [(hu0, hu1, hz0, hz1)]，可跨多个高度带。
    """
    zs = sorted({round(z0, 6), round(z1, 6)}
                | {round(h[2], 6) for h in holes}
                | {round(h[3], 6) for h in holes})
    for za, zb in zip(zs, zs[1:]):
        if zb - za < 1e-6:
            continue
        segs = [(min(h[0], h[1]), max(h[0], h[1])) for h in holes
                if h[2] <= za + 1e-9 and h[3] >= zb - 1e-9]
        spans = [(u0, u1)]
        for a, b in segs:                       # 逐洞求差集
            nxt = []
            for c, d in spans:
                if b <= c or a >= d:
                    nxt.append((c, d))
                    continue
                if c < a:
                    nxt.append((c, a))
                if b < d:
                    nxt.append((b, d))
            spans = nxt
        for c, d in spans:
            if d - c < 1e-6:
                continue
            _wall_course(bm,c,d,za,zb,t0,t1,axis)


def _lattice_x(bm, bmg, x0, x1, z0, z1, yc, pitch=0.24, hstep=0.62):
    """法线沿 Y 的木格扇（0.04 方棂条；bmg 给则同时出一片玻璃）。"""
    f, d, b = 0.10, 0.13, 0.04
    y0, y1 = yc - d / 2, yc + d / 2
    _box(bm, x0, x0 + f, y0, y1, z0, z1)
    _box(bm, x1 - f, x1, y0, y1, z0, z1)
    _box(bm, x0 + f, x1 - f, y0, y1, z0, z0 + f)
    _box(bm, x0 + f, x1 - f, y0, y1, z1 - f, z1)
    ix0, ix1, iz0, iz1 = x0 + f, x1 - f, z0 + f, z1 - f
    n = max(1, int(round((ix1 - ix0) / pitch)))
    for i in range(1, n):
        x = ix0 + (ix1 - ix0) * i / n
        _box(bm, x - b / 2, x + b / 2, yc - 0.03, yc + 0.04, iz0, iz1)
    m = max(1, int(round((iz1 - iz0) / hstep)))
    for k in range(1, m):
        z = iz0 + (iz1 - iz0) * k / m
        _box(bm, ix0, ix1, yc - 0.03, yc + 0.04, z - b / 2, z + b / 2)
    if bmg is not None:
        _box(bmg, ix0, ix1, yc + 0.045, yc + 0.062, iz0, iz1)


def _lattice_y(bm, bmg, y0, y1, z0, z1, xc, pitch=0.24, hstep=0.62):
    """法线沿 X 的木格扇。"""
    f, d, b = 0.10, 0.13, 0.04
    x0, x1 = xc - d / 2, xc + d / 2
    _box(bm, x0, x1, y0, y0 + f, z0, z1)
    _box(bm, x0, x1, y1 - f, y1, z0, z1)
    _box(bm, x0, x1, y0 + f, y1 - f, z0, z0 + f)
    _box(bm, x0, x1, y0 + f, y1 - f, z1 - f, z1)
    iy0, iy1, iz0, iz1 = y0 + f, y1 - f, z0 + f, z1 - f
    n = max(1, int(round((iy1 - iy0) / pitch)))
    for i in range(1, n):
        y = iy0 + (iy1 - iy0) * i / n
        _box(bm, xc - 0.03, xc + 0.04, y - b / 2, y + b / 2, iz0, iz1)
    m = max(1, int(round((iz1 - iz0) / hstep)))
    for k in range(1, m):
        z = iz0 + (iz1 - iz0) * k / m
        _box(bm, xc - 0.03, xc + 0.04, iy0, iy1, z - b / 2, z + b / 2)
    if bmg is not None:
        _box(bmg, xc + 0.045, xc + 0.062, iy0, iy1, iz0, iz1)


def _path_samples(path, step, z_off=0.0):
    """沿檐口折线按弧长等距采样 → [(点, 单位切向, 单位外法线)]。"""
    pts = [Vector(p) for p in path]
    if len(pts) < 2:
        return []
    acc = [0.0]
    for i in range(1, len(pts)):
        acc.append(acc[-1] + (pts[i] - pts[i - 1]).length)
    L = acc[-1]
    if L < 0.05:
        return []
    n = max(1, int(round(L / step)))
    out = []
    Z = Vector((0.0, 0.0, 1.0))
    for k in range(n):
        s = (k + 0.5) * L / n
        i = 1
        while i < len(acc) - 1 and acc[i] < s:
            i += 1
        seg = acc[i] - acc[i - 1]
        f = 0.5 if seg < 1e-9 else (s - acc[i - 1]) / seg
        p = pts[i - 1].lerp(pts[i], f)
        t = pts[i] - pts[i - 1]
        if t.length < 1e-9:
            continue
        t.normalize()
        nrm = t.cross(Z)
        if nrm.length < 1e-6:
            continue
        nrm.normalize()
        out.append((p + Vector((0.0, 0.0, z_off)), t, nrm))
    return out


def _smooth_path(path, iters=3):
    """相邻三点加权平均（端点保持），抹掉 corrugated 檐口的瓦垄锯齿。"""
    pts = [Vector(p) for p in path]
    n = len(pts)
    if n < 3:
        return pts
    for _ in range(iters):
        out = [pts[0]]
        for i in range(1, n - 1):
            out.append((pts[i - 1] + pts[i] * 2.0 + pts[i + 1]) * 0.25)
        out.append(pts[-1])
        pts = out
    return pts


def _poly_fan(bm, c, t, n, segs=6, phase=0.0):
    """以 c 为心、t/up 为基向量张成 segs 边正多边形扇面（segs tri）。"""
    up = Vector((0.0, 0.0, 1.0))
    hub = bm.verts.new(c)
    ring = []
    for j in range(segs):
        a = phase + TAU * j / segs
        ring.append(bm.verts.new(c + t * (math.cos(a) * n) + up * (math.sin(a) * n)))
    for j in range(segs):
        mu.face(bm, [hub, ring[j], ring[(j + 1) % segs]])


# ============================================================ 1 台明与台阶
def _taiji(C):
    """殿内台明 z 0 → 0.45（须弥座顶面之上），四边留台阶位。

    殿内地面就是本台明的顶面（stone_lite），室内家具直接落在 z=0.45。
    """
    coll = ("主殿", "台明")

    # ---- 台明主体 ----
    bm = mu.new_bm()
    _box(bm,-TJX+.10,TJX-.10,TJY0+.10,TJY1-.10,0,.26)
    _box(bm,-TJX,TJX,TJY0,TJY1,.26,HJ)
    C.bm_obj(bm, "hall_taiji", "foundation", coll,
             cn="殿内台明（顶面 z=0.45 = 室内地面）", mat="stone_lite", uv=1.0)

    # ---- 石勒脚：四周压一道 stone_dark 圭角，高 0.26 ----
    bm = mu.new_bm()
    e = 0.035
    for sign in (-1,1):
        # Cut back the projecting toe at every stair cheek and butt the riser.
        for a,b,proj in ((TJY0-e,RIDGE_Y-2,e),(RIDGE_Y-2,RIDGE_Y+2,0),
                         (RIDGE_Y+2,TJY1+e,e)):
            _box(bm,sign*(TJX-.10),sign*(TJX+proj),a,b,0,.26)
    for y,sign,width in ((TJY0,-1,3.92),(TJY1,1,3.50)):
        for a,b,proj in ((-TJX+.10,-width,e),(-width,width,0),(width,TJX-.10,e)):
            _box(bm,a,b,y-sign*.10,y+sign*proj,0,.26)
    C.bm_obj(bm, "hall_taiji_ledger", "foundation", coll,
             cn="台明勒脚（青灰圭角）", mat="stone_dark", uv=1.0)

    # ---- 四边台阶：南面 3 级（宽 7.0），东西北各 2 级小阶 ----
    bm = mu.new_bm()
    s = 3.50
    # 南：y −13.20 → −13.86（两级踏面 0.33 + 台明顶面 = 3 级）
    _box(bm, -s, s, TJY0 - 2 * STEP_T, TJY0 - STEP_T, 0.0, STEP_R)
    _box(bm, -s, s, TJY0 - STEP_T, TJY0, 0.0, 2 * STEP_R)
    # 北：y 7.20 → 7.86
    _box(bm, -s, s, TJY1, TJY1 + STEP_T, 0.0, 2 * STEP_R)
    _box(bm, -s, s, TJY1 + STEP_T, TJY1 + 2 * STEP_T, 0.0, STEP_R)
    # 东 / 西：x ±14.20 → ±14.86
    for sx in (-1, 1):
        _box(bm, sx * TJX, sx * (TJX + STEP_T), RIDGE_Y - 2.0, RIDGE_Y + 2.0, 0.0, 2 * STEP_R)
        _box(bm, sx * (TJX + STEP_T), sx * (TJX + 2 * STEP_T), RIDGE_Y - 2.0, RIDGE_Y + 2.0, 0.0, STEP_R)

    # ---- 垂带石：南面台阶两侧的斜条石 ----
    for sx in (-1, 1):
        _prism_yz_x(bm, [(TJY0 - 2 * STEP_T - 0.10, 0.0),
                         (TJY0, 0.0), (TJY0, HJ + 0.02),
                         (TJY0 - 2 * STEP_T - 0.10, STEP_R + 0.02)],
                    sx * s, sx * (s + 0.42))
    C.bm_obj(bm, "hall_steps", "foundation", coll,
             cn="台明四边台阶 + 垂带石", mat="stone_lite", uv=1.0)

    # ---- 门槛石 / 门枕石（明间门洞 6.5 宽）----
    bm = mu.new_bm()
    hw = D.DOOR_W / 2 - .55 - .18
    _box(bm, -hw, hw, HY0 - 0.24, HY0 + 0.16, HJ, HJ + 0.13)
    for sx in (-1, 1):
        _box(bm, sx * hw, sx * (hw + 0.18), HY0 - 0.26, HY0 + 0.18, HJ, HJ + 0.34)
    C.bm_obj(bm, "hall_threshold", "detail", ("主殿", "细部"),
             cn="门槛石 / 门枕石", mat="stone_dark", uv=1.0)


# ============================================================ 2 柱网与柱础
def _column_head(x, y):
    on_end = y in (HY0, HY1)
    on_side = abs(abs(x) - HX) < 1e-9
    rise = .04 if on_end and on_side else 0.
    top = COL_TOP + rise if on_end else min(COL_TOP, CAIS_BOT - .052)
    foot = HJ + .185
    direction = Vector((-x, RIDGE_Y-y)).normalized()
    lean = direction * ((top-foot)*.008 if on_end or on_side else 0.)
    return top, lean, rise


def _columns(C):
    coll = ("主殿", "柱网")
    r0, r1 = D.COL_R, D.COL_R_TOP

    # 16 根檐柱：南 6 + 北 6 + 东 2 + 西 2（外围一圈）
    #  8 根内柱：x=±COL_X[1] / ±COL_X[2] 与 y=CYS[1] / CYS[2] 的 2×4 交点（v13 由 dim13 推导）
    pts = []
    for y in CYS:
        for x in CXS:
            on_edge = (y in (HY0, HY1)) or (abs(abs(x) - HX) < 1e-9)
            inner = (abs(abs(x) - D.COL_X[1]) < 1e-9 or abs(abs(x) - D.COL_X[2]) < 1e-9) \
                and y in (CYS[1], CYS[2])
            if on_edge or inner:
                pts.append((x, y))

    bm = mu.new_bm()
    # 覆盆柱础自 HJ+0.02 起，高 0.165；柱脚精确落在其顶面，不做穿插。
    h0 = HJ + 0.02 + 0.165
    for x, y in pts:
        top, lean, _ = _column_head(x, y)
        shoulder = ARCH0 + _column_head(x,y)[2]
        f=(shoulder-h0)/(top-h0)
        endx,endy=x+lean.x*f,y+lean.y*f
        _column(bm,x,y,h0,shoulder,r0,r0+(r1-r0)*f,lean=lean*f,seg=32)
        # The narrower tenon stays enclosed by the two crossing beams.
        _box(bm,endx-.075,endx+.075,endy-.075,endy+.075,shoulder,PUT1-.012)
    C.bm_obj(bm, "hall_col", "hall", coll, cn="柱24根：侧脚、生起、柱肩及150毫米方榫",
             mat="wood_dark", uv=0.8)

    # ---- 覆盆柱础：stone_lite R0.52（覆盆锥面）+ 1.06 方座 ----
    prof = [(0.52, 0.00), (0.518, 0.045), (0.500, 0.085),
            (0.470, 0.120), (0.435, 0.150), (0.420, 0.165)]
    bm = mu.new_bm()
    for x, y in pts:
        _revolve_solid(bm, x, y, prof, z0=HJ + 0.02, segments=12)
    C.bm_obj(bm, "hall_col_base", "hall", coll,
             cn="覆盆柱础（汉白玉 R0.52）", mat="stone_lite", uv=1.0)

    bm = mu.new_bm()
    for x, y in pts:
        # 方座顶与覆盆底在 HJ+0.02 平接，避免 40mm 实体互穿。
        _box(bm, x - 0.53, x + 0.53, y - 0.53, y + 0.53, HJ, HJ + 0.02)
    C.bm_obj(bm, "hall_col_plinth", "hall", coll, cn="柱础方座压线",
             mat="stone_lite", uv=1.0)


# ============================================================ 3 阑额 / 普拍枋
def _beams(C):
    bm = mu.new_bm()
    rows = [[(x, y) for x in CXS] for y in CYS]
    rows.extend([[(x, y) for y in CYS] for x in CXS])
    for row in rows:
        sideways = Vector((0, 1, 0)) if row[0][1] == row[-1][1] else Vector((1, 0, 0))
        for half, bottom, upper in ((.21, ARCH0, ARCH1), (.275, ARCH1, PUT1)):
            rings = []
            along=Vector((1,0,0)) if row[0][1]==row[-1][1] else Vector((0,1,0))
            for ix,(x,y) in enumerate(row):
                _, offset, rise = _column_head(x, y)
                center = Vector((x+offset.x, y+offset.y, rise))
                if ix in (0,len(row)-1): center+=along*(.18 if ix else -.18)
                rings.append([bm.verts.new(center + side*sideways + Vector((0,0,min(z, DG0-.001-rise))))
                              for side,z in ((-half,bottom),(half,bottom),(half,upper),(-half,upper))])
            for left, right in zip(rings, rings[1:]):
                mu.bridge_rings(bm, left, right, closed=True)
            mu.cap_ring(bm, rings[0], flip=True)
            mu.cap_ring(bm, rings[-1])
    mu.recalc_normals(bm)
    C.bm_obj(bm, "hall_beams", "hall", ("主殿", "梁架"),
             cn="阑额 8.90–9.15 / 普拍枋 9.15–9.40", mat="wood_dark", uv=0.8)


# ============================================================ 4 斗拱带
def _dg_finish(bm, verts):
    """Bevel only this new closed solid; never repeatedly bevel existing geometry."""
    edges=list(dict.fromkeys(e for v in verts for e in v.link_edges))
    faces=list({f for e in edges for f in e.link_faces})
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for face in faces:
        face.normal_update()
    sharp=[e for e in edges if len(e.link_faces)==2 and e.calc_face_angle(0)>.38]
    if sharp:
        bmesh.ops.bevel(bm, geom=sharp, offset=.002, segments=2, affect='EDGES', clamp_overlap=True)


def _dg_prism(bm, c, t, n, profile, width, center, along="u"):
    """Extrude a sampled curved outline in the actual local basis."""
    rings=[]
    for lateral in (center-width/2, center+width/2):
        ring=[]
        for a,z in profile:
            u,v=(a,lateral) if along=="u" else (lateral,a)
            ring.append(bm.verts.new((c[0]+t[0]*u+n[0]*v,
                                       c[1]+t[1]*u+n[1]*v,z)))
        rings.append(ring)
    mu.bridge_rings(bm,rings[0],rings[1],closed=True)
    mu.cap_ring(bm,rings[0],flip=True)
    mu.cap_ring(bm,rings[1],flip=False)
    _dg_finish(bm,rings[0]+rings[1])


def _dg_wave(bm,c,t,n,half,center,z,width=.16,along="u"):
    # Five sampled scallops and a continuous rolled underside, not stacked boxes.
    profile=[]
    for i in range(81):
        q=-1+2*i/80
        bottom=z+.025+.065*abs(q)**1.6+.025*(1+math.cos(5*math.pi*q))/2
        profile.append((half*q,bottom))
    profile += [(half,z+.19),(-half,z+.19)]
    _dg_prism(bm,c,t,n,profile,width,center,along)


def _dg_ludou(bm,c,t,n,z):
    """Single closed tapered block with a real orthogonal cross-shaped top recess.
    Internal cell faces are never emitted. Four sloped ears remain above the slot.
    """
    heights=(z,z+.16,z+.26)
    radii=(.20,.24,.26)
    slot=.075
    cache={}
    def v(i,j,k):
        key=(i,j,k)
        if key not in cache:
            xy=(-radii[k],-slot,slot,radii[k])
            u,w=xy[i],xy[j]
            cache[key]=bm.verts.new((c[0]+t[0]*u+n[0]*w,c[1]+t[1]*u+n[1]*w,heights[k]))
        return cache[key]
    cells={(i,j,k) for k in range(2) for i in range(3) for j in range(3)
           if k==0 or (i!=1 and j!=1)}
    faces=[((-1,0,0),[(0,0,0),(0,0,1),(0,1,1),(0,1,0)]),
           ((1,0,0),[(1,0,0),(1,1,0),(1,1,1),(1,0,1)]),
           ((0,-1,0),[(0,0,0),(1,0,0),(1,0,1),(0,0,1)]),
           ((0,1,0),[(0,1,0),(0,1,1),(1,1,1),(1,1,0)]),
           ((0,0,-1),[(0,0,0),(0,1,0),(1,1,0),(1,0,0)]),
           ((0,0,1),[(0,0,1),(1,0,1),(1,1,1),(0,1,1)])]
    for i,j,k in sorted(cells):
        for (dx,dy,dz),corners in faces:
            if (i+dx,j+dy,k+dz) not in cells:
                bm.faces.new([v(i+a,j+b,k+d) for a,b,d in corners])
    _dg_finish(bm,cache.values())


def _dg_set(bw,bc,bl,c,t,n,dt=True):
    """Five-puzuo study: slotted ludou, rolled arms, sparse blocks, 30° xiaang."""
    z=DG0
    _dg_ludou(bw,c,t,n,z)
    # Two directions at distinct half-lap elevations, not coincident solid bars.
    _dg_wave(bw,c,t,n,.44,.0,z+.163,width=.142)
    _dg_wave(bw,c,t,n,.34,.0,z+.357,width=.142,along="v")
    for u,v in ((-.31,0),(.31,0),(0,.29)):
        cc=(c[0]+t[0]*u+n[0]*v,c[1]+t[1]*u+n[1]*v)
        _taper_box(bw,cc,t,n,.065,.065,.085,.085,z+.55,z+.65)
    _dg_wave(bw,c,t,n,.38,.29,z+.654,width=.16)
    # A single inclined, cut-nose solid. dz/dv = -tan(30 degrees).
    a,b=.16,.87
    slope=math.tan(math.radians(30))
    top=z+.85
    profile=[(a,top-.12),(b-.025,top-slope*(b-a)-.12),
             (b,top-slope*(b-a)-.08),(b,top-slope*(b-a)),(a,top)]
    _dg_prism(bw,c,t,n,profile,.12,0,along="v")
    _dg_wave(bw,c,t,n,.43,.36,z+.849,width=.16)
    for u in (-.30,0,.30):
        cc=(c[0]+t[0]*u+n[0]*.36,c[1]+t[1]*u+n[1]*.36)
        _taper_box(bw,cc,t,n,.045,.045,.055,.055,z+1.042,z+1.12)
    # Applied colours are seated 1 mm in the tapered face and cut arm ends.
    profile=[(.209,.04),(.212,.04),(.23825,.145),(.23525,.145)]
    rings=[[bc.verts.new((c[0]+u*t[0]+d*n[0],c[1]+u*t[1]+d*n[1],z+h))
            for d,h in profile] for u in (-.08,.08)]
    mu.bridge_rings(bc,*rings,closed=True)
    mu.cap_ring(bc,rings[0],flip=True)
    mu.cap_ring(bc,rings[1])
    _lbox(bl,c,t,n,-.36,.36,.439,.442,z+.98,z+1.025)
    tip=top-slope*(b-a)
    _lbox(bl,c,t,n,-.05,.05,b-.001,b+.002,tip-.065,tip-.015)


def _dougong(C):
    """四边五铺作；彩层靠实栱头，栱眼壁的两道线脚直接赋面材质。"""
    coll = ("主殿", "斗拱")

    bw, bc, bl = mu.new_bm(), mu.new_bm(), mu.new_bm()
    sides = (((0, -1), (1, 0), -HX, HX, False, HY0),      # 南：n=(0,-1) t=(1,0)
             ((0, 1), (-1, 0), -HX, HX, False, HY1),      # 北
             ((1, 0), (0, 1), HY0, HY1, True, HX),        # 东
             ((-1, 0), (0, -1), HY0, HY1, True, -HX))     # 西
    for (n, t, a, b, is_x, fixed) in sides:
        # 北面（n=(0,1) 且非 x 向）在殿后，永远看不到 → 省掉耍头与散斗
        dt = is_x or n[1] <= 0
        for u in _spread(a, b, DGW, inset=0.45):
            c = (fixed, u) if is_x else (u, fixed)
            _dg_set(bw, bc, bl, c, t, n, dt)

    # One properly rotated corner set, clear of the nearest straight sets.
    for sx in (-1,1):
        for sy in (-1,1):
            root=math.sqrt(.5)
            c=(sx*HX,HY0 if sy<0 else HY1)
            n=(sx*root,sy*root)
            t=(-n[1],n[0])
            _dg_set(bw,bc,bl,c,t,n,True)

    C.bm_obj(bw, "hall_dougong", "hall", coll,
             cn="斗拱（按 0.90 一攒 + 四角转角铺作）", mat="wood_dark", uv=0.7)
    C.bm_obj(bc, "hall_dg_crimson", "hall", coll,
             cn="斗拱朱砂斗心 0.18", mat="crimson", uv=0.5, flat=True)
    C.bm_obj(bl, "hall_dg_celadon", "hall", coll,
             cn="斗拱青绿拱头 / 昂嘴 0.05 线", mat="celadon", uv=0.5, flat=True)

    # ---- 栱眼壁 ----
    # 宋式栱眼壁是"斗拱带以上、檐口以下"的暗板，不是通高的整墙。
    # 旧版从 8.80 封到 11.30、厚 0.22 压在柱中线上，把斗拱（栌斗背面 -0.26、
    # 昂到 +0.87）整片穿进去，审计报 13,044 面对相交 —— 这是板位错了，不是榫卯。
    # 现在只填斗拱顶（10.55）与栱眼壁顶（10.92）之间的 0.37 m，退到墙厚内 0.10…0.20。
    bm = mu.new_bm()
    _ring_solid(bm,
                -HX + 0.14, HX - 0.14, HY0 + 0.14, HY1 - 0.14,
                -HX + 0.24, HX - 0.24, HY0 + 0.24, HY1 - 0.24,
                DG1 + 0.01, CWALL_TOP)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                           plane_co=(0,0,CWALL_TOP-.06),plane_no=(0,0,1),dist=1e-6)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                           plane_co=(0,0,DG1+.07),plane_no=(0,0,1),dist=1e-6)
    for f in bm.faces:
        z=f.calc_center_median().z
        f.material_index=int(z>CWALL_TOP-.06 or z<DG1+.07)
    C.bm_obj(bm, "hall_gongyanbi", "hall", coll,
             cn="栱眼壁暗板（10.56→10.92，退 0.14 让石青线脚）", mat=("wood_dark","celadon"), uv=0.9)

    bm = mu.new_bm()
    # Mitred flashing closes the skirt to the infill. Its outer edge mates
    # with the vertical inner edge of the tiles. The inner lip sits on the wall.
    x0,y0,x1,y1 = _waist_edge()
    _ring_solid(bm,x0,x1,y0,y1,-HX+HW,HX-HW,HY0+HW,HY1-HW,
                WALL_TOP,WALL_TOP+.085)
    flashing=C.bm_obj(bm, "hall_weiji", "roof", ("主殿", "下檐"),
             cn="下檐围脊", mat="roof_dai", uv=0.4)


    # Through-holes cut to the actual battered shaft section at this height.
    bore=mu.new_bm()
    for y in CYS:
        for x in CXS:
            if y not in (HY0,HY1) and abs(x)!=HX: continue
            head,lean,_=_column_head(x,y)
            z0,z1=WALL_TOP-.10,WALL_TOP+.18
            f0=(z0-(HJ+.185))/(head-(HJ+.185))
            f1=(z1-(HJ+.185))/(head-(HJ+.185))
            r0=D.COL_R+(D.COL_R_TOP-D.COL_R)*f0+.003
            r1=D.COL_R+(D.COL_R_TOP-D.COL_R)*f1+.003
            _column(bore,x+lean.x*f0,y+lean.y*f0,z0,z1,r0,r1,
                    lean=lean*(f1-f0),seg=32)
    mu.recalc_normals(bore)
    cutter_mesh=mu.bm_to_mesh(bore,"waist_post_socket")
    bore.free()
    cutter=bpy.data.objects.new("waist_post_socket",cutter_mesh)
    flashing.users_collection[0].objects.link(cutter)
    mod=flashing.modifiers.new("柱位开孔","BOOLEAN")
    mod.operation='DIFFERENCE'
    mod.solver='EXACT'
    mod.object=cutter
    bpy.context.view_layer.objects.active=flashing
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
    bpy.data.meshes.remove(cutter_mesh)


# ============================================================ 5 墙身与门窗
def _walls(C):
    coll = ("主殿", "墙身")
    zt = WALL_TOP                         # 8.80 白墙顶
    sill = HJ + 0.55                      # 1.00 槛窗窗台

    win_z0, win_z1 = sill, HJ + 5.15      # 1.00 … 5.60
    door_z1 = HJ + D.DOOR_H               # 6.05
    hp_z0, hp_z1 = door_z1 + 0.20, zt - 0.50    # 6.25 … 8.30 门上横披
    #   6.25 必须正好接住门楣顶（ztop+0.20），差 0.10 会在门楣上方留一条白墙亮带
    hw = D.DOOR_W / 2                     # 3.25

    # ---------------- 南立面 ----------------
    holes = [(-hw+.55, hw-.55, HJ, door_z1 + .20)]
    holes.append((-hw + 0.55, hw - 0.55, hp_z0, hp_z1))
    for sx in (-1, 1):
        for (a, b) in (BAY_CI, BAY_SHAO):
            lo, hi = sorted((sx * (a + 0.55), sx * (b - 0.55)))
            holes.append((lo, hi, win_z0, win_z1))
    bm = mu.new_bm()
    _wall_panels(bm, -HX, HX, HJ, zt, HY0 - HW, HY0 + HW, holes, axis="y")
    C.bm_obj(bm, "hall_wall_s", "hall", coll, cn="南立面白墙",
             mat="wall_white", uv=1.0)

    # 槛窗 + 玻璃（次 / 梢间各 2 樘）
    bm = mu.new_bm()
    bmg = mu.new_bm()
    for sx in (-1, 1):
        for (a, b) in (BAY_CI, BAY_SHAO):
            lo, hi = sorted((sx * (a + 0.55), sx * (b - 0.55)))
            _lattice_x(bm, bmg, lo, hi, win_z0, win_z1, HY0, pitch=0.26, hstep=0.72)
    # 门上横披
    _lattice_x(bm, bmg, -hw + 0.55, hw - 0.55, hp_z0, hp_z1, HY0,
               pitch=0.28, hstep=0.70)
    C.bm_obj(bm, "hall_grille_s", "screen", coll,
             cn="南面槛窗木格心（次/梢间 4 樘 + 横披）", mat="wood_dark", uv=0.8)
    C.bm_obj(bmg, "hall_glass_s", "screen", coll, cn="影青玉石屏扇（南）",
             mat="glass", uv=0.6, flat=True)

    # ---------------- 东西山墙：各 3 樘 ----------------
    wl = ((HY0 + 2.70 - 1.20, HY0 + 2.70 + 1.20),
          (RIDGE_Y - 1.20, RIDGE_Y + 1.20),
          (HY1 - 2.70 - 1.20, HY1 - 2.70 + 1.20))
    bm = mu.new_bm()
    bmg = mu.new_bm()
    bmw = mu.new_bm()
    for sx in (-1, 1):
        xc = sx * HX
        _wall_panels(bmw, HY0 + 0.30, HY1 - 0.30, HJ, zt, xc - HW, xc + HW,
                     [(a, b, win_z0, win_z1) for a, b in wl], axis="x")
        for a, b in wl:
            _lattice_y(bm, bmg, a, b, win_z0, win_z1, xc, pitch=0.26, hstep=0.72)
    C.bm_obj(bmw, "hall_wall_ew", "hall", coll, cn="东西山墙白墙",
             mat="wall_white", uv=1.0)
    C.bm_obj(bm, "hall_grille_ew", "screen", coll, cn="山墙木格心（各 3 樘）",
             mat="wood_dark", uv=0.8)
    C.bm_obj(bmg, "hall_glass_ew", "screen", coll, cn="山墙格心玻璃",
             mat="glass", uv=0.6, flat=True)

    # ---------------- 北墙：中央 4.2m 内门通后阁 ----------------
    bm = mu.new_bm()
    _wall_panels(bm, -HX, HX, HJ, zt, HY1 - HW, HY1 + HW,
                 [(-2.10, 2.10, HJ, HJ + 4.20),(-2.,2.,HJ+4.30,zt-.60)], axis="y")
    C.bm_obj(bm, "hall_wall_n", "hall", coll, cn="后墙白墙（中央 4.2m 内门）",
             mat="wall_white", uv=1.0)

    bm = mu.new_bm()
    bmg = mu.new_bm()
    _lattice_x(bm, bmg, -2.00, 2.00, HJ + 4.30, zt - 0.60, HY1,
               pitch=0.30, hstep=0.92)
    C.bm_obj(bm, "hall_grille_n", "hall", coll, cn="后墙内门横披格心",
             mat="wood_dark", uv=0.8)
    C.bm_obj(bmg, "hall_glass_n", "screen", coll, cn="后墙横披玻璃",
             mat="glass", uv=0.6, flat=True)

    _door(C, coll, hw-.55-.18, door_z1)


def _door(C, coll, hw, ztop):
    """明间 6 扇格扇门：6.50 × 5.60，wood_dark 框 + glass 芯 + bronze 门钉铺首。

    所有 y 一律以 DY 为基准（门扇中面），门钉/铺首朝 −Y 凸出 —— 直接写 y=0
    会把整扇门丢到殿中央去（第一版就是这么错的）。
    """
    DY = HY0 - 0.03                       # 门扇中面

    bm = mu.new_bm()                      # 门框（抱框 + 门楣）
    _box(bm, -hw - 0.18, -hw, HY0 - 0.20, HY0 + 0.14, HJ+.34, ztop)
    _box(bm, hw, hw + 0.18, HY0 - 0.20, HY0 + 0.14, HJ+.34, ztop)
    _box(bm, -hw - 0.18, hw + 0.18, HY0 - 0.20, HY0 + 0.14, ztop, ztop + 0.20)

    bmg = mu.new_bm()                     # 玻璃芯
    bmp = mu.new_bm()                     # 门钉 + 铺首（bronze）
    n = 6
    w = 2*hw / n                      # 1.0833
    e0, e1 = 0.095, 0.105                 # 边梃宽 / 门厚的一半
    ya, yb = DY - e1, DY + e1             # 门扇前后两面
    for i in range(n):
        existing = [set(mesh.verts) for mesh in (bm, bmg, bmp)]
        x0 = -hw + i * w + 0.012
        x1 = x0 + w - 0.024
        # 边梃（左右）
        _box(bm, x0, x0 + e0, ya, yb, HJ, ztop)
        _box(bm, x1 - e0, x1, ya, yb, HJ, ztop)
        _box(bm, x0 + e0, x1 - e0, ya, yb, HJ, HJ + 0.15)          # 下槛
        _box(bm, x0 + e0, x1 - e0, ya, yb, HJ + 0.15, HJ + 0.90)   # 裙板（实心）
        _box(bm, x0 + e0, x1 - e0, ya, yb, HJ + 0.90, HJ + 1.00)   # 中抹头
        _box(bm, x0 + e0, x1 - e0, ya, yb, ztop - 0.16, ztop)      # 上抹头
        # 格心：竖棂 0.035 @ 0.16 + 横档 @ 0.46（棂条贴在门扇前脸）
        ix0, ix1 = x0 + e0, x1 - e0
        gz0, gz1 = HJ + 1.00, ztop - 0.16
        m = max(2, int(round((ix1 - ix0) / 0.16)))
        for k in range(1, m):
            gx = ix0 + (ix1 - ix0) * k / m
            _box(bm, gx - 0.0175, gx + 0.0175, ya + 0.02, ya + 0.105, gz0, gz1)
        h = max(2, int(round((gz1 - gz0) / 0.46)))
        for k in range(1, h):
            gz = gz0 + (gz1 - gz0) * k / h
            _box(bm, ix0, ix1, ya + 0.02, ya + 0.105, gz - 0.0175, gz + 0.0175)
        # 玻璃（贴在格心背面）
        _box(bmg, ix0+0.0035, ix1-0.0035, DY+0.0035, DY+0.0195, gz0+0.0035, gz1-0.0035)
        # 裙板 bronze 门钉 2 排 × 3 列（朝外凸 0.03）
        for r in (HJ + 0.26, HJ + 0.62):
            for k in range(3):
                px = x0 + e0 + (x1 - x0 - 2 * e0) * (k + 0.5) / 3
                _box(bmp, px - 0.045, px + 0.045, ya - 0.03, ya + 0.003,
                     r - 0.045, r + 0.045)
        # 中两扇的铺首（兽面衔环）
        if i in (2, 3):
            cx = x1 - e0 - 0.10 if i == 2 else x0 + e0 + 0.10
            _box(bmp,cx-.055,cx+.055,ya-.022,ya+.003,HJ+.365,HJ+.48)
            ring=[(cx+.047*math.sin(TAU*j/24),ya-.037,
                   HJ+.355+.058*math.cos(TAU*j/24)) for j in range(25)]
            mu.swept_tube(bmp,ring,.007,segments=8)
            _box(bmp,cx-.012,cx+.012,ya-.042,ya-.015,HJ+.398,HJ+.428)
        # Closed rest pose; the two banks pivot at their outside jambs in the viewer.
        for mesh, old in zip((bm, bmg, bmp), existing):
            for vert in mesh.verts:
                if vert not in old:
                    z = HJ+0.145+(vert.co.z-HJ)*(ztop-HJ-0.160)/(ztop-HJ)
                    vert.co.z = z

    C.bm_obj(bm, "hall_door", "hall", coll, cn="明间六扇格扇（轴线开间6.50米，抱框按柱础内净距设置）",
             mat="wood_dark", uv=0.8)
    C.bm_obj(bmg, "hall_door_glass", "screen", coll, cn="格心影青玻璃",
             mat="glass", uv=0.6, flat=True)
    C.bm_obj(bmp, "hall_door_bronze", "detail", ("主殿", "细部"),
             cn="门钉 / 铺首（鎏金）", mat="bronze", uv=0.5, flat=True)


# ============================================================ 6 下檐
def _waist_edge():
    return (-HX-.44, HY0-.44, HX+.44, HY1+.44)


def _lower_eave(C):
    """下檐（腰檐）：外缘 x±16.2 / y −15.2…9.2 于 6.40，内缘 ±13 / y −12…6 于 8.80。"""
    outer = (-D.LOWER_EAVE_TIP, D.LOWER_EAVE_TIP_Y0,
             D.LOWER_EAVE_TIP, D.LOWER_EAVE_TIP_Y1)
    inner = _waist_edge()
    bm = mu.new_bm()
    ep = rk.corrugated_skirt(bm, outer, LOW_Z, inner, WALL_TOP,
                             thick=D.ROOF_THICK, amp=D.TILE_AMP,
                             gauge=D.TILE_GAUGE, nv=16, mat=0)
    for ci in range(4):
        p = rk.hip_ridge_path(outer, LOW_Z, inner, WALL_TOP, ci)
        rk.ridge_along_path(bm, p, w=0.26, h=0.32, mat=0)
    C.bm_obj(bm, "hall_eave_lower", "roof", ("主殿", "下檐"), cn="下檐（腰檐）",
             mat="roof_dai", uv=0.2)
    return ep


# ============================================================ 7 上檐
def _upper_roof(C):
    """上檐歇山：ridge_bar 脊帽顶 = z_ridge + 0.84 → 传 15.66 得 16.50。"""
    outer = (-D.UPPER_EAVE_TIP_X, D.UPPER_EAVE_TIP_Y0,
             D.UPPER_EAVE_TIP_X, D.UPPER_EAVE_TIP_Y1)
    inner = (-GABLE_X, D.GABLE_Y0, GABLE_X, D.GABLE_Y1)
    bm = mu.new_bm()
    ep = rk.xieshan_roof(bm, outer=outer, z_eave=UP_Z, inner=inner,
                         z_break=D.SKIRT_BREAK_Z, gable_x=GABLE_X,
                         ridge_y=RIDGE_Y, z_ridge=Z_RIDGE_IN,
                         mat=0, mat_ridge=0, nv=16)
    C.bm_obj(bm, "hall_roof_upper", "roof", ("主殿", "上檐"), cn="上檐歇山顶",
             mat="roof_dai", uv=0.2)
    return ep


# ============================================================ 8 檐下细节
def _eave_detail(C, ep_low, ep_up):
    """檐下木作：圆檐椽 + 方飞椽 + 封檐板 + 朱砂/石青描边 + 瓦当滴水。

    v14 口径（用户 m03040「屋顶木架突起」）：
      檐口瓦壳下表面 ≈ 檐口线 p.z − ROOF_THICK(0.34)。
      因此椽/板一律排在 p.z − 0.34 以下，或只在瓦壳**外沿以外**出挑，
      绝不允许高于瓦底，避免椽头从瓦面里冒出来。
    """
    bm_r = mu.new_bm()                    # 圆檐椽与端帽共用边环
    bm_t = mu.new_bm()                    # 瓦当（roof_dai）
    bm_fly, bm_fascia = mu.new_bm(), mu.new_bm()
    up = Vector((0, 0, 1))
    for ep, roof_name, fascia in ((ep_low, "hall_eave_lower", True), (ep_up, "hall_roof_upper", False)):
        roof = next(ob.data for ob in C.objects if ob.name == roof_name)
        roof.calc_loop_triangles()
        surface = BVHTree.FromPolygons([v.co for v in roof.vertices],
                                       [tuple(f.vertices) for f in roof.loop_triangles],
                                       all_triangles=True)
        for path in ep.values():
            brackets = _path_samples(path, .45)
            rail=[]
            for p, tangent, normal in brackets:
                side = up.cross(normal).normalized()
                # Probe the smooth soffit over the whole timber footprint, including the hip.
                depths = []
                for j in range(12):
                    for dx in (-.05, 0, .05):
                        q = p - normal*(j*.03+.002) + side*dx
                        hit = surface.ray_cast(Vector((q.x,q.y,0)), up)[0]
                        if hit is not None:
                            depths.append(hit.z)
                soffit = min(depths) if depths else p.z - D.ROOF_THICK - D.TILE_AMP
                zc = soffit - .14
                rail.append((Vector((p.x,p.y,zc-.139))-normal*.10,normal))
                end = Vector((p.x, p.y, zc)) + normal*.064
                inner = Vector((p.x, p.y, zc)) - normal*.30
                rings = mu.swept_tube(bm_r, [inner, end, end+normal*.003], .045,
                                      segments=24, caps=True)
                for vertex in rings[-1]:
                    for face in vertex.link_faces:
                        face.material_index = 1
                q = Vector((p.x,p.y,zc+.047))
                mu.swept_profile_along(bm_fly, [q - normal*.06, q + normal*.14],
                                       [(-.025,0),(.025,0),(.025,.070),(-.025,.070)])
            if fascia:
                # Follow the measured eave underside. Keep the board on the exterior face.
                profile = [(-.035,-.10),(.035,-.10),(.035,.10),(-.035,.10),
                           (-.035,-.009),(-.035,-.031)]
                tangent0=(rail[1][0]-rail[0][0]).normalized()
                tangent1=(rail[-1][0]-rail[-2][0]).normalized()
                rail=[(rail[0][0]-.12*tangent0,rail[0][1])]+rail+[(rail[-1][0]+.12*tangent1,rail[-1][1])]
                # Keep the board vertical; a moving Frenet frame tips it away
                # from the rafter at the eave's corrugated corner stations.
                rings=[[bm_fascia.verts.new(c+n*dx+up*h) for dx,h in profile] for c,n in rail]
                for left,right in zip(rings,rings[1:]): mu.bridge_rings(bm_fascia,left,right,closed=True)
                mu.cap_ring(bm_fascia,rings[0],flip=True)
                mu.cap_ring(bm_fascia,rings[-1])
                for left, right in zip(rings, rings[1:]):
                    stripe = bm_fascia.faces.get((left[4],left[5],right[5],right[4]))
                    stripe.material_index = 1
            # ---- 檐口瓦当：每 0.42 一枚 ----
            for (p, t, nn) in _path_samples(path, D.TILE_GAUGE):
                # Each end tile has a planar exposed cap and a neck bedded in
                # the eave course. Probe in the horizontal outward direction.
                side = up.cross(nn).normalized()
                center = p - up*(.115 if fascia else .032)
                def skin(q):
                    hit = surface.ray_cast(q+nn*.42,-nn,.9)[0]
                    return (hit-q).dot(nn) if hit is not None else None
                outline = [center + .065*(side*math.cos(TAU*j/12)+up*math.sin(TAU*j/12))
                           for j in range(12)]
                measured = [skin(q) for q in outline]
                apex = skin(center)
                if apex is None: raise ValueError("Missing tile seat on "+roof_name)
                front = max(v for v in measured+[apex] if v is not None)+.008
                # A smaller shank can seat entirely on the curved half-round.
                shank=[center+(q-center)*.40 for q in outline]
                rings=[]
                for points,depths in ((shank,[(skin(q) if skin(q) is not None else apex)-.004 for q in shank]),
                                      (shank,[front-.003]*12),(outline,[front-.003]*12),(outline,[front]*12)):
                    rings.append([bm_t.verts.new(q+nn*h) for q,h in zip(points,depths)])
                for left,right in zip(rings,rings[1:]): mu.bridge_rings(bm_t,left,right,closed=True)
                mu.cap_ring(bm_t,rings[0],flip=True)
                mu.cap_ring(bm_t,rings[-1])

    C.bm_obj(bm_fly, "hall_flying_rafters", "detail", ("主殿","檐下"), cn="方飞椽", mat="wood_dark")
    C.bm_obj(bm_fascia, "hall_fascia", "detail", ("主殿","檐下"), cn="封檐板及朱砂描边", mat=("wood_dark","crimson"))
    C.bm_obj(bm_r, "hall_rafters", "detail", ("主殿", "檐下"),
             cn="二十四边圆檐椽及三毫米朱砂端帽", mat=("wood_dark","crimson"), uv=0.6)
    C.bm_obj(bm_t, "hall_tiles", "roof", ("主殿", "檐下"),
             cn="檐口瓦当滴水", mat="roof_dai", uv=0.5, flat=True)


# ============================================================ 9 山花四件套
def _gables(C):
    """山花：底 z=13.60 @ y −6.4…0.4，顶点 (−3.0, 15.60)，净高 2.0。"""
    coll = ("主殿", "山花")
    floor = D.SKIRT_BREAK_Z+.15
    dx = RIDGE_Y-D.GABLE_Y0
    def border(v):
        return (D.SKIRT_BREAK_Z + (Z_RIDGE_IN-D.SKIRT_BREAK_Z)*v**1.35
                -D.ROOF_THICK-D.TILE_AMP-.025)
    start = ((floor-border(0))/(Z_RIDGE_IN-D.SKIRT_BREAK_Z))**(1/1.35)
    samples = sorted({start,1.} | {j/16 for j in range(17) if j/16>start})
    top = [(RIDGE_Y-dx*(1-v),border(v)) for v in samples]
    top += [(2*RIDGE_Y-y,z) for y,z in reversed(top[:-1])]
    cy,cz = RIDGE_Y, floor+(border(1)-floor)*.35
    inner = [(cy+(y-cy)*.82,cz+(z-cz)*.82) for y,z in top]
    for sx,tag in ((1,"e"),(-1,"w")):
        rear = sx*(GABLE_X-.05)
        face = sx*(GABLE_X+.06)
        front = sx*(GABLE_X+.105)
        panel = mu.new_bm()
        _prism_yz_x(panel,top,rear,face)
        C.bm_obj(panel,"hall_gable_"+tag,"hall",coll,cn="随屋底举折的山花板",mat="wood_lite")
        trim = mu.new_bm()
        for i in range(len(top)):
            j=(i+1)%len(top)
            _prism_yz_x(trim,[top[i],top[j],inner[j],inner[i]],face,front)
        C.bm_obj(trim,"hall_gable_trim_"+tag,"hall",coll,cn="山花压边",mat="wall_white")
        ornament=mu.new_bm()
        apex=inner[len(top)//2][1]-.045
        fish=[(cy,apex),(cy+.13,apex-.22),(cy+.145,apex-.34),
              (cy+.105,apex-.49),(cy,apex-.62),(cy-.105,apex-.49),
              (cy-.145,apex-.34),(cy-.13,apex-.22)]
        _prism_yz_x(ornament,fish,face,sx*(GABLE_X+.135))
        for sign in (-1,1):
            _prism_yz_x(ornament,[(cy+sign*y,apex-z) for y,z in
                                    ((.25,.33),(.60,.59),(.61,.68),(.24,.41))],
                        face,sx*(GABLE_X+.115))
        C.bm_obj(ornament,"hall_gable_orn_"+tag,"detail",coll,cn="悬鱼惹草",mat="bronze")


# ============================================================ 10 鸱吻（宋式立体）+ 垂脊走兽
def _orn_ellipsoid(bm, center, radii, seg=24, rings=12):
    """Closed curved sculptural component with real poles, no degenerate pole rings."""
    c=Vector(center); rx,ry,rz=radii
    bottom=bm.verts.new(c+Vector((0,0,-rz)))
    top=bm.verts.new(c+Vector((0,0,rz)))
    loops=[]
    for j in range(1,rings):
        lat=-math.pi/2+math.pi*j/rings
        loops.append([bm.verts.new(c+Vector((rx*math.cos(lat)*math.cos(2*math.pi*k/seg),
                         ry*math.cos(lat)*math.sin(2*math.pi*k/seg),rz*math.sin(lat)))) for k in range(seg)])
    for k in range(seg):
        kn=(k+1)%seg
        bm.faces.new((bottom,loops[0][kn],loops[0][k]))
        bm.faces.new((top,loops[-1][k],loops[-1][kn]))
    for a,b in zip(loops,loops[1:]): mu.bridge_rings(bm,a,b,closed=True)


def _chiwen(C):
    """Original procedural ridge ornament: curved body, open jaws, spiral fin and relief scales.

    Components are sculptural assemblies, not a claim of Boolean-unified topology
    or an archaeological replica. The open mouth surrounds the end of the ridge.
    """
    coll=("主殿","鸱吻")
    bm=mu.new_bm(); relief=mu.new_bm()
    relief_paths=[]
    def body(z):
        t=max(0.,min(1.,(z-16.62)/1.20))
        return (7.63+.12*math.sin(math.pi*t),
                .23*(1-.92*t**1.5)+.035*math.sin(math.pi*t),
                .285*(1-.90*t**1.6))
    for side in (-1,1):
        def p(x,y,z): return (side*x,RIDGE_Y+y,z)
        def ell(x,y,z,rx,ry,rz): _orn_ellipsoid(bm,p(x,y,z),(rx,ry,rz))
        # 33 longitudinal stations, 32-sided rings, rather than the former six octagons.
        loops=[]
        for j in range(33):
            z=16.62+1.20*j/32; x,rx,ry=body(z)
            loops.append([bm.verts.new(p(x+rx*math.cos(2*math.pi*k/32),
                           ry*math.sin(2*math.pi*k/32),z)) for k in range(32)])
        # Continue the narrowing ellipse into a recurved point with a shared terminal pole.
        x, rx, ry = body(17.82)
        for j in range(1, 8):
            t = j / 8
            loops.append([bm.verts.new(p(x - .065*t*t + rx*(1-t)*math.cos(TAU*k/32),
                                          ry*(1-t)*math.sin(TAU*k/32), 17.82 + .105*t))
                          for k in range(32)])
        for a,b in zip(loops,loops[1:]):mu.bridge_rings(bm,a,b,closed=True)
        mu.cap_ring(bm,loops[0],flip=True)
        pole = bm.verts.new(p(x-.065, 0, 17.925))
        for k, v in enumerate(loops[-1]):
            bm.faces.new((v, loops[-1][(k+1)%32], pole))
        # Separate upper/lower jaw profiles leave a real void, not a black mouth decal.
        ell(7.34,0,16.94,.32,.235,.095)
        # Flat bearing sole on the ridge cap. Do not bury the curved lip.
        jaw=mu.new_bm()
        _orn_ellipsoid(jaw,p(7.39,0,16.52),(.31,.215,.065))
        cut=bmesh.ops.bisect_plane(jaw,geom=list(jaw.verts)+list(jaw.edges)+list(jaw.faces),
                                   dist=1e-7,plane_co=(0,0,D.RIDGE_Z),plane_no=(0,0,1),clear_inner=True)
        edges=[e for e in cut["geom_cut"] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
        bmesh.ops.holes_fill(jaw,edges=edges)
        jm=mu.bm_to_mesh(jaw,"chiwen_lower_jaw")
        bm.from_mesh(jm)
        jaw.free()
        bpy.data.meshes.remove(jm)
        for sy in (-1,1):
            ell(7.55,sy*.105,16.625,.10,.060,.112)
        for sy in (-1,1):
            ell(7.55,sy*.235,16.91,.215,.135,.185)
            ell(7.40,sy*.352,17.005,.066,.026,.048)
            # Brow, whisker and two inward curved fangs per cheek.
            brow=[p(7.32+.18*i/20,sy*(.35+.015*math.sin(math.pi*i/20)),
                    17.045+.048*math.sin(math.pi*i/20)) for i in range(21)]
            relief_paths.append((brow,.014,.007,10))
            whisker=[p(7.32-.14*i/24,sy*(.24+.05*math.sin(math.pi*i/24)),
                        16.85+.13*math.sin(math.pi*i/24)) for i in range(25)]
            relief_paths.append((whisker,.012,.003,10))
            for x in (7.15,7.36):
                path=[p(x+.04*(i/16)**2,sy*.17,16.88-.15*i/16) for i in range(17)]
                mu.swept_tube(bm,path,.026,segments=12,radius_end=.003)
        # Thick volumetric fin follows an inward spiral with 65 sampled sections.
        path=[]
        for j in range(65):
            t=j/64; a=math.radians(-70+365*t); r=.40*(1-t)+.055*t
            path.append(Vector((7.60+r*math.cos(a),0,17.65+r*math.sin(a))))
        fins=[]
        for j,q in enumerate(path):
            tangent=(path[min(64,j+1)]-path[max(0,j-1)]).normalized()
            normal=Vector((-tangent.z,0,tangent.x)); t=j/64
            width=.11*(1-t)+.025*t; thick=.065*(1-t)+.018*t
            fins.append([bm.verts.new(p(*(q+normal*(width*math.cos(2*math.pi*k/16))
                              +Vector((0,(thick+(.007*(1-t)+.003*t if k in (4,12) else 0))*math.sin(2*math.pi*k/16),0))))) for k in range(16)])
        for a,b in zip(fins,fins[1:]):mu.bridge_rings(bm,a,b,closed=True)
        mu.cap_ring(bm,fins[0],flip=True);mu.cap_ring(bm,fins[-1])
        # Bilateral fin ribs and six staggered rows of scales, conformed to the actual body.
        for sy in (-1,1):
            # The raised crest on each fin is part of its elliptical sections.
            for row in range(8):
                zz=17.02+row*.104
                for col in range(4):
                    theta=sy*(.55+col*.60+(row%2)*.12)
                    arc=[]
                    for j in range(17):
                        a=-math.pi/2+math.pi*j/16
                        z=zz+.058*math.cos(a); x,rx,ry=body(z)
                        phi=theta+.22*math.sin(a)
                        arc.append(p(x+(rx+.0008)*math.cos(phi),(ry+.0008)*math.sin(phi),z))
                    radius=.006 if row<6 else .004
                    relief_paths.append((arc,radius,radius,8))
    mu.recalc_normals(bm)
    skin=BVHTree.FromBMesh(bm)
    for points,start_r,end_r,n in relief_paths:
        bed=[]
        for i,p0 in enumerate(points):
            q,normal,_,_=skin.find_nearest(Vector(p0))
            r=start_r+(end_r-start_r)*i/(len(points)-1)
            q=q+normal*(r*.25)
            if not bed or (q-bed[-1]).length>.0005:
                bed.append(q)
        if len(bed)<2: raise ValueError("Collapsed chiwen relief")
        mu.swept_tube(relief,bed,start_r,segments=n,radius_end=end_r)
    for mesh,name,cn in ((bm,"hall_chiwen","双面鼓腮吞脊鸱吻·曲面内卷鳍"),
                         (relief,"hall_chiwen_trim","鸱吻双面鳞甲眉脊须纹")):
        mu.recalc_normals(mesh)
        C.bm_obj(mesh,name,"roof" if mesh is bm else "detail",coll,cn=cn,mat="bronze",uv=.5)


def _proto_beast(C, key="phoenix"):
    """Four distinguishable curved silhouettes; original decorative interpretations."""
    def fn(bm):
        def ell(c,r): _orn_ellipsoid(bm,c,r,seg=16,rings=10)
        def tube(points,r,end=None):
            mu.swept_tube(bm,points,r,segments=10,radius_end=r if end is None else end)
        def feather(points,width=.022):
            profile=[(width*math.cos(2*math.pi*j/12),.005*math.sin(2*math.pi*j/12)) for j in range(12)]
            mu.swept_profile_along(bm,points,profile,scale_fn=lambda t:(.2+.8*math.sin(math.pi*t),1.0))
        # A softly rounded ceramic plinth; no cubic body parts.
        ell((0,0,.014),(.14,.065,.014))
        if key in ("phoenix","rider"):
            ell((0,0,.10),(.085,.039,.052))
            neck=[(.04+.045*math.sin(math.pi*t/2),0,.12+.105*t) for t in [i/24 for i in range(25)]]
            tube(neck,.021,.014);ell((.09,0,.225),(.031,.025,.028))
            tube([(.11,0,.229),(.139,0,.219),(.148,0,.207)],.012,.002)
            for sy in (-1,1):
                for j in range(5):
                    points=[(.025-j*.019-.025*t,sy*(.032+.105*t),.135+.045*math.sin(math.pi*t)) for t in [i/18 for i in range(19)]]
                    feather(points,.015)
                tube([(.035,sy*.024,.075),(.025,sy*.033,.035),(.055,sy*.034,.025)],.009,.006)
            for j in range(3):
                points=[(-.06-.19*t,(j-1)*.035*t,.10+.09*t+.03*math.sin(2*math.pi*t)) for t in [i/28 for i in range(29)]]
                feather(points,.018)
            for j in range(3):
                tube([(.075-j*.007,0,.247),(.065-j*.012,0,.272)],.004,.001)
            if key=="rider":
                ell((-.012,0,.208),(.034,.030,.052))
                ell((-.012,0,.285),(.025,.024,.029))
                ell((-.015,0,.309),(.030,.027,.010))
                for sy in (-1,1):
                    tube([(-.02,sy*.024,.183),(.012,sy*.047,.14),(.047,sy*.041,.125)],.013,.009)
                    tube([(.005,sy*.026,.232),(.035,sy*.039,.209),(.069,sy*.021,.211)],.009,.006)
        elif key=="horse":
            ell((-.015,0,.12),(.10,.041,.055))
            for sy in (-1,1):
                for x in (-.075,.055):
                    tube([(x,sy*.03,.12),(x+.012,sy*.036,.066),(x-.005,sy*.038,.027)],.011,.008)
                    ell((x+.002,sy*.039,.025),(.018,.013,.008))
            tube([(.055,0,.14),(.077,0,.19),(.095,0,.225)],.032,.021)
            ell((.113,0,.225),(.042,.025,.026))
            ell((.143,0,.21),(.023,.021,.017))
            for sy in (-1,1):tube([(.09,sy*.016,.243),(.084,sy*.023,.282)],.009,.002)
            for j in range(8):
                z=.15+j*.01
                tube([(.047,0,z),(.029,0,z+.009)],.005,.002)
            tail=[(-.10-.10*t, .01*math.sin(math.pi*t),.14+.06*math.sin(math.pi*t)) for t in [i/24 for i in range(25)]]
            tube(tail,.013,.003)
        elif key=="dragon":
            pts=[(-.12+.21*t,.018*math.sin(2*math.pi*t),.10+.035*math.sin(math.pi*t)) for t in [i/32 for i in range(33)]]
            tube(pts,.031,.037)
            ell((.105,0,.166),(.045,.033,.038))
            ell((.14,0,.18),(.037,.026,.015));ell((.14,0,.15),(.03,.023,.009))
            for sy in (-1,1):
                horn=[(.085-.035*t,sy*(.023+.018*t),.19+.07*math.sin(math.pi*t/2)) for t in [i/20 for i in range(21)]]
                tube(horn,.007,.0015)
                for x in (-.075,.045):
                    tube([(x,sy*.022,.10),(x-.015,sy*.054,.068),(x+.02,sy*.056,.03)],.009,.005)
                whisker=[(.145+.03*t,sy*(.023+.04*t),.17+.025*math.sin(math.pi*t)) for t in [i/18 for i in range(19)]]
                tube(whisker,.004,.001)
            tail=[(-.12-.11*t,.025*math.sin(math.pi*t),.10+.065*t) for t in [i/24 for i in range(25)]]
            tube(tail,.021,.002)
            for j in range(8):
                x=-.10+j*.024
                tube([(x,0,.136),(x-.012,0,.165)],.006,.001)
        else:
            raise ValueError("Unknown ridge beast: "+key)
        mu.recalc_normals(bm)
    return C.proto("v15_beast_"+key,fn,mat="roof_dai",smooth=35.0,uv=.4)


def _ridge_beasts(C):
    """四道垂脊/戗脊端部：垂兽座 + 3 只蹲伏走兽（上檐与下檐各 4 条脊）。"""
    up_outer = (-D.UPPER_EAVE_TIP_X, D.UPPER_EAVE_TIP_Y0,
                D.UPPER_EAVE_TIP_X, D.UPPER_EAVE_TIP_Y1)
    up_inner = (-GABLE_X, D.GABLE_Y0, GABLE_X, D.GABLE_Y1)
    lo_outer = (-D.LOWER_EAVE_TIP, D.LOWER_EAVE_TIP_Y0,
                D.LOWER_EAVE_TIP, D.LOWER_EAVE_TIP_Y1)
    lo_inner = _waist_edge()
    beasts = {k: _proto_beast(C,k) for k in ("rider","dragon","phoenix","horse")}
    coll = ("主殿", "垂脊")
    seat = mu.new_bm()
    for outer, za, inner, zb, height in ((up_outer, UP_Z, up_inner, D.SKIRT_BREAK_Z, .42),
                                         (lo_outer, LOW_Z, lo_inner, WALL_TOP, .32)):
        for ci in range(4):
            p = rk.hip_ridge_path(outer, za, inner, zb, ci)
            pts = []
            for j, q in enumerate(p):
                tangent = (p[min(j+1, len(p)-1)] - p[max(j-1, 0)]).normalized()
                across = Vector((0, 0, 1)).cross(tangent).normalized()
                pts.append(q + height * tangent.cross(across).normalized())
            q0 = pts[0].lerp(pts[1], .30)
            along = (pts[1] - pts[0]).normalized()
            mu.swept_profile_along(seat, [q0 - along*.08, q0 + along*.08],
                                   [(-.065,.0002),(.065,.0002),(.055,.022),(-.055,.022)])
            # 走兽：自端部向内 0.30 / 0.56 / 0.82（沿路径按长度取点）
            acc = [0.0]
            for a, b in zip(pts, pts[1:]):
                acc.append(acc[-1] + (b - a).length)
            total = acc[-1]
            for kind, frac in zip(beasts, (.18,.36,.54,.72) if height==.32 else (.10,.22,.34,.46)):
                d = total * frac
                for k in range(len(pts) - 1):
                    if acc[k] <= d <= acc[k + 1]:
                        span = acc[k + 1] - acc[k]
                        # Seat each 280 mm plinth wholly on one planar cap facet.
                        margin = min(.15, span/2)
                        t = min(span-margin, max(margin, d-acc[k])) / span
                        pos = pts[k].lerp(pts[k + 1], t)
                        tan = (pts[k + 1] - pts[k]).normalized()
                        front = -tan
                        lateral = Vector((-front.y, front.x, 0)).normalized()
                        normal = front.cross(lateral).normalized()
                        basis = Matrix((front, lateral, normal)).transposed().to_4x4()
                        # Follow the local ridge slope; a horizontal base would float or cut in.
                        C.place_world(beasts[kind],
                                      Matrix.Translation(pos + normal * .0002) @ basis,
                                      name="hall_beast_"+kind, cat="detail", coll_path=coll,
                                      cn="垂脊蹲兽")
                        break

    C.bm_obj(seat, "hall_beast_seat", "roof", coll,
             cn="垂兽座（四角端部）", mat="roof_dai", uv=0.4, flat=True)


# ============================================================ 11 藻井
def _caisson(C):
    """8×8 藻井：天花板 z=9.60，十一层逐层内收至 1.8×1.8 天光口（顶 12.00）。

    每层 = 井壁（wood_dark，四周各一块竖板）+ 踏面（wood_lite，水平一圈）
    + 踏面外缘的 lightstrip 发光珠（每层 4 颗）。全部构件 ≤ 12.00。
    """
    coll = ("主殿", "藻井")
    cx, cy = 0.0, RIDGE_Y

    # ---- 天花板：井口 8×8 之外的四块平顶 ----
    bm = mu.new_bm()
    z0, z1 = CAIS_BOT - 0.05, CAIS_BOT
    # Allow 20 mm beyond the inward tangent, including lean and taper at soffit level.
    setback = D.COL_R_TOP + 0.008 * (COL_TOP + 0.04 - HJ) + 0.021
    _ring_solid(bm, -HX + setback, HX - setback, HY0 + setback, HY1 - setback,
                cx - CAIS, cx + CAIS, cy - CAIS, cy + CAIS, z0, z1)
    C.bm_obj(bm, "hall_ceiling", "interior", coll, cn="天花板（井口四边斜接，外缘避让柱顶）",
             mat="wood_dark", uv=1.0)

    # ---- 十一层藻井 ----
    bm = mu.new_bm()                      # 井壁 wood_dark
    bml = mu.new_bm()                     # 踏面 wood_lite
    bms = mu.new_bm()                     # 发光珠 lightstrip
    dz = (CAIS_TOP - CAIS_BOT) / CAIS_N
    dsz = (CAIS - SKY) / CAIS_N           # 每层单边内收量
    th = 0.07
    for i in range(CAIS_N):
        zz = CAIS_BOT + i * dz
        s = CAIS - i * dsz
        sn = s - dsz
        # 井壁四周
        _box(bm, cx - s, cx - s + th, cy - s, cy + s, zz, zz + dz - 0.045)
        _box(bm, cx + s - th, cx + s, cy - s, cy + s, zz, zz + dz - 0.045)
        _box(bm, cx - s + th, cx + s - th, cy - s, cy - s + th, zz, zz + dz - 0.045)
        _box(bm, cx - s + th, cx + s - th, cy + s - th, cy + s, zz, zz + dz - 0.045)
        # 踏面一圈（内收）
        zt0 = zz + dz - 0.045
        _box(bml, cx - s, cx + s, cy - s, cy - sn, zt0, zt0 + 0.045)
        _box(bml, cx - s, cx + s, cy + sn, cy + s, zt0, zt0 + 0.045)
        _box(bml, cx - s, cx - sn, cy - sn, cy + sn, zt0, zt0 + 0.045)
        _box(bml, cx + sn, cx + s, cy - sn, cy + sn, zt0, zt0 + 0.045)
        # 发光珠：去掉（原先每层 4 颗在低角度仰视下会读成一圈白色虚线，
        # 与「不做自发光怪雾」的审美口径冲突；照明改由天光口与室内面光承担）

    # ---- 天光口：1.8×1.8 lightstrip 顶板 + 一圈 bronze 压边 ----
    _box(bms, cx - SKY, cx + SKY, cy - SKY, cy + SKY, CAIS_TOP - .045, CAIS_TOP-.025)
    C.bm_obj(bm, "hall_caisson_wall", "interior", coll,
             cn="藻井井壁（11 层，wood_dark）", mat="wood_dark", uv=0.8)
    C.bm_obj(bml, "hall_caisson_step", "interior", coll,
             cn="藻井踏面（11 层，wood_lite）", mat="wood_lite", uv=0.6)
    C.bm_obj(bms, "hall_caisson_light", "interior", coll,
             cn="天光口透光板，铜压边承托", mat="lightstrip", uv=0.5, flat=True)

    bm = mu.new_bm()
    for (x0, x1, y0, y1) in ((cx - SKY - 0.07, cx + SKY + 0.07, cy - SKY - 0.07, cy - SKY+.006),
                             (cx - SKY - 0.07, cx + SKY + 0.07, cy + SKY-.006, cy + SKY + 0.07),
                             (cx - SKY - 0.07, cx - SKY+.006, cy - SKY+.006, cy + SKY-.006),
                             (cx + SKY-.006, cx + SKY + 0.07, cy - SKY+.006, cy + SKY-.006)):
        _box(bm, x0, x1, y0, y1, CAIS_TOP - .10, CAIS_TOP - .045)
    C.bm_obj(bm, "hall_caisson_rim", "interior", coll, cn="天光口 bronze 压边",
             mat="bronze", uv=0.5, flat=True)


# ============================================================ 自检
def _report(objs):
    tris = sum(mu.tri_count(o) for o in objs)
    zmax, zmin = -1e9, 1e9
    bb = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9]
    by_mat = {}
    for o in objs:
        t = mu.tri_count(o)
        mats = o.data.materials
        key = mats[0].name if (mats and mats[0]) else "?"
        by_mat[key] = by_mat.get(key, 0) + t
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            zmax = max(zmax, w.z)
            zmin = min(zmin, w.z)
            bb[0] = min(bb[0], w.x)
            bb[3] = max(bb[3], w.x)
            bb[1] = min(bb[1], w.y)
            bb[4] = max(bb[4], w.y)
            bb[2] = min(bb[2], w.z)
            bb[5] = max(bb[5], w.z)
    print(f"[hall] 对象 {len(objs)} / 三角面 {tris} / max(z) {zmax:.3f} / min(z) {zmin:.3f}")
    print("[hall] tri 分类 " + " ".join(f"{k}:{v}" for k, v in
                                        sorted(by_mat.items(), key=lambda kv: -kv[1])))
    print(f"[hall] 包围盒 x[{bb[0]:.2f},{bb[3]:.2f}] "
          f"y[{bb[1]:.2f},{bb[4]:.2f}] z[{bb[2]:.2f},{bb[5]:.2f}]")
    return tris, zmax


# ============================================================ 编排
def build(C):
    n0 = len(C.objects)
    _taiji(C)                              # 台明 + 台阶 + 门槛
    _columns(C)                            # 柱础 → 柱
    _beams(C)                              # 阑额 → 普拍枋
    _dougong(C)                            # 斗拱带 + 栱眼壁 + 围脊
    _walls(C)                              # 墙身 + 门窗
    ep_low = _lower_eave(C)                # 下檐
    ep_up = _upper_roof(C)                 # 上檐
    _eave_detail(C, ep_low, ep_up)         # 封檐板 / 椽头 / 瓦当
    _gables(C)                             # 山花
    _chiwen(C)                             # 鸱吻（宋式立体）
    _ridge_beasts(C)                       # 垂兽座 + 走兽（四垂脊）
    _caisson(C)                            # 藻井
    _report(C.objects[n0:])
