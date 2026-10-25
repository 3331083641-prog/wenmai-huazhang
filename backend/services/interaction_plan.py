"""Qwen3-VL plans grounded in the bytes of one actual generated image."""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import io
import json
import math
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from PIL import Image

from services.vision_analysis import VisionAnalysisError, VisionAnalysisService

PLAN_VERSION = 2


def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def _text(minimum=1, maximum=400):
    return {'type': 'string', 'minLength': minimum, 'maxLength': maximum}


def _array(items, minimum, maximum):
    return {'type': 'array', 'items': items, 'minItems': minimum, 'maxItems': maximum}


PLAN_SCHEMA = _object({
    'title': _text(1, 24), 'subtitle': _text(1, 40), 'lead': _text(8, 200),
    'observed_subjects': _array(_text(1, 40), 1, 8),
    'dominant_colors': _array(_text(1, 30), 2, 5),
    'visual_features': _array(_text(1, 60), 3, 6),
    'scene_kind': {'type': 'string', 'enum': ['flat_artwork', 'spatial_scene'], 'minLength': 1, 'maxLength': 20},
    'motion_regions': _object({key: {'type': 'boolean'} for key in ('water', 'mist', 'foliage')}),
    'hotspots': _array(_object({
        'title': _text(1, 24), 'x': {'type': 'number', 'minimum': 0, 'maximum': 1},
        'y': {'type': 'number', 'minimum': 0, 'maximum': 1},
        'r': {'type': 'number', 'minimum': .04, 'maximum': .2},
        'depth': {'type': 'number', 'minimum': .1, 'maximum': .9},
        'observation': _text(10, 200), 'interpretation': _text(20, 240),
    }), 4, 6),
    'chapters': _array(_object({
        'title': _text(1, 40), 'eyebrow': _text(1, 16), 'body': _text(40, 300),
        'focus_indices': _array({'type': 'integer', 'minimum': 0, 'maximum': 5}, 1, 3),
    }), 3, 3),
})

CROP_SCHEMA = _object({
    'useful': {'type':'boolean'}, 'title': _text(1,24),
    'observation': _text(10,200), 'interpretation': _text(20,240),
})

REVIEW_PROMPT = """你是本地Qwen3-VL局部图像观察助手。第一张为完整AI画作，用于认出主体与方位；第二张是本次唯一要解读的实际裁切局部。
只描述第二张清楚可见的形状、色彩、纹样、结构。可结合第一张辨认局部属于主体哪个部位，不添加两张图都没有的内容。
useful：有清楚的纹样/主体细节则true；纯空白、无法识别则false。
title必须写具体主体部位或元素及其可见特色，不使用“局部图”“截图”、坐标数字或空泛的“纹样局部”作为标题。observation只写看见什么。
interpretation写这些可见线条、色彩、疏密与留白带来的审美感受，20至80字。不要编造民俗寓意、历史出处、针法/雕刻/烧制工艺事实，不套玄学词语。
本图是AI画作，描写风格相似不代表认定真实工艺。简体中文，只返回schema规定的JSON。"""

NARRATIVE_PROMPT = """你是本地Qwen3-VL看图叙事助手。请看实际完整成图，再参考本地Qwen3-VL逐局部读取的4处观察，为这张图写独特的标题、引子和3个章节。
必须围绕本图真实主体、局部线条色彩和它们的构图关系写作，各章40至100字。不能用同风格通用历史说明充数，也不编造民俗寓意、文化事实或真实工艺归属。
每章focus_indices从0开始，只引用给出的hotspots下标，3章不同。审美联想可以保留，但不能将AI图像当作历史实物。简体中文，只返回schema规定的JSON。"""

