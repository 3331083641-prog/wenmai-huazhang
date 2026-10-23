"""V5 building shell: hollow walls with real openings, joinery, plaque, lanterns.

Design intent, matching the concept art:
  * the walls are a HOLLOW SHELL with real rectangular openings. The first pass
    built one solid box and stuck a porch and window frames onto its surface,
    which is why the entrance was invisible and every window looked painted on;
  * a recessed entrance porch ~1.1 m deep, with the door leaves standing open so
    the lit interior reads from the street;
  * upper storey inset, open balcony with a proper balustrade;
  * an attic band between the second-floor window head and the main roof, which
    gives the skirt roof something to attach to;
  * sparse lattice, not a dense screen: the wall must stay a wall.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Matrix, Vector

import gal5 as G

# Set-back of the upper storey. Kept at 0 on purpose: the web places every
# artwork at (anchor + 0.06 along the wall normal), so the wall INNER face must
# coincide with the layout anchors (x +-4.04, y -4.14 / +3.04). A 0.16 m
# set-back pushed the inner face 0.16 m past the anchor and buried all 15
# paintings inside the wall. The storey step now reads from ATTIC_INSET only.
INSET = 0.00        # second storey set-back
ATTIC_INSET = 0.34  # attic band set-back (leaves a ledge for the skirt roof)
WALL_T = 0.16       # wall thickness (tuned so inner faces hit the anchors)


def _front_y():
    """Facade plane. +Y is the street side and the web's "front" camera."""
    return G.BCY + G.BD * 0.5


def _back_y():
    return G.BCY - G.BD * 0.5


def _window_glow():
    return G.mat("M_window_glow", (0.99, 0.84, 0.62), rough=0.62,
                 emit=(1.0, 0.78, 0.50), emit_str=0.75, alpha=0.62)


# ------------------------------------------------------------------ walls
def wall_with_holes(name, axis, at, u0, u1, z0, z1, holes, col,
                    material=None, thick=WALL_T):
    """Wall slab with real rectangular openings.

    axis='x': wall runs along X, `at` is its Y coordinate.
    axis='y': wall runs along Y, `at` is its X coordinate.
    holes : [(u_center, u_width, z_low, z_high)] non-overlapping in u.
    """
    material = material or G.P("plaster")
    obs = []
    holes = sorted(holes, key=lambda h: h[0])

    def seg(tag, uu0, uu1, zz0, zz1):
        if uu1 - uu0 < 1e-4 or zz1 - zz0 < 1e-4:
            return
        if axis == "x":
            dims = (uu1 - uu0, thick, zz1 - zz0)
            loc = ((uu0 + uu1) * 0.5, at, (zz0 + zz1) * 0.5)
        else:
            dims = (thick, uu1 - uu0, zz1 - zz0)
            loc = (at, (uu0 + uu1) * 0.5, (zz0 + zz1) * 0.5)
        obs.append(G.add_box(name + tag, dims, loc, col, material))

    cur = u0
    for i, (uc, uw, hz0, hz1) in enumerate(holes):
        a = max(uc - uw * 0.5, u0)
        b = min(uc + uw * 0.5, u1)
        seg("_S%d" % i, cur, a, z0, z1)
        seg("_B%d" % i, a, b, z0, hz0)
        seg("_T%d" % i, a, b, hz1, z1)
        cur = b
    seg("_SEND", cur, u1, z0, z1)
    return obs


# Opening schedule. The wall builder and the joinery builder both read it, so a
# frame can never end up sitting on a solid wall again.
F1_PORCH = (0.0, 3.16, G.F1, G.F1 + 2.52)
F1_BAY_U = 2.72
F1_BAY_W = 2.10
F1_BAY_Z0 = G.F1 + 0.30
F1_BAY_Z1 = G.F1 + 2.68
F1_SIDE_W = [(G.BCY - 2.35, 1.62, G.F1 + 1.05, G.F1 + 2.39),
             (G.BCY + 0.55, 1.62, G.F1 + 1.05, G.F1 + 2.39)]
F1_BACK_W = [(x, 1.50, G.F1 + 1.14, G.F1 + 2.42) for x in (-2.35, 0.0, 2.35)]
F2_SIDE_W = [(G.BCY - 2.30, 1.50, G.F2 + 1.00, G.F2 + 2.24),
             (G.BCY + 0.60, 1.50, G.F2 + 1.00, G.F2 + 2.24)]
F2_BACK_W = [(x, 1.44, G.F2 + 1.04, G.F2 + 2.24) for x in (-2.40, 0.0, 2.40)]


