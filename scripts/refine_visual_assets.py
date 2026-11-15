#!/usr/bin/env python3
"""
refine_visual_assets.py
Portable processor to extract true alpha channels, clear checkerboard artifacts,
feather boundaries, and generate optimized WebP + PNG assets.
"""

import os
import sys
import argparse
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "frontend" / "public" / "visuals" / "vnext"

def get_default_input_dir() -> Path:
    env_dir = os.environ.get("WENMAI_RAW_ASSETS_DIR")
    if env_dir and Path(env_dir).exists():
        return Path(env_dir)
    # Check if repo has a raw_assets folder
    local_raw = REPO_ROOT / "raw_assets"
    if local_raw.exists():
        return local_raw
    # Check default conversation artifact folder if present
    appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("USERPROFILE")
    if appdata:
        gemini_dir = Path(appdata) / ".gemini" / "antigravity" / "brain"
        if gemini_dir.exists():
            for p in gemini_dir.glob("*/.user_uploaded"):
                if p.exists() and any(p.glob("media_1794755004504_32de8504.*")):
                    return p
    return local_raw

def process_asset_01(input_dir: Path, output_dir: Path):
    print("Processing Asset 01: Cultural Brush...")
    candidates = list(input_dir.glob("*32de8504*.png")) + list(input_dir.glob("*brush*.*"))
    if not candidates:
        print(f"  [!] Asset 01 raw file not found in {input_dir}, skipping.")
        return
    orig = candidates[0]
    img = cv2.imread(str(orig), cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"  [!] Failed to read {orig}")
        return
    
    a = img[:, :, 3].astype(np.float32)
    ramp = np.clip((a - 12.0) / (26.0 - 12.0), 0.0, 1.0)
    smooth_ramp = ramp * ramp * (3.0 - 2.0 * ramp)
    new_a = np.where(a <= 12.0, 0.0, a * smooth_ramp)
    
    new_a[0:3, :] = 0
    new_a[-3:, :] = 0
    new_a[:, 0:3] = 0
    new_a[:, -3:] = 0
    
    img[:, :, 3] = np.clip(new_a, 0, 255).astype(np.uint8)
    
    out_png = output_dir / "ui-img-01-cultural-brush.png"
    cv2.imwrite(str(out_png), img)
    
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA))
    out_webp = output_dir / "ui-img-01-cultural-brush.webp"
    pil_img.save(str(out_webp), "WEBP", quality=95, method=6)
    
    print(f"  Saved PNG: {out_png.stat().st_size / 1024:.1f} KB, WebP: {out_webp.stat().st_size / 1024:.1f} KB")

def process_black_bg(input_dir: Path, output_dir: Path, pattern: str, output_base: str):
    print(f"Processing Black Background Asset: {output_base}...")
    candidates = list(input_dir.glob(f"*{pattern}*"))
    if not candidates:
        print(f"  [!] Raw file for pattern '{pattern}' not found in {input_dir}, skipping.")
        return
    orig = candidates[0]
    bgr = cv2.imread(str(orig))
    if bgr is None:
        print(f"  [!] Failed to read {orig}")
        return
    
    max_val = np.maximum.reduce([bgr[:,:,0], bgr[:,:,1], bgr[:,:,2]])
    fg_mask = (max_val > 12).astype(np.uint8) * 255
    
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel_close)
    
    dist_inside = cv2.distanceTransform(fg_mask, cv2.DIST_L2, 3)
    dist_outside = cv2.distanceTransform(255 - fg_mask, cv2.DIST_L2, 3)
    
    alpha = np.clip((dist_inside - dist_outside + 1.2) / 2.4 * 255.0, 0.0, 255.0).astype(np.uint8)
    
    alpha[0:2, :] = 0
    alpha[-2:, :] = 0
    alpha[:, 0:2] = 0
    alpha[:, -2:] = 0
    
    rgba = np.dstack([bgr, alpha])
    
    out_png = output_dir / f"{output_base}.png"
    cv2.imwrite(str(out_png), rgba)
    
    pil_img = Image.fromarray(cv2.cvtColor(rgba, cv2.COLOR_BGRA2RGBA))
    out_webp = output_dir / f"{output_base}.webp"
    pil_img.save(str(out_webp), "WEBP", quality=95, method=6)
    
    print(f"  Saved PNG: {out_png.stat().st_size / 1024:.1f} KB, WebP: {out_webp.stat().st_size / 1024:.1f} KB")

