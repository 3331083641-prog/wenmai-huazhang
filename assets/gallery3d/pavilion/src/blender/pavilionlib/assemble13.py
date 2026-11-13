"""v14 装配管线（80 × 96m 宋风四方水院，零穿模疏朗布局）。
blender -b --factory-startup -P build_v13.py -- [选项]
    --only site,gate,hall,halls,exhibits   # 只建指定部件  --no-bake / --no-uv1 / --no-export / --no-save / --reuse-ao / --force-tex / --draco
  --samples 24 / --out D:\\Design
"""
from __future__ import annotations

import importlib
import os
import sys
import time

import bpy
import bmesh
from mathutils import Matrix, Vector

from . import Context
from . import finalize as fz
from . import mesh_util as mu
from .dim13 import DIM13
from .materials import build_materials, reload_textures

PARTS = ["site", "gate", "hall", "halls", "crafts", "exhibits"]

OUT_DEFAULT = r"D:\Design"


def _args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    opt = {"only": None, "bake": True, "uv1": True, "samples": 24,
           "out": OUT_DEFAULT, "export": True, "save": True, "draco": False,
           "reuse_ao": False, "force_tex": False, "audit_overlap": False,
           "preview": None, "qa": [], "tag": "v15"}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--only" and i + 1 < len(argv):
            opt["only"] = [x.strip() for x in argv[i + 1].split(",") if x.strip()]
            i += 2
        elif a == "--preview" and i + 1 < len(argv):
            opt["preview"] = argv[i + 1]
            i += 2
        elif a == "--qa-cam" and i + 1 < len(argv):
            opt["qa"].append(argv[i + 1])
            i += 2
        elif a == "--audit-overlap":
            opt["audit_overlap"] = True
            i += 1
        elif a == "--reuse-ao":
            opt["reuse_ao"] = True
            i += 1
        elif a == "--force-tex":
            opt["force_tex"] = True
            i += 1
        elif a == "--no-bake":
            opt["bake"] = False
            i += 1
        elif a == "--no-uv1":
            opt["uv1"] = False
            i += 1
        elif a == "--no-export":
            opt["export"] = False
            i += 1
        elif a == "--no-save":
            opt["save"] = False
            i += 1
        elif a == "--draco":
            opt["draco"] = True
            i += 1
        elif a == "--samples" and i + 1 < len(argv):
            opt["samples"] = int(argv[i + 1])
            i += 2
        elif a == "--out" and i + 1 < len(argv):
            opt["out"] = argv[i + 1]
            i += 2
        elif a == "--tag" and i + 1 < len(argv):
            opt["tag"] = argv[i + 1]
            i += 2
        else:
            raise ValueError(f"Unknown or incomplete build option: {a}")
    if opt["only"] is not None and (not opt["only"] or set(opt["only"]) - set(PARTS)):
        raise ValueError(f"Invalid part selection: {opt['only']}")
    if opt["bake"] and not opt["uv1"]:
        raise ValueError("AO baking requires UV1; use --no-bake with --no-uv1")
    if opt["samples"] < 1:
        raise ValueError("--samples must be positive")
    return opt


def _tri(ob):
    try:
        return sum(max(0, len(p.vertices) - 2) for p in ob.data.polygons)
    except Exception:
        return 0


def build_parts(C, only=None):
    for name in PARTS:
        if only and name not in only:
            continue
        mod = importlib.import_module(f".parts13.{name}", __package__)
        fn = getattr(mod, "build", None)
        if not callable(fn):
            raise RuntimeError(f"Required part {name} has no callable build(C)")
        t0 = time.time()
        n0 = len(C.objects)
        t_before = sum(_tri(ob) for ob in C.objects)
        try:
            fn(C)
        except Exception as e:
            import traceback
            print(f"[assemble] !! {name} 构建失败: {e}")
            traceback.print_exc()
            raise RuntimeError(f"Part {name} failed; export aborted") from e
        new_objs = C.objects[n0:]
        if not new_objs:
            raise RuntimeError(f"Part {name} produced no geometry; export aborted")
        bpy.context.view_layer.update()
        tris = sum(_tri(ob) for ob in C.objects) - t_before
        zmax = None
        bmin = [1e9, 1e9, 1e9]
        bmax = [-1e9, -1e9, -1e9]
        for ob in new_objs:
            if ob.type != "MESH":
                continue
            for v in ob.data.vertices:
                w = ob.matrix_world @ v.co
                for i in range(3):
                    bmin[i] = min(bmin[i], w[i])
                    bmax[i] = max(bmax[i], w[i])
                zmax = w.z if zmax is None else max(zmax, w.z)
        bb = ("-", "-", "-", "-", "-", "-") if zmax is None else (
            f"{bmin[0]:.2f}", f"{bmin[1]:.2f}", f"{bmin[2]:.2f}",
            f"{bmax[0]:.2f}", f"{bmax[1]:.2f}", f"{bmax[2]:.2f}")
        print(f"[部件] {name:<11} {time.time() - t0:6.1f}s  {len(new_objs):4d} 对象  "
              f"{tris:7d} tri  max(z)={('%.3f' % zmax) if zmax is not None else '-'}  "
              f"bbox=({bb[0]},{bb[1]},{bb[2]})→({bb[3]},{bb[4]},{bb[5]})")