def build_walls(col):
    obs = []
    hw, hd = G.BW * 0.5, G.BD * 0.5
    fy, by = _front_y(), _back_y()

    # ---- first floor
    bays = [(sign * F1_BAY_U, F1_BAY_W, F1_BAY_Z0, F1_BAY_Z1) for sign in (-1, 1)]
    obs.extend(wall_with_holes("WALL_F1_Front", "x", fy - WALL_T * 0.5,
                               -hw, hw, G.F1, G.F2, [F1_PORCH] + bays, col))
    obs.extend(wall_with_holes("WALL_F1_Back", "x", by + WALL_T * 0.5,
                               -hw, hw, G.F1, G.F2, F1_BACK_W, col))
    for sx in (-1, 1):
        obs.extend(wall_with_holes("WALL_F1_Side%d" % sx, "y",
                                   sx * (hw - WALL_T * 0.5), by, fy,
                                   G.F1, G.F2, F1_SIDE_W, col))

    # ---- second floor (inset)
    hw2, hd2 = hw - INSET, hd - INSET
    fy2, by2 = G.BCY + hd2, G.BCY - hd2
    # the front of the upper storey is a sill wall under an open bay: a balcony
    # is meant to be walked on, so it must not be sealed behind glass
    obs.append(G.add_box("WALL_F2_Sill", (hw2 * 2, WALL_T, 0.92),
                         (0, fy2 - WALL_T * 0.5, G.F2 + 0.46), col, G.P("plaster")))
    obs.append(G.add_box("WALL_F2_SillCap", (hw2 * 2 + 0.12, WALL_T + 0.10, 0.08),
                         (0, fy2 - WALL_T * 0.5, G.F2 + 0.94), col, G.P("wood_m")))
    obs.extend(wall_with_holes("WALL_F2_Back", "x", by2 + WALL_T * 0.5,
                               -hw2, hw2, G.F2, G.TOP, F2_BACK_W, col))
    for sx in (-1, 1):
        obs.extend(wall_with_holes("WALL_F2_Side%d" % sx, "y",
                                   sx * (hw2 - WALL_T * 0.5), by2, fy2,
                                   G.F2, G.TOP, F2_SIDE_W, col))

    # ---- attic band and trims
    obs.append(G.add_box("WALL_Attic",
                         (G.BW - ATTIC_INSET * 2, G.BD - ATTIC_INSET * 2,
                          G.ATTIC - G.TOP),
                         (0, G.BCY, (G.TOP + G.ATTIC) * 0.5), col, G.P("plaster_d")))
    obs.append(G.add_box("WALL_Band", (G.BW + 0.14, G.BD + 0.14, 0.20),
                         (0, G.BCY, G.F2 + 0.02), col, G.P("wood_m")))
    # 墙基座：正立面在门口断开（否则 0.4 m 高的石条会横在门槛位置挡门）
    plinth_proud = 0.09
    plinth_h = 0.40
    plinth_z = G.F1 + plinth_h * 0.5
    door_gap = 1.72
    fx0 = -G.BW * 0.5 - plinth_proud
    fx1 = G.BW * 0.5 + plinth_proud
    for sgn in (-1, 1):
        x0 = fx0 if sgn < 0 else door_gap
        x1 = -door_gap if sgn < 0 else fx1
        obs.append(G.add_box("WALL_PlinthF%d" % sgn, (x1 - x0, 0.18, plinth_h),
                             ((x0 + x1) * 0.5, _front_y() + 0.09, plinth_z),
                             col, G.P("stone")))
    obs.append(G.add_box("WALL_PlinthB", (G.BW + 0.18, 0.18, plinth_h),
                         (0, _back_y() - 0.09, plinth_z), col, G.P("stone")))
    for sgn in (-1, 1):
        obs.append(G.add_box("WALL_PlinthS%d" % sgn, (0.18, G.BD + 0.18, plinth_h),
                             (sgn * (G.BW * 0.5 + 0.09), G.BCY, plinth_z), col,
                             G.P("stone")))
    obs.append(G.add_box("WALL_HeadBeam", (G.BW - ATTIC_INSET * 2 + 0.22,
                                           G.BD - ATTIC_INSET * 2 + 0.22, 0.24),
                         (0, G.BCY, G.ATTIC - 0.12), col, G.P("wood_m")))
    # Floor 2 is a RING around a 6.6 x 4.8 void. A solid slab here becomes a
    # ceiling over the ground floor and the hall stops reading as a double
    # height space, which is the exact failure the reference rules out.
    ow, od = 6.6, 4.8
    ring_t = 0.16
    z_ring = G.F2 - 0.10
    for sy in (-1, 1):
        obs.append(G.add_box("WALL_F2_RingFB%d" % sy,
                             (G.BW - 1.10, (G.BD - 1.10 - od) * 0.5, ring_t),
                             (0, G.BCY + sy * (od * 0.5 + (G.BD - 1.10 - od) * 0.25),
                              z_ring), col, G.P("wood_m")))
    for sx in (-1, 1):
        obs.append(G.add_box("WALL_F2_RingLR%d" % sx,
                             ((G.BW - 1.10 - ow) * 0.5, od, ring_t),
                             (sx * (ow * 0.5 + (G.BW - 1.10 - ow) * 0.25),
                              G.BCY, z_ring), col, G.P("wood_m")))
    # trimmed opening edge so the void has a visible lip from below
    for sy in (-1, 1):
        obs.append(G.add_box("WALL_F2_LipFB%d" % sy, (ow + 0.24, 0.10, 0.16),
                             (0, G.BCY + sy * od * 0.5, z_ring - 0.10), col,
                             G.P("wood")))
    for sx in (-1, 1):
        obs.append(G.add_box("WALL_F2_LipLR%d" % sx, (0.10, od + 0.24, 0.16),
                             (sx * ow * 0.5, G.BCY, z_ring - 0.10), col,
                             G.P("wood")))
    return obs


# ------------------------------------------------------------------ joinery
def _put(col, rot_z, cx, cy, name, dims, u, v, n, material):
    ca, sa = math.cos(rot_z), math.sin(rot_z)
    x = cx + ca * u + sa * n
    y = cy + sa * u + ca * n
    return G.add_box(name, dims, (x, y, v), col, material, rot_z=rot_z)


