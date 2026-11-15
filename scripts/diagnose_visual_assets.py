import os
import cv2
import numpy as np
from PIL import Image

ASSETS_DIR = r"D:\wenmai-huazhang\frontend\public\visuals\vnext"

def analyze_asset(name):
    path = os.path.join(ASSETS_DIR, name)
    if not os.path.exists(path):
        print(f"[-] {name} does not exist at {path}")
        return
    
    size_kb = os.path.getsize(path) / 1024.0
    pil_img = Image.open(path)
    cv_img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    
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
        zero_count = np.sum(alpha == 0)
        full_count = np.sum(alpha == 255)
        trans_count = np.sum((alpha > 0) & (alpha < 255))
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
            mean_a = np.mean(cpatch)
            max_a = np.max(cpatch)
            print(f"    {cname}: mean={mean_a:.1f}, max={max_a}")
            
        # Check RGB values where alpha == 0 vs alpha > 0
        rgb = cv_img[:, :, :3]
        # Check if there are visible checkerboard patterns in opaque areas near boundaries
        # Specifically check background leakage
        border_alpha = np.concatenate([
            alpha[0, :], alpha[-1, :], alpha[:, 0], alpha[:, -1]
        ])
        border_non_zero = np.sum(border_alpha > 0)
        print(f"  Outer 1px border non-zero alpha count: {border_non_zero} / {len(border_alpha)} ({border_non_zero/len(border_alpha)*100:.1f}%)")

def main():
    assets = [
        "ui-img-01-cultural-brush.png",
        "ui-img-02-heritage-pavilion.png",
        "ui-img-03-celadon-vessel.png",
        "ui-img-04-archive-casket.png",
        "ui-img-05-ink-bloom-sprite.png"
    ]
    for asset in assets:
        analyze_asset(asset)

if __name__ == "__main__":
    main()