def add_interior_lights(sc):
    """导出 Blender 场景为 GLB。"""
    import bpy as _bpy
    from mathutils import Vector as _V

    SPECS = [
        ("INT_SkyShaft", (0.0, 9.0, 14.60), (0.0, 9.0, 0.30), 5.0, 1300.0, (1.0, 0.95, 0.86), True),
        ("INT_Bounce",   (0.0, 9.0, 1.40),  (0.0, 9.0, 9.0),  18.0, 620.0, (1.0, 0.90, 0.78), False),
        ("INT_Door",     (0.0, 0.6, 3.60),  (0.0, 8.0, 3.0),  8.0, 340.0, (1.0, 0.93, 0.84), False),
        ("P13_KM", (-32.0, -30.0, 4.00), (-32.0, -30.0, 0.0), 10.0, 420.0, (1.0, 0.93, 0.84), False),
        ("P13_CH", (-32.0, -12.0, 4.00), (-32.0, -12.0, 0.0), 10.0, 420.0, (1.0, 0.93, 0.84), False),
        ("P13_ZJ", (32.0, -30.0, 4.00),  (32.0, -30.0, 0.0),  10.0, 420.0, (1.0, 0.93, 0.84), False),
        ("P13_SJ", (32.0, -12.0, 4.00),  (32.0, -12.0, 0.0),  10.0, 420.0, (1.0, 0.93, 0.84), False),
        ("P13_LJ", (-20.0, -42.0, 3.20), (-20.0, -42.0, 0.15), 8.0, 300.0, (1.0, 0.93, 0.84), False),
        ("CL_S", (0.0, -38.7, 3.20), (0.0, -38.7, 0.0), 12.0, 240.0, (1.0, 0.90, 0.80), False),
        ("CL_N", (0.0, -11.7, 3.20), (0.0, -11.7, 0.0), 12.0, 240.0, (1.0, 0.90, 0.80), False),
    ]
    for name, loc, look, size, energy, color, shadow in SPECS:
        ld = _bpy.data.lights.new(name, "AREA")
        ld.shape = "SQUARE"
        ld.size = size
        ld.energy = energy
        ld.color = color
        ld.use_shadow = shadow
        ob = _bpy.data.objects.new(name, ld)
        ob.location = _V(loc)
        ob.rotation_euler = (_V(look) - _V(loc)).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(ob)
    print(f"[light] 布置 {len(SPECS)} 盏灯")


def _remove_zero_area_and_duplicate_faces(objects):
    """Triangulate and remove coincident or zero-area delivery faces."""
    removed_degenerate = 0
    removed_duplicate = 0
    for ob in objects:
        if ob.type != "MESH":
            continue
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bad = [f for f in bm.faces if f.calc_area() <= 1.0e-10]
        removed_degenerate += len(bad)
        if bad:
            bmesh.ops.delete(bm, geom=bad, context="FACES_ONLY")
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        # A valid n-gon can contain collinear perimeter vertices. Its
        # tessellation can create zero-area triangles even when the n-gon passed.
        collapsed = []
        for face in bm.faces:
            a,b,c = (v.co for v in face.verts)
            if (b-a).cross(c-a).length_squared <= 4.0e-20:
                collapsed.append(face)
        if collapsed:
            removed_degenerate += len(collapsed)
            bmesh.ops.delete(bm, geom=collapsed, context="FACES_ONLY")
        seen = set()
        duplicate_faces = set()
        for face in bm.faces:
            if len(face.verts) != 3:
                raise RuntimeError("Triangulation did not produce triangles: " + ob.name)
            key = tuple(sorted(tuple(round(c, 7) for c in v.co)
                               for v in face.verts))
            if key in seen:
                duplicate_faces.add(face)
            else:
                seen.add(key)
        removed_duplicate += len(duplicate_faces)
        if duplicate_faces:
            bmesh.ops.delete(bm, geom=list(duplicate_faces), context="FACES_ONLY")
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()
    print(f"[mesh-clean] degenerate={removed_degenerate} duplicate={removed_duplicate}")
    return removed_degenerate, removed_duplicate


