import { Link, useNavigate } from 'react-router-dom';
import { savedCases, loadSavedCase } from '../data/savedCases';
import CultureCard from '../components/creator/CultureCard';

export default function Gallery() {
  const navigate = useNavigate();
  return <main className="max-w-7xl mx-auto px-6 py-12">
    <p className="text-primary text-sm">无需配置模型 · 已保存的真实生成案例</p>
    <h1 className="text-4xl font-serif mt-3 mb-5">从参考图，到文化表达</h1>
    <p className="max-w-3xl text-ink/70 leading-7">五组作品来自项目真实 Qwen Image 3.0 图生图链路。文化说明由本地 Qwen3-VL 读取对应成图后产生。这里浏览的是保存的结果，点击浏览不会调用付费模型。实时生成须在本机配置个人服务。</p>
    <nav className="flex flex-wrap gap-4 my-8">{savedCases.map(c=><button key={c.styleId} onClick={()=>document.getElementById(`case-${c.styleId}`)?.scrollIntoView({behavior:'smooth'})} className="px-4 py-2 rounded-full border border-primary/20 text-primary">{c.styleName}</button>)}</nav>
    {savedCases.map(c=><article id={`case-${c.styleId}`} key={c.styleId} className="mb-14 scroll-mt-20">
      <h2 className="font-serif text-2xl mb-2">{c.artworkTitle} · {c.styleName}</h2>
      <p className="text-sm text-ink/60 mb-5">风格提示强度 {Math.round(c.styleStrength*100)}% · 参考图已参与推理 · {c.generatedAt?.slice(0,10) || '原始生成日期未留存'}</p>
      <div className="grid md:grid-cols-3 gap-6 mb-6">{[[c.referenceUrl,'参考输入'],[c.imageUrl,'真实生成作品'],[c.cardUrl,'已导出 CultureCard']].map(([url,label])=><figure key={label} className="bg-white border border-primary/10 rounded-xl p-4"><a href={url} target="_blank" rel="noreferrer"><img src={url} alt={`${c.styleName}${label}`} className="w-full aspect-square object-contain" loading="lazy" /></a><figcaption className="mt-3 text-center text-sm">{label}</figcaption></figure>)}</div>
      <CultureCard imageUrl={c.imageUrl} theme={'theme' in c ? c.theme : c.artworkTitle} styleId={c.styleId} styleName={c.styleName} visualFeatures={c.visionAnalysis.visual_features} cultureSummary={c.visionAnalysis.culture_interpretation} recommendedScenes={c.visionAnalysis.recommended_scenes} generatedAt={c.generatedAt || ''} analysis={c.visionAnalysis} analysisSource={c.analysisSource} />
      <div className="flex gap-4 mt-5"><button className="rounded-lg bg-primary text-white px-5 py-3" onClick={()=>{loadSavedCase(c);navigate('/products');}}>查看文创预览与下载</button><Link className="rounded-lg border border-primary/20 px-5 py-3" to="/creator" onClick={()=>loadSavedCase(c)}>查看保存的工作台记录</Link></div>
    </article>)}
  </main>;
}
