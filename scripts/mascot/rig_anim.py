"""Armature + the 8 mascot actions for 「纹纹」.

Kept separate from build_mascot.py so the mesh code stays readable.
The rig and animation helpers are imported by build_mascot.build_final.
"""
import math

import bpy
from mathutils import Matrix, Vector

from mlib import TAU

# eye centre / proportions must match build_mascot
EYE_C = Vector((0.084, 0.163, 0.768))
EAR_TIP_Z = 1.000
LEG_X, LEG_FRONT_Y, LEG_BACK_Y = 0.088, 0.060, -0.056


def build_rig(body_ob, gear_ob, tail_pts):
    sc = bpy.context.scene
    arm_data = bpy.data.armatures.new("WWArmature")
    arm = bpy.data.objects.new("WWArmature", arm_data)
    sc.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    def bone(name, head, tail, parent=None, connect=False):
        b = arm_data.edit_bones.new(name)
        b.head = Vector(head)
        b.tail = Vector(tail)
        b.roll = 0.0
        if parent:
            b.parent = arm_data.edit_bones[parent]
            b.use_connect = connect
        return b

    bone("root", (0, 0, 0.0), (0, 0, 0.10))
    bone("hips", (0, 0, 0.300), (0, 0, 0.400), "root")
    bone("spine", (0, 0, 0.400), (0, 0, 0.480), "hips", True)
    bone("chest", (0, 0, 0.480), (0, 0, 0.575), "spine", True)
    bone("neck", (0, 0, 0.575), (0, 0.008, 0.618), "chest", True)
    bone("head", (0, 0.008, 0.618), (0, 0.012, 0.800), "neck", True)

    for sgn, side in ((-1, "L"), (1, "R")):
        bone(f"ear.{side}", (sgn * 0.095, 0.026, 0.845),
             (sgn * 0.206, 0.012, EAR_TIP_Z), "head")
        # lid bones point straight UP out of the eye, so rotating about their
        # local X sweeps the cap down over the eyeball
        bone(f"lid.{side}", (sgn * EYE_C.x, EYE_C.y, EYE_C.z),
             (sgn * EYE_C.x, EYE_C.y, EYE_C.z + 0.060), "head")

    idx = [0, 6, 12, 18, 24, len(tail_pts) - 1]
    for k in range(5):
        parent = "hips" if k == 0 else f"tail.{k:02d}"
        bone(f"tail.{k + 1:02d}", tail_pts[idx[k]], tail_pts[idx[k + 1]],
             parent, connect=(k > 0))

    for sgn, side in ((-1, "L"), (1, "R")):
        for tag, y, x in (("front", LEG_FRONT_Y, LEG_X),
                          ("back", LEG_BACK_Y, LEG_X + 0.012)):
            bone(f"{tag}_upper.{side}", (sgn * x, y, 0.232),
                 (sgn * x, y + 0.004, 0.150), "hips")
            bone(f"{tag}_lower.{side}", (sgn * x, y + 0.004, 0.150),
                 (sgn * x, y + 0.010, 0.058), f"{tag}_upper.{side}", True)
            bone(f"{tag}_paw.{side}", (sgn * x, y + 0.010, 0.058),
                 (sgn * x, y + 0.070, 0.030), f"{tag}_lower.{side}", True)

    bpy.ops.object.mode_set(mode="OBJECT")

    for ob in (body_ob, gear_ob):
        ob.parent = arm
        ob.matrix_parent_inverse = Matrix.Identity(4)
        md = ob.modifiers.new("Armature", "ARMATURE")
        md.object = arm
        md.use_vertex_groups = True

    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    return arm


# ------------------------------------------------------------------ helpers --
def clear_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_euler = (0.0, 0.0, 0.0)
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)


def apply_pose(arm, pose):
    for name, vals in pose.items():
        pb = arm.pose.bones.get(name)
        if pb is None:
            continue
        if "rot" in vals:
            pb.rotation_euler = tuple(math.radians(a) for a in vals["rot"])
        if "loc" in vals:
            pb.location = vals["loc"]
        if "scale" in vals:
            pb.scale = vals["scale"]


