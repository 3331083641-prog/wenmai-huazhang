"""One call per parameter. Preserve genuine prompts and image provenance."""
from pathlib import Path
import json,urllib.request,time
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'iCAN_应用方案/视频/02_generated_assets/revision/strength'
old=json.loads((ROOT/'iCAN_应用方案/05_生成案例/正式验收_20260929/02_汴绣/request_summary.json').read_text(encoding='utf-8'))
for strength in [.65,.9]:
    folder=DEST/str(round(strength*100));folder.mkdir(parents=True,exist_ok=True)
    if (folder/'generated.png').exists():continue
    payload={k:old[k] for k in ['theme','style','styleName','compositionMode']}
    payload.update(outputType='poster',styleStrength=strength,negativePrompt=old['userNegativePrompt'],generationProvider='dashscope_qwen_image')
    (folder/'request.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Generating genuine strength {round(strength*100)}%',flush=True)
    t=time.monotonic()
    req=urllib.request.Request('http://127.0.0.1:8000/generate',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    response=json.load(urllib.request.urlopen(req,timeout=420))
    (folder/'response.json').write_text(json.dumps(response,ensure_ascii=False,indent=2),encoding='utf-8')
    if not response.get('imageUrl') or response.get('referenceImageUsed'):
        print('Generation did not return a valid image; safe response fields:',{k:response.get(k) for k in ['success','errorCode','status']},flush=True)
        raise RuntimeError('No genuine text generation; inspect archived response before retry')
    urllib.request.urlretrieve(response['imageUrl'],folder/'generated.png')
    print(f'Real output saved after {time.monotonic()-t:.1f}s',flush=True)