SYSTEM_PROMPT = '''你是纹脉华章的实际成图解读与互动策划助手，必须先看本次附带图片，再策划内容。
只能依据图片真实可见内容写作；风格资料只是文化背景，不代表画中一定存在某种动物、器物或景物。
先列可见主体、色彩、构图关系，再选4至6处不同位置的真实细节。热点标题要具体且不同，观察只描述看见的形状、颜色、相对位置。
interpretation 必须从该处实际可见细节展开，文化联想用“可联想到/呈现出”等审美措辞，不捏造历史事实、出处、非遗身份、馆藏或手工制作归属。
写3段彼此不同、只属于这张画的章节：每段围绕具体主体或局部关系展开，不能把同风格通用说明复制三次，也不能只有抽象口号。
热点x/y均为整幅图片0到1的归一化中心，原点左上，x向右、y向下，r按画面短边计。只选择4处清晰且分散的单个细节，各中心必须相距至少0.08，不要在同一花朵或鹤头上挤多个点。4个标题不能重复，不能将整幅图的标题用于全部热点。
chapters.focus_indices 引用 hotspots 数组下标，严格从0开始，不能引用不存在的下标。
motion_regions 仅在画面真实可见水面/云雾/植物时分别设为true，不能把瓷器蓝纹一律判断成水面。
scene_kind：纸面纹样、剪纸、刺绣或居中的装饰主体通常为flat_artwork；有明确前后遮挡的山水空间为spatial_scene。
每个热点depth是该处可见内容的相对景深，0.1远、0.9近；依据遮挡与远近大小判断，不能依据颜色深浅推断远近。平面装饰各处应接近0.5，不臆造前后层次。
本图是AI图像，全部章节也必须区分视觉相似和真实制作工艺。不得认定釉下彩、点彩或针法实际存在，不用“象征某寓意”“暗示某仙物”等无依据断言。只写可见形态及有保留的审美联想。
interpretation和章节以本图具体形状、色彩、留白与疏密的审美感受为主；不要套用“天人合一、阴阳相生、水火相生”或为动物颜色编造民俗寓意。经核验的风格背景会由页面另行提供。
title不超过24字、subtitle不超过40字；观察10至80字、解读20至80字、每段章节正文40至100字。简体中文，只返回符合schema的JSON。'''


def _check(value, schema, path='plan'):
    kind = schema['type']
    if kind == 'object':
        if not isinstance(value, dict):
            raise VisionAnalysisError(f'{path} 不是对象')
        for key, item in schema['properties'].items():
            if key not in value:
                raise VisionAnalysisError(f'{path}.{key} 缺失')
            _check(value[key], item, path + '.' + key)
    elif kind == 'array':
        if not isinstance(value, list) or not schema['minItems'] <= len(value) <= schema['maxItems']:
            raise VisionAnalysisError(f'{path} 项数不符合约定')
        for i, item in enumerate(value):
            _check(item, schema['items'], f'{path}[{i}]')
    elif kind == 'string':
        if not isinstance(value, str) or not schema['minLength'] <= len(value.strip()) <= schema['maxLength']:
            raise VisionAnalysisError(f'{path} 文字长度不符合约定')
        if 'enum' in schema and value not in schema['enum']:
            raise VisionAnalysisError(f'{path} 不属于允许的类型')
    elif kind == 'boolean':
        if not isinstance(value, bool):
            raise VisionAnalysisError(f'{path} 不是布尔值')
    elif isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise VisionAnalysisError(f'{path} 不是有效数字')
    elif kind == 'integer' and not isinstance(value, int):
        raise VisionAnalysisError(f'{path} 不是整数')
    elif not schema['minimum'] <= value <= schema['maximum']:
        raise VisionAnalysisError(f'{path} 坐标或引用越界')


def validate_plan(value):
    _check(value, PLAN_SCHEMA)
    spots = value['hotspots']
    if len({s['title'].strip() for s in spots}) != len(spots):
        raise VisionAnalysisError('热点标题重复')
    for i, spot in enumerate(spots):
        for previous in spots[:i]:
            if math.hypot(spot['x']-previous['x'], spot['y']-previous['y']) < .08:
                raise VisionAnalysisError(f"热点位置过于集中：{previous['title']}({previous['x']},{previous['y']})与{spot['title']}({spot['x']},{spot['y']})，请从本图另选可见细节，最多4处即可")
    for chapter in value['chapters']:
        if any(index >= len(spots) for index in chapter['focus_indices']):
            raise VisionAnalysisError('章节引用了不存在的热点')
    if len({c['body'].strip() for c in value['chapters']}) != 3:
        raise VisionAnalysisError('章节内容重复')
    return value


