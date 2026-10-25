"""Depth helpers stay image-bound and never download weights implicitly."""
import ast
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/interactive'))
from image_geometry import image_depth, DEPTH_SOURCE
from build_painting_world import run_depth
import depth_estimation


class GeometryTests(unittest.TestCase):
    def test_geometry_depends_on_current_image_and_ignores_foreign_cached_depth(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            root=Path(folder);image=root/'new.png';cache=root/'old.npy'
            Image.new('RGB',(32,32),'black').save(image)
            first=image_depth(image)
            im=Image.new('RGB',(32,32),'white');im.paste('black',(0,0,16,16));im.save(image)
            np.save(cache,np.ones((512,512)))
            second=run_depth(str(image),'forbidden-other-model',str(cache),False)
            self.assertFalse(np.allclose(first,second))
            np.testing.assert_array_equal(second,image_depth(image))
            self.assertEqual(DEPTH_SOURCE,'image_geometry_v1')

    def test_automatic_pipeline_does_not_call_cloud_content_models(self):
        for name in ['ingest_case.py','build_painting_world.py','image_geometry.py']:
            tree=ast.parse((ROOT/'scripts/interactive'/name).read_text(encoding='utf-8'))
            imports=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):imports.extend(i.name for i in node.names)
                elif isinstance(node,ast.ImportFrom):imports.append(node.module or '')
            self.assertFalse(set(i.split('.')[0] for i in imports)&{'diffusers','openai','dashscope'})

    def test_missing_depth_weights_fail_without_network_or_silent_geometry(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            image=Path(folder)/'image.png';Image.new('RGB',(32,32),'blue').save(image)
            with patch.dict('os.environ',{'WENMAI_DEPTH_MODE':'model','WENMAI_DEPTH_MODEL_DIR':folder}), patch.object(
                depth_estimation,'run_local_model') as model:
                with self.assertRaises(RuntimeError):depth_estimation.estimate_image_depth(image)
                model.assert_not_called()

    def test_depth_cache_is_bound_to_image_bytes_and_model_revision(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            root=Path(folder);image=root/'image.png';Image.new('RGB',(32,32),'blue').save(image)
            first=np.linspace(0,1,1024,dtype=np.float32).reshape(32,32)
            with patch.dict('os.environ',{'WENMAI_DEPTH_MODE':'model'}), patch.object(depth_estimation,'ROOT',root), patch.object(
                depth_estimation,'verify_local_model',return_value=root
            ), patch.object(depth_estimation,'run_local_model',side_effect=[first,first[::-1]]) as model:
                a,info=depth_estimation.estimate_image_depth(image)
                depth_estimation.estimate_image_depth(image)
                self.assertEqual(model.call_count,1)
                Image.new('RGB',(32,32),'red').save(image)
                b,other=depth_estimation.estimate_image_depth(image)
            self.assertNotEqual(info['inputImageSha256'],other['inputImageSha256'])
            self.assertFalse(np.array_equal(a,b))


if __name__=='__main__':unittest.main()
