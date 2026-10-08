"""Isolated real backend without a key or VL; never alters the private project env."""
from pathlib import Path
import base64, json, os, subprocess, sys, time, urllib.request, socket
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.cache/publication_tools'))
os.environ['TEMP']=os.environ['TMP']=str(ROOT/'.cache/temp')
from playwright.sync_api import sync_playwright
WORK=ROOT/'.cache/aic-unconfigured-runtime';WORK.mkdir(parents=True,exist_ok=True)
envfile=WORK/'isolated.env'
envfile.write_text('GENERATION_PROVIDER=dashscope_qwen_image\nALLOW_MOCK_FALLBACK=false\nDASHSCOPE_API_KEY=\nDASHSCOPE_BASE_URL=\nDASHSCOPE_IMAGE_MODEL=qwen-image-3.0\nQWEN_VL_ENABLED=false\n',encoding='utf-8')
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
env=os.environ.copy();env['WENMAI_ENV_FILE']=str(envfile)
with (WORK/'backend.log').open('w',encoding='utf-8') as log:
    process=subprocess.Popen([str(ROOT/'backend/venv/Scripts/python.exe'),'-m','uvicorn','app:app','--host','127.0.0.1','--port',str(port),'--log-level','warning'],cwd=ROOT/'backend',env=env,stdout=log,stderr=log)
    try:
        url=f'http://127.0.0.1:{port}'
        health=None
        for _ in range(30):
            try:health=json.load(urllib.request.urlopen(url+'/health',timeout=15));break
            except Exception:time.sleep(.3)
        assert health and not health['providers']['dashscope_qwen_image']['hasApiKey']
        assert not health['localVisionAnalysis']['available']
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel='msedge',headless=True)
            page=browser.new_page(viewport={'width':1600,'height':1100},locale='zh-CN')
            def health_proxy(route):route.fulfill(response=route.fetch(url=url+'/health'))
            payloads=[]
            def generate_proxy(route):
                payloads.append(route.request.post_data_json)
                route.fulfill(response=route.fetch(url=url+'/generate'))
            page.route('**/health',health_proxy);page.route('**/generate',generate_proxy)
            page.goto('http://127.0.0.1:5173/creator');page.wait_for_load_state('networkidle')
            assert '未配置' in page.locator('body').inner_text()
            page.locator('textarea').first.fill('白兔与牡丹')
            page.locator('#subject-lock').fill('一只白兔')
            page.get_by_role('button',name='选择汴绣纹样').click()
            page.locator('input[type=file]').set_input_files(str(ROOT/'docs/examples/bianxiu/reference.png'))
            page.get_by_role('button',name='AI 生成视觉作品').click()
            page.get_by_text('图像生成失败。请检查个人 API Key、服务额度及网络连接；本次未使用演示图片替代。').wait_for(timeout=60000)
            assert len(payloads)==1 and payloads[0]['subjectLock']=='一只白兔'
            assert payloads[0]['style']=='bianxiu'
            decoded=base64.b64decode(payloads[0]['uploadedImage'].split(',',1)[1])
            assert decoded==(ROOT/'docs/examples/bianxiu/reference.png').read_bytes()
            text=page.locator('body').inner_text();assert 'Traceback' not in text and 'D:\\' not in text and 'Debug:' not in text
            page.screenshot(path=str(ROOT/'docs/images/aic/unconfigured-real-backend.png'),full_page=True)
            page.goto('http://127.0.0.1:5173/gallery');page.wait_for_load_state('networkidle')
            assert page.get_by_test_id('culture-card').count()==5
            browser.close()
        result={'realBackendNoKey':True,'realBackendNoVision':True,'browserGenerateFailedClearly':True,'actualFrontendReferencePayloadMatches':True,'savedCasesReadable':True,'paidRequests':0}
        (ROOT/'.cache/aic-unconfigured-results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result))
    finally:
        process.terminate()
        try:process.wait(timeout=12)
        except subprocess.TimeoutExpired:process.kill();process.wait()