def lattice_window(name, cx, cy, cz, w, h, col, rot_z=0.0, cols=4, rows=3):
    """Joinery that fills a real opening: frame, sparse bars, lit panel."""
    obs = []
    glow = _window_glow()

    def put(nm, dims, u, v, n, material):
        return _put(col, rot_z, cx, cy, name + nm, dims, u, cz + v, n, material)

    for sign in (-1, 1):
        obs.append(put("_FrmV%d" % sign, (0.085, 0.10, h + 0.16),
                       sign * (w * 0.5 + 0.035), 0.0, 0.03, G.P("wood")))
        obs.append(put("_FrmH%d" % sign, (w + 0.18, 0.10, 0.085), 0.0,
                       sign * (h * 0.5 + 0.035), 0.03, G.P("wood")))
    for i in range(1, cols):
        u = -w * 0.5 + w * i / cols
        obs.append(put("_BarV%d" % i, (0.042, 0.07, h), u, 0.0, 0.02, G.P("wood_l")))
    for j in range(1, rows):
        v = -h * 0.5 + h * j / rows
        obs.append(put("_BarH%d" % j, (w, 0.07, 0.042), 0.0, v, 0.02, G.P("wood_l")))
    obs.append(put("_Glow", (w, 0.02, h), 0.0, 0.0, -0.06, glow))
    obs.append(put("_Sill", (w + 0.26, 0.24, 0.09), 0.0,
                   -(h * 0.5 + 0.09), 0.09, G.P("wood_m")))
    return obs


def lattice_wall(name, cx, cy, cz, w, h, col, rot_z=0.0, cols=5, rows=4):
    """Ground-floor lattice door panel filling a bay opening."""
    obs = []
    glow = _window_glow()

    def put(nm, dims, u, v, n, material):
        return _put(col, rot_z, cx, cy, name + nm, dims, u, cz + v, n, material)

    obs.append(put("_Glow", (w, 0.02, h), 0.0, 0.0, -0.05, glow))
    obs.append(put("_RailB", (w, 0.16, 0.11), 0.0, -(h * 0.5 - 0.08), 0.03,
                   G.P("wood")))
    obs.append(put("_RailT", (w, 0.12, 0.10), 0.0, h * 0.5 - 0.06, 0.03,
                   G.P("wood")))
    for i in range(cols + 1):
        u = -w * 0.5 + w * i / cols
        obs.append(put("_Stile%d" % i, (0.06, 0.11, h), u, 0.0, 0.04, G.P("wood")))
    for j in range(1, rows):
        v = -h * 0.5 + h * j / rows
        obs.append(put("_Rail%d" % j, (w, 0.06, 0.045), 0.0, v, 0.05, G.P("wood_l")))
    return obs


def build_facade(col):
    obs = []
    hw, hd = G.BW * 0.5, G.BD * 0.5
    fy, by = _front_y(), _back_y()

    for sign in (-1, 1):
        cz = (F1_BAY_Z0 + F1_BAY_Z1) * 0.5
        obs.extend(lattice_wall("LAT_F1_%d" % sign, sign * F1_BAY_U,
                                fy, cz, F1_BAY_W,
                                F1_BAY_Z1 - F1_BAY_Z0, col, rot_z=0.0))
    for sx in (-1, 1):
        for k, (uy, uw, z0, z1) in enumerate(F1_SIDE_W):
            obs.extend(lattice_window("WIN_F1_%d_%d" % (sx, k),
                                      sx * hw, uy,
                                      (z0 + z1) * 0.5, uw, z1 - z0, col,
                                      rot_z=math.pi * 0.5 if sx < 0 else -math.pi * 0.5,
                                      cols=4, rows=3))
    for k, (ux, uw, z0, z1) in enumerate(F1_BACK_W):
        obs.extend(lattice_window("WIN_F1_B%d" % k, ux, by,
                                  (z0 + z1) * 0.5, uw, z1 - z0, col,
                                  rot_z=math.pi, cols=4, rows=3))
    hw2 = hw - INSET
    for sx in (-1, 1):
        for k, (uy, uw, z0, z1) in enumerate(F2_SIDE_W):
            obs.extend(lattice_window("WIN_F2_%d_%d" % (sx, k),
                                      sx * hw2, uy,
                                      (z0 + z1) * 0.5, uw, z1 - z0, col,
                                      rot_z=math.pi * 0.5 if sx < 0 else -math.pi * 0.5,
                                      cols=4, rows=3))
    for k, (ux, uw, z0, z1) in enumerate(F2_BACK_W):
        obs.extend(lattice_window("WIN_F2_B%d" % k, ux,
                                  G.BCY - (G.BD * 0.5 - INSET),
                                  (z0 + z1) * 0.5, uw, z1 - z0, col,
                                  rot_z=math.pi, cols=4, rows=3))
    # 二层正立面：原来整排是空洞，从外面能直接看到室内后墙那扇窗，像一扇
    # 悬空的窗户；现补一排对称格心窗，立面读数完整、左右也对称。
    for k, ux in enumerate((-3.15, -1.05, 1.05, 3.15)):
        obs.extend(lattice_window("WIN_F2_F%d" % k, ux, fy - WALL_T * 0.5,
                                  5.48, 1.62, 1.80, col,
                                  rot_z=0.0, cols=4, rows=3))
    obs.append(G.huiwen_band("BAND_Hui", G.BW - 1.4, 0.12, 0.04,
                             (0, fy + 0.10, G.F2 + 0.02), col, G.P("gold"),
                             axis="x", period=0.38, bar=0.042))
    return obs


# ------------------------------------------------------------------ porch
def build_entrance_porch(col):
    """Recessed entrance inside the real opening in the front wall."""
    obs = []
    depth = 1.10
    fy = _front_y()
    w = 3.16
    z0 = G.F1
    obs.append(G.add_box("PORCH_Ceiling", (w, depth, 0.16),
                         (0, fy - depth * 0.5, G.F1 + 2.44), col, G.P("wood")))
    obs.append(G.add_box("PORCH_Floor", (w, depth, 0.10),
                         (0, fy - depth * 0.5, z0 - 0.05), col, G.P("stone_l")))
    for sign in (-1, 1):
        obs.append(G.add_box("PORCH_Jamb%d" % sign, (0.16, 0.22, 2.52),
                             (sign * (w * 0.5 - 0.09), fy - depth + 0.14,
                              z0 + 1.26), col, G.P("wood")))
    obs.append(G.add_box("PORCH_Lintel", (w - 0.06, 0.24, 0.26),
                         (0, fy - depth + 0.14, z0 + 2.36), col, G.P("wood")))
    # 门扇不再藏在凹龛里（旧版整扇门退到立面内 0.88 m，从外面看像门在屋里），
    # 改由 build_door() 立在立面平面上，并带可交互的铰链节点。
    for i in range(2):
        obs.append(G.add_box("PORCH_Step%d" % i, (w + 0.66, 0.34, 0.13),
                             (0, fy + 0.17 + i * 0.34, z0 - 0.065 - i * 0.13),
                             col, G.P("stone_l")))
    return obs


