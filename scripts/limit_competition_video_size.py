"""Keep the reviewed Jianying picture/audio within the user's 200 MB limit."""
from pathlib import Path
import json,subprocess,sys,shutil
ROOT=Path(__file__).resolve().parents[1];V=ROOT/'iCAN_应用方案/视频'
sys.path.insert(0,str(ROOT/'.cache/publication_tools'))
import imageio_ffmpeg
FF=imageio_ffmpeg.get_ffmpeg_exe()
source=V/'09_final/纹脉华章_2026_iCAN_演示视频.mp4'
if source.stat().st_mtime<(V/'06_ffmpeg/ffmpeg_master.mp4').stat().st_mtime:raise RuntimeError('Final native export is older than revised master')
if source.stat().st_size>=200_000_000:
    native=V/'07_jianying/精修原生导出.mp4'
    shutil.copy2(source,native)
    temp=V/'06_ffmpeg/submission_under_200mb.mp4'
    args=[FF,'-hide_banner','-y','-i',str(native),'-map','0:v:0','-map','0:a:0','-c:v','libx264','-preset','medium','-crf','18','-maxrate','5M','-bufsize','10M','-pix_fmt','yuv420p','-r','30','-c:a','aac','-b:a','192k','-movflags','+faststart',str(temp)]
    with (V/'06_ffmpeg/size_limit_export.log').open('w') as log:subprocess.run(args,stdout=log,stderr=log,check=True)
    if temp.stat().st_size>=200_000_000:raise RuntimeError('Size bound exceeded')
    shutil.copy2(temp,source)
assert source.stat().st_size<200_000_000
(V/'08_review/final_size_limit.json').write_text(json.dumps({'file':str(source),'bytes':source.stat().st_size,'limitBytes':200_000_000,'passed':True},ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Final export: {source.stat().st_size/1_000_000:.2f} MB, under 200 MB')
