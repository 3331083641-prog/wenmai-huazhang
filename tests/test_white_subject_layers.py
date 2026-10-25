"""Keep full white-background silhouettes intact instead of tearing a depth mesh."""
from pathlib import Path
import sys
import unittest
import tempfile,os,json,io,contextlib
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/interactive'))
from white_subject import extract_white_subject
import build_painting_world as builder


class WhiteSubjectTests(unittest.TestCase):
    def test_whole_subject_includes_thin_parts_and_removes_underlying_duplicate(self):
        image=Image.new('RGB',(256,256),'white');draw=ImageDraw.Draw(image)
        draw.ellipse((75,55,180,170),fill='#315f88')
        draw.rectangle((100,150,106,220),fill='#315f88')
        draw.ellipse((20,20,42,42),fill='red') # unrelated ornament must remain in background
        result=extract_white_subject(np.asarray(image),{'x':.5,'y':.4})
        self.assertIsNotNone(result)
        self.assertTrue(result['mask'][210,103])
        self.assertFalse(result['mask'][30,30])
        np.testing.assert_array_equal(result['surface'][100,110],[255,255,255])
        np.testing.assert_array_equal(result['surface'][30,30],[255,0,0])

    def test_coloured_or_busy_border_does_not_claim_white_background(self):
        self.assertIsNone(extract_white_subject(np.full((128,128,3),80,dtype=np.uint8),{'x':.5,'y':.5}))

    def test_complete_subject_world_builds_all_manifest_assets_and_report(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            root=Path(folder);image=Image.new('RGB',(256,256),'white')
            ImageDraw.Draw(image).ellipse((50,50,210,210),fill='red')
            source=root/'image.png';image.save(source)
            depth=np.linspace(0,1,256*256,dtype=np.float32).reshape(256,256)
            cfg=builder.normalise_config({'slug':'test-layer','title':'本地测试图','source':str(source),
                'sceneKind':'flat_artwork','subjectSeed':{'x':.5,'y':.5},
                'hotspots':[{'id':'subject','x':.5,'y':.5,'r':.1}],'cutouts':[]})
            original=Path.cwd()
            try:
                os.chdir(root)
                with patch.object(builder,'estimate_image_depth',return_value=(depth,{'source':'test-depth'})), contextlib.redirect_stdout(io.StringIO()):
                    report=builder.build_artwork(cfg,SimpleNamespace(gamma=.72,depth_smooth=3,force_depth=False))
                world_dir=root/'frontend/public/interactive/test-layer/world'
                world=json.loads((world_dir/'world.json').read_text(encoding='utf-8'))
                for key in ['art','surface','depth','backdrop','masks']:
                    self.assertTrue((world_dir/world[key]['file']).is_file())
                self.assertTrue(world['cutouts'][0]['completeSubject'])
                self.assertEqual(world['provenance']['render_mode'],'complete-subject-layers')
                self.assertTrue(report['cutouts'][0]['ok'])
            finally:os.chdir(original)