def build_door(col):
    """立面双扇格心门 + 可交互铰链（向外开）。

    造型：抱框、上槛、门簪；两扇格心门由大边、抹头、上下两段棂条格心、
    纸绢、铜门环组成。**没有门槛**——门口与门廊地面齐平，门扇底只离地 2 mm，
    这样人/视线都不会被一道坎挡住。

    开门方式：两扇向外（朝街 +Y）各转 85°，铰链在立面外侧；
    门廊只有 1.10 m 深，若向内开会扫到廊内的墙面（旧版就是向内开，穿模）。
    """
    obs = []
    fy = _front_y()
    z0 = G.F1
    zb = z0 + 0.002      # 门扇底只比地面高 2 mm，不做门槛
    h = 2.34          # 门顶 2.592，让开门廊天花底面 2.61（否则开门扫到顶板）
    half = 1.52          # 门轴到中缝
    leaf_w = 1.48
    y_face = fy - 0.10   # 门扇平面（立面内侧 10 cm）
    th = 0.075
    lintel_bottom = zb + h + 0.006

    for s in (-1, 1):
        obs.append(G.add_box("DOOR_Jamb%d" % s, (0.15, 0.24, h + 0.10),
                             (s * (half + 0.09), y_face, zb + (h + 0.10) * 0.5),
                             col, G.P("wood_d")))
        obs.append(G.add_box("DOOR_JambGold%d" % s, (0.02, 0.26, h + 0.04),
                             (s * (half + 0.015), y_face, zb + (h + 0.04) * 0.5),
                             col, G.P("gold")))
    obs.append(G.add_box("DOOR_Lintel", (3.44, 0.26, 0.24),
                         (0, y_face, lintel_bottom + 0.12), col, G.P("wood_d")))
    obs.append(G.add_box("DOOR_LintelGold", (3.22, 0.28, 0.025),
                         (0, y_face, lintel_bottom + 0.005), col, G.P("gold")))
    for s in (-1, 1):
        obs.append(G.add_box("DOOR_Zan%d" % s, (0.16, 0.30, 0.16),
                             (s * 0.62, y_face, lintel_bottom + 0.13), col,
                             G.P("gold")))

    for s, tag in ((-1, "L"), (1, "R")):
        hinge = bpy.data.objects.new("DOOR_Hinge" + tag, None)
        hinge.empty_display_size = 0.20
        col.objects.link(hinge)
        hinge.location = (s * half, y_face, zb)

        def part(name, dims, loc, mat, hinge=hinge):
            ob = G.add_box(name, dims, loc, col, mat)
            ob.parent = hinge
            ob.matrix_parent_inverse = Matrix.Translation(-Vector(hinge.location))
            obs.append(ob)
            return ob

        def wx(lx):
            return s * (half - lx)

        cx = wx(leaf_w * 0.5)
        # 大边
        part("DOOR_%s_StileA" % tag, (0.09, th, h - 0.06),
             (wx(0.045), y_face, zb + (h - 0.06) * 0.5), G.P("wood"))
        part("DOOR_%s_StileB" % tag, (0.09, th, h - 0.06),
             (wx(leaf_w - 0.045), y_face, zb + (h - 0.06) * 0.5), G.P("wood"))
        # 抹头：上 / 中（绦环）/ 下
        for zz, name in ((h - 0.10, "RailTop"), (1.16, "RailMid")):
            part("DOOR_%s_%s" % (tag, name), (leaf_w - 0.14, th, 0.085),
                 (cx, y_face, zb + zz), G.P("wood"))
        # 上段格心：3 竖 4 横 + 纸绢
        for i in range(3):
            part("DOOR_%s_LatV%d" % (tag, i), (0.020, th * 0.7, 1.02),
                 (wx(0.26 + i * (leaf_w - 0.52) / 2.0), y_face + 0.008,
                  zb + 1.70), G.P("wood_m"))
        for i in range(4):
            part("DOOR_%s_LatH%d" % (tag, i), (leaf_w - 0.26, th * 0.7, 0.020),
                 (cx, y_face + 0.008, zb + 1.32 + i * 0.26), G.P("wood_m"))
        part("DOOR_%s_PaperTop" % tag, (leaf_w - 0.24, 0.012, 1.00),
             (cx, y_face - 0.012, zb + 1.70), G.P("paper"))
        # 下段格心（避免整块裙板把门口挡成一块黑板）：3 竖 2 横
        for i in range(3):
            part("DOOR_%s_LowV%d" % (tag, i), (0.020, th * 0.7, 1.06),
                 (wx(0.26 + i * (leaf_w - 0.52) / 2.0), y_face + 0.008,
                  zb + 0.59), G.P("wood_m"))
        for i in range(2):
            part("DOOR_%s_LowH%d" % (tag, i), (leaf_w - 0.26, th * 0.7, 0.020),
                 (cx, y_face + 0.008, zb + 0.34 + i * 0.38), G.P("wood_m"))
        part("DOOR_%s_PaperLow" % tag, (leaf_w - 0.24, 0.012, 1.06),
             (cx, y_face - 0.012, zb + 0.59), G.P("paper"))
        # 背面木衬板 + 两道穿带：门开着时背面是木作，不是一块白板
        part("DOOR_%s_Back" % tag, (leaf_w - 0.20, 0.014, h - 0.22),
             (cx, y_face - 0.032, zb + (h - 0.22) * 0.5 + 0.03), G.P("wood"))
        for i in range(2):
            part("DOOR_%s_BackStrap%d" % (tag, i), (leaf_w - 0.26, 0.020, 0.07),
                 (cx, y_face - 0.048, zb + 0.62 + i * 0.98), G.P("wood_m"))
        # 中绦环：一道细金线
        part("DOOR_%s_Band%d" % (tag, 1), (leaf_w - 0.18, 0.014, 0.030),
             (cx, y_face + 0.046, zb + 1.16), G.P("gold"))
        # 铜门环
        part("DOOR_%s_RingPlate" % tag, (0.14, 0.02, 0.14),
             (wx(leaf_w - 0.10), y_face + 0.05, zb + 1.30), G.P("gold"))
        bpy.ops.mesh.primitive_torus_add(
            major_radius=0.072, minor_radius=0.014,
            major_segments=16, minor_segments=6,
            location=(wx(leaf_w - 0.10), y_face + 0.075, zb + 1.23),
            rotation=(math.pi * 0.5, 0.0, 0.0))
        torus = bpy.context.object
        torus.name = "DOOR_%s_Ring" % tag
        torus.data.materials.append(G.P("gold"))
        G._move_to(torus, col)
        torus.parent = hinge
        torus.matrix_parent_inverse = Matrix.Translation(-Vector(hinge.location))
        obs.append(torus)
    return obs


