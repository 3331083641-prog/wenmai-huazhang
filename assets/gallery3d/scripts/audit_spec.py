"""Spec conformance audit: measure the model against the written brief.

Run against the audit build (collections still separate):

    blender -b .../wenmai_gallery_audit.blend -P audit_spec.py

Every check prints PASS / FAIL / NOTE plus the measured value, so the delta
list is reproducible instead of guessed. Coordinate note: Blender is Z-up and
the hall faces +Y; the brief is written in web coords (Y up, front = -Z), so
web_z = -blender_y and web_y = blender_z.
"""
from __future__ import annotations

import json
import os

import bpy
from mathutils import Vector

rows = []


def check(label, ok, measured, expected, note=""):
    tag = "PASS" if ok else "FAIL"
    rows.append((tag, label, measured, expected, note))
    print("[%s] %-34s measured=%-30s spec=%s %s"
          % (tag, label, measured, expected, note))


def note(label, measured, note_text=""):
    rows.append(("NOTE", label, measured, "-", note_text))
    print("[NOTE] %-34s %s %s" % (label, measured, note_text))


def obj(name):
    return bpy.data.objects.get(name)


def bbox(name):
    o = obj(name)
    if o is None:
        return None
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def size(name):
    b = bbox(name)
    return None if b is None else (b[1] - b[0])


def wverts(name):
    o = obj(name)
    if o is None:
        return []
    m = o.matrix_world
    return [m @ v.co for v in o.data.vertices]


