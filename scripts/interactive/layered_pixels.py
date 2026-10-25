"""Deterministic image-space helpers for single-image 2.5D layers.

Depth is a relative estimate, not measured geometry. Inpainting infers a plausible
continuation from visible pixels; it does not recover the real hidden background.
No helper downloads models or changes the supplied arrays.
"""
from __future__ import annotations

import numpy as np


def _guide(image: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    image = np.asarray(image)
    if image.ndim != 3 or image.shape[:2] != shape or image.shape[2] not in (3, 4):
        raise ValueError('image shape must match depth and contain RGB or RGBA channels')
    rgb = image[..., :3].astype(np.float32)
    if not np.isfinite(rgb).all():
        raise ValueError('image must contain finite RGB values')
    if np.issubdtype(image.dtype, np.integer) or float(rgb.max(initial=0)) > 1:
        rgb /= 255.0
    return np.clip(rgb, 0, 1)


def _depth_array(depth: np.ndarray) -> np.ndarray:
    depth = np.array(depth, dtype=np.float32, copy=True)
    if depth.ndim != 2 or not depth.size:
        raise ValueError('depth shape must be a nonempty H x W array')
    return depth


def _bilateral(depth: np.ndarray, rgb: np.ndarray, confidence: np.ndarray) -> np.ndarray:
    """Small joint bilateral window; zero-confidence neighbours never contribute.

    Colour only gates smoothing. Every resulting value is a weighted mean of
    supplied depth, so drawing details cannot become invented depth relief.
    """
    height, width = depth.shape
    weighted = np.zeros_like(depth)
    weights = np.zeros_like(depth)
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            if abs(dy) >= height or abs(dx) >= width:
                continue
            target = (slice(max(0, -dy), min(height, height - dy)),
                      slice(max(0, -dx), min(width, width - dx)))
            neighbour = (slice(max(0, dy), min(height, height + dy)),
                         slice(max(0, dx), min(width, width + dx)))
            delta_depth = depth[target] - depth[neighbour]
            delta_rgb = rgb[target] - rgb[neighbour]
            exponent = ((dx * dx + dy * dy) / (2 * 1.0 ** 2)
                        + delta_depth ** 2 / (2 * .10 ** 2)
                        + np.mean(delta_rgb ** 2, axis=2) / (2 * .12 ** 2))
            weight = np.exp(-exponent) * confidence[neighbour]
            weighted[target] += weight * depth[neighbour]
            weights[target] += weight
    return np.divide(weighted, weights, out=depth.copy(), where=weights > 0)


def subject_relief(rgb_or_rgba: np.ndarray, depth: np.ndarray,
                   alpha: np.ndarray) -> np.ndarray:
    """Return float32 relative subject depth in [0, 1], neutral .5 outside.

    Uses the 2nd/98th depth percentiles within visible subject pixels to suppress
    outliers, then a 5x5 alpha-aware joint bilateral pass. One-pixel limbs remain
    supported because no background samples enter their depth average. Alpha may
    be boolean, 0..1, or 0..255. Partial alpha blends relief toward .5. Empty,
    flat, single-pixel or missing depth remains neutral. RGB is only a guide.
    """
    raw = _depth_array(depth)
    rgb = _guide(rgb_or_rgba, raw.shape)
    opacity = np.array(alpha, dtype=np.float32, copy=True)
    if opacity.shape != raw.shape:
        raise ValueError('alpha shape must match depth shape')
    if not np.isfinite(opacity).all():
        raise ValueError('alpha must contain finite values')
    if float(opacity.max(initial=0)) > 1:
        opacity /= 255.0
    opacity = np.clip(opacity, 0, 1)
    valid = (opacity > .05) & np.isfinite(raw)
    result = np.full(raw.shape, .5, dtype=np.float32)
    if np.count_nonzero(valid) < 2:
        return result
    low, high = np.percentile(raw[valid], [2, 98])
    spread = float(high - low)
    if spread <= max(1e-7, 1e-7 * max(abs(float(low)), abs(float(high)))):
        return result
    # Replace invalid samples before any arithmetic, preventing NaN propagation.
    normalized = np.full(raw.shape, .5, dtype=np.float32)
    normalized[valid] = np.clip((raw[valid] - low) / spread, 0, 1)
    confidence = np.where(valid, opacity, 0).astype(np.float32)
    smooth = _bilateral(normalized, rgb, confidence)
    result[valid] = .5 + (smooth[valid] - .5) * opacity[valid]
    return np.clip(result, 0, 1).astype(np.float32)


def edge_preserving_depth(raw_depth: np.ndarray, rgb: np.ndarray) -> np.ndarray:
    """Joint bilateral smoothing in the input depth units, preserving boundaries.

    A robust span sets the bilateral range scale. Non-finite pixels retain their
    input values and are excluded as neighbours. RGB supplies edge guidance only.
    """
    raw = _depth_array(raw_depth)
    guide = _guide(rgb, raw.shape)
    valid = np.isfinite(raw)
    if not valid.any():
        return raw
    low, high = np.percentile(raw[valid], [2, 98])
    spread = float(high - low)
    if spread <= max(1e-7, 1e-7 * max(abs(float(low)), abs(float(high)))):
        return raw
    normalized = np.zeros_like(raw)
    normalized[valid] = (raw[valid] - low) / spread
    smooth = _bilateral(normalized, guide, valid.astype(np.float32))
    raw[valid] = smooth[valid] * spread + low
    return raw


def border_backdrop(image: np.ndarray) -> np.ndarray:
    """Extend estimated paper colours using only thin outer-border samples.

    Robust RGB medians of four short L-shaped corner strips determine a smooth
    bilinear colour field. The interior is never sampled or blurred, so a central
    foreground cannot appear as an enlarged ghost outside the artwork. This is
    a plausible paper extension, not reconstruction of unseen image content.
    Input/output are H x W x 3 uint8 RGB, with the input left untouched.
    """
    source = np.asarray(image)
    if (source.ndim != 3 or source.shape[2] != 3 or not source.size
            or source.dtype != np.uint8):
        raise ValueError('image shape must be nonempty H x W x 3 uint8 RGB')
    height, width = source.shape[:2]
    strip_h = min(3, max(1, height // 100))
    strip_w = min(3, max(1, width // 100))
    corner_h = max(strip_h, round(height * .05))
    corner_w = max(strip_w, round(width * .05))

    def corner(bottom: bool, right: bool) -> np.ndarray:
        rows = slice(height - corner_h, height) if bottom else slice(0, corner_h)
        cols = slice(width - corner_w, width) if right else slice(0, corner_w)
        edge_rows = slice(height - strip_h, height) if bottom else slice(0, strip_h)
        edge_cols = slice(width - strip_w, width) if right else slice(0, strip_w)
        samples = np.concatenate((source[edge_rows, cols].reshape(-1, 3),
                                  source[rows, edge_cols].reshape(-1, 3)))
        return np.median(samples, axis=0).astype(np.float32)

    top_left, top_right = corner(False, False), corner(False, True)
    bottom_left, bottom_right = corner(True, False), corner(True, True)
    x = np.linspace(0, 1, width, dtype=np.float32)[None, :, None]
    y = np.linspace(0, 1, height, dtype=np.float32)[:, None, None]
    top = top_left * (1 - x) + top_right * x
    bottom = bottom_left * (1 - x) + bottom_right * x
    return np.clip(np.rint(top * (1 - y) + bottom * y), 0, 255).astype(np.uint8)


def occlusion_background(image: np.ndarray, foreground_mask: np.ndarray,
                         max_fraction: float = .25) -> dict:
    """Infer only bounded interior holes with OpenCV Telea image inpainting.

    The original copy is returned when the mask is empty, exceeds max_fraction,
    or touches the image boundary. ``coverage`` is the requested mask fraction.
    Applied output identifies the inference method explicitly. Unmasked RGB and
    every original alpha value are retained exactly. Requires installed OpenCV
    only when there is an eligible hole; never installs or downloads anything.
    """
    source = np.asarray(image)
    if source.ndim != 3 or source.shape[2] not in (3, 4) or not source.size:
        raise ValueError('image shape must be nonempty H x W x RGB/RGBA')
    if source.dtype != np.uint8:
        raise ValueError('inpainting image must use uint8 pixels')
    mask_values = np.asarray(foreground_mask)
    if mask_values.shape != source.shape[:2]:
        raise ValueError('foreground_mask shape must match image shape')
    if not np.isfinite(mask_values).all():
        raise ValueError('foreground_mask must contain finite values')
    if not np.isfinite(max_fraction) or not 0 <= max_fraction <= 1:
        raise ValueError('max_fraction must be between 0 and 1')
    mask = mask_values > 0
    coverage = float(mask.mean())
    result = {'image': source.copy(), 'method': 'none',
              'applied': False, 'coverage': coverage}
    if (not mask.any() or coverage > max_fraction or mask[0].any()
            or mask[-1].any() or mask[:, 0].any() or mask[:, -1].any()):
        return result
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError('OpenCV (cv2) must already be installed for image inpainting') from exc
    inferred = cv2.inpaint(np.ascontiguousarray(source[..., :3]),
                           mask.astype(np.uint8) * 255, 3, cv2.INPAINT_TELEA)
    result['image'][..., :3][mask] = inferred[mask]
    result.update(method='image-inpainting-telea-inferred', applied=True)
    return result
