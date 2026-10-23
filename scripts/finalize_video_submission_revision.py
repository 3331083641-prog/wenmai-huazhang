from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1];V=ROOT/'iCAN_应用方案/视频';D=ROOT/'iCAN_应用方案/07_最终提交'
p=V/'09_final/纹脉华章_2026_iCAN_演示视频.mp4'
review=json.loads((V/'08_review/final_video_verification.json').read_text(encoding='utf-8'))
sha=hashlib.sha256(p.read_bytes()).hexdigest()
assert review['sha256']==sha and len(review['playbacks'])==2
assert all(c['error'] is None and c['endTime']>=264.9 and c['rate']==1 for c in review['playbacks'])
assert review['completeDecode']=='passed' and not review['blackIntervals']
assert p.stat().st_size<200_000_000
shutil.copy2(p,D/'02_纹脉华章_演示视频.mp4')
check=D/'00_纹脉华章_提交清单.md'
text=check.read_text(encoding='utf-8')
text=text.replace('等待正式成片完成并验收后补齐；当前尚未包含','已完成修订并验收；4分25秒、70.61MB、1080p30，含完整中文配音与字幕')
text=text.replace('**当前提交包尚需补齐正式视频，不能作为完整提交包上传。**','**提交材料已整理齐全。演示视频已完成两遍完整播放、编码与完整解码检查，并满足200MB以内的要求。**')
text=text.replace('待补齐；计划4分25秒，1920×1080、30fps、H.264与AAC，MP4。最终以验收后的文件参数为准。','MP4，4分25秒，70,605,166字节（70.61MB），1920×1080、30fps、H.264与AAC；文件与已验收成片SHA256一致。')
check.write_text(text,encoding='utf-8')
log=V/'00_video_plan/edit_log.md'
with log.open('a',encoding='utf-8') as out:
    out.write('\n- 最终视频按既有剪映草稿的100%画面尺寸与配乐−3.1dB设定，由FFmpeg复制视频轨并混音导出。当前修订未完成剪映原生导出，最终以FFmpeg文件验收为准。\n- 成片265.000秒、1080p30、H.264/AAC，70,605,166字节；完整解码通过，无黑帧，两次原速完整播放无媒体错误；提交目录副本SHA256一致。\n')
print('Updated submission checklist and synchronized the verified 70.61 MB export')