def render_previews(sc, outdir, views=None, qa=None):
    """按 CAM_* 机位用 EEVEE 渲染。"""
    import bpy
    os.makedirs(outdir, exist_ok=True)
    try:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x = 1400
    sc.render.resolution_y = 1000
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    for attr, val in (("taa_render_samples", 24), ("use_gtao", True),
                      ("use_raytracing", True)):
        try:
            setattr(sc.eevee, attr, val)
        except Exception:
            pass
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = 0.0
    sc.render.image_settings.color_mode = "RGB"

    cd = bpy.data.cameras.new("PREVIEW_CAM")
    cd.clip_start = 0.05
    cd.clip_end = 4000.0
    cd.sensor_width = 36.0
    cam = bpy.data.objects.new("PREVIEW_CAM", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam

    names = sorted(o.name for o in sc.objects
                   if o.type == "EMPTY" and o.name.startswith("CAM_"))
    # Explicit QA shots replace default views unless a view subset was also requested.
    for name in ([] if qa and not views else names):
        if views and name not in views:
            continue
        e = bpy.data.objects[name]
        cam.matrix_world = e.matrix_world.copy()
        cd.lens = float(e.get("lens", 35.0))
        path = os.path.join(outdir, name + ".png")
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print(f"[preview] {path}")

    for spec in (qa or []):
        try:
            name, loc_s, tgt_s, lens_s = spec.split(":")
            loc = Vector([float(v) for v in loc_s.split(",")])
            tgt = Vector([float(v) for v in tgt_s.split(",")])
            d = tgt - loc
            # 逐张 QA 相机
            # 每张 EEVEE 独立相机
            qcd = bpy.data.cameras.new("QA_" + name)
            qcd.lens = float(lens_s) if lens_s else 35.0
            qcd.clip_start = 0.05
            qcd.clip_end = 4000.0
            qcam = bpy.data.objects.new("QA_" + name, qcd)
            sc.collection.objects.link(qcam)
            qcam.matrix_world = (Matrix.Translation(loc)
                                 @ d.to_track_quat("-Z", "Y").to_matrix().to_4x4())
            sc.camera = qcam
            bpy.context.view_layer.update()
            path = os.path.join(outdir, name + ".png")
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
            print(f"[qa-cam] {path}")
            bpy.data.objects.remove(qcam, do_unlink=True)
            bpy.data.cameras.remove(qcd)
        except Exception as exc:
            raise RuntimeError(f"QA camera render failed: {spec}") from exc
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(cd)


def main():
    opt = _args()
    t_all = time.time()
    sc = fz.reset_scene()
    mats = build_materials()
    C = Context(dim=DIM13, mats=mats)
    print(f"[assemble] {opt['tag']} 部件: {opt['only'] or PARTS}")

    build_parts(C, opt["only"])
    tris, per = C.stats()
    print(f"[assemble] 共 {len(C.objects)} 对象 / {tris} 三角面")
    for k, v in sorted(per.items(), key=lambda kv: -kv[1]):
        print(f"           {k:<11} {v:>8}")

    ground_objs = [o.name for o in C.objects if o.get("cat") == "ground"]
    if ground_objs:
        raise RuntimeError("发现 cat=ground 对象: " + ", ".join(ground_objs))

    _bmin = [1e9, 1e9, 1e9]
    _bmax = [-1e9, -1e9, -1e9]
    for o in C.objects:
        if o.get("cat") == "ground":
            continue
        for v in o.bound_box:
            w = o.matrix_world @ Vector(v)
            for i in range(3):
                _bmin[i] = min(_bmin[i], w[i])
                _bmax[i] = max(_bmax[i], w[i])
    arch_bbox = [round(x, 3) for x in _bmin] + [round(x, 3) for x in _bmax]
    print(f"[assemble] 建筑包围盒 {arch_bbox}")

    overlap_result = None
    if opt["audit_overlap"]:
        from .overlap13 import audit
        overlap_result = audit(C.objects, os.path.join(opt["out"], f"{opt['tag']}_overlap.json"))
        if (opt["save"] or opt["export"]) and (overlap_result["cross"] or overlap_result["coplanar"]):
            raise RuntimeError("Unresolved cross/coplanar contacts; publication aborted. Inspect overlap report.")

    merged = fz.join_by_material(C, grp="arch")
    degenerate, duplicates = _remove_zero_area_and_duplicate_faces(merged.values())
    C.prune_helpers()
    objs = list(merged.values())
    tris2 = sum(mu.tri_count(o) for o in objs)
    print(f"[assemble] 合并后 {len(objs)} 个 Mesh / {tris2} 三角面")

    if opt["uv1"]:
        unwrapped = fz.uv1_lightmap(objs)
        if set(unwrapped) != {ob.name for ob in objs}:
            raise RuntimeError("UV1 lightmap packing incomplete")
    tex_dir = os.path.join(opt["out"], "textures")
    used_keys = sorted({o.data.materials[0].get("key") for o in objs if o.data.materials})
    ao_results = {}
    if opt["bake"]:
        ao_results = fz.bake_ao(objs, tex_dir, samples=opt["samples"],
                                reuse=opt["reuse_ao"], skip=("lightstrip",))
        missing_ao = set(used_keys) - {"lightstrip"} - set(ao_results)
        if missing_ao:
            raise RuntimeError(f"AO baking incomplete: {sorted(missing_ao)}")

    if opt["bake"] or opt["force_tex"]:
        # Generate into this build's output; never reconnect old canonical AO.
        tmod = importlib.import_module(".textures", __package__)
        generated = tmod.generate_all(tex_dir, materials=used_keys, only=used_keys,
                                      ao_keys=ao_results if opt["bake"] else None)
        if set(used_keys) - set(generated):
            raise RuntimeError(f"Missing texture outputs: {set(used_keys) - set(generated)}")
        if opt["bake"]:
            from . import texopt
            started = time.time_ns()
            texopt.optimize(tex_dir)
            for maps in generated.values():
                for png in maps.values():
                    jpg = os.path.splitext(png)[0] + ".jpg"
                    if not os.path.isfile(jpg) or os.stat(jpg).st_mtime_ns < started:
                        raise RuntimeError(f"Missing fresh Web texture: {jpg}")
            # A same-path image may still hold pixels loaded at build startup.
            for image in bpy.data.images:
                if image.source == "FILE" and image.filepath:
                    path = os.path.abspath(bpy.path.abspath(image.filepath))
                    if os.path.dirname(path) == os.path.abspath(tex_dir) and os.path.isfile(path):
                        image.reload()
        reload_textures(tex_dir, prefer_png=not opt["bake"])
    else:
        tex_dir = r"D:\Design\textures"
        reload_textures(tex_dir)
        print("[textures] Preview uses canonical textures; no new AO baked")

    fz.add_camera_anchors(sc, dim=DIM13)

    exmod = importlib.import_module(".parts13.exhibits", __package__)
    exmod.add_anchors(sc)

    frames = [o for o in sc.objects if o.type == "EMPTY" and o.name.startswith("FRAME_")]
    frames.sort(key=lambda o: o.name)
    snaps = [o for o in sc.objects if o.type == "EMPTY" and o.name.startswith("SNAP_")]
    snaps.sort(key=lambda o: o.name)
    cams = [o for o in sc.objects if o.type == "EMPTY" and o.name.startswith("CAM_")]
    fz.add_groups(objs, [], anchors=frames + snaps, cams=cams)
    bpy.context.view_layer.update()
    print(f"[anchor] 画框 {len(frames)} 组 / 吸附 {len(snaps)} 个")

    fz.add_lights(sc)
    envmod = importlib.import_module(".parts13.env", __package__)
    envmod.build_sky(sc, DIM13)

    blend = os.path.join(opt["out"], "wenmai_master_pavilion.blend")
    if opt["preview"]:
        render_previews(sc, opt["preview"], None, opt["qa"])
    if opt["save"]:
        fz.save_blend(blend)
    if opt["export"]:
        glb = os.path.join(opt["out"], "wenmai_master_pavilion.glb")
        fz.export_glb(glb, objs, draco=opt["draco"])

    mesh_min, mesh_max = fz.scene_bbox(objs)
    extra = {
        "source_blend": "wenmai_master_pavilion.blend" if opt["save"] else None,
        "glb": "wenmai_master_pavilion.glb" if opt["export"] else None,
        "bbox_architecture": list(mesh_min) + list(mesh_max),
        "cameras": {name: {"cn": spec["cn"], "location": list(spec["loc"]),
                           "look_at": list(spec["look"]), "lens_mm": spec["lens"]}
                    for name, spec in DIM13.CAMERAS.items()},
        "build_seconds": round(time.time() - t_all, 1),
        "mesh_cleanup": {"removed_degenerate": degenerate, "removed_duplicate": duplicates},
        "version": opt["tag"],
        "build_scope": opt["only"] or list(PARTS),
        "saved_blend": bool(opt["save"]),
        "exported_glb": bool(opt["export"]),
        "baked_ao": sorted(ao_results),
        "coordinates": "Blender metres Z-up; glTF converts to Y-up",
        "nominal_base": {"x": [-40,40], "y": [-48,48], "z": [-1.2,0]},
        "tolerance_spec_m": {"LIFT": .0015, "FLIFT": .0025, "SEAM": .0035},
        "contact_audit": ({
            "schema": overlap_result["schema"],
            "cross_candidates": len(overlap_result["cross"]),
            "coplanar_candidates": len(overlap_result["coplanar"]),
            "review_required": overlap_result["review_required"],
            "accepted_contacts": overlap_result["accepted_contacts"],
            "verified_zero_intersections": overlap_result["verified_zero_intersections"],
            "report": f"{opt['tag']}_overlap.json",
        } if overlap_result else {"status": "not_run"}),
        "notes": [
            "Nominal plinth footprint differs from full geometry bounds including eaves and dragon spouts.",
            "Contact classes are review hints, not proof that intersections are harmless.",
            "Craft motifs are original procedural interpretations, not authenticated historical reproductions.",
            "Craft assemblies are integrated by parts13/crafts.py; independent props exports are not asserted by this manifest.",
            "Requested dimensional and clearance tolerances require separate measurement evidence.",
        ],
    }
    extra["groups"] = {
        "GRP_Pavilion_Architecture": {
            "meshes": [o.name for o in objs],
            "cameras": [c.name for c in cams],
            "anchors": [a.name for a in frames],
            "snaps": [s.name for s in snaps],
        },
    }
    extra["anchors"] = []
    for a in frames:
        e = {"name": a.name,
             "location": [round(v, 4) for v in a.matrix_world.translation],
             "cn": a.get("cn", ""),
             "mount": a.get("mount", ""),
             "facing": a.get("facing", "-Y"),
             "frame_size": list(a.get("frame_size", [])),
             "note": "画框朝 -Y、法线朝 +Z"}
        for k in ("style", "slot", "cls", "aspect", "size"):
            if k in a.keys():
                v = a[k]
                e[k] = list(v) if k == "size" else (float(v) if k == "aspect" else v)
        extra["anchors"].append(e)

    extra["snap_anchors"] = []
    for s in snaps:
        e = {"name": s.name,
             "location": [round(v, 4) for v in s.matrix_world.translation],
             "cn": s.get("cn", ""),
             "hall": s.get("hall", ""),
             "kind": s.get("kind", "desk"),
             "limit": s.get("limit", ""),
             "note": "正向朝 +Z"}
        extra["snap_anchors"].append(e)

    extra["halls"] = [
        {"id": k, "cn": v["cn"], "style": v["style"],
         "center": [v["cx"], v["cy"]], "half": [v["hx"], v["hy"]]}
        for k, v in DIM13.HALLS.items()
    ]
    extra["teleports"] = [{"id": k, "cn": v["cn"], "loc": list(v["loc"]),
                           "look": list(v["look"])}
                          for k, v in DIM13.TELEPORTS.items()]
    fz.write_manifest(os.path.join(opt["out"], "build_manifest.json"), objs, extra)
    print(f"[assemble] 总耗时 {time.time() - t_all:.1f}s")


if __name__ == "__main__":
    main()
