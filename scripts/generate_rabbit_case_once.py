"""One authorized paid request with the new photographic-style rabbit reference."""
from pathlib import Path
from datetime import datetime
import base64, hashlib, json, shutil, urllib.request

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'docs/examples/bianxiu'
EVIDENCE=ROOT/'.cache/aic-rabbit-real-call'
EVIDENCE.mkdir(parents=True,exist_ok=True)
if (EVIDENCE/'submitted.json').exists():
    raise SystemExit('Already submitted; no automatic paid retry.')
health=json.load(urllib.request.urlopen('http://127.0.0.1:8001/health',timeout=90))
assert health['provider']=='dashscope_qwen_image' and health['model']=='qwen-image-3.0'
assert health['providers']['dashscope_qwen_image']['available'] and not health['allowMockFallback']
for name in ['reference.png','generated.png','metadata.json','culture_card.png']:
    shutil.copy2(DEST/name,EVIDENCE/name)
source=Path('D:/Codex/.codex/generated_images/01a0ee16-3d92-7370-ab9c-2a6d6b169488/exec-b9757064-66f3-48f9-b2f5-735a40c1ec9a.png')
shutil.copy2(source, DEST/'reference.png')
payload={'theme':'绣兔牡丹：以参考图中的白兔为唯一主要动物，保持左向侧坐姿、长耳、眼睛、身体和四肢轮廓。把整只兔子重新表现为传统汴绣丝线织绣作品，不保留摄影皮毛。每个部位可见精细有方向的针脚，白色绣线带柔和丝光，兔耳粉色渐变绣线。加入少量粉红牡丹与青绿枝叶，花瓣、叶片同样以层层绣线表现。米白绢地、明确织物经纬和手工刺绣凹凸质感，主体居中完整、清雅有层次。',
 'style':'bianxiu','styleName':'汴绣纹样','styleStrength':1.0,'compositionMode':'object','outputType':'poster',
 'subjectLock':'一只白兔，左向侧坐、长耳、白色身体、完整四肢；主体不是鸟或仙鹤',
 'negativePrompt':'写实动物摄影，普通油画，水彩画，平涂插画，鸟，仙鹤，其他动物，多只兔子，文字，题字，水印，logo，二维码，畸形，多余肢体，裁切耳朵',
 'generationProvider':'dashscope_qwen_image'}
started=datetime.now().astimezone().isoformat()
(EVIDENCE/'submitted.json').write_text(json.dumps({'submittedAt':started,'payload':payload},ensure_ascii=False,indent=2),encoding='utf-8')
payload['uploadedImage']='data:image/png;base64,'+base64.b64encode(source.read_bytes()).decode('ascii')
req=urllib.request.Request('http://127.0.0.1:8001/generate',data=json.dumps(payload).encode('utf-8'),headers={'Content-Type':'application/json'})
result=json.load(urllib.request.urlopen(req,timeout=600))
assert result['success'] and result['provider']=='dashscope_qwen_image' and result['model']=='qwen-image-3.0'
assert result['referenceImageUsed'] is True and result['debug']['modelInputImageCount']==1
with urllib.request.urlopen(result['imageUrl'],timeout=90) as response:
    content=response.read()
from PIL import Image
import io
with Image.open(io.BytesIO(content)) as image:
    image.verify()
(DEST/'generated.png').write_bytes(content)
m={k:v for k,v in payload.items() if k not in ['uploadedImage','generationProvider','style']}
m.update(styleId='bianxiu',referenceSubject='白兔',artworkTitle='绣兔牡丹',referenceSource='2026-10-08 经用户授权，以旧兔子作品的主体姿态为参考，通过 Codex 内置 imagegen 生成白底写实风格兔子素材；不是相机实拍，不声明 CC0。',
 referenceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),generatedSha256=hashlib.sha256(content).hexdigest(),generatedBytes=len(content),
 provider=result['provider'],model=result['model'],generatedAt=started,generationSucceeded=True,referenceImageUsed=True,modelInputImageCount=1,
 analysisSource=result['analysisSource'],visionAnalysis=result.get('visionAnalysis'),visionProvider='ollama_local',visionModel='qwen3-vl:4b-instruct-q4_K_M',
 cultureCardAnalysisSource='qwen3_vl_on_generated_image' if result['analysisSource']=='qwen3_vl' else 'unavailable')
(DEST/'metadata.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'success':True,'referenceImageUsed':True,'inputImageCount':1,'analysisSource':m['analysisSource'],'generatedBytes':len(content)}))
