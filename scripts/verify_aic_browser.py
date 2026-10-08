"""Actual browser exports and smoke checks. No paid generation requests."""
from pathlib import Path
import json, os, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.cache/publication_tools'))
os.environ['TEMP']=os.environ['TMP']=str(ROOT/'.cache/temp')
from playwright.sync_api import sync_playwright

OUT=ROOT/'docs/images/aic'
OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True)
    context=browser.new_context(viewport={'width':1600,'height':1100},locale='zh-CN',accept_downloads=True)
    page=context.new_page()
    page.set_default_timeout(45000)
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    result={'pages':{},'cards':{},'downloads':{},'errors':errors}
    page.goto('http://127.0.0.1:5173/gallery');page.wait_for_load_state('networkidle')
    page.get_by_role('heading',name='从参考图，到文化表达').wait_for()
    cards=page.get_by_test_id('culture-card')
    assert cards.count()==5
    for i,style in enumerate(['zhuxianzhen','bianxiu','songhua','qinghua','jianzhi']):
        button=cards.nth(i).get_by_role('button',name='下载文化说明卡')
        button.scroll_into_view_if_needed()
        with page.expect_download() as event: button.click()
        event.value.save_as(str(ROOT/'docs/examples'/style/'culture_card.png'))
        result['cards'][style]='exported_using_application_button'
        mpath=ROOT/'docs/examples'/style/'metadata.json'
        metadata=json.loads(mpath.read_text(encoding='utf-8-sig'))
        import hashlib
        metadata['cultureCardGeneratedSha256']=metadata['generatedSha256']
        metadata['cultureCardSha256']=hashlib.sha256((mpath.parent/'culture_card.png').read_bytes()).hexdigest()
        metadata['cultureCardExport']='Application CultureCard download button, Playwright browser, PNG'
        mpath.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page.goto('http://127.0.0.1:5173/gallery');page.wait_for_load_state('networkidle')
    page.screenshot(path=str(OUT/'gallery.png'),full_page=False)
    # Inspect stored records in the actual workbench, including the uploaded reference preview.
    page.locator('#case-songhua').get_by_role('link',name='查看保存的工作台记录').click()
    page.wait_for_url('**/creator')
    page.locator('#subject-lock').wait_for()
    page.get_by_test_id('culture-card').wait_for()
    page.wait_for_load_state('networkidle')
    page.screenshot(path=str(ROOT/'docs/images/workspace.png'),full_page=True)
    page.screenshot(path=str(OUT/'workspace.png'),full_page=True)
    assert page.get_by_text('已保存的真实案例 · 当前未执行实时推理。',exact=False).count()>0
    for route in ['','styles','creator','products','scenarios','about','gallery']:
        page.goto('http://127.0.0.1:5173/'+route);page.wait_for_load_state('networkidle')
        assert page.locator('body').inner_text().strip()
        page.locator('img').evaluate_all('(imgs)=>imgs.forEach(i=>i.loading="eager")')
        page.wait_for_function('Array.from(document.images).every(i=>i.complete && i.naturalWidth>0)')
        broken=page.locator('img').evaluate_all('(imgs)=>imgs.filter(i=>!i.complete||i.naturalWidth===0).map(i=>i.src)')
        assert not broken, (route,broken)
        result['pages'][route or 'home']='loaded_images_valid'
    page.locator('#case-songhua').get_by_role('button',name='查看文创预览与下载').click()
    page.wait_for_url('**/products')
    page.get_by_role('heading',name='文创载体效果预览').wait_for()
    page.wait_for_load_state('networkidle')
    for name,file in [('文旅明信片','postcard.png'),('帆布袋','bag.png')]:
        with page.expect_download() as event:
            page.get_by_role('button',name=f'下载{name}效果图',exact=True).click()
        event.value.save_as(str(OUT/file));result['downloads'][name]='actual_application_export'
    page.screenshot(path=str(OUT/'products.png'),full_page=True)
    # Browser fixtures exercise UI status only, never masquerade as genuine inference.
    def unavailable(route):
        route.fulfill(json={'status':'ok','generationProvider':'dashscope_qwen_image','provider':'dashscope_qwen_image','model':'qwen-image-3.0','allowMockFallback':False,'providers':{'dashscope_qwen_image':{'available':False,'hasApiKey':False}},'localVisionAnalysis':{'enabled':True,'available':False,'provider':'ollama_local','model':'qwen3-vl:4b-instruct-q4_K_M','message':'未安装'}})
    page.route('**/health',unavailable)
    page.goto('http://127.0.0.1:5173/creator');page.wait_for_load_state('networkidle')
    assert '未配置' in page.locator('body').inner_text()
    assert '本地未启动或模型未安装' in page.locator('body').inner_text()
    page.screenshot(path=str(OUT/'missing-services.png'),full_page=True)
    result['unconfiguredStatus']='browser_fixture_passed'
    page.goto('http://127.0.0.1:5173/gallery');page.wait_for_load_state('networkidle')
    assert page.get_by_test_id('culture-card').count()==5
    result['savedCasesWithoutServices']='passed_browser_health_fixture'
    assert not errors, errors
    (ROOT/'.cache/aic-browser-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True))
    context.close();browser.close()
