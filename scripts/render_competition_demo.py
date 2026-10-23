"""FFmpeg Video Editor skill workflow: inspect, trim/retime, subtitle, normalize, export."""
from pathlib import Path
import json, re, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'outputs/video/source'
sys.path.insert(0,str(ROOT/'.cache/publication_tools'))
import imageio_ffmpeg
FF=imageio_ffmpeg.get_ffmpeg_exe()
TIMELINE=json.loads((WORK/'recording_timeline.json').read_text(encoding='utf-8'))
TARGET=[29,29,39,37,43,41,35]

def run(args,logname):
    with (WORK/logname).open('w',encoding='utf-8') as log:
        p=subprocess.run([FF,'-hide_banner','-y',*args],cwd=WORK,stdout=log,stderr=log)
    if p.returncode:raise RuntimeError('Render failed; see '+str(WORK/logname))

def srt_time(s):
    ms=round(s*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'
def ass_time(s):
    cs=round(s*100);return f'{cs//360000}:{cs//6000%60:02d}:{cs//100%60:02d}.{cs%100:02d}'
def parse_time(s):
    h,m,rest=s.split(':');return int(h)*3600+int(m)*60+float(rest.replace(',','.'))
def subtitles(index):
    s=(WORK/f'voice_{index:02d}.srt').read_text(encoding='utf-8')
    output=[]
    for block in s.strip().split('\n\n'):
        lines=block.splitlines()
        if len(lines)<3:continue
        a,b=lines[1].split(' --> ');a,b=parse_time(a)+1.1,parse_time(b)+1.1
        text=''.join(lines[2:])
        # Each narrated sentence is proportionally divided into readable short cues.
        pieces=[];current=''
        for char in text:
            current+=char
            if (len(current)>=12 and char in '，。；：') or len(current)>=25:
                pieces.append(current);current=''
        if current:pieces.append(current)
        offset=0
        for piece in pieces:
            end=offset+len(piece)
            output.append((a+(b-a)*offset/len(text),a+(b-a)*end/len(text),piece))
            offset=end
    return output

HEADER='''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Subtitle,Microsoft YaHei,31,&H00FFFFFF,&H00FFFFFF,&H850B2024,&H850B2024,0,0,0,0,100,100,1,0,3,10,0,2,100,100,34,1
Style: Chapter,Microsoft YaHei,27,&H00564E16,&H00564E16,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,1,0,3,12,0,7,30,30,94,1
Style: Meta,Microsoft YaHei,19,&H00676767,&H00676767,&H00FFFFFF,&H00FFFFFF,0,0,0,0,100,100,0,0,3,8,0,7,30,30,155,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''

def main():
    inspect=subprocess.run([FF,'-hide_banner','-i',str(WORK/'continuous_browser.webm')],capture_output=True,text=True,encoding='utf-8',errors='replace')
    (WORK/'source_media_probe.txt').write_text(inspect.stderr,encoding='utf-8')
    all_cues=[];offset=0
    for i,mark in enumerate(TIMELINE):
        duration=TARGET[i];source_duration=mark['end']-mark['start']
        cues=subtitles(i)
        ass=HEADER+f'Dialogue: 1,0:00:00.50,{ass_time(duration-.6)},Chapter,,0,0,0,,{{\\fad(350,350)}}{i+1:02d}  {mark["title"].replace("，","\\N     ")}\n'
        meta='真实服务调用 · 等待时间已加速' if i==3 else '纹脉华章 · 实际操作演示'
        ass+=f'Dialogue: 1,0:00:01.00,{ass_time(duration-.7)},Meta,,0,0,0,,{{\\fad(350,350)}}{meta}\n'
        for a,b,text in cues:
            ass+=f'Dialogue: 2,{ass_time(a)},{ass_time(b)},Subtitle,,0,0,0,,{text}\n'
            all_cues.append((a+offset,b+offset,text))
        (WORK/f'chapter_{i:02d}.ass').write_text(ass,encoding='utf-8-sig')
        ratio=duration/source_duration
        vf=f'setpts={ratio:.9f}*(PTS-STARTPTS),fps=30,setsar=1'
        if i==0:vf+=',fade=t=in:d=0.6'
        if i==6:vf+=f',fade=t=out:st={duration-.75}:d=0.75'
        # Keep the continuous UI master without burned text for the editable JianYing draft.
        run(['-ss',str(mark['start']),'-i','continuous_browser.webm','-t',str(duration),'-vf',vf,'-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p',f'clean_{i:02d}.mp4'],f'clean_{i:02d}.log')
        run(['-i',f'clean_{i:02d}.mp4','-i',f'voice_{i:02d}.mp3','-t',str(duration),'-vf',f'ass=chapter_{i:02d}.ass','-af',f'adelay=1100:all=1,apad,loudnorm=I=-16:TP=-1.5:LRA=7','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-ac','2',f'chapter_{i:02d}.mp4'],f'chapter_{i:02d}.log')
        offset+=duration
        print(f'Rendered chapter {i+1}/7',flush=True)
    (WORK/'concat_final.txt').write_text('\n'.join(f"file 'chapter_{i:02d}.mp4'" for i in range(7)),encoding='utf-8')
    (WORK/'concat_clean.txt').write_text('\n'.join(f"file 'clean_{i:02d}.mp4'" for i in range(7)),encoding='utf-8')
    final=ROOT/'outputs/video/纹脉华章_比赛演示_1080p.mp4'
    run(['-f','concat','-safe','0','-i','concat_final.txt','-c','copy','-movflags','+faststart',str(final)],'final_concat.log')
    run(['-f','concat','-safe','0','-i','concat_clean.txt','-c','copy','-movflags','+faststart','edited_browser_clean.mp4'],'clean_concat.log')
    srt='\n\n'.join(f'{i+1}\n{srt_time(a)} --> {srt_time(b)}\n{text}' for i,(a,b,text) in enumerate(all_cues))+'\n'
    (ROOT/'outputs/video/纹脉华章_比赛演示.srt').write_text(srt,encoding='utf-8-sig')
    (WORK/'edit_manifest.json').write_text(json.dumps({'source':'continuous_browser.webm','method':'actual continuous browser recording, no screenshot slideshow','skills':['bryanwhl/ffmpeg-video-editor','luoluoluo22/jianying-editor-skill'],'resolution':[1920,1080],'fps':30,'duration':offset,'chapters':[{**m,'output_duration':TARGET[i]} for i,m in enumerate(TIMELINE)]},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Final video ready: '+str(final),flush=True)

if __name__=='__main__':main()
