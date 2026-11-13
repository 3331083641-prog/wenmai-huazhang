"""构建上下文 Context —— 所有构件模块唯一对外依赖（自 gallerylib 演化）。

职责：集合归集、材质槽、原型(proto)缓存与实例化、面数统计。
"""
from __future__ import annotations

import math
from typing import Callable

import bmesh
import bpy
from mathutils import Matrix, Vector

from .dim import DIM, Dim
from . import mesh_util as mu

CAT_CN = {
    "foundation": "基盘与驳岸", "water": "水体", "hall": "主殿大木构架",
    "gallery": "水上连廊", "pavilion": "副展阁", "bridge": "凌波飞桥",
    "roof": "屋面与屋脊", "interior": "室内（藻井/水镜/展墙）",
    "detail": "细部", "misc": "其他",
}


class Context:
    def __init__(self, dim: Dim = None, mats=None, root_name="WenmaiPavilion",
                 options=None):
        self.d = dim or DIM
        self.mats = mats
        self.options = options or {}
        self.root = self._ensure_coll(root_name, None)
        self.objects: list[bpy.types.Object] = []
        self._colls: dict[str, bpy.types.Collection] = {}
        self._proto_objs: dict[str, bpy.types.Object] = {}
        self.log: list[str] = []

    # -------------------------------------------------------------- 集合
    def _ensure_coll(self, name, parent):
        c = bpy.data.collections.get(name)
        if c is None:
            c = bpy.data.collections.new(name)
        if parent is None:
            if c.name not in {x.name for x in bpy.context.scene.collection.children}:
                bpy.context.scene.collection.children.link(c)
        else:
            if c.name not in {x.name for x in parent.children}:
                try:
                    parent.children.link(c)
                except RuntimeError:
                    pass
        return c

    def coll(self, *path) -> bpy.types.Collection:
        key = "/".join(path)
        if key in self._colls:
            return self._colls[key]
        parent = self.root
        for seg in path:
            nm = seg if parent == self.root else f"{parent.name}__{seg}"
            parent = self._ensure_coll(nm, parent)
        self._colls[key] = parent
        return parent

    # -------------------------------------------------------------- 材质
    def mat1(self, key):
        return None if self.mats is None else self.mats.get(key)

    def mat(self, *keys):
        return [self.mat1(k) for k in keys]

    # -------------------------------------------------------------- 建对象
    def bm_obj(self, bm, name, cat, coll_path, cn=None, mat="wood_dark",
               smooth=35.0, uv=1.0, flat=False, free=True) -> bpy.types.Object:
        coll = coll_path if isinstance(coll_path, bpy.types.Collection) else self.coll(*coll_path)
        if uv:
            try:
                bm.normal_update()
                mu.uv_box_project(bm, uv)
            except Exception:
                pass
        me = mu.bm_to_mesh(bm, name)
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        if self.mats is not None and mat:
            keys = mat if isinstance(mat, (list, tuple)) else [mat]
            for k in keys:
                m = k if isinstance(k, bpy.types.Material) else self.mats.get(k)
                if m is not None:
                    ob.data.materials.append(m)
        ob["cat"] = cat
        ob["cn"] = cn or CAT_CN.get(cat, "")
        if flat:
            mu.flat_shade(ob)
        else:
            mu.smooth_by_angle(ob, smooth)
        self.objects.append(ob)
        if free:
            bm.free()
        return ob

    # -------------------------------------------------------------- 原型/实例
    def proto(self, key, build_fn: Callable, mat="wood_dark", smooth=35.0, uv=1.0):
        if key in self._proto_objs:
            return self._proto_objs[key]
        bm = mu.new_bm()
        build_fn(bm)
        coll = self.coll("_Prototypes")
        ob = self._finish_proto(bm, f"PROTO_{key}", mat, smooth, uv, coll)
        bm.free()
        ob.hide_viewport = True
        ob.hide_render = True
        self._proto_objs[key] = ob
        return ob

    def _finish_proto(self, bm, name, mat, smooth, uv, coll):
        if uv:
            try:
                bm.normal_update()
                mu.uv_box_project(bm, uv)
            except Exception:
                pass
        me = mu.bm_to_mesh(bm, name)
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        if self.mats is not None and mat:
            keys = mat if isinstance(mat, (list, tuple)) else [mat]
            for k in keys:
                m = k if isinstance(k, bpy.types.Material) else self.mats.get(k)
                if m is not None:
                    ob.data.materials.append(m)
        mu.smooth_by_angle(ob, smooth)
        return ob

    def place_at(self, proto_obj, loc, rot_z=0.0, name="inst", cat="detail",
                 coll_path=("_Instances",), cn=None, rot_y=0.0, rot_x=0.0, scale=1.0):
        m = (Matrix.Translation(Vector(loc))
             @ Matrix.Rotation(math.radians(rot_z), 4, "Z")
             @ Matrix.Rotation(math.radians(rot_y), 4, "Y")
             @ Matrix.Rotation(math.radians(rot_x), 4, "X")
             @ Matrix.Scale(scale, 4))
        coll = coll_path if isinstance(coll_path, bpy.types.Collection) else self.coll(*coll_path)
        ob = bpy.data.objects.new(name, proto_obj.data)
        ob.matrix_world = m
        coll.objects.link(ob)
        ob["cat"] = cat
        ob["cn"] = cn or CAT_CN.get(cat, "")
        ob["inst_of"] = proto_obj.name
        self.objects.append(ob)
        return ob

    def place_world(self, proto_obj, matrix, name="inst", cat="detail",
                    coll_path=("_Instances",), cn=None):
        coll = coll_path if isinstance(coll_path, bpy.types.Collection) else self.coll(*coll_path)
        ob = bpy.data.objects.new(name, proto_obj.data)
        ob.matrix_world = matrix
        coll.objects.link(ob)
        ob["cat"] = cat
        ob["cn"] = cn or CAT_CN.get(cat, "")
        ob["inst_of"] = proto_obj.name
        self.objects.append(ob)
        return ob

    # -------------------------------------------------------------- 统计
    def stats(self):
        total = 0
        per = {}
        for ob in self.objects:
            if ob.type != "MESH":
                continue
            n = mu.tri_count(ob)
            total += n
            c = ob.get("cat", "misc")
            per[c] = per.get(c, 0) + n
        return total, per

    def prune_helpers(self):
        for ob in list(self._proto_objs.values()):
            if ob.name in bpy.data.objects:
                bpy.data.objects.remove(ob, do_unlink=True)
        self._proto_objs.clear()
        c = bpy.data.collections.get("_Prototypes")
        if c:
            bpy.data.collections.remove(c)


def rot_z(deg):
    return Matrix.Rotation(math.radians(deg), 4, "Z")