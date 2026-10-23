from pathlib import Path
import re, shutil
ROOT=Path(__file__).resolve().parents[1]
BACKUP=ROOT/'.cache/aic-judge-experience-prechange/final-edit'
def edit(path,fn):
    dest=BACKUP/path.relative_to(ROOT)
    if not dest.exists():
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    path.write_text(fn(path.read_text(encoding='utf-8-sig')),encoding='utf-8')
for path in (ROOT/'frontend/src').rglob('*.tsx'):
    if path.name in ['Home.tsx','Scenarios.tsx']:
        edit(path,lambda s:re.sub(r'src="/(\w+)\.png"',r'src={import.meta.env.BASE_URL + "\1.png"}',s).replace("].map((src, idx)","].map((src, idx)").replace('<img src={src}', '<img src={import.meta.env.BASE_URL + src.replace(/^\\//, "")}'))
edit(ROOT/'frontend/src/data/styleLibrary.ts',lambda s:re.sub(r"img: '/(\w+)\.png'",r"img: import.meta.env.BASE_URL + '\1.png'",s))
edit(ROOT/'frontend/src/components/Navbar.tsx',lambda s:s.replace("{ name: '风格库', path: '/styles' },","{ name: '风格库', path: '/styles' },\n  { name: '真实案例', path: '/gallery' },").replace('gap-8','gap-5'))
def creator(s):
    s=s.replace('buildLocalCultureCard, checkBackendHealth','buildLocalCultureCard, checkBackendHealth')
    s=s.replace("import { useSearchParams, useNavigate }", "import { Link, useSearchParams, useNavigate }")
    s=s.replace("const [prompt, setPrompt]", "const [savedExample, setSavedExample] = useState(false);\n  const [prompt, setPrompt]")
    s=s.replace('setHistoryImages([parsed.imageUrl]);','setHistoryImages([parsed.imageUrl]);\n              setSavedExample(parsed.savedExample === true);\n              if (parsed.referencePreviewUrl) setPreviewUrl(parsed.referencePreviewUrl);')
    s=s.replace('setIsGenerating(true);','setIsGenerating(true);\n    setSavedExample(false);',1)
    s=s.replace('<a className="text-primary underline" href="/gallery">查看已保存的真实案例</a>','<Link className="text-primary underline" to="/gallery">查看已保存的真实案例</Link>')
    s=s.replace('<section className="mb-5 rounded-xl','{savedExample && <p role="status" className="mb-4 rounded-lg bg-secondary/10 p-3 text-sm text-secondary">已保存的真实案例 · 当前未执行实时推理。参考图预览为原始输入；重新生成需再次选择上传文件。</p>}\n              <section className="mb-5 rounded-xl')
    s=s.replace("bg-[url('/songhua.png')] bg-cover", "bg-cover").replace('className="absolute inset-0 bg-cover bg-center opacity-10 filter sepia"','className="absolute inset-0 bg-cover bg-center opacity-10 filter sepia" style={{backgroundImage: `url(${import.meta.env.BASE_URL}songhua.png)`}}')
    s=s.replace("    checkBackendHealth()", "    (import.meta.env.VITE_STATIC_SHOWCASE === 'true' ? Promise.reject(new Error('在线浏览模式：实时生成请下载项目后在本机启动。')) : checkBackendHealth())",1)
    s=s.replace('const health = await checkBackendHealth();',"if (import.meta.env.VITE_STATIC_SHOWCASE === 'true') throw new Error('在线浏览模式不执行实时推理。请下载源码，在本机配置个人 API Key 后运行。');\n        const health = await checkBackendHealth();")
    return s
edit(ROOT/'frontend/src/pages/AICreator.tsx',creator)
