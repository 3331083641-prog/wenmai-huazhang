"""Actual Edge UI acceptance for the integrated mascot, with isolated browser state."""
import json,os,time
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path(r'D:/wenmai-huazhang');OUT=R/'docs/mascot/v003-integration';OUT.mkdir(parents=True,exist_ok=True)
os.environ['TMP']=os.environ['TEMP']=r'D:/Codex/temp';Path(os.environ['TMP']).mkdir(exist_ok=True)
report={'checks':{},'errors':[],'warnings':[],'failedRequests':[]}
with sync_playwright() as pw:
 edge=r'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
 browser=pw.chromium.launch(executable_path=edge,headless=True,args=['--enable-webgl','--ignore-gpu-blocklist','--force-high-performance-gpu'])
 page=browser.new_page(viewport={'width':1280,'height':900},device_scale_factor=1)
 page.on('pageerror',lambda e:report['errors'].append(str(e)))
 page.on('console',lambda m:report['errors' if m.type=='error' else 'warnings'].append(m.text) if m.type in ['error','warning'] else None)
 page.on('requestfailed',lambda r:report['failedRequests'].append({'url':r.url,'failure':r.failure}))
 try:
  page.goto('http://127.0.0.1:5173/heritage-gallery',wait_until='networkidle',timeout=120000)
  page.get_by_role('button',name='探索模式',exact=True).click()
  page.get_by_test_id('mascot-wake').click()
  page.wait_for_function('window.__wenwenModel?.clips.length===8 && window.__mascot?.phase==="ready"',timeout=120000)
  report['model']=page.evaluate('({url:window.__wenwenModel.url,clips:window.__wenwenModel.clips,scale:window.__wenwenModel.scale,offsetY:window.__wenwenModel.offsetY})')
  report['webgl']=page.evaluate("()=>{const gl=document.querySelector('canvas').getContext('webgl2');const ext=gl.getExtension('WEBGL_debug_renderer_info');return {renderer:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):null,maxTexture:gl.getParameter(gl.MAX_TEXTURE_SIZE)}}")
  report['checks']['spawn']=page.evaluate('window.__mascot')
  pose=page.evaluate('window.__wenwenModel.samplePose()');page.wait_for_timeout(500);pose2=page.evaluate('window.__wenwenModel.samplePose()')
  assert pose!=pose2,'Idle bones do not animate'
  report['checks']['idleAnimated']=True
  page.screenshot(path=str(OUT/'gallery-third-person.png'))
  # Safe interior aisle: normal keyboard motion; no teleport for movement tests.
  page.evaluate('window.__mascotDebug.teleport(-1.2,1.2,Math.PI)');page.wait_for_timeout(150)
  before=page.evaluate('window.__mascot.position');page.keyboard.down('w');page.wait_for_function('window.__mascot.action==="walk"');page.wait_for_timeout(180)
  report['checks']['walk']=page.evaluate('window.__mascot');page.keyboard.up('w')
  assert report['checks']['walk']['action']=='walk' and before!=report['checks']['walk']['position']
  page.evaluate('window.__mascotDebug.teleport(-1.2,1.2,Math.PI)')
  page.keyboard.down('Shift');page.keyboard.down('w');page.wait_for_function('window.__mascot.action==="run"',timeout=4000)
  report['checks']['run']=page.evaluate('window.__mascot');page.keyboard.up('w');page.keyboard.up('Shift')
  assert report['checks']['run']['action']=='run' and report['checks']['run']['speed']>1.9
  page.wait_for_function('window.__mascot.speed===0',timeout=4000)
  page.keyboard.down('a');page.wait_for_function('window.__mascot.action==="turn"',timeout=4000);report['checks']['turn']=page.evaluate('window.__mascot');page.keyboard.up('a')
  assert report['checks']['turn']['action']=='turn'
  page.keyboard.press('v');page.wait_for_timeout(500);report['checks']['firstPerson']=page.evaluate('window.__mascot');assert report['checks']['firstPerson']['view']=='first'
  page.screenshot(path=str(OUT/'gallery-first-person.png'));page.keyboard.press('v');page.wait_for_timeout(400)
  page.keyboard.press('Space');page.wait_for_timeout(180);report['checks']['happy']=page.evaluate('window.__mascot');assert report['checks']['happy']['action']=='happy'
  page.wait_for_timeout(1200)
  # Place at the actual stair entrances, then use ordinary W to traverse each run.
  page.evaluate('window.__mascotDebug.teleport(.35,3.4,-Math.PI/2,.28)');page.wait_for_timeout(120)
  page.keyboard.down('w');page.wait_for_function('window.__mascot.position[1]>1.9',timeout=20000);page.keyboard.up('w');page.wait_for_timeout(200)
  report['checks']['stairA']=page.evaluate('window.__mascot');assert report['checks']['stairA']['position'][1]>1.7
  page.evaluate('window.__mascotDebug.teleport(2.85,2.31,Math.PI/2,2.01)');page.wait_for_timeout(120)
  page.keyboard.down('w');page.wait_for_function('window.__mascot.position[1]>=3.59',timeout=20000);page.keyboard.up('w');page.wait_for_timeout(200)
  report['checks']['stairB']=page.evaluate('window.__mascot');assert report['checks']['stairB']['floor']==2
  page.screenshot(path=str(OUT/'gallery-upstairs.png'))
  page.evaluate('window.__mascotDebug.teleport(.62,2.31,-Math.PI/2,3.55)');page.wait_for_timeout(120)
  page.keyboard.down('w');page.wait_for_function('window.__mascot.position[1]<2.05',timeout=20000);page.keyboard.up('w');page.wait_for_timeout(200)
  report['checks']['stairDown']=page.evaluate('window.__mascot');assert report['checks']['stairDown']['position'][1]<2.3
  page.evaluate('window.__mascotDebug.teleport(3.2,3.4,Math.PI/2,1.98)');page.wait_for_timeout(120)
  page.keyboard.down('w');page.wait_for_function('window.__mascot.position[1]<.30',timeout=20000);page.keyboard.up('w');page.wait_for_timeout(200)
  report['checks']['stairDownA']=page.evaluate('window.__mascot');assert abs(report['checks']['stairDownA']['position'][1]-.25)<.08
  page.evaluate('window.__mascotDebug.teleport(-1.2,3.0,Math.PI,.25)');page.wait_for_timeout(300)
  assert page.evaluate('window.__mascot.nearestFrame')
  page.keyboard.press('e');page.wait_for_timeout(150);report['checks']['exhibit']=page.evaluate('window.__mascot');assert report['checks']['exhibit']['action']=='interact'
  assert page.get_by_text('视觉特征',exact=True).count()>0
  page.screenshot(path=str(OUT/'gallery-exhibit.png'))
  page.keyboard.press('Escape');page.wait_for_timeout(300);assert page.get_by_test_id('mascot-hud').count()==0;report['checks']['exit']=True
  page.get_by_role('button',name='探索模式',exact=True).click();page.get_by_test_id('mascot-wake').click();page.wait_for_function('window.__mascot?.phase==="ready"',timeout=20000);report['checks']['respawn']=True
  page.screenshot(path=str(OUT/'gallery-respawn.png'))
  assert not report['errors'],report['errors']
  assert not any('CONTEXT_LOST' in w or 'OUT_OF_MEMORY' in w for w in report['warnings']),report['warnings']
  report['status']='pass'
 except Exception as e:
  report['status']='fail';report['failure']=str(e);page.screenshot(path=str(OUT/'gallery-failure.png'))
 finally:
  (OUT/'ui-test.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');browser.close()
print(json.dumps({'status':report['status'],'failure':report.get('failure'),'checks':list(report['checks'])}))
if report['status']!='pass':raise SystemExit(1)
