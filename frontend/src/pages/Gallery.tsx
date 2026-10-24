import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Frame,
  Layers,
  Loader2,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { autoSavedCases, savedCases, loadSavedCase } from '../data/savedCases';
import { experienceById, experienceByStyle, cultureSourcesVersion } from '../data/experiences';
import {
  fetchRuntimeCases,
  mergeCases,
  rebuildCaseInteractions,
  type CaseInteraction,
  type GalleryCase,
} from '../services/caseService';
import CultureCard from '../components/creator/CultureCard';
import ArtworkCompare from '../features/culture-experience/components/ArtworkCompare';

/**
 * 作品展厅。
 *
 * 所有作品用同一套卡片，但身份严格由 caseId 决定：
 *  - 内置精选（编译期）：离线可看，带已复核的互动；
 *  - 运行期新生成：后端自动保存，三种互动由后台流水线按这件作品自己的图生成，
 *    状态通过 /cases 实时回读，构建完成后无需重启前端即可进入。
 */

const STYLE_ACCENT: Record<string, string> = {
  zhuxianzhen: '#9E241B',
  bianxiu: '#A64C54',
  songhua: '#426C62',
  qinghua: '#315F88',
  jianzhi: '#A52225',
};

type OriginFilter = 'all' | 'curated' | 'runtime';

function hasWorldAsset(experience: ReturnType<typeof experienceById.get>): boolean {
  if (!experience) return false;
  if (experience.animation.mode === 'world') return Boolean(experience.animation.world?.url);
  return experience.animation.mode === 'layered' && Boolean(experience.animation.layers?.length);
}

function interactionOf(item: GalleryCase, experience: ReturnType<typeof experienceById.get>): CaseInteraction {
  if (item.interaction) return item.interaction;
  const hasExperience = Boolean(experience);
  const hasWorld = hasWorldAsset(experience);
  return {
    status: hasExperience ? (hasWorld ? 'ready' : 'partial') : 'none',
    stages: { hotspots: hasExperience, story: hasExperience, world: hasWorld },
    hasExperience,
    hasWorld,
    experienceId: experience?.id ?? item.experienceId ?? '',
    job: null,
  };
}

const STATUS_LABEL: Record<string, string> = {
  ready: '三种互动已就绪',
  partial: '部分互动已就绪',
  queued: '互动排队中',
  processing: '互动自动构建中',
  failed: '互动构建失败',
  none: '仅保存作品',
};

