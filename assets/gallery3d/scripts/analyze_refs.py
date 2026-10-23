"""Deterministic local reference-image analysis (no network, no vision model).

Reads the 10 pasted reference PNGs and writes, per image:
  - a manifest entry (size, background estimate, silhouette bbox)
  - a quantized palette with coverage
  - a luminance ASCII map and a quantized-colour ASCII map

The ASCII maps are the fallback "eyes" when the vision proxy is unavailable:
they preserve silhouette, value structure and colour blocking well enough to
derive architecture proportions.

Usage:
  python analyze_refs.py <src_dir> <out_dir>
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

LUM_RAMP = " .:-=+*#%@"
# Compact palette letters for the colour map.
PALETTE_LETTERS = "abcdefghijklmnopqrstuvwxyz"


def load_rgb(path: Path) -> np.ndarray:
    im = Image.open(path).convert("RGB")
    return np.asarray(im, dtype=np.float32)


def estimate_background(arr: np.ndarray) -> tuple[np.ndarray, float]:
    """Median of a border frame = studio background colour."""
    h, w, _ = arr.shape
    b = max(2, min(h, w) // 64)
    frame = np.concatenate(
        [
            arr[:b].reshape(-1, 3),
            arr[-b:].reshape(-1, 3),
            arr[:, :b].reshape(-1, 3),
            arr[:, -b:].reshape(-1, 3),
        ]
    )
    med = np.median(frame, axis=0)
    dist = np.linalg.norm(frame - med, axis=1)
    spread = float(np.percentile(dist, 90))
    return med, spread


def silhouette(arr: np.ndarray, bg: np.ndarray, thresh: float) -> np.ndarray:
    d = np.linalg.norm(arr - bg, axis=2)
    return d > thresh


def palette(arr: np.ndarray, mask: np.ndarray, k: int = 12):
    px = arr[mask]
    if px.size == 0:
        px = arr.reshape(-1, 3)
    q = (px // 16 * 16 + 8).astype(np.int32)
    keys = q[:, 0] * 65536 + q[:, 1] * 256 + q[:, 2]
    uniq, counts = np.unique(keys, return_counts=True)
    order = np.argsort(-counts)[:k]
    total = counts.sum()
    out = []
    for i in order:
        key = int(uniq[i])
        r, g, b = key >> 16, (key >> 8) & 255, key & 255
        out.append(
            {
                "hex": f"#{r:02x}{g:02x}{b:02x}",
                "rgb": [r, g, b],
                "pct": round(100.0 * float(counts[i]) / float(total), 2),
            }
        )
    return out


def downsample(arr: np.ndarray, cols: int, rows: int) -> np.ndarray:
    """Area-average downsample."""
    h, w, _ = arr.shape
    ys = np.linspace(0, h, rows + 1).astype(int)
    xs = np.linspace(0, w, cols + 1).astype(int)
    out = np.zeros((rows, cols, 3), dtype=np.float32)
    for j in range(rows):
        for i in range(cols):
            blk = arr[ys[j] : max(ys[j] + 1, ys[j + 1]), xs[i] : max(xs[i] + 1, xs[i + 1])]
            out[j, i] = blk.reshape(-1, 3).mean(axis=0)
    return out


def ascii_luma(small: np.ndarray) -> list[str]:
    lum = small @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    lo, hi = float(lum.min()), float(lum.max())
    if hi - lo < 1e-3:
        hi = lo + 1.0
    norm = (lum - lo) / (hi - lo)
    idx = np.clip((norm * (len(LUM_RAMP) - 1)).round().astype(int), 0, len(LUM_RAMP) - 1)
    return ["".join(LUM_RAMP[v] for v in row) for row in idx]


def ascii_colour(small: np.ndarray, pal: list[dict], bg: np.ndarray, thresh: float):
    """Assign each cell to nearest palette colour or '.' for background."""
    pal_rgb = np.array([p["rgb"] for p in pal[: min(len(pal), 26)]], dtype=np.float32)
    letters = PALETTE_LETTERS[: len(pal_rgb)]
    flat = small.reshape(-1, 3)
    d_bg = np.linalg.norm(flat - bg, axis=1)
    d_pal = np.linalg.norm(flat[:, None, :] - pal_rgb[None, :, :], axis=2)
    near = d_pal.argmin(axis=1)
    cells = np.where(d_bg > thresh, np.array(list(letters))[near], ".")
    return cells.reshape(small.shape[0], small.shape[1])


def bbox_of(mask: np.ndarray) -> list[int] | None:
    ys, xs = np.nonzero(mask)
    if ys.size == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


def main() -> int:
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in src.glob("*.png"))
    manifest = []

    for path in files:
        arr = load_rgb(path)
        h, w, _ = arr.shape
        bg, spread = estimate_background(arr)
        thresh = max(10.0, spread * 1.4 + 6.0)
        mask = silhouette(arr, bg, thresh)

        # Fill holes: a pixel is foreground if it differs OR is enclosed.
        filled = mask.copy()
        for _ in range(3):
            nb = np.zeros_like(filled)
            nb[1:, :] |= filled[:-1, :]
            nb[:-1, :] |= filled[1:, :]
            nb[:, 1:] |= filled[:, :-1]
            nb[:, :-1] |= filled[:, 1:]
            filled = filled | (nb & (np.linalg.norm(arr - bg, axis=2) > thresh * 0.45))

        bb = bbox_of(mask)
        bb_f = bbox_of(filled)
        pal = palette(arr, mask, k=14)

        cols, rows = 96, 48
        small = downsample(arr, cols, rows)
        luma_map = ascii_luma(small)
        col_map = ascii_colour(small, pal, bg, thresh)

        stem = path.stem
        txt = []
        txt.append(f"FILE {path.name}  {w}x{h}  aspect={w / h:.4f}")
        txt.append(f"BG {tuple(int(v) for v in bg)}  border_spread={spread:.1f}  thresh={thresh:.1f}")
        txt.append(f"BBOX_mask {bb}  BBOX_filled {bb_f}")
        if bb:
            txt.append(
                "BBOX_norm " + json.dumps(
                    {
                        "x0": round(bb[0] / w, 4), "y0": round(bb[1] / h, 4),
                        "x1": round(bb[2] / w, 4), "y1": round(bb[3] / h, 4),
                        "w": round((bb[2] - bb[0]) / w, 4), "h": round((bb[3] - bb[1]) / h, 4),
                    }
                )
            )
        txt.append("PALETTE " + json.dumps(pal))
        txt.append("")
        txt.append(f"LUMA {cols}x{rows}  ramp=[{LUM_RAMP}]")
        txt.extend(luma_map)
        txt.append("")
        txt.append(f"COLOR {cols}x{rows}  '.'=background  letters=PALETTE order  palette={PALETTE_LETTERS[:len(pal)]}")
        txt.extend("".join(r) for r in col_map)
        txt.append("")

        (out / f"{stem}.txt").write_text("\n".join(txt), encoding="utf-8")
        manifest.append(
            {
                "file": path.name,
                "w": w, "h": h, "aspect": round(w / h, 4),
                "bg": [int(v) for v in bg],
                "bbox": bb,
                "bbox_filled": bb_f,
                "coverage_pct": round(100.0 * float(mask.mean()), 2),
                "palette": pal,
            }
        )

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps([{k: v for k, v in m.items() if k != "palette"} for m in manifest], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())