"""``compare_reference`` / ``propose_geometry_changes`` — real visual comparison.

``compare_reference`` loads a reference and a render as numpy arrays, aligns the
render's foreground onto the reference frame (auto scale + translate), and writes
**real files**: ``side_by_side.png``, ``overlay.png``, ``contour.png`` (plus an
alpha overlay), together with a full ``comparison_<ref>.json``.

Honesty rules built into this module:

* it consumes the reference classification produced by ``analyze_references``
  and reports ``silhouetteApplicable: false`` for interior and montage frames,
  where a silhouette IoU would be meaningless; those fall back to region-colour
  and edge metrics;
* it never emits a "fidelity %" — only the underlying measured numbers;
* ``propose_geometry_changes`` only emits a change when a measured delta
  crosses a threshold, and every change cites the region and the delta it came
  from, plus the ``gain`` used to turn a delta into a value.

Owned by ``visual-match``.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

import wm_common as C
import wm_image as WI

try:
    import wm_analysis as A
except Exception:                                   # pragma: no cover
    A = None

BAND_NAMES = ["roof", "upper", "lower", "plinth", "ground"]
BAND_ZH = {"roof": "屋面/檐口", "upper": "上层檐下", "lower": "下层檐下",
           "plinth": "台基", "ground": "地面接触带"}

# Defaults straight from CONTRACT §4B, used as the `from` side of a proposal.
PARAMETER_CATALOG = {
    "overhang":    {"part": "roof", "default": 1.55, "range": [0.6, 3.2], "unit": "m",
                    "meaning": "檐口出挑 (eave overhang)"},
    "cornerLift":  {"part": "roof", "default": 0.55, "range": [0.0, 1.6], "unit": "m",
                    "meaning": "翼角起翘 (corner lift)"},
    "slopePower":  {"part": "roof", "default": 1.75, "range": [1.0, 3.5], "unit": "-",
                    "meaning": "屋面曲率指数 (roof slope curvature)"},
    "ridgeHalf":   {"part": "roof", "default": 1.35, "range": [0.3, 3.0], "unit": "m",
                    "meaning": "正脊半长 (half ridge length)"},
    "tileRows":    {"part": "roof", "default": 28, "range": [8, 64], "unit": "rows",
                    "meaning": "瓦垄数 (tile course count)"},
    "tileSegments": {"part": "roof", "default": 26, "range": [6, 64], "unit": "seg",
                     "meaning": "沿坡向分段 (slide-direction segments)"},
    "eaveZ":       {"part": "roof", "default": 6.15, "range": [4.0, 8.5], "unit": "m",
                    "meaning": "檐口高度 (eave height)"},
    "ridgeZ":      {"part": "roof", "default": 11.30, "range": [8.0, 14.0], "unit": "m",
                    "meaning": "屋脊高度 (ridge height)"},
    "f1H":         {"part": "timber", "default": 3.35, "range": [2.4, 4.2], "unit": "m",
                    "meaning": "一层净高 (storey 1 height)"},
    "f2H":         {"part": "timber", "default": 2.95, "range": [2.2, 3.8], "unit": "m",
                    "meaning": "二层净高 (storey 2 height)"},
    "corridorWidth": {"part": "interior", "default": 1.9, "range": [0.9, 3.2], "unit": "m",
                      "meaning": "回廊宽度 (gallery corridor width)"},
    "railingHeight": {"part": "interior", "default": 1.05, "range": [0.7, 1.4], "unit": "m",
                      "meaning": "栏杆高度 (railing height)"},
    "plinthHeight": {"part": "diorama", "default": 0.65, "range": [0.3, 1.4], "unit": "m",
                     "meaning": "须弥座高度 (plinth height)"},
    "baseSize":    {"part": "diorama", "default": 16.0, "range": [10.0, 24.0], "unit": "m",
                    "meaning": "台基边长 (plinth footprint)"},
    "detail":      {"part": "roof", "default": "medium", "range": ["low", "medium", "high"],
                    "unit": "-", "meaning": "细分等级 (subdivision level)"},
}


# ==================================================================== helpers

def load_measurements(ctx: dict) -> dict:
    reports = ctx.get("reportsDir") or os.path.join(
        ctx.get("projectRoot") or os.getcwd(), "outputs", "wenmai-3d", "reports")
    path = os.path.join(reports, "analysis", "measurements.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def segment(arr: np.ndarray, tol: float = 20.0):
    """Foreground mask + cleaned bbox for one image."""
    raw, info = WI.foreground_mask(arr, tol=tol)
    mask, cinfo = WI.clean_mask(raw, step=4)
    box = WI.bbox_of(mask)
    if box is None:
        mask = np.ones(arr.shape[:2], dtype=bool)
        box = WI.bbox_of(mask)
    return mask, box, info, cinfo


def classify_reference(arr: np.ndarray, entry: dict | None) -> dict:
    """Reuse the analyze_references classification when it is available."""
    if entry:
        return {"kind": entry.get("kind"), "id": entry.get("id"),
                "skyFraction": entry.get("skyFraction"),
                "source": "measurements.json",
                "bands": [{"name": b["name"], "y0": b["y0"], "y1": b["y1"],
                           "ratio": b["ratio"]} for b in entry.get("bands", [])],
                "bandSource": entry.get("bandSource"),
                "orientationPerBand": entry.get("orientationPerBand")}
    if A is None:
        return {"kind": "unknown", "id": None, "source": "unavailable",
                "bands": [], "skyFraction": None}
    sky = float(WI.sky_mask(arr).mean())
    mont = A.detect_montage(arr)
    kind = A.classify_kind(sky, mont)
    return {"kind": kind, "id": None, "skyFraction": round(sky, 4),
            "montage": mont, "source": "computed-on-the-fly", "bands": []}


def band_regions(ref_bands: list, ref_box: dict, height: int) -> list:
    """Named comparison regions: the reference's own bands, or an equal split."""
    if ref_bands:
        return [{"name": b["name"], "y0": int(b["y0"]), "y1": int(b["y1"])}
                for b in ref_bands]
    y0, y1 = ref_box["y0"], ref_box["y1"]
    span = max(1, y1 - y0 + 1)
    out = []
    for i, name in enumerate(BAND_NAMES):
        out.append({"name": name,
                    "y0": int(y0 + span * i / 5.0),
                    "y1": int(y0 + span * (i + 1) / 5.0)})
    return out


