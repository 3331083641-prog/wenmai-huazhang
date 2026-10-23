"""Geometry kernel for the 纹脉华章 parametric generators.

Owned by ``blender-gen``. Nothing in here knows about a specific component:
the roof / timber / interior / diorama modules build meshes with these
primitives and then hand them to :func:`finish`, which applies the naming and
``wm_part`` tagging contract from ``docs/CONTRACT.md``.

Design notes
------------
* Everything accumulates into a :class:`Geo` buffer, so a whole eave assembly
  becomes ONE object instead of ~900. That is what keeps object counts and the
  GLB node tree sane for the web viewer.
* No ``bpy.ops`` in the geometry paths: primitives are written as explicit
  vertex/face lists so a job is bit-for-bit reproducible (``bpy.ops`` depends
  on the active collection/selection state and is a common source of drift).
* Winding convention (``wm_common.mesh_object`` does not fix normals for us):

  - box template: exactly the ordering of ``wm_common.box`` -- CCW seen from
    outside.
  - sweep: each station is a closed polygon ordered CCW in the station's
    ``(side, normal)`` basis, where ``side = normal x tangent``. With that
    handedness the ring winding produces outward normals on the side walls,
    the last station cap faces forward and the first station cap is reversed.
  - Any single-face panel we add is wound explicitly by the caller.

Coordinates: metres, Z up, ``+Y`` is the building front (street side, matching
the shipped v5 blend and ``gallery_layout.json``), the plinth top is z = 0.
"""
from __future__ import annotations

import json
import math
import os

import bpy
from mathutils import Euler, Matrix, Vector

import wm_common as WC

# --------------------------------------------------------------------- helpers


def rnd(i, j, k=0):
    """Deterministic pseudo random in [0, 1) -- no ``random`` dependency."""
    n = (int(i) * 73856093) ^ (int(j) * 19349663) ^ (int(k) * 83492791)
    n &= 0x7FFFFFFF
    return (n % 10007) / 10007.0


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def lerp(a, b, t):
    return Vector(a) + (Vector(b) - Vector(a)) * t


def frame(origin, ex, ey):
    """Matrix with local +X = ex, +Y = ey, +Z = world up (both flattened to XY)."""
    ex = Vector((ex[0], ex[1], 0.0))
    ey = Vector((ey[0], ey[1], 0.0))
    if ex.length < 1e-9:
        ex = Vector((1.0, 0.0, 0.0))
    if ey.length < 1e-9:
        ey = Vector((0.0, 1.0, 0.0))
    ex.normalize()
    ey = Vector((-ex.y, ex.x, 0.0)) if abs(ey.dot(ex)) > 0.999 else ey.normalized()
    return Matrix(((ex.x, ey.x, 0.0, origin[0]),
                   (ex.y, ey.y, 0.0, origin[1]),
                   (0.0, 0.0, 1.0, origin[2]),
                   (0.0, 0.0, 0.0, 1.0)))


BOX_FACES = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
BOX_CORNERS = ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
               (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1))


