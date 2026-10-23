"""Read-only real UI and Remotion Studio verification for the video task."""
from pathlib import Path
import json, os, urllib.request
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/'iCAN_应用方案/视频/08_review'
os.environ['TEMP']=os.environ['TMP']=str(ROOT/'.cache/temp')
with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=30) as r:
    health=json.load(r)
# Select public health fields; never serialize service credentials/configuration.
report={'healthStatus':health.get('status'),'generationProvider':health.get('generationProvider'),
        'localVisionAnalysis':health.get('localVisionAnalysis'),'pages':[]}
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1920,'height':1080},locale='zh-CN')
    for route,name in [('/','首页'),('/styles','风格库'),('/creator','智能生成'),('/products','文创转化'),('/scenarios','应用场景'),('/about','关于项目')]:
        response=page.goto('http://127.0.0.1:5173'+route,wait_until='networkidle')
        text=page.locator('body').inner_text()
        report['pages'].append({'page':name,'status':response.status,'projectNamePresent':'纹脉华章' in text,'textLength':len(text)})
        if route=='/about':page.screenshot(path=str(REVIEW/'real_about_verification.png'))
    page.goto('http://127.0.0.1:3001',wait_until='networkidle')
    page.wait_for_timeout(3000)
    report['studio']={'title':page.title(),'compositionListed':page.get_by_text('WenmaiICAN',exact=True).count()>0}
    page.screenshot(path=str(REVIEW/'remotion_studio_verification.png'))
    browser.close()
(REVIEW/'runtime_ui_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
