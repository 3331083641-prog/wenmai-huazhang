from pathlib import Path
import os,json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(r'D:\JianyingPro\installer');OUT.mkdir(parents=True,exist_ok=True)
os.environ['TEMP']=os.environ['TMP']=str(ROOT/'.cache/temp')
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    ctx=browser.new_context(accept_downloads=True)
    page=ctx.new_page()
    page.goto('https://www.capcut.cn/',wait_until='domcontentloaded',timeout=60000)
    page.locator('a[href*="download-guidance"]').first.wait_for(timeout=30000)
    with page.expect_download(timeout=90000) as ev:
        page.locator('a[href*="download-guidance"]').first.click()
    d=ev.value
    print('Official download: '+d.suggested_filename,flush=True)
    print('Source URL: '+d.url,flush=True)
    d.save_as(str(OUT/'JianyingPro_Official_Installer.exe'))
    (OUT/'download_origin.json').write_text(json.dumps({'website':'https://www.capcut.cn/','url':d.url,'filename':d.suggested_filename},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Installer bytes: '+str((OUT/'JianyingPro_Official_Installer.exe').stat().st_size),flush=True)
    browser.close()