# --------------------------------------------------------------------- buffer
class Geo:
    """Vertex/face accumulator; one instance becomes one mesh object."""

    __slots__ = ("v", "f")

    def __init__(self):
        self.v = []
        self.f = []

    # -- low level ----------------------------------------------------
    def add(self, verts, faces):
        o = len(self.v)
        self.v.extend(tuple(float(c) for c in p) for p in verts)
        self.f.extend(tuple(i + o for i in fc) for fc in faces)
        return o

    def box(self, centre, size, mat=None, rot=None):
        """Axis-aligned (or ``rot`` Euler XYZ) box."""
        cx, cy, cz = centre
        hx, hy, hz = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
        verts = [(cx + sx * hx, cy + sy * hy, cz + sz * hz)
                 for sx, sy, sz in BOX_CORNERS]
        if rot:
            R = Euler(tuple(rot), "XYZ").to_matrix()
            c = Vector((cx, cy, cz))
            verts = [tuple(R @ (Vector(v) - c) + c) for v in verts]
        self.add(verts, BOX_FACES)

    def box_m(self, M, centre=(0.0, 0.0, 0.0), size=(1.0, 1.0, 1.0)):
        """Box in the local frame ``M`` (used for every oriented roof part)."""
        hx, hy, hz = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
        verts = [M @ Vector((centre[0] + sx * hx, centre[1] + sy * hy,
                             centre[2] + sz * hz)) for sx, sy, sz in BOX_CORNERS]
        self.add(verts, BOX_FACES)

    def prism_xz(self, origin, profile, thickness, flip=False):
        """Extrude a 2D (x, z) profile along Y -- 3D text-free ornaments."""
        n = len(profile)
        verts = []
        for sy in (-1.0, 1.0):
            for (px, pz) in profile:
                verts.append((origin[0] + px, origin[1] + sy * thickness * 0.5,
                              origin[2] + pz))
        faces = []
        for i in range(n):
            a = i
            b = (i + 1) % n
            faces.append((a, a + n, b + n, b) if not flip else (a, b, b + n, a + n))
        front = tuple(range(n))
        back = tuple(range(n, 2 * n))
        faces.append(tuple(reversed(front)) if not flip else front)
        faces.append(back if not flip else tuple(reversed(back)))
        self.add(verts, faces)

    def disc(self, centre, normal, out, radius, thick, seg=12):
        """Round tile end (瓦当) standing proud of the eave along ``out``."""
        nrm = Vector(normal).normalized()
        ov = Vector(out).normalized()
        e1 = nrm.cross(ov)
        if e1.length < 1e-6:
            e1 = nrm.cross(Vector((1.0, 0.0, 0.0)))
        e1.normalize()
        c = Vector(centre)
        a = c - ov * thick * 0.5
        b = c + ov * thick * 0.5
        verts = []
        for cc in (a, b):
            for i in range(seg):
                t = 2.0 * math.pi * i / seg
                verts.append(tuple(cc + e1 * (radius * math.cos(t)) +
                                   nrm * (radius * math.sin(t))))
        faces = []
        for i in range(seg):
            j = (i + 1) % seg
            faces.append((i, j, j + seg, i + seg))
        faces.append(tuple(range(seg - 1, -1, -1)))
        faces.append(tuple(range(seg, 2 * seg)))
        self.add(verts, faces)

    def sphere(self, centre, radius, seg=10, rings=6, scale=(1.0, 1.0, 1.0)):
        """UV sphere (deterministic; used for foliage pads and beads)."""
        cx, cy, cz = centre
        verts = []
        for j in range(1, rings):
            phi = math.pi * j / rings
            r, z = math.sin(phi), math.cos(phi)
            for i in range(seg):
                a = 2.0 * math.pi * i / seg
                verts.append((cx + math.cos(a) * r * radius * scale[0],
                              cy + math.sin(a) * r * radius * scale[1],
                              cz + z * radius * scale[2]))
        top = len(verts)
        verts.append((cx, cy, cz + radius * scale[2]))
        bot = len(verts)
        verts.append((cx, cy, cz - radius * scale[2]))
        faces = []
        for j in range(rings - 2):
            for i in range(seg):
                a = j * seg + i
                b = j * seg + (i + 1) % seg
                faces.append((a, b, b + seg, a + seg))
        for i in range(seg):
            j = (i + 1) % seg
            faces.append((top, i, j))
            base = (rings - 2) * seg
            faces.append((bot, base + j, base + i))
        self.add(verts, faces)

    def limb(self, p0, p1, r0, r1=None, seg=8, cap=True):
        """Tapered tube between two arbitrary points (trunk / rafter / column)."""
        a, b = Vector(p0), Vector(p1)
        d = b - a
        if d.length < 1e-6:
            return
        t = d.normalized()
        up = Vector((0.0, 0.0, 1.0))
        if abs(t.z) > 0.94:
            up = Vector((0.0, 1.0, 0.0))
        n = t.cross(up).normalized()
        side = n.cross(t)
        r1 = r0 if r1 is None else r1
        rings = []
        for cc, r in ((a, r0), (b, r1)):
            rings.append([tuple(cc + side * (r * math.cos(2.0 * math.pi * i / seg)) +
                                n * (r * math.sin(2.0 * math.pi * i / seg)))
                          for i in range(seg)])
        o = self.add(rings[0] + rings[1], [])
        faces = []
        for i in range(seg):
            j = (i + 1) % seg
            faces.append((o + i, o + j, o + seg + j, o + seg + i))
        if cap:
            faces.append(tuple(o + i for i in range(seg - 1, -1, -1)))
            faces.append(tuple(o + seg + i for i in range(seg)))
        self.f.extend(faces)

    def sweep(self, stations, caps=True):
        """Sweep closed cross-sections.

        ``stations`` is a list of ``(pts, )`` where ``pts`` is a closed polygon
        ordered CCW in the station basis (see module docstring). Consecutive
        stations must have the same point count.
        """
        if len(stations) < 2:
            return
        n = len(stations[0])
        if any(len(s) != n for s in stations) or n < 3:
            return
        base = len(self.v)
        for st in stations:
            self.v.extend(tuple(float(c) for c in p) for p in st)
        for k in range(len(stations) - 1):
            a = base + k * n
            b = a + n
            for i in range(n):
                j = (i + 1) % n
                self.f.append((a + i, a + j, b + j, b + i))
        if caps:
            self.f.append(tuple(base + i for i in range(n - 1, -1, -1)))
            last = base + (len(stations) - 1) * n
            self.f.append(tuple(last + i for i in range(n)))


