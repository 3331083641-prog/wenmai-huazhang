import { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
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
  ShieldCheck,
  X,
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
  const [showArchiveCert, setShowArchiveCert] = useState(false);
  const casketTriggerRef = useRef<HTMLButtonElement | null>(null);
  const prevShowArchiveCert = useRef(showArchiveCert);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowArchiveCert(false);
    };
    if (showArchiveCert) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showArchiveCert]);

  useEffect(() => {
    if (prevShowArchiveCert.current && !showArchiveCert) {
      casketTriggerRef.current?.focus();
    }
    prevShowArchiveCert.current = showArchiveCert;
  }, [showArchiveCert]);

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
      <header className="mb-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-[color:var(--color-gold)]/40 bg-white/70 shadow-xs mb-3">
            <Sparkles size={13} className="text-gold" />
            <span className="text-xs font-serif font-medium text-[color:var(--color-primary)] tracking-widest">
              观其形 · 知其意 · 入其境
            </span>
          </div>
          <h1 className="font-serif text-[clamp(2.1rem,4.5vw,3rem)] font-bold leading-tight text-[color:var(--color-ink)]">
            数字非遗典藏展厅
          </h1>
          <p className="mt-3 max-w-2xl text-sm sm:text-base leading-relaxed text-[color:var(--color-ink)]/75 font-sans">
            成图即自动落盘入展，并由后台流水线自动化构建多维互动体验，亦可一键通往三维展馆进行空间策展。
          </p>

          <div className="mt-5 flex flex-wrap gap-2.5 text-xs text-[color:var(--color-ink)]/65 font-serif">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--color-gold)]/50 bg-white/70 px-3 py-1 shadow-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
              精选典藏已逐项核验
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--color-gold)]/50 bg-white/70 px-3 py-1 shadow-xs">
              文化考据体系 {cultureSourcesVersion}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--color-gold)]/50 bg-white/70 px-3 py-1 shadow-xs">
              已展出 {cases.length} 件作品
              {runtimeCount > 0 && ` · 新生成 ${runtimeCount} 件`}
              {runtimeState === 'offline' && ' · 离线模式'}
            </span>
          </div>
        </div>

        {/* 金石百宝匣 · 数字存证徽章 (GPT Image 2 真实视觉资产) */}
        <motion.button
          ref={casketTriggerRef}
          type="button"
          className="relative w-40 sm:w-48 aspect-[3/2] cursor-pointer shrink-0 self-center md:self-auto group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold rounded-2xl bg-transparent border-0 p-0 text-left"
          animate={{ y: [-3, 3] }}
          transition={{ duration: 4.8, repeat: Infinity, ease: 'easeInOut' }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => setShowArchiveCert(true)}
          title="点击查看数字典藏与数据完整性机制说明"
          aria-haspopup="dialog"
          aria-expanded={showArchiveCert}
        >
          <picture>
            <source
              type="image/webp"
              srcSet={import.meta.env.BASE_URL + "visuals/vnext/ui-img-04-archive-casket.webp"}
            />
            <img
              src={import.meta.env.BASE_URL + "visuals/vnext/ui-img-04-archive-casket.png"}
              alt="古籍卷轴式立体书香金石印匣"
              className="w-full h-full object-contain drop-shadow-[0_12px_24px_rgba(70,42,30,0.18)]"
            />
          </picture>
          <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 bg-white/95 border border-gold/40 shadow-xs px-2.5 py-0.5 rounded-full text-[10px] font-serif text-primary whitespace-nowrap opacity-90 group-hover:opacity-100 flex items-center gap-1 pointer-events-none">
            <ShieldCheck size={11} className="text-gold" />
            <span>数字典藏机制</span>
          </div>
        </motion.button>
      </header>

      {/* 典藏印匣弹窗 */}
      <AnimatePresence>
        {showArchiveCert && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowArchiveCert(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 16 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 16 }}
              transition={{ duration: 0.3 }}
              role="dialog"
              aria-modal="true"
              aria-labelledby="archive-cert-title"
              className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto scrollbar-thin bg-[#FCF8F2] border-2 border-gold/50 rounded-3xl p-6 sm:p-7 shadow-2xl z-10 font-serif"
            >
              <div className="flex items-center justify-between pb-3 border-b border-gold/30 mb-4">
                <div className="flex items-center gap-2">
                  <span className="chinese-seal text-[10px]">典藏</span>
                  <span id="archive-cert-title" className="text-base font-bold text-ink">作品归档与数据完整性机制说明</span>
                </div>
                <button
                  type="button"
                  onClick={() => setShowArchiveCert(false)}
                  aria-label="关闭数字典藏机制说明"
                  className="w-8 h-8 rounded-full border border-gold/30 bg-white flex items-center justify-center text-ink/60 hover:text-primary transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold"
                >
                  <X size={15} />
                </button>
              </div>

              <div className="flex items-center gap-4 p-3.5 rounded-xl bg-white/80 border border-gold/30 mb-4">
                <img
                  src={import.meta.env.BASE_URL + "visuals/vnext/ui-img-04-archive-casket.png"}
                  alt=""
                  className="w-20 h-14 object-contain shrink-0"
                />
                <div className="text-xs text-ink/75 leading-relaxed font-sans">
                  本展厅作品遵循本地持久化存储规范（Case Store），记录作品参考图、生成参数与文化说明卡。通过 SHA-256 计算作品元数据哈希摘要，用于本地文件防篡改完整性校验与版本追溯。
                </div>
              </div>

              <div className="space-y-2 text-xs font-sans text-ink/80 mb-5">
                <div className="p-2.5 rounded-lg bg-paper border border-gold/25 flex items-center justify-between">
                  <span className="font-serif">数据校验机制</span>
                  <span className="font-mono text-emerald-800 font-bold">SHA-256 数据完整性摘要</span>
                </div>
                <div className="p-2.5 rounded-lg bg-paper border border-gold/25 flex items-center justify-between">
                  <span className="font-serif">作品归档存储</span>
                  <span className="font-mono text-ink/70">Local Case Store 持久化规范</span>
                </div>
                <div className="p-2.5 rounded-lg bg-paper border border-gold/25 flex items-center justify-between">
                  <span className="font-serif">离线运行状态</span>
                  <span className="text-ink/80">内置 5 件精选支持离线浏览，新作品需本地服务</span>
                </div>
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => setShowArchiveCert(false)}
                  className="px-5 py-2 rounded-xl btn-chinese text-xs font-serif cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold"
                >
                  我知道了
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

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
                  {item.qualityReview && item.qualityReview.status!=='disabled' && (
                    <p className="mb-2 text-xs text-[color:var(--color-ink)]/65" role="status">
                      {item.qualityReview.status==='approved'?'画境视觉复审通过':
                        item.qualityReview.status==='needs_review'?'画境仍有待完善项':'画境视觉复审未完成'}
                      {item.qualityReview.rounds>0?` · ${item.qualityReview.rounds} 轮`:''}
                    </p>
                  )}
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