def region_metrics(ref: np.ndarray, ren: np.ndarray, ref_mask: np.ndarray,
                   ren_mask: np.ndarray, region: dict) -> dict:
    """Colour / edge / fill deltas for one horizontal region."""
    y0, y1 = int(region["y0"]), int(region["y1"])
    h = ref.shape[0]
    y0 = max(0, min(h - 1, y0)); y1 = max(y0 + 1, min(h, y1))
    rm = ref_mask[y0:y1]
    nm = ren_mask[y0:y1]
    sub_ref = ref[y0:y1]
    sub_ren = ren[y0:y1]

    lab_ref = WI.rgb_to_lab(sub_ref)
    lab_ren = WI.rgb_to_lab(sub_ren)
    out = {"name": region.get("name"),
           "y0": int(y0), "y1": int(y1),
           "refBox": [0, y0, ref.shape[1] - 1, y1 - 1],
           "rows": [int(y0), int(y1)],
           "heightNorm": round((y1 - y0) / float(h), 5)}
    if rm.any() and nm.any():
        a = lab_ref[rm].mean(axis=0)
        b = lab_ren[nm].mean(axis=0)
        out["refLabMean"] = [round(float(v), 3) for v in a]
        out["renderLabMean"] = [round(float(v), 3) for v in b]
        out["deltaE"] = round(float(np.sqrt(np.sum((a - b) ** 2))), 4)
        out["deltaL"] = round(float(b[0] - a[0]), 4)
        out["deltaA"] = round(float(b[1] - a[1]), 4)
        out["deltaB"] = round(float(b[2] - a[2]), 4)
        gm_ref = WI.to_gray(sub_ref); gm_ren = WI.to_gray(sub_ren)
        out["refEdgeDensity"] = round(WI.edge_density(gm_ref, rm), 4)
        out["renderEdgeDensity"] = round(WI.edge_density(gm_ren, nm), 4)
        out["edgeDensityDelta"] = round(out["renderEdgeDensity"]
                                        - out["refEdgeDensity"], 4)
        out["refFill"] = round(float(rm.mean()), 4)
        out["renderFill"] = round(float(nm.mean()), 4)
        out["fillDelta"] = round(out["renderFill"] - out["refFill"], 4)
        out["silhouetteIoU"] = round(WI.jaccard(rm, nm), 4)
        lab_ref_band = lab_ref[rm]
        lab_ren_band = lab_ren[nm]
        out["refDetailEnergy"] = round(WI.laplacian_energy(gm_ref), 5)
        out["renderDetailEnergy"] = round(WI.laplacian_energy(gm_ren), 5)
        out["refLuma"] = round(float(gm_ref[rm].mean()), 2)
        out["renderLuma"] = round(float(gm_ren[nm].mean()), 2)
    else:
        out["deltaE"] = None
        out["edgeDensityDelta"] = None
        out["silhouetteIoU"] = None
        out["note"] = "empty foreground in this region for one of the images"
    return out


