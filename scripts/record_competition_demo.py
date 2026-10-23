"""Record real browser operations and retain timing, narration and downloads locally."""
from pathlib import Path
import asyncio, json, os, sys, time

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'outputs/video/source'
WORK.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / '.cache/publication_tools'))
os.environ['TEMP'] = os.environ['TMP'] = str(ROOT / '.cache/temp')
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.cache/playwright')
import edge_tts
from playwright.sync_api import sync_playwright

CHAPTERS = [
    ('文化创作，从灵感到应用', '纹脉华章，是传统文化视觉智能创作与文创应用平台。我们把文化风格选择、智能图像生成、作品理解、文化说明和文创预览连接起来，让一次创作既有视觉成果，也有可阅读、可传播的文化内容。接下来，通过真实浏览器操作，演示完整的创作过程。'),
    ('五类风格，结构化表达', '进入风格库，可以看到朱仙镇木版年画、汴绣纹样、宋画青绿山水、青花瓷纹样和中国剪纸。每个条目整理了视觉特征、文化说明和适用场景。这里选择宋画青绿山水，围绕山水与楼阁展开创作。风格资料随后会参与提示词组织。'),
    ('主题、参考与约束', '在智能生成页，输入具体主题：青绿群山之间，楼阁临水，仙鹤掠过云间。加入参考图，让原有的山水结构参与创作。负向提示词用来排除现代建筑、文字和水印。风格影响强度设为百分之六十五，并选择横向层次布局与文旅明信片。所有设置都能在请求参数预览中核对。'),
    ('真实生成与图像理解', '点击生成，系统将主题、文化风格、参考图和约束组织成生成请求，交给 Qwen Image 三点零完成视觉创作。随后，本地 Qwen 三视觉模型读取实际成图，提取主体、构图、色彩和文化元素。两个模型分别负责创作和理解，结果回到同一个工作台。画面中的等待过程来自实际服务调用；本段仅对等待时间进行适度加速。'),
    ('作品与 CultureCard', '生成结果已经返回。我们可以查看完整作品，再向下阅读文化说明卡。卡片中的主体描述、色彩构图、文化元素和应用建议，与这张成图对应。页面显示本地图像理解的来源。打开生成详情，还可以核对模型、参考图是否参与以及本次参数。接着下载原图和文化说明卡，把作品与解释一起保存。'),
    ('文创预览与文件导出', '同一张生成作品可以进入文创转化页面，自动应用到明信片、数字海报、帆布袋、书签、杯垫、手机分享图、展陈屏和纪念票等载体。切换预览，可以比较不同媒介中的呈现效果。这里实际下载明信片和帆布袋效果图，便于方案展示与后续设计。页面明确展示的是应用效果预览。'),
    ('让文化成果进入更多场景', '应用场景页展示教学、文旅传播、文化展陈和内容分享的使用方向。至此，我们完成了主题输入、参考图参与、风格控制、真实生成、作品理解、文化说明、文创预览与下载的完整流程。项目以 MIT 许可证开放代码，评审可以通过随附的源码和运行说明复现。纹脉华章，让中华美学融入现代生活。'),
]

async def voices():
    for i, (title, speech) in enumerate(CHAPTERS):
        mp3 = WORK / f'voice_{i:02d}.mp3'
        if mp3.exists():
            continue
        comm = edge_tts.Communicate(speech, 'zh-CN-YunxiNeural', rate='+6%')
        subs = edge_tts.SubMaker()
        with mp3.open('wb') as f:
            async for chunk in comm.stream():
                if chunk['type'] == 'audio': f.write(chunk['data'])
                elif chunk['type'] in ('WordBoundary','SentenceBoundary'): subs.feed(chunk)
        (WORK / f'voice_{i:02d}.srt').write_text(subs.get_srt(), encoding='utf-8')
        print(f'Narration {i+1}/7 ready', flush=True)

