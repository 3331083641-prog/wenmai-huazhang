"""Alpha-composite mascot previews onto the neutral light-grey backdrop.

    python scripts/mascot/compose.py                 # all _flat-*.png
    python scripts/mascot/compose.py --tag blockout  # only the blockout set
"""
import argparse
import glob
import os

from PIL import Image

OUT_DIR = r"D:\wenmai-huazhang\docs\mascot\previews"
BG = (218, 221, 225, 255)      # neutral light grey, deliberately not warm white


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()

    pat = os.path.join(OUT_DIR, "_flat-*.png")
    files = sorted(glob.glob(pat))
    if args.tag:
        files = [f for f in files
                 if (f"-{args.tag}.png" in f) == (args.tag != "")]
    if not files:
        raise SystemExit(f"no _flat-*.png in {OUT_DIR}")
    for src in files:
        stem = os.path.basename(src)[len("_flat-"):]
        dst = os.path.join(OUT_DIR, stem)
        im = Image.open(src).convert("RGBA")
        plate = Image.new("RGBA", im.size, BG)
        plate.alpha_composite(im)
        plate.convert("RGB").save(dst, "PNG", optimize=True)
        print(f"[compose] {os.path.basename(dst)}  {im.size}")


if __name__ == "__main__":
    main()