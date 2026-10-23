"""Measure where the model actually sits inside each render.

The sky is a vertical gradient, so the background can be sampled per row from
the left and right edges. Everything that is not background is the model, and
its bounding box tells us the framing: margins should be small and balanced,
which is what "建筑位于中央 / 不出现大面积无效背景 / 完整看到底座" means in
numbers rather than in adjectives.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image

TOL = 20.0


def analyse(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im, dtype=np.float32)
    h, w, _ = a.shape
    edge = np.concatenate([a[:, :12, :], a[:, -12:, :]], axis=1)
    bg = np.median(edge, axis=1)[:, None, :]            # per-row background colour
    mask = np.abs(a - bg).max(axis=2) > TOL              # True = model
    # ignore isolated noise: keep rows/cols with a meaningful share of model px
    rows = np.where(mask.sum(axis=1) > w * 0.02)[0]
    cols = np.where(mask.sum(axis=0) > h * 0.02)[0]
    if len(rows) == 0 or len(cols) == 0:
        return None
    return {
        "w": w, "h": h,
        "share": mask.mean(),
        "top": rows[0] / h, "bottom": 1.0 - rows[-1] / h,
        "left": cols[0] / w, "right": 1.0 - cols[-1] / w,
        "model_w": (cols[-1] - cols[0]) / w, "model_h": (rows[-1] - rows[0]) / h,
    }


def main(paths):
    print("%-22s %-10s %-26s %-24s %s"
          % ("render", "model%", "margins T/B/L/R", "model width/height", "verdict"))
    for p in paths:
        m = analyse(p)
        name = os.path.basename(p)
        if not m:
            print("%-22s all background?" % name)
            continue
        worst = max(m["top"], m["bottom"], m["left"], m["right"])
        small = min(m["top"], m["bottom"], m["left"], m["right"])
        verdict = "OK" if worst < 0.14 else ("LOOSE" if worst < 0.25 else "TOO SMALL")
        print("%-22s %5.1f%%     T%.3f B%.3f L%.3f R%.3f    %.2f x %.2f      %s"
              % (name, m["share"] * 100, m["top"], m["bottom"], m["left"], m["right"],
                 m["model_w"], m["model_h"], verdict))
        del small


if __name__ == "__main__":
    main(sys.argv[1:])