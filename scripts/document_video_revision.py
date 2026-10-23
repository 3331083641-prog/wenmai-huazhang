from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];V=ROOT/'iCAN_应用方案/视频'
plan=V/'00_video_plan/video_plan.md'
s=plan.read_text(encoding='utf-8')
s=s.replace('实际录屏58.031—192.551秒段：39秒普通操作、79.36秒等待4倍加速为19.84秒、16.16秒实际结果','新实录：39秒普通操作、193.828秒实际等待8倍加速为24.229秒、11.771秒实际结果')
s=s.replace('有/无用户排除词滑动遮罩','有/无用户排除词完整并列与文字焦点框')
s=s.replace('实际录屏192.551—219.391秒段','新实录302.771—334秒段').replace('实际录屏219.391—260.391秒段','新实录334—375.016秒段')
s=s.replace('`outputs/video/source/continuous_browser.webm`，总长295.391秒','`01_screen_recordings/revision/continuous_browser.webm`，总长410.016秒')
s=s.replace('`outputs/video/source/generation_evidence.json`','`01_screen_recordings/revision/generation_evidence.json`')
s=s.replace('65是五风格正式验收案例','65与90是本次按用户要求新生成的真实案例')
s=s.replace('有/无参考图比较以65基准为无参考，以剪纸作品输入汴绣创作的案例为有参考','有/无参考图比较以本次新65基准为无参考，以项目已有汴绣牡丹花鸟素材输入汴绣创作的新案例为有参考')
plan.write_text(s,encoding='utf-8')
entries=[]
paths={'strength30':ROOT/'iCAN_应用方案/08_对照实验/风格强度/30_汴绣_低强度/generated.png','strength65':V/'02_generated_assets/revision/strength/65/generated.png','strength90':V/'02_generated_assets/revision/strength/90/generated.png','referenceInput':ROOT/'backend/style_refs/bianxiu.png','referenceNo':V/'02_generated_assets/revision/strength/65/generated.png','referenceYes':V/'02_generated_assets/revision/bianxiu_reference/generated.png','negativeNo':ROOT/'iCAN_应用方案/08_对照实验/负向提示词/A_未填写用户排除词/generated.png','negativeYes':ROOT/'iCAN_应用方案/05_生成案例/正式验收_20260929/02_汴绣/generated.png','towerReference':V/'02_generated_assets/revision/tower_reference.png','mainGenerated':V/'01_screen_recordings/revision/generated.png'}
for name,p in paths.items():entries.append({'name':name,'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(V/'08_review/revision_asset_provenance.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
chapters=json.loads((V/'03_voiceover/旁白章节.json').read_text(encoding='utf-8'))
(V/'03_voiceover/最终旁白.txt').write_text('\n\n'.join(c['text'] for c in chapters)+'\n',encoding='utf-8')
print('Updated plan, narration and image provenance')
