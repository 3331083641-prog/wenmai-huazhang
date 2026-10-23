"""Build a self-contained refinement draft without touching existing app drafts.

The baked master already contains narration and captions. Optional source assets
are registered as materials and copied beside the draft, not played twice.
"""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
VIDEO=ROOT/'iCAN_应用方案'/'视频'
SKILL=Path(os.environ.get('JY_SKILL_ROOT',r'D:\Codex\.codex\skills\jianying-editor'))
sys.stdout.reconfigure(encoding='utf-8')
sys.path[:0]=[str(ROOT/'.cache'/'publication_tools'),str(SKILL/'scripts')]
os.environ['JY_SKILL_ROOT']=str(SKILL)
# Process-local tooling paths; no global PATH or app configuration changes.
os.environ['PATH']=r'D:\EV\EVCapture'+os.pathsep+os.environ.get('PATH','')
from jy_wrapper import JyProject
import pyJianYingDraft as draft

def verify_scope(path):
    resolved=Path(path).resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError(f'Project path outside allowed root: {resolved}')
    return resolved

def make_draft(master, name):
    master=verify_scope(master)
    if not master.is_file():
        raise FileNotFoundError(f'Wait for completed master render: {master}')
    probe=subprocess.run([r'D:\EV\EVCapture\ffprobe.exe','-v','error','-show_streams','-show_format','-of','json',str(master)],capture_output=True,text=True,encoding='utf-8',check=True)
    info=json.loads(probe.stdout)
    stream=next(s for s in info['streams'] if s.get('codec_type')=='video')
    duration_us=round(float(info['format']['duration'])*1_000_000)
    assert stream['width']==1920 and stream['height']==1080
    assert stream['codec_name']=='h264'
    assert duration_us<=285_000_000
    root=verify_scope(VIDEO/'07_jianying'/'JianyingPro Drafts')
    root.mkdir(parents=True,exist_ok=True)
    target=verify_scope(root/name)
    if target.exists():
        raise FileExistsError(f'Existing draft preserved: {target}')
    project=JyProject(name,width=1920,height=1080,drafts_root=str(root),overwrite=False)
    segment=project.add_media_safe(str(master),start_time=0,duration=duration_us,track_name='正式成片主轨')
    if segment is None:
        raise RuntimeError('Main MP4 could not be registered')
    # Keep framing unchanged, while preserving an editable native keyframe pair.
    # This API uses segment-relative offsets in microseconds.
    segment.add_keyframe(draft.KeyframeProperty.uniform_scale,0,1.0)
    segment.add_keyframe(draft.KeyframeProperty.uniform_scale,max(0,duration_us-33_333),1.0)
    if duration_us<30_000_000:
        project.add_text_simple('纹脉华章 · 中文字幕验证',start_time=0,duration=2_000_000,track_name='中文显示验证')
    music=VIDEO/'02_generated_assets'/'original_ambient.wav'
    if music.is_file() and duration_us>200_000_000:
        music_segment=project.add_media_safe(str(music),start_time=0,duration=duration_us,track_name='原创轻配乐')
        if music_segment is None:
            raise RuntimeError('Original ambient music could not be registered')
        music_segment.volume=0.7
    optional=target/'可选精修素材'
    optional.mkdir()
    copies=[]
    sources=list((VIDEO/'03_voiceover').glob('voice_*.mp3'))
    sources.extend([VIDEO/'03_voiceover'/'最终旁白.txt',VIDEO/'04_subtitles'/'字幕.srt'])
    sources.extend([VIDEO/'02_generated_assets'/f for f in ['generated.png','CultureCard.png','bag.png','postcard.png']])
    for source in sources:
        if not source.is_file():
            continue
        copy=optional/source.name
        shutil.copy2(source,copy)
        copies.append(str(copy))
        if copy.suffix.lower()=='.png':
            project.script.add_material(draft.VideoMaterial(str(copy)))
        elif copy.suffix.lower()=='.mp3':
            project.script.add_material(draft.AudioMaterial(str(copy)))
    project.save()
    # Fill only this new draft's own metadata using the wrapper's template schema.
    meta_path=target/'draft_meta_info.json'
    meta=json.loads(meta_path.read_text(encoding='utf-8'))
    meta.update(draft_name=name,draft_id=str(uuid.uuid4()).upper(),draft_fold_path=str(target),draft_root_path=str(root),tm_duration=duration_us,tm_draft_modified=int(time.time()*1_000_000))
    meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    readme='''# 纹脉华章 iCAN 最终精修草稿\n\n主轨是程序化成片，已包含AI中文配音及完整字幕，避免再次叠加同一旁白/字幕。原创轻配乐为独立音轨，默认音量0.7，源文件已采用低响度并在结尾淡出。\n\n可选精修素材内提供SRT、逐段旁白、作品、CultureCard和文创效果PNG；已注册图像和声音素材，但未加入播放轨。\n\n画面关键帧保持缩放1.0，不改变原成片内容，可在剪映中微调。\n\n草稿文件全部位于本项目D盘目录，没有更改现有AppData草稿。请通过剪映正常的本地草稿导入功能打开本文件夹；当前版本实际打开与最终导出仍需界面验证。\n'''
    (target/'精修说明.md').write_text(readme,encoding='utf-8')
    content=json.loads((target/'draft_info.json').read_text(encoding='utf-8'))
    tracks=content.get('tracks',[])
    videos=[t for t in tracks if t.get('type')=='video']
    assert len(videos)==1 and len(videos[0].get('segments',[]))==1
    keyframes=videos[0]['segments'][0].get('common_keyframes',[])
    assert keyframes
    referenced=[m['path'] for kind in ['videos','audios'] for m in content['materials'].get(kind,[]) if m.get('path')]
    assert all(Path(p).exists() and Path(p).resolve().is_relative_to(target) for p in referenced)
    report={'draft':str(target),'master':str(master),'duration_seconds':duration_us/1_000_000,'main_video_tracks':len(videos),'main_segments':1,'native_keyframe_lists':len(keyframes),'audio_tracks':[t.get('name') for t in tracks if t.get('type')=='audio'],'optional_material_files':len(copies),'all_references_self_contained':True,'appdata_modified':False,'native_open_verified':False,'narration_or_captions_duplicated':False}
    report_name='jianying_environment_draft_structure.json' if duration_us<30_000_000 else 'jianying_draft_structure.json'
    (VIDEO/'08_review'/report_name).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--video',type=Path,default=VIDEO/'06_ffmpeg'/'remotion_master.mp4')
    p.add_argument('--name',default='纹脉华章_iCAN_最终精修')
    a=p.parse_args()
    make_draft(a.video,a.name)