def process_checkerboard_bg(input_dir: Path, output_dir: Path, pattern: str, output_base: str):
    print(f"Processing Checkerboard Background Asset: {output_base}...")
    candidates = list(input_dir.glob(f"*{pattern}*"))
    if not candidates:
        print(f"  [!] Raw file for pattern '{pattern}' not found in {input_dir}, skipping.")
        return
    orig = candidates[0]
    bgr = cv2.imread(str(orig))
    if bgr is None:
        print(f"  [!] Failed to read {orig}")
        return
    
    b = bgr[:,:,0].astype(int)
    g = bgr[:,:,1].astype(int)
    r = bgr[:,:,2].astype(int)
    
    diff = np.maximum.reduce([np.abs(r-g), np.abs(g-b), np.abs(r-b)])
    min_val = np.minimum.reduce([r, g, b])
    
    is_checkerboard = (min_val >= 228) & (diff <= 15)
    fg_mask = (~is_checkerboard).astype(np.uint8) * 255
    
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel_close)
    
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(fg_mask)
    clean_fg = np.zeros_like(fg_mask)
    for lbl in range(1, num_labels):
        if stats[lbl, cv2.CC_STAT_AREA] >= 30:
            clean_fg[labels == lbl] = 255
            
    dist_inside = cv2.distanceTransform(clean_fg, cv2.DIST_L2, 3)
    dist_outside = cv2.distanceTransform(255 - clean_fg, cv2.DIST_L2, 3)
    alpha = np.clip((dist_inside - dist_outside + 1.2) / 2.4 * 255.0, 0.0, 255.0).astype(np.uint8)
    
    alpha[0:2, :] = 0
    alpha[-2:, :] = 0
    alpha[:, 0:2] = 0
    alpha[:, -2:] = 0
    
    rgba = np.dstack([bgr, alpha])
    
    out_png = output_dir / f"{output_base}.png"
    cv2.imwrite(str(out_png), rgba)
    
    pil_img = Image.fromarray(cv2.cvtColor(rgba, cv2.COLOR_BGRA2RGBA))
    out_webp = output_dir / f"{output_base}.webp"
    pil_img.save(str(out_webp), "WEBP", quality=95, method=6)
    
    print(f"  Saved PNG: {out_png.stat().st_size / 1024:.1f} KB, WebP: {out_webp.stat().st_size / 1024:.1f} KB")

def main():
    parser = argparse.ArgumentParser(description="Process and refine visual assets into high-quality WebP and PNG.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=get_default_input_dir(),
        help="Directory containing uploaded raw asset files"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Target directory to write output assets"
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Refining assets from '{args.input_dir}' to '{args.output_dir}'...")

    process_asset_01(args.input_dir, args.output_dir)
    process_black_bg(args.input_dir, args.output_dir, "0cdc88a1", "ui-img-02-heritage-pavilion")
    process_black_bg(args.input_dir, args.output_dir, "645c216c", "ui-img-03-celadon-vessel")
    process_checkerboard_bg(args.input_dir, args.output_dir, "a46e1ba9", "ui-img-04-archive-casket")
    process_checkerboard_bg(args.input_dir, args.output_dir, "b84267cd", "ui-img-05-ink-bloom-sprite")
    print("\nVisual asset refinement process completed.")

if __name__ == "__main__":
    main()