def bound_display_radii(value):
    """Constrain marker size only; never repair an invented position or text."""
    result = deepcopy(value)
    if isinstance(result, dict) and isinstance(result.get('hotspots'), list):
        for spot in result['hotspots']:
            if not isinstance(spot, dict):
                continue
            radius = spot.get('r')
            if (not isinstance(radius, bool) and isinstance(radius, (int, float))
                    and math.isfinite(radius) and 0 < radius <= .5):
                spot['r'] = min(.2, max(.04, radius))
    return result


class InteractionPlanService:
    def __init__(self, vision=None):
        self.vision = vision or VisionAnalysisService()

    def review(self, image_bytes, analysis):
        """Read every actual crop with local Qwen, then write the story from those readings."""
        vision=self.vision
        def ask(prompt, schema, context, pixels, limit=1800):
            response=vision.session.post(vision.chat_url,json={
                'model':vision.model,'stream':False,'format':schema,'keep_alive':'2m',
                'messages':[{'role':'system','content':prompt},
                            {'role':'user','content':json.dumps(context,ensure_ascii=False),
                             'images':[base64.b64encode(item).decode('ascii') for item in (pixels if isinstance(pixels,list) else [pixels])]}],
                'options':{'temperature':.2,'num_ctx':vision.context_tokens,'num_predict':limit},
            },timeout=vision.timeout,allow_redirects=False)
            response.raise_for_status()
            value=json.loads(response.json()['message']['content'])
            _check(value,schema,'local_crop_or_story')
            return value

        evidence=[]
        with Image.open(io.BytesIO(image_bytes)) as source:
            source=source.convert('RGB')
            overview=source.copy();overview.thumbnail((512,512))
            overview_buffer=io.BytesIO();overview.save(overview_buffer,format='PNG')
            for index,spot in enumerate(analysis['hotspots']):
                radius=max(.10,spot['r'])*1.35
                left=max(0,round((spot['x']-radius)*source.width))
                top=max(0,round((spot['y']-radius)*source.height))
                right=min(source.width,round((spot['x']+radius)*source.width))
                bottom=min(source.height,round((spot['y']+radius)*source.height))
                piece=source.crop((left,top,right,bottom));piece.thumbnail((448,448))
                buffer=io.BytesIO();piece.save(buffer,format='PNG');pixels=buffer.getvalue()
                region=('左' if spot['x']<.4 else '右' if spot['x']>.6 else '中')+('上' if spot['y']<.4 else '下' if spot['y']>.6 else '部')
                result=ask(REVIEW_PROMPT,CROP_SCHEMA,{'regionInWholeImage':region,
                    'instruction':'第一张看主体关系，第二张读取该处细节；用具体元素或部位命名'},[overview_buffer.getvalue(),pixels],900)
                if not result['useful']:
                    raise VisionAnalysisError(f'热点{index}实际裁切缺少清楚可见内容，请从原图重新选点')
                if re.search(r'局部图|截图|\d+\.\d+', result['title']):
                    raise VisionAnalysisError('热点标题必须写实际可见元素，不使用局部图或坐标数字')
                spot.update({key:result[key] for key in ('title','observation','interpretation')})
                evidence.append({'index':index,'inputCropSha256':hashlib.sha256(pixels).hexdigest(),
                    'cropBox':[left,top,right,bottom],'model':vision.model,'analysis':result})

        narrative_schema=_object({key:deepcopy(PLAN_SCHEMA['properties'][key]) for key in ('title','subtitle','lead','chapters')})
        narrative_schema['properties']['chapters']['items']['properties']['body']['maxLength']=140
        narrative=ask(NARRATIVE_PROMPT,narrative_schema,{'hotspots':analysis['hotspots'],
            'visibleSubjects':analysis['observed_subjects']},image_bytes,2200)
        analysis.update(narrative)
        validate_plan(analysis)
        return {'kind':'qwen3_vl_actual_crop_grounding','hotspots':evidence,
                'storySource':'same-image whole view plus local-Qwen crop observations'}

    def analyze(self, image_path, style, cache_path):
        vision = self.vision
        endpoint = urlsplit(vision.chat_url)
        if (endpoint.scheme != 'http' or endpoint.hostname not in {'127.0.0.1', 'localhost', '::1'}
                or endpoint.username or endpoint.password or endpoint.path != '/api/chat'):
            raise VisionAnalysisError('互动解析仅允许本机 Ollama /api/chat，禁止云端或远程模型。')
        if not vision.model.lower().startswith('qwen3-vl:') or 'cloud' in vision.model.lower():
            raise VisionAnalysisError('互动解析只允许本地 Qwen3-VL 模型，禁止其他模型替代。')
        vision.session.trust_env = False
        if not vision.enabled:
            raise VisionAnalysisError('互动构建需要启用本地 Qwen3-VL，不能用风格模板冒充图片解析。')
        image_bytes = Path(image_path).read_bytes()
        if not image_bytes or len(image_bytes) > vision.max_image_bytes:
            raise VisionAnalysisError('互动解析图片为空或超过大小限制。')
        digest = hashlib.sha256(image_bytes).hexdigest()
        context = {'style_name': style['name'], 'verified_style_context': style['explain']}
        context_digest = hashlib.sha256(json.dumps(context, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        prompt_digest = hashlib.sha256((SYSTEM_PROMPT+REVIEW_PROMPT+NARRATIVE_PROMPT).encode()).hexdigest()
        cache_path = Path(cache_path)
        try:
            cached = json.loads(cache_path.read_text(encoding='utf-8'))
            if (cached.get('schemaVersion') == PLAN_VERSION and cached.get('inputImageSha256') == digest
                    and cached.get('contextSha256') == context_digest and cached.get('model') == vision.model
                    and cached.get('promptSha256') == prompt_digest):
                validate_plan(cached['analysis'])
                if not cached.get('localReview'):raise VisionAnalysisError('缺少本地局部复核')
                return cached
        except (OSError, ValueError, KeyError, VisionAnalysisError):
            pass
        generation_schema=deepcopy(PLAN_SCHEMA)
        generation_schema['properties']['hotspots']['maxItems']=4
        generation_schema['properties']['chapters']['items']['properties']['body']['maxLength']=140
        payload = {
            'model': vision.model, 'stream': False, 'format': generation_schema, 'keep_alive': '2m',
            'messages': [{'role': 'system', 'content': SYSTEM_PROMPT},
                         {'role': 'user', 'content': json.dumps(context, ensure_ascii=False),
                          'images': [base64.b64encode(image_bytes).decode('ascii')]}],
            'options': {'temperature': .3, 'num_ctx': vision.context_tokens, 'num_predict': 3000},
        }
        initial_messages = payload['messages'][:]
        last_error = None
        for attempt in range(3):
            raw_content = ''
            try:
                response = vision.session.post(vision.chat_url, json=payload, timeout=vision.timeout, allow_redirects=False)
                response.raise_for_status()
                body = response.json()
                raw_content = body['message']['content']
                analysis = validate_plan(bound_display_radii(json.loads(raw_content)))
                review = self.review(image_bytes, analysis)
                break
            except VisionAnalysisError as exc:
                last_error = exc
                diagnostic=Path(__file__).resolve().parents[2]/'.cache/interaction-diagnostics'/digest
                diagnostic.mkdir(parents=True,exist_ok=True)
                (diagnostic/f'attempt-{attempt+1}.json').write_text(json.dumps({'error':str(exc),'response':raw_content},ensure_ascii=False,indent=2),encoding='utf-8')
                payload['messages'] = initial_messages + [
                    {'role':'user','content':'上述方案未通过本地核对，请重新看原图并完整重写方案。修正：'+str(exc)}]
            except (ValueError, KeyError, TypeError) as exc:
                last_error = exc
                payload['messages'][1]['content'] += '\n请严格返回完整JSON，检查文字长度、坐标及章节热点下标。'
            except Exception as exc:
                raise VisionAnalysisError(f'Qwen3-VL 互动图片解析请求失败：{type(exc).__name__}') from exc
        else:
            raise VisionAnalysisError('Qwen3-VL 互动策划未通过完整性校验：' + str(last_error)[:120])
        result = {'schemaVersion': PLAN_VERSION, 'contentSource': 'qwen3_vl_image',
                  'inputImageSha256': digest, 'contextSha256': context_digest, 'promptSha256': prompt_digest, 'model': vision.model,
                  'inputImageCount': 1, 'inputImageBytes': len(image_bytes), 'analysis': analysis,
                  'totalDurationNs': body.get('total_duration'), 'localReview':review,
                  'reviewModel':vision.model,'reviewInput':'same-image whole view and deterministic hotspot crops'}
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache_path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(cache_path)
        return result


def assemble_experience(slug, style_id, style, image_size, artifact):
    plan = validate_plan(artifact['analysis'])
    prefix = artifact['inputImageSha256'][:12]
    hotspots = []
    for i, spot in enumerate(plan['hotspots']):
        chapter = next((n+1 for n,c in enumerate(plan['chapters']) if i in c['focus_indices']), 1)
        hotspots.append({'id': f'{prefix}-spot-{i+1}', 'title': spot['title'], 'kicker': '画面细读',
            'shape': 'circle', 'geometry': {'cx': spot['x'], 'cy': spot['y'], 'r': spot['r']},
            'shortDescription': spot['observation'][:60], 'visualObservation': spot['observation'],
            'culturalExplanation': spot['interpretation'], 'sourceIds': list(style['sources']),
            'locationStatus': 'approximate', 'reviewStatus': 'pending', 'relatedChapterId': f'fold-{chapter}'})
    chapters = []
    for n, chapter in enumerate(plan['chapters'], 1):
        group = [hotspots[i] for i in chapter['focus_indices']]
        cx = sum(h['geometry']['cx'] for h in group)/len(group)
        cy = sum(h['geometry']['cy'] for h in group)/len(group)
        chapters.append({'id': f'fold-{n}', 'index': n, 'eyebrow': chapter['eyebrow'],
            'title': chapter['title'], 'body': chapter['body'], 'focusHotspotIds': [h['id'] for h in group],
            'frame': {'scale': round(1.7-.6*max(abs(cx-.5),abs(cy-.5)),2), 'focusX':cx,'focusY':cy},
            'sourceIds': list(style['sources'])})
    return {'id':slug,'styleId':style_id,'styleName':style['name'],'title':plan['title'],
        'subtitle':plan['subtitle'],'lead':plan['lead'],
        'artworkSize':{'width':image_size[0],'height':image_size[1]},
        'theme':{key:style[key] for key in ('accent','accentSoft','paper','ink','gold')},
        'visualAnalysis':{'source':'qwen3_vl_image','model':artifact['model'],
            'observedSubjects':plan['observed_subjects'],'visualFeatures':plan['visual_features'],
            'sceneKind':plan['scene_kind'],
            'dominantColors':plan['dominant_colors']},
        'hotspots':hotspots,'chapters':chapters,
        'animation':{'mode':'world','world':{'url':f'interactive/{slug}/world/world.json'},
            'capabilityNote':'画境贴图、热点与深度均对应这张成图；支持推进与有限转头，不恢复遮挡背面，不是完整三维重建。',
            'layerSource':'本图深度与颜色派生素材；微动类别按本图视觉解析启用。'},
        'provenance':{'sourceCaseId':slug,'sourceImageSha256':artifact['inputImageSha256'],
            'knowledgeVersion':'1.0.0','hotspotMethod':'Qwen3-VL 直接读取本图，估计归一化热点；自动定位不冒充人工复核。',
            'designNote':'热点观察、局部审美解读与三折叙事均来自本图专属视觉策划；来源条目用于文化背景，不认证AI画面。'}}