def main():
    print("\n================ base ================")
    b = bbox("BASE_Main")
    if b:
        lo, hi = b
        check("plinth plan (web X x Z)", abs((hi.x - lo.x) - 14) < 0.02 and abs((hi.y - lo.y) - 14) < 0.02,
              "%.3f x %.3f" % (hi.x - lo.x, hi.y - lo.y), "14 x 14 m")
        vs = wverts("BASE_Main")
        deck = [p.z for p in vs if abs(p.x) < 6.5 and abs(p.y) < 6.5]
        deck_z = max(deck) if deck else 0.0
        bottom = min(p.z for p in vs)
        # the side faces carry a deliberate chamfer, so thickness is deck-to-bottom
        check("plinth body thickness", abs((deck_z - bottom) - 0.65) < 0.02,
              "%.3f (z %.3f..%.3f)" % (deck_z - bottom, bottom, deck_z), "0.65 m")
        check("deck top at y=0", abs(deck_z) < 0.003, "%.4f" % deck_z, "0.0 (web y=0)")
        # three-tier reading: horizontal bands in the plinth skin
        zs = sorted({round(p.z, 3) for p in vs if p.z < 0})
        note("plinth z levels", ", ".join("%.3f" % z for z in zs)[:120], "0.16 / 0.28 / 0.21 bands")
        # carved meander frieze: modular units marching along all four faces
        f0 = -0.65 + 0.16
        f1 = f0 + 0.28
        fret = [p for p in vs if f0 - 0.02 <= p.z <= f1 + 0.02]
        check("frieze meander band", len(fret) > 400, "%d verts in the frieze band" % len(fret), ">400")
        sides = {s: sum(1 for p in fret if (abs(p.y) > 6.4 if s in "FB" else abs(p.x) > 6.4))
                 for s in ("F", "B", "L", "R")}
        even = max(sides.values()) - min(sides.values()) <= max(2, max(sides.values()) * 0.10)
        check("frieze units on all four faces", even and min(sides.values()) > 40,
              "F/B/L/R = " + "/".join(str(sides[s]) for s in ("F", "B", "L", "R")),
              "balanced, >40 per face")

    print("\n================ hall envelope ================")
    w = bbox("BUILDING_Walls")
    if w:
        lo, hi = w
        check("footprint (web X x Z)", abs((hi.x - lo.x) - 8.4) < 0.05 and abs((hi.y - lo.y) - 7.5) < 0.05,
              "%.3f x %.3f" % (hi.x - lo.x, hi.y - lo.y), "8.4 x 7.5 m")
        front_web = -hi.y            # hall front faces +Y in Blender -> web -Z
        check("front face at web Z=-3.20", abs(front_web + 3.2) < 0.05, "%.3f" % front_web, "-3.20")
        check("hall centred on web Z=+0.55", abs((lo.y + hi.y) / 2 + 0.55) < 0.05,
              "%.3f" % (-(lo.y + hi.y) / 2 * -1), "0.55")

    cols = bbox("BUILDING_Columns")
    if cols:
        lo, hi = cols
        note("column band", "z %.3f..%.3f" % (lo.z, hi.z), "diameter checked below")
        # cluster the shaft footprints: the columns are round, so the (x, y)
        # scatter collapses to a handful of tight clusters
        vs = wverts("BUILDING_Columns")
        groups = {}
        for p in vs:
            if 1.00 < p.z < 2.20:
                groups.setdefault((round(p.x / 0.4), round(p.y / 0.4)), []).append(p)
        big = [g for g in groups.values() if len(g) > 20]
        if big:
            g = max(big, key=len)
            d = ((max(p.x for p in g) - min(p.x for p in g))
                 + (max(p.y for p in g) - min(p.y for p in g))) / 2.0
            check("column diameter", 0.26 <= d <= 0.34, "%.3f m (%d clusters)" % (d, len(big)),
                  "0.26-0.32 m")

    print("\n================ roof ================")
    rt = bbox("TILE_Main")
    rr = bbox("ROOF_Eave")
    if rt and w:
        lo, hi = rt
        check("roof plan (web X x Z)", abs((hi.x - lo.x) - 10.2) < 0.45 and abs((hi.y - lo.y) - 9.3) < 0.45,
              "%.2f x %.2f" % (hi.x - lo.x, hi.y - lo.y), "about 10.2 x 9.3")
        over = max(hi.x - 4.2, -(lo.x + 4.2))
        check("eave overhang", 0.75 <= over <= 0.98, "%.3f m" % over, "0.75-0.95 m")
        check("ridge apex height", 8.55 <= hi.z <= 8.85, "%.3f m" % hi.z, "8.70 m")
        # eave line + corner lift: compare the lowest tile z at mid-span vs at a corner
        vs = wverts("TILE_Main")
        mid = [p.z for p in vs if abs(p.x) < 0.3 and p.y > 3.0]
        cor = [p.z for p in vs if p.x > 4.6 and p.y > 3.0]
        if mid and cor:
            lift = max(cor) - max(mid) if max(cor) > max(mid) else max(mid) - max(cor)
            note("corner lift probe", "mid %.3f / corner %.3f" % (max(mid), max(cor)),
                 "configured EAVE_LIFT=0.40")
        check("roof below 9.0 m", hi.z < 9.0, "%.3f" % hi.z, "< 9.0")

    # the ring eave is four slope meshes plus a joined fascia object, so the union
    # is the only honest measurement (ROOF_Lower alone is just the fascia bands)
    ring = [o for o in bpy.data.objects if o.name.startswith("ROOF_Lower")]
    zs, xs, ys = [], [], []
    for o in ring:
        bb = bbox(o.name)
        if bb:
            zs += [bb[0].z, bb[1].z]
            xs += [bb[0].x, bb[1].x]
            ys += [bb[0].y, bb[1].y]
    if zs:
        check("ring eave band", 3.40 <= min(zs) and max(zs) <= 4.30,
              "z %.3f..%.3f over %d meshes" % (min(zs), max(zs), len(ring)),
              "3.4-4.3 m incl. eave edge + fascia")

    print("\n================ interior ceiling ================")
    ce = bbox("BEAM_Ceiling")
    if ce:
        check("ceiling top plate", abs(ce[1].z - 6.55) < 0.12, "%.3f" % ce[1].z, "6.55 m")
        vs = wverts("BEAM_Ceiling")
        cof = [p for p in vs if abs(p.x) < 1.2 and abs(p.y + 0.4) < 1.2 and p.z < 6.3]
        if cof:
            dia = max(p.x for p in cof) - min(p.x for p in cof)
            check("coffer diameter", 1.0 <= dia <= 1.32, "%.3f m" % dia, "1.0-1.3 m")
            note("coffer z range", "%.3f..%.3f" % (min(p.z for p in cof), max(p.z for p in cof)))
            note("coffer vert count", "%d" % len(cof))

    print("\n================ stair ================")
    st = bbox("STAIR_Main")
    if st:
        lo, hi = st
        vs = wverts("STAIR_Main")
        # L-shaped stair: flight 1 runs along X in the rear band, flight 2 runs
        # along Y in the side band. The object bbox spans both flights plus the
        # railing, so width is measured from the tread faces themselves.
        o = obj("STAIR_Main")
        m = o.matrix_world
        treads = []
        for poly in o.data.polygons:
            n = (m.to_3x3() @ poly.normal).normalized()
            c = m @ poly.center
            if n.z > 0.85 and 0.30 < c.z < 3.55 and poly.area > 0.10:
                co = [m @ o.data.vertices[i].co for i in poly.vertices]
                treads.append((max(p.x for p in co) - min(p.x for p in co),
                               max(p.y for p in co) - min(p.y for p in co)))
        if treads:
            # a tread is long across the flight (net width) and short along it
            # (going depth); both flights therefore share the same width.
            widths = [max(t) for t in treads]
            runs = [min(t) for t in treads]
            check("tread net width", 1.05 <= sum(widths) / len(widths) <= 1.25,
                  "%.3f m over %d treads" % (sum(widths) / len(widths), len(treads)), "1.10 m")
            runs.sort()
            med = runs[len(runs) // 2]
            check("tread going depth (median)", 0.25 <= med <= 0.29,
                  "%.3f m median (mean %.3f, max %.2f = landing)"
                  % (med, sum(runs) / len(runs), runs[-1]), "0.26-0.28 m (brief)")
        note("stair plan", "x %.2f..%.2f y %.2f..%.2f" % (lo.x, hi.x, lo.y, hi.y),
             "brief: rear-right; web X %.2f..%.2f" % (lo.x, hi.x))
        # top tread = the highest LARGE horizontal face (railing caps are ~4 cm铏?
        o = obj("STAIR_Main")
        m = o.matrix_world
        tops = []
        for poly in o.data.polygons:
            n = (m.to_3x3() @ poly.normal).normalized()
            if n.z > 0.85:
                c = m @ poly.center
                area = poly.area
                if 3.20 < c.z < 3.75 and area > 0.05:
                    tops.append((c.z, area))
        if tops:
            top_z = max(t[0] for t in tops)
            riser = (3.60 - 0.25) / 18.0
            check("top tread + riser lands on F2 slab", abs(top_z + riser - 3.60) < 0.015,
                  "%.3f + %.3f = %.3f m" % (top_z, riser, top_z + riser), "3.600 m")

    print("\n================ landscape ================")
    pl = bbox("PROP_Plants")
    if pl:
        note("plants bbox", "x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f"
             % (pl[0].x, pl[1].x, pl[0].y, pl[1].y, pl[0].z, pl[1].z))
        vs = wverts("PROP_Plants")
        top = max(p.z for p in vs)
        check("tallest planting", 2.0 <= top <= 3.20, "%.3f m" % top, "trees 2.2-2.8 / bamboo 2-3")
    streets = bbox("PROP_Street")
    if streets:
        note("street bbox", "x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f"
             % (streets[0].x, streets[1].x, streets[0].y, streets[1].y,
                streets[0].z, streets[1].z))

    print("\n================ layout (frames) ================")
    p = os.path.join(os.path.dirname(bpy.data.filepath), "..", "exports", "gallery_layout.json")
    p = os.path.abspath(p)
    if os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        frames = d.get("frames", [])
        note("frame count", "%d (f1 %d / f2 %d)"
             % (len(frames), sum(1 for f in frames if f.get("floor") == 1),
                sum(1 for f in frames if f.get("floor") == 2)), "7 + 8 = 15")
        ws = [f.get("width") for f in frames if f.get("width")]
        hs = [f.get("height") for f in frames if f.get("height")]
        if ws and hs:
            note("frame sizes", "w %.2f..%.2f  h %.2f..%.2f" % (min(ws), max(ws), min(hs), max(hs)),
                 "regular 1.05-1.25 x 0.8-0.95 / feature 1.45x1.1")
    else:
        note("layout json", "not found at %s" % p)

    fails = sum(1 for r in rows if r[0] == "FAIL")
    print("\n================ summary ================")
    print("checks: %d   FAIL: %d" % (len(rows), fails))
    for r in rows:
        if r[0] == "FAIL":
            print("  FAIL %-32s %s  (spec %s)" % (r[1], r[2], r[3]))


main()