"""Pixel-preserving depth relief and bounded, explicitly inferred inpainting."""
from pathlib import Path
import sys

import numpy as np
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'interactive'))


def helpers():
    import layered_pixels
    return layered_pixels


def test_flat_depth_stays_neutral_even_with_detailed_colours():
    rng = np.random.default_rng(7)
    image = rng.integers(0, 256, (24, 32, 4), dtype=np.uint8)
    depth = np.full((24, 32), 12, dtype=np.float32)
    alpha = np.full(depth.shape, 255, dtype=np.uint8)
    result = helpers().subject_relief(image, depth, alpha)
    assert result.dtype == np.float32
    np.testing.assert_array_equal(result, np.full(depth.shape, .5, np.float32))


def test_subject_gradient_thin_limb_and_background_are_preserved():
    h, w = 48, 64
    image = np.full((h, w, 3), 90, dtype=np.uint8)
    alpha = np.zeros((h, w), dtype=np.uint8)
    alpha[6:30, 12:52] = 255
    alpha[30:45, 31] = 255  # A one-pixel limb must not average with the backdrop.
    depth = np.tile(np.linspace(0, 1, w, dtype=np.float32), (h, 1))
    depth[alpha == 0] = -1000
    depth[35:45, 31] = .8
    before = [a.copy() for a in (image, depth, alpha)]
    result = helpers().subject_relief(image, depth, alpha)
    assert result.shape == alpha.shape
    assert np.isfinite(result).all()
    assert 0 <= result.min() <= result.max() <= 1
    np.testing.assert_array_equal(result[alpha == 0], .5)
    assert result[18, 45] - result[18, 18] > .6
    assert result[40, 31] > .85
    for original, snapshot in zip((image, depth, alpha), before):
        np.testing.assert_array_equal(original, snapshot)


def test_percentile_clipping_contains_outlier_and_missing_values():
    image = np.full((40, 40, 3), 140, dtype=np.uint8)
    depth = np.tile(np.linspace(10, 20, 40, dtype=np.float32), (40, 1))
    depth[0, 0] = 1e12
    depth[0, 1] = np.nan
    depth[0, 2] = np.inf
    alpha = np.ones(depth.shape, dtype=np.float32)
    result = helpers().subject_relief(image, depth, alpha)
    assert np.isfinite(result).all()
    assert result[20, 35] - result[20, 5] > .7
    np.testing.assert_array_equal(result[0, 1:3], .5)


def test_empty_subject_and_single_pixel_are_neutral():
    rgb = np.zeros((8, 8, 3), dtype=np.uint8)
    depth = np.arange(64, dtype=np.float32).reshape(8, 8)
    alpha = np.zeros((8, 8), dtype=np.uint8)
    np.testing.assert_array_equal(helpers().subject_relief(rgb, depth, alpha), .5)
    alpha[3, 3] = 255
    np.testing.assert_array_equal(helpers().subject_relief(rgb, depth, alpha), .5)


def test_edge_preserving_depth_smooths_noise_without_erasing_step():
    rng = np.random.default_rng(12)
    depth = np.zeros((48, 64), dtype=np.float32)
    depth[:, 32:] = 1
    depth += rng.normal(0, .025, depth.shape).astype(np.float32)
    rgb = np.zeros((48, 64, 3), dtype=np.uint8)
    rgb[:, 32:] = 255
    snapshot = depth.copy()
    result = helpers().edge_preserving_depth(depth, rgb)
    assert result.dtype == np.float32
    assert result[:, 4:28].std() < depth[:, 4:28].std() * .8
    assert np.mean(result[:, 32] - result[:, 31]) > .9
    np.testing.assert_array_equal(depth, snapshot)


def test_small_occlusion_fills_real_pixels_and_preserves_every_unmasked_pixel():
    y, x = np.indices((64, 80))
    image = np.stack((80 + x, 100 + y, 60 + x // 2), axis=-1).astype(np.uint8)
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    mask[24:36, 32:44] = 255
    image[mask != 0] = [255, 0, 255]
    before = image.copy()
    result = helpers().occlusion_background(image, mask)
    assert result['applied'] is True
    assert result['method'] == 'image-inpainting-telea-inferred'
    assert abs(result['coverage'] - 144 / (64 * 80)) < 1e-9
    np.testing.assert_array_equal(result['image'][mask == 0], image[mask == 0])
    assert np.abs(result['image'][mask != 0].astype(float) - [120, 130, 80]).mean() < 20
    np.testing.assert_array_equal(image, before)


def test_empty_large_and_unbounded_masks_are_unchanged():
    image = np.full((32, 40, 3), 180, dtype=np.uint8)
    for mask in (np.zeros((32, 40), bool), np.ones((32, 40), bool)):
        result = helpers().occlusion_background(image, mask)
        assert result['applied'] is False
        np.testing.assert_array_equal(result['image'], image)
    edge_mask = np.zeros((32, 40), bool)
    edge_mask[0:4, 8:12] = True
    result = helpers().occlusion_background(image, edge_mask)
    assert result['applied'] is False
    np.testing.assert_array_equal(result['image'], image)


def test_rejects_mismatched_shapes_and_invalid_fraction():
    image = np.zeros((8, 8, 3), dtype=np.uint8)
    with unittest.TestCase().assertRaisesRegex(ValueError, 'shape'):
        helpers().subject_relief(image, np.ones((4, 4)), np.ones((8, 8)))
    with unittest.TestCase().assertRaisesRegex(ValueError, 'max_fraction'):
        helpers().occlusion_background(image, np.ones((8, 8)), max_fraction=1.1)


def test_border_backdrop_white_paper_never_contains_subject_ghost():
    image = np.full((96, 128, 3), 255, dtype=np.uint8)
    image[8:88, 9:119] = [255, 0, 0]
    before = image.copy()
    result = helpers().border_backdrop(image)
    assert result.shape == image.shape
    assert result.dtype == np.uint8
    np.testing.assert_array_equal(result, np.full_like(image, 255))
    np.testing.assert_array_equal(image, before)


def test_border_backdrop_preserves_smooth_border_colour_gradient():
    y, x = np.indices((100, 120), dtype=np.float32)
    x /= 119
    y /= 99
    paper = np.stack((100 + 70 * x, 130 + 50 * y,
                      180 + 30 * x + 20 * y), axis=-1).astype(np.uint8)
    image = paper.copy()
    image[8:-8, 8:-8] = [255, 0, 255]
    result = helpers().border_backdrop(image)
    assert np.max(np.abs(result.astype(float) - paper)) <= 4
    assert result[50, -1, 0] - result[50, 0, 0] > 60
    assert result[-1, 60, 1] - result[0, 60, 1] > 40


def test_border_backdrop_ignores_isolated_corner_outlier_and_handles_one_pixel():
    image = np.full((100, 120, 3), [248, 242, 230], dtype=np.uint8)
    image[0, 0] = [0, 0, 0]
    result = helpers().border_backdrop(image)
    np.testing.assert_array_equal(result, np.full_like(image, [248, 242, 230]))
    pixel = np.array([[[12, 23, 34]]], dtype=np.uint8)
    np.testing.assert_array_equal(helpers().border_backdrop(pixel), pixel)


def load_tests(loader,tests,pattern):
    return unittest.TestSuite(unittest.FunctionTestCase(value)
        for name,value in sorted(globals().items()) if name.startswith('test_') and callable(value))


if __name__=='__main__':unittest.main(verbosity=2)
