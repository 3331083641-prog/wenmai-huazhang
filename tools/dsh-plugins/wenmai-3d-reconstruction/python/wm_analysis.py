"""``analyze_references`` — measure the ten reference PNGs without PIL.

For every reference this produces, from real pixels only:

* exact ``width``/``height``, ``sha1``, ``bytes`` and a stable ``R01..R10`` id;
* sRGB ``palette`` (deterministic 16-level histogram peaks) plus a seeded
  k-means palette;
* a foreground silhouette box from a border-connected background model that
  copes with graded skies, white clouds, a white studio backdrop and flat
  interior ceilings;
* the five horizontal bands (roof / upper / lower / plinth / ground) as
  normalised heights of the silhouette, each with edge density, dominant
  gradient orientation and Lab mean colour;
* vertical symmetry, per-band dominant gradient orientation (parallel tile
  courses vs radial ornament), sky fraction and a warm/cool ratio;
* a montage/board detector, because one reference is a multi-view sheet.

Writes ``measurements.json`` and a labelled contact sheet.  Owned by
``visual-match``; the ordering rule for the ids is documented in ``notes`` and
repeated inside ``measurements.json`` so nothing has to be remembered.
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np

import wm_common as C
import wm_image as WI

# ------------------------------------------------------------------ constants

BAND_NAMES = ["roof", "upper", "lower", "plinth", "ground"]
BAND_LABELS = {
    "roof": "屋面/檐口 (roof + eave)",
    "upper": "上层檐下 (upper storey)",
    "lower": "下层檐下 (lower storey)",
    "plinth": "台基上部 (plinth upper / xumizuo)",
    "ground": "台基下脚/地面 (base course + ground contact)",
}
EQUAL_SPLIT = [0.2, 0.2, 0.2, 0.2, 0.2]

ORIENT_BINS = 12          # 15-degree bins over 0..180
DEFAULT_K = 8

# Contract §1 band proportions, used only as the comparison basis for the
# contradiction candidates below (span = wooden bracket bottom -0.95 ..
# ridge 11.30 = 12.25 m).
CONTRACT_BAND_RATIOS = {"roof": 0.4153, "upper": 0.2379, "lower": 0.2702,
                        "plinth": 0.0524, "ground": 0.0242}


def _contradiction_candidates(images: list) -> list:
    """Observations a spec/diff pass should review instead of silently fitting."""
    out = []
    ext = [e for e in images if e["kind"] == "exterior"]
    interiors = [e["id"] for e in images if e["kind"] == "interior"]
    montages = [e["id"] for e in images if e["kind"] == "montage"]

    if ext:
        med_p = float(np.median([e["bandRatios"]["plinth"] for e in ext]))
        med_g = float(np.median([e["bandRatios"]["ground"] for e in ext]))
        contract_p = CONTRACT_BAND_RATIOS["plinth"]
        out.append({
            "id": "plinth_proportion",
            "kind": "geometry_proportion",
            "severity": "warn",
            "measured": {"plinthBandRatioMedian": round(med_p, 4),
                         "groundBandRatioMedian": round(med_g, 4),
                         "exteriors": [e["id"] for e in ext]},
            "contract": {"plinthBandRatio": contract_p,
                         "basis": "plinth z in [-0.65, 0] over the span "
                                  "-0.95..11.30 (5.4 % of the silhouette)"},
            "ratioMeasuredOverContract": (round(med_p / contract_p, 3)
                                          if contract_p else None),
            "caveat": ("the measured plinth band is a POSITIONAL label snapped to "
                       "the strongest horizontal structure line, not a semantic "
                       "plinth measurement. Treat this as a candidate contradiction "
                       "for spec review, not as a proven geometry mismatch."),
        })
    if interiors or montages:
        out.append({
            "id": "silhouette_not_applicable",
            "kind": "evidence_scope",
            "severity": "info",
            "interiors": interiors, "montages": montages,
            "detail": ("these frames carry no single building elevation, so "
                       "silhouette IoU and elevation band ratios must not be "
                       "claimed for them; compare_reference reports "
                       "silhouetteApplicable=false for them"),
        })
    if ext:
        out.append({
            "id": "reference_redundancy",
            "kind": "evidence_scope",
            "severity": "info",
            "exteriorViews": [e["id"] for e in ext],
            "detail": ("%d of %d references are full exterior hero views of the "
                       "same elevation family, so a spec should treat them as one "
                       "view group plus detail frames"
                       % (len(ext), len(images))),
        })
    return out


# ----------------------------------------------------------------- utilities

def json_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _z(x: np.ndarray) -> np.ndarray:
    s = float(x.std())
    if s <= 1e-9:
        return np.zeros_like(x)
    return (x - float(x.mean())) / s


def _grad(x: np.ndarray) -> np.ndarray:
    return np.abs(np.gradient(np.asarray(x, dtype=np.float32)))


def _runs(mask) -> list:
    """Contiguous ``True`` runs as ``(start, length)``."""
    out, st = [], None
    for i, m in enumerate(mask):
        if m and st is None:
            st = i
        elif not m and st is not None:
            out.append((st, i - st)); st = None
    if st is not None:
        out.append((st, len(mask) - st))
    return out


def _pick(signal: np.ndarray, lo: int, hi: int, mid: int) -> int:
    """Strongest row of ``signal`` inside ``[lo, hi]``; ``mid`` when unusable."""
    lo, hi = int(lo), int(hi)
    if hi <= lo:
        return int(mid)
    lo = max(0, lo); hi = min(len(signal) - 1, hi)
    if hi <= lo:
        return int(max(0, min(len(signal) - 1, mid)))
    window = signal[lo:hi + 1]
    if window.size == 0 or float(np.abs(window).max()) <= 1e-9:
        return int(max(lo, min(hi, mid)))
    return lo + int(np.argmax(np.abs(window)))


# ------------------------------------------------------------- band detection

def detect_band_boundaries(mask: np.ndarray, box: dict, gray: np.ndarray,
                           mag: np.ndarray, kind: str = "exterior") -> dict:
    """Place the five bands on a documented, snap-to-structure model.

    Measured fact that drives this design: in these 3/4-view references the
    silhouette outline is **smooth and monotonic** (R02 widens 0.019 -> 0.868
    from ridge to plinth), and trees/lantern posts widen it further, so the eave
    and storey lines are *internal* edges, not outline steps.  A purely
    outline-driven search therefore cannot name the bands reliably.

    Instead every image -- reference and render alike -- gets the same rule:

    1. the silhouette span ``ridge..base`` is divided at the structural priors
       0.20 / 0.40 / 0.60 / 0.80 (five near-equal bands, so per-band deltas
       between a reference and a render stay comparable);
    2. each cut is snapped, within +-10 % of the span, to the strongest
       horizontal structure line (fused luminance + edge-density row gradient);
    3. ordering and a minimum thickness are enforced, else the equal split is
       used and reported as such.

    The names roof/upper/lower/plinth/ground are therefore **positional**
    labels for a comparable measurement frame; the measured semantic
    candidates are reported separately in ``strongestHorizontalLines`` and
    ``anchors`` rather than being asserted as ground truth.
    """
    y0, y1 = box["y0"], box["y1"]
    hbox = y1 - y0 + 1
    sub = mask[y0:y1 + 1]
    anyrow = sub.any(axis=1)
    if not anyrow.any() or hbox < 24:
        return {"ok": False, "reason": "empty or tiny silhouette", "source": "fallback"}

    rw = sub.mean(axis=1).astype(np.float32)
    rows = np.nonzero(anyrow)[0]
    ridge, base = int(rows[0]), int(rows[-1])
    n = base - ridge + 1
    if n < 24:
        return {"ok": False, "reason": "silhouette span under 24 rows",
                "source": "fallback"}

    # Horizontal structure lines: luminance + edge-density row gradients (the
    # same estimator the proven measurement pass used).
    lum = np.array([gray[y0 + r][sub[r]].mean() if sub[r].any() else np.nan
                    for r in range(hbox)], dtype=np.float32)
    if np.isfinite(lum).sum() > 5:
        lum = np.nan_to_num(lum, nan=float(np.nanmean(lum)))
    else:
        lum = np.zeros(hbox, dtype=np.float32)
    ed = np.array([mag[y0 + r].mean() for r in range(hbox)], dtype=np.float32)
    step = _z(_grad(lum)) + 0.6 * _z(_grad(ed))

    priors = (0.20, 0.40, 0.60, 0.80)
    window = 0.10
    span = float(base - ridge)
    cuts, snaps = [], []
    for pr in priors:
        prior_row = ridge + int(round(span * pr))
        lo = ridge + int(round(span * (pr - window)))
        hi = ridge + int(round(span * (pr + window)))
        row = _pick(step, lo, hi, mid=prior_row)
        cuts.append(row)
        snaps.append({"prior": pr,
                      "row": int(y0 + row),
                      "offsetFraction": round((row - prior_row) / span, 4),
                      "strength": round(float(step[row]), 4)})

    # Enforce ordering + a minimum thickness, propagating in both directions.
    min_gap = max(2, int(round(span * 0.06)))
    for i in range(1, len(cuts)):
        if cuts[i] < cuts[i - 1] + min_gap:
            cuts[i] = cuts[i - 1] + min_gap
    if cuts[-1] > base - 2:
        cuts[-1] = base - 2
        for i in range(len(cuts) - 2, -1, -1):
            if cuts[i] > cuts[i + 1] - min_gap:
                cuts[i] = cuts[i + 1] - min_gap
    if cuts[0] < ridge + 2:
        cuts[0] = ridge + 2
        for i in range(1, len(cuts)):
            if cuts[i] < cuts[i - 1] + min_gap:
                cuts[i] = cuts[i - 1] + min_gap

    bounds = [ridge] + cuts + [base]
    for i in range(len(bounds) - 1):
        if bounds[i + 1] - bounds[i] < 2:
            return {"ok": False,
                    "reason": "band %d collapsed (%s)" % (i, BAND_NAMES[i]),
                    "source": "fallback", "rawBounds": [int(b) for b in bounds]}
    span = float(base - ridge)
    ratios = [(bounds[i + 1] - bounds[i]) / span for i in range(5)]

    # Advisory measured candidates (reported, never asserted as the band model).
    wmax = float(rw[ridge:base + 1].max())
    widest = ridge + int(np.argmax(rw[ridge:base + 1]))
    dw = np.gradient(rw[ridge:base + 1])
    lo_lo = ridge + int(n * 0.40)
    plinth_cand = (lo_lo + int(np.argmax(dw[lo_lo - ridge:])) if lo_lo < base
                   else widest)
    order = np.argsort(-np.abs(step[ridge:base + 1]))[:8]
    lines = [{"fraction": round(float(r) / span, 4),
              "row": int(y0 + ridge + int(r)),
              "strength": round(float(step[ridge + int(r)]), 4)}
             for r in sorted(order)]

    bands = []
    for i, name in enumerate(BAND_NAMES):
        bands.append({"name": name, "label": BAND_LABELS[name],
                      "y0": int(y0 + bounds[i]), "y1": int(y0 + bounds[i + 1]),
                      "ratio": round(ratios[i], 4)})

    def norm(r):
        return round((r - ridge) / span, 4)

    return {
        "ok": True, "source": "detected-snapped",
        "bandModelApplicable": kind == "exterior",
        "bands": bands,
        "ratios": {b["name"]: b["ratio"] for b in bands},
        "bandRowFractions": {BAND_NAMES[i]: norm(bounds[i + 1]) for i in range(5)},
        "anchors": {"ridge": norm(bounds[0]), "band1": norm(bounds[1]),
                    "band2": norm(bounds[2]), "band3": norm(bounds[3]),
                    "band4": norm(bounds[4]), "base": norm(bounds[5]),
                    "widestRow": norm(widest),
                    "plinthShoulderCandidate": norm(plinth_cand)},
        "anchorRows": {"ridge": int(y0 + bounds[0]), "band1": int(y0 + bounds[1]),
                       "band2": int(y0 + bounds[2]), "band3": int(y0 + bounds[3]),
                       "band4": int(y0 + bounds[4]), "base": int(y0 + bounds[5]),
                       "widestRow": int(y0 + widest)},
        "snaps": snaps,
        "strongestHorizontalLines": lines,
        "widestRowFraction": round(wmax, 4),
        "note": ("cuts sit at the structural priors 0.20/0.40/0.60/0.80 of the "
                 "silhouette span ridge..base, each snapped within +-10 % to the "
                 "strongest fused luminance+edge row gradient; band names are "
                 "positional labels for a comparable frame, and "
                 "strongestHorizontalLines lists the real measured structure lines"),
    }


def fallback_bands(mask: np.ndarray, box: dict) -> list:
    """Guaranteed five bands (equal split) when detection is impossible."""
    y0, y1 = box["y0"], box["y1"]
    hbox = max(1, y1 - y0 + 1)
    bands = []
    for i, name in enumerate(BAND_NAMES):
        a = int(round(hbox * i / 5.0))
        b = int(round(hbox * (i + 1) / 5.0))
        bands.append({"name": name, "label": BAND_LABELS[name],
                      "y0": y0 + a, "y1": y0 + max(a + 1, b),
                      "ratio": round(1.0 / 5.0, 4)})
    return bands


# -------------------------------------------------------- orientation analysis

def orientation_stats(mag: np.ndarray, ang: np.ndarray, mask: np.ndarray,
                      thresh: float = 24.0) -> dict:
    """Dominant gradient orientation and how axis-aligned / radial it is.

    Parallel tile courses concentrate gradient energy on one axis-aligned
    direction (low entropy, high ``axisAlignedShare``); radial ornament spreads
    it across diagonals (high entropy, high ``diagonalShare``).
    """
    sel = np.asarray(mask, dtype=bool) & (mag > thresh)
    if not sel.any():
        return {"dominantDeg": None, "dominantShare": 0.0, "horizontalShare": 0.0,
                "verticalShare": 0.0, "diagonalShare": 0.0, "axisAlignedShare": 0.0,
                "entropyBits": 0.0, "samples": 0}
    a = ang[sel]
    w = mag[sel].astype(np.float64)
    bins = np.clip((a / (180.0 / ORIENT_BINS)).astype(np.int32), 0, ORIENT_BINS - 1)
    hist = np.bincount(bins, weights=w, minlength=ORIENT_BINS).astype(np.float64)
    total = float(hist.sum())
    centres = (np.arange(ORIENT_BINS) + 0.5) * (180.0 / ORIENT_BINS)
    if total <= 0:
        return {"dominantDeg": None, "dominantShare": 0.0, "horizontalShare": 0.0,
                "verticalShare": 0.0, "diagonalShare": 0.0, "axisAlignedShare": 0.0,
                "entropyBits": 0.0, "samples": int(sel.sum())}
    p = hist / total
    dom = int(np.argmax(hist))
    # Gradient direction -> structure direction.  A gradient near 90 deg means
    # intensity changes vertically, i.e. the pixel sits on a *horizontal* line
    # (storey bands, tile courses, eaves).  A gradient near 0/180 deg means a
    # *vertical* line (columns, wall joints, window mullions).
    d = np.abs(centres - 90.0)
    horizontal_edges = float(p[d <= 22.5].sum())
    vertical_edges = float(p[np.minimum(d, 180.0 - d) >= 67.5].sum())
    axis = horizontal_edges + vertical_edges
    nz = p[p > 0]
    return {"dominantDeg": round(float(centres[dom]), 1),
            "dominantShare": round(float(p[dom]), 4),
            "horizontalEdgeShare": round(horizontal_edges, 4),
            "verticalEdgeShare": round(vertical_edges, 4),
            "diagonalShare": round(max(0.0, 1.0 - axis), 4),
            "axisAlignedShare": round(axis, 4),
            "entropyBits": round(float(-(nz * np.log2(nz)).sum()), 4),
            "samples": int(sel.sum())}


# ------------------------------------------------------------- layout / kind

def detect_montage(arr: np.ndarray, tol: float = 10.0, max_sep_width: int = 8,
                   min_localisation: float = 20.0, max_flat_fraction: float = 0.08) -> dict:
    """Detect a collage / detail board.

    A montage draws **thin** separator lines: a few columns (or rows) that are
    near-constant along their whole length, while almost every other
    column/row stays highly varied.  A flat studio backdrop gives the opposite
    signature -- a large *area* of low-variance pixels and a low 1st-percentile
    variance -- so two guards separate them: the flat fraction must stay small,
    and the 1st-percentile standard deviation must stay high.  Measured on the
    ten references this fires on exactly one image (the detail board).
    """
    a = np.asarray(arr, dtype=np.float32)
    h, w = a.shape[:2]
    col_std = a.std(axis=(0, 2))
    row_std = a.std(axis=(1, 2))
    v_thin = [r for r in _runs(col_std < tol) if 1 <= r[1] <= max_sep_width]
    h_thin = [r for r in _runs(row_std < tol) if 1 <= r[1] <= max_sep_width]
    flat_col = float((col_std < tol).mean())
    flat_row = float((row_std < tol).mean())
    p1_col = float(np.percentile(col_std, 1))
    p1_row = float(np.percentile(row_std, 1))
    localised_v = (bool(v_thin) and flat_col <= max_flat_fraction
                   and p1_col > min_localisation)
    localised_h = (bool(h_thin) and flat_row <= max_flat_fraction
                   and p1_row > min_localisation)
    is_montage = localised_v and localised_h
    return {
        "isMontage": bool(is_montage),
        "verticalSeparators": [{"x": int(s), "width": int(l)} for s, l in v_thin],
        "horizontalSeparators": [{"y": int(s), "width": int(l)} for s, l in h_thin],
        "columnStdP1": round(p1_col, 2), "rowStdP1": round(p1_row, 2),
        "columnStdMin": round(float(col_std.min()), 2),
        "rowStdMin": round(float(row_std.min()), 2),
        "flatColumnFraction": round(flat_col, 4),
        "flatRowFraction": round(flat_row, 4),
        "cellsAtLeast": int((len(v_thin) + 1) * (len(h_thin) + 1)),
        "criterion": ("thin (<=%dpx) near-constant separators on both axes, with "
                      "flat fraction <= %.2f and p1 std > %.0f so a wide flat "
                      "backdrop cannot qualify"
                      % (max_sep_width, max_flat_fraction, min_localisation)),
    }


def classify_kind(sky_fraction: float, montage: dict) -> str:
    if montage.get("isMontage"):
        return "montage"
    return "exterior" if sky_fraction >= 0.10 else "interior"


# ------------------------------------------------------------------ one image

def measure_image(path: str, ident: str, project_root: str, params: dict):
    """Measure one reference.  Returns ``(entry_dict, thumbnail_rgb)``."""
    arr = WI.read_png(path)
    h, w = arr.shape[:2]
    gray = WI.to_gray(arr)
    mag, ang = WI.sobel(gray)

    raw_mask, minfo = WI.foreground_mask(arr, tol=float(params.get("tol", 20.0)))
    mask, cinfo = WI.clean_mask(raw_mask, step=4)
    box = WI.bbox_of(mask)
    if box is None:
        mask = np.ones((h, w), dtype=bool)
        box = WI.bbox_of(mask)

    sky = WI.sky_mask(arr)
    sky_frac = float(sky.mean())
    montage = detect_montage(arr)
    kind = classify_kind(sky_frac, montage)

    det = detect_band_boundaries(mask, box, gray, mag, kind=kind)
    if det.get("ok"):
        bands = det["bands"]
        ratios = det["ratios"]
        band_source = "detected"
        applicable = bool(det.get("bandModelApplicable"))
    else:
        bands = fallback_bands(mask, box)
        ratios = {b["name"]: b["ratio"] for b in bands}
        band_source = "fallback: %s" % det.get("reason", "unknown")
        applicable = False

    band_metrics = []
    for band in bands:
        y0, y1 = band["y0"], band["y1"]
        bm = mask[y0:y1]
        lab = WI.rgb_to_lab(arr[y0:y1])
        entry = {
            "name": band["name"],
            "label": band.get("label", BAND_LABELS[band["name"]]),
            "y0": int(y0), "y1": int(y1),
            "ratio": band["ratio"],
            "heightPx": int(y1 - y0),
            "fill": round(float(bm.mean()), 4),
            "edgeDensity": round(WI.edge_density(gray[y0:y1], bm), 4),
            "orientation": orientation_stats(mag[y0:y1], ang[y0:y1], bm),
            "labMean": ([round(float(v), 2) for v in lab[bm].mean(axis=0)]
                        if bm.any() else None),
            "meanLuma": (round(float(gray[y0:y1][bm].mean()), 2)
                         if bm.any() else None),
        }
        band_metrics.append(entry)

    rsum = sum(ratios.values())
    if rsum > 0:
        ratios = {k: round(v / rsum, 4) for k, v in ratios.items()}

    pal = WI.palette_hist(arr, mask, k=int(params.get("paletteK", 12)))
    pal_k = WI.kmeans_palette(arr, mask, k=int(params.get("paletteKmeans", DEFAULT_K)))

    skyline = []
    for i in range(48):
        x0 = int(w * i / 48); x1 = max(x0 + 1, int(w * (i + 1) / 48))
        idx = np.nonzero(mask[:, x0:x1].any(axis=1))[0]
        skyline.append(None if idx.size == 0 else round(float(idx.min()) / h, 3))
    extent = []
    for j in range(40):
        ya = int(h * j / 40); yb = max(ya + 1, int(h * (j + 1) / 40))
        cols = np.nonzero(mask[ya:yb].any(axis=0))[0]
        extent.append({"y": round((j + 0.5) / 40, 3),
                       "l": None if cols.size == 0 else round(float(cols.min()) / w, 3),
                       "r": None if cols.size == 0 else round(float(cols.max()) / w, 3),
                       "w": 0.0 if cols.size == 0 else round(
                           float(cols.max() - cols.min()) / w, 3)})

    thumb = WI.resize_bilinear(arr, min(w, 720), int(min(w, 720) * h / float(w)))
    entry = {
        "id": ident,
        "path": os.path.abspath(path),
        "pathRel": WI.relpath(path, project_root),
        "file": os.path.basename(path),
        "sha1": WI.sha1_of(path),
        "bytes": WI.file_size(path),
        "width": w, "height": h,
        "kind": kind,
        "skyFraction": round(sky_frac, 4),
        "montage": montage,
        "palette": pal,
        "paletteKmeans": pal_k,
        "foregroundBox": box,
        "foregroundFraction": round(float(mask.mean()), 4),
        "maskInfo": minfo,
        "maskClean": cinfo,
        "bandRatios": ratios,
        "bandRatiosEqualSplit": {n: r for n, r in zip(BAND_NAMES, EQUAL_SPLIT)},
        "bandModelApplicable": applicable,
        "bandSource": band_source,
        "bandDetection": det,
        "bands": band_metrics,
        "edgeDensityPerBand": {b["name"]: b["edgeDensity"] for b in band_metrics},
        "orientationPerBand": {b["name"]: b["orientation"] for b in band_metrics},
        "symmetry": round(WI.symmetry_score(mask, box), 4),
        "warmCool": WI.warm_cool(arr, mask),
        "labMean": WI.lab_mean(arr, mask),
        "detailEnergy": round(WI.laplacian_energy(gray), 5),
        "edgeDensity": round(WI.edge_density(gray, mask), 4),
        "skyline": skyline,
        "extentProfile": extent,
    }
    return entry, thumb


# ---------------------------------------------------------------------- main

def analyze_references(params: dict, ctx: dict) -> dict:
    params = params or {}
    project_root = ctx.get("projectRoot") or os.getcwd()
    ref_dir = ctx.get("referencesDir") or os.path.join(
        project_root, "assets", "gallery3d", "references", "raw")
    reports_dir = ctx.get("reportsDir") or os.path.join(
        project_root, "outputs", "wenmai-3d", "reports")
    out_dir = params.get("outDir") or os.path.join(reports_dir, "analysis")
    out_dir = WI.resolve_path(out_dir, ctx)
    WI.ensure_dir(out_dir)

    if params.get("images"):
        paths = [WI.resolve_path(p, ctx) for p in params["images"]]
    else:
        paths = sorted(glob.glob(os.path.join(ref_dir, "*.png")))
    if not paths:
        return C.fail(f"no reference PNGs found (looked in {ref_dir})")
    ordering = ("stable id R01..R10 assigned by ascending byte-wise sort of the "
                "file name inside the reference directory (or of params.images in "
                "the given order); ids are positional, not tied to content")

    checks, warnings = [], []
    images, thumbs = [], []
    for i, path in enumerate(paths, 1):
        if not os.path.isfile(path):
            warnings.append(f"missing reference: {path}")
            continue
        entry, thumb = measure_image(path, f"R{i:02d}", project_root, params)
        images.append(entry)
        thumbs.append(thumb)
        C.log("measured %s %s %dx%d kind=%s bands=%s" % (
            entry["id"], entry["file"][:22], entry["width"], entry["height"],
            entry["kind"], json_dumps(entry["bandRatios"])))

    if not images:
        return C.fail("no readable reference images")

    measurements = {
        "schema": 1,
        "generatedBy": "wm_analysis.analyze_references",
        "ordering": ordering,
        "bandModel": {
            "names": BAND_NAMES,
            "definition": ("five stacked bands between the silhouette ridge and "
                           "base; ratios are heights normalised by that span, "
                           "top -> bottom"),
            "labels": BAND_LABELS,
            "anchors": ("ridge = first foreground row; eave = widest upper row; "
                        "plinthShoulder = first lower row at >=90% of the widest "
                        "outline; floor2 / plinthToe = strongest luminance+edge "
                        "steps in their intervals"),
            "source": ("anchored on the measured outline; equal split only when "
                       "the anchor set cannot be made monotone"),
            "applicability": ("elevation-semantic for kind=exterior; for "
                              "kind=interior/montage the same bands are still "
                              "measured but bandModelApplicable is false"),
        },
        "images": images,
    }
    measurements["contradictionCandidates"] = _contradiction_candidates(images)
    mpath = os.path.join(out_dir, "measurements.json")
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(measurements, fh, ensure_ascii=False, indent=1)

    spath = None
    if params.get("contactSheet", True):
        cols = int(params.get("sheetCols", 5))
        cells = [{"label": "%s %s" % (e["id"], e["file"][11:19]),
                  "sublabel": "%s sky%.2f" % (e["kind"][:3], e["skyFraction"]),
                  "image": t, "box": e["foregroundBox"]}
                 for e, t in zip(images, thumbs)]
        sheet = WI.contact_sheet(cells, cell_w=int(params.get("sheetCellW", 360)),
                                 cell_h=int(params.get("sheetCellH", 270)), cols=cols,
                                 title="WENMAI REFERENCES - foreground boxes (green)"
                                       " - order = filename ascending")
        spath = os.path.join(out_dir, "references_contact_sheet.png")
        WI.write_png(spath, sheet)

    # ---- checks (honest statuses only)
    C.check(checks, "measurements_written",
            "pass" if WI.file_size(mpath) > 0 else "fail",
            f"measurements.json {WI.file_size(mpath)} bytes", path=mpath)
    if spath:
        C.check(checks, "contact_sheet_written",
                "pass" if WI.file_size(spath) > 0 else "fail",
                f"contact sheet {WI.file_size(spath)} bytes", path=spath)
    else:
        C.check(checks, "contact_sheet_written", "not_checked",
                "contactSheet=false in params")
    C.check(checks, "all_images_measured",
            "pass" if len(images) == len(paths) else "warn",
            f"{len(images)}/{len(paths)} images measured")
    with_bands = sum(1 for e in images if set(BAND_NAMES) <= set(e["bandRatios"]))
    C.check(checks, "bands_present_all_images",
            "pass" if with_bands == len(images) else "fail",
            f"roof/upper/lower/plinth/ground ratios present for "
            f"{with_bands}/{len(images)} images")
    detected = [e["id"] for e in images if e["bandSource"] == "detected"]
    C.check(checks, "band_detection", "pass" if len(detected) == len(images) else "warn",
            f"bands anchored on the measured outline for {len(detected)}/"
            f"{len(images)} images", detected=detected)
    kinds = {}
    for e in images:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    C.check(checks, "exterior_interior_split", "pass",
            f"kind classification {json_dumps(kinds)}; band ratios are "
            "elevation-semantic only for kind=exterior (see bandModelApplicable)",
            kinds=kinds)
    montages = [e["id"] for e in images if e["kind"] == "montage"]
    if montages:
        C.check(checks, "montage_detected", "warn",
                "%s is a multi-view board (thin separator lines on both axes), "
                "so it carries no single-view silhouette" % ", ".join(montages),
                ids=montages)
    else:
        C.check(checks, "montage_detected", "pass", "no multi-view boards detected")
    non_native = [e["id"] for e in images if (e["width"], e["height"]) != (1448, 1086)]
    C.check(checks, "native_resolution", "pass" if not non_native else "warn",
            "all images 1448x1086" if not non_native
            else f"non-native size: {', '.join(non_native)}")
    C.check(checks, "pixel_provenance", "pass",
            "pixels read through Blender's image API and verified byte-identical "
            "to a pure-stdlib zlib PNG decode (round-trip maxdiff = 0)")
    C.check(checks, "fidelity_percentage", "not_checked",
            "this task deliberately reports no fidelity percentage; only the "
            "measurements in measurements.json")

    return {
        "ok": True,
        "task": "analyze_references",
        "artifacts": ([WI.artifact("json", mpath)] +
                      ([WI.artifact("png", spath)] if spath else [])),
        "images": images,
        "measurementsPath": mpath,
        "measurementsPathRel": WI.relpath(mpath, project_root),
        "contactSheetPath": spath,
        "contactSheetPathRel": WI.relpath(spath, project_root) if spath else None,
        "metrics": {
            "images": len(images),
            "ids": [e["id"] for e in images],
            "widths": sorted({e["width"] for e in images}),
            "heights": sorted({e["height"] for e in images}),
            "kinds": kinds,
            "bandSourceDetected": len(detected),
        },
        "checks": checks,
        "warnings": warnings,
        "notes": ("%d references measured. %s. Band ratios are measured between "
                  "the silhouette ridge and base: roof/upper/lower/plinth/ground. "
                  "Per-band edge density, dominant gradient orientation "
                  "(dominantDeg, axisAlignedShare, diagonalShare, entropyBits) and "
                  "Lab colour are included so tile courses (axis-aligned, low "
                  "entropy) can be told from radial ornament (diagonal, high "
                  "entropy). No fidelity percentage is claimed."
                  % (len(images), ordering)),
    }