def make_action(arm, name, keys, end, loop=True):
    clear_pose(arm)
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = act
    slot = None
    try:
        if hasattr(act, "slots"):
            slot = (act.slots.new(id_type="OBJECT", name=arm.name)
                    if len(act.slots) == 0 else act.slots[0])
            arm.animation_data.action_slot = slot
    except Exception as exc:
        print("  slot note:", exc)

    used = sorted({b for _, pose in keys for b in pose})
    for frame, pose in keys:
        clear_pose(arm)
        apply_pose(arm, pose)
        for bname in used:
            pb = arm.pose.bones[bname]
            pb.keyframe_insert("rotation_euler", frame=frame)
            pb.keyframe_insert("location", frame=frame)
            pb.keyframe_insert("scale", frame=frame)
    act.frame_start = 0
    act.frame_end = end
    try:
        for fc in act.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
    except Exception:
        pass
    clear_pose(arm)
    n = -1
    try:
        n = len(act.fcurves)
    except Exception:
        pass
    if n <= 0 and hasattr(act, "layers"):
        n = 0
        for layer in act.layers:
            for strip in layer.strips:
                try:
                    n += len(strip.channelbag(slot).fcurves)
                except Exception:
                    pass
    print(f"[anim] {name}: 0..{end} ({end / 30.0:.2f}s) fcurves={n}")
    return act


def tail_wave(phase, amp=9.0, lift=0.0):
    """Secondary motion: every tail joint lags the one before it."""
    out = {}
    for k in range(5):
        out[f"tail.{k + 1:02d}"] = {
            "rot": [lift * (1.0 if k == 0 else 0.5), 0.0,
                    amp * math.sin(phase - k * 0.55)]}
    return out


def blink_keys(frame_at, closed=1.0, hold=3, span=3):
    """A quick close/open pair for the eyelid bones."""
    a = frame_at
    return [(a, {"lid.L": {"rot": [0, 0, 0]}, "lid.R": {"rot": [0, 0, 0]}}),
            (a + span, {"lid.L": {"rot": [82.0 * closed, 0, 0]},
                        "lid.R": {"rot": [82.0 * closed, 0, 0]}}),
            (a + span + hold, {"lid.L": {"rot": [82.0 * closed, 0, 0]},
                               "lid.R": {"rot": [82.0 * closed, 0, 0]}}),
            (a + span * 2 + hold, {"lid.L": {"rot": [0, 0, 0]},
                                   "lid.R": {"rot": [0, 0, 0]}})]


