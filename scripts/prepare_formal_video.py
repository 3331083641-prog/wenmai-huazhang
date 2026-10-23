from pathlib import Path
import asyncio,json,sys,shutil,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
V=ROOT/'iCAN_应用方案/视频'
R=V/'05_remotion'
sys.path.insert(0,str(ROOT/'.cache/publication_tools'))
import edge_tts,imageio_ffmpeg
FF=imageio_ffmpeg.get_ffmpeg_exe()
chapters=json.loads((V/'03_voiceover/旁白章节.json').read_text(encoding='utf-8'))

async def narrations():
    for chapter in chapters:
        i=chapter['id'];p=V/f'03_voiceover/voice_{i:02d}.mp3'
        if not p.exists():
            maker=edge_tts.SubMaker()
            with p.open('wb') as out:
                async for chunk in edge_tts.Communicate(chapter['speechText'],'zh-CN-YunxiNeural',rate='-2%').stream():
                    if chunk['type']=='audio':out.write(chunk['data'])
                    elif chunk['type'] in ('SentenceBoundary','WordBoundary'):maker.feed(chunk)
            (V/f'04_subtitles/voice_{i:02d}.srt').write_text(maker.get_srt(),encoding='utf-8')
        info=subprocess.run([FF,'-hide_banner','-i',str(p)],capture_output=True,text=True,encoding='utf-8',errors='replace').stderr
        h,m,s=re.search(r'Duration: (\d+):(\d+):([\d.]+)',info).groups();duration=int(h)*3600+int(m)*60+float(s)
        chapter['voiceDuration']=duration
        if duration>chapter['duration']-1:raise RuntimeError(f'Voice {i} exceeds slot: {duration}')
        shutil.copy2(p,R/f'public/voice/voice_{i:02d}.mp3')
        print(f'Voice {i+1}/10: {duration:.1f}s / {chapter["duration"]}s',flush=True)

def seconds(s):
    h,m,s=s.split(':');return int(h)*3600+int(m)*60+float(s.replace(',','.'))
def srt_time(s):
    x=round(s*1000);return f'{x//3600000:02d}:{x//60000%60:02d}:{x//1000%60:02d},{x%1000:03d}'
def main():
    asyncio.run(narrations())
    captions=[]
    names={'千问图像三点零':'Qwen Image 3.0','千问三视觉模型':'Qwen3-VL','文化说明卡':'CultureCard','提示词构建器':'Prompt Builder'}
    for ch in chapters:
        text=(V/f'04_subtitles/voice_{ch["id"]:02d}.srt').read_text(encoding='utf-8')
        for block in text.strip().split('\n\n'):
            lines=block.splitlines()
            if len(lines)<3:continue
            a,b=lines[1].split(' --> ');a=seconds(a)+ch['startSeconds']+.5;b=seconds(b)+ch['startSeconds']+.5
            spoken=''.join(lines[2:]).replace(',','');parts=[];part=''
            # Keep complete phrases and culture/model names within each cue.
            phrases=re.findall(r'[^，。；：、]+[，。；：、]*',spoken)
            for phrase in phrases:
                if part and len(part)+len(phrase)>24:
                    parts.append(part);part=''
                part+=phrase
            if part:parts.append(part)
            position=0
            for part in parts:
                end=position+len(part);display=part
                for key,val in names.items():display=display.replace(key,val)
                display=display.strip(' ，。；：、,')
                captions.append({'text':display,'startMs':round((a+(b-a)*position/len(spoken))*1000),'endMs':round((a+(b-a)*end/len(spoken))*1000),'timestampMs':None,'confidence':None})
                position=end
    for current,following in zip(captions,captions[1:]):
        current['endMs']=min(current['endMs'],following['startMs'])
    (R/'public/data/captions.json').write_text(json.dumps(captions,ensure_ascii=False,indent=2),encoding='utf-8')
    (R/'public/data/chapters.json').write_text(json.dumps(chapters,ensure_ascii=False,indent=2),encoding='utf-8')
    (V/'04_subtitles/字幕.srt').write_text('\n\n'.join(f'{i+1}\n{srt_time(c["startMs"]/1000)} --> {srt_time(c["endMs"]/1000)}\n{c["text"]}' for i,c in enumerate(captions))+'\n',encoding='utf-8-sig')
    formal=ROOT/'iCAN_应用方案/05_生成案例/正式验收_20260929'
    comparisons=ROOT/'iCAN_应用方案/08_对照实验'
    cases={
        'strength30': comparisons/'风格强度/30_汴绣_低强度/generated.png',
        'strength65': V/'02_generated_assets/revision/strength/65/generated.png',
        'strength90': V/'02_generated_assets/revision/strength/90/generated.png',
        'negativeNo':comparisons/'负向提示词/A_未填写用户排除词/generated.png',
        'negativeYes':formal/'02_汴绣/generated.png',
        'referenceInput':ROOT/'backend/style_refs/bianxiu.png',
        'referenceNo':V/'02_generated_assets/revision/strength/65/generated.png',
        'referenceYes':V/'02_generated_assets/revision/bianxiu_reference/generated.png',
        'scenarios':ROOT/'iCAN_应用方案/figures/references/figure_14_scenarios.png',
        'work':V/'02_generated_assets/generated.png',
        'cultureCard':V/'02_generated_assets/CultureCard.png',
        'postcard':V/'02_generated_assets/postcard.png',
        'bag':V/'02_generated_assets/bag.png',
    }
    for name,p in cases.items():shutil.copy2(p,R/f'public/cases/{name}.png')
    clips=[('home',0,29,20),('styles',29,58.031,20),('demo_input',58.031,97.031,39),('demo_wait',97.031,176.391,19.84),('demo_result',176.391,192.551,16.16),('card',192.551,219.391,25),('products',219.391,260.391,30),('scenes_ui',260.391,295.391,20)]
    source=V/'01_screen_recordings/continuous_browser.webm'
    for name,start,end,target in clips:
        output=R/f'public/media/{name}.mp4'
        if output.exists():continue
        args=[FF,'-hide_banner','-y','-ss',str(start),'-i',str(source),'-t',str(target),'-vf',f'setpts={target/(end-start):.9f}*(PTS-STARTPTS),fps=30,setsar=1','-an','-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p',str(output)]
        with (V/f'06_ffmpeg/{name}.log').open('w',encoding='utf-8') as log:result=subprocess.run(args,stdout=log,stderr=log)
        if result.returncode:raise RuntimeError('Clip preparation failed: '+name)
        print('Prepared real footage '+name,flush=True)
    (V/'03_voiceover/voice_timing.json').write_text(json.dumps(chapters,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
