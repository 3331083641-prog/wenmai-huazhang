"""快速体检：截图是否为空/全黑、主色是否落在暖木+米白+青瓦的预期范围。"""
import glob
import os

import numpy as np
from PIL import Image

ROOT = r"D:\wenmai-huazhang\docs\heritage_gallery\screens"

for path in sorted(glob.glob(os.path.join(ROOT, "glb-*.png"))):
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
    lum = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
    h, w, _ = arr.shape
    # 中心 60% 区域：排除 UI 卡片影响
    c = arr[int(h * 0.2):int(h * 0.8), int(w * 0.2):int(w * 0.8)]
    std = float(c.reshape(-1, 3).std(axis=0).mean())
    print(
        f"{os.path.basename(path):26s} {w}x{h} "
        f"mean={lum.mean():6.1f} p05={np.percentile(lum, 5):5.1f} p95={np.percentile(lum, 95):5.1f} "
        f"std={std:5.1f} unique={len(np.unique(arr.reshape(-1, 3), axis=0))}"
    )