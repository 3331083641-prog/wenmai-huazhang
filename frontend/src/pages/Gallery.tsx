import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, BookOpen, Layers, Sparkles } from 'lucide-react';
import { autoSavedCases, savedCases, loadSavedCase } from '../data/savedCases';
import { experienceById, experienceByStyle, cultureSourcesVersion } from '../data/experiences';
import { fetchRuntimeCases, mergeCases, type GalleryCase } from '../services/caseService';
import CultureCard from '../components/creator/CultureCard';
import ArtworkCompare from '../features/culture-experience/components/ArtworkCompare';

/**
 * 文化作品展厅。
 *
 * 两类案例用同一套卡片渲染：
 *  - 内置五件（编译期打包，离线可看，带人工标注的互动解读）
 *  - 后端每次生成成功后自动落盘的运行期案例（通过 /cases 拉取）
 *
 * 运行期案例默认没有热点坐标与章节，因此不显示互动入口——
 * 宁可少一个按钮，也不把用户带到一个坐标对不上的页面。
 */
export default function Gallery() {
  const navigate = useNavigate();
  const { hash } = useLocation();
  const [openCard, setOpenCard] = useState<string | null>(null);
  const [runtimeCases, setRuntimeCases] = useState<GalleryCase[]>([]);
  const [runtimeState, setRuntimeState] = useState<'loading' | 'ready' | 'offline'>('loading');

  useEffect(() => {
    let alive = true;
    fetchRuntimeCases()
      .then((list) => {
        if (!alive) return;
        setRuntimeCases(list);
        setRuntimeState('ready');
      })
      .catch(() => {
        if (alive) setRuntimeState('offline');
      });
    return () => {
      alive = false;
    };
  }, []);

  const cases = useMemo(
    () => mergeCases([...savedCases, ...autoSavedCases], runtimeCases),
    [runtimeCases],
  );

  // 从创作台的「查看《…》」跳过来时定位到对应卡片；案例是异步拉取的，所以也依赖数量变化
  useEffect(() => {
    if (!hash.startsWith('#case-')) return;
    const target = document.getElementById(hash.slice(1));
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [hash, cases.length]);

  const resolveExperience = (item: GalleryCase) => {
    if (item.experienceId) return experienceById.get(item.experienceId);
    // 运行期案例的内容与原案例不同，绝不能借用同风格的旧热点坐标
    if (item.caseOrigin === 'curated') return experienceByStyle.get(item.styleId);
    return undefined;
  };

  return (
    <main className="mx-auto max-w-[1240px] px-4 pb-16 pt-24 sm:px-6">
      <header className="mb-8">
        <p className="text-[11px] tracking-[0.34em] text-[color:var(--color-primary)]">
          无需配置模型 · 已保存的真实生成案例
        </p>
        <h1 className="mt-3 font-serif text-[clamp(1.9rem,4vw,2.8rem)] leading-tight text-[color:var(--color-ink)]">
          文化作品展厅
        </h1>
        <p className="mt-3 max-w-3xl text-[13.5px] leading-[1.9] text-[color:var(--color-ink)]/70">
          内置的 {savedCases.length} 组作品来自项目真实 Qwen Image 3.0 图生图链路，文化说明由本地 Qwen3-VL 读取对应成图后产生。
          此后每次在创作台成功生成的图，都会自动落盘成一份案例出现在这里：参考图、成图、文化卡与下载入口与原案例一致。
          浏览与互动都不会调用付费模型。
        </p>

        <div className="mt-5 flex flex-wrap gap-2 text-[11.5px] text-[color:var(--color-ink)]/55">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--color-gold)]/50 bg-white/50 px-2.5 py-1">
            <Sparkles size={12} />
            内置案例热点位置均经裁切复核
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--color-gold)]/50 bg-white/50 px-2.5 py-1">
            文化来源 {cultureSourcesVersion}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--color-gold)]/50 bg-white/50 px-2.5 py-1">
            内置 {savedCases.length} 件 · 离线可看
            {runtimeState === 'ready' && runtimeCases.length > 0 && ` · 自动保存 ${runtimeCases.length} 件`}
          </span>
        </div>
      </header>

      {runtimeState === 'offline' && (
        <p className="mb-5 rounded border border-[color:var(--color-gold)]/40 bg-white/50 px-3 py-2 text-[12px] text-[color:var(--color-ink)]/60">
          没有连上本地后端，只显示随项目内置的 {savedCases.length} 件案例；启动后端后刷新即可看到自动保存的新作品。
        </p>
      )}

      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
        {cases.map((item) => {
          const experience = resolveExperience(item);
          // 画境漫游有两种实现：world（深度网格，5 件作品都用它）与旧的 layered（三层视差）。
          // 只要该作品真的声明了可用的清单，就给它「画境漫游」按钮，否则不显示死入口。
          const canWander =
            experience?.animation.mode === 'world'
              ? Boolean(experience.animation.world?.url)
              : experience?.animation.mode === 'layered' && Boolean(experience?.animation.layers?.length);
          const isRuntime = item.caseOrigin === 'runtime';
          const accent = experience?.theme.accent ?? '#9E241B';
          return (
            <article
              key={item.caseId}
              id={`case-${item.caseId}`}
              className="flex scroll-mt-24 flex-col self-start overflow-hidden rounded-lg border border-[color:var(--color-gold)]/40 bg-[#FDFBF7] shadow-[0_8px_24px_rgba(63,43,31,0.05)] transition hover:shadow-[0_14px_36px_rgba(63,43,31,0.09)]"
            >
              <div className="p-2.5 pb-0">
                <ArtworkCompare
                  referenceUrl={item.referenceUrl}
                  artworkUrl={item.imageUrl}
                  title={item.artworkTitle}
                  accent={accent}
                />
              </div>

              <div className="flex flex-1 flex-col p-3.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h2 className="truncate font-serif text-lg text-[color:var(--color-ink)]">{item.artworkTitle}</h2>
                    <p className="mt-0.5 text-[11.5px] text-[color:var(--color-ink)]/50">
                      {item.styleName} · 提示强度 {Math.round((item.styleStrength || 0) * 100)}%
                    </p>
                  </div>
                  {experience ? (
                    <span
                      className="shrink-0 rounded-full px-2 py-0.5 text-[10px]"
                      style={{ backgroundColor: `${experience.theme.accent}14`, color: experience.theme.accent }}
                    >
                      {experience.hotspots.length} 处线索
                    </span>
                  ) : isRuntime ? (
                    <span className="shrink-0 rounded-full bg-[color:var(--color-gold)]/15 px-2 py-0.5 text-[10px] text-[color:var(--color-ink)]/60">
                      自动保存
                    </span>
                  ) : null}
                </div>

                <p className="mt-2 line-clamp-2 text-[12px] leading-relaxed text-[color:var(--color-ink)]/60">
                  {item.visionAnalysis.culture_interpretation || item.visionAnalysis.theme_summary || '暂无文化解读。'}
                </p>

                <div className="mt-3 flex flex-wrap gap-1.5">
                  {item.visionAnalysis.visual_features.slice(0, 3).map((feature) => (
                    <span
                      key={feature}
                      className="rounded border border-[color:var(--color-gold)]/40 px-1.5 py-0.5 text-[10.5px] text-[color:var(--color-ink)]/55"
                    >
                      {feature}
                    </span>
                  ))}
                </div>

                <div className="mt-3.5 flex flex-wrap gap-2 border-t border-[color:var(--color-gold)]/25 pt-3">
                  {experience ? (
                    <>
                      <Link
                        to={`/experience/${experience.id}`}
                        className="inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-[12px] text-white transition hover:opacity-90"
                        style={{ backgroundColor: experience.theme.accent }}
                      >
                        进入互动画境
                        <ArrowRight size={13} />
                      </Link>
                      <Link
                        to={`/story/${experience.id}`}
                        className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/60 px-3 py-1.5 text-[12px] text-[color:var(--color-ink)]/75 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
                      >
                        <BookOpen size={13} />
                        一图一境
                      </Link>
                      {canWander && (
                        <Link
                          to={`/wander/${experience.id}`}
                          className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/60 px-3 py-1.5 text-[12px] text-[color:var(--color-ink)]/75 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
                        >
                          <Layers size={13} />
                          画境漫游
                        </Link>
                      )}
                    </>
                  ) : (
                    <>
                      <span className="inline-flex items-center gap-1.5 rounded border border-dashed border-[color:var(--color-gold)]/60 px-3 py-1.5 text-[12px] text-[color:var(--color-ink)]/45">
                        自动保存 · 热点待标注
                      </span>
                      <Link
                        to="/creator"
                        className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/60 px-3 py-1.5 text-[12px] text-[color:var(--color-ink)]/75"
                      >
                        在创作台再生成一件
                      </Link>
                    </>
                  )}
                </div>

                <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[11px] text-[color:var(--color-ink)]/45">
                  <button
                    type="button"
                    onClick={() => {
                      loadSavedCase(item);
                      navigate('/products');
                    }}
                    className="underline decoration-dotted underline-offset-4 transition hover:text-[color:var(--color-primary)]"
                  >
                    文创预览与下载
                  </button>
                  <button
                    type="button"
                    onClick={() => setOpenCard(openCard === item.caseId ? null : item.caseId)}
                    className="underline decoration-dotted underline-offset-4 transition hover:text-[color:var(--color-primary)]"
                    aria-expanded={openCard === item.caseId}
                  >
                    {openCard === item.caseId ? '收起文化卡' : '展开文化卡'}
                  </button>
                  <span className="ml-auto">{item.generatedAt?.slice(0, 10) || '生成日期未留存'}</span>
                </div>
              </div>

              {openCard === item.caseId && (
                <div className="max-h-[560px] overflow-y-auto border-t border-[color:var(--color-gold)]/30 bg-white/60 p-3">
                  <CultureCard
                    imageUrl={item.imageUrl}
                    theme={item.theme || item.artworkTitle}
                    styleId={item.styleId}
                    styleName={item.styleName}
                    visualFeatures={item.visionAnalysis.visual_features}
                    cultureSummary={item.visionAnalysis.culture_interpretation}
                    recommendedScenes={item.visionAnalysis.recommended_scenes}
                    generatedAt={item.generatedAt || ''}
                    analysis={item.visionAnalysis}
                    analysisSource={item.analysisSource}
                  />
                </div>
              )}
            </article>
          );
        })}
      </div>

      <section className="mt-10 rounded-lg border border-[color:var(--color-gold)]/40 bg-white/45 p-5 sm:p-6">
        <h2 className="font-serif text-lg text-[color:var(--color-ink)]">这些坐标是怎么来的</h2>
        <ul className="mt-3 grid gap-2 text-[12.5px] leading-relaxed text-[color:var(--color-ink)]/65 sm:grid-cols-2">
          <li>· 原始生成结果里没有坐标信息，热点位置由本项目用本地视觉模型候选 + 逐点裁切复核确定。</li>
          <li>· 通过复核记为「已逐点复核」，未通过则降级为「约定位」，宁可不标也不猜。</li>
          <li>· 新生成的作品会自动保存为案例，但热点需要人工标注，所以它们先以「自动保存」状态出现在展厅。</li>
          <li>· 互动页与自动保存的案例都离线可用：内置五件不配置模型也能打开，自动保存的案例需要本地后端在运行。</li>
        </ul>
      </section>
    </main>
  );
}