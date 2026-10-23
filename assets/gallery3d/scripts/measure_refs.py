"""Quantitative reference measurement: silhouette profiles, banding, bay periodicity.

Instead of asking a vision model to describe the ten references, this derives
numbers a modeller can build from:

  extent   : horizontal silhouette extent (normalised) per height band
  skyline  : top-most foreground row per column  -> roof ridge / eave curve
  hedges   : strongest horizontal boundaries      -> eave, floor, base lines
  vedges   : strongest vertical boundaries        -> bay / column rhythm
  zones    : named colour-zone map                -> where materials live

Usage:
  python measure_refs.py <src_dir> <out_dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# Named buckets tuned for a Chinese timber gallery on a stone base.
ZONES = [
    ("sky",   (206, 226, 246)),
    ("cloud", (245, 249, 253)),
    ("wall",  (238, 232, 218)),   # warm off-white plaster
    ("stone", (196, 192, 184)),   # light carved stone base
    ("tile",  (126, 136, 142)),   # blue-grey roof tile
    ("slate", ( 74,  82,  92)),   # dark tile / shadow under eaves
    ("wood",  (146, 100,  66)),   # warm timber
    ("wdeep", ( 86,  56,  38)),   # dark timber / door leaf
    ("red",   (176,  58,  44)),   # lantern / lacquer
    ("gold",  (198, 158,  84)),   # gilded ornament
    ("green", ( 96, 132,  74)),   # planting
    ("ink",   ( 28,  26,  26)),   # voids, deep shadow
    ("sky2",  (168, 200, 236)),   # lower sky gradient
]
ZONE_KEYS = "abcdefghijklm"
ZONE_LOOKUP = {name: ZONE_KEYS[i] for i, (name, _) in enumerate(ZONES)}


def load(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)


def bg_colour(arr: np.ndarray) -> np.ndarray:
    h, w, _ = arr.shape
    b = max(2, min(h, w) // 64)
    frame = np.concatenate([arr[:b].reshape(-1, 3), arr[-b:].reshape(-1, 3),
                            arr[:, :b].reshape(-1, 3), arr[:, -b:].reshape(-1, 3)])
    return np.median(frame, axis=0)


def mask_of(arr: np.ndarray, bg: np.ndarray) -> np.ndarray:
    d = np.linalg.norm(arr - bg, axis=2)
    base = d > 18.0
    # keep coherent blobs: drop isolated specks via 3x3 neighbour agreement
    nb = np.zeros_like(base, dtype=np.int16)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            nb += np.roll(np.roll(base, dy, 0), dx, 1).astype(np.int16)
    return base & (nb >= 2)


def luminance(arr: np.ndarray) -> np.ndarray:
    return arr @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def extent_profile(mask: np.ndarray, bands: int = 40):
    h, w = mask.shape
    rows = []
    for j in range(bands):
        y0 = int(h * j / bands)
        y1 = max(y0 + 1, int(h * (j + 1) / bands))
        band = mask[y0:y1]
        cols = np.nonzero(band.any(axis=0))[0]
        if cols.size == 0:
            rows.append({"y": round((j + 0.5) / bands, 3), "l": None, "r": None, "w": 0.0})
        else:
            rows.append({
                "y": round((j + 0.5) / bands, 3),
                "l": round(float(cols.min()) / w, 4),
                "r": round(float(cols.max()) / w, 4),
                "w": round(float(cols.max() - cols.min()) / w, 4),
            })
    return rows


def skyline(mask: np.ndarray, cols: int = 48):
    h, w = mask.shape
    out = []
    for i in range(cols):
        x0 = int(w * i / cols)
        x1 = max(x0 + 1, int(w * (i + 1) / cols))
        col = mask[:, x0:x1].any(axis=1)
        idx = np.nonzero(col)[0]
        out.append(round(float(idx.min()) / h, 4) if idx.size else None)
    return out


def strong_edges(profile: np.ndarray, count: int, min_gap: int):
    """Peaks of |derivative| with non-maximum suppression."""
    if profile.size < 3:
        return []
    p = profile - profile.mean()
    d = np.abs(np.gradient(p))
    order = np.argsort(-d)
    picked = []
    for i in order:
        if d[i] <= 0:
            break
        if all(abs(int(i) - p2) >= min_gap for p2 in picked):
            picked.append(int(i))
        if len(picked) >= count:
            break
    return sorted(picked)


def zone_map(arr: np.ndarray, mask: np.ndarray, cols: int = 64, rows: int = 32):
    h, w, _ = arr.shape
    pal = np.array([c for _, c in ZONES], dtype=np.float32)
    ys = np.linspace(0, h, rows + 1).astype(int)
    xs = np.linspace(0, w, cols + 1).astype(int)
    lines = []
    for j in range(rows):
        line = []
        for i in range(cols):
            blk = arr[ys[j]:max(ys[j] + 1, ys[j + 1]), xs[i]:max(xs[i] + 1, xs[i + 1])]
            mblk = mask[ys[j]:max(ys[j] + 1, ys[j + 1]), xs[i]:max(xs[i] + 1, xs[i + 1])]
            mean = blk.reshape(-1, 3).mean(axis=0)
            if mblk.mean() < 0.30:
                line.append(".")
            else:
                line.append(ZONE_KEYS[int(np.linalg.norm(pal - mean, axis=1).argmin())])
        lines.append("".join(line))
    return lines


def palette(arr: np.ndarray, mask: np.ndarray, k: int = 10):
    px = arr[mask] if mask.any() else arr.reshape(-1, 3)
    q = (px // 12 * 12 + 6).astype(np.int32)
    keys = q[:, 0] * 65536 + q[:, 1] * 256 + q[:, 2]
    uniq, counts = np.unique(keys, return_counts=True)
    order = np.argsort(-counts)[:k]
    tot = float(counts.sum())
    res = []
    for i in order:
        key = int(uniq[i])
        r, g, b = key >> 16, (key >> 8) & 255, key & 255
        res.append({"hex": f"#{r:02x}{g:02x}{b:02x}", "pct": round(100 * counts[i] / tot, 1)})
    return res


def main() -> int:
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    summary = []
    for path in sorted(src.glob("*.png")):
        arr = load(path)
        h, w, _ = arr.shape
        bg = bg_colour(arr)
        mask = mask_of(arr, bg)
        lum = luminance(arr)
        mrow = np.where(mask.any(axis=1)[:, None], lum, np.nan)
        # rows/cols edges only where foreground exists
        colprof = np.nan_to_num(np.nanmean(mrow, axis=1), nan=0.0)
        mcol = np.where(mask.any(axis=0)[None, :], lum, np.nan)
        rowprof = np.nan_to_num(np.nanmean(mcol, axis=0), nan=0.0)
        he = strong_edges(colprof, 14, max(2, h // 60))
        ve = strong_edges(rowprof, 18, max(2, w // 80))
        ext = extent_profile(mask, 40)
        widths = [e["w"] for e in ext if e["l"] is not None]
        max_w = max(widths) if widths else 0.0
        entries = {
            "file": path.name, "w": w, "h": h,
            "bg": [int(v) for v in bg],
            "coverage_pct": round(100 * float(mask.mean()), 2),
            "max_width": max_w,
            "hedges_y": [round(y / h, 4) for y in he],
            "vedges_x": [round(x / w, 4) for x in ve],
            "palette": palette(arr, mask),
        }
        lines = [json.dumps(entries, indent=1), "",
                 "EXTENT (y, left, right, width) normalised:",
                 "  " + "  ".join(
                     f"{e['y']:.2f}:{'-' if e['l'] is None else f'{e[chr(108)]:.2f}/{e[chr(114)]:.2f}/{e[chr(119)]:.2f}'}"
                     for e in ext[:20]),
                 "  " + "  ".join(
                     f"{e['y']:.2f}:{'-' if e['l'] is None else f'{e[chr(108)]:.2f}/{e[chr(114)]:.2f}/{e[chr(119)]:.2f}'}"
                     for e in ext[20:]),
                 "",
                 "SKYLINE (top row per column, 48 cols):",
                 "  " + str(skyline(mask)),
                 "",
                 "ZONES  . = background/empty",
                 "  legend: " + "  ".join(f"{ZONE_KEYS[i]}={n}" for i, (n, _) in enumerate(ZONES)),
                 ]
        lines.extend("  " + ln for ln in zone_map(arr, mask))
        txt = "\n".join(lines)
        (out / f"{path.stem}.txt").write_text(txt, encoding="utf-8")
        summary.append(entries | {"zone_lines": zone_map(arr, mask)})
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps([{k: v for k, v in s.items() if k != "zone_lines"} for s in summary], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())