def compare_reference(params: dict, ctx: dict) -> dict:
    params = params or {}
    project_root = ctx.get("projectRoot") or os.getcwd()
    checks, warnings = [], []

    if not params.get("reference") or not params.get("render"):
        return C.fail("both 'reference' and 'render' image paths are required")
    ref_path = WI.resolve_path(params["reference"], ctx)
    ren_path = WI.resolve_path(params["render"], ctx)
    for label, path in (("reference", ref_path), ("render", ren_path)):
        if not os.path.isfile(path):
            return C.fail(f"{label} image not found: {path}")

    ref = WI.read_png(ref_path)
    ren = WI.read_png(ren_path)
    h, w = ref.shape[:2]

    # ---- reference classification (from analyze_references when possible)
    meas = load_measurements(ctx)
    entry = None
    for e in meas.get("images", []) or []:
        if e.get("file") == os.path.basename(ref_path):
            entry = e
            break
    cls = classify_reference(ref, entry)
    kind = cls.get("kind")
    silhouette_applicable = kind == "exterior"
    if kind in ("interior", "montage"):
        warnings.append(
            f"reference is kind={kind}: a silhouette IoU is not a meaningful "
            "measure here, so silhouetteIoU is reported as null and the "
            "comparison falls back to region colour, edge and detail metrics")

    ref_mask, ref_box, ref_info, ref_clean = segment(ref, tol=float(params.get("tol", 20.0)))
    ren_mask, ren_box, ren_info, ren_clean = segment(ren, tol=float(params.get("tol", 20.0)))

    # ---- scale-invariant band proportions for both images
    # The bbox scale ratio conflates camera framing with model size, so vertical
    # proportion proposals are driven by these ratios instead.
    ref_band_ratios = {b["name"]: b["ratio"] for b in (cls.get("bands") or [])
                       if b.get("ratio") is not None}
    ren_band_ratios, ren_bands = {}, []
    if A is not None:
        try:
            ren_gray0 = WI.to_gray(ren)
            ren_mag0, _ = WI.sobel(ren_gray0)
            rdet = A.detect_band_boundaries(ren_mask, ren_box, ren_gray0, ren_mag0,
                                           kind="exterior")
            if rdet.get("ok"):
                ren_bands = rdet["bands"]
                ren_band_ratios = rdet["ratios"]
            else:
                warnings.append("render band detection failed: %s"
                                % rdet.get("reason"))
        except Exception as exc:                       # pragma: no cover
            warnings.append(f"could not measure render bands: {exc}")

    # ---- alignment: scale + translate the render onto the reference frame
    align_mode = str(params.get("align", "auto"))
    sx = ref_box["w"] / float(max(1, ren_box["w"]))
    sy = ref_box["h"] / float(max(1, ren_box["h"]))
    if align_mode == "none":
        sx = sy = 1.0
        tx = ref_box["x0"] - ren_box["x0"]
        ty = ref_box["y0"] - ren_box["y0"]
    else:
        # uniform scale keeps the render's aspect; the residual x/y ratio is
        # reported as bboxScaleRatio so an anisotropic mismatch stays visible
        s = 0.5 * (sx + sy)
        sx = sy = s
        tx = ref_box["x0"] - s * ren_box["x0"]
        ty = ref_box["y0"] - s * ren_box["y0"]

    ren_aligned = WI.resample_into(ren, w, h, sx, sy, tx, ty, fill=255)
    ren_mask_aligned = WI.resample_into(ren_mask.astype(np.uint8) * 255, w, h,
                                        sx, sy, tx, ty, fill=0) > 127
    ref_gray = WI.to_gray(ref)
    ren_gray = WI.to_gray(ren_aligned)

    # ---- global metrics
    a_cent = np.array([ref_box["x0"] + ref_box["w"] / 2.0,
                       ref_box["y0"] + ref_box["h"] / 2.0])
    b_cent = np.array([ren_box["x0"] * sx + tx + ren_box["w"] * sx / 2.0,
                       ren_box["y0"] * sy + ty + ren_box["h"] * sy / 2.0])
    cent_off = b_cent - a_cent
    iou = WI.jaccard(ref_mask, ren_mask_aligned)
    detail_ref = WI.laplacian_energy(ref_gray)
    detail_ren = WI.laplacian_energy(ren_gray)

    metrics = {
        "silhouetteApplicable": bool(silhouette_applicable),
        "silhouetteIoU": round(iou, 4) if silhouette_applicable else None,
        "silhouetteIoUUnconditional": round(iou, 4),
        "centroidOffsetPx": [round(float(cent_off[0]), 2), round(float(cent_off[1]), 2)],
        "centroidOffsetNorm": [round(float(cent_off[0]) / w, 5),
                               round(float(cent_off[1]) / h, 5)],
        "bboxScaleRatio": {"x": round(float(sx), 5), "y": round(float(sy), 5),
                           "anisotropy": round(float(abs(sx - sy) / max(sx, sy)), 5)},
        "bboxRef": ref_box["norm"], "bboxRender": ren_box["norm"],
        "bboxAlignedBox": {"x": int(round(ren_box["x0"] * sx + tx)),
                           "y": int(round(ren_box["y0"] * sy + ty)),
                           "w": int(round(ren_box["w"] * sx)),
                           "h": int(round(ren_box["h"] * sy))},
        "coverage": {"reference": round(float(ref_mask.mean()), 4),
                     "renderAligned": round(float(ren_mask_aligned.mean()), 4)},
        "detailEnergy": {"reference": round(detail_ref, 5),
                         "renderAligned": round(detail_ren, 5),
                         "ratio": round(detail_ren / detail_ref, 4) if detail_ref else None},
        "edgeDensity": {"reference": round(WI.edge_density(ref_gray, ref_mask), 4),
                        "renderAligned": round(WI.edge_density(ren_gray, ren_mask_aligned), 4)},
        "warmCool": {"reference": WI.warm_cool(ref, ref_mask),
                     "renderAligned": WI.warm_cool(ren_aligned, ren_mask_aligned)},
        "alignMode": align_mode,
        "referenceKind": kind,
        "referenceId": cls.get("id"),
        "bandRatiosReference": ref_band_ratios or None,
        "bandRatiosRender": ren_band_ratios or None,
        "bandRatioDelta": ({k: round(ren_band_ratios[k] - ref_band_ratios[k], 4)
                            for k in BAND_NAMES
                            if k in ren_band_ratios and k in ref_band_ratios}
                           or None),
        "bandRatioNote": ("band ratios are heights normalised by each image's own "
                          "silhouette span, so they are invariant to camera "
                          "framing; bandRatioDelta is the honest signal for "
                          "proportion changes"),
        "bboxScaleNote": ("bboxScaleRatio measures how much the render's foreground "
                          "had to be scaled to match the reference's; it mixes "
                          "framing distance with real size and must NOT be read as "
                          "a height error"),
    }

    # ---- per-region metrics
    regions = []
    for region in band_regions(cls.get("bands") or [], ref_box, h):
        regions.append(region_metrics(ref, ren_aligned, ref_mask,
                                      ren_mask_aligned, region))
    metrics["bandEdgeErrors"] = {r["name"]: r.get("edgeDensityDelta")
                                 for r in regions}
    metrics["regionColorDeltaE"] = {r["name"]: r.get("deltaE") for r in regions}
    metrics["regionSilhouetteIoU"] = {r["name"]: r.get("silhouetteIoU")
                                      for r in regions}

    # ---- artifacts
    out_dir = WI.resolve_path(params.get("outDir") or ctx.get("rendersDir")
                              or os.path.join(project_root, "outputs",
                                              "wenmai-3d", "renders"), ctx)
    out_dir = os.path.join(out_dir, "compare")
    WI.ensure_dir(out_dir)
    ref_stem = os.path.splitext(os.path.basename(ref_path))[0]
    ren_stem = os.path.splitext(os.path.basename(ren_path))[0]
    tag = params.get("tag") or f"{ref_stem}__{ren_stem}"

    sbs = np.zeros((h, 2 * w + 4, 3), dtype=np.uint8)
    sbs[:, :w] = ref
    sbs[:, w:2 * w] = ren_aligned
    sbs[:, w:2 * w:1][:, 0:4] = 0
    sbs[:, w:w + 4] = (255, 255, 255)
    WI.draw_text(sbs, 8, 8, "REFERENCE " + (cls.get("id") or ref_stem)[:20],
                 color=(255, 255, 255), scale=2)
    WI.draw_text(sbs, w + 12, 8, "RENDER " + ren_stem[:20],
                 color=(255, 255, 255), scale=2)
    if not silhouette_applicable:
        WI.draw_text(sbs, 8, 30, f"KIND={kind} SILHOUETTE-IOU NOT-APPLICABLE",
                     color=(255, 210, 90), scale=2)
    side_path = os.path.join(out_dir, f"side_by_side_{tag}.png")
    WI.write_png(side_path, sbs)

    ov = WI.blend_overlay(ref, ren_aligned, alpha=0.5)
    WI.draw_text(ov, 8, 8, "OVERLAY 50%", color=(255, 255, 255), scale=2)
    ov_path = os.path.join(out_dir, f"overlay_{tag}.png")
    WI.write_png(ov_path, ov)

    rgba = np.dstack([ref, np.full((h, w), 255, np.uint8)])
    rgba[:, :, :3] = np.where(ren_mask_aligned[:, :, None],
                              (0.5 * ref + 0.5 * ren_aligned).astype(np.uint8), ref)
    rgba[:, :, 3] = np.where(ren_mask_aligned, 128, 255).astype(np.uint8)
    ov_alpha_path = os.path.join(out_dir, f"overlay_alpha_{tag}.png")
    WI.write_png(ov_alpha_path, rgba)

    contour = np.full((h, w, 3), 18, dtype=np.uint8)
    contour[ref_mask] = (34, 34, 40)
    rc = WI.mask_outline(ref_mask, 2)
    nc = WI.mask_outline(ren_mask_aligned, 2)
    contour[rc] = (60, 200, 255)
    contour[nc] = (255, 120, 60)
    contour[rc & nc] = (240, 240, 240)
    for region in regions:
        cy = int(region["y1"] - 1)
        if 0 <= cy < h:
            contour[cy, :] = (90, 90, 110)
        WI.draw_text(contour, 8, max(0, int(region["y0"]) + 3),
                     region["name"].upper(), color=(200, 200, 210), scale=2)
    WI.draw_text(contour, 8, 8, "CONTOUR cyan=reference orange=render white=both",
                 color=(255, 255, 255), scale=2)
    contour_path = os.path.join(out_dir, f"contour_{tag}.png")
    WI.write_png(contour_path, contour)

    # ---- checks
    for label, path in (("side_by_side", side_path), ("overlay", ov_path),
                        ("contour", contour_path),
                        ("overlay_alpha", ov_alpha_path)):
        C.check(checks, f"{label}_written",
                "pass" if WI.file_size(path) > 0 else "fail",
                f"{os.path.basename(path)} {WI.file_size(path)} bytes", path=path)
    nums = [iou if silhouette_applicable else None,
            metrics["detailEnergy"]["ratio"],
            metrics["bboxScaleRatio"]["x"]]
    C.check(checks, "metrics_numerically_populated",
            "pass" if all(v is not None for v in nums) else "warn",
            "silhouetteIoU, detail ratio and bbox scale are all populated "
            "(IoU only where applicable)")
    C.check(checks, "silhouette_claim_scope",
            "pass" if silhouette_applicable else "warn",
            ("reference kind=%s supports a silhouette comparison" % kind)
            if silhouette_applicable else
            ("reference kind=%s does not support a silhouette claim; "
             "silhouetteIoU is null and region colour/edge metrics are reported "
             "instead" % kind))
    C.check(checks, "alignment", "pass" if align_mode == "auto" else "manual",
            f"align={align_mode}, uniform scale {metrics['bboxScaleRatio']['x']}, "
            f"anisotropy {metrics['bboxScaleRatio']['anisotropy']}")
    C.check(checks, "fidelity_percentage", "not_checked",
            "no fidelity percentage is computed or claimed by this module")
    C.check(checks, "camera_consistency", "not_checked",
            "bbox alignment is used, not the render's camera; a cameraPath does "
            "not by itself prove the two images share a viewpoint")

    result = {
        "ok": True,
        "task": "compare_reference",
        "artifacts": [WI.artifact("png", side_path),
                      WI.artifact("png", ov_path),
                      WI.artifact("png", contour_path),
                      WI.artifact("png", ov_alpha_path)],
        "sideBySide": side_path,
        "overlay": ov_path,
        "overlayAlpha": ov_alpha_path,
        "contour": contour_path,
        "metrics": metrics,
        "regions": regions,
        "reference": {"path": ref_path, "id": cls.get("id"), "kind": kind,
                      "classificationSource": cls.get("source"),
                      "width": w, "height": h},
        "render": {"path": ren_path, "width": ren.shape[1], "height": ren.shape[0],
                   "cameraPath": params.get("cameraPath")},
        "alignment": {"scale": [round(float(sx), 6), round(float(sy), 6)],
                      "translate": [round(float(tx), 3), round(float(ty), 3)],
                      "mode": align_mode},
        "checks": checks,
        "warnings": warnings,
        "notes": (f"compared {os.path.basename(ref_path)} (kind={kind}) with "
                  f"{os.path.basename(ren_path)} at {w}x{h}. "
                  + (f"silhouette IoU {iou:.4f}; " if silhouette_applicable
                     else "silhouette IoU withheld (not applicable); ")
                  + f"detail-energy ratio "
                  f"{metrics['detailEnergy']['ratio']}, centroid offset "
                  f"({cent_off[0]:+.1f}, {cent_off[1]:+.1f}) px. Per-region Lab "
                  "deltaE and edge-density deltas are in regions[]. No fidelity "
                  "percentage is claimed."),
    }

    cpath = os.path.join(out_dir, f"comparison_{ref_stem}.json")
    if params.get("comparisonPath"):
        cpath = WI.resolve_path(params["comparisonPath"], ctx)
        WI.ensure_dir(os.path.dirname(cpath))
    payload = dict(result)
    payload["regions"] = regions
    with open(cpath, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    result["comparisonPath"] = cpath
    result["comparisonPathRel"] = WI.relpath(cpath, project_root)
    result["artifacts"].append(WI.artifact("json", cpath))
    return result


# ======================================================= parameter proposals

def _clamp(value, spec):
    rng = spec.get("range")
    if not rng or not isinstance(rng[0], (int, float)):
        return value
    return max(float(rng[0]), min(float(rng[1]), float(value)))


def _numeric(parameter: str, spec: dict, gain: float, delta: float,
             log_scale: bool = False) -> dict | None:
    """Turn a measured delta into a proposed value, or None if it is too small."""
    base = spec["default"]
    if not isinstance(base, (int, float)):
        return None
    if abs(delta) < 1e-9:
        return None
    factor = 1.0 + gain * delta
    factor = max(0.35, min(3.0, factor))
    proposed = base * (factor if not log_scale else factor)
    proposed = _clamp(proposed, spec)
    if isinstance(base, int):
        proposed = int(round(proposed))
    else:
        proposed = round(float(proposed), 3)
    if proposed == base:
        return None
    return {"from": base, "to": proposed, "factor": round(factor, 4),
            "gain": gain}


def propose_geometry_changes(params: dict, ctx: dict) -> dict:
    params = params or {}
    project_root = ctx.get("projectRoot") or os.getcwd()
    checks, warnings = [], []

    payload = None
    src = params.get("comparisonPath") or params.get("reportPath")
    if src:
        p = WI.resolve_path(src, ctx)
        try:
            with open(p, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, ValueError) as exc:
            return C.fail(f"cannot read comparison/report JSON {p}: {exc}")
    elif params.get("comparison"):
        payload = params["comparison"]
    if not isinstance(payload, dict):
        return C.fail("comparisonPath (or comparison) with a compare_reference "
                      "result is required")

    catalog = dict(PARAMETER_CATALOG)
    for k, v in (params.get("parameterCatalog") or {}).items():
        catalog[k] = {**catalog.get(k, {}), **v}

    metrics = payload.get("metrics") or {}
    regions = payload.get("regions") or []
    kind = (payload.get("reference") or {}).get("kind") or metrics.get("referenceKind")
    applicable = bool(metrics.get("silhouetteApplicable", kind == "exterior"))
    rmap = {r.get("name"): r for r in regions}

    def spec(p):
        return catalog.get(p) or {"part": "roof", "default": 1.0, "range": [0.0, 1e9]}

    changes = []
    thresholds = {"deltaE": 4.0, "edge": 0.06, "fill": 0.08, "iou": 0.72,
                  "detail": 0.25, "scale": 0.03}

    def add(parameter, component, reason, evidence, expected, priority,
            proposal, severity, confidence="medium", caveat=None):
        if proposal is None:
            return
        s = spec(parameter)
        item = {
            "priority": int(priority),
            "parameter": parameter,
            "component": component,
            "object": s.get("part"),
            "reason": reason,
            "from": proposal["from"],
            "to": proposal["to"],
            "gain": proposal["gain"],
            "expectedEffect": expected,
            "severity": severity,
            "confidence": confidence,
            "evidence": evidence,
        }
        if caveat:
            item["caveat"] = caveat
        changes.append(item)

    # ---- roof band outline: eave overhang
    roof = rmap.get("roof") or {}
    r_iou = roof.get("silhouetteIoU")
    if applicable and r_iou is not None and r_iou < thresholds["iou"]:
        d_fill = float(roof.get("fillDelta") or 0.0)
        add("overhang", "roof",
            "roof-band silhouette does not match the reference; the eave band is "
            "the widest, most outline-sensitive part of the model",
            {"region": "roof", "silhouetteIoU": r_iou, "fillDelta": d_fill,
             "threshold": thresholds["iou"]},
            "widening/narrowing the eave overhang moves the roof outline toward "
            "the reference", 1,
            _numeric("overhang", spec("overhang"), 1.6, -d_fill), "high",
            confidence="medium",
            caveat="driven by a band silhouette IoU after bbox alignment, which "
                   "still absorbs some framing difference")

    # ---- vertical proportions from scale-invariant band ratios
    brd = metrics.get("bandRatioDelta") or {}
    if applicable and brd:
        # roof band = ridge..eave: a short roof band can be fixed by dropping the
        # eave or raising the ridge; eaveZ is proposed because it is the lower,
        # more constrained of the two.
        d_roof = float(brd.get("roof") or 0.0)
        if abs(d_roof) > 0.045:
            add("eaveZ", "roof",
                f"roof band occupies {abs(d_roof) * 100:.1f}% "
                f"{'more' if d_roof > 0 else 'less'} of the silhouette than the "
                "reference; band ratios are normalised by each image's own span so "
                "this is independent of camera framing",
                {"region": "roof", "bandRatioDelta": d_roof, "threshold": 0.045,
                 "referenceRatio": (metrics.get("bandRatiosReference") or {}).get("roof"),
                 "renderRatio": (metrics.get("bandRatiosRender") or {}).get("roof")},
                "lowering the eave deepens the roof band; raising it shrinks the "
                "band. The sign below follows the measured delta so the proposal "
                "always moves toward the reference.", 2,
                {"from": spec("eaveZ")["default"],
                 "to": round(_clamp(spec("eaveZ")["default"]
                                    * (1.0 + 0.9 * d_roof), spec("eaveZ")), 3),
                 "factor": round(1.0 + 0.9 * d_roof, 4), "gain": 0.9},
                "medium", confidence="medium",
                caveat="band names are positional labels snapped to structure "
                       "lines, not measured eaves; treat this as a direction to "
                       "test, then re-render and re-measure")
        for band, param, meaning in (("upper", "f2H", "upper storey height"),
                                     ("lower", "f1H", "lower storey height"),
                                     ("plinth", "plinthHeight", "plinth height")):
            d = float(brd.get(band) or 0.0)
            if abs(d) <= 0.045:
                continue
            add(param, "timber" if param in ("f1H", "f2H") else "diorama",
                f"{band} band differs from the reference by {d * 100:+.1f}% of the "
                f"silhouette span ({meaning})",
                {"region": band, "bandRatioDelta": round(d, 4), "threshold": 0.045,
                 "referenceRatio": (metrics.get("bandRatiosReference") or {}).get(band),
                 "renderRatio": (metrics.get("bandRatiosRender") or {}).get(band)},
                f"scaling {meaning} proportionally re-distributes the facade bands",
                3, _numeric(param, spec(param), 0.9, -d), "medium",
                confidence="medium",
                caveat="positional band label, not a measured storey line; the sign "
                       "follows the measured delta so the storey that is too tall "
                       "shrink")

    # ---- detail energy: tile density (low confidence, strong confound)
    det = metrics.get("detailEnergy") or {}
    ratio = det.get("ratio")
    if ratio is not None and float(ratio) < (1.0 - thresholds["detail"]):
        d = float(ratio) - 1.0
        add("tileRows", "roof",
            "high-frequency detail energy is much lower than the reference, which "
            "is consistent with fewer visible tile courses",
            {"region": "global", "detailEnergyRatio": ratio,
             "threshold": thresholds["detail"]},
            "more tile courses add fine-scale edge energy", 4,
            {"from": spec("tileRows")["default"],
             "to": int(round(_clamp(
                 spec("tileRows")["default"] * max(0.6, min(1.8, 1.0 - 0.5 * d)),
                 spec("tileRows")))),
             "factor": round(1.0 - 0.5 * d, 4), "gain": 0.5}, "low",
            confidence="low",
            caveat="the reference is a painted illustration while the render is "
                   "flat-shaded geometry, so a large detail-energy gap is expected "
                   "and does not by itself prove a tile-count error")

    # ---- colour deltas per region -> palette parameters
    for name in BAND_NAMES:
        r = rmap.get(name) or {}
        de = r.get("deltaE")
        if de is None or float(de) < thresholds["deltaE"]:
            continue
        dl, da, db = (r.get("deltaL"), r.get("deltaA"), r.get("deltaB"))
        changes.append({
            "priority": 2 if float(de) > 2 * thresholds["deltaE"] else 4,
            "parameter": f"palette.{_palette_key(name)}",
            "component": _palette_part(name),
            "object": _palette_part(name),
            "reason": (f"{name} region colour differs by deltaE "
                       f"{float(de):.2f} in CIE Lab"),
            "from": list(r.get("refLabMean") or []),
            "to": list(r.get("renderLabMean") or []),
            "gain": None,
            "confidence": "medium",
            "caveat": ("the reference is an illustration and the render is lit "
                       "geometry; part of a Lab delta is lighting and "
                       "post-processing, not material colour"),
            "expectedEffect": (
                "move the material's base colour toward the reference: "
                f"dL* {dl} (lightness), da* {da} (red-green), db* {db} (blue-yellow)"),
            "severity": "high" if float(de) > 2 * thresholds["deltaE"] else "medium",
            "evidence": {"region": name, "deltaE": de, "deltaL": dl,
                         "deltaA": da, "deltaB": db,
                         "threshold": thresholds["deltaE"]},
        })

    # ---- not-applicable references
    if not applicable:
        changes.insert(0, {
            "priority": 0,
            "parameter": "geometryReview",
            "component": "review",
            "object": None,
            "reason": (f"reference kind={kind} carries no single elevation, so "
                       "silhouette-driven geometry proposals are withheld"),
            "from": None, "to": None, "gain": None,
            "expectedEffect": "collect an exterior reference before fitting roof "
                              "or storey parameters",
            "severity": "info",
            "evidence": {"referenceKind": kind,
                         "silhouetteApplicable": False},
        })

    changes.sort(key=lambda c: (c["priority"], c["parameter"]))

    caveats = [
        "bbox alignment removes framing translation and scale, so the reported "
        "bboxScaleRatio mixes framing distance with real size and is NOT used to "
        "propose any absolute size change.",
        "band names (roof/upper/lower/plinth/ground) are positional labels snapped "
        "to strong horizontal structure lines; they are not measured eaves or "
        "storey lines. Proportion proposals are directions to test, not facts.",
        "the references are painted illustrations while renders are flat-shaded "
        "geometry, so detail-energy and Lab colour deltas include lighting, "
        "shading and post-processing, not only geometry or material errors.",
        "no fidelity percentage is computed anywhere in this module.",
    ]

    # ---- reports
    out_dir = WI.resolve_path(params.get("outDir") or ctx.get("reportsDir")
                              or os.path.join(project_root, "outputs",
                                              "wenmai-3d", "reports"), ctx)
    WI.ensure_dir(out_dir)
    stem = ((payload.get("reference") or {}).get("id")
            or os.path.splitext(os.path.basename(
                (payload.get("reference") or {}).get("path") or "ref"))[0])
    jpath = WI.resolve_path(params.get("outPath") or
                            os.path.join(out_dir, f"proposals_{stem}.json"), ctx)
    mpath = os.path.splitext(jpath)[0] + ".md"

    with open(jpath, "w", encoding="utf-8") as fh:
        json.dump({"schema": 1, "generatedBy": "wm_compare.propose_geometry_changes",
                   "source": src, "referenceKind": kind,
                   "silhouetteApplicable": applicable,
                   "caveats": caveats,
                   "parameterCatalog": catalog, "changes": changes},
                  fh, ensure_ascii=False, indent=1)

    lines = [f"# Geometry change proposals — {stem}", "",
             f"Source comparison: `{src}`  ", f"Reference kind: **{kind}**  ",
             f"Silhouette applicable: **{applicable}**", "",
             "Every row cites the measured delta it came from. `gain` is the "
             "multiplier applied to that delta to reach `to`; nothing here is a "
             "measured fact about the reference beyond the `evidence` field.", "",
             "| # | P | parameter | from | to | conf | evidence | reason |",
             "|---|---|---|---|---|---|---|---|"]
    for i, ch in enumerate(changes, 1):
        ev = ch.get("evidence") or {}
        evs = ", ".join(f"{k}={v}" for k, v in ev.items() if v is not None)
        lines.append("| {} | {} | `{}` | {} | {} | {} | {} | {} |".format(
            i, ch["priority"], ch["parameter"], ch["from"], ch["to"],
            ch.get("confidence", "-"),
            evs.replace("|", "/")[:110], ch["reason"].replace("|", "/")))
    if not changes:
        lines += ["", "_No delta crossed a threshold, so no parameter change is "
                     "proposed._"]
    caveated = [c for c in changes if c.get("caveat")]
    if caveated:
        lines += ["", "## Caveats attached to individual proposals", ""]
        for ch in caveated:
            lines.append(f"- `{ch['parameter']}`: {ch['caveat']}")
    lines += ["", "## Method caveats", ""] + [f"- {c}" for c in caveats]
    lines += ["", "## Parameter catalog", "",
              "| parameter | part | default | range | unit | meaning |",
              "|---|---|---|---|---|---|"]
    for k, v in sorted(catalog.items()):
        lines.append("| `{}` | {} | {} | {} | {} | {} |".format(
            k, v.get("part"), v.get("default"), v.get("range"), v.get("unit"),
            v.get("meaning")))
    with open(mpath, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    C.check(checks, "source_comparison_read", "pass",
            f"read comparison from {src}", silhouetteApplicable=applicable)
    C.check(checks, "changes_grounded", "pass",
            "every proposed change carries an evidence object with the measured "
            "delta and the threshold it crossed")
    C.check(checks, "silhouette_scope", "pass" if applicable else "warn",
            f"reference kind={kind} does not support silhouette-driven proposals"
            if not applicable else "elevation bands support geometry proposals")
    C.check(checks, "reports_written",
            "pass" if WI.file_size(jpath) and WI.file_size(mpath) else "fail",
            f"JSON {WI.file_size(jpath)} B + Markdown {WI.file_size(mpath)} B")
    C.check(checks, "fidelity_percentage", "not_checked",
            "this module proposes parameter changes; it does not score fidelity")

    return {
        "ok": True,
        "task": "propose_geometry_changes",
        "artifacts": [WI.artifact("json", jpath), WI.artifact("markdown", mpath)],
        "changes": changes,
        "parameterCatalog": catalog,
        "caveats": caveats,
        "reportPath": jpath,
        "reportPathRel": WI.relpath(jpath, project_root),
        "markdownPath": mpath,
        "markdownPathRel": WI.relpath(mpath, project_root),
        "referenceKind": kind,
        "silhouetteApplicable": applicable,
        "metrics": {"changes": len(changes),
                    "highSeverity": sum(1 for c in changes if c["severity"] == "high"),
                    "parametersTouched": sorted({c["parameter"] for c in changes})},
        "checks": checks,
        "warnings": warnings,
        "notes": (f"{len(changes)} grounded parameter change(s) ordered by priority. "
                  "Each change names the plugin parameter, the measured delta and "
                  "the gain used to convert it; the Markdown report is the "
                  "human-readable view of the same data."),
    }


def _palette_key(band: str) -> str:
    return {"roof": "roof_tile", "upper": "wall", "lower": "timber",
            "plinth": "stone", "ground": "paving"}.get(band, "wall")


def _palette_part(band: str) -> str:
    return {"roof": "roof", "upper": "timber", "lower": "timber",
            "plinth": "diorama", "ground": "diorama"}.get(band, "timber")