# ------------------------------------------------------------ surface shell
def surface_shell(geo, surf, nu, nv, thickness, hole=None, inside=None,
                  strip=None):
    """Solid slab following ``surf.point(u, v)`` with a constant thickness.

    ``strip`` = (u0, u1, v0, v1) restricts the grid to a sub-rectangle of
    parameter space, which is how the skirt roof is built as four closed ring
    strips instead of one slab with a hole cut in it: a cut hole leaves a raw
    boundary loop (136 boundary edges on the double-eave skirt), while four
    strips are each a closed solid that happens to overlap the hidden middle.

    ``hole`` / ``inside`` are the older single-slab filters, kept for callers
    that want them.
    """
    u0, u1, v0, v1 = strip or (-1.0, 1.0, -1.0, 1.0)
    top, bot = [], []
    for j in range(nv + 1):
        v = v0 + (v1 - v0) * j / nv
        rt, rb = [], []
        for i in range(nu + 1):
            u = u0 + (u1 - u0) * i / nu
            p = surf.point(u, v)
            rt.append((p.x, p.y, p.z))
            rb.append((p.x, p.y, p.z - thickness))
        top.append(rt)
        bot.append(rb)
    verts = [q for r in top for q in r] + [q for r in bot for q in r]
    n = (nu + 1) * (nv + 1)
    faces = []
    for j in range(nv):
        for i in range(nu):
            uc = u0 + (u1 - u0) * (i + 0.5) / nu
            vc = v0 + (v1 - v0) * (j + 0.5) / nv
            if hole is not None and abs(uc) < hole[0] and abs(vc) < hole[1]:
                continue
            if inside is not None and not inside(uc, vc):
                continue
            a = j * (nu + 1) + i
            q = (a, a + 1, a + nu + 2, a + nu + 1)
            faces.append(q)
            faces.append(tuple(reversed(tuple(x + n for x in q))))
    for j in range(nv):
        for i in (0, nu):
            a = j * (nu + 1) + i
            b = (j + 1) * (nu + 1) + i
            faces.append((a, b, b + n, a + n) if i == 0 else (b, a, a + n, b + n))
    for i in range(nu):
        for j in (0, nv):
            a = j * (nu + 1) + i
            b = j * (nu + 1) + i + 1
            faces.append((b, a, a + n, b + n) if j == 0 else (a, b, b + n, a + n))
    geo.add(verts, faces)
    return faces


