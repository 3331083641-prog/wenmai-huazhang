"""生成「画境漫游」所需的三层素材（本地离线，无需任何模型）。

分层方式：把同一幅青绿山水按垂直区域分带，用羽化遮罩切成
背景（far）/ 中景（mid）/ 近景（near）三张透明 PNG，再用 CSS perspective
让三层在 Z 轴上分离，倾斜时产生轻微视差。

必须如实说明的边界：
  * 这不是深度估计，没有使用 Depth Anything 等深度模型（权重未下载）；
  * 不是三维重建，没有几何与相机参数；
  * 三层的「远近」来自画面本身的构图分带与大气透视（远端轻微模糊、降饱和），
    属于人工分层，不是测量结果。

输出：frontend/public/interactive/songhua/layer-{far,mid,near}.png
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "docs" / "examples" / "songhua" / "generated.png"
OUT = ROOT / "frontend" / "public" / "interactive" / "songhua"


def vertical_ramp(height: int, stops: list[tuple[float, float]]) -> np.ndarray:
    """按 [(y, alpha), ...] 生成平滑的垂直 alpha 曲线（0..1），返回长度 height 的一维数组。"""
    ys = np.array([s[0] for s in stops], dtype=np.float32) * (height - 1)
    alphas = np.array([s[1] for s in stops], dtype=np.float32)
    column = np.interp(np.arange(height, dtype=np.float32), ys, alphas)
    return np.clip(column, 0.0, 1.0)


def alpha_layer(height: int, width: int, stops: list[tuple[float, float]]) -> np.ndarray:
    column = vertical_ramp(height, stops)
    return np.repeat(column[:, None], width, axis=1)


def soft_blur(image: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return image
    return cv2.GaussianBlur(image, (0, 0), sigma)


def write_layer(name: str, bgr: np.ndarray, alpha: np.ndarray) -> None:
    rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2BGRA)
    rgba[:, :, 3] = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)
    # 用 WebP 交付：同样的透明通道，体积约为 PNG 的 1/6，避免首屏拖慢。
    path = OUT / f"layer-{name}.webp"
    cv2.imwrite(str(path), rgba, [cv2.IMWRITE_WEBP_QUALITY, 90])
    if not path.exists():
        raise SystemExit(f"WebP 写入失败：{path}")
    opaque = int((rgba[:, :, 3] > 250).mean() * 100)
    print(f"  {path.name:16s} {path.stat().st_size // 1024:>4d} KB  不透明区域 {opaque}%")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    bgr = cv2.imread(str(SRC), cv2.IMREAD_COLOR)
    if bgr is None:
        raise SystemExit(f"找不到源图：{SRC}")
    h, w = bgr.shape[:2]
    print(f"源图 {w}x{h}")

    # 背景：全幅；远端做轻微模糊与降饱和，模拟大气透视
    far = soft_blur(bgr, 1.4)
    far = cv2.cvtColor(far, cv2.COLOR_BGR2HSV)
    far[:, :, 1] = (far[:, :, 1] * 0.94).astype(np.uint8)
    far = cv2.cvtColor(far, cv2.COLOR_HSV2BGR)
    write_layer("far", far, alpha_layer(h, w, [(0.0, 1.0), (1.0, 1.0)]))

    # 中景：上缘淡入、下缘淡出，覆盖山体与楼阁所在的中段
    mid = bgr.copy()
    write_layer(
        "mid",
        mid,
        alpha_layer(h, w, [(0.0, 0.0), (0.16, 0.0), (0.30, 1.0), (0.62, 1.0), (0.80, 0.0), (1.0, 0.0)]),
    )

    # 近景：下段，含松石与水面；略作锐化强化「近实」
    near = bgr.astype(np.float32)
    blurred = cv2.GaussianBlur(near, (0, 0), 2.0)
    near = cv2.addWeighted(near, 1.35, blurred, -0.35, 0)
    near = np.clip(near, 0, 255).astype(np.uint8)
    write_layer("near", near, alpha_layer(h, w, [(0.0, 0.0), (0.52, 0.0), (0.68, 1.0), (1.0, 1.0)]))


if __name__ == "__main__":
    main()