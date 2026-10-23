"""Numeric read-out of the gallery renders (no vision model involved).

    python check_render.py <png> [<png> ...]

Reports, per image:
  sky      mean RGB / saturation / blue share of the top sky band
  black    share of near-black pixels (light leaks, crushed shadows)
  clip     share of blown-out pixels
  bottom   mean RGB of the lowest 12 px row (does the plinth reach the frame?)
  subject  share of pixels that differ from the sky (how much model is in frame)
"""
from __future__ import annotations

import sys

from PIL import Image


def band(im, y0, y1):
    w, h = im.size
    px = im.load()
    step = max(1, w // 320)
    red = green = blue = n = 0
    for y in range(y0, y1, 2):
        for x in range(0, w, step):
            r, g, b = px[x, y][:3]
            red += r
            green += g
            blue += b
            n += 1
    return red / n, green / n, blue / n


def sat(rgb):
    hi = max(rgb)
    lo = min(rgb)
    return 0.0 if hi == 0 else (hi - lo) / hi


def main(paths):
    for path in paths:
        im = Image.open(path).convert("RGB")
        w, h = im.size
        px = im.load()
        sky = band(im, 0, max(2, int(h * 0.10)))
        bottom = band(im, h - 12, h)
        black = clip = 0
        blueish = 0
        n = 0
        step = max(1, w // 360)
        for y in range(0, h, 2):
            for x in range(0, w, step):
                r, g, b = px[x, y]
                n += 1
                if r < 26 and g < 26 and b < 26:
                    black += 1
                if r > 250 and g > 250 and b > 250:
                    clip += 1
                if b > r + 8 and b > g + 4:
                    blueish += 1
        print("%-26s %dx%d" % (path.rsplit("\\", 1)[-1], w, h))
        print("  sky   rgb(%3.0f,%3.0f,%3.0f) sat=%.3f blue_share=%.3f"
              % (sky[0], sky[1], sky[2], sat(sky), blueish / n))
        print("  black=%.4f  clip=%.4f  bottom_rgb(%3.0f,%3.0f,%3.0f)"
              % (black / n, clip / n, bottom[0], bottom[1], bottom[2]))


if __name__ == "__main__":
    main(sys.argv[1:])