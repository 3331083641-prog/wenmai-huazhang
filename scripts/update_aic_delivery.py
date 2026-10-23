"""Prepare reviewed saved examples; never invokes a paid image API."""
from pathlib import Path
import hashlib
import json
import shutil
import re

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / '.cache/aic-judge-experience-prechange/final-edit'

def backup(path):
    dest = BACKUP / path.relative_to(ROOT)
    if path.exists() and not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)

def edit(rel, transform):
    path = ROOT / rel
    backup(path)
    path.write_text(transform(path.read_text(encoding='utf-8-sig')), encoding='utf-8')

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def replace_saved(style, ref, output, response, request, title, subject, source, timestamp):
    folder = ROOT / 'docs/examples' / style
    prior = read(folder/'metadata.json')
    archive = ROOT / '.cache/aic-animal-attempts' / style
    archive.mkdir(parents=True, exist_ok=True)
    for name in ['generated.png', 'reference.png', 'metadata.json']:
        shutil.copy2(folder/name, archive/name)
        backup(folder/name)
    shutil.copy2(ref, folder/'reference.png')
    shutil.copy2(output, folder/'generated.png')
    m = {
        'styleId': style, 'styleName': prior['styleName'], 'referenceSubject': subject,
        'artworkTitle': title, 'theme': request['theme'], 'referenceSource': source,
        'referenceSha256': sha(ref), 'generatedSha256': sha(output),
        'generatedBytes': output.stat().st_size, 'provider': response['provider'],
        'model': response['model'], 'styleStrength': request['styleStrength'],
        'compositionMode': request['compositionMode'], 'outputType': 'poster',
        'negativePrompt': request.get('negativePrompt'), 'generatedAt': timestamp,
        'generationSucceeded': True, 'referenceImageUsed': response['referenceImageUsed'],
        'modelInputImageCount': response.get('debug', {}).get('modelInputImageCount'),
        'generationEvidence': 'Archived project generation response; output and reference copied without modification.',
        'analysisSource': response['analysisSource'], 'visionAnalysis': response['visionAnalysis'],
        'visionProvider': 'ollama_local', 'visionModel': 'qwen3-vl:4b-instruct-q4_K_M',
        'cultureCardAnalysisSource': 'qwen3_vl_on_generated_image',
        'selectionNote': 'User requested reuse of the previous genuine video case on 2026-10-08; not newly generated.',
    }
    (folder/'metadata.json').write_text(json.dumps(m, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')

def main():
    rev = ROOT / 'iCAN_应用方案/视频/02_generated_assets/revision'
    rabbit = rev/'bianxiu_reference'
    r = read(rabbit/'response.json')
    # Extract generation time from the genuine output filename, not file copy time.
    match = re.search(r'qwen_image_(\d{8})_(\d{6})', r.get('imageUrl',''))
    timestamp = None
    if match:
        d,t=match.groups(); timestamp=f'{d[:4]}-{d[4:6]}-{d[6:]}T{t[:2]}:{t[2:4]}:{t[4:]}+08:00'
    replace_saved('bianxiu', rabbit/'reference.png', rabbit/'generated.png', r,
        read(rabbit/'request.json'), '绣兔牡丹', '牡丹锦禽刺绣纹样（主题指定白兔）',
        '项目原有 AI 生成的汴绣风格展示图；原始生成工具版本未留存，不声明公有领域或 CC0。',timestamp)
    recording=ROOT/'iCAN_应用方案/视频/01_screen_recordings/revision'
    replace_saved('songhua', rev/'tower_reference.png', recording/'generated.png',
        read(recording/'generation_evidence.json'),
        {'theme':'青绿群山之间，参考图中的双层古典楼阁临水而立，保留楼阁的木构屋檐与双层形制，仙鹤掠过云间，松树与祥云点缀画面，清雅留白，横向山水构图',
         'styleStrength':.65, 'compositionMode':'landscape',
         'negativePrompt':'现代建筑，现代服饰，文字，水印，模糊，畸形'},
        '云鹤临水楼', '双层古典楼阁',
        '用户提供的 AI 生成建筑参考图（ChatGPT 图像）；图示为宋式建筑创作参考，不声称为宋代文物实物照片。',
        '2026-09-30T22:28:33+08:00')
    # Conservative instructions supersede old poetic certainty; future and current analyses use these.
    edit('backend/services/vision_analysis.py', lambda s: s[:s.index('VISION_SYSTEM_PROMPT =')] + '''VISION_SYSTEM_PROMPT = """你是纹脉华章的传统文化视觉解读助手。先仔细观察实际生成图片，再结合用户主题和给定风格资料输出 JSON。
observed_subjects 只列真实可见的实体；visual_features、composition、dominant_colors 只描述实际画面。不得把主题要求当成已经看见的内容。
culture_interpretation 从至少两项可见细节出发写80至180字审美解读。区分画面观察和文化联想，以准确、保守的表述为准，不编造历史出处、年份、民俗寓意、非遗身份或艺术家归属。不必引用诗文；如引用只能使用给定 literaryReferences 的准确原文与篇名。
传统风格是本次 AI 视觉转化的方向，不据此认定作品是历史实物或手工制品。只使用所选风格适用的材质语言，不把青花写成刺绣。看不清的细节不要猜测。
应用建议用“可用于”“适用于”，不声称已落地。全部简体中文，严格按要求的JSON字段返回，不输出Markdown。
"""


''' + s[s.index('VISION_JSON_SCHEMA'):])
    edit('backend/app.py',lambda s:s.replace('from typing import Any, Optional','from typing import Any, Optional\nfrom pathlib import Path').replace('service = GenerationService()', 'app.mount("/examples", StaticFiles(directory=str(Path(__file__).resolve().parents[1] / "docs/examples")), name="examples")\n\nservice = GenerationService()'))
    edit('frontend/src/services/generationService.ts', lambda s:s.replace('前端无法连接后端 FastAPI，请确认 http://127.0.0.1:8000/health 是否可打开。','生成服务未连接。请双击 start_windows.cmd 启动完整系统，或先浏览已保存的真实案例。').replace('throw new ApiResponseError(data.error || `API error: ${response.status}`);','throw new ApiResponseError("生成服务暂不可用，请检查个人服务配置和网络后重试。");').replace('const debugText = data.debug ? ` Debug: ${JSON.stringify(data.debug)}` : "";\n      throw new ApiResponseError((data.error || "后端生成失败。") + debugText);','throw new ApiResponseError("图像生成失败。请检查个人 API Key、服务额度及网络连接；本次未使用演示图片替代。");'))
    for rel in ['frontend/src/pages/Home.tsx','frontend/src/pages/About.tsx']:
        edit(rel,lambda s:s.replace('2026 iCAN大学生创新创业大赛 · AI应用创新挑战赛 · 软件赛道','传统文化视觉创作 · 文化理解 · 文创应用'))
    def creator(s):
        s=s.replace('启动：D:\\wenmai-huazhang\\scripts\\start_backend.bat','双击 start_windows.cmd 启动')
        s=re.sub(r'\s*\{resultData\?\.realProviderError && <div.*?</div>\}', '', s)
        s=re.sub(r'\s*<details className="border-t border-black/5 px-4 py-3"><summary className="cursor-pointer text-xs font-medium text-ink/55">开发者信息</summary>.*?</details>', '',s)
        s=s.replace('{/* Prompt Area */}', '''<section className="mb-5 rounded-xl border border-primary/10 bg-paper p-4 text-sm" aria-label="模型服务状态">
                <p>图像生成 · Qwen Image 3.0：{backendStatus === 'disconnected' ? '当前不可用' : backendStatus === 'checking' ? '检查中' : backendHealth?.providers?.dashscope_qwen_image?.hasApiKey === false ? '未配置' : backendHealth?.providers?.dashscope_qwen_image?.available ? '已连接（配置就绪）' : '当前不可用'}</p>
                <p className="mt-2">文化理解 · Qwen3-VL：{backendHealth?.localVisionAnalysis?.available ? '本地可用' : '本地未启动或模型未安装'}</p>
                <p className="mt-3 text-xs text-ink/60">实时图像生成需要配置阿里云百炼服务及个人 API Key，可能产生调用费用。没有模型也可<a className="text-primary underline" href="/gallery">查看已保存的真实案例</a>；模板说明不代表看图分析成功。</p>
              </section>
              {/* Prompt Area */}''')
        # Timer animations must not claim that a server stage has completed.
        s=s.replace('"正在保存生成作品..."','"正在等待生成结果..."').replace('"正在整理文化风格说明..."','"生成与文化分析进行中，请稍候..."')
        return s
    edit('frontend/src/pages/AICreator.tsx',creator)

if __name__=='__main__':
    main()
