"""一次性探针：确认 Depth Anything V2 在本机可用，并测出深度质量。

只用于可行性判断，不产出前端资产。真正出资产的脚本是同目录的
build_painting_world.py。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import torch
from PIL import Image

ART = r"frontend\public\songhua.png"


def main() -> int:
    t0 = time.time()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={device} torch={torch.__version__}", flush=True)

    from transformers import AutoImageProcessor, DepthAnythingForDepthEstimation

    repo = "depth-anything/Depth-Anything-V2-Small-hf"
    processor = AutoImageProcessor.from_pretrained(repo)
    model = DepthAnythingForDepthEstimation.from_pretrained(repo).to(device).eval()
    print(f"model loaded in {time.time() - t0:.1f}s", flush=True)

    img = Image.open(ART).convert("RGB")
    print("artwork:", img.size)

    inputs = processor(images=img, return_tensors="pt").to(device)
    with torch.inference_mode():
        outputs = model(**inputs)

    pred = outputs.predicted_depth
    print("raw pred shape:", tuple(pred.shape), "dtype", pred.dtype)

    # 两种后处理都试：不同 transformers 版本的接口不一致，谁通用用谁
    post = getattr(processor, "post_process_depth_estimation", None)
    if post is not None:
        try:
            res = post(outputs, target_sizes=[(img.height, img.width)])[0]["predicted_depth"]
            depth = res.detach().float().cpu().numpy()
            print("post_process_depth_estimation: OK")
        except Exception as exc:  # noqa: BLE001
            print("post_process failed:", exc)
            post = None
    if post is None:
        import torch.nn.functional as F

        depth = F.interpolate(
            pred.unsqueeze(1), size=(img.height, img.width), mode="bicubic", align_corners=False
        ).squeeze().float().cpu().numpy()
        print("manual bicubic upsample: OK")

    lo, hi = np.percentile(depth, [2, 98])
    norm = np.clip((depth - lo) / max(hi - lo, 1e-6), 0, 1)
    print(
        "depth stats: min=%.3f max=%.3f p2=%.3f p50=%.3f p98=%.3f"
        % (depth.min(), depth.max(), lo, np.percentile(depth, 50), hi)
    )

    out_dir = os.path.join("scripts", "interactive", "_probe")
    os.makedirs(out_dir, exist_ok=True)
    np.save(os.path.join(out_dir, "depth.npy"), depth.astype(np.float32))

    # 上近下远的合理方向：先按原样存一张灰度，再存一张伪彩，人/模型都能判读
    Image.fromarray((norm * 255).astype(np.uint8)).save(os.path.join(out_dir, "depth-gray.png"))
    try:
        import matplotlib

        Image.fromarray(
            (matplotlib.colormaps["turbo"](norm)[:, :, :3] * 255).astype(np.uint8)
        ).save(os.path.join(out_dir, "depth-turbo.png"))
        print("colormap preview: OK")
    except Exception as exc:  # noqa: BLE001
        print("colormap skipped:", exc)

    # 分带统计：把画面按纵向切 5 带看深度是否单调递减（青绿山水应大致如此）
    h = norm.shape[0]
    for i in range(5):
        band = norm[i * h // 5 : (i + 1) * h // 5]
        print("  band %d (top->bottom) mean depth-straight=%.3f" % (i, band.mean()))

    # 四角 vs 中心：判断是「场景深度」还是「径向渐变伪深度」
    m = norm.mean()
    print(
        "  corners=%.3f  center=%.3f  global=%.3f"
        % (
            np.mean([norm[0, 0], norm[0, -1], norm[-1, 0], norm[-1, -1]]),
            norm[h // 3 : 2 * h // 3, norm.shape[1] // 3 : 2 * norm.shape[1] // 3].mean(),
            m,
        )
    )
    print(f"done in {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())