# ---------------------------------------------------------------- collection
def collection(name):
    return WC.get_collection(name)


# --------------------------------------------------------------------- output
def finish(geo, name, part, component, mat_key, col, params,
           smooth=False, flat_shade_ok=True):
    """Turn a :class:`Geo` buffer into a tagged object (or ``None`` if empty)."""
    if geo is None or not geo.f:
        return None
    obj = WC.mesh_object(name, geo.v, geo.f, mat_key, col, smooth=smooth)
    obj["wm_part"] = part
    obj["wm_component"] = component
    obj["wm_params"] = json.dumps(params or {}, ensure_ascii=False,
                                  sort_keys=True)[:8000]
    if flat_shade_ok:
        obj.data.update()
    return obj


def tri_count(objs) -> int:
    total = 0
    for obj in objs:
        if obj is None or obj.type != "MESH":
            continue
        obj.data.calc_loop_triangles()
        total += len(obj.data.loop_triangles)
    return total


def inventory(objs) -> list:
    out = []
    for obj in objs:
        if obj is None or obj.type != "MESH":
            continue
        out.append({
            "name": obj.name,
            "part": obj.get("wm_part"),
            "component": obj.get("wm_component"),
            "verts": len(obj.data.vertices),
            "faces": len(obj.data.polygons),
        })
    return out


def mesh_report(objs) -> dict:
    """Topology audit used by the per-task checks."""
    boundary = nonmanifold = degenerate = 0
    faces = verts = 0
    for obj in objs:
        if obj is None or obj.type != "MESH":
            continue
        me = obj.data
        faces += len(me.polygons)
        verts += len(me.vertices)
        edges = {}
        for poly in me.polygons:
            vs = list(poly.vertices)
            for i, a in enumerate(vs):
                b = vs[(i + 1) % len(vs)]
                key = (a, b) if a < b else (b, a)
                edges[key] = edges.get(key, 0) + 1
            if poly.area <= 1e-9:
                degenerate += 1
        boundary += sum(1 for c in edges.values() if c == 1)
        nonmanifold += sum(1 for c in edges.values() if c > 2)
    return {"verts": verts, "faces": faces, "boundaryEdges": boundary,
            "nonManifoldEdges": nonmanifold, "degenerateFaces": degenerate}


# ------------------------------------------------------------------ plumbing
PART_COLLECTIONS = {
    "roof": "WM_ROOF",
    "timber": "WM_TIMBER",
    "interior": "WM_INTERIOR",
    "diorama": "WM_BASE",
    "export": "WM_EXPORT",
}


def open_base(params: dict, ctx: dict, part: str):
    """Open the base scene, drop this module's previous output, return info.

    Never overwrites ``baseBlend``: if the caller asks for the same path the
    output is redirected to ``<stem>_wm.blend`` and a warning is reported.
    """
    base = params.get("baseBlend") or ctx.get("baseBlend")
    warnings = []
    if base and not os.path.isfile(base):
        warnings.append(f"baseBlend not found, started from an empty scene: {base}")
        base = None
    WC.open_scene(base)
    deleted = WC.delete_part(part)
    scene_dir = ctx.get("sceneDir") or os.path.join(
        ctx.get("workDir") or os.getcwd(), "scene")
    out = params.get("outBlend") or ctx.get("outBlend") or os.path.join(
        scene_dir, "wenmai_scene.blend")
    if base and os.path.abspath(out) == os.path.abspath(base):
        stem, ext = os.path.splitext(out)
        out = stem + "_wm" + (ext or ".blend")
        warnings.append("outBlend pointed at baseBlend; redirected to " + out)
    return {"base": base, "out": out, "deleted": deleted, "warnings": warnings}


def save_out(out_blend: str) -> str:
    return WC.save_blend(out_blend)


