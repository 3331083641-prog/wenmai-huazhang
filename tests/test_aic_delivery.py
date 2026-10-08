"""Offline regression tests; fake network responses never become published cases."""
import base64, hashlib, io, json, os, re, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import Mock, patch
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from style_config import STYLE_LIBRARY, get_style
from prompt_builder import build_enhanced_prompt
from providers.dashscope_qwen_image_provider import DashScopeQwenImageProvider, _save_image_bytes
from providers.base import ProviderError
from provider_service import GenerationService
from services.vision_analysis import VisionAnalysisService, VisionAnalysisError

SLUGS=('zhuxianzhen','bianxiu','songhua','qinghua','jianzhi')
def png():
    buf=io.BytesIO();Image.new('RGB',(32,32),'white').save(buf,format='PNG');return buf.getvalue()
def metadata(slug): return json.loads((ROOT/'docs/examples'/slug/'metadata.json').read_text(encoding='utf-8-sig'))

class GalleryTests(unittest.TestCase):
    def test_01_inputs_valid(self):
        for slug in SLUGS:
            with Image.open(ROOT/'docs/examples'/slug/'reference.png') as image: image.verify()
    def test_02_current_subject_mapping(self):
        expected={'zhuxianzhen':'猫','bianxiu':'白兔','songhua':'楼阁','qinghua':'蝴蝶','jianzhi':'赤狐'}
        for slug,subject in expected.items(): self.assertIn(subject,metadata(slug)['referenceSubject'])
    def test_03_style_ids_match_backend(self):
        self.assertEqual(set(SLUGS),set(STYLE_LIBRARY))
        for slug in SLUGS:self.assertEqual(metadata(slug)['styleId'],slug)
    def test_04_reference_hashes_and_usage(self):
        for slug in SLUGS:
            m=metadata(slug);self.assertTrue(m['referenceImageUsed'])
            self.assertEqual(m['referenceSha256'],hashlib.sha256((ROOT/'docs/examples'/slug/'reference.png').read_bytes()).hexdigest())
            if m['modelInputImageCount'] is not None:self.assertEqual(m['modelInputImageCount'],1)
    def test_07_outputs_saved_valid(self):
        for slug in SLUGS:
            p=ROOT/'docs/examples'/slug/'generated.png'
            with Image.open(p) as image:self.assertEqual(image.format,'PNG');self.assertEqual(image.size,(1024,1024))
            self.assertEqual(metadata(slug)['generatedSha256'],hashlib.sha256(p.read_bytes()).hexdigest())
    def test_08_card_paired_with_generated_image(self):
        for slug in SLUGS:
            m=metadata(slug);self.assertEqual(m['analysisSource'],'qwen3_vl')
            self.assertEqual(m['cultureCardGeneratedSha256'],m['generatedSha256'])
            self.assertTrue(m['visionAnalysis']['observed_subjects'])
    def test_09_readme_local_image_links(self):
        for path in [ROOT/'README.md', ROOT/'docs/examples/README.md']:
            text=path.read_text(encoding='utf-8')
            links=re.findall(r'<img[^>]+src="([^"]+)"',text)+re.findall(r'!\[[^\]]*\]\(([^)]+)\)',text)
            for link in links:
                if not link.startswith('http'): self.assertTrue((path.parent/link).is_file(),link)
    def test_10_exported_card_png(self):
        for slug in SLUGS:
            with Image.open(ROOT/'docs/examples'/slug/'culture_card.png') as im:self.assertEqual(im.size,(1080,1440));self.assertEqual(im.format,'PNG')
    def test_11_windows_wrapper_paths(self):
        for name in ['setup_windows','start_windows','stop_windows','check_environment']:
            self.assertIn('%~dp0scripts\\windows_launcher.ps1',(ROOT/f'{name}.cmd').read_text())
        launcher=(ROOT/'scripts/windows_launcher.ps1').read_text()
        self.assertIn('StartTime.ToUniversalTime()',launcher)
        self.assertNotIn('taskkill',launcher.lower())
    def test_16_five_frontend_styles(self):
        s=(ROOT/'frontend/src/data/styleLibrary.ts').read_text(encoding='utf-8')
        for slug in SLUGS:self.assertIn(f"id: '{slug}'",s)
    def test_18_canonical_style_assets_separate(self):
        for slug in SLUGS:
            content=(ROOT/'assets/style_refs'/f'{slug}.png').read_bytes()
            for sub in ['backend/style_refs','frontend/public']:self.assertEqual(content,(ROOT/sub/f'{slug}.png').read_bytes())
            self.assertNotEqual(hashlib.sha256(content).hexdigest(),metadata(slug)['referenceSha256'])
    def test_metadata_has_no_sensitive_payload(self):
        for slug in SLUGS:
            text=(ROOT/'docs/examples'/slug/'metadata.json').read_text(encoding='utf-8')
            self.assertNotIn('data:image',text);self.assertNotIn('DASHSCOPE_API_KEY',text)
            self.assertNotIn('D:\\',text)

