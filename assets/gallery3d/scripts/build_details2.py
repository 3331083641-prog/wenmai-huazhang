"""Signature details: the carved name plaque with real glyphs, door furniture,
interior sconces.

The plaque is the one place where the model carries actual Chinese characters.
They are converted to mesh from a system font, so the web build needs no font
file and the glyphs cannot degrade into a colour block.
"""
from __future__ import annotations

import math
import os
import sys

import bmesh
import bpy

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gal_common import (  # noqa: E402
    BUILD_DEPTH, BUILD_X, BUILD_Y, F1_H, F2_H, Z_F1, Z_F2, Z_TOP, box, cyl,
    join_objects, material, prism, report,
)

HY = BUILD_DEPTH / 2.0


def text_mesh(name, body, size, location, rot, mat_key, font_path,
              extrude=0.014, spacing=1.0):
    """Create a real mesh from a system font (converted, never a texture)."""
    curve = bpy.data.curves.new(name, type="FONT")
    curve.body = body
    curve.font = bpy.data.fonts.load(font_path, check_existing=True)
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = size
    curve.space_character = spacing
    curve.extrude = extrude
    curve.resolution_u = 3
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.view_layer.objects.active
    obj.rotation_euler = rot
    obj.location = location
    obj.data.materials.append(material(mat_key))
    for coll in list(obj.users_collection):
        coll.objects.unlink(obj)
    return obj


def build_plaque(col):
    """3.0 m plaque above the door: vermilion lacquered board, gold border and glyphs.

    The board is sized so the four glyphs sit inside the recessed field with a
    margin; the earlier version had the text wider than the field, which is why
    the inscription read as a black smear.
    """
    parts = []
    y = HY - 0.02
    # Brief: plaque about 2.6 m wide x 0.65 m tall. Scaled down uniformly from the
    # earlier 3.10 x 0.76 (same 4.55 aspect, so the baked glyphs do not stretch).
    parts.append(box("PROP_Plaque_Board", col, (2.52, 0.13, 0.55),
                     (0, y + 0.07, 2.95), "timber_dark", chamfer=0.012))
    parts.append(box("PROP_Plaque_Border", col, (2.60, 0.05, 0.64),
                     (0, y + 0.13, 2.95), "gold_light", chamfer=0.01))
    parts.append(box("PROP_Plaque_Field", col, (2.38, 0.03, 0.42),
                     (0, y + 0.155, 2.95), "red_deep"))
    for sx in (-1, 1):
        parts.append(box("PROP_Plaque_Bracket%d" % sx, col, (0.10, 0.16, 0.18),
                         (sx * 1.16, y + 0.04, 3.28), "gold_light", chamfer=0.008))
    board = join_objects(parts, "PROP_Plaque")

    font = r"C:\Windows\Fonts\STKAITI.TTF"
    if not os.path.exists(font):
        font = r"C:\Windows\Fonts\simhei.ttf"
    # face +Y, upright: Rx(90) then Rz(180)
    txt = text_mesh("PROP_Plaque_Text", "\u7eb9\u8109\u5c55\u9986", 0.386,
                    (0, y + 0.175, 2.95),
                    (math.pi / 2.0, 0.0, math.pi), "gold_light", font,
                    extrude=0.012, spacing=1.12)
    report("plaque text: %d verts" % len(txt.data.vertices))
    return [board, txt]


def build_door_furniture(col):
    """Pair of drum stones beside the entrance steps."""
    parts = []
    for sx in (-1, 1):
        x = sx * 1.42
        parts.append(box("PROP_Drum%d_Base" % sx, col, (0.34, 0.44, 0.20),
                         (x, HY + 0.20, Z_F1 + 0.10), "stone_dark",
                         chamfer=0.012))
        parts.append(cyl("PROP_Drum%d_Drum" % sx, col, 0.19, 0.16,
                         (x, HY + 0.22, Z_F1 + 0.40), "stone_warm",
                         segments=14, rot_x=math.pi / 2.0))
        parts.append(cyl("PROP_Drum%d_Hub" % sx, col, 0.075, 0.18,
                         (x, HY + 0.23, Z_F1 + 0.40), "stone_dark",
                         segments=10, rot_x=math.pi / 2.0))
        parts.append(box("PROP_Drum%d_Top" % sx, col, (0.30, 0.20, 0.10),
                         (x, HY + 0.16, Z_F1 + 0.58), "stone_warm",
                         chamfer=0.01))
    return join_objects(parts, "PROP_DrumStones")


