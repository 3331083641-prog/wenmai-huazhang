"""Reference measurement v2: flood-fill background + HSV semantic zone map.

Outputs, per reference image:
  - exterior/interior classification
  - silhouette bbox, coverage, extent profile (width vs height band)
  - skyline (top foreground row per column)  -> roof silhouette
  - strong horizontal / vertical boundaries   -> eave, floor, base, bay rhythm
  - a semantically labelled zone map (64x32)  -> material layout

Usage:
  python measure_v2.py <src_dir> <out_dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# ---------------------------------------------------------------- helpers

def rgb_to_hsv(arr: np.ndarray):
    r, g, b = arr[..., 0] / 255.0, arr[..., 1] / 255.0, arr[..., 2] / 255.0
    mx = np.max(arr, axis=-1) / 255.0
    mn = np.min(arr, axis=-1) / 255.0
    d = np.maximum(mx - mn, 1e-6)
    h = np.zeros_like(mx)
    m = (mx == r)
    h[m] = (60 * ((g - b) / d) % 360)[m]
    m = (mx == g) & (mx != r)
    h[m] = (60 * ((b - r) / d) + 120)[m]
    m = (mx == b) & (mx != r) & (mx != g)
    h[m] = (60 * ((r - g) / d) + 240)[m]
    s = np.where(mx <= 1e-6, 0.0, d / np.maximum(mx, 1e-6))
    return h, s, mx


def flood_background(arr: np.ndarray, tol: float = 26.0, step: int = 4) -> np.ndarray:
    """Flood fill from the border on a reduced grid; return full-res bool mask."""
    h, w, _ = arr.shape
    hs, ws = h // step, w // step
    small = arr[: hs * step, : ws * step].reshape(hs, step, ws, step, 3).mean(axis=(1, 3))
    seen = np.zeros((hs, ws), dtype=bool)
    stack = []
    for x in range(ws):
        for y in (0, hs - 1):
            stack.append((y, x))
    for y in range(hs):
        for x in (0, ws - 1):
            stack.append((y, x))
    seeds = []
    for y, x in stack:
        if not seen[y, x]:
            seen[y, x] = True
            seeds.append((y, x))

    # Background colour model = colours of the accepted region.
    ref = small[seen]
    out = seen.copy()
    frontier = list(seeds)
    while frontier:
        nxt = []
        for y, x in frontier:
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < hs and 0 <= nx < ws and not out[ny, nx]:
                    c = small[ny, nx]
                    if np.min(np.linalg.norm(ref - c, axis=1)) <= tol:
                        out[ny, nx] = True
                        nxt.append((ny, nx))
        frontier = nxt
        if len(frontier) > 40000:
            break
    up = np.repeat(np.repeat(out, step, axis=0), step, axis=1)
    full = np.zeros((h, w), dtype=bool)
    full[: up.shape[0], : up.shape[1]] = up
    full[up.shape[0]:, :] = full[up.shape[0] - 1:up.shape[0], :]
    full[:, up.shape[1]:] = full[:, up.shape[1] - 1:up.shape[1]]
    return full


def classify(arr: np.ndarray) -> np.ndarray:
    """Return an int zone label per pixel."""
    h, s, v = rgb_to_hsv(arr)
    label = np.full(h.shape, 11, dtype=np.int8)  # 11 = other
    blue = (h >= 190) & (h <= 250) & (s > 0.18) & (v > 0.55)
    label[blue & (v > 0.86) & (s < 0.35)] = 0          # pale sky
    label[blue] = 1                                     # sky
    white = (v > 0.84) & (s < 0.16)
    label[white] = 2                                    # white / plaster / cloud
    warm = (h < 70) | (h > 340)
    label[warm & (v > 0.66) & (s > 0.05) & (s < 0.42)] = 3   # warm wall / stone
    label[warm & (s >= 0.42) & (v > 0.55) & (v <= 0.85) & (h > 18)] = 7   # wood mid
    label[warm & (s >= 0.34) & (v <= 0.55)] = 8               # dark wood
    red = ((h < 20) | (h > 352)) & (s > 0.52) & (v > 0.34) & (v < 0.72)
    label[red] = 9                                       # red lacquer / lantern
    goldm = (h >= 34) & (h <= 62) & (s > 0.42) & (v > 0.60) & (v < 0.90)
    label[goldm] = 10                                    # gold / ochre ornament
    green = (h >= 70) & (h <= 165) & (s > 0.18)
    label[green] = 6                                     # planting
    gray = (s < 0.20) & (v > 0.34) & (v <= 0.84)
    label[gray] = 4                                      # stone / tile grey
    vslate = (s < 0.32) & (v > 0.16) & (v <= 0.38)
    label[vslate] = 5                                    # slate / shadow
    dark = v <= 0.18
    label[dark] = 12                                     # near black
    return label


ZONE_CHARS = {
    0: "a", 1: "s", 2: "w", 3: "c", 4: "g", 5: "f", 6: "p",
    7: "W", 8: "D", 9: "R", 10: "G", 11: "?", 12: "k",
}
ZONE_NAMES = {
    0: "pale-sky", 1: "sky", 2: "white", 3: "warm-wall/stone", 4: "grey-stone/tile",
    5: "slate/shadow", 6: "plant-green", 7: "wood-mid", 8: "wood-dark",
    9: "red-lacquer", 10: "gold/ochre", 11: "other", 12: "near-black",
}


def extent_profile(fg: np.ndarray, bands: int = 40):
    h, w = fg.shape
    rows = []
    for j in range(bands):
        y0 = int(h * j / bands); y1 = max(y0 + 1, int(h * (j + 1) / bands))
        cols = np.nonzero(fg[y0:y1].any(axis=0))[0]
        rows.append({"y": round((j + 0.5) / bands, 3),
                     "l": None if cols.size == 0 else round(float(cols.min()) / w, 3),
                     "r": None if cols.size == 0 else round(float(cols.max()) / w, 3),
                     "w": 0.0 if cols.size == 0 else round(float(cols.max() - cols.min()) / w, 3)})
    return rows


def skyline(fg: np.ndarray, cols: int = 48):
    h, w = fg.shape
    out = []
    for i in range(cols):
        x0 = int(w * i / cols); x1 = max(x0 + 1, int(w * (i + 1) / cols))
        idx = np.nonzero(fg[:, x0:x1].any(axis=1))[0]
        out.append(None if idx.size == 0 else round(float(idx.min()) / h, 3))
    return out


def peaks(profile: np.ndarray, count: int, gap: int):
    if profile.size < 3:
        return []
    d = np.abs(np.gradient(profile - profile.mean()))
    order = np.argsort(-d)
    picked = []
    for i in order:
        i = int(i)
        if d[i] <= 0:
            break
        if all(abs(i - p) >= gap for p in picked):
            picked.append(i)
        if len(picked) >= count:
            break
    return sorted(picked)


def quant_palette(fg_arr: np.ndarray, k: int = 12):
    if fg_arr.size == 0:
        return []
    px = np.clip(fg_arr.astype(np.int32), 0, 255)
    q = np.clip(((px // 16) * 16 + 8), 0, 255).astype(np.int32)
    key = q[:, 0] * 65536 + q[:, 1] * 256 + q[:, 2]
    uniq, counts = np.unique(key, return_counts=True)
    order = np.argsort(-counts)[:k]
    tot = float(counts.sum())
    out = []
    for i in order:
        kv = int(uniq[i])
        r, g, b = (kv >> 16) & 255, (kv >> 8) & 255, kv & 255
        out.append({"hex": f"#{r:02x}{g:02x}{b:02x}", "rgb": [r, g, b],
                    "pct": round(100 * float(counts[i]) / tot, 1)})
    return out


def zone_lines(labels: np.ndarray, cols: int = 64, rows: int = 32):
    h, w = labels.shape
    ys = np.linspace(0, h, rows + 1).astype(int)
    xs = np.linspace(0, w, cols + 1).astype(int)
    lines = []
    for j in range(rows):
        row = []
        for i in range(cols):
            blk = labels[ys[j]:max(ys[j] + 1, ys[j + 1]), xs[i]:max(xs[i] + 1, xs[i + 1])]
            vals, counts = np.unique(blk, return_counts=True)
            row.append(ZONE_CHARS[int(vals[counts.argmax()])])
        lines.append("".join(row))
    return lines


def main() -> int:
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    summary = []
    for path in sorted(src.glob("*.png")):
        arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
        h, w, _ = arr.shape
        bgmask = flood_background(arr)
        fg = ~bgmask
        labels = classify(arr)
        sky_frac = float(((labels == 0) | (labels == 1)).mean())
        kind = "exterior" if sky_frac > 0.10 else "interior"

        lum = arr @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        rowp = np.array([lum[y][fg[y]].mean() if fg[y].any() else np.nan for y in range(h)])
        colp = np.array([lum[:, x][fg[:, x]].mean() if fg[:, x].any() else np.nan for x in range(w)])
        rowp = np.nan_to_num(rowp, nan=np.nanmean(rowp) if np.isfinite(rowp).any() else 0.0)
        colp = np.nan_to_num(colp, nan=np.nanmean(colp) if np.isfinite(colp).any() else 0.0)
        he = peaks(rowp, 12, max(2, h // 50))
        ve = peaks(colp, 16, max(2, w // 70))

        ys, xs = np.nonzero(fg)
        bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if xs.size else None
        ent = {
            "file": path.name, "w": w, "h": h, "kind": kind,
            "sky_frac": round(sky_frac, 3),
            "bg_frac": round(float(bgmask.mean()), 3),
            "coverage_pct": round(100 * float(fg.mean()), 2),
            "bbox_norm": None if bbox is None else {
                "x0": round(bbox[0] / w, 4), "y0": round(bbox[1] / h, 4),
                "x1": round(bbox[2] / w, 4), "y1": round(bbox[3] / h, 4)},
            "hedges_y": [round(p / h, 3) for p in he],
            "vedges_x": [round(p / w, 3) for p in ve],
            "palette": quant_palette(arr[fg]),
        }
        ext = extent_profile(fg, 40)

        lines = [f"{path.name}  {w}x{h}  kind={kind}  sky={sky_frac:.2f}  bg={bgmask.mean():.2f}",
                 f"bbox_norm {json.dumps(ent['bbox_norm'])}",
                 f"HEDGES y {ent['hedges_y']}",
                 f"VEDGES x {ent['vedges_x']}",
                 "PALETTE " + json.dumps(ent["palette"]),
                 "",
                 "EXTENT bands (y:left/right/width):"]
        for i in range(0, 40, 10):
            lines.append("  " + "  ".join(
                f"{e['y']:.2f}:{'-' if e['l'] is None else f'{e[chr(108)]:.2f}/{e[chr(114)]:.2f}/{e[chr(119)]:.2f}'}"
                for e in ext[i:i + 10]))
        lines.append("")
        lines.append("SKYLINE (top fg row per column /48):")
        lines.append("  " + json.dumps(skyline(fg)))
        lines.append("")
        lines.append("ZONES 64x32  legend: " + " ".join(f"{ZONE_CHARS[k]}={v}" for k, v in ZONE_NAMES.items()))
        lines.extend(zone_lines(labels))
        (out / f"{path.stem}.txt").write_text("\n".join(lines), encoding="utf-8")
        ent["zones"] = zone_lines(labels)
        summary.append(ent)

    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps([{k: v for k, v in s.items() if k != "zones"} | {"zones": s["zones"]} for s in summary],
                     indent=1)[:200])
    print("KIND SUMMMARY:")
    for s in summary:
        print(f"  {s['file'][:22]}  {s['kind']:9s} sky={s['sky_frac']:.2f} cov={s['coverage_pct']:5.1f}% "
              f"bbox={s['bbox_norm']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())