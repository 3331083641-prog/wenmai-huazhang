"""Complete real-time playback twice, media integrity and format verification."""
from pathlib import Path
import json, os, subprocess, threading, time, sys, hashlib
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
V=ROOT/'iCAN_应用方案/视频'
FINAL=V/'09_final/纹脉华章_2026_iCAN_演示视频.mp4'
REVIEW=V/'08_review'
BIN=V/'05_remotion/node_modules/@remotion/compositor-win32-x64-msvc'
os.environ['TEMP']=os.environ['TMP']=str(ROOT/'.cache/temp')
sys.path.insert(0,str(ROOT/'.cache/publication_tools'))
import imageio_ffmpeg
FF=imageio_ffmpeg.get_ffmpeg_exe();PROBE=str(BIN/'ffprobe.exe')
metadata=json.loads(subprocess.check_output([PROBE,'-v','error','-show_streams','-show_format','-of','json',str(FINAL)],text=True,encoding='utf-8'))
video=next(s for s in metadata['streams'] if s['codec_type']=='video')
audio=next(s for s in metadata['streams'] if s['codec_type']=='audio')
assert video['codec_name']=='h264' and audio['codec_name']=='aac'
assert (video['width'],video['height'])==(1920,1080)
assert video['avg_frame_rate']=='30/1'
assert 255<=float(metadata['format']['duration'])<=275
report={'metadata':metadata,'playbacks':[],'file':str(FINAL),'sha256':hashlib.sha256(FINAL.read_bytes()).hexdigest()}
if '--resume' in sys.argv:
    previous=json.loads((REVIEW/'final_video_verification.json').read_text(encoding='utf-8'))
    if previous.get('sha256')!=report['sha256']:
        raise RuntimeError('Cannot resume playback review for a different export')
    report['playbacks']=previous.get('playbacks',[])
    if len(report['playbacks'])>=2:raise SystemExit('Two complete playbacks already verified for this exact export')
with (REVIEW/'final_decode.log').open('w',encoding='utf-8') as log:
    decode=subprocess.run([FF,'-hide_banner','-v','error','-i',str(FINAL),'-f','null','-'],stdout=log,stderr=log)
assert decode.returncode==0
report['completeDecode']='passed'
analysis=subprocess.run([FF,'-hide_banner','-i',str(FINAL),'-vf','blackdetect=d=0.08:pix_th=0.10','-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True,encoding='utf-8',errors='replace')
(REVIEW/'final_black_loudness.log').write_text(analysis.stderr,encoding='utf-8')
report['blackIntervals']=[line for line in analysis.stderr.splitlines() if 'black_start:' in line]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
class QuietServer(ThreadingHTTPServer):
    def handle_error(self,request,client_address):
        if isinstance(sys.exception(),ConnectionResetError):return
        super().handle_error(request,client_address)
server=QuietServer(('127.0.0.1',0),partial(QuietHandler,directory=str(FINAL.parent)))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True,args=['--autoplay-policy=no-user-gesture-required'])
        page=browser.new_page(viewport={'width':1920,'height':1080})
        url=f'http://127.0.0.1:{server.server_port}/'+FINAL.name
        page.goto(url,wait_until='domcontentloaded')
        page.evaluate("""()=>{const v=document.querySelector('video');v.style.cssText='width:100vw;height:100vh;object-fit:contain';document.body.style.cssText='margin:0;background:#faf7f0';window.reviewEvents=[];['error','waiting','stalled'].forEach(t=>v.addEventListener(t,()=>window.reviewEvents.push({event:t,time:v.currentTime})));}""")
        page.wait_for_function('document.querySelector("video").readyState>=2')
        for run in range(len(report['playbacks'])+1,3):
            started=time.monotonic();page.evaluate("""async()=>{const v=document.querySelector('video');v.currentTime=0;v.playbackRate=1;v.muted=false;await v.play();}""")
            recorded=set()
            while not page.evaluate('document.querySelector("video").ended'):
                current=page.evaluate('document.querySelector("video").currentTime')
                for sample in (6,24,41,64,104,123,137,148,157,172,197,227,247,260):
                    if current>=sample and sample not in recorded:
                        page.screenshot(path=str(REVIEW/f'playback_{run}_{sample:03d}s.png'))
                        recorded.add(sample)
                if time.monotonic()-started>330:raise RuntimeError('Real-time playback failed to finish')
                page.wait_for_timeout(1000)
            quality=page.evaluate("""()=>{const v=document.querySelector('video');const q=v.getVideoPlaybackQuality();return {endTime:v.currentTime,duration:v.duration,rate:v.playbackRate,error:v.error?{code:v.error.code}:null,totalFrames:q.totalVideoFrames,droppedFrames:q.droppedVideoFrames,events:window.reviewEvents}}""")
            quality['elapsedSeconds']=round(time.monotonic()-started,2)
            report['playbacks'].append(quality)
            (REVIEW/'final_video_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(f'Playback {run}/2 complete: {quality["endTime"]:.3f}s',flush=True)
        browser.close()
finally:
    server.shutdown();server.server_close()
print('Verified 1080p / 30fps / H.264 / AAC and two complete real-time playbacks',flush=True)
