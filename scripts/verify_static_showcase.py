"""Validate the built GitHub Pages site with all backend requests blocked."""
from pathlib import Path
import json,os,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.cache/publication_tools'))
os.environ['TEMP']=os.environ['TMP']=str(ROOT/'.cache/temp')
from playwright.sync_api import sync_playwright
base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:5175/wenmai-huazhang/'
out=ROOT/'.cache/aic-static-results.json'
with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1600,'height':1100},locale='zh-CN',accept_downloads=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    def block(route):route.abort()
    page.route('**/health',block);page.route('**/generate',block)
    checked=[]
    for route in ['','styles','gallery','about','scenarios']:
        page.goto(base+'#/'+route);page.wait_for_load_state('networkidle')
        page.locator('img').evaluate_all('(imgs)=>imgs.forEach(i=>i.loading="eager")')
        page.wait_for_function('Array.from(document.images).every(i=>i.complete && i.naturalWidth>0)')
        checked.append(route or 'home')
    page.goto(base+'#/gallery');page.wait_for_load_state('networkidle')
    page.get_by_role('heading',name='从参考图，到文化表达').wait_for()
    assert page.get_by_test_id('culture-card').count()==5
    page.locator('#case-bianxiu').get_by_role('button',name='查看文创预览与下载').click()
    page.wait_for_url('**/#/products')
    page.get_by_role('heading',name='文创载体效果预览').wait_for()
    with page.expect_download() as d:page.get_by_role('button',name='下载文旅明信片效果图',exact=True).click()
    d.value.save_as(str(ROOT/'.cache/aic-static-postcard.png'))
    page.goto(base+'#/creator');page.wait_for_load_state('networkidle')
    page.locator('#subject-lock').wait_for()
    assert '在线浏览模式' in page.locator('body').inner_text()
    assert not errors,errors
    result={'baseUrl':base,'pages':checked,'savedCases':5,'productDownload':True,'backendBlocked':True,'errors':errors}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result))
    browser.close()
