"""Capture safety and image evidence use real parsing/files; no simulated browser DOM."""
import importlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts' / 'interactive'))


class WorldCaptureTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('capture_world'),
                             'The reusable browser capture module has not been implemented')
        self.capture = importlib.import_module('capture_world')

    def test_safe_case_ids_preserve_original_and_generated_ids(self):
        for value in ('zhuxianzhen-ruimao', 'case_20261025-ab12', 'a'):
            self.assertEqual(self.capture.validate_case_id(value), value)
        for value in ('', '../secrets', 'a/b', 'a?token=x', 'a#x', 'a\\b', '含中文', '.', 'a' * 129):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.capture.validate_case_id(value)

    def test_loopback_preview_urls_and_hash_routes(self):
        self.assertEqual(self.capture.world_url('abc', 'http://127.0.0.1:5173'),
                         'http://127.0.0.1:5173/wander/abc')
        self.assertEqual(self.capture.world_url('abc', 'http://localhost:4173/wenmai-huazhang/#'),
                         'http://localhost:4173/wenmai-huazhang/#/wander/abc')
        self.assertEqual(self.capture.world_url('abc', 'http://[::1]:5173'),
                         'http://[::1]:5173/wander/abc')

    def test_remote_urls_credentials_queries_and_ambiguous_hosts_rejected(self):
        for value in ('https://example.com', 'http://127.0.0.1.evil.test',
                      'http://user:secret@localhost:5173', 'http://localhost:5173?api_key=secret',
                      'file:///D:/index.html', 'http://localhost:bad',
                      'http://localhost:5173/#/other', 'http://localhost\\@example.com',
                      'http://localhost:5173/%2f%2fexample.com', 'http://localhost:5173/../private'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.capture.world_url('case-id', value)

    def test_output_stays_on_d_and_inside_project(self):
        good = ROOT / 'outputs' / 'capture-test'
        self.assertEqual(self.capture.validate_output_dir(good), good.resolve())
        for value in ('C:/Users/Public/capture', 'D:/elsewhere/capture', ROOT / '..' / 'escape'):
            with self.subTest(value=str(value)), self.assertRaises(ValueError):
                self.capture.validate_output_dir(value)

    def test_curated_ids_resolve_to_unchanged_style_slugs(self):
        for case_id, slug in {'zhuxianzhen-ruimao': 'zhuxianzhen', 'bianxiu-xiutu': 'bianxiu',
                              'songhua-yunhe': 'songhua', 'qinghua-dieyun': 'qinghua',
                              'jianzhi-linghu': 'jianzhi'}.items():
            self.assertEqual(self.capture.expected_world_slug(case_id), slug)
        self.assertEqual(self.capture.expected_world_slug('generated-ab12'), 'generated-ab12')

    def test_pixel_measurement_distinguishes_same_changed_and_blank_frames(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            first, same, changed = [Path(folder) / name for name in ('a.jpg', 'b.jpg', 'c.jpg')]
            image = Image.new('RGB', (64, 64), 'white')
            image.paste('blue', (16, 16, 48, 48)); image.save(first); image.save(same)
            image.paste('red', (16, 16, 48, 48)); image.save(changed)
            identical = self.capture.image_difference(first, same)
            altered = self.capture.image_difference(first, changed)
            self.assertEqual(identical['mean_absolute_difference'], 0)
            self.assertEqual(identical['changed_pixel_ratio'], 0)
            self.assertGreater(altered['mean_absolute_difference'], 10)
            self.assertGreater(altered['changed_pixel_ratio'], .20)
            self.assertTrue(self.capture.image_evidence(first)['nonblank'])
            blank = Path(folder) / 'blank.jpg'; Image.new('RGB', (64, 64), 'white').save(blank)
            self.assertFalse(self.capture.image_evidence(blank)['nonblank'])

    def test_pixel_measurement_rejects_mismatched_dimensions(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            a, b = Path(folder) / 'a.jpg', Path(folder) / 'b.jpg'
            Image.new('RGB', (16, 16), 'white').save(a)
            Image.new('RGB', (32, 16), 'white').save(b)
            with self.assertRaises(ValueError):
                self.capture.image_difference(a, b)

    def test_invalid_input_rejected_before_any_browser_or_files(self):
        with self.assertRaises(ValueError):
            self.capture.capture_world('../unsafe', ROOT / 'outputs' / 'capture-test')

    def test_expected_blocked_remote_font_is_separate_from_local_asset_failure(self):
        self.assertTrue(self.capture._ignorable_request('https://fonts.googleapis.com/css2?family=Serif', 'stylesheet'))
        self.assertFalse(self.capture._ignorable_request('http://127.0.0.1:5173/interactive/case/art.webp', 'image'))
        self.assertFalse(self.capture._ignorable_request('http://127.0.0.1:5173/src/main.tsx', 'script'))

    def test_static_scene_can_pass_while_motion_remains_false(self):
        self.assertTrue(hasattr(self.capture, 'capture_checks_passed'),
                        'Capture must distinguish required checks from optional motion evidence')
        checks = {key: True for key in (
            'canvas', 'slug_matches', 'not_degraded', 'no_page_errors', 'no_render_errors',
            'no_failed_requests', 'hotspots_visible', 'hotspot_click',
            'nonblank_frames', 'camera_changed', 'parallax')}
        checks['motion'] = False
        self.assertTrue(self.capture.capture_checks_passed(checks))
        self.assertFalse(checks['motion'])
        checks['parallax'] = False
        checks['passed'] = True
        self.assertFalse(self.capture.capture_checks_passed(checks))
        checks['parallax'] = True
        self.assertFalse(self.capture.capture_checks_passed(checks, ['browser_resource_failed']))
        self.assertFalse(self.capture.capture_checks_passed({'motion': False}))


if __name__ == '__main__':
    unittest.main()