def build_sconces(col):
    """Two warm wall sconces inside, so the ground floor never goes flat."""
    parts = []
    for i, (x, y) in enumerate(((-4.00, 1.60), (4.00, 1.60))):
        sx = -1 if x < 0 else 1
        parts.append(box("PROP_Sconce%d_Arm" % i, col, (0.22, 0.05, 0.05),
                         (x + sx * 0.10, y, Z_F1 + 2.35), "timber_dark"))
        parts.append(cyl("PROP_Sconce%d_Shade" % i, col, 0.12, 0.18,
                         (x + sx * 0.20, y, Z_F1 + 2.26), "lamp_glow",
                         segments=10))
        parts.append(cyl("PROP_Sconce%d_Ring" % i, col, 0.14, 0.03,
                         (x + sx * 0.20, y, Z_F1 + 2.36), "gold", segments=10))
    return join_objects(parts, "PROP_Sconces")


def build_left_elevation(col):
    """Left (-X) elevation treatment.

    The +X side carries the covered veranda, so the -X elevation used to be a
    blank mirrored copy of it — the four orthographic views then looked almost
    identical. A 砖雕盲窗 (blind brick-carved lattice window) with its own little
    hood, plus a stone bench and an inscribed stele at eye level, gives the left
    side its own rhythm without opening the wall (the interior frames behind it
    stay valid).
    """
    parts = []
    wx = -(BUILD_X / 2.0)          # -4.20 outer wall face
    cy = 0.55                      # window centre along Y
    cz = 4.95                      # window centre height (upper storey)
    half_w, half_h = 0.65, 0.775

    # recessed backing panel, sits inside the wall thickness
    parts.append(box("LFX_Panel", col, (0.06, 1.30, 1.55),
                     (wx + 0.015, cy, cz), "stone"))

    # stone frame, protruding 0.06 from the wall plane
    for i, dz in enumerate((half_h + 0.07, -(half_h + 0.07))):
        parts.append(box("LFX_FrameH%d" % i, col, (0.12, 1.44, 0.14),
                         (wx - 0.03, cy, cz + dz), "stone_warm"))
    for i, dy in enumerate((half_w + 0.07, -(half_w + 0.07))):
        parts.append(box("LFX_FrameV%d" % i, col, (0.12, 0.14, 1.55),
                         (wx - 0.03, cy + dy, cz), "stone_warm"))

    # lattice: 3 vertical + 2 horizontal bars, recessed inside the frame
    for i, dy in enumerate((-0.325, 0.0, 0.325)):
        parts.append(box("LFX_Bar%d" % i, col, (0.06, 0.05, 1.53),
                         (wx - 0.055, cy + dy, cz), "timber_dark"))
    for i, dz in enumerate((-0.36, 0.36)):
        parts.append(box("LFX_Rail%d" % i, col, (0.06, 1.28, 0.05),
                         (wx - 0.055, cy, cz + dz), "timber_dark"))

    # sill
    parts.append(box("LFX_Sill", col, (0.20, 1.62, 0.12),
                     (wx - 0.08, cy, cz - half_h - 0.16), "stone_warm"))

    # small tiled hood over the window (extruded along Y)
    parts.append(prism("LFX_Hood", col,
                       [(-4.19, cz + half_h + 0.20), (-4.66, cz + half_h - 0.14),
                        (-4.66, cz + half_h - 0.26), (-4.19, cz + half_h + 0.08)],
                       1.80, (0.0, cy - 0.90, 0.0), "roof_tile", axis="y"))
    parts.append(box("LFX_HoodRail", col, (0.50, 1.84, 0.06),
                     (-4.42, cy, cz + half_h - 0.13), "timber_dark"))

    # stone bench on the plinth
    parts.append(box("LFX_BenchTop", col, (0.40, 1.50, 0.12),
                     (wx - 0.22, cy, 0.46), "stone_warm"))
    for i, dy in enumerate((0.55, -0.55)):
        parts.append(box("LFX_BenchLeg%d" % i, col, (0.34, 0.16, 0.40),
                         (wx - 0.22, cy + dy, 0.20), "stone"))

    # inscribed stele
    parts.append(box("LFX_SteleBase", col, (0.28, 0.72, 0.16),
                     (wx - 0.10, -0.85, 0.08), "stone"))
    parts.append(box("LFX_Stele", col, (0.14, 0.56, 0.86),
                     (wx - 0.14, -0.85, 0.63), "stone_warm"))
    parts.append(box("LFX_SteleCap", col, (0.20, 0.64, 0.10),
                     (wx - 0.14, -0.85, 1.10), "stone"))

    return join_objects(parts, "PROP_LeftFacade")


def build(col):
    objs = []
    objs += build_plaque(col)
    objs.append(build_door_furniture(col))
    objs.append(build_sconces(col))
    objs.append(build_left_elevation(col))
    report("details2 built")
    return objs