# Legacy v5 object prefixes per part. The shipped v5 blend predates the
# wm_part tag, so ` delete_part ` cannot see its objects; these lists let an
# incremental run replace the previous version of *its own* part without
# touching another module's output.
#
# An entry is either a bare prefix or ``(prefix, min_top_z)``: the height guard
# is for families that are not always roof structure (INT_BEAM_MAIN is a roof
# main beam only above the eave line).
#
# Verified against the live v5 inventory with a bbox probe
# (reports/probe_above_v5.json): the old 歇山 attic survives a roof sweep as
# INT_ATTIC_L/R (z 6.55..11.04, poking straight through a new roof),
# INT_ROOF_BOARD (to 10.88), 25x INT_RAFTER_* and 14x INT_BEAM_SEC* (to 10.87),
# 6x INT_BEAM_MAIN* (to 8.02), the 24-part INT_CAISSON* and 13-part
# INT_LANTERN_CAISSON* hanging in the old attic.
LEGACY_PREFIXES = {
    "roof": ("ROOF_MAIN", "ROOF_SKIRT", "TILE_", "ROOF_Gable", "ROOF_Barge",
             "ROOF_Xuanyu", "ROOF_Ridge", "ROOF_Hip", "ROOF_Chiwen",
             "INT_ATTIC", "INT_ROOF_BOARD", "INT_RAFTER", "INT_BEAM_SEC",
             "INT_BEAM_RIDGE", "INT_CAISSON", "INT_LANTERN_CAISSON",
             ("INT_BEAM_MAIN", 6.0)),
    "interior": ("INT_", "RAIL2_", "PLAQUE_"),
    "timber": (),
    "diorama": ("SITE_",),
}


def world_bbox(obj):
    lo = [math.inf, math.inf, math.inf]
    hi = [-math.inf, -math.inf, -math.inf]
    for corner in obj.bound_box:
        w = obj.matrix_world @ Vector(corner)
        for i in range(3):
            lo[i] = min(lo[i], w[i])
            hi[i] = max(hi[i], w[i])
    return lo, hi


def objects_above(z: float, skip_tagged: bool = True) -> dict:
    """Prefix histogram of untagged meshes whose bbox top is above ``z``."""
    hist = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        if skip_tagged and obj.get("wm_part"):
            continue
        lo, hi = world_bbox(obj)
        if hi[2] <= z:
            continue
        key = obj.name.split("_")[0] + "_"
        hist[key] = hist.get(key, 0) + 1
    return hist


def replace_legacy(params: dict, part: str) -> list:
    """Delete the untagged legacy objects that belong to ``part``.

    Enabled by ``params['legacyReplace']`` (default true, because the base blend
    in this project is the pre-tag v5 scene). Names removed are returned so the
    result can report exactly what was replaced. Objects already carrying a
    ``wm_part`` are left to :func:`wm_common.delete_part`.
    """
    if not params.get("legacyReplace", True):
        return []
    entries = LEGACY_PREFIXES.get(part) or ()
    if not entries:
        return []
    removed = []
    for obj in list(bpy.data.objects):
        if obj.get("wm_part"):
            continue
        for entry in entries:
            prefix, min_top = (entry, None) if isinstance(entry, str) else entry
            if not obj.name.startswith(prefix):
                continue
            if min_top is not None:
                lo, hi = world_bbox(obj)
                if hi[2] <= float(min_top):
                    continue
            data = obj.data
            name = obj.name
            bpy.data.objects.remove(obj, do_unlink=True)
            if data is not None and getattr(data, "users", 0) == 0:
                try:
                    if isinstance(data, bpy.types.Mesh):
                        bpy.data.meshes.remove(data)
                except Exception:
                    pass
            removed.append(name)
            break
    return removed


