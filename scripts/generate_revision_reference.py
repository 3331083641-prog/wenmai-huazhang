"""Generate one genuine embroidery-reference case using the installed app API."""
from pathlib import Path
import base64,json,urllib.request,time
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'iCAN_应用方案/视频/02_generated_assets/revision/bianxiu_reference'
DEST.mkdir(parents=True,exist_ok=True)
old=json.loads((ROOT/'iCAN_应用方案/05_生成案例/正式验收_20260929/02_汴绣/request_summary.json').read_text(encoding='utf-8'))
ref=ROOT/'backend/style_refs/bianxiu.png'
payload={k:old[k] for k in ['theme','styleStrength','compositionMode']}
payload.update(style='bianxiu',styleName=old.get('styleName','汴绣'),outputType='poster',negativePrompt=old.get('userNegativePrompt'),generationProvider='dashscope_qwen_image')
payload['uploadedImage']='data:image/png;base64,'+base64.b64encode(ref.read_bytes()).decode()
safe={k:v for k,v in payload.items() if k!='uploadedImage'}
safe['referenceFile']=str(ref)
(DEST/'request.json').write_text(json.dumps(safe,ensure_ascii=False,indent=2),encoding='utf-8')
(DEST/'reference.png').write_bytes(ref.read_bytes())
if (DEST/'response.json').exists():raise SystemExit('Existing result retained; no duplicate API request')
print('Generating one real embroidery-reference comparison',flush=True)
t=time.monotonic()
request=urllib.request.Request('http://127.0.0.1:8000/generate',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
result=json.load(urllib.request.urlopen(request,timeout=420))
if not result.get('imageUrl') or not result.get('referenceImageUsed'):raise RuntimeError('No genuine reference result')
(DEST/'response.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
urllib.request.urlretrieve(result['imageUrl'],DEST/'generated.png')
print(f'Genuine reference case saved in {time.monotonic()-t:.1f}s',flush=True)
