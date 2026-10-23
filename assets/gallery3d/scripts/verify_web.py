"""Measure a browser screenshot against the matching reference image.

Same statistics as measure_v2.py / compare2.py, but the "render" side is a real
browser screenshot (the shipped deliverable), not a Blender render.

    python verify_web.py shot=../screens/glb-01-exterior-clean.png ref=34905d3a

Prints coverage / dark share / mean rgb / p95 luma / 24-band fill profile and
the per-band delta against the reference. Exit code 1 when the mean absolute
band error exceeds --tol (default 0.16).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.abspath(os.path.join(HERE, "..", "references", "raw"))
SUMMARY = os.path.abspath(os.path.join(HERE, "..", "references", "analysis2", "summary.json"))
BANDS = 24


def load(path: str) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)


def background_mask(arr: np.ndarray, tol: float = 42.0) -> np.ndarray:
    """Flood fill from the four borders: everything reachable within tol of the
    local border colour is background."""
    h, w, _ = arr.shape
    bg = np.zeros((h, w), dtype=bool)
    # sample the corner colours and grow greedily (cheap two-pass approximation:
    # distance to the per-row border median)
    left = np.median(arr[:, :4], axis=1)
    right = np.median(arr[:, -4:], axis=1)
    top = np.median(arr[:4, :], axis=0)
    bottom = np.median(arr[-4:, :], axis=0)
    dl = np.linalg.norm(arr - left[:, None, :], axis=2)
    dr = np.linalg.norm(arr - right[:, None, :], axis=2)
    dt = np.linalg.norm(arr - top[None, :, :], axis=2)
    db = np.linalg.norm(arr - bottom[None, :, :], axis=2)
    edge = (dl < tol) | (dr < tol) | (dt < tol) | (db < tol)
    # keep only the connected part that touches a border
    from collections import deque
    dq = deque()
    for x in range(w):
        if edge[0, x]:
            bg[0, x] = True
            dq.append((0, x))
        if edge[h - 1, x]:
            bg[h - 1, x] = True
            dq.append((h - 1, x))
    for y in range(h):
        if edge[y, 0]:
            bg[y, 0] = True
            dq.append((y, 0))
        if edge[y, w - 1]:
            bg[y, w - 1] = True
            dq.append((y, w - 1))
    while dq:
        y, x = dq.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and not bg[ny, nx] and edge[ny, nx]:
                bg[ny, nx] = True
                dq.append((ny, nx))
    return ~bg


def band_profile(mask: np.ndarray, bands: int = BANDS) -> list:
    h = mask.shape[0]
    step = max(1, h // bands)
    out = []
    for i in range(bands):
        y0 = i * step
        y1 = min(h, y0 + step)
        if y1 <= y0:
            continue
        out.append(float(mask[y0:y1].mean()))
    return out


def stats(path: str) -> dict:
    arr = load(path)
    fg = background_mask(arr)
    lum = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
    fg_pixels = arr[fg]
    if fg_pixels.size == 0:
        fg_pixels = arr.reshape(-1, 3)
    return {
        "cover": float(fg.mean()),
        "dark": float((lum[fg] < 96).mean()) if fg.any() else 0.0,
        "mean_rgb": [float(v) for v in fg_pixels.mean(axis=0)],
        "p95_luma": float(np.percentile(lum[fg], 95)) if fg.any() else 0.0,
        "bands": band_profile(fg),
    }


def find_ref(key: str) -> str:
    for name in os.listdir(REF_DIR):
        if name.lower().startswith(key.lower()):
            return os.path.join(REF_DIR, name)
    raise SystemExit(f"no reference matching {key} in {REF_DIR}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("shot")
    ap.add_argument("ref")
    ap.add_argument("--tol", type=float, default=0.16)
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    shot = os.path.abspath(args.shot)
    ref = find_ref(args.ref)
    a = stats(ref)
    b = stats(shot)
    n = min(len(a["bands"]), len(b["bands"]))
    deltas = [abs(a["bands"][i] - b["bands"][i]) for i in range(n)]
    mae = sum(deltas) / max(1, n)

    print(f"ref  {os.path.basename(ref)}")
    print(f"shot {os.path.basename(shot)}")
    print(f"  cover   ref {a['cover']:.3f}  shot {b['cover']:.3f}  delta {b['cover'] - a['cover']:+.3f}")
    print(f"  dark    ref {a['dark']:.3f}  shot {b['dark']:.3f}  delta {b['dark'] - a['dark']:+.3f}")
    print(f"  meanLum ref {sum(a['mean_rgb']) / 3:.1f}  shot {sum(b['mean_rgb']) / 3:.1f}")
    print(f"  meanRGB ref {[round(v) for v in a['mean_rgb']]}  shot {[round(v) for v in b['mean_rgb']]}")
    print(f"  p95Lum  ref {a['p95_luma']:.1f}  shot {b['p95_luma']:.1f}")
    print("  band profile (top -> bottom)")
    print("    ref ", " ".join(f"{v:.2f}" for v in a["bands"]))
    print("    shot", " ".join(f"{v:.2f}" for v in b["bands"]))
    print("    diff", " ".join(f"{d:+.2f}" for d in deltas))
    print(f"  mean abs band error {mae:.3f} (tol {args.tol})")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"ref": ref, "shot": shot, "refStats": a, "shotStats": b,
                       "bandDelta": deltas, "mae": mae}, fh, indent=1)
    return 0 if mae <= args.tol else 1


if __name__ == "__main__":
    sys.exit(main())