def cut_faces_in_rect(names=(), prefixes=(), rect=(0, 0, 0, 0),
                      z_band=(0, 0)) -> dict:
    """Delete faces of the named (untagged) objects that fall inside a rect.

    The surgical alternative to deleting a legacy object whole: the v5 level-2
    floor is two full-footprint plates (``VER_Slab`` at z 3.44..3.60 and
    ``WALL_Band`` at 3.52..3.72) that also carry the exterior veranda, so
    cutting the interior footprint out of them keeps the veranda and opens the
    central void that the camera looks through.
    """
    import bmesh

    x0, x1, y0, y1 = rect
    z0, z1 = z_band
    report = {"objects": 0, "faces": 0, "names": []}
    for obj in list(bpy.data.objects):
        if obj.type != "MESH" or obj.get("wm_part"):
            continue
        if obj.name not in names and not any(obj.name.startswith(p) for p in prefixes):
            continue
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        coords = [obj.matrix_world @ v.co for v in bm.verts]
        if not coords:
            bm.free()
            continue
        cz = sum(c.z for c in coords) / len(coords)
        # A legacy plate is a coarse mesh (a handful of big quads), so a
        # face-centre test alone under-cuts: it removed 6 faces from the two v5
        # level-2 plates while the void stayed covered. Bisect along the four
        # rect boundaries first, then drop the faces that fall inside.
        for (plane_co, plane_no) in (((x0, 0.0, cz), (1.0, 0.0, 0.0)),
                                     ((x1, 0.0, cz), (1.0, 0.0, 0.0)),
                                     ((0.0, y0, cz), (0.0, 1.0, 0.0)),
                                     ((0.0, y1, cz), (0.0, 1.0, 0.0))):
            try:
                bmesh.ops.bisect_plane(
                    bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                    plane_co=plane_co, plane_no=plane_no,
                    clear_inner=False, clear_outer=False)
            except Exception:
                pass
        kill = []
        for face in bm.faces:
            w = obj.matrix_world @ face.calc_center_median()
            if x0 < w.x < x1 and y0 < w.y < y1 and z0 < w.z < z1:
                kill.append(face)
        if kill:
            bmesh.ops.delete(bm, geom=kill, context="FACES")
            bm.to_mesh(obj.data)
            obj.data.update()
            report["objects"] += 1
            report["faces"] += len(kill)
            report["names"].append(obj.name)
        bm.free()
    return report


def result(task: str, ctx: dict, params: dict, objs, artifacts, metrics,
           checks, warnings, notes) -> dict:
    """Assemble the CONTRACT section 2 result dict."""
    return {
        "ok": True,
        "task": task,
        "artifacts": artifacts,
        "objects": inventory(objs),
        "metrics": metrics,
        "checks": checks,
        "warnings": list(warnings),
        "notes": notes,
        "params": params,
    }


def snapshot_anchors(prefixes=("FRAME_",)) -> dict:
    """Capture anchor empties verbatim so an incremental run can restore them."""
    out = {}
    for obj in bpy.data.objects:
        if obj.type != "EMPTY":
            continue
        if not any(obj.name.startswith(p) for p in prefixes):
            continue
        props = {}
        for key in obj.keys():
            if key.startswith("_"):
                continue
            try:
                props[key] = obj[key]
            except Exception:
                pass
        out[obj.name] = {
            "location": [float(v) for v in obj.location],
            "rotation_euler": [float(v) for v in obj.rotation_euler],
            "scale": [float(v) for v in obj.scale],
            "empty_display_type": obj.empty_display_type,
            "empty_display_size": obj.empty_display_size,
            "props": props,
        }
    return out


def restore_anchors(snapshot: dict) -> list:
    """Recreate any anchor missing from the scene; returns the created names."""
    made = []
    for name, data in snapshot.items():
        if bpy.data.objects.get(name) is not None:
            continue
        obj = bpy.data.objects.new(name, None)
        obj.empty_display_type = data.get("empty_display_type", "PLAIN_AXES")
        obj.empty_display_size = data.get("empty_display_size", 0.3)
        obj.location = Vector(data.get("location", (0.0, 0.0, 0.0)))
        obj.rotation_euler = Euler(tuple(data.get("rotation_euler", (0.0, 0.0, 0.0))), "XYZ")
        obj.scale = Vector(data.get("scale", (1.0, 1.0, 1.0)))
        bpy.context.scene.collection.objects.link(obj)
        for key, value in (data.get("props") or {}).items():
            try:
                obj[key] = value
            except Exception:
                pass
        made.append(name)
    return made
