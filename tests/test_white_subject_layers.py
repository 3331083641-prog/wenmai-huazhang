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
    def test_continuous_landscape_is_not_cut_at_an_arbitrary_window(self):
        image=np.full((256,256,3),140,dtype=np.uint8)
        depth=np.full((256,256),.8,dtype=np.float32)
        spec={'id':'connected-rock','seed_x':.5,'seed_y':.5,
              'half_w':.2,'half_h':.2,'depth_min':.58}
        self.assertIsNone(builder.make_cutout(image,depth,spec))

    @staticmethod
    def full_rgba(result, size):
        width,height=size
        rgba=np.zeros((height,width,4),dtype=np.uint8)
        x,y,_,_=result['info']['bbox_norm']
        left,top=round(x*width),round(y*height)
        crop=np.asarray(result['image'])
        rgba[top:top+crop.shape[0],left:left+crop.shape[1]]=crop
        return rgba

    def test_white_crane_body_stays_opaque_and_paper_ring_preserves_hole(self):
        image=Image.new('RGB',(256,256),'white')
        ImageDraw.Draw(image).ellipse((50,45,205,195),fill='white',outline='#38434a',width=6)
        crane=extract_white_subject(np.asarray(image),{'x':.5,'y':.2})
        self.assertIsNotNone(crane)
        self.assertEqual(self.full_rgba(crane,image.size)[110,120,3],255)
        self.assertFalse(crane['info']['negativeSpacePreserved'])
        paper=Image.new('RGB',(256,256),'white')
        draw=ImageDraw.Draw(paper)
        draw.ellipse((45,45,210,210),fill='#b01928')
        draw.ellipse((85,85,170,170),fill='white')
        result=extract_white_subject(np.asarray(paper),{'x':.5,'y':.3},preserve_holes=True)
        self.assertIsNotNone(result)
        self.assertEqual(self.full_rgba(result,paper.size)[120,120,3],0)
        self.assertTrue(result['info']['negativeSpacePreserved'])
        self.assertTrue(result['info']['completeSubject'])

    def test_antialiased_foreground_recomposites_without_white_halo(self):
        image=Image.new('RGB',(1024,1024),'white')
        draw=ImageDraw.Draw(image)
        draw.ellipse((230,140,780,720),fill='#385870')
        draw.rectangle((490,660,498,930),fill='#385870')
        draw.line((730,440,860,370),fill='#385870',width=5)
        draw.ellipse((45,45,110,110),fill='red')
        image=image.resize((256,256),Image.Resampling.LANCZOS)
        original=np.asarray(image)
        result=extract_white_subject(original,{'x':.5,'y':.45})
        self.assertIsNotNone(result)
        rgba=self.full_rgba(result,image.size)
        alpha=rgba[:,:,3:4].astype(float)/255
        rebuilt=rgba[:,:,:3]*alpha+result['surface']*(1-alpha)
        self.assertLessEqual(np.abs(rebuilt-original).mean(),3)
        edge=(alpha[:,:,0]>.03)&(alpha[:,:,0]<.95)
        self.assertTrue(edge.any())
        # Defringed foreground should still be blue, not the pale source composite.
        self.assertLess(np.abs(rgba[:,:,:3][edge].astype(float)-[56,88,112]).mean(),18)
        self.assertTrue(result['mask'][225,123])
        self.assertFalse(result['mask'][18,18])

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
                self.assertTrue((world_dir/world['cutouts'][0]['relief_file']).is_file())
                self.assertGreater(world['tuning']['subject_relief'],0)
                self.assertEqual(world['provenance']['render_mode'],'complete-subject-layers')
                self.assertTrue(report['cutouts'][0]['ok'])
            finally:os.chdir(original)