export default function Gallery() {
  const navigate = useNavigate();
  const { hash } = useLocation();
  const [openCard, setOpenCard] = useState<string | null>(null);
  const [runtimeCases, setRuntimeCases] = useState<GalleryCase[]>([]);
  const [runtimeState, setRuntimeState] = useState<'loading' | 'ready' | 'offline'>('loading');
  const [originFilter, setOriginFilter] = useState<OriginFilter>('all');
  const [styleFilter, setStyleFilter] = useState<string>('all');
  const [busyCase, setBusyCase] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string>('');

  const load = useCallback(async (): Promise<GalleryCase[]> => {
    try {
      const list = await fetchRuntimeCases({ timeoutMs: 3500 });
      setRuntimeCases(list);
      setRuntimeState('ready');
      return list;
    } catch {
      setRuntimeState('offline');
      return [];
    }
  }, []);

  useEffect(() => {
    let alive = true;
    let timer: number | undefined;

    const tick = async () => {
      const list = await load();
      if (!alive) return;
      const building = list.some((item) => {
        const status = item.interaction?.status;
        return status === 'queued' || status === 'processing';
      });
      if (building) timer = window.setTimeout(tick, 4000);
    };

    void tick();
    return () => {
      alive = false;
      if (timer) window.clearTimeout(timer);
    };
  }, [load]);

  const cases = useMemo(() => {
    const merged = mergeCases([...savedCases, ...autoSavedCases], runtimeCases);
    return merged.slice().sort((a, b) => {
      const left = a.generatedAt || '';
      const right = b.generatedAt || '';
      return left < right ? 1 : left > right ? -1 : 0;
    });
  }, [runtimeCases]);

  const runtimeCount = cases.filter((item) => item.caseOrigin === 'runtime').length;

  const styles = useMemo(() => {
    const seen = new Map<string, string>();
    for (const item of cases) {
      if (item.styleId && !seen.has(item.styleId)) seen.set(item.styleId, item.styleName);
    }
    return Array.from(seen.entries());
  }, [cases]);

  const visibleCases = useMemo(
    () => cases.filter((item) => {
      if (originFilter !== 'all' && item.caseOrigin !== originFilter) return false;
      if (styleFilter !== 'all' && item.styleId !== styleFilter) return false;
      return true;
    }),
    [cases, originFilter, styleFilter],
  );

  // 从创作台的「查看《…》」跳过来时定位到对应卡片
  useEffect(() => {
    if (!hash.startsWith('#case-')) return;
    const target = document.getElementById(hash.slice(1));
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [hash, visibleCases.length]);

  const resolveExperience = (item: GalleryCase) => {
    if (item.experienceId) return experienceById.get(item.experienceId);
    if (item.caseOrigin === 'curated') return experienceByStyle.get(item.styleId);
    return undefined;
  };

  const handleRebuild = async (caseId: string) => {
    setBusyCase(caseId);
    setActionError('');
    try {
      await rebuildCaseInteractions(caseId);
      await load();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : '重新构建失败，请确认后端已启动。');
    } finally {
      setBusyCase(null);
    }
  };

  return (
    <main className="mx-auto max-w-[1240px] px-4 pb-16 pt-24 sm:px-6">
      <header className="mb-8">
        <p className="text-[11px] tracking-[0.34em] text-[color:var(--color-primary)]">
          生成即入展 · 互动自动构建 · 可进入三维展馆
        </p>
        <h1 className="mt-3 font-serif text-[clamp(1.9rem,4vw,2.8rem)] leading-tight text-[color:var(--color-ink)]">
          作品展厅
        </h1>
        <p className="mt-3 max-w-3xl text-[13.5px] leading-[1.9] text-[color:var(--color-ink)]/70">
          内置 {savedCases.length} 件精选作品，来自项目真实 Qwen Image 3.0 生成链路，互动内容经逐点复核。
          此后每次在创作台成功生成的作品都会自动保存到这里，并自动构建画中有话、一图一境与画境漫游；
          构建完成后无需重启前端，刷新或稍候即可进入。浏览与互动不会调用付费模型。
        </p>

        <div className="mt-5 flex flex-wrap gap-2 text-[11.5px] text-[color:var(--color-ink)]/55">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--color-gold)]/50 bg-white/50 px-2.5 py-1">
            <Sparkles size={12} />
            精选作品已核验
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--color-gold)]/50 bg-white/50 px-2.5 py-1">
            文化来源 {cultureSourcesVersion}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--color-gold)]/50 bg-white/50 px-2.5 py-1">
            共 {cases.length} 件
            {runtimeCount > 0 && ` · 新生成 ${runtimeCount} 件`}
            {runtimeState === 'offline' && ' · 离线'}
          </span>
        </div>
      </header>

      {runtimeState === 'offline' && (
        <p className="mb-5 rounded border border-[color:var(--color-gold)]/40 bg-white/50 px-3 py-2 text-[12px] text-[color:var(--color-ink)]/60">
          没有连上本地后端，只显示随项目内置的作品。启动后端后刷新，新生成作品会自动出现。
        </p>
      )}

      {actionError && (
        <p className="mb-5 flex items-center gap-2 rounded border border-[color:var(--color-primary)]/30 bg-[color:var(--color-primary)]/5 px-3 py-2 text-[12px] text-[color:var(--color-primary)]">
          <AlertTriangle size={14} />
          {actionError}
        </p>
      )}

      <div className="mb-6 flex flex-wrap items-center gap-x-4 gap-y-2 border-y border-[color:var(--color-gold)]/25 py-3">
        <div className="flex flex-wrap gap-1.5">
          {([
            ['all', '全部作品'],
            ['curated', '精选'],
            ['runtime', '新生成'],
          ] as const).map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => setOriginFilter(value)}
              className={`rounded-full border px-3 py-1 text-[11.5px] transition ${
                originFilter === value
                  ? 'border-[color:var(--color-primary)] bg-[color:var(--color-primary)] text-white'
                  : 'border-[color:var(--color-gold)]/50 text-[color:var(--color-ink)]/65 hover:border-[color:var(--color-primary)]'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <span className="h-4 w-px bg-[color:var(--color-gold)]/30" />
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={() => setStyleFilter('all')}
            className={`rounded-full px-2.5 py-1 text-[11.5px] transition ${
              styleFilter === 'all'
                ? 'bg-[color:var(--color-ink)] text-[color:var(--color-paper)]'
                : 'text-[color:var(--color-ink)]/55 hover:text-[color:var(--color-primary)]'
            }`}
          >
            全部风格
          </button>
          {styles.map(([id, name]) => (
            <button
              key={id}
              type="button"
              onClick={() => setStyleFilter(id)}
              className={`rounded-full px-2.5 py-1 text-[11.5px] transition ${
                styleFilter === id
                  ? 'bg-[color:var(--color-ink)] text-[color:var(--color-paper)]'
                  : 'text-[color:var(--color-ink)]/55 hover:text-[color:var(--color-primary)]'
              }`}
            >
              {name}
            </button>
          ))}
        </div>
      </div>

      {visibleCases.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[color:var(--color-gold)]/50 px-6 py-16 text-center">
          <p className="font-serif text-lg text-[color:var(--color-ink)]">这个筛选下还没有作品</p>
          <p className="mt-2 text-[12.5px] text-[color:var(--color-ink)]/55">
            换一个风格，或者去创作台生成一件新作品。
          </p>
          <Link
            to="/creator"
            className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-[color:var(--color-primary)] px-4 py-2 text-[12.5px] text-white"
          >
            去智能生成
            <ArrowRight size={13} />
          </Link>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {visibleCases.map((item) => {
            const experience = resolveExperience(item);
            const interaction = interactionOf(item, experience);
            const accent = experience?.theme.accent ?? STYLE_ACCENT[item.styleId] ?? '#9E241B';
            const experienceId = interaction.experienceId || item.experienceId || item.caseId;
            const building = interaction.status === 'queued' || interaction.status === 'processing';
            const canWander = interaction.hasWorld;
            const isRuntime = item.caseOrigin === 'runtime';
            return (
              <article
                key={item.caseId}
                id={`case-${item.caseId}`}
                className="group flex scroll-mt-24 flex-col self-start overflow-hidden rounded-xl border border-[color:var(--color-gold)]/35 bg-[#FDFBF7] shadow-[0_8px_24px_rgba(63,43,31,0.05)] transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_16px_40px_rgba(63,43,31,0.10)]"
              >
                <div className="relative p-2.5 pb-0">
                  <ArtworkCompare
                    referenceUrl={item.referenceUrl}
                    artworkUrl={item.imageUrl}
                    title={item.artworkTitle}
                    accent={accent}
                  />
                  <span
                    className={`absolute left-4 top-4 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] shadow-sm backdrop-blur ${
                      interaction.status === 'ready'
                        ? 'bg-emerald-50/90 text-emerald-800'
                        : interaction.status === 'partial'
                          ? 'bg-amber-50/90 text-amber-800'
                          : interaction.status === 'failed'
                            ? 'bg-red-50/90 text-red-700'
                            : 'bg-white/85 text-[color:var(--color-ink)]/60'
                    }`}
                  >
                    {building ? <Loader2 size={10} className="animate-spin" /> : interaction.status === 'ready' ? <CheckCircle2 size={10} /> : null}
                    {isRuntime ? '' : '精选 · '}
                    {STATUS_LABEL[interaction.status] ?? STATUS_LABEL.none}
                  </span>
                </div>

                <div className="flex flex-1 flex-col p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h2 className="truncate font-serif text-lg text-[color:var(--color-ink)]">{item.artworkTitle}</h2>
                      <p className="mt-0.5 text-[11.5px] text-[color:var(--color-ink)]/50">
                        {item.styleName}
                        {item.styleStrength ? ` · 提示强度 ${Math.round(item.styleStrength * 100)}%` : ''}
                        {item.generatedAt ? ` · ${item.generatedAt.slice(0, 10)}` : ''}
                      </p>
                    </div>
                    {experience && (
                      <span
                        className="shrink-0 rounded-full px-2 py-0.5 text-[10px]"
                        style={{ backgroundColor: `${accent}14`, color: accent }}
                      >
                        {experience.hotspots.length} 处线索
                      </span>
                    )}
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

                  <div className="mt-3.5 flex flex-wrap items-center gap-2 border-t border-[color:var(--color-gold)]/25 pt-3">
                    {interaction.hasExperience ? (
                      <>
                        <Link
                          to={`/experience/${experienceId}`}
                          className="inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-[12px] text-white transition hover:opacity-90"
                          style={{ backgroundColor: accent }}
                        >
                          画中有话
                          <ArrowRight size={13} />
                        </Link>
                        <Link
                          to={`/story/${experienceId}`}
                          className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/60 px-3 py-1.5 text-[12px] text-[color:var(--color-ink)]/75 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
                        >
                          <BookOpen size={13} />
                          一图一境
                        </Link>
                        {canWander && (
                          <Link
                            to={`/wander/${experienceId}`}
                            className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/60 px-3 py-1.5 text-[12px] text-[color:var(--color-ink)]/75 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
                          >
                            <Layers size={13} />
                            画境漫游
                          </Link>
                        )}
                      </>
                    ) : building ? (
                      <span className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/50 px-3 py-1.5 text-[12px] text-[color:var(--color-ink)]/60">
                        <Loader2 size={13} className="animate-spin" />
                        后台构建中，完成后自动出现入口
                      </span>
                    ) : null}

                    {isRuntime && !building && !canWander && (interaction.status === 'failed' || interaction.status === 'partial' || interaction.status === 'none') && (
                      <button
                        type="button"
                        onClick={() => void handleRebuild(item.caseId)}
                        disabled={busyCase === item.caseId}
                        className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/60 px-3 py-1.5 text-[12px] text-[color:var(--color-ink)]/70 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)] disabled:opacity-50"
                      >
                        {busyCase === item.caseId ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
                        {interaction.status === 'partial' ? '补全画境' : '重新构建互动'}
                      </button>
                    )}
                  </div>

                  <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[11px] text-[color:var(--color-ink)]/45">
                    <Link
                      to="/heritage-gallery"
                      className="inline-flex items-center gap-1 underline decoration-dotted underline-offset-4 transition hover:text-[color:var(--color-primary)]"
                    >
                      <Frame size={11} />
                      去纹脉展馆布展
                    </Link>
                    <button
                      type="button"
                      onClick={() => {
                        loadSavedCase(item);
                        navigate('/products');
                      }}
                      className="underline decoration-dotted underline-offset-4 transition hover:text-[color:var(--color-primary)]"
                    >
                      文创预览
                    </button>
                    <button
                      type="button"
                      onClick={() => setOpenCard(openCard === item.caseId ? null : item.caseId)}
                      className="underline decoration-dotted underline-offset-4 transition hover:text-[color:var(--color-primary)]"
                      aria-expanded={openCard === item.caseId}
                    >
                      {openCard === item.caseId ? '收起文化卡' : '展开文化卡'}
                    </button>
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
      )}

      <section className="mt-10 rounded-lg border border-[color:var(--color-gold)]/40 bg-white/45 p-5 sm:p-6">
        <h2 className="font-serif text-lg text-[color:var(--color-ink)]">这些互动是怎么来的</h2>
        <ul className="mt-3 grid gap-2 text-[12.5px] leading-relaxed text-[color:var(--color-ink)]/65 sm:grid-cols-2">
          <li>· 新作品生成成功后先保存原图、参考图、参数与文化卡，再进入本展厅。</li>
          <li>· 后台流水线对这张作品自己的图估计深度、选热点、写三折叙事并烘焙画境资产。</li>
          <li>· 内置作品的热点经逐点裁切复核；自动构建的热点标记为「约定位」，不冒充人工复核。</li>
          <li>· 构建失败或只完成一部分时会显示状态，并提供「重新构建互动 / 补全画境」。</li>
          <li>· 所有图片、热点、章节、画境、文化卡与展馆挂画都绑定同一个 caseId，不会跨作品借用。</li>
          <li>· 静态 GitHub Pages 只提供随仓库内置的作品；运行期生成需要本地后端。</li>
        </ul>
      </section>
    </main>
  );
}