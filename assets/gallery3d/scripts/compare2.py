"""Compare our renders with the measured reference images.

  python compare2.py

Foreground is estimated per row from the border pixels (a smooth sky gradient
breaks a single-colour flood fill, and the alpha channel is unreliable on some
shots). The same estimator runs on the references, so the two sets are
comparable. Only silhouette, coverage, band fill and palette statistics are
claimed - nothing about pixel-level identity.
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDERS = os.path.join(HERE, "renders")
REFS = os.path.join(HERE, "references", "raw")
OUT = os.path.join(HERE, "renders", "compare2.json")

# view -> reference file (from the measured analysis: upload order differs)
PAIRS = [
    ("01_front34.png", "34905d3a"),
    ("06_top.png", "881293cb"),
]


def bg_estimate(arr):
    """Per-row background colour from the image borders."""
    h, w = arr.shape[:2]
    band = np.concatenate([arr[:, :6], arr[:, -6:]], axis=1)
    return np.median(band, axis=1)          # (h, 3)


def mask_of(arr, tol=20.0):
    bg = bg_estimate(arr)
    diff = np.abs(arr - bg[:, None, :]).max(axis=2)
    return diff > tol


def stats(path):
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    h, w = arr.shape[:2]
    m = mask_of(arr)
    rows = np.where(m.any(axis=1))[0]
    cols = np.where(m.any(axis=0))[0]
    if rows.size == 0:
        return None
    prof = []
    for j in range(24):
        y0, y1 = int(h * j / 24), max(int(h * j / 24) + 1, int(h * (j + 1) / 24))
        prof.append(round(float(m[y0:y1].mean()), 3))
    fg = arr[m]
    return {
        "cover": round(float(m.mean()) * 100, 1),
        "bbox": [round(cols.min() / w, 3), round(rows.min() / h, 3),
                 round(cols.max() / w, 3), round(rows.max() / h, 3)],
        "band_fill": prof,
        "mean_rgb": [int(v) for v in fg.mean(axis=0)],
        "p95_luma": round(float(np.percentile(fg.mean(axis=1), 95)), 1),
        "dark_share": round(float((fg.mean(axis=1) < 110).mean()) * 100, 1),
        "warm_share": round(float(((fg[:, 0] - fg[:, 2]) > 18).mean())) * 100,
    }


def ref_by_hash():
    out = {}
    for p in glob.glob(os.path.join(REFS, "*.png")):
        out[os.path.basename(p).split("-")[-1].split(".")[0]] = p
    return out


def main():
    refs = ref_by_hash()
    mine = {os.path.basename(p): stats(p)
            for p in sorted(glob.glob(os.path.join(RENDERS, "*.png")))}
    res = {}
    for name, s in mine.items():
        if s is None:
            print(f"{name:>16} EMPTY")
            continue
        print(f"{name:>16} cover={s['cover']:5.1f}% bbox={s['bbox']} "
              f"mean={s['mean_rgb']} dark={s['dark_share']}% warm={s['warm_share']}%")
        res[name] = s

    print("\n--- reference exteriors (same estimator) ---")
    for name, key in PAIRS:
        p = refs.get(key)
        if not p:
            continue
        s = stats(p)
        print(f"{key:>12} cover={s['cover']:5.1f}% bbox={s['bbox']} "
              f"mean={s['mean_rgb']} dark={s['dark_share']}% warm={s['warm_share']}%")
        res[f"REF_{key}"] = s
        m = res.get(name)
        if m:
            print(f"   delta {name}: dCover={m['cover'] - s['cover']:+.1f} "
                  f"dDark={m['dark_share'] - s['dark_share']:+.1f} "
                  f"dWarm={m['warm_share'] - s['warm_share']:+.1f}")
            a = np.array(m["band_fill"])
            b = np.array(s["band_fill"])
            print("   band_fill mine:", " ".join(f"{v:.2f}" for v in a))
            print("   band_fill ref :", " ".join(f"{v:.2f}" for v in b))
            print(f"   band MAE={np.abs(a - b).mean():.3f}")

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()