def main():
    asyncio.run(voices())
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(viewport={'width':1920,'height':1080}, record_video_dir=str(WORK), record_video_size={'width':1920,'height':1080}, accept_downloads=True, locale='zh-CN')
        context.add_init_script("""document.addEventListener('DOMContentLoaded',()=>{let c=document.createElement('div');c.id='demo-cursor';c.style.cssText='position:fixed;left:-40px;top:-40px;width:25px;height:25px;border:2px solid #b8422e;border-radius:50%;background:#b8422e22;pointer-events:none;z-index:2147483647;transform:translate(-50%,-50%);transition:width .1s,height .1s';document.body.append(c);document.addEventListener('mousemove',e=>{c.style.left=e.clientX+'px';c.style.top=e.clientY+'px'});document.addEventListener('mousedown',()=>{c.style.width='17px';c.style.height='17px'});document.addEventListener('mouseup',()=>{c.style.width='25px';c.style.height='25px'})})""")
        page = context.new_page()
        page.set_default_timeout(18000)
        started = time.monotonic()
        marks=[]
        def begin(i):
            marks.append({'chapter':i,'start':time.monotonic()-started,'title':CHAPTERS[i][0]})
            print(f'Recording chapter {i+1}/7',flush=True)
        def wait(seconds): page.wait_for_timeout(int(seconds*1000))
        def scroll(y):
            page.evaluate('(y)=>window.scrollTo({top:y,behavior:"smooth"})',y);wait(1.6)
        def click(loc):
            loc.scroll_into_view_if_needed();wait(.6)
            box=loc.bounding_box()
            if box:page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2,steps=22)
            wait(.5);loc.click();wait(1.5)
        def hold(minimum):
            elapsed=time.monotonic()-started-marks[-1]['start']
            wait(max(0,minimum-elapsed))
        def download(loc,name):
            with page.expect_download(timeout=30000) as dl: click(loc)
            dl.value.save_as(str(WORK/name))

        begin(0)
        page.goto('http://127.0.0.1:5173/',wait_until='networkidle');wait(3)
        page.mouse.move(1220,400,steps=25);scroll(400);wait(5);scroll(0);hold(29)
        begin(1)
        click(page.get_by_role('link',name='风格库',exact=True));wait(3)
        scroll(420);wait(6);scroll(920);wait(6);scroll(0);hold(29)
        begin(2)
        click(page.get_by_role('link',name='智能生成',exact=True))
        textarea=page.locator('textarea').first
        click(textarea);textarea.fill('');textarea.press_sequentially('青绿群山之间，宋代楼阁临水而立，仙鹤掠过云间，松树与祥云点缀画面，清雅留白，横向山水构图',delay=65)
        negative=page.get_by_placeholder('例如：现代建筑、现代服饰、文字、水印...')
        click(negative);negative.press_sequentially('现代建筑，现代服饰，文字，水印，模糊，畸形',delay=70)
        page.locator('input[type=file]').set_input_files(str(ROOT/'docs/examples/songhua/generated.png'));wait(3)
        click(page.get_by_role('button',name='选择宋画青绿山水'))
        scroll(420)
        page.locator('input[type=range]').evaluate('(el)=>{el.value=65;el.dispatchEvent(new Event("input",{bubbles:true}));el.dispatchEvent(new Event("change",{bubbles:true}))}')
        page.locator('select').nth(0).select_option('landscape');wait(2)
        page.locator('select').nth(1).select_option('postcard');wait(2)
        click(page.get_by_text('本次请求参数预览',exact=True));wait(4)
        hold(39)
        begin(3)
        response_box=[]
        page.on('response',lambda resp: response_box.append(resp) if resp.url.endswith('/generate') and resp.request.method=='POST' else None)
        click(page.get_by_role('button',name='AI 生成视觉作品'))
        generation_start=time.monotonic()
        while not response_box:
            if time.monotonic()-generation_start>420: raise RuntimeError('Actual generation timed out')
            wait(2)
        response=response_box[0]
        data=response.json()
        if response.status !=200 or not data.get('imageUrl'):raise RuntimeError('Actual generation failed; status '+str(response.status))
        if data.get('analysisSource') !='qwen3_vl':raise RuntimeError('Real image understanding did not complete')
        # Store only public-safe evidence; never request headers, env or embedded input data.
        safe={k:data.get(k) for k in ['imageUrl','provider','model','mode','referenceImageUsed','analysisSource','visionAnalysis','cultureCard','createdAt']}
        (WORK/'generation_evidence.json').write_text(json.dumps(safe,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Actual generation and Qwen3-VL analysis completed',flush=True)
        wait(4)
        begin(4)
        scroll(0);wait(5)
        (ROOT/'docs/images').mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(ROOT/'docs/images/workspace.png'))
        scroll(450);wait(4);scroll(800);wait(5)
        click(page.get_by_text('查看生成详情',exact=True));wait(4)
        download(page.get_by_role('button',name='下载文化说明卡'),'CultureCard.png')
        download(page.get_by_role('button',name='下载生成原图'),'generated.png')
        hold(43)
        begin(5)
        click(page.get_by_role('button',name='前往文创预览'));wait(3)
        scroll(330);wait(4)
        click(page.get_by_role('button',name='查看效果').first);wait(4)
        download(page.get_by_role('button',name='下载文旅明信片效果图'),'postcard.png')
        download(page.get_by_role('button',name='下载帆布袋效果图'),'bag.png')
        scroll(650);wait(5);scroll(1050);wait(4);hold(41)
        begin(6)
        scroll(0)
        click(page.get_by_role('link',name='应用场景',exact=True));wait(3)
        scroll(380);wait(5);scroll(800);wait(5);scroll(0);hold(35)
        end=time.monotonic()-started
        for i,m in enumerate(marks):m['end']=marks[i+1]['start'] if i+1<len(marks) else end
        video=page.video
        context.close()
        video.save_as(str(WORK/'continuous_browser.webm'))
        browser.close()
        (WORK/'recording_timeline.json').write_text(json.dumps(marks,ensure_ascii=False,indent=2),encoding='utf-8')
        (WORK/'narration.json').write_text(json.dumps(CHAPTERS,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Recording complete',flush=True)

if __name__=='__main__':main()