def build_plaque(col):
    """馆名匾额: black lacquer board under the balcony, real 3D 汉字 纹脉展馆."""
    obs = []
    fy = _front_y()
    py = fy + G.VER_W + 0.04
    z = G.F2 - 0.30
    obs.append(G.add_box("PLAQUE_Board", (3.30, 0.14, 0.58),
                         (0, py, z), col, G.P("ink")))
    for sign in (-1, 1):
        obs.append(G.add_box("PLAQUE_FrameH%d" % sign, (3.48, 0.09, 0.07),
                             (0, py + 0.05, z + sign * 0.33), col, G.P("gold")))
        obs.append(G.add_box("PLAQUE_FrameV%d" % sign, (0.07, 0.09, 0.70),
                             (sign * 1.70, py + 0.05, z), col, G.P("gold")))
    txt = G.text_mesh("PLAQUE_Text", "纹脉展馆", 0.33,
                      (0, py + 0.10, z), col, G.P("gold"),
                      font_path=G.cjk_font(), extrude=0.016,
                      rot=(math.radians(90), 0, math.radians(180)))
    obs.append(txt)
    return obs


# ------------------------------------------------------------------ posts
def build_posts(col):
    """墙身木柱（一层与二层）。

    所有柱子一律「落地到楼面、柱头顶到梁/窗楣」，不再用 F2-F1-0.30 这类
    估算高度：之前一层柱 0.50..3.55、二层柱 3.80..6.55，柱脚都悬在楼面上方
    0.2~0.25 m，从外面看就是一排没有落地的木柱。
    """
    obs = []
    hw, hd = G.BW * 0.5, G.BD * 0.5
    fy, by = _front_y(), _back_y()
    f1_bottom = G.F1                 # 一层楼面
    f1_top = G.F2                    # 一层柱顶 = 二层楼面标高
    f2_bottom = G.F2                 # 二层柱脚 = 二层楼面
    f2_top = G.TOP                   # 二层柱顶 = 窗楣
    xs = (-hw + 0.20, -F1_BAY_U - F1_BAY_W * 0.5 - 0.10,
          F1_BAY_U + F1_BAY_W * 0.5 + 0.10, hw - 0.20)
    for x in xs:
        for sy in (-1, 1):
            yy = (fy - WALL_T * 0.5) if sy > 0 else (by + WALL_T * 0.5)
            obs.append(G.add_box("POST_F1_%d_%d" % (int(x * 100), sy),
                                 (0.28, 0.34, f1_top - f1_bottom),
                                 (x, yy, (f1_bottom + f1_top) * 0.5), col,
                                 G.P("wood")))
    for x in (-hw + 0.22, hw - 0.22):
        for sy in (-1, 1):
            obs.append(G.add_box("POST_F1S_%d_%d" % (int(x * 100), sy),
                                 (0.30, 0.34, f1_top - f1_bottom),
                                 (x, G.BCY + sy * (hd - 0.10),
                                  (f1_bottom + f1_top) * 0.5), col,
                                 G.P("wood")))
    hw2 = hw - INSET
    for x in (-hw2 + 0.18, -1.50, 1.50, hw2 - 0.18):
        for sy in (-1, 1):
            yy = (G.BCY + (hd - INSET)) if sy > 0 else (G.BCY - (hd - INSET))
            obs.append(G.add_box("POST_F2_%d_%d" % (int(x * 100), sy),
                                 (0.24, 0.30, f2_top - f2_bottom),
                                 (x, yy, (f2_bottom + f2_top) * 0.5), col,
                                 G.P("wood")))
    for sx in (-1, 1):
        for sy in (-1, 1):
            obs.append(G.add_box("POST_C_%d%d" % (sx, sy),
                                 (0.30, 0.30, f1_top - f1_bottom),
                                 (sx * (hw - 0.15), G.BCY + sy * (hd - 0.15),
                                  (f1_bottom + f1_top) * 0.5), col,
                                 G.P("wood")))
    return obs


