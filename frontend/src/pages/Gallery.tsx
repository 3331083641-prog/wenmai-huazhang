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
  Trash2,
} from 'lucide-react';
import { autoSavedCases, savedCases, loadSavedCase } from '../data/savedCases';
import { experienceById, experienceByStyle, cultureSourcesVersion } from '../data/experiences';
import {
  fetchRuntimeCases,
  mergeCases,
  rebuildCaseInteractions,
  deleteRuntimeCase,
  type CaseInteraction,
  type GalleryCase,
} from '../services/caseService';
import CultureCard from '../components/creator/CultureCard';
import ArtworkCompare from '../features/culture-experience/components/ArtworkCompare';
import { clearRuntimeExperience } from '../data/runtimeExperiences';
import { deletedCaseIds, markCaseDeleted, DELETED_CASES_KEY } from '../services/deletedCases';
import { forgetRuntimeArtwork, refreshGalleryPool } from '../data/galleryPool';
import { useCurationStore } from '../features/heritage-gallery/state/curationStore';

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
  const [deletedIds, setDeletedIds] = useState(deletedCaseIds);
  const [deletingCase, setDeletingCase] = useState<string | null>(null);

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

  const hasActiveBuild = runtimeCases.some((item) =>
    item.interaction?.status === 'queued' || item.interaction?.status === 'processing');

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
      if (!import.meta.env.VITE_STATIC_SHOWCASE || import.meta.env.VITE_STATIC_SHOWCASE !== 'true') {
        timer = window.setTimeout(tick, building ? 2000 : 8000);
      }
    };
    const refresh = () => { if (!document.hidden) void load(); };
    const onStorage = (event: StorageEvent) => {
      if (event.key === 'wenmai_latest_result') refresh();
      if (event.key === DELETED_CASES_KEY) { setDeletedIds(deletedCaseIds()); refresh(); }
    };

    void tick();
    window.addEventListener('focus', refresh);
    window.addEventListener('storage', onStorage);
    return () => {
      alive = false;
      if (timer) window.clearTimeout(timer);
      window.removeEventListener('focus', refresh);
      window.removeEventListener('storage', onStorage);
    };
  }, [load, hasActiveBuild]);

  const cases = useMemo(() => {
    const base = runtimeState === 'ready' ? savedCases : [...savedCases, ...autoSavedCases];
    const merged = mergeCases(base, runtimeCases);
    return merged.filter(item => !deletedIds.has(item.caseId)).sort((a, b) => {
      const left = a.generatedAt || '';
      const right = b.generatedAt || '';
      return left < right ? 1 : left > right ? -1 : 0;
    });
  }, [runtimeCases, runtimeState, deletedIds]);

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
      clearRuntimeExperience(caseId);
      await rebuildCaseInteractions(caseId);
      await load();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : '重新构建失败，请确认后端已启动。');
    } finally {
      setBusyCase(null);
    }
  };

  const handleDelete = async (item: GalleryCase) => {
    if (item.caseOrigin !== 'runtime' || deletingCase) return;
    if (!window.confirm(`删除《${item.artworkTitle}》？该作品及对应的三种互动将从展厅移除。`)) return;
    setDeletingCase(item.caseId); setActionError('');
    try {
      await deleteRuntimeCase(item.caseId);
      setDeletedIds(markCaseDeleted(item.caseId));
      clearRuntimeExperience(item.caseId);
      forgetRuntimeArtwork(item.caseId);
      const curation = useCurationStore.getState();
      for (const [frameId, artworkId] of Object.entries(curation.assignments)) {
        if (artworkId === item.caseId) curation.clearFrame(frameId);
      }
      setRuntimeCases(current => current.filter(entry => entry.caseId !== item.caseId));
      if (openCard === item.caseId) setOpenCard(null);
      await load();
      void refreshGalleryPool();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : '删除失败，请稍后重试。');
    } finally { setDeletingCase(null); }
  };

  return (
    <main className="mx-auto max-w-[1240px] px-4 pb-20 pt-24 sm:px-6">
      <header className="mb-10">
        <p className="text-xs font-medium tracking-[0.3em] text-[color:var(--color-primary)]">
          生成即入展 · 互动自动构建 · 可进入三维展馆
        </p>
        <h1 className="mt-3 font-serif text-[clamp(2.1rem,4.5vw,3rem)] font-bold leading-tight text-[color:var(--color-ink)]">
          作品展厅
        </h1>
        <p className="mt-3 max-w-3xl text-sm sm:text-base leading-relaxed text-[color:var(--color-ink)]/75 font-sans">
          内置 {savedCases.length} 件精选作品，来自项目真实 Qwen Image 3.0 生成链路，互动内容经逐点复核。
          此后每次在创作台成功生成的作品都会自动保存到这里，并自动构建画中有话、一图一境与画境漫游；
          构建完成后无需重启前端，刷新或稍候即可进入。浏览与多维深度互动不会调用付费模型。
        </p>

        <div className="mt-5 flex flex-wrap gap-2.5 text-xs text-[color:var(--color-ink)]/65 font-serif">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--color-gold)]/50 bg-white/70 px-3 py-1 shadow-xs">
            <Sparkles size={13} className="text-gold" />
            精选作品已逐项核验
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--color-gold)]/50 bg-white/70 px-3 py-1 shadow-xs">
            文化来源 {cultureSourcesVersion}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--color-gold)]/50 bg-white/70 px-3 py-1 shadow-xs">
            共 {cases.length} 件作品
            {runtimeCount > 0 && ` · 新生成 ${runtimeCount} 件`}
            {runtimeState === 'offline' && ' · 离线模式'}
          </span>
        </div>
      </header>

      {runtimeState === 'offline' && (
        <p className="mb-6 rounded-xl border border-[color:var(--color-gold)]/40 bg-white/70 px-4 py-2.5 text-xs text-[color:var(--color-ink)]/70">
          没有连上本地后端，只显示随项目内置的作品。启动后端后刷新，新生成作品会自动出现。
        </p>
      )}

      {actionError && (
        <p className="mb-6 flex items-center gap-2 rounded-xl border border-[color:var(--color-primary)]/30 bg-[color:var(--color-primary)]/5 px-4 py-2.5 text-xs text-[color:var(--color-primary)]">
          <AlertTriangle size={15} />
          {actionError}
        </p>
      )}

      {/* 筛选与分类工具栏 */}
      <div className="mb-8 flex flex-wrap items-center gap-x-5 gap-y-3 border-y border-[color:var(--color-gold)]/30 py-3.5">
        <div className="flex flex-wrap gap-2">
          {([
            ['all', '全部作品'],
            ['curated', '精选作品'],
            ['runtime', '新生成'],
          ] as const).map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => setOriginFilter(value)}
              className={`rounded-full border px-4 py-1.5 text-xs sm:text-sm font-serif transition ${
                originFilter === value
                  ? 'border-[color:var(--color-primary)] bg-[color:var(--color-primary)] text-white shadow-xs'
                  : 'border-[color:var(--color-gold)]/50 bg-white/60 text-[color:var(--color-ink)]/70 hover:border-[color:var(--color-primary)] hover:text-primary'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <span className="h-4 w-px bg-[color:var(--color-gold)]/40" />
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setStyleFilter('all')}
            className={`rounded-full px-3.5 py-1.5 text-xs sm:text-sm font-serif transition ${
              styleFilter === 'all'
                ? 'bg-[color:var(--color-ink)] text-[color:var(--color-paper)] shadow-xs'
                : 'text-[color:var(--color-ink)]/65 hover:text-[color:var(--color-primary)] bg-white/40'
            }`}
          >
            全部风格
          </button>
          {styles.map(([id, name]) => (
            <button
              key={id}
              type="button"
              onClick={() => setStyleFilter(id)}
              className={`rounded-full px-3.5 py-1.5 text-xs sm:text-sm font-serif transition ${
                styleFilter === id
                  ? 'bg-[color:var(--color-ink)] text-[color:var(--color-paper)] shadow-xs'
                  : 'text-[color:var(--color-ink)]/65 hover:text-[color:var(--color-primary)] bg-white/40'
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
                className="group flex scroll-mt-24 flex-col self-start overflow-hidden rounded-2xl border border-[color:var(--color-gold)]/40 bg-[#FAF8F5] shadow-[0_8px_24px_rgba(63,43,31,0.06)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_20px_48px_rgba(63,43,31,0.12)] hover:border-[color:var(--color-primary)]/40"
              >
                <div className="relative p-3 pb-0">
                  <ArtworkCompare
                    referenceUrl={item.referenceUrl}
                    artworkUrl={item.imageUrl}
                    title={item.artworkTitle}
                    accent={accent}
                  />
                  {isRuntime && (
                    <div className="flex justify-end px-1 pb-1 pt-2">
                      <button type="button" aria-label={`删除作品《${item.artworkTitle}》`}
                        onClick={() => void handleDelete(item)}
                        disabled={building || deletingCase !== null || runtimeState !== 'ready'}
                        title={building ? '互动构建完成后可删除' : runtimeState !== 'ready' ? '连接本地后端后可删除' : '删除这件作品及对应互动'}
                        className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-red-700/75 transition hover:bg-red-50 hover:text-red-800 disabled:cursor-not-allowed disabled:opacity-40">
                        {deletingCase === item.caseId ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                        {deletingCase === item.caseId ? '删除中…' : '删除作品'}
                      </button>
                    </div>
                  )}

                  {/* 仅在后台正在构建或明确构建失败时显示低干扰状态提示；已就绪的精选作品与常规作品不盖角标 */}
                  {(building || interaction.status === 'failed') && (
                    <span
                      className={`absolute left-5 top-5 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs shadow-md backdrop-blur ${
                        building
                          ? 'bg-black/65 text-white'
                          : 'bg-red-600/85 text-white'
                      }`}
                    >
                      {building && <Loader2 size={11} className="animate-spin text-gold" />}
                      {STATUS_LABEL[interaction.status] ?? '状态更新中'}
                    </span>
                  )}
                </div>

                <div className="flex flex-1 flex-col p-5">
                  <div className="flex items-start justify-between gap-2.5">
                    <div className="min-w-0">
                      <h2 className="truncate font-serif text-xl sm:text-2xl font-bold text-[color:var(--color-ink)] group-hover:text-[color:var(--color-primary)] transition-colors">
                        {item.artworkTitle}
                      </h2>
                      <p className="mt-1 text-xs sm:text-[13px] text-[color:var(--color-ink)]/60 font-serif">
                        {item.styleName}
                        {item.styleStrength ? ` · 提示强度 ${Math.round(item.styleStrength * 100)}%` : ''}
                        {item.generatedAt ? ` · ${item.generatedAt.slice(0, 10)}` : ''}
                      </p>
                    </div>
                    {experience && (
                      <span
                        className="shrink-0 rounded-full px-2.5 py-1 text-xs font-serif font-medium shadow-2xs"
                        style={{ backgroundColor: `${accent}18`, color: accent }}
                      >
                        {experience.hotspots.length} 处解读
                      </span>
                    )}
                  </div>

                  <p className="mt-3 line-clamp-2 text-xs sm:text-[13.5px] leading-relaxed text-[color:var(--color-ink)]/75 font-sans">
                    {item.visionAnalysis.culture_interpretation || item.visionAnalysis.theme_summary || '暂无文化解读。'}
                  </p>

                  <div className="mt-3.5 flex flex-wrap gap-1.5">
                    {item.visionAnalysis.visual_features.slice(0, 3).map((feature) => (
                      <span
                        key={feature}
                        className="rounded-md border border-[color:var(--color-gold)]/40 px-2 py-0.5 text-xs font-serif text-[color:var(--color-ink)]/65 bg-white/60"
                      >
                        {feature}
                      </span>
                    ))}
                  </div>

                  {/* 核心互动入口操作区 */}
                  <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-[color:var(--color-gold)]/30 pt-3.5">
                    {interaction.hasExperience ? (
                      <>
                        <Link
                          to={`/experience/${experienceId}`}
                          className="inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs sm:text-sm font-serif font-medium text-white transition hover:opacity-90 shadow-xs hover:shadow-md"
                          style={{ backgroundColor: accent }}
                        >
                          画中有话
                          <ArrowRight size={14} />
                        </Link>
                        <Link
                          to={`/story/${experienceId}`}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-[color:var(--color-gold)]/60 px-3.5 py-2 text-xs sm:text-sm font-serif font-medium text-[color:var(--color-ink)]/80 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)] bg-white/70 shadow-xs"
                        >
                          <BookOpen size={14} />
                          一图一境
                        </Link>
                        {canWander && (
                          <Link
                            to={`/wander/${experienceId}`}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-[color:var(--color-gold)]/60 px-3.5 py-2 text-xs sm:text-sm font-serif font-medium text-[color:var(--color-ink)]/80 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)] bg-white/70 shadow-xs"
                          >
                            <Layers size={14} />
                            画境漫游
                          </Link>
                        )}
                      </>
                    ) : building ? (
                      <span className="inline-flex items-center gap-1.5 rounded-lg border border-[color:var(--color-gold)]/50 px-3.5 py-2 text-xs text-[color:var(--color-ink)]/65 bg-white/50">
                        <Loader2 size={13} className="animate-spin text-gold" />
                        后台构建中，完成后自动出现入口
                      </span>
                    ) : null}

                    {isRuntime && !building && !canWander && (interaction.status === 'failed' || interaction.status === 'partial' || interaction.status === 'none') && (
                      <button
                        type="button"
                        onClick={() => void handleRebuild(item.caseId)}
                        disabled={busyCase === item.caseId}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-[color:var(--color-gold)]/60 px-3 py-2 text-xs font-serif text-[color:var(--color-ink)]/75 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)] disabled:opacity-50 bg-white"
                      >
                        {busyCase === item.caseId ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
                        {interaction.status === 'partial' ? '补全画境' : '重新构建互动'}
                      </button>
                    )}
                  </div>

                  {/* 辅助操作与抽屉触发 */}
                  <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs font-serif text-[color:var(--color-ink)]/60">
                    <Link
                      to="/heritage-gallery"
                      className="inline-flex items-center gap-1 underline decoration-dotted underline-offset-4 transition hover:text-[color:var(--color-primary)]"
                    >
                      <Frame size={12} />
                      去纹脉展馆布展
                    </Link>
                    <button
                      type="button"
                      onClick={() => {
                        loadSavedCase(item);
                        navigate('/products');
                      }}
                      className="inline-flex items-center gap-1 underline decoration-dotted underline-offset-4 transition hover:text-[color:var(--color-primary)]"
                    >
                      文创打样预览
                    </button>
                    <button
                      type="button"
                      onClick={() => setOpenCard(openCard === item.caseId ? null : item.caseId)}
                      className="underline decoration-dotted underline-offset-4 transition hover:text-[color:var(--color-primary)] ml-auto"
                      aria-expanded={openCard === item.caseId}
                    >
                      {openCard === item.caseId ? '收起文化说明卡 ↑' : '展开文化说明卡 ↓'}
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
