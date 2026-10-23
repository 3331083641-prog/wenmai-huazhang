"""用真实的三层素材拼一张「分层示意」图，供首页「画境漫游」卡片使用。

不是画出来的示意图：每一带都是从 frontend/public/interactive/songhua/ 里
对应的真实图层文件中截取的原样像素，只做拼接与投影。
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(r"D:\wenmai-huazhang")
LAYER_DIR = ROOT / "frontend" / "public" / "interactive" / "songhua"
OUT = LAYER_DIR / "layers-preview.webp"

CANVAS = (1280, 800)
PAPER = (247, 239, 224)

# 每一带：(图层文件, 源图 y 起点, 源图高度, 目标宽度)
BANDS = [
    ("layer-far.webp", 10, 200, 900),    # 远山与天空
    ("layer-mid.webp", 300, 200, 900),   # 中景山峦
    ("layer-near.webp", 780, 200, 900),  # 近景水面与坡石
]

GAP = 22
SHADOW_BLUR = 16


def shadow_mask(size: tuple[int, int], radius: int = 18) -> Image.Image:
    mask = Image.new("L", size, 0)
    from PIL import ImageDraw

    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), (size[0] - 1, size[1] - 1)], radius=radius, fill=170)
    return mask.filter(ImageFilter.GaussianBlur(SHADOW_BLUR))


def main() -> None:
    canvas = Image.new("RGB", CANVAS, PAPER)

    slices = []
    for name, top, height, width in BANDS:
        with Image.open(LAYER_DIR / name) as layer:
            plane = layer.convert("RGBA").crop((0, top, layer.width, top + height))
        ratio = width / plane.width
        plane = plane.resize((width, max(1, round(height * ratio))), Image.LANCZOS)
        # 图层带 alpha，铺到宣纸上（透明处就是纸）
        backed = Image.new("RGBA", plane.size, PAPER + (255,))
        backed.alpha_composite(plane)
        slices.append(backed.convert("RGB"))

    total_h = sum(item.height for item in slices) + GAP * (len(slices) - 1)
    y = (CANVAS[1] - total_h) // 2

    for band in slices:
        x = (CANVAS[0] - band.width) // 2
        # 投影
        shadow = Image.new("RGB", band.size, PAPER)
        shadow.paste((120, 104, 88), (0, 0), shadow_mask(band.size))
        canvas.paste(shadow, (x, y + 8))
        canvas.paste(band, (x, y))
        y += band.height + GAP

    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, format="WEBP", quality=88, method=6)
    print(f"saved {OUT} ({OUT.stat().st_size} bytes, {CANVAS[0]}x{CANVAS[1]})")


if __name__ == "__main__":
    main()