# ------------------------------------------------------------------ balcony
def build_veranda(col):
    obs = []
    hw, hd = G.BW * 0.5, G.BD * 0.5
    proj = G.VER_W
    xs = (-hw - proj + 0.18, -1.55, 1.55, hw + proj - 0.18)
    # 廊柱必须落地：柱脚落在台面上的石柱础，柱头抵住檐下额枋底面。
    # 旧版 z 从 F1-0.86 起、到 F2-0.86 止，上下各悬空约 0.4 m，是「柱子没落地」的根因。
    base_z = G.BASE_TOP                 # 台面 0.25
    plinth_h = 0.10                     # 柱础高
    beam_bottom = G.F2 - 0.32 - 0.11   # 额枋(z F2-0.32, 高 0.22)的底面 = 3.17
    col_z0 = base_z + plinth_h
    col_h = beam_bottom - col_z0
    for x in xs:
        for sy in (-1, 1):
            yy = G.BCY + sy * (hd + proj - 0.18)
            obs.append(G.add_box("VER_Plinth_%d_%d" % (int(x * 100), sy),
                                 (0.36, 0.36, plinth_h),
                                 (x, yy, base_z + plinth_h * 0.5), col,
                                 G.P("stone")))
            obs.append(G.add_box("VER_Col_%d_%d" % (int(x * 100), sy),
                                 (0.24, 0.24, col_h),
                                 (x, yy, col_z0 + col_h * 0.5), col, G.P("wood")))
    for sx in (-1, 1):
        for sy in (-1, 1):
            obs.append(G.add_box("VER_PlinthC_%d%d" % (sx, sy),
                                 (0.36, 0.36, plinth_h),
                                 (sx * (hw + proj - 0.18),
                                  G.BCY + sy * (hd + proj - 0.18),
                                  base_z + plinth_h * 0.5), col, G.P("stone")))
            obs.append(G.add_box("VER_ColC_%d%d" % (sx, sy),
                                 (0.24, 0.24, col_h),
                                 (sx * (hw + proj - 0.18),
                                  G.BCY + sy * (hd + proj - 0.18),
                                  col_z0 + col_h * 0.5), col, G.P("wood")))
    obs.append(G.add_box("VER_Slab", (G.BW + proj * 2, G.BD + proj * 2, 0.16),
                         (0, G.BCY, G.F2 - 0.08), col, G.P("wood_m")))
    for sy in (-1, 1):
        obs.append(G.add_box("VER_FasciaF%d" % sy, (G.BW + proj * 2, 0.07, 0.11),
                             (0, G.BCY + sy * (hd + proj), G.F2 - 0.20), col,
                             G.P("wood")))
        obs.append(G.add_box("VER_Beam%d" % sy, (G.BW + proj * 2, 0.18, 0.22),
                             (0, G.BCY + sy * (hd + proj - 0.18), G.F2 - 0.32),
                             col, G.P("wood_m")))
    for sx in (-1, 1):
        obs.append(G.add_box("VER_FasciaS%d" % sx, (0.07, G.BD + proj * 2, 0.11),
                             (sx * (hw + proj), G.BCY, G.F2 - 0.20), col,
                             G.P("wood")))
    return obs


def build_balcony_rail(col):
    obs = []
    hw = G.BW * 0.5 - INSET
    hd = G.BD * 0.5 - INSET
    proj = 0.62
    z0 = G.F2            # 栏杆柱脚直接落在二层楼板上（原来留了 0.04 的缝）
    h = 1.02

    def run(x0, y0, x1, y1, tag):
        length = math.hypot(x1 - x0, y1 - y0)
        n = max(2, int(round(length / 0.40)))
        for i in range(n + 1):
            t = i / n
            obs.append(G.add_box("RAIL2_Post_%s_%d" % (tag, i),
                                 (0.075, 0.075, h),
                                 (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t,
                                  z0 + h * 0.5), col, G.P("wood")))
        ang = math.atan2(y1 - y0, x1 - x0)
        cx, cy = (x0 + x1) * 0.5, (y0 + y1) * 0.5
        obs.append(G.add_box("RAIL2_Top_%s" % tag, (length, 0.085, 0.075),
                             (cx, cy, z0 + h - 0.04), col, G.P("wood_m"),
                             rot_z=ang))
        obs.append(G.add_box("RAIL2_Mid_%s" % tag, (length, 0.045, 0.045),
                             (cx, cy, z0 + 0.40), col, G.P("wood_l"), rot_z=ang))
        obs.append(G.add_box("RAIL2_Bot_%s" % tag, (length, 0.065, 0.065),
                             (cx, cy, z0 + 0.09), col, G.P("wood_m"), rot_z=ang))

    py = hd + proj
    run(-hw, G.BCY + py, hw, G.BCY + py, "F")
    run(-hw, G.BCY - py, hw, G.BCY - py, "B")
    run(-hw, G.BCY - py, -hw, G.BCY + py, "L")
    run(hw, G.BCY - py, hw, G.BCY + py, "R")
    return obs


