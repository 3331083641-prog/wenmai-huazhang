# -*- coding: utf-8 -*-
"""v15 三间四柱七楼牌楼。楼跨、柱位与正脊标高由 dim13 定义。

七座悬山各有水平正脊、两面阶形瓦坡与四条垂脊。每条垂脊安放三只走兽，
双颚鸱吻立在正脊两端。双层椽与五铺作分列各楼前后檐，明间下方保持通透。
"""

from __future__ import annotations

import math

from mathutils import Matrix, Vector

from .. import mesh_util as mu
from ..dim13 import DIM13 as D

TAU = math.tau

# ============================================================ 尺寸别名
GY = D.GATE_Y                     # -46.0 牌楼中线
HX = D.GATE_HX                    # 12.0
CX_MID = D.GATE_COL_X[1]          # 4.40  中柱
CX_OUT = D.GATE_COL_X[2]          # 12.00 外柱
CR = D.GATE_COL_R                 # 0.46 柱底半径
CRT = 0.40                        # 柱顶半径（收分）
Z0 = D.GROUND_Z                   # 台基完成面
Z_G = D.GATE_H                    # 10.60 主楼正脊顶
Z_S = D.GATE_SIDE_H               # 7.90 次楼脊
Z_I = D.GATE_INNER_H              # 6.90 夹楼脊
Z_O = D.GATE_OUTER_H              # 6.40 边楼脊
DEP = D.GATE_DEPTH                # 1.50 楼身进深
HDR = D.GATE_HDR_H                # 1.15 明间金匾带

# 柱
Z_BASE = Z0 + 0.46                # 柱础顶 = 柱身起
Z_PL_TOP = 6.90                   # 中柱顶（= GATE_INNER_H 一带）
Z_PL_OUT = 5.53                   # 外柱顶（必须压在边楼檐口 5.65 之下，否则柱头穿瓦）
Z_CAP = 0.26                      # 柱础方座高

# 明间 stack
Z_PAI = 6.55                      # 5 道短枋底
Z_PAI_N = 5
Z_BIAN0, Z_BIAN1 = 7.34, 8.14     # 金匾 0.80
Z_DG0, Z_DG1 = 8.25, 9.41         # 明间斗拱带
Z_EAVE_M = 9.55                   # 主楼檐口
# 次间 stack
Z_EF0, Z_EF1 = 5.30, 5.51         # 下额枋（顶 = 边楼屋面底皮 5.65-0.14）
Z_HB0, Z_HB1 = 5.51, 5.96         # 花板一（顶 = 夹楼屋面底皮 6.10-0.14）
Z_HB2, Z_HB3 = 5.96, 6.78         # 花板二（顶 = 次楼额枋底）
Z_EF2, Z_EF3 = 6.78, 6.96         # 次楼额枋（顶 = 次楼屋面底皮 7.10-0.14）

# 楼表：(名字, xa, xb, 脊顶, 檐口, 半深, 中文)
# 半深受基盘南缘约束：GY - hd - 0.06 >= PLATE_Y_S(-59.0) → hd <= 0.90
# x 跨**必须首尾相接、互不越界**：任一 x 的最高命中点只能是本楼的正脊，
# 否则「沿 x 5 点竖射线极差 ≤ 0.5mm」会被邻楼更高的脊打穿（见 §偏离 2）。
LOUS = (
    ("lou_main", -CX_MID, CX_MID, Z_G, Z_EAVE_M, 0.90, "主楼"),
    ("lou_side_e", CX_MID, 7.80, Z_S, 7.10, 0.84, "东次楼"),
    ("lou_side_w", -7.80, -CX_MID, Z_S, 7.10, 0.84, "西次楼"),
    ("lou_in_e", 7.80, 10.45, Z_I, 6.10, 0.78, "东夹楼"),
    ("lou_in_w", -10.45, -7.80, Z_I, 6.10, 0.78, "西夹楼"),
    ("lou_out_e", 10.45, 12.40, Z_O, 5.65, 0.74, "东边楼"),
    ("lou_out_w", -12.40, -10.45, Z_O, 5.65, 0.74, "西边楼"),
)

# 景墙
SC_H = D.SCREEN_H                 # 3.60
SC_T = D.SCREEN_T                 # 0.45
WIN_W = D.WINDOW_W                # 1.70
WIN_H = D.WINDOW_H                # 1.35
SC_X1 = 19.00                     # 景墙外端（= site 院墙起点，见汇报）
WIN_C = (13.50, 15.50, 17.50)     # 三樘漏窗中心
WIN_Z0 = Z0 + 1.50                # 漏窗台 = 广场上 1.50
WIN_Z1 = WIN_Z0 + WIN_H


# ============================================================ 通用
def _q(bm, pts):
    try:
        bm.faces.new(pts)
    except ValueError:
        pass


def _quad(bm, p0, p1, p2, p3):
    _q(bm, [bm.verts.new(Vector(p)) for p in (p0, p1, p2, p3)])


def _tri(bm, p0, p1, p2):
    _q(bm, [bm.verts.new(Vector(p)) for p in (p0, p1, p2)])


