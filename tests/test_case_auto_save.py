"""Verify a successful real-provider response saves an image-bound case offline."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import case_store


class AutoSaveTests(unittest.TestCase):
    def test_success_response_saves_before_queuing_its_own_interactions(self):
        import app
        from starlette.requests import Request
        order=[]
        saved={'caseId':'own-new-image','artworkTitle':'本图作品'}
        def save(**kwargs):order.append('saved');return saved
        def queue(case_id):order.append(('queued',case_id));return {'enabled':True,'status':'queued'}
        with patch.object(app.service,'generate',return_value={'success':True}), patch.object(
            app,'auto_save_enabled',return_value=True
        ), patch.object(app,'save_case',side_effect=save), patch.object(app,'start_interactive_build',side_effect=queue):
            result=app.generate(app.GenerateRequest(theme='测试自动流程'),Request({'type':'http','scheme':'http',
                'server':('127.0.0.1',8000),'path':'/generate','headers':[]}))
        self.assertEqual(order,['saved',('queued','own-new-image')])
        self.assertTrue(result['autoSave']['saved'])
        self.assertEqual(result['interactiveJob']['status'],'queued')

    def test_saved_card_points_to_its_generated_image_hash(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            root=Path(folder);image=root/'source.png'
            Image.new('RGB',(32,32),'blue').save(image)
            def render(**kwargs):
                Image.new('RGB',(20,30),'white').save(kwargs['out_path'])
                return 'test_png'
            with patch.object(case_store,'EXAMPLES_DIR',root/'examples'), patch.object(case_store,'_prune_cases'), patch.object(
                case_store,'_has_cjk_font',return_value=True
            ), patch.object(case_store,'_render_culture_card',side_effect=render):
                saved=case_store.save_case(payload={'style':'qinghua'},response={
                    'provider':'dashscope_qwen_image','success':True,'localPath':str(image),
                    'analysisSource':'qwen3_vl','visionAnalysis':{'observed_subjects':['蓝色色块']}},base_url='http://127.0.0.1:8000')
            self.assertIsNotNone(saved)
            target=root/'examples'/saved['caseId']
            meta=json.loads((target/'metadata.json').read_text(encoding='utf-8'))
            self.assertEqual(meta['cultureCardGeneratedSha256'],meta['generatedSha256'])
            self.assertEqual(meta['cultureCardSha256'],hashlib.sha256((target/'culture_card.png').read_bytes()).hexdigest())


if __name__=='__main__':unittest.main()
