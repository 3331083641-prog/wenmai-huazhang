import os
import cv2
import numpy as np
from PIL import Image

USER_UPLOADED_DIR = r"C:\Users\WPY11\.gemini\antigravity\brain\4a5395b1-6a38-4bc7-9343-b8cac7dcebd5\.user_uploaded"
OUTPUT_DIR = r"D:\wenmai-huazhang\frontend\public\visuals\vnext"

def process_asset_01():
    print("Processing Asset 01: Cultural Brush...")
    orig = os.path.join(USER_UPLOADED_DIR, "media_1794755004504_32de8504.png")
    img = cv2.imread(orig, cv2.IMREAD_UNCHANGED)
    
    # img is (1024, 1024, 4)
    # The brush has a faint rectangular haze with alpha < 15
    a = img[:, :, 3].astype(np.float32)
    
    # Smooth Hermite curve to zero out faint haze (< 14) and transition smoothly to 26
    # For a <= 12: 0
    # For a in [12, 26]: smooth ramp
    ramp = np.clip((a - 12.0) / (26.0 - 12.0), 0.0, 1.0)
    smooth_ramp = ramp * ramp * (3.0 - 2.0 * ramp)
    new_a = np.where(a <= 12.0, 0.0, a * smooth_ramp)
    
    # Also clear outer 3px boundary to guarantee no edge lines
    new_a[0:3, :] = 0
    new_a[-3:, :] = 0
    new_a[:, 0:3] = 0
    new_a[:, -3:] = 0
    
    img[:, :, 3] = np.clip(new_a, 0, 255).astype(np.uint8)
    
    out_png = os.path.join(OUTPUT_DIR, "ui-img-01-cultural-brush.png")
    cv2.imwrite(out_png, img)
    
    # Also save high-quality WebP
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA))
    out_webp = os.path.join(OUTPUT_DIR, "ui-img-01-cultural-brush.webp")
    pil_img.save(out_webp, "WEBP", quality=95, method=6)
    
    print(f"  Saved PNG: {os.path.getsize(out_png)/1024:.1f} KB, WebP: {os.path.getsize(out_webp)/1024:.1f} KB")

def process_black_bg(input_filename, output_base, erode_iters=1):
    print(f"Processing Black Background Asset: {output_base}...")
    orig = os.path.join(USER_UPLOADED_DIR, input_filename)
    bgr = cv2.imread(orig)
    
    # Background is black studio: max(b, g, r) <= 12
    max_val = np.maximum.reduce([bgr[:,:,0], bgr[:,:,1], bgr[:,:,2]])
    fg_mask = (max_val > 12).astype(np.uint8) * 255
    
    # Slight morphological close to bridge tiny gaps inside golden lines
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel_close)
    
    # Soft feathering at the boundary for anti-aliasing
    dist_inside = cv2.distanceTransform(fg_mask, cv2.DIST_L2, 3)
    dist_outside = cv2.distanceTransform(255 - fg_mask, cv2.DIST_L2, 3)
    
    # Alpha transition within +/- 1.2 pixels of boundary
    alpha = np.clip((dist_inside - dist_outside + 1.2) / 2.4 * 255.0, 0.0, 255.0).astype(np.uint8)
    
    # Zero out outer 2px boundary
    alpha[0:2, :] = 0
    alpha[-2:, :] = 0
    alpha[:, 0:2] = 0
    alpha[:, -2:] = 0
    
    rgba = np.dstack([bgr, alpha])
    
    out_png = os.path.join(OUTPUT_DIR, f"{output_base}.png")
    cv2.imwrite(out_png, rgba)
    
    pil_img = Image.fromarray(cv2.cvtColor(rgba, cv2.COLOR_BGRA2RGBA))
    out_webp = os.path.join(OUTPUT_DIR, f"{output_base}.webp")
    pil_img.save(out_webp, "WEBP", quality=95, method=6)
    
    print(f"  Saved PNG: {os.path.getsize(out_png)/1024:.1f} KB, WebP: {os.path.getsize(out_webp)/1024:.1f} KB")

def process_checkerboard_bg(input_filename, output_base):
    print(f"Processing Checkerboard Background Asset: {output_base}...")
    orig = os.path.join(USER_UPLOADED_DIR, input_filename)
    bgr = cv2.imread(orig)
    
    b = bgr[:,:,0].astype(int)
    g = bgr[:,:,1].astype(int)
    r = bgr[:,:,2].astype(int)
    
    diff = np.maximum.reduce([np.abs(r-g), np.abs(g-b), np.abs(r-b)])
    min_val = np.minimum.reduce([r, g, b])
    
    # Checkerboard background pixels: high luminance and very low chromatic difference
    is_checkerboard = (min_val >= 228) & (diff <= 15)
    
    fg_mask = (~is_checkerboard).astype(np.uint8) * 255
    
    # Morphological close to bridge tiny gaps inside intricate golden stipples
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel_close)
    
    # Remove isolated tiny noise specks in background
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_mask)
    clean_fg = np.zeros_like(fg_mask)
    for lbl in range(1, num_labels):
        if stats[lbl, cv2.CC_STAT_AREA] >= 30: # retain anything >= 30 pixels
            clean_fg[labels == lbl] = 255
            
    # Anti-aliased feathering
    dist_inside = cv2.distanceTransform(clean_fg, cv2.DIST_L2, 3)
    dist_outside = cv2.distanceTransform(255 - clean_fg, cv2.DIST_L2, 3)
    alpha = np.clip((dist_inside - dist_outside + 1.2) / 2.4 * 255.0, 0.0, 255.0).astype(np.uint8)
    
    # Zero out outer 2px boundary
    alpha[0:2, :] = 0
    alpha[-2:, :] = 0
    alpha[:, 0:2] = 0
    alpha[:, -2:] = 0
    
    rgba = np.dstack([bgr, alpha])
    
    out_png = os.path.join(OUTPUT_DIR, f"{output_base}.png")
    cv2.imwrite(out_png, rgba)
    
    pil_img = Image.fromarray(cv2.cvtColor(rgba, cv2.COLOR_BGRA2RGBA))
    out_webp = os.path.join(OUTPUT_DIR, f"{output_base}.webp")
    pil_img.save(out_webp, "WEBP", quality=95, method=6)
    
    print(f"  Saved PNG: {os.path.getsize(out_png)/1024:.1f} KB, WebP: {os.path.getsize(out_webp)/1024:.1f} KB")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    process_asset_01()
    process_black_bg("media_1794755004563_0cdc88a1.jpg", "ui-img-02-heritage-pavilion")
    process_black_bg("media_1794755004490_645c216c.jpg", "ui-img-03-celadon-vessel")
    process_checkerboard_bg("media_1794755004556_a46e1ba9.jpg", "ui-img-04-archive-casket")
    process_checkerboard_bg("media_1794755004540_b84267cd.jpg", "ui-img-05-ink-bloom-sprite")
    print("\nAll 5 visual assets re-processed with true alpha and optimized WebP!")

if __name__ == "__main__":
    main()
