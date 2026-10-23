"""Keep the native Jianying export evidence and editable finish materials."""
from pathlib import Path
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / 'iCAN_应用方案' / '视频'
REVIEW = VIDEO / '08_review'
FINAL = VIDEO / '09_final' / '纹脉华章_2026_iCAN_演示视频.mp4'
DRAFT = VIDEO / '07_jianying' / 'JianyingPro Drafts' / '9月30日'
OPTIONAL = VIDEO / '07_jianying' / '精修素材'
OPTIONAL.mkdir(parents=True, exist_ok=True)

for source in [
    VIDEO / '03_voiceover' / '完整配音.wav',
    VIDEO / '03_voiceover' / '最终旁白.txt',
    VIDEO / '04_subtitles' / '字幕.srt',
    *[VIDEO / '02_generated_assets' / name for name in
      ['generated.png', 'CultureCard.png', 'bag.png', 'postcard.png']],
]:
    if not source.is_file():
        raise FileNotFoundError(source)
    shutil.copy2(source, OPTIONAL / source.name)

probe = json.loads(subprocess.run([
    r'D:\EV\EVCapture\ffprobe.exe', '-v', 'error', '-show_entries',
    'format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels',
    '-of', 'json', str(FINAL),
], capture_output=True, text=True, encoding='utf-8', check=True).stdout)
video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
audio = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
assert video['codec_name'] == 'h264' and video['width'] == 1920 and video['height'] == 1080
assert video['r_frame_rate'] == '30/1' and audio['codec_name'] == 'aac'
assert float(probe['format']['duration']) <= 285

report_path = REVIEW / 'jianying_environment_verification.json'
report = json.loads(report_path.read_text(encoding='utf-8'))
report.update({
    'ui_import_mp4': 'verified_native_editor_latest_ffmpeg_master_265s',
    'ui_import_png': 'verified_native_editor_generated_artwork',
    'ui_chinese': 'verified_native_editor_title_and_video_subtitles',
    'ui_keyframes': 'verified_native_scale_keyframe_at_100_percent',
    'ui_tts': 'voice_panel_loaded; free 解说小帅 and premium voices visible; no synthesis purchased or performed',
    'ui_captions': 'manual subtitles and SRT/LRC/ASS local import available; automatic recognition shows 1 monthly trial',
    'native_draft_title': '纹脉华章_iCAN_提交版精修',
    'native_draft_directory': str(DRAFT),
    'draft_location_set_via_normal_ui': True,
    'actual_new_draft_root': str(DRAFT.parent),
    'native_music_gain_db': -3.1,
    'native_main_scale_percent': 100,
    'native_export_completed': True,
    'native_export_path': str(FINAL),
    'native_export_ffprobe': probe,
    'membership_purchase': False,
    'cloud_upload_or_publish': False,
    'registry_modified': False,
    'appdata_modified_by_agent': False,
    'old_user_drafts_modified': False,
    'evidence': [
        'jianying_media_imported_0.png',
        'jianying_native_mix_keyframe_preview_2.png',
        'jianying_native_volume_corrected_2.png',
        'jianying_final_export_options_1.png',
        'jianying_native_export_after_wait_1.png',
        'jianying_native_manual_subtitle_options_2.png',
        'jianying_native_tts_loaded_2.png',
        'jianying_native_draft_final_restored_2.png',
    ],
})
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

(VIDEO / '07_jianying' / '剪映精修说明.md').write_text(f'''# 纹脉华章 iCAN 提交版精修

## 成片

`{FINAL}`

已从官方剪映专业版 11.5.3.14501 实际导出。265.010 秒，1920×1080，30 fps，H.264，AAC，双声道。

## 原生可编辑草稿

剪映首页的草稿标题：**纹脉华章_iCAN_提交版精修**。

原生草稿目录：`{DRAFT}`。

剪映正常重命名修改的是标题，当前版本保留创建日期文件夹名。不要在应用外直接改该文件夹名，以免草稿索引失效。

草稿位置已通过应用“全局设置”设到本项目 `07_jianying`，剪映自动创建 `JianyingPro Drafts` 子目录。

主视频引用 `06_ffmpeg/ffmpeg_master.mp4`，265 秒，内含已同步的旁白和字幕；独立音乐轨引用 `02_generated_assets/original_ambient.wav`，从零开始，音量 -3.1 dB（约原音量 0.7），尾部淡出在音乐素材内完成。

保持主视频原始尺寸，100% 缩放；原生关键帧验证没有改变镜头布局。文案朗读验证用的临时文本已经撤销，没有进入最终草稿或成片。

## 可选精修素材

`精修素材` 保存完整配音、旁白文本、SRT 和真实作品、CultureCard、帆布袋、明信片 PNG。

主轨字幕已烧录。若需要重新定位字幕，应先由保留的 Remotion 源项目重新渲染无字幕主轨，再通过剪映“字幕 → 新建字幕 → 导入本地字幕”导入 SRT，避免重复叠加。

剪映字幕识别面板显示本月试用一次；本地字幕导入可用。朗读音色面板能正常加载，显示免费与带会员标记的声音。没有购买会员，没有使用收费音色，没有订阅，也没有发布到社交平台。

本任务没有修改旧 AppData 用户草稿、注册表或其他项目。
''', encoding='utf-8')
print(json.dumps({'native_export': str(FINAL), 'native_draft': str(DRAFT), 'duration': probe['format']['duration']}, ensure_ascii=False))
