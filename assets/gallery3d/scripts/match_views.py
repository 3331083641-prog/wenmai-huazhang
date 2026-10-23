"""Match each captured view to the reference it best corresponds to.

The upload order did not follow the ten-image table, so instead of trusting a
hand-written pairing we measure every (view, reference) pair with the same band
statistics and report the best match plus the full matrix. That is the honest
way to say "this render corresponds to that reference".

    python match_views.py
"""
from __future__ import annotations

import itertools
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.abspath(os.path.join(HERE, "..", "references", "raw"))
SHOTS = os.path.abspath(os.path.join(HERE, "..", "..", "..", "docs", "heritage_gallery", "screens"))
BANDS = 24

VIEWS = {
    "front34": "glb-08-exterior.png",
    "front": "glb-10-front.png",
    "back": "view-back.png",
    "left": "view-left.png",
    "right": "view-right.png",
    "top": "view-top.png",
}


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)


def foreground(arr):
    """Border-connected background mask (same rule as verify_web.py)."""
    h, w, _ = arr.shape
    left = np.median(arr[:, :4], axis=1)
    right = np.median(arr[:, -4:], axis=1)
    top = np.median(arr[:4, :], axis=0)
    bottom = np.median(arr[-4:, :], axis=0)
    tol = 42.0
    edge = (
        (np.linalg.norm(arr - left[:, None, :], axis=2) < tol)
        | (np.linalg.norm(arr - right[:, None, :], axis=2) < tol)
        | (np.linalg.norm(arr - top[None, :, :], axis=2) < tol)
        | (np.linalg.norm(arr - bottom[None, :, :], axis=2) < tol)
    )
    from collections import deque

    bg = np.zeros((h, w), dtype=bool)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if edge[y, x] and not bg[y, x]:
                bg[y, x] = True
                dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if edge[y, x] and not bg[y, x]:
                bg[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and not bg[ny, nx] and edge[ny, nx]:
                bg[ny, nx] = True
                dq.append((ny, nx))
    return ~bg


def signature(path):
    arr = load(path)
    fg = foreground(arr)
    lum = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
    h = fg.shape[0]
    step = max(1, h // BANDS)
    bands = [float(fg[i * step:(i + 1) * step].mean()) for i in range(BANDS)]
    px = arr[fg] if fg.any() else arr.reshape(-1, 3)
    return {
        "cover": float(fg.mean()),
        "dark": float((lum[fg] < 96).mean()) if fg.any() else 0.0,
        "lum": float(lum[fg].mean()) if fg.any() else 0.0,
        "rgb": [float(v) for v in px.mean(axis=0)],
        "bands": bands,
    }


def main():
    refs = {}
    for name in sorted(os.listdir(REFS)):
        if name.lower().endswith(".png"):
            refs[name] = signature(os.path.join(REFS, name))
    views = {k: signature(os.path.join(SHOTS, v)) for k, v in VIEWS.items() if os.path.exists(os.path.join(SHOTS, v))}

    keys = list(refs)
    print("pairing matrix: mean abs band error (lower = closer)")
    header = "view".ljust(9) + "".join(k.split("-")[1][:8].rjust(10) for k in keys)
    print(header)
    best = {}
    for view, sig in views.items():
        row = []
        for k in keys:
            other = refs[k]
            err = sum(abs(a - b) for a, b in zip(sig["bands"], other["bands"])) / BANDS
            row.append(err)
        best[view] = keys[int(np.argmin(row))]
        print(view.ljust(9) + "".join(f"{v:10.3f}" for v in row))

    print()
    print("best match per view")
    for view, k in best.items():
        a, b = views[view], refs[k]
        print(
            f"  {view:8s} -> {k.split('-')[1][:8]}  "
            f"cover {a['cover']:.3f}/{b['cover']:.3f}  "
            f"dark {a['dark']:.3f}/{b['dark']:.3f}  "
            f"lum {a['lum']:.1f}/{b['lum']:.1f}"
        )


if __name__ == "__main__":
    main()