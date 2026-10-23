"""Tile the mascot action frames into 2x2 contact sheets."""
import glob
import os

from PIL import Image

OUT_DIR = r"D:\wenmai-huazhang\docs\mascot\previews"
TMP = os.path.join(OUT_DIR, "_anim_raw")
BG = (218, 221, 225, 255)
CELL = 400


def main():
    groups = {}
    for p in sorted(glob.glob(os.path.join(TMP, "*.png"))):
        name = os.path.basename(p).rsplit("-", 1)[0]
        groups.setdefault(name, []).append(p)
    if not groups:
        raise SystemExit(f"no frames in {TMP}; run render_anim.py first")

    for name, files in sorted(groups.items()):
        files = files[:4]
        sheet = Image.new("RGBA", (CELL * 2, CELL * 2), BG)
        for i, f in enumerate(files):
            im = Image.open(f).convert("RGBA")
            cell = Image.new("RGBA", (CELL, CELL), BG)
            cell.alpha_composite(im)
            sheet.alpha_composite(cell, ((i % 2) * CELL, (i // 2) * CELL))
        dst = os.path.join(OUT_DIR, f"anim-{name}.png")
        sheet.convert("RGB").save(dst, "PNG", optimize=True)
        print(f"[tile] {os.path.basename(dst)}  {sheet.size}  from {len(files)} frames")


if __name__ == "__main__":
    main()