def _bx(bm, x0, x1, y0, y1, z0, z1):
    """盒（mu.box_mm 内部取 abs，端点顺序无所谓）。"""
    mu.box_mm(bm, x0, x1, y0, y1, z0, z1)


def _solid_yz(bm, x0, x1, pts):
    """(y,z) 平面多边形沿 x 挤出 [x0,x1] 的闭合棱柱（正脊 / 博风板 / 墙帽）。"""
    a = [bm.verts.new(Vector((x0, p[0], p[1]))) for p in pts]
    b = [bm.verts.new(Vector((x1, p[0], p[1]))) for p in pts]
    _q(bm, a)
    _q(bm, list(reversed(b)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        _q(bm, [a[i], a[j], b[j], b[i]])


def _solid_xz(bm, y0, y1, pts):
    """(x,z) 平面多边形沿 y 挤出 [y0,y1] 的闭合棱柱（脊饰卷云用）。"""
    a = [bm.verts.new(Vector((p[0], y0, p[1]))) for p in pts]
    b = [bm.verts.new(Vector((p[0], y1, p[1]))) for p in pts]
    _q(bm, a)
    _q(bm, list(reversed(b)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        _q(bm, [a[i], a[j], b[j], b[i]])


def _disc(bm, c, n, r, seg=8, phase=0.0):
    """法线 n 的零厚度圆片（瓦当）。"""
    nn = Vector(n).normalized()
    u = Vector((0.0, 0.0, 1.0)).cross(nn)
    if u.length < 1e-6:
        u = Vector((1.0, 0.0, 0.0)).cross(nn)
    u.normalize()
    w = nn.cross(u)
    ctr = bm.verts.new(Vector(c) + nn * 0.006)
    ring = []
    for i in range(seg):
        a = phase + TAU * i / seg
        ring.append(bm.verts.new(Vector(c) + u * (r * math.cos(a))
                                 + w * (r * math.sin(a))))
    for i in range(seg):
        _q(bm, [ctr, ring[i], ring[(i + 1) % seg]])


def _emit(C, bm, M, name, cat, coll, cn, mat, flat=False, smooth=35.0):
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        v.co = M @ v.co if M is not None else v.co
    mu.recalc_normals(bm)
    C.bm_obj(bm, name, cat, coll, cn=cn, mat=mat, flat=flat, smooth=smooth)


# ============================================================ 柱与柱础
def _col_base(bm_sd, bm_st, bm_br, x):
    """石牌坊的「身份件」：stone_dark 柱础 + stone_lite 夹杆石一对 + 鼓墩。

    - 柱础：0.90 见方 / 0.20 高，柱脚从广场 z=-1.80 起（不悬空）
    - 夹杆石：柱前后各一，1.24 高、顶端放大，bronze 箍一道
    """
    _bx(bm_sd, x - 0.45, x + 0.45, GY - 0.45, GY + 0.45, Z0, Z0 + 0.20)
    _bx(bm_sd, x - 0.40, x + 0.40, GY - 0.40, GY + 0.40, Z0 + 0.20, Z0 + 0.26)
    for sy in (-1.0, 1.0):
        yc = GY + sy * .590
        _bx(bm_st, x - 0.26, x + 0.26, yc - .085, yc + .085, Z0, Z0 + 1.22)
        _bx(bm_st, x - 0.31, x + 0.31, yc - .095, yc + .095, Z0 + 1.22,
            Z0 + 1.33)
        ya=GY+sy*.675
        rings=mu.cylinder(bm_br,(x,min(ya,ya+sy*.018),Z0+.84),.245,.018,segments=16,axis="Y",cap=False)
        mu.cap_ring(bm_br,rings[16:] if sy>0 else rings[:16])
    # 鼓墩（八角覆盆）
    mu.cylinder(bm_st, (x, GY, Z0 + 0.26), 0.50, 0.20, segments=8,
                radius_top=CR + 0.02)


def _column(bm, x, z_top, sockets):
    """八角收分石柱（R0.46 → 0.40），底部落在柱础顶。"""
    def radius(z):
        return CR+(CRT-CR)*(z-Z_BASE)/(z_top-Z_BASE)
    prof=[(CR,Z_BASE)]
    for z in (Z_BASE+.10,3.45):
        # 凸出 6mm 的八角石托棱支住铜带底面；止口背坡回到柱身，
        # 铸带内壁与石柱留 0.5mm 装配净空。
        prof.extend(((radius(z-.012),z-.012),(radius(z)+.006,z),
                     (radius(z-.002),z-.002),(radius(z+.13),z+.13)))
    prof.append((radius(z_top-.02),z_top-.02))
    shaft=mu.new_bm()
    rings=mu.revolve(shaft,prof,(x,GY,0),segments=8)
    mu.cap_ring(shaft,[r[0] for r in rings],flip=True)
    prev=[r[-1] for r in rings]
    for z in (z_top-.02,z_top+.06):
        new=[]
        for k in range(8):
            dx,dy=math.cos(k*math.pi/4),math.sin(k*math.pi/4)
            scale=.44/max(abs(dx),abs(dy))
            new.append(shaft.verts.new((x+dx*scale,GY+dy*scale,z)))
        mu.bridge_rings(shaft,prev,new)
        prev=new
    mu.cap_ring(shaft,prev)
    mu.recalc_normals(shaft)

    # 榫底直接承在石槽底，四侧预留 1 mm，槽顶留 1 mm。
    # 仅切与柱材相遇的枋头和横挑梁，不对成品组作整场布尔。
    import bpy
    def temporary(mesh,name):
        ob=bpy.data.objects.new(name,mesh)
        bpy.context.scene.collection.objects.link(ob)
        return ob
    stock=temporary(mu.bm_to_mesh(shaft,"Stone_post_stock"),"Stone_post_stock")
    shaft.free()
    cuts=[]
    try:
        for xa,xb,ya,yb,za,zb in sockets:
            if xb<x-.45 or xa>x+.45 or zb<Z_BASE or za>z_top+.06:continue
            cutter=mu.new_bm()
            _bx(cutter,xa-.001,xb+.001,ya-.001,yb+.001,za,zb+.001)
            cut=temporary(mu.bm_to_mesh(cutter,"Timber_mortise"),"Timber_mortise")
            cutter.free()
            cuts.append(cut)
            mod=stock.modifiers.new("Dressed beam pocket","BOOLEAN")
            mod.operation="DIFFERENCE";mod.solver="EXACT";mod.object=cut
        dg=bpy.context.evaluated_depsgraph_get()
        result=bpy.data.meshes.new_from_object(stock.evaluated_get(dg))
        try:
            if not result.polygons:raise ValueError("Empty gate pillar after mortising")
            bm.from_mesh(result)
        finally: bpy.data.meshes.remove(result)
    finally:
        for ob in (stock,*cuts):
            mesh=ob.data;bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(mesh)


# ============================================================ 额枋 / 花板 / 斗拱
def _bracket_proto(C):
    from .hall import _dg_ludou

    def build(bm):
        # All dimensions below are in the local unscaled bracket. +Y projects outward.
        _dg_ludou(bm, (0, 0), (1, 0), (0, 1), 0)
        for f in bm.faces:
            f.material_index = 1
        # First cross arm fits the slot. Distinct arm elevations and scattered bearing blocks.
        def arm(along_x, half, out, bottom, width):
            prof = []
            for i in range(25):
                t = 2*i/24 - 1
                y = bottom + 0.055*abs(t)**2 + 0.018*(1-math.cos(5*math.pi*t))/2
                prof.append((half*t, y))
            prof.extend(((half, bottom+0.145), (-half, bottom+0.145)))
            if along_x:
                _solid_xz(bm, out-width/2, out+width/2, prof)
            else:
                _solid_yz(bm, -width/2, width/2, [(u+out,z) for u,z in prof])
        arm(True, 0.45, 0, 0.160, 0.142)
        arm(False, 0.33, 0.12, 0.305, 0.142)
        for x in (-0.30,0.30):
            _bx(bm,x-.065,x+.065,-.07,.07,.305,.450)
        arm(True, 0.48, 0, 0.450, 0.145)
        arm(True, 0.39, 0.37, 0.450, 0.145)
        # One solid xiaang with a 30 degree upper plane and a cut nose.
        slope = math.tan(math.pi/6)
        a,b = 0.06,0.84
        top=0.83
        tip=top-(b-a)*slope
        _solid_yz(bm,-.059,.059,[(a,top-.10),(b-.035,tip-.105),(b,tip-.065),(b,tip),(a,top)])
        for x in (-.30,.30):
            _bx(bm,x-.064,x+.064,.30,.44,.595,.701)
        arm(True,0.45,.37,.701,.15)
        for x in (-.29,.29):
            _bx(bm,x-.055,x+.055,.31,.43,.846,.94)
        mu.recalc_normals(bm)
    return C.proto("gate_five_puzuo", build, mat=("celadon","crimson"), smooth=30.0)


def _panel_box(bm,x0,x1,y0,y1,z0,z1,openings):
    from .site import _sub_many
    for a,b,c,d in _sub_many((x0,x1,z0,z1),openings):
        _bx(bm,a,b,y0,y1,c,d)


def _panel_frame(bmc, x0, x1, z0, z1, th, openings, w=0.05):
    """花板上的青绿框线（宋式彩画）：前后两面都画，凸出板面 0.008。"""
    for sy in (-1.0, 1.0):
        yy = GY + sy * (th + 0.008)
        def piece(a,b,c,d):
            _panel_box(bmc,a,b,yy-.008,yy+.008,c,d,openings)
        piece(x0,x1,z0,z0+w)
        piece(x0,x1,z1-w,z1)
        piece(x0,x0+w,z0+w,z1-w)
        piece(x1-w,x1,z0+w,z1-w)
        xm = (x0 + x1) * 0.5
        piece(xm-.026,xm+.026,z0+w,z1-w)


def _panel_bays(bml,bmc,x0,x1,z0,z1,th,posts,openings):
    cuts=[x0]
    for p in sorted(posts):
        cuts.extend((p-.061,p+.061))
    cuts.append(x1)
    for a,b in zip(cuts[::2],cuts[1::2]):
        _panel_box(bml,a,b,GY-th,GY+th,z0,z1,openings)
        _panel_frame(bmc,a+.015,b-.015,z0+.015,z1-.015,th,openings)


def _collar(bm,xc,z,thickness,z_top):
    """八角带内净空按柱身收分，两个环端面连续封合。"""
    rings=[]
    for zz,out in ((z,.0005),(z,thickness),(z+.13,thickness),(z+.13,.0005)):
        r=CR+(CRT-CR)*(zz-Z_BASE)/(z_top-Z_BASE)+out
        rings.append([bm.verts.new((xc+r*math.cos(k*math.pi/4),GY+r*math.sin(k*math.pi/4),zz))
                      for k in range(8)])
    for i in range(4): mu.bridge_rings(bm,rings[i],rings[(i+1)%4])


def _ming_stack(bmw, bml, bmc, bm_lac, bm_wh, bm_br,openings,sockets):
    """明间：5 道短枋 + 金匾 +（满铺花板 + 两攒斗拱）。x 向以 0 为对称。"""
    xa, xb = -CX_MID + 0.30, CX_MID - 0.30        # 4.10 净跨
    dy = 0.44                                      # 枋厚（进深）
    # 5 道短枋
    pitch = (7.334 - Z_PAI) / Z_PAI_N
    for k in range(Z_PAI_N):
        z0 = Z_PAI + k * pitch
        _bx(bmw, xa, xb, GY - dy * 0.5, GY + dy * 0.5, z0, z0 + 0.088)
        sockets.append((xa,xb,GY-dy*.5,GY+dy*.5,z0,z0+.088))
    # 匾两侧花板
    for sx in (-1.0, 1.0):
        _bx(bml, sx * 1.38, sx * xb, GY - 0.09, GY + 0.09, Z_BIAN0, Z_BIAN1)
        _panel_frame(bmc, min(sx * 1.44, sx * xb), max(sx * 1.44, sx * xb),
                     Z_BIAN0, Z_BIAN1, 0.09,openings)
    # 金匾：黑漆板 2.6x0.80 + 汉白玉匾心 + 鎏金框
    _bx(bm_lac, -1.30, 1.30, GY - 0.09, GY + 0.09, Z_BIAN0, Z_BIAN1)
    _bx(bm_wh, -1.20, 1.20, GY - 0.155, GY - 0.085,
        Z_BIAN0 + 0.09, Z_BIAN1 - 0.09)
    fb, fd = 0.075, 0.075
    for sx in (-1.0, 1.0):
        _bx(bm_br, sx * 1.30, sx * (1.30 + fb), GY - 0.175, GY - 0.09,
            Z_BIAN0 - 0.02, Z_BIAN1 + 0.02)
    for zz in (Z_BIAN0 - 0.02, Z_BIAN1 - fd + 0.02):
        _bx(bm_br, -1.30, 1.30, GY - 0.175, GY - 0.09, zz, zz + fd)
    # 匾下小横枋（托匾）
    _bx(bmw, -1.30, 1.30, GY - 0.089, GY + 0.089, Z_BIAN0 - 0.10, Z_BIAN0)
    # 明间斗拱带：普拍枋 + 满铺花板（不许透空）+ 两攒斗拱
    _bx(bmw, xa, xb, GY - 0.17, GY + 0.17, Z_BIAN1+.025, Z_DG0)
    _panel_bays(bml,bmc,xa,xb,Z_DG0,Z_DG1,.05,(-2.20,2.20),openings)
    # 斗拱带两根间柱（打断大片花板）
    for sx in (-1.0, 1.0):
        _bx(bmw, sx * 2.20 - 0.06, sx * 2.20 + 0.06, GY - 0.08, GY + 0.08,
            Z_DG0, Z_DG1)


def _ci_stack(bmw, bml, bmc, sx,openings,sockets):
    """次间（4.40…12.00，sx=±1）四道横带：下额枋 → 花板一 → 花板二 → 次楼额枋。

    每道带的顶面都严格等于其上方屋面的底皮（5.51 / 5.96 / 6.78→6.96），
    不许捅进楼板 —— 三条带的 x 收头分别落在边楼(10.45) / 夹楼(7.80) 的起点。
    额枋用 wood_dark（结构）、花板用 wood_lite（雕花板）+ celadon 框线。
    """
    def _r(a, b):
        return (a, b) if sx > 0 else (-b, -a)

    x0, x1 = _r(CX_MID + 0.26, CX_OUT - 0.10)
    _bx(bmw, x0, x1, GY - 0.24, GY + 0.24, Z_EF0, Z_EF1)        # 下额枋
    sockets.append((x0,x1,GY-.24,GY+.24,Z_EF0,Z_EF1))
    x0, x1 = _r(CX_MID + 0.445, 10.45)
    _panel_box(bml, x0, x1, GY - 0.08, GY + 0.08, Z_HB0, Z_HB1,openings)
    _panel_frame(bmc, x0 + 0.05, x1 - 0.05, Z_HB0 + 0.02, Z_HB1-.002, 0.08,openings)
    x0, x1 = _r(CX_MID + 0.445, 7.76)
    _panel_bays(bml,bmc,x0,x1,Z_HB2,Z_HB3,.08,(sx*6.10,),openings)
    # 花板中间一根间柱，把 3.1m 大板断成两格
    _bx(bmw, sx * 6.10 - 0.06, sx * 6.10 + 0.06, GY - 0.09, GY + 0.09,
        Z_HB2, Z_HB3)
    _bx(bmw, x0, x1, GY - 0.26, GY + 0.26, Z_EF2, Z_EF3)        # 次楼额枋



# ============================================================ 楼（悬山：一脊两坡）
def _cap_z(zt, zc, hd, d):
    """Planar top of the two sloped ridge strips, in world Z."""
    return zt - 0.065 - (zt - 0.20 - zc) * d / hd


def _lou(bmr, bm_raft, xa, xb, zt, zc, hd):
    """七楼统一剖面：阶形瓦面、正脊、两端垂脊连成闭合瓦壳。"""
    zs = zt - .20
    rise = zs - zc
    n = max(5, round(rise/.07))
    steps = [hd*(i/n)**(1/1.12) for i in range(n+1)]
    dgrid = sorted(set(steps + [.13, .21, .26]))
    half = []
    for d in dgrid:
        idx = max(i for i,v in enumerate(steps) if v <= d)
        # Tread heights immediately before and after the riser.
        for j in ([idx-1,idx] if d in steps[1:-1] else [min(idx,n-1)]):
            z = zs-rise*j/n
            if d <= .13:
                z = zt
            elif d <= .21:
                z = max(z, zt-.04*(d-.13)/.08)
            elif d <= .26:
                z = max(z, zt-.04-.13*(d-.21)/.05)
            half.append((d,z))
    cross = [(-d,z) for d,z in reversed(half) if d] + half
    xs = [(xa,0),(xa+.040,0),(xa+.080,1),(xa+.205,1),(xa+.245,0),
          (xb-.245,0),(xb-.205,1),(xb-.080,1),(xb-.040,0),(xb,0)]
    vertices={}
    def v(x,y,z):
        key=(round(x,7),round(y,7),round(z,7))
        if key not in vertices:
            vertices[key]=bmr.verts.new((x,GY+y,z))
        return vertices[key]
    def face(vertices):
        ring=list(dict.fromkeys(vertices))
        if len(ring)>=3:
            bmr.faces.new(ring)
    def soffit(d):
        return zs-rise*(abs(d)/hd)**1.12-.14
    top=[]; bottom=[]
    for x,lane in xs:
        top.append([v(x,d,max(z,_cap_z(zt,zc,hd,abs(d))) if lane else z) for d,z in cross])
        bottom.append([v(x,d,soffit(d)) for d,z in cross])
    for i in range(len(xs)-1):
        for j in range(len(cross)-1):
            face([top[i][j],top[i+1][j],top[i+1][j+1],top[i][j+1]])
            face([bottom[i][j],bottom[i][j+1],bottom[i+1][j+1],bottom[i+1][j]])
        for j in (0,-1):
            face([bottom[i][j],bottom[i+1][j],top[i+1][j],top[i][j]])
    for i in (0,-1):
        # The gable side has one contour. Shared vertices along a riser avoid
        # overlapping coplanar quads at the vertical step.
        face(top[i]+bottom[i][::-1])

    n = max(2, round((xb-xa)/.36))
    for sy in (-1,1):
        ye=GY+sy*hd
        y0,y1=sorted((ye+sy*.002,ye+sy*.036))
        _bx(bm_raft,xa+.005,xb-.005,y0,y1,zc-.13,zc-.028)
        for j in range(n):
            x=xa+(xb-xa)*(j+.5)/n
            _disc(bmr,(x,ye+sy*.042,zc-.048),(0,sy,0),.065,12)
            # Two separate members following the underside. End grain is a
            # material assignment on the actual round face.
            path=[(x,GY+sy*hd*t,soffit(hd*t)-.096) for t in (.29,.48,.66,.83,.98)]
            rings=mu.swept_tube(bm_raft,path,.036,segments=16,caps=False)
            mu.cap_ring(bm_raft,rings[0],flip=True)
            cap=bm_raft.faces.new(rings[-1]); cap.material_index=1
            d0,d1=hd*.64,hd+.105
            _solid_yz(bm_raft,x-.029,x+.029,[(GY+sy*d0,soffit(d0)-.009),
                      (ye,soffit(hd)-.009),(GY+sy*d1,soffit(hd)-.030),
                      (GY+sy*d1,soffit(hd)-.076),(ye,soffit(hd)-.055),
                      (GY+sy*d0,soffit(d0)-.055)])


def _chiwen_one(bm, xe, toward, zt, h):
    """双颚由两组椭圆截面放样；吻身与卷尾共用收尖的连续曲面。"""
    def p(u,v,w):
        return (xe+toward*u*h,GY+v*h,zt+w*h)
    def loft(sections, vertical):
        rings=[]
        for u,z,rx,ry in sections:
            ring=[]
            for i in range(20):
                a=i*math.tau/20
                co=p(u+rx*math.cos(a),ry*math.sin(a),z) if vertical else p(u,ry*math.cos(a),z+rx*math.sin(a))
                ring.append(bm.verts.new(co))
            rings.append(ring)
        mu.cap_ring(bm,rings[0],flip=True)
        for a,b in zip(rings,rings[1:]): mu.bridge_rings(bm,a,b)
        return rings[-1]
    spine=[(.28,.004,.20,.14),(.27,.16,.22,.18),(.27,.34,.18,.16),
           (.31,.51,.15,.13),(.37,.66,.12,.105),(.44,.79,.085,.077),
           (.48,.90,.052,.052),(.46,.97,.029,.030),(.415,.985,.015,.017),
           (.384,.966,.008,.008)]
    last=loft(spine,True)
    tip=bm.verts.new(p(.365,0,.944))
    for k in range(len(last)): bm.faces.new((last[k],last[(k+1)%len(last)],tip))
    for z,thick in ((.205,.057),(.062,.036)):
        last=loft([(.24,z+.02,thick*1.5,.155),(.09,z,thick,.17),
                   (-.015,z,thick*.86,.14),(-.095,z+.015,thick*.40,.11)], False)
        mu.cap_ring(bm,last)
    from .hall import _orn_ellipsoid
    for sy in (-1,1):
        _orn_ellipsoid(bm,p(.15,sy*.143,.26),(.042*h,.033*h,.04*h),seg=12,rings=6)
        fang=[p(-.053,sy*.077,.195),p(-.048,sy*.078,.164),p(-.031,sy*.077,.122)]
        mu.swept_tube(bm,fang,.016*h,segments=8,radius_end=.002*h)
        for row in range(4):
            for i in range(3):
                z=.30+.079*row; u=.20+.05*i+.015*(row%2)
                arc=[p(u+.035*math.sin(t),sy*(.166-.012*row),z+.029*math.cos(t))
                     for t in [math.pi*(k/8-.5) for k in range(9)]]
                mu.swept_tube(bm,arc,.006*h,segments=5,radius_end=.004*h)


def _beast_proto(C, kind):
    from .hall import _orn_ellipsoid
    def build(bm):
        def oval(c,r): _orn_ellipsoid(bm,c,r,seg=10,rings=5)
        def tube(path,r,tip): mu.swept_tube(bm,path,r,segments=6,radius_end=tip)
        _bx(bm,-.084,.084,-.041,.041,0,.016)
        oval((0,0,.075),(.073,.034,.040))
        for sx in (-1,1):
            for sy in (-1,1):
                tube([(sx*.045,sy*.020,.073),(sx*.057,sy*.024,.041),(sx*.045,sy*.028,.018)],.011,.008)
        tube([(.032,0,.096),(.057,0,.13),(.078,0,.145)],.029,.020)
        oval((.085,0,.147),(.030,.021,.024))
        if kind=="horse":
            oval((.108,0,.141),(.021,.016,.012))
            for sy in (-1,1): tube([(.073,sy*.012,.158),(.068,sy*.016,.192)],.009,.002)
            tube([(-.055,0,.078),(-.082,0,.087),(-.098,0,.062),(-.100,0,.025)],.013,.004)
        elif kind=="dragon":
            for sy in (-1,1):
                tube([(.08,sy*.013,.159),(.060,sy*.021,.179),(.048,sy*.026,.194)],.007,.0015)
                tube([(.105,sy*.014,.146),(.114,sy*.024,.140),(.119,sy*.043,.150)],.004,.001)
            tube([(-.060,0,.080),(-.088,0,.093),(-.10,.01,.116),(-.12,.01,.122)],.014,.002)
        else:
            tube([(.10,0,.151),(.124,0,.145),(.128,0,.137)],.010,.0015)
            for sy in (-1,1):
                for j in range(3):
                    tube([(.013,sy*.022,.091),(-.024,sy*.042,.116+j*.006),
                          (-.068-j*.011,sy*(.050+.010*j),.13+j*.012)],.009,.0015)
            for j in (-1,0,1):
                tube([(-.050,0,.082),(-.080,.012*j,.073),(-.109,.020*j,.104),
                      (-.135,.025*j,.116)],.008,.0015)
        mu.recalc_normals(bm)
    return C.proto("gate_ridge_"+kind,build,mat="roof_dai",smooth=35.0)


def _screen_wall(bmw, bmd, sx):
    """两侧景墙：白墙 3.60 高 + 石勒脚 + 黛瓦墙帽 + 3 樘漏窗。"""
    x0, x1 = (CX_OUT, SC_X1) if sx > 0 else (-SC_X1, -CX_OUT)
    y0, y1 = GY - SC_T * 0.5, GY + SC_T * 0.5
    zb = Z0 + 0.34                                     # 石勒脚顶
    zt = Z0 + SC_H
    holes = [(sx * c - WIN_W * 0.5, sx * c + WIN_W * 0.5, WIN_Z0, WIN_Z1)
             for c in WIN_C]
    holes.sort(key=lambda h: h[0])
    # 勒脚
    mu.box_mm(bmd, x0, x1, y0 - 0.05, y1 + 0.05, Z0, zb)
    # 墙身（按洞口切）
    cur = x0
    for (h0, h1, hz0, hz1) in holes:
        if h0 > cur:
            _bx(bmw, cur, h0, y0, y1, zb, zt)
        _bx(bmw, h0, h1, y0, y1, zb, hz0)
        _bx(bmw, h0, h1, y0, y1, hz1, zt)
        cur = h1
    if cur < x1:
        _bx(bmw, cur, x1, y0, y1, zb, zt)
    # 漏窗：木框 + 方格棂
    for (h0, h1, hz0, hz1) in holes:
        f = 0.09
        _bx(bmw, h0, h1, y0 - 0.03, y0 + 0.03, hz0 - f, hz0)
        _bx(bmw, h0, h1, y0 - 0.03, y0 + 0.03, hz1, hz1 + f)
        _bx(bmw, h0 - f, h0, y0 - 0.03, y0 + 0.03, hz0, hz1)
        _bx(bmw, h1, h1 + f, y0 - 0.03, y0 + 0.03, hz0, hz1)
        cw = (h1 - h0) / 2.0
        for i in range(1, 2):
            xx = h0 + cw * i
            _bx(bmw, xx - 0.035, xx + 0.035, y0 - 0.02, y0 + 0.02, hz0, hz1)
        zh = (hz1 - hz0) / 2.0
        xx = h0 + cw
        _bx(bmw, h0, xx, y0 - 0.02, y0 + 0.02, hz0 + zh - 0.035,
            hz0 + zh + 0.035)
        _bx(bmw, xx, h1, y0 - 0.02, y0 + 0.02, hz0 + zh - 0.035,
            hz0 + zh + 0.035)
    # 黛瓦墙帽：两坡 + 脊
    cap = [(-SC_T * 0.5 - 0.10, zt), (-SC_T * 0.5 - 0.10, zt + 0.12),
           (0.0, zt + 0.30), (SC_T * 0.5 + 0.10, zt + 0.12),
           (SC_T * 0.5 + 0.10, zt)]
    _solid_yz(bmd, x0, x1, [(GY + p[0], p[1]) for p in cap])
    _solid_yz(bmd, x0, x1, [(GY - 0.08, zt + 0.28), (GY - 0.08, zt + 0.40),
                            (GY, zt + 0.44), (GY + 0.08, zt + 0.40),
                            (GY + 0.08, zt + 0.28)])


# ============================================================ 主入口
def build(C):
    coll = C.coll("gate")
    cn = "迎宾牌楼"
    M = None

    bm_st = mu.new_bm()
    bm_br = mu.new_bm()
    bm_wd = mu.new_bm()
    bm_wl = mu.new_bm()      # 花板（wood_lite）
    bm_ce = mu.new_bm()
    bm_dai = mu.new_bm()
    bm_lac = mu.new_bm()
    bm_wh = mu.new_bm()
    bm_sd = mu.new_bm()      # stone_dark 柱础

    # ---- 柱、柱础、夹杆石、柱箍
    for sx in (-1.0, 1.0):
        for xc, zt in ((sx * CX_MID, Z_PL_TOP), (sx * CX_OUT, Z_PL_OUT)):
            _col_base(bm_sd, bm_st, bm_br, xc)
            # 两道 bronze 柱箍
            for zz in (Z_BASE + 0.10, 3.45):
                _collar(bm_br,xc,zz,.035,zt)

    # ---- 额枋 / 花板 / 斗拱 / 金匾
    # 明间金匾：汉白玉匾心正面加「文脉华章」四字鎏金匾额（匾心前面 y = GY-0.155）
    bm_tx = mu.new_bm()
    _plaque_text(bm_tx, "文脉华章", 0.46, GY - 0.163,
                 (Z_BIAN0 + Z_BIAN1) * 0.5, step=0.56)
    openings=[]
    sockets=[]

    bracket = _bracket_proto(C)
    beasts = {k:_beast_proto(C,k) for k in ("phoenix","dragon","horse")}
    for (nm, xa, xb, zt, zc, hd, cnl) in LOUS:
        _lou(bm_dai,bm_wd,xa,xb,zt,zc,hd)
        height = 1.05 if nm=="lou_main" else min(.70,(xb-xa)*.22)
        _chiwen_one(bm_br,xa+.11,1,zt,height)
        _chiwen_one(bm_br,xb-.11,-1,zt,height)
        scale=.48*hd
        base=.565
        bearing=base+.37*scale
        rise=zt-.20-zc
        purlin_top=zt-.20-rise*(bearing/hd)**1.12-.14-.136
        zb=purlin_top-.065-.94*scale-.001
        for xe in (xa+.45,xb-.45):
            end=base+.25*scale
            box=(xe-.09,xe+.09,GY-end,GY+end,zb-.065,zb-.001)
            _bx(bm_wd,*box)
            openings.append((box[0]-.001,box[1]+.001,box[4],box[5]+.001))
            sockets.append(box)
        for side in (-1,1):
            py=GY+side*bearing
            _bx(bm_wd,xa+.01,xb-.01,py-.026,py+.026,purlin_top-.065,purlin_top)
            for idx,xe in enumerate((xa+.45,xb-.45)):
                C.place_at(bracket,(xe,GY+side*base,zb),rot_z=0 if side==1 else 180,
                           scale=scale,name=f"gate_puzuo_{nm}_{side}_{idx}",cat="detail",
                           coll_path=coll,cn=cnl+"·栌斗五铺作下昂")
            front=Vector((0,side,-rise/hd)).normalized()
            lateral=Vector((-side,0,0))
            normal=front.cross(lateral).normalized()
            basis=Matrix((front,lateral,normal)).transposed().to_4x4()
            for ix,x in enumerate((xa+.1425,xb-.1425)):
                for kind,frac in zip(beasts,(.47,.66,.85)):
                    d=frac*hd
                    pos=Vector((x,GY+side*d,_cap_z(zt,zc,hd,d)))
                    matrix=Matrix.Translation(pos+normal*.001) @ basis @ Matrix.Scale(.7*hd,4)
                    C.place_world(beasts[kind],matrix,name=f"gate_beast_{nm}_{side}_{ix}_{kind}",
                                  cat="roof",coll_path=coll,cn=cnl+"·垂脊走兽")

    _ming_stack(bm_wd,bm_wl,bm_ce,bm_lac,bm_wh,bm_br,openings,sockets)
    for sx in (-1,1):
        _ci_stack(bm_wd,bm_wl,bm_ce,sx,openings,sockets)
    for sx in (-1,1):
        for x,zt in ((sx*CX_MID,Z_PL_TOP),(sx*CX_OUT,Z_PL_OUT)):
            _column(bm_st,x,zt,sockets)
    # ---- 两侧景墙：v13 为四面通透的宋风水院，牌楼独立立于青石台基，
    #      不再接景墙/院墙（否则会与南门西侧的镂金坊相距不足 0.3m）。
    # for sx in (-1.0, 1.0):
    #     _screen_wall(bm_wh, bm_dai, sx)

    # ---- 落对象
    _emit(C, bm_sd, M, "gate_plinth", "detail", coll, cn + "·青石柱础",
          "stone_dark", flat=True)
    _emit(C, bm_st, M, "gate_stone", "detail", coll, cn + "·汉白玉柱身与柱础",
          "stone_lite", flat=True)
    _emit(C, bm_br, M, "gate_bronze", "detail", coll, cn + "·鎏金柱箍与匾框",
          "bronze")
    _emit(C, bm_wd, M, "gate_beam", "detail", coll, cn + "·额枋与椽头",
          ("wood_dark","crimson"))
    _emit(C, bm_wl, M, "gate_huaban", "detail", coll, cn + "·花板",
          "wood_lite", flat=True)
    _emit(C, bm_ce, M, "gate_gong", "detail", coll, cn + "·青绿拱身与框线",
          "celadon")
    _emit(C, bm_dai, M, "gate_roof", "roof", coll, cn + "·七楼瓦顶墙帽",
          "roof_dai")
    _emit(C, bm_lac, M, "gate_bian", "detail", coll, cn + "·金匾底板",
          "lacquer", flat=True)
    # v13 无景墙，但 bm_wh 里装着明间「汉白玉匾心」，不能因为景墙禁用就一起丢掉
    _emit(C, bm_wh, M, "gate_bianxin", "detail", coll, cn + "·汉白玉匾心",
          "stone_lite", flat=True)
    _emit(C, bm_tx, M, "gate_bianzi", "detail", coll, cn + "·鎏金匾字",
          "bronze", flat=True)
def _plaque_text(bm, text, size, yface, cz, step=0.56):
    """在 y=yface 的竖直面上排一行居中宋体字（匾额用）。

    做法：给每个字建一条 FONT 曲线 -> 转 mesh -> 乘上朝向 -Y 的基矩阵，
    再逐顶点/逐面拷进目标 bmesh。字体优先微软雅黑，其次黑体/宋体。
    """
    import os
    import bpy
    import bmesh
    from mathutils import Matrix

    fp = None
    for cand in (r"C:\Windows\Fonts\msyh.ttc",
                 r"C:\Windows\Fonts\simhei.ttf",
                 r"C:\Windows\Fonts\simsun.ttc"):
        if os.path.exists(cand):
            fp = cand
            break

    n = len(text)
    x0 = -step * (n - 1) * 0.5
    for k, ch in enumerate(text):
        cu = bpy.data.curves.new("tmp_bian", "FONT")
        cu.body = ch
        cu.size = size
        cu.extrude = 0.010
        cu.align_x = "CENTER"
        cu.align_y = "CENTER"
        cu.resolution_u = 2
        if fp:
            try:
                cu.font = bpy.data.fonts.load(fp, check_existing=True)
            except Exception:
                pass
        ob = bpy.data.objects.new("tmp_bian", cu)
        bpy.context.scene.collection.objects.link(ob)
        M = Matrix((
            (1.0, 0.0, 0.0, x0 + step * k),
            (0.0, 0.0, -1.0, yface),
            (0.0, 1.0, 0.0, cz),
            (0.0, 0.0, 0.0, 1.0),
        ))
        ob.matrix_world = M
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        me.transform(M)
        tmp = bmesh.new()
        tmp.from_mesh(me)
        vmap = {}
        for v in tmp.verts:
            vmap[v] = bm.verts.new(v.co)
        for f in tmp.faces:
            try:
                bm.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                pass
        tmp.free()
        bpy.data.meshes.remove(me)
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.curves.remove(cu)
