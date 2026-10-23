from pathlib import Path
import json,shutil,sys,subprocess,os
ROOT=Path(__file__).resolve().parents[1]
VIDEO=ROOT/'iCAN_应用方案/视频'
for name in ['00_video_plan','01_screen_recordings','02_generated_assets','03_voiceover','04_subtitles','05_remotion','06_ffmpeg','07_jianying','08_review','09_final']:(VIDEO/name).mkdir(parents=True,exist_ok=True)
source=ROOT/'outputs/video/source'
for name in ['continuous_browser.webm','recording_timeline.json','generation_evidence.json']:
    shutil.copy2(source/name,VIDEO/'01_screen_recordings'/name)
for name in ['generated.png','CultureCard.png','postcard.png','bag.png']:
    shutil.copy2(source/name,VIDEO/'02_generated_assets'/name)
project=VIDEO/'05_remotion'
for d in ['src','public/media','public/cases','public/voice','public/data']:(project/d).mkdir(parents=True,exist_ok=True)
(project/'package.json').write_text(json.dumps({'name':'wenmai-huazhang-ican-video','version':'1.0.0','private':True,'type':'module','scripts':{'studio':'remotion studio src/index.tsx','render':'node render.mjs','review':'node render.mjs --stills'},'dependencies':{'remotion':'4.0.530','@remotion/cli':'4.0.530','@remotion/renderer':'4.0.530','@remotion/bundler':'4.0.530','@remotion/captions':'4.0.530','react':'19.0.0','react-dom':'19.0.0'},'devDependencies':{'typescript':'~5.8.2','@types/react':'^19.0.0'}},indent=2),encoding='utf-8')
audit={'os':'Windows 11 Home Chinese, build 26200, x64','disk_free_GB':128.9,'node':'24.15.0','npm':'11.12.1','npx':'11.12.1','powershell_note':'Use npm.cmd/npx.cmd; no execution policy change','git':'2.54.0.windows.1','ffmpeg':'7.1 bundled with imageio-ffmpeg in project cache','ffprobe':'existing D:/EV/EVCapture/ffprobe.exe','skills_root':'D:/Codex/.codex/skills','existing_video_skills':['ffmpeg-video-editor','jianying-editor'],'plugins':{'Scientific Illustrator':'enabled','Sivia':'disabled'},'global_configuration_modified':False}
(VIDEO/'08_review/environment_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print('Video workspace ready')