class ProviderTests(unittest.TestCase):
    def provider(self):
        with patch.dict(os.environ,{'DASHSCOPE_API_KEY':'unit-test-placeholder','DASHSCOPE_BASE_URL':'https://test.cn-beijing.maas.aliyuncs.com','DASHSCOPE_IMAGE_MODEL':'qwen-image-3.0'}):
            return DashScopeQwenImageProvider()
    def run_fake(self,slug,count):
        provider=self.provider()
        submit=Mock(status_code=200);submit.json.return_value={'output':{'task_id':'fixture-task'}}
        poll=Mock(status_code=200);poll.json.return_value={'output':{'task_status':'SUCCEEDED','results':[{'url':'https://fixture.invalid/output.png'}]},'usage':{'input_image_count':count,'output_image_count':1}}
        input_image='data:image/png;base64,'+base64.b64encode((ROOT/'docs/examples'/slug/'reference.png').read_bytes()).decode()
        with patch.dict(os.environ,{'DASHSCOPE_BASE_URL':'https://test.cn-beijing.maas.aliyuncs.com'}),patch.object(provider,'is_available',return_value=(True,'')),patch.object(provider,'_request',side_effect=[submit,poll]) as request,patch('requests.get',return_value=Mock(content=png())),patch('providers.dashscope_qwen_image_provider._save_image_bytes',return_value=Path('fixture.png')),patch('providers.dashscope_qwen_image_provider._write_trace'):
            result=provider.generate({'uploadedImage':input_image},'fixture prompt','',get_style(slug),{}, {},base_url='http://fixture.invalid/')
            sent=request.call_args_list[0].kwargs['json_body']['input']['messages'][0]['content'][0]['image']
            self.assertEqual(sent,input_image)
            self.assertTrue(request.call_args_list[0].kwargs['single_attempt'])
            return result
    def test_05_five_requests_include_correct_reference(self):
        for slug in SLUGS:self.assertTrue(self.run_fake(slug,1)['referenceImageUsed'])
    def test_06_reference_usage_not_invented(self):
        with self.assertRaises(ProviderError): self.run_fake('bianxiu',0)
    def test_real_failure_no_mock(self):
        provider=Mock();provider.is_available.return_value=(True,'');provider.generate.side_effect=ProviderError('dashscope_qwen_image','network','fixture failure')
        fallback=Mock()
        with patch.dict(os.environ,{'ALLOW_MOCK_FALLBACK':'false'}),patch.object(GenerationService,'_providers',return_value={'dashscope_qwen_image':provider,'fast_demo':fallback,'mock':fallback}),patch('provider_service.analyze_image',return_value={}),patch('provider_service._trace_generate'):
            result=GenerationService().generate({'theme':'测试','style':'bianxiu','generationProvider':'dashscope_qwen_image'},base_url='http://fixture.invalid/')
        self.assertFalse(result['success']);self.assertEqual(result['imageUrl'],'');fallback.generate.assert_not_called()
    def test_14_missing_vl_preserves_image_explicit_fallback(self):
        provider=Mock();provider.is_available.return_value=(True,'');provider.generate.return_value={'success':True,'imageUrl':'http://fixture.invalid/image.png','provider':'dashscope_qwen_image','mode':'image_to_image','referenceImageUsed':True,'localPath':'fixture.png'}
        with patch.dict(os.environ,{'ALLOW_MOCK_FALLBACK':'false'}),patch.object(GenerationService,'_providers',return_value={'dashscope_qwen_image':provider}),patch('provider_service.analyze_image',return_value={}),patch('provider_service._trace_generate'),patch.object(VisionAnalysisService,'analyze',side_effect=VisionAnalysisError('not available')):
            result=GenerationService().generate({'theme':'测试','style':'bianxiu','generationProvider':'dashscope_qwen_image'},base_url='http://fixture.invalid/')
        self.assertTrue(result['success']);self.assertEqual(result['analysisSource'],'template_fallback');self.assertIsNone(result['visionAnalysis'])
    def test_13_missing_key(self):
        with patch.dict(os.environ,{'DASHSCOPE_API_KEY':''}):self.assertFalse(DashScopeQwenImageProvider().is_available()[0])
    def test_invalid_image_rejected(self):
        with self.assertRaises(ProviderError):_save_image_bytes(b'not-an-image','bianxiu')
    def test_valid_image_saved(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder,patch('providers.dashscope_qwen_image_provider.OUTPUT_DIR',Path(folder)),patch('providers.dashscope_qwen_image_provider.ensure_runtime_dirs'):
            p=_save_image_bytes(png(),'bianxiu');self.assertEqual(p.read_bytes(),png())
    def test_subject_lock_optional_not_global_crane_ban(self):
        p={'theme':'仙鹤','style':'songhua','subjectLock':'白兔'}
        prompt=build_enhanced_prompt(p,get_style('songhua'));self.assertIn('白兔',prompt)
        prompt=build_enhanced_prompt({'theme':'仙鹤','style':'songhua'},get_style('songhua'));self.assertNotIn('唯一主要主体',prompt)

if __name__=='__main__':unittest.main(verbosity=2)