# ------------------------------------------------------------------ lanterns
def lantern(name, x, y, z, col, scale=1.0, anchor=None):
    """宫灯：灯身 + 吊杆 + 吊环。

    `anchor` 是吊点标高（上方梁/楼板底面）。旧版只画一根短杆，杆顶停在半空，
    所以从任何角度看灯笼都是悬着的；现在吊杆一直画到吊点，并在吊点加一个
    吊环，灯笼才真正「挂」在建筑上。
    """
    obs = []
    if anchor is not None and anchor > z:
        h = anchor - z
        obs.append(G.add_cyl(name + "_Rod", 0.030, h, (x, y, z + h * 0.5),
                             col, G.P("wood"), segments=6))
        # 吊点铁件：一块小垫板 + 吊环，让吊杆末端有落点
        obs.append(G.add_box(name + "_Plate", (0.16, 0.16, 0.035),
                             (x, y, anchor - 0.018), col, G.P("wood_m")))
        obs.append(G.add_cyl(name + "_Ring", 0.05, 0.05, (x, y, anchor - 0.055),
                             col, G.P("gold"), segments=10))
    body = G.add_sphere(name + "_Body", 0.19 * scale, (x, y, z), col,
                        G.E("lantern", (1.0, 0.30, 0.11), 2.2),
                        segments=16, rings=12)
    body.scale = (1.0, 1.0, 1.20)
    obs.append(body)
    obs.append(G.add_cyl(name + "_CapT", 0.11 * scale, 0.045,
                         (x, y, z + 0.205 * scale), col, G.P("gold"), segments=12))
    obs.append(G.add_cyl(name + "_CapB", 0.11 * scale, 0.045,
                         (x, y, z - 0.205 * scale), col, G.P("gold"), segments=12))
    obs.append(G.add_cone(name + "_Tassel", 0.05, 0.012, 0.28,
                          (x, y, z - 0.34 * scale), col, G.P("red"),
                          segments=6, rot=(math.pi, 0, 0)))
    return obs


def build_lanterns(col):
    obs = []
    hw, hd = G.BW * 0.5, G.BD * 0.5
    fy = _front_y()
    # 吊点：一层檐下吊在二层楼板底面（3.44），檐下宫灯吊在撩檐枋底面（7.50）
    deck_bottom = G.F2 - 0.16
    eave_beam_bottom = G.ROOF_MAIN_EAVE - 0.34   # 撩檐枋底面（枋 z 7.61..7.78）
    for sign in (-1, 1):
        x = sign * 2.42
        y = fy + 0.62
        # 门头两盏：从墙面挑出一段挑臂，灯笼吊在挑臂端头
        obs.append(G.add_box("LANTERN_F%d_Arm" % sign, (0.07, 0.70, 0.07),
                             (x, (fy + y) * 0.5, deck_bottom - 0.05), col,
                             G.P("wood_m")))
        obs.extend(lantern("LANTERN_F%d" % sign, x, y, G.F1 + 2.10, col,
                           scale=1.12, anchor=deck_bottom))
    for i, x in enumerate((-3.60, 3.60)):
        # 二楼外沿只留两盏，落在 ±1.55 / ±5.37 两根廊柱之间的空当里；
        # ±1.55 位置的旧灯笼正对匾额、太密，已删除。
        y_out = G.BCY + hd + G.VER_W - 0.10
        arm_z = deck_bottom - 0.06
        obs.append(G.add_box("LANTERN_B%d_Arm" % i,
                             (0.07, G.VER_W + 0.10, 0.07),
                             (x, G.BCY + hd + G.VER_W * 0.5 - 0.05, arm_z),
                             col, G.P("wood_m")))
        obs.extend(lantern("LANTERN_B%d" % i, x, y_out, G.F2 - 0.62, col,
                           scale=0.82, anchor=arm_z + 0.02))
    # 后立面同样对称挂两盏（同一高度、同一挑臂做法）
    for i, x in enumerate((-3.60, 3.60)):
        y_out = G.BCY - hd - (G.VER_W - 0.10)
        arm_z = deck_bottom - 0.06
        obs.append(G.add_box("LANTERN_BK%d_Arm" % i,
                             (0.07, G.VER_W + 0.10, 0.07),
                             (x, G.BCY - hd - G.VER_W * 0.5 + 0.05, arm_z),
                             col, G.P("wood_m")))
        obs.extend(lantern("LANTERN_BK%d" % i, x, y_out, G.F2 - 0.62, col,
                           scale=0.82, anchor=arm_z + 0.02))
    for sx in (-1, 1):
        for sy in (-1, 1):
            obs.extend(lantern("LANTERN_E_%d%d" % (sx, sy),
                               sx * (G.ROOF_W * 0.5 - 1.15),
                               G.BCY + sy * (G.ROOF_D * 0.5 - 0.55),
                               G.ROOF_MAIN_EAVE - 1.00, col, scale=0.92,
                               anchor=eave_beam_bottom))
    return obs


# ------------------------------------------------------------------ trims
def wainscot(col, z0, z1, sides=("F", "B", "L", "R"), proud=0.045):
    """Wood wainscot band on the outer wall faces.

    The plaster walls were the largest single blank area on the model, which is
    what made the hall read as a plain box from every angle. A dark timber
    skirt under the windows gives the wall a base, a colour break and a shadow
    line, and it is exactly what the reference elevations show.
    """
    obs = []
    hw, hd = G.BW * 0.5, G.BD * 0.5
    fy, by = _front_y(), _back_y()
    h = z1 - z0
    zc = z0 + h * 0.5
    if "F" in sides:
        # 正立面腰线在门口断开：原来一整条 8.4 m 的护墙板横穿门洞，
        # 把门的下半截挡成一堵木墙（用户说的「挡着门的木槛」）。
        gap = 1.72
        for sgn in (-1, 1):
            x0 = -hw if sgn < 0 else gap
            x1 = -gap if sgn < 0 else hw
            obs.append(G.add_box("TRIM_WainF%d" % sgn, (x1 - x0, proud, h),
                                 ((x0 + x1) * 0.5, fy + proud * 0.5, zc),
                                 col, G.P("wood_m")))
            obs.append(G.add_box("TRIM_WainF_Cap%d" % sgn,
                                 (x1 - x0 + 0.06, proud + 0.05, 0.06),
                                 ((x0 + x1) * 0.5, fy + proud * 0.5, z1 + 0.03),
                                 col, G.P("wood")))
    if "B" in sides:
        obs.append(G.add_box("TRIM_WainB", (G.BW, proud, h), (0, by - proud * 0.5, zc),
                             col, G.P("wood_m")))
        obs.append(G.add_box("TRIM_WainB_Cap", (G.BW + 0.06, proud + 0.05, 0.06),
                             (0, by - proud * 0.5, z1 + 0.03), col, G.P("wood")))
    if "L" in sides:
        obs.append(G.add_box("TRIM_WainL", (proud, G.BD, h), (-hw - proud * 0.5, G.BCY, zc),
                             col, G.P("wood_m")))
        obs.append(G.add_box("TRIM_WainL_Cap", (proud + 0.05, G.BD + 0.06, 0.06),
                             (-hw - proud * 0.5, G.BCY, z1 + 0.03), col, G.P("wood")))
    if "R" in sides:
        obs.append(G.add_box("TRIM_WainR", (proud, G.BD, h), (hw + proud * 0.5, G.BCY, zc),
                             col, G.P("wood_m")))
        obs.append(G.add_box("TRIM_WainR_Cap", (proud + 0.05, G.BD + 0.06, 0.06),
                             (hw + proud * 0.5, G.BCY, z1 + 0.03), col, G.P("wood")))
    return obs


