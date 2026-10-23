from pathlib import Path
import json,subprocess,sys,shutil
ROOT=Path(__file__).resolve().parents[1]
V=ROOT/'iCAN_应用方案/视频';R=V/'05_remotion';S=V/'01_screen_recordings/revision'
sys.path.insert(0,str(ROOT/'.cache/publication_tools'))
import imageio_ffmpeg
FF=imageio_ffmpeg.get_ffmpeg_exe()
marks=json.loads((S/'recording_timeline.json').read_text(encoding='utf-8'))
start=marks[2]['start'];wait=marks[3]['start'];result=marks[4]['start'];products=marks[5]['start'];end=marks[6]['start']
wait_duration=(result-wait)/8
result_duration=75-39-wait_duration
if result_duration<8:raise RuntimeError('Wait exceeds video slot at authorized 8x speed')
segments=[('demo_input',start,wait,39),('demo_wait',wait,result,wait_duration),('demo_result',result,result+result_duration,result_duration),('card',result+result_duration,products,25),('products',products,end,30)]
for name,a,b,target in segments:
    log=V/f'06_ffmpeg/revision_{name}.log'
    # trim the source interval before altering timestamps, then pad only fractional frame tail
    args=[FF,'-hide_banner','-y','-i',str(S/'continuous_browser.webm'),'-vf',f'trim=start={a}:end={b},setpts={target/(b-a)}*(PTS-STARTPTS),fps=30,setsar=1,tpad=stop_mode=clone:stop_duration=0.1','-t',str(target),'-an','-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p',str(R/f'public/media/{name}.mp4')]
    with log.open('w') as out:subprocess.run(args,stdout=out,stderr=out,check=True)
    print(f'Real {name}: {target:.2f}s',flush=True)
for name in ['generated.png','CultureCard.png','postcard.png','bag.png']:
    shutil.copy2(S/name,V/'02_generated_assets'/name)
frames=round(wait_duration*30)
(V/'00_video_plan/revision_timing.json').write_text(json.dumps({'inputFrames':1170,'waitFrames':frames,'resultFrames':2258-1170-frames,'waitSpeed':8,'recordingSource':str(S/'continuous_browser.webm')},indent=2),encoding='utf-8')
text=(R/'src/Demo.tsx').read_text(encoding='utf-8')
text=text.replace('durationInFrames={595}',f'durationInFrames={{{frames}}}').replace('from={1765}',f'from={{{1170+frames}}}').replace('durationInFrames={493}',f'durationInFrames={{{2258-1170-frames}}}').replace('4倍速','8倍速').replace('实际等待 ×4','实际等待 ×8')
(R/'src/Demo.tsx').write_text(text,encoding='utf-8')
ch=json.loads((V/'03_voiceover/旁白章节.json').read_text(encoding='utf-8'))
for key in ['text','speechText']:
    ch[3][key]=ch[3][key].replace('已有山水作品作为参考','你提供的楼阁图作为参考')
    ch[4][key]=ch[4][key].replace('左右滑动比较有无用户排除词','完整并列比较有无用户排除词')
(V/'03_voiceover/旁白章节.json').write_text(json.dumps(ch,ensure_ascii=False,indent=2),encoding='utf-8')
for i in [3,4]:
    p=V/f'03_voiceover/voice_{i:02d}.mp3'
    if p.exists():p.rename(ROOT/f'.cache/video_source_backup/revision_2230/voice_{i:02d}.mp3')
print('Revised footage and narration configuration ready',flush=True)
