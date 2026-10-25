"""Image-bound plans must stay distinct and never become template success."""
from copy import deepcopy
import base64
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

    def test_repeated_padding_and_machine_field_eyebrows_are_rejected(self):
        for kind in ('repeated','field','numeric'):
            value=plan('蝴蝶')
            if kind=='repeated':value['chapters'][0]['body']='蓝白花枝之间的装饰节奏。'*7
            elif kind=='field':value['chapters'][0]['eyebrow']='focus_indices: 0'
            else:value['chapters'][0]['eyebrow']='0'
            with self.subTest(kind=kind),self.assertRaises(VisionAnalysisError):validate_plan(value)

    def test_other_models_and_remote_servers_are_rejected_before_any_request(self):
        for url,model in [('https://example.com/api/chat','qwen3-vl:4b'),
                          ('http://127.0.0.1:11434/api/chat','other-vision:latest')]:
            vision=self.vision([]);vision.chat_url=url;vision.model=model
            with self.subTest(url=url,model=model), self.assertRaises(VisionAnalysisError):
                InteractionPlanService(vision).analyze(ROOT/'frontend/public/qinghua.png',STYLE,ROOT/'.cache/forbidden-plan.json')
            vision.session.post.assert_not_called()

    def test_local_refinement_sends_full_image_and_cached_observations_but_keeps_hotspots(self):
        vision=self.vision([plan('蝴蝶')]);service=InteractionPlanService(vision)
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            image=Path(folder)/'image.png';cache=Path(folder)/'plan.json'
            Image.new('RGB',(30,30),'blue').save(image)
            original=service.analyze(image,STYLE,cache)
            narrative={key:deepcopy(original['analysis'][key]) for key in ('title','subtitle','lead','chapters')}
            narrative['title']='花枝间的蓝蝶'
            reply=Mock();reply.json.return_value={'message':{'content':json.dumps(narrative)}}
            vision.session.post.reset_mock();vision.session.post.side_effect=[reply]
            feedback={'issues':[{'code':'NARRATIVE_FACT','description':'请检查是否误写真实材料工艺'}]}
            result=service.refine_narrative(image,STYLE,cache,feedback)
            self.assertEqual(result['analysis']['title'],narrative['title'])
            self.assertEqual(result['analysis']['hotspots'],original['analysis']['hotspots'])
            self.assertEqual(result['localReview'],original['localReview'])
            self.assertEqual(json.loads(cache.read_text(encoding='utf-8')),result)
            payload=vision.session.post.call_args.kwargs['json']
            self.assertEqual(base64.b64decode(payload['messages'][1]['images'][0]),image.read_bytes())
            self.assertIn('不可信',payload['messages'][0]['content'])
            context=json.loads(payload['messages'][1]['content'])
            self.assertEqual(context['hotspots'],original['analysis']['hotspots'])
            self.assertEqual(context['untrustedCritique'],feedback)
            self.assertEqual(set(payload['format']['properties']),{'title','subtitle','lead','chapters'})
            proof=result['localNarrativeRefinement']
            self.assertEqual(proof['model'],vision.model)
            self.assertEqual(proof['inputImageSha256'],original['inputImageSha256'])
            self.assertEqual(proof['source'],'local_qwen3_vl_actual_image')
            self.assertEqual(proof['attempts'],1)
            self.assertEqual(len(proof['feedbackSha256']),64)

    def test_refinement_retries_validation_three_times_without_overwriting_on_failure(self):
        vision=self.vision([plan('蝴蝶')]);service=InteractionPlanService(vision)
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            image=Path(folder)/'image.png';cache=Path(folder)/'plan.json'
            Image.new('RGB',(30,30)).save(image)
            original=service.analyze(image,STYLE,cache);before=cache.read_bytes()
            narrative={key:deepcopy(original['analysis'][key]) for key in ('title','subtitle','lead','chapters')}
            narrative['chapters'][0]['eyebrow']='观察1'
            reply=Mock();reply.json.return_value={'message':{'content':json.dumps(narrative)}}
            vision.session.post.reset_mock();vision.session.post.side_effect=[reply,reply,reply]
            with self.assertRaises(VisionAnalysisError):service.refine_narrative(image,STYLE,cache,{'issues':[]})
            self.assertEqual(vision.session.post.call_count,3)
            self.assertEqual(cache.read_bytes(),before)
            self.assertIn('修正',vision.session.post.call_args.kwargs['json']['messages'][-1]['content'])

    def test_refinement_rejects_stale_image_model_or_local_crop_review_before_request(self):
        vision=self.vision([plan('蝴蝶')]);service=InteractionPlanService(vision)
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            image=Path(folder)/'image.png';cache=Path(folder)/'plan.json'
            Image.new('RGB',(30,30)).save(image);original=service.analyze(image,STYLE,cache)
            for kind in ('image','model','review','crop'):
                artifact=deepcopy(original)
                if kind=='image':artifact['inputImageSha256']='0'*64
                elif kind=='model':artifact['model']='other-model'
                elif kind=='review':artifact.pop('localReview')
                else:artifact['localReview']['hotspots'][0]['inputCropSha256']='0'*64
                cache.write_text(json.dumps(artifact),encoding='utf-8')
                vision.session.post.reset_mock()
                with self.subTest(kind=kind),self.assertRaises(VisionAnalysisError):
                    service.refine_narrative(image,STYLE,cache,{})
                vision.session.post.assert_not_called()

    def test_refinement_rejects_nonlocal_provider_before_reading_cache(self):
        vision=self.vision([]);vision.chat_url='https://api.deepseek.com/chat/completions'
        with self.assertRaises(VisionAnalysisError):
            InteractionPlanService(vision).refine_narrative('missing.png',STYLE,'missing.json',{})
        vision.session.post.assert_not_called()

    def test_refinement_recovers_from_invalid_local_response_and_records_attempt_count(self):
        vision=self.vision([plan('蝴蝶')]);service=InteractionPlanService(vision)
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            image=Path(folder)/'image.png';cache=Path(folder)/'plan.json'
            Image.new('RGB',(30,30)).save(image);original=service.analyze(image,STYLE,cache)
            narrative={key:deepcopy(original['analysis'][key]) for key in ('title','subtitle','lead','chapters')}
            invalid=deepcopy(narrative);invalid['chapters'][0]['injectedField']='not allowed'
            bad=Mock();bad.json.return_value={'message':{'content':json.dumps(invalid)}}
            good=Mock();good.json.return_value={'message':{'content':json.dumps(narrative)}}
            vision.session.post.reset_mock();vision.session.post.side_effect=[bad,good]
            result=service.refine_narrative(image,STYLE,cache,{'issues':[]})
            self.assertEqual(vision.session.post.call_count,2)
            self.assertEqual(result['localNarrativeRefinement']['attempts'],2)
            self.assertNotIn('injectedField',result['analysis']['chapters'][0])

    def test_hotspot_refinement_uses_local_integer_points_then_rereads_real_crops(self):
        vision=self.vision([plan('蝴蝶')]);service=InteractionPlanService(vision)
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            image=Path(folder)/'image.png';cache=Path(folder)/'plan.json'
            Image.new('RGB',(60,60),'blue').save(image);original=service.analyze(image,STYLE,cache)
            points=[(250,250),(750,250),(250,750),(750,750)]
            replies=[]
            for point in points:
                reply=Mock();reply.json.return_value={'message':{'content':json.dumps({'point_2d':list(point)})}}
                replies.append(reply)
            replies+=list(self.vision([plan('蝴蝶')]).session.post.side_effect)[1:]
            vision.session.post.reset_mock();vision.session.post.side_effect=replies
            result=service.refine_hotspots(image,STYLE,cache,{'suggestedPoint':[999,999]})
            self.assertEqual(vision.session.post.call_count,9)
            for index,point in enumerate(points):
                spot=result['analysis']['hotspots'][index]
                self.assertEqual((spot['x'],spot['y']),(point[0]/1000,point[1]/1000))
                payload=vision.session.post.call_args_list[index].kwargs['json']
                self.assertEqual(base64.b64decode(payload['messages'][1]['images'][0]),image.read_bytes())
                context=json.loads(payload['messages'][1]['content'])
                self.assertEqual(context['target']['title'],original['analysis']['hotspots'][index]['title'])
                self.assertIn('不可信',payload['messages'][0]['content'])
                self.assertFalse(vision.session.post.call_args_list[index].kwargs['allow_redirects'])
            self.assertNotEqual(result['localReview']['hotspots'][0]['cropBox'],original['localReview']['hotspots'][0]['cropBox'])
            proof=result['localHotspotRefinement']
            self.assertEqual(proof['model'],vision.model)
            self.assertEqual(proof['attempts'],1)
            self.assertEqual(proof['initialProposedPositions'][0]['x'],.3)
            self.assertEqual(proof['inputImageSha256'],original['inputImageSha256'])
            self.assertEqual(json.loads(cache.read_text(encoding='utf-8')),result)
            # The new crop provenance must itself satisfy the next local repair's guard.
            service._refinement_input(image,STYLE,cache,{})

    def test_hotspot_refinement_rejects_bad_points_and_preserves_old_cache(self):
        vision=self.vision([plan('蝴蝶')]);service=InteractionPlanService(vision)
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            image=Path(folder)/'image.png';cache=Path(folder)/'plan.json'
            Image.new('RGB',(30,30)).save(image);service.analyze(image,STYLE,cache);before=cache.read_bytes()
            for point in ([True,250],[float('nan'),250],[1001,250],[-1,250],[25.5,250],[250],None):
                reply=Mock();reply.json.return_value={'message':{'content':json.dumps({'point_2d':point})}}
                vision.session.post.reset_mock();vision.session.post.side_effect=[reply,reply]
                with self.subTest(point=point),self.assertRaises(VisionAnalysisError):
                    service.refine_hotspots(image,STYLE,cache,{})
                self.assertEqual(vision.session.post.call_count,2)
                self.assertEqual(cache.read_bytes(),before)
            repeated=Mock();repeated.json.return_value={'message':{'content':json.dumps({'point_2d':[250,250]})}}
            vision.session.post.reset_mock();vision.session.post.side_effect=[repeated]*8
            with patch.object(service,'review') as review:
                with self.assertRaises(VisionAnalysisError):service.refine_hotspots(image,STYLE,cache,{})
                review.assert_not_called()
            self.assertEqual(cache.read_bytes(),before)

    def test_hotspot_refinement_reuses_local_endpoint_and_crop_evidence_guards(self):
        vision=self.vision([]);vision.chat_url='https://api.deepseek.com/chat/completions'
        with self.assertRaises(VisionAnalysisError):
            InteractionPlanService(vision).refine_hotspots('missing.png',STYLE,'missing.json',{})
        vision.session.post.assert_not_called()

    def test_hotspot_refinement_crop_failure_never_publishes_proposed_positions(self):
        vision=self.vision([plan('蝴蝶')]);service=InteractionPlanService(vision)
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            image=Path(folder)/'image.png';cache=Path(folder)/'plan.json'
            Image.new('RGB',(30,30)).save(image);service.analyze(image,STYLE,cache);before=cache.read_bytes()
            replies=[]
            for point in [(250,250),(750,250),(250,750),(750,750)]*2:
                reply=Mock();reply.json.return_value={'message':{'content':json.dumps({'point_2d':list(point)})}}
                replies.append(reply)
            vision.session.post.reset_mock();vision.session.post.side_effect=replies
            with patch.object(service,'review',side_effect=VisionAnalysisError('实际裁切为空白')) as review:
                with self.assertRaises(VisionAnalysisError):service.refine_hotspots(image,STYLE,cache,{})
                self.assertEqual(review.call_count,2)
            self.assertEqual(vision.session.post.call_count,8)
            self.assertEqual(cache.read_bytes(),before)


if __name__=='__main__':unittest.main(verbosity=2)
