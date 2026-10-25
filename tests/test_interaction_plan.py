"""Image-bound plans must stay distinct and never become template success."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from services.interaction_plan import InteractionPlanService, assemble_experience, validate_plan
from services.vision_analysis import VisionAnalysisError


def plan(subject):
    return {
        'title':subject+'与花枝','subtitle':'观察这幅画的主体、细节与关系',
        'lead':f'从画面中央的{subject}出发，观察花枝与背景的蓝白关系。',
        'observed_subjects':[subject,'花枝'],'dominant_colors':['蓝','白'],
        'visual_features':['蓝白对比','花枝环绕','主体居中'],
        'scene_kind':'flat_artwork',
        'motion_regions':{'water':False,'mist':False,'foliage':True},
        'hotspots':[{'title':subject+str(i+1),'x':x,'y':y,'r':0.09,'depth':.5,
            'observation':f'这一处能看到{subject}的外缘与周围细小花枝形成蓝白对比。',
            'interpretation':f'以{subject}的这一处轮廓为观察起点，可感受花枝之间疏密相间的装饰节奏。'}
            for i,(x,y) in enumerate(((.3,.3),(.7,.3),(.3,.7),(.7,.7)))],
        'chapters':[{'title':subject+label,'eyebrow':'图像阅读','body':f'这一段从{subject}的{label}出发，观察它与蓝白花枝之间的形态呼应，并把画面中的留白视为审美解读的起点。','focus_indices':[i]}
                    for i,label in enumerate(('形态','色彩','关系'))]
    }

STYLE={'name':'青花瓷纹样','explain':'蓝白器物装饰视觉语言','sources':['SRC-QH-JINGDEZHEN-001'],
       'accent':'#22508F','accentSoft':'#CBD9EC','paper':'#F3F5F8','ink':'#243040','gold':'#9C8556'}


class InteractionPlanTests(unittest.TestCase):
    def vision(self, plans):
        vision=Mock(enabled=True,model='qwen3-vl:test',chat_url='http://127.0.0.1:11434/api/chat',timeout=30,context_tokens=8192,max_image_bytes=20*1024*1024)
        responses=[]
        for item in plans:
            response=Mock();response.json.return_value={'message':{'content':json.dumps(item)},'model':'test-vl'}
            responses.append(response)
            for spot in item['hotspots']:
                crop={'useful':True,**{key:spot[key] for key in ('title','observation','interpretation')}}
                response=Mock();response.json.return_value={'message':{'content':json.dumps(crop)}}
                responses.append(response)
            narrative={key:item[key] for key in ('title','subtitle','lead','chapters')}
            response=Mock();response.json.return_value={'message':{'content':json.dumps(narrative)}}
            responses.append(response)
        vision.session.post.side_effect=responses
        return vision

    def test_two_images_same_style_get_different_grounded_content(self):
        a=assemble_experience('case-a','qinghua',STYLE,(100,100),{'inputImageSha256':'a'*64,'model':'test-vl','analysis':plan('蝴蝶')})
        b=assemble_experience('case-b','qinghua',STYLE,(100,100),{'inputImageSha256':'b'*64,'model':'test-vl','analysis':plan('小鸟')})
        self.assertNotEqual(a['chapters'],b['chapters'])
        self.assertIn('蝴蝶',a['hotspots'][0]['visualObservation'])
        self.assertIn('小鸟',b['hotspots'][0]['visualObservation'])
        self.assertNotIn('小鸟',json.dumps(a,ensure_ascii=False))
        self.assertNotEqual(a['animation']['world']['url'],b['animation']['world']['url'])

    def test_actual_image_is_sent_and_cache_invalidates_on_replacement(self):
        vision=self.vision([plan('蝴蝶'),plan('小鸟')])
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            image=Path(folder)/'generated.png';cache=Path(folder)/'interaction-analysis.json'
            Image.new('RGB',(30,30),'blue').save(image)
            service=InteractionPlanService(vision)
            a=service.analyze(image,STYLE,cache)
            payload=vision.session.post.call_args_list[0].kwargs['json']
            self.assertEqual(len(payload['messages'][-1]['images']),1)
            service.analyze(image,STYLE,cache)
            self.assertEqual(vision.session.post.call_count,6)
            Image.new('RGB',(30,30),'red').save(image)
            b=service.analyze(image,STYLE,cache)
            self.assertNotEqual(a['inputImageSha256'],b['inputImageSha256'])
            self.assertEqual(vision.session.post.call_count,12)
            review_payload=vision.session.post.call_args.kwargs['json']
            self.assertEqual(len(review_payload['messages'][-1]['images']),1)
            self.assertEqual(b['reviewModel'],vision.model)

    def test_unmatched_hotspot_review_cannot_publish_a_successful_plan(self):
        vision=self.vision([plan('蝴蝶'),plan('蝴蝶'),plan('蝴蝶')])
        # Each retry must still request a fresh whole-image plan.
        vision.session.post.side_effect=[vision.session.post.side_effect.__next__(),
                                        self.vision([plan('蝴蝶')]).session.post.side_effect.__next__(),
                                        self.vision([plan('蝴蝶')]).session.post.side_effect.__next__()]
        service=InteractionPlanService(vision)
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            image=Path(folder)/'image.png';Image.new('RGB',(30,30)).save(image)
            cache=Path(folder)/'plan.json'
            with patch.object(service,'review',side_effect=VisionAnalysisError('热点没有对应本图内容')):
                with self.assertRaises(VisionAnalysisError):service.analyze(image,STYLE,cache)
            self.assertFalse(cache.exists())

    def test_unavailable_vision_does_not_write_fake_plan(self):
        vision=self.vision([]);vision.enabled=False
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            image=Path(folder)/'generated.png';Image.new('RGB',(30,30)).save(image)
            cache=Path(folder)/'interaction-analysis.json'
            with self.assertRaises(VisionAnalysisError):InteractionPlanService(vision).analyze(image,STYLE,cache)
            self.assertFalse(cache.exists())

    def test_display_radius_is_bounded_without_changing_model_locations(self):
        value=plan('蝴蝶');value['hotspots'][0]['r']=.3
        vision=self.vision([value])
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            image=Path(folder)/'generated.png';Image.new('RGB',(30,30)).save(image)
            result=InteractionPlanService(vision).analyze(image,STYLE,Path(folder)/'plan.json')
        spot=result['analysis']['hotspots'][0]
        self.assertEqual(spot['r'],.2)
        self.assertEqual((spot['x'],spot['y']),(.3,.3))

    def test_bad_coordinates_and_foreign_chapter_references_are_rejected(self):
        for change in ('geometry','reference','duplicate'):
            value=plan('蝴蝶')
            if change=='geometry':value['hotspots'][0]['x']=1.3
            elif change=='reference':value['chapters'][0]['focus_indices']=[99]
            else:value['hotspots'][1]['x']=.3;value['hotspots'][1]['y']=.3
            with self.subTest(change=change),self.assertRaises(VisionAnalysisError):validate_plan(value)

    def test_other_models_and_remote_servers_are_rejected_before_any_request(self):
        for url,model in [('https://example.com/api/chat','qwen3-vl:4b'),
                          ('http://127.0.0.1:11434/api/chat','other-vision:latest')]:
            vision=self.vision([]);vision.chat_url=url;vision.model=model
            with self.subTest(url=url,model=model), self.assertRaises(VisionAnalysisError):
                InteractionPlanService(vision).analyze(ROOT/'frontend/public/qinghua.png',STYLE,ROOT/'.cache/forbidden-plan.json')
            vision.session.post.assert_not_called()


if __name__=='__main__':unittest.main(verbosity=2)
