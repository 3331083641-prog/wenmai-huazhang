"""Compare our own renders numerically: elevation distinctness + exposure.

    python compare_views.py
"""
from __future__ import annotations

import itertools
import os

from PIL import Image, ImageChops, ImageStat

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "renders")


def load(name):
    return Image.open(os.path.join(R, name)).convert("RGB")


def diff(a, b):
    """Mean absolute difference in 0-255 units, plus the share of pixels >24."""
    d = ImageChops.difference(a, b)
    mean = sum(ImageStat.Stat(d).mean) / 3.0
    hist = d.convert("L").histogram()
    total = float(sum(hist))
    moved = sum(hist[25:]) / total
    return mean, moved


def exposure(im):
    g = im.convert("L")
    hist = g.histogram()
    total = float(sum(hist))
    dark = sum(hist[:45]) / total
    mid = sum(hist[45:200]) / total
    bright = sum(hist[200:]) / total
    return dark, mid, bright, ImageStat.Stat(g).mean[0]


def main():
    print("== elevation distinctness (mean |d| 0-255, share of pixels moved >24) ==")
    views = ["02_front.png", "03_left.png", "04_right.png", "05_back.png"]
    ims = {v: load(v) for v in views}
    for a, b in itertools.combinations(views, 2):
        mean, moved = diff(ims[a], ims[b])
        print("  %-14s vs %-14s  mean=%5.2f  moved=%.2f" % (a, b, mean, moved))

    print("\n== interior exposure (dark<45 / mid / blown>200, mean luma) ==")
    for name in ("07_floor1.png", "08_floor2.png", "09_ceiling.png",
                 "10_eave.png"):
        dark, mid, bright, luma = exposure(load(name))
        print("  %-16s dark=%.3f mid=%.3f bright=%.3f luma=%5.1f"
              % (name, dark, mid, bright, luma))


if __name__ == "__main__":
    main()