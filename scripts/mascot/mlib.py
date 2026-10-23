"""Self-contained Blender helper library for the 「纹纹」 mascot.

Everything the mascot needs is here so the build does not depend on the
(deleted) world3d scripts.

Conventions
  * geometry is authored directly in world space -> object transforms stay
    identity, so there is no "apply transform" step
  * Blender +Y is the FRONT; the glTF exporter maps +Y -> -Z, which is the
    contract's "front faces -Z"
  * colours are converted sRGB -> linear before assignment so the rendered /
    exported hex matches the art direction
  * no image textures anywhere: Principled BSDF base colour only
"""
import math

import bmesh
import bpy
from mathutils import Vector

TAU = math.tau


# --------------------------------------------------------------------------- #
# colour
# --------------------------------------------------------------------------- #
def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear_rgba(hx, alpha=1.0):
    hx = hx.lstrip("#")
    r, g, b = (int(hx[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), alpha)


def make_material(name, hx, rough=0.8, metal=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
        if out is None:
            out = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    rgba = hex_to_linear_rgba(hx)
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    mat.diffuse_color = rgba
    mat.roughness = rough
    mat.metallic = metal
    return mat


# --------------------------------------------------------------------------- #
# primitives -> (verts, faces)
# --------------------------------------------------------------------------- #
def box(center, size, rot=None):
    cx, cy, cz = center
    sx, sy, sz = (s * 0.5 for s in size)
    pts = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
           (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    if rot is not None:
        pts = [rot @ Vector(p) for p in pts]
    verts = [(p[0] + cx, p[1] + cy, p[2] + cz) for p in pts]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return verts, faces


def _frame_from_dir(direction):
    d = Vector(direction).normalized()
    ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(ref).normalized()
    v = d.cross(u).normalized()
    return u, v


def cylinder(p0, p1, r0, r1, n=12, caps=True):
    p0, p1 = Vector(p0), Vector(p1)
    u, v = _frame_from_dir(p1 - p0)
    verts, faces = [], []
    for i in range(n):
        a = TAU * i / n
        off = math.cos(a) * u + math.sin(a) * v
        verts.append(tuple(p0 + off * r0))
        verts.append(tuple(p1 + off * r1))
    for i in range(n):
        a, b = 2 * i, 2 * i + 1
        c, d = 2 * ((i + 1) % n), 2 * ((i + 1) % n) + 1
        faces.append((a, c, d, b))
    if caps:
        faces.append(tuple(range(0, 2 * n, 2))[::-1])
        faces.append(tuple(range(1, 2 * n, 2)))
    return verts, faces


def ellipsoid(center, radii, nu=16, nv=10):
    cx, cy, cz = center
    rx, ry, rz = radii
    verts, faces = [], []
    verts.append((cx, cy, cz + rz))
    for j in range(1, nv):
        phi = math.pi * j / nv
        sp, cp = math.sin(phi), math.cos(phi)
        for i in range(nu):
            th = TAU * i / nu
            verts.append((cx + rx * sp * math.cos(th),
                          cy + ry * sp * math.sin(th),
                          cz + rz * cp))
    verts.append((cx, cy, cz - rz))
    top, bot = 0, len(verts) - 1
    ring = lambda j: 1 + (j - 1) * nu
    for i in range(nu):
        faces.append((top, ring(1) + i, ring(1) + (i + 1) % nu))
    for j in range(1, nv - 1):
        for i in range(nu):
            a = ring(j) + i
            b = ring(j) + (i + 1) % nu
            c = ring(j + 1) + (i + 1) % nu
            d = ring(j + 1) + i
            faces.append((a, b, c, d))
    for i in range(nu):
        faces.append((bot, ring(nv - 1) + (i + 1) % nu, ring(nv - 1) + i))
    return verts, faces


def loft(rings, cap_start=True, cap_end=True):
    n = len(rings[0])
    verts, faces = [], []
    for r in rings:
        assert len(r) == n, "all rings need the same point count"
        verts.extend(tuple(p) for p in r)
    for j in range(len(rings) - 1):
        base, nxt = j * n, (j + 1) * n
        for i in range(n):
            a = base + i
            b = base + (i + 1) % n
            c = nxt + (i + 1) % n
            d = nxt + i
            faces.append((a, b, c, d))
    if cap_start:
        faces.append(tuple(range(n - 1, -1, -1)))
    if cap_end:
        o = (len(rings) - 1) * n
        faces.append(tuple(o + i for i in range(n)))
    return verts, faces


def tube_along(points, radii, n=8, caps=True):
    """Sweep a circular profile along a polyline (parallel-transport frames)."""
    pts = [Vector(p) for p in points]
    if isinstance(radii, (int, float)):
        radii = [float(radii)] * len(pts)
    tangents = []
    for i in range(len(pts)):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == len(pts) - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        if t.length < 1e-9:
            t = Vector((0, 0, 1))
        tangents.append(t.normalized())
    up = Vector((0, 0, 1))
    if abs(tangents[0].dot(up)) > 0.95:
        up = Vector((1, 0, 0))
    normal = (up - tangents[0] * up.dot(tangents[0])).normalized()
    rings = []
    for i, (p, t) in enumerate(zip(pts, tangents)):
        if i > 0:
            normal = (normal - t * normal.dot(t))
            normal = normal.normalized() if normal.length > 1e-8 else _frame_from_dir(t)[0]
        binormal = t.cross(normal).normalized()
        ring = []
        for k in range(n):
            a = TAU * k / n
            ring.append(p + normal * (math.cos(a) * radii[i])
                        + binormal * (math.sin(a) * radii[i]))
        rings.append(ring)
    return loft(rings, caps, caps)


def smoothstep(e0, e1, x):
    if e1 == e0:
        return 0.0 if x < e0 else 1.0
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def ring_pts(center, rx, ry, n=16, z=None):
    cx, cy, cz = center
    return [(cx + math.cos(TAU * i / n) * rx,
             cy + math.sin(TAU * i / n) * ry,
             cz if z is None else z) for i in range(n)]


# --------------------------------------------------------------------------- #
# mesh builder: one object, many material slots, per-vertex skin weights
# --------------------------------------------------------------------------- #
class MeshBuilder:
    def __init__(self, name):
        self.name = name
        self.verts = []
        self.faces = []
        self.face_mats = []
        self.face_smooth = []
        self.materials = []
        self.weights = []

    def slot(self, mat):
        if mat not in self.materials:
            self.materials.append(mat)
        return self.materials.index(mat)

    def add(self, geo, mat, smooth=False, weights=None):
        verts, faces = geo
        base = len(self.verts)
        self.verts.extend(verts)
        idx = self.slot(mat)
        for f in faces:
            f = [i + base for i in f]
            dedup = []
            for i in f:
                if not dedup or dedup[-1] != i:
                    dedup.append(i)
            if len(dedup) > 2 and dedup[0] == dedup[-1]:
                dedup.pop()
            if len(dedup) < 3:
                continue
            self.faces.append(tuple(dedup))
            self.face_mats.append(idx)
            self.face_smooth.append(smooth)
        for co in verts:
            if weights is None:
                self.weights.append({})
            elif callable(weights):
                w = weights(Vector(co)) or {}
                s = sum(w.values())
                self.weights.append({k: v / s for k, v in w.items() if v > 0}
                                    if s > 0 else {})
            else:
                self.weights.append(dict(weights))
        return self

    def build(self):
        me = bpy.data.meshes.new(self.name)
        me.from_pydata(self.verts, [], self.faces)
        me.validate(verbose=False)
        for mat in self.materials:
            me.materials.append(mat)
        for i, poly in enumerate(me.polygons):
            poly.material_index = self.face_mats[i]
            poly.use_smooth = self.face_smooth[i]
        me.update()
        ob = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(ob)

        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        me.update()

        if any(self.weights):
            self._apply_weights(ob)
        return ob

    def _apply_weights(self, ob):
        names = []
        for w in self.weights:
            for nm in w:
                if nm not in names:
                    names.append(nm)
        groups = {nm: ob.vertex_groups.new(name=nm) for nm in names}
        from mathutils.kdtree import KDTree
        kd = KDTree(len(self.verts))
        for i, co in enumerate(self.verts):
            kd.insert(co, i)
        kd.balance()
        for v in ob.data.vertices:
            _, idx, _ = kd.find(v.co)
            for nm, weight in self.weights[idx].items():
                groups[nm].add([v.index], weight, "REPLACE")


# --------------------------------------------------------------------------- #
# scene / export / measure
# --------------------------------------------------------------------------- #
def reset_scene(fps=30):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.render.fps = fps
    sc.frame_start = 0
    sc.frame_end = 90
    return sc


def export_glb(filepath, **kwargs):
    props = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    defaults = dict(
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_materials="EXPORT",
        export_texcoords=False,
        export_normals=True,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_frame_range=False,
        export_anim_slide_to_zero=True,
        export_optimize_animation_size=False,
        export_skins=True,
        export_def_bones=False,
        export_cameras=False,
        export_lights=False,
        use_selection=False,
        export_extras=False,
    )
    defaults.update(kwargs)
    args = {k: v for k, v in defaults.items() if k in props}
    bpy.ops.export_scene.gltf(filepath=filepath, **args)
    return args


def object_bounds(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    pts = [ob.matrix_world @ v.co
           for v in ob.evaluated_get(deps).to_mesh().vertices]
    if not pts:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def scene_bounds():
    pts = []
    deps = bpy.context.evaluated_depsgraph_get()
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        ev = ob.evaluated_get(deps)
        me = ev.to_mesh()
        pts += [ob.matrix_world @ v.co for v in me.vertices]
        ev.to_mesh_clear()
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def tri_count(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(deps).to_mesh()
    return sum(len(p.vertices) - 2 for p in me.polygons)


def fit_height(ob, target, center_xy=True):
    """Scale uniformly so the mesh is exactly `target` tall and sits on z=0."""
    lo, hi = object_bounds(ob)
    size = hi - lo
    k = target / size.z if size.z > 1e-9 else 1.0
    anchor = Vector(((lo.x + hi.x) * 0.5 if center_xy else 0.0,
                     (lo.y + hi.y) * 0.5 if center_xy else 0.0, lo.z))
    for v in ob.data.vertices:
        v.co = Vector(((v.co.x - anchor.x) * k,
                       (v.co.y - anchor.y) * k,
                       (v.co.z - anchor.z) * k))
    ob.data.update()
    return object_bounds(ob)