# ------------------------------------------------------------------ actions --
def build_actions(arm):
    make = lambda n, k, e: make_action(arm, n, sorted(k, key=lambda x: x[0]), e)

    # ---------------- 1. Idle: 4 s loop ---------------- #
    keys = []
    for f in range(0, 121, 5):
        t = f / 120.0
        ph = TAU * t
        br = 0.5 - 0.5 * math.cos(ph)
        pose = {
            "chest": {"scale": [1.0, 1.0, 1.0 + 0.020 * br]},
            "spine": {"rot": [-1.1 * br, 0, 0]},
            "head": {"rot": [0.9 * br, 0, 0.8 * math.sin(ph)]},
            "ear.L": {"rot": [0, 0, 3.0 * math.sin(ph + 0.4)]},
            "ear.R": {"rot": [0, 0, -3.0 * math.sin(ph + 0.7)]},
        }
        pose.update(tail_wave(ph, amp=10.0, lift=2.0))
        keys.append((f, pose))
    keys += blink_keys(70)
    for f, a in ((38, 0.0), (41, 11.0), (44, -5.0), (47, 0.0)):
        keys.append((f, {"ear.L": {"rot": [0, 0, a]}}))
    make("Idle", keys, 120)

    # ---------------- 2. Spawn: 1.2 s one shot ---------------- #
    drop = [
        (0, {"root": {"loc": [0, 0, -0.16]},
             "hips": {"scale": [1.06, 1.06, 0.88]},
             "front_upper.L": {"rot": [26, 0, 0]},
             "front_upper.R": {"rot": [26, 0, 0]},
             "back_upper.L": {"rot": [24, 0, 0]},
             "back_upper.R": {"rot": [24, 0, 0]},
             "head": {"rot": [-14, 0, 0]}}),
        (9, {"root": {"loc": [0, 0, 0.20]},
             "hips": {"scale": [0.94, 0.94, 1.12]},
             "front_upper.L": {"rot": [-30, 0, 0]},
             "front_upper.R": {"rot": [-30, 0, 0]},
             "back_upper.L": {"rot": [-26, 0, 0]},
             "back_upper.R": {"rot": [-26, 0, 0]},
             "head": {"rot": [10, 0, 0]},
             "ear.L": {"rot": [-12, 0, 0]},
             "ear.R": {"rot": [-12, 0, 0]}}),
        (19, {"root": {"loc": [0, 0, -0.07]},
              "hips": {"scale": [1.08, 1.08, 0.86]},
              "front_upper.L": {"rot": [20, 0, 0]},
              "front_upper.R": {"rot": [20, 0, 0]},
              "back_upper.L": {"rot": [18, 0, 0]},
              "back_upper.R": {"rot": [18, 0, 0]},
              "head": {"rot": [-8, 0, 0]}}),
        (27, {"root": {"loc": [0, 0, 0.02]},
              "hips": {"scale": [0.98, 0.98, 1.03]},
              "head": {"rot": [3, 0, 0]}}),
        (36, {}),
    ]
    keys = [(f, dict(p, **tail_wave(f * 0.28, amp=14.0))) for f, p in drop]
    make("Spawn", keys, 36)

    # ---------------- 3. Walk: 32 f loop ---------------- #
    keys = []
    for f in range(0, 33, 4):
        ph = TAU * f / 32.0
        swing = 26.0 * math.sin(ph)
        pose = {
            "root": {"loc": [0, 0, 0.012 * math.cos(2 * ph)]},
            "hips": {"rot": [0, 0, 3.0 * math.sin(ph)]},
            "spine": {"rot": [1.5, 0, 0]},
            "chest": {"rot": [0, 0, -2.0 * math.sin(ph)]},
            "head": {"rot": [-1.5 * math.cos(2 * ph), 0, 1.6 * math.sin(ph)]},
            "front_upper.L": {"rot": [swing, 0, 0]},
            "front_upper.R": {"rot": [-swing, 0, 0]},
            "back_upper.L": {"rot": [-swing * 0.9, 0, 0]},
            "back_upper.R": {"rot": [swing * 0.9, 0, 0]},
            "front_lower.L": {"rot": [max(0.0, -swing) * 0.5, 0, 0]},
            "front_lower.R": {"rot": [max(0.0, swing) * 0.5, 0, 0]},
            "back_lower.L": {"rot": [max(0.0, swing) * 0.5, 0, 0]},
            "back_lower.R": {"rot": [max(0.0, -swing) * 0.5, 0, 0]},
        }
        pose.update(tail_wave(ph + 0.8, amp=13.0, lift=4.0))
        keys.append((f, pose))
    make("Walk", keys, 32)

    # ---------------- 4. Run: 24 f loop ---------------- #
    keys = []
    for f in range(0, 25, 3):
        ph = TAU * f / 24.0
        swing = 44.0 * math.sin(ph)
        pose = {
            "root": {"loc": [0, 0, 0.030 * math.cos(2 * ph)]},
            "hips": {"rot": [0, 0, 5.0 * math.sin(ph)]},
            "spine": {"rot": [7.0, 0, 0]},
            "chest": {"rot": [4.0, 0, -3.0 * math.sin(ph)]},
            "head": {"rot": [-5.0, 0, 2.5 * math.sin(ph)]},
            "front_upper.L": {"rot": [swing + 8, 0, 0]},
            "front_upper.R": {"rot": [-swing + 8, 0, 0]},
            "back_upper.L": {"rot": [-swing * 1.05, 0, 0]},
            "back_upper.R": {"rot": [swing * 1.05, 0, 0]},
            "front_lower.L": {"rot": [max(0.0, -swing) * 0.8, 0, 0]},
            "front_lower.R": {"rot": [max(0.0, swing) * 0.8, 0, 0]},
            "back_lower.L": {"rot": [max(0.0, swing) * 0.8, 0, 0]},
            "back_lower.R": {"rot": [max(0.0, -swing) * 0.8, 0, 0]},
            "ear.L": {"rot": [-9, 0, 0]},
            "ear.R": {"rot": [-9, 0, 0]},
        }
        pose.update(tail_wave(ph + 0.6, amp=17.0, lift=16.0))
        keys.append((f, pose))
    make("Run", keys, 24)

    # ---------------- 5. Turn: 40 f full spin, loops ---------------- #
    keys = []
    for f in range(0, 41, 5):
        t = f / 40.0
        e = t * t * (3 - 2 * t)
        pose = {
            "root": {"rot": [0, 0, 360.0 * e]},
            "spine": {"rot": [2.0 * math.sin(TAU * t), 0, 0]},
            "chest": {"rot": [0, 0, -8.0 * math.sin(TAU * t)]},
            "head": {"rot": [0, 0, 14.0 * math.sin(TAU * t)]},
            "ear.L": {"rot": [0, 0, 6.0 * math.sin(TAU * t)]},
            "ear.R": {"rot": [0, 0, 6.0 * math.sin(TAU * t)]},
        }
        pose.update(tail_wave(TAU * t, amp=22.0, lift=6.0))
        keys.append((f, pose))
    make("Turn", keys, 40)

    # ---------------- 6. Happy: 45 f, two hops ---------------- #
    keys = []
    for f in range(0, 46, 3):
        t = f / 45.0
        hop = max(0.0, math.sin(TAU * t * 2.0))
        pose = {
            "root": {"loc": [0, 0, 0.085 * hop]},
            "hips": {"scale": [1.0 - 0.06 * hop, 1.0 - 0.06 * hop, 1.0 + 0.07 * hop]},
            "spine": {"rot": [-6.0 * hop, 0, 0]},
            "head": {"rot": [-7.0 * hop, 0, 9.0 * math.sin(TAU * t)]},
            "ear.L": {"rot": [-15.0 * hop, 0, 5.0 * math.sin(TAU * t)]},
            "ear.R": {"rot": [-15.0 * hop, 0, 5.0 * math.sin(TAU * t)]},
            "front_upper.L": {"rot": [-34.0 * hop, 0, 0]},
            "front_upper.R": {"rot": [-34.0 * hop, 0, 0]},
            "back_upper.L": {"rot": [22.0 * hop, 0, 0]},
            "back_upper.R": {"rot": [22.0 * hop, 0, 0]},
        }
        pose.update(tail_wave(TAU * t * 2.0, amp=20.0, lift=24.0))
        keys.append((f, pose))
    make("Happy", keys, 45)

    # ---------------- 7. Curious: 90 f loop ---------------- #
    keys = []
    for f in range(0, 91, 6):
        ph = TAU * f / 90.0
        tilt = 15.0 * math.sin(ph)
        pose = {
            "neck": {"rot": [2.0, 0, tilt * 0.35]},
            "head": {"rot": [-4.0 + 3.0 * math.cos(ph), 0, tilt]},
            "ear.L": {"rot": [-10.0, 0, 4.0 * math.sin(ph + 0.3)]},
            "ear.R": {"rot": [-10.0, 0, 4.0 * math.sin(ph + 0.3)]},
            "spine": {"rot": [1.5 * math.cos(ph), 0, 0]},
            "chest": {"scale": [1.0, 1.0,
                                1.0 + 0.012 * (0.5 - 0.5 * math.cos(ph))]},
        }
        pose.update(tail_wave(ph, amp=8.0, lift=5.0))
        keys.append((f, pose))
    keys += blink_keys(42)
    make("Curious", keys, 90)

    # ---------------- 8. Interact: 60 f one shot ---------------- #
    keys = []
    for f in range(0, 61, 4):
        t = f / 60.0
        k = math.sin(math.pi * min(1.0, t * 1.15))
        pose = {
            "spine": {"rot": [7.0 * k, 0, 0]},
            "chest": {"rot": [4.0 * k, 0, 0]},
            "neck": {"rot": [-9.0 * k, 0, 0]},
            "head": {"rot": [-13.0 * k, 0, 3.0 * math.sin(TAU * t)]},
            "ear.L": {"rot": [-14.0 * k, 0, 3.0 * k]},
            "ear.R": {"rot": [-14.0 * k, 0, 3.0 * k]},
            "front_upper.L": {"rot": [-10.0 * k, 0, 0]},
            "front_upper.R": {"rot": [-10.0 * k, 0, 0]},
            "back_upper.L": {"rot": [7.0 * k, 0, 0]},
            "back_upper.R": {"rot": [7.0 * k, 0, 0]},
        }
        pose.update(tail_wave(TAU * t, amp=10.0, lift=30.0 * k))
        keys.append((f, pose))
    make("Interact", keys, 60)

    clear_pose(arm)
    arm.animation_data.action = None
    bpy.context.scene.frame_set(0)

    order = ["Idle", "Spawn", "Walk", "Run", "Turn", "Happy", "Curious",
             "Interact"]
    return order