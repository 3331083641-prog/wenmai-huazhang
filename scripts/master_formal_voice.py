"""Align the actual TTS tracks to the subtitle timeline, then master narration."""
from pathlib import Path
import json,subprocess,re,sys
ROOT=Path(__file__).resolve().parents[1]
V=ROOT/'iCAN_应用方案/视频'
sys.path.insert(0,str(ROOT/'.cache/publication_tools'))
import imageio_ffmpeg
FF=imageio_ffmpeg.get_ffmpeg_exe()
chapters=json.loads((V/'03_voiceover/旁白章节.json').read_text(encoding='utf-8'))
voice=V/'03_voiceover/完整配音.wav'
args=[FF,'-hide_banner','-y']
for c in chapters:args+=['-i',str(V/f'03_voiceover/voice_{c["id"]:02d}.mp3')]
filters=[]
for i,c in enumerate(chapters):
    delay=round((c['startSeconds']+.5)*1000)
    filters.append(f'[{i}:a]adelay={delay}:all=1[a{i}]')
filters.append(''.join(f'[a{i}]' for i in range(10))+'amix=inputs=10:duration=longest:normalize=0,apad=whole_dur=265,atrim=duration=265[a]')
args+=['-filter_complex',';'.join(filters),'-map','[a]','-ar','48000','-ac','2','-c:a','pcm_s16le',str(voice)]
with (V/'06_ffmpeg/voice_alignment.log').open('w',encoding='utf-8') as log:subprocess.run(args,stdout=log,stderr=log,check=True)
measure=subprocess.run([FF,'-hide_banner','-i',str(voice),'-af','loudnorm=I=-18:TP=-2:LRA=7:print_format=json','-f','null','-'],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True)
data=json.loads(re.search(r'\{\s*"input_i".*?\}',measure.stderr,re.S).group())
(V/'08_review/aligned_voice_loudness.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
af=f'loudnorm=I=-18:TP=-2:LRA=7:measured_I={data["input_i"]}:measured_TP={data["input_tp"]}:measured_LRA={data["input_lra"]}:measured_thresh={data["input_thresh"]}:offset={data["target_offset"]}:linear=true'
picture=V/'06_ffmpeg/remotion_master.mp4'
args=[FF,'-hide_banner','-y','-i',str(picture),'-i',str(voice),'-map','0:v','-map','1:a','-t','265','-c:v','copy','-af',af,'-ar','48000','-c:a','aac','-b:a','192k','-movflags','+faststart',str(V/'06_ffmpeg/ffmpeg_master.mp4')]
with (V/'06_ffmpeg/master_normalize.log').open('w',encoding='utf-8') as log:subprocess.run(args,stdout=log,stderr=log,check=True)
print('Narration aligned at chapter start + 0.5 seconds; FFmpeg master complete',flush=True)