# ------------------------------------------------------------------ canopy
def build_side_canopy(col):
    """Tiled pent canopy on the right (+X) wall, with a fabric valance.

    Reference sheet 03 shows the right elevation carrying a small tiled eave
    over the corner window plus a pale canvas awning. The V5 shell had only a
    bare wall there, which is why the street corner read as "four identical
    sides". Everything here hangs below the storey band (2.55-3.10 m) so it can
    never collide with the skirt roof.
    """
    obs = []
    hw, hd = G.BW * 0.5, G.BD * 0.5
    x_in = hw + 0.02
    x_out = hw + 1.06
    z_in, z_out = 3.06, 2.56
    y0, y1 = G.BCY - 2.65, G.BCY + 2.05
    # sloped slab
    verts = [(x_in, y0, z_in), (x_in, y1, z_in), (x_out, y1, z_out), (x_out, y0, z_out),
             (x_in, y0, z_in - 0.09), (x_in, y1, z_in - 0.09),
             (x_out, y1, z_out - 0.09), (x_out, y0, z_out - 0.09)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
             (2, 3, 7, 6), (3, 0, 4, 7)]
    obs.append(G.add_mesh("CANOPY_Slab", verts, faces, col, G.P("tile_d")))
    # half-round tile courses running down the slope
    n = int((y1 - y0) / 0.30)
    ang = math.atan2(z_in - z_out, x_out - x_in)
    length = math.hypot(x_out - x_in, z_in - z_out)
    for i in range(n + 1):
        y = y0 + (i + 0.5) * (y1 - y0) / (n + 1)
        cx = (x_in + x_out) * 0.5
        cz = (z_in + z_out) * 0.5 + 0.03
        obs.append(G.add_cyl("CANOPY_Tile%d" % i, 0.045, length, (cx, y, cz), col,
                             G.P("tile"), segments=8, rot=(0, math.pi * 0.5 - ang, 0)))
    # outer fascia + drip edge
    obs.append(G.add_box("CANOPY_Fascia", (0.09, y1 - y0, 0.16),
                         (x_out + 0.02, (y0 + y1) * 0.5, z_out - 0.06), col, G.P("wood_m")))
    # brackets on the wall
    for i in range(4):
        y = y0 + 0.35 + i * (y1 - y0 - 0.7) / 3.0
        obs.append(G.add_box("CANOPY_Bracket%d" % i, (0.48, 0.09, 0.11),
                             (x_in + 0.24, y, z_in - 0.20), col, G.P("wood")))
    # fabric valance under the outer edge (the pale awning of reference 03)
    for i in range(10):
        y = y0 + 0.14 + i * (y1 - y0 - 0.28) / 9.0
        obs.append(G.add_box("CANOPY_Valance%d" % i, (0.03, 0.20, 0.34),
                             (x_out + 0.05, y, z_out - 0.30), col, G.P("paper")))
    obs.append(G.add_box("CANOPY_ValRail", (0.05, y1 - y0, 0.05),
                         (x_out + 0.05, (y0 + y1) * 0.5, z_out - 0.13), col, G.P("wood_m")))
    return obs


def build_trims(col):
    """Wainscot on both storeys + a thin string course above the ground floor."""
    obs = []
    # ground floor: from the stone plinth up to just under the window sills
    obs.extend(wainscot(col, G.F1 + 0.42, G.F1 + 0.96))
    # upper storey: back and both sides (the front is the balcony sill wall)
    obs.extend(wainscot(col, G.F2 + 0.44, G.F2 + 0.96, sides=("B", "L", "R")))
    # string course: catches light along the whole length of the wall
    hw, hd = G.BW * 0.5, G.BD * 0.5
    for sign in (-1, 1):
        obs.append(G.add_box("TRIM_StringF%d" % sign, (G.BW + 0.10, 0.06, 0.075),
                             (0, G.BCY + sign * (hd + 0.03), G.F2 - 0.34), col,
                             G.P("wood_l")))
        obs.append(G.add_box("TRIM_StringS%d" % sign, (0.06, G.BD + 0.10, 0.075),
                             (sign * (hw + 0.03), G.BCY, G.F2 - 0.34), col,
                             G.P("wood_l")))
    return obs


def build(col):
    obs = []
    obs.extend(build_walls(col))
    obs.extend(build_posts(col))
    obs.extend(build_entrance_porch(col))
    obs.extend(build_door(col))
    obs.extend(build_plaque(col))
    obs.extend(build_facade(col))
    obs.extend(build_veranda(col))
    obs.extend(build_balcony_rail(col))
    obs.extend(build_lanterns(col))
    obs.extend(build_side_canopy(col))
    obs.extend(build_trims(col))
    G.log("shell objects: %d" % len(obs))
    return obs
