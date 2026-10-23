"""Replace reviewed intervals with exact frame counts, then remaster true voice."""
from pathlib import Path
import subprocess,json,sys
ROOT=Path(__file__).resolve().parents[1]
V=ROOT/'iCAN_应用方案/视频'
sys.path.insert(0,str(ROOT/'.cache/publication_tools'))
import imageio_ffmpeg
FF=imageio_ffmpeg.get_ffmpeg_exe()
PROBE=str(V/'05_remotion/node_modules/@remotion/compositor-win32-x64-msvc/ffprobe.exe')
parts=[('remotion_master',7950),('core_patch',2258),('experiment_patch',900),('ending_patch',1208)]
args=[FF,'-hide_banner','-y']
for name,expected in parts:
    p=V/f'06_ffmpeg/{name}.mp4'
    data=json.loads(subprocess.check_output([PROBE,'-v','error','-show_streams','-of','json',str(p)]))
    actual=int(next(s for s in data['streams'] if s['codec_type']=='video')['nb_frames'])
    assert actual==expected,(name,actual,expected)
    args+=['-i',str(p)]
filters='[0:v]split=3[first][middle][last];[first]trim=start_frame=0:end_frame=1650,setpts=PTS-STARTPTS[v0];[1:v]setpts=PTS-STARTPTS[v1];[2:v]setpts=PTS-STARTPTS[v2];[middle]trim=start_frame=4808:end_frame=6450,setpts=PTS-STARTPTS[v3];[3:v]setpts=PTS-STARTPTS[v4];[last]trim=start_frame=7658:end_frame=7950,setpts=PTS-STARTPTS[v5];[v0][v1][v2][v3][v4][v5]concat=n=6:v=1:a=0[v]'
args+=['-filter_complex',filters,'-map','[v]','-an','-r','30','-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart',str(V/'06_ffmpeg/remotion_reviewed.mp4')]
with (V/'06_ffmpeg/reviewed_assembly.log').open('w',encoding='utf-8') as log:subprocess.run(args,stdout=log,stderr=log,check=True)
chapters=json.loads((V/'03_voiceover/旁白章节.json').read_text(encoding='utf-8'))
(V/'03_voiceover/最终旁白.txt').write_text('\n\n'.join(c['text'] for c in chapters)+'\n',encoding='utf-8')
subprocess.run([sys.executable,str(ROOT/'scripts/master_formal_voice.py')],check=True)
print('Reviewed 7950-frame picture and synchronized narration ready',flush=True)
