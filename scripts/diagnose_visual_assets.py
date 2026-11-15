#!/usr/bin/env python3
"""
diagnose_visual_assets.py
Portable diagnostic tool for inspecting transparency, dimensions, and alpha metrics of UI assets.
"""

import os
import sys
import argparse
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASSETS_DIR = REPO_ROOT / "frontend" / "public" / "visuals" / "vnext"

def analyze_asset(assets_dir: Path, name: str):
    path = assets_dir / name
    if not path.exists():
        print(f"[-] {name} does not exist at {path}")
        return
    
    size_kb = path.stat().st_size / 1024.0
    pil_img = Image.open(str(path))
    cv_img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    
    w, h = pil_img.size
    mode = pil_img.mode
    has_alpha = (cv_img.shape[2] == 4) if len(cv_img.shape) == 3 else False
    
    print(f"\n==========================================")
    print(f"Asset: {name}")
    print(f"  Dimensions: {w} x {h}")
    print(f"  Mode: {mode}")
    print(f"  Size: {size_kb:.1f} KB")
    print(f"  Has Alpha: {has_alpha}")
    
    if has_alpha:
        alpha = cv_img[:, :, 3]
        zero_count = int(np.sum(alpha == 0))
        full_count = int(np.sum(alpha == 255))
        trans_count = int(np.sum((alpha > 0) & (alpha < 255)))
        total_pixels = w * h
        print(f"  Alpha breakdown:")
        print(f"    Fully transparent (0): {zero_count} ({zero_count / total_pixels * 100:.1f}%)")
        print(f"    Semi-transparent (1-254): {trans_count} ({trans_count / total_pixels * 100:.1f}%)")
        print(f"    Fully opaque (255): {full_count} ({full_count / total_pixels * 100:.1f}%)")
        
        # Check corners to see if they are transparent
        corners = [
            ("Top-Left", alpha[0:20, 0:20]),
            ("Top-Right", alpha[0:20, -20:]),
            ("Bottom-Left", alpha[-20:, 0:20]),
            ("Bottom-Right", alpha[-20:, -20:])
        ]
        print(f"  Corner Alpha Analysis:")
        for cname, cpatch in corners:
            mean_a = float(np.mean(cpatch))
            max_a = int(np.max(cpatch))
            print(f"    {cname}: mean={mean_a:.1f}, max={max_a}")
            
        # Check outer border alpha
        border_alpha = np.concatenate([
            alpha[0, :], alpha[-1, :], alpha[:, 0], alpha[:, -1]
        ])
        border_non_zero = int(np.sum(border_alpha > 0))
        print(f"  Outer 1px border non-zero alpha count: {border_non_zero} / {len(border_alpha)} ({border_non_zero/len(border_alpha)*100:.1f}%)")

def main():
    parser = argparse.ArgumentParser(description="Diagnose visual asset alpha channels and geometries.")
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=DEFAULT_ASSETS_DIR,
        help="Directory containing vnext assets (default: frontend/public/visuals/vnext)"
    )
    args = parser.parse_args()

    assets = [
        "ui-img-01-cultural-brush.png",
        "ui-img-02-heritage-pavilion.png",
        "ui-img-03-celadon-vessel.png",
        "ui-img-04-archive-casket.png",
        "ui-img-05-ink-bloom-sprite.png"
    ]
    for asset in assets:
        analyze_asset(args.assets_dir, asset)

if __name__ == "__main__":
    main()
