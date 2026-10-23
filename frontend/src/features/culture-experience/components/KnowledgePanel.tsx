import { Link } from 'react-router-dom';
import { AnimatePresence, motion } from 'motion/react';
import { ChevronLeft, ChevronRight, Link2, X } from 'lucide-react';
import type { CultureExperience, CultureHotspot } from '../types';
import SourceChips from './SourceChips';

interface KnowledgePanelProps {
  experience: CultureExperience;
  active: CultureHotspot | null;
  activeIndex: number;
  reducedMotion: boolean;
  onSelect: (id: string) => void;
  onClose: () => void;
  onPrev: () => void;
  onNext: () => void;
}

const locationLabel: Record<CultureHotspot['locationStatus'], string> = {
  verified: '位置已逐点复核',
  approximate: '位置为约定位',
  unverified: '位置未核验',
};

/**
 * 知识面板：先给画面观察，再给文化解读，最后给来源。
 * 这三段刻意分开——「我看到的」和「我知道的」不能在排版里混成一段。
 */
export function KnowledgePanel({
  experience,
  active,
  activeIndex,
  reducedMotion,
  onSelect,
  onClose,
  onPrev,
  onNext,
}: KnowledgePanelProps) {
  const total = experience.hotspots.length;
  const duration = reducedMotion ? 0 : 0.28;

  return (
    <aside
      className="relative flex h-full flex-col overflow-hidden rounded-lg border border-[color:var(--color-gold)]/45 bg-[#FDFBF7] shadow-[0_10px_30px_rgba(63,43,31,0.06)]"
      aria-label="文化解读面板"
    >
      <div
        className="h-1 w-full shrink-0"
        style={{ background: `linear-gradient(90deg, ${experience.theme.accent} 0%, ${experience.theme.gold} 45%, transparent 100%)` }}
        aria-hidden="true"
      />

      <div className="flex items-center justify-between gap-3 border-b border-[color:var(--color-gold)]/25 px-4 py-3">
        <div className="min-w-0">
          <p className="truncate text-[11px] tracking-[0.22em] text-[color:var(--color-ink)]/50">
            {experience.styleName}
          </p>
          <p className="truncate font-serif text-sm text-[color:var(--color-ink)]">
            {active ? `${activeIndex + 1} / ${total} · ${active.kicker}` : `共 ${total} 处线索`}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            onClick={onPrev}
            className="rounded-full p-1.5 text-[color:var(--color-ink)]/55 transition hover:bg-black/5 hover:text-[color:var(--color-primary)] disabled:opacity-30"
            aria-label="上一处线索"
            disabled={total === 0}
          >
            <ChevronLeft size={17} />
          </button>
          <button
            type="button"
            onClick={onNext}
            className="rounded-full p-1.5 text-[color:var(--color-ink)]/55 transition hover:bg-black/5 hover:text-[color:var(--color-primary)] disabled:opacity-30"
            aria-label="下一处线索"
            disabled={total === 0}
          >
            <ChevronRight size={17} />
          </button>
          <button
            type="button"
            onClick={onClose}
            className="ml-1 rounded-full p-1.5 text-[color:var(--color-ink)]/55 transition hover:bg-black/5 hover:text-[color:var(--color-primary)]"
            aria-label="收起解读，回到完整画面"
          >
            <X size={17} />
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
        <AnimatePresence mode="wait" initial={false}>
          {active ? (
            <motion.div
              key={active.id}
              initial={{ opacity: 0, y: reducedMotion ? 0 : 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: reducedMotion ? 0 : -6 }}
              transition={{ duration, ease: [0.22, 0.61, 0.36, 1] }}
            >
              <h2 className="mb-1 font-serif text-xl text-[color:var(--color-ink)]">{active.title}</h2>
              <p className="mb-4 text-[13px] leading-relaxed text-[color:var(--color-ink)]/65">
                {active.shortDescription}
              </p>

              <section className="mb-4">
                <h3 className="mb-1.5 flex items-center gap-2 text-[11px] font-medium tracking-[0.18em] text-[color:var(--color-ink)]/45">
                  <span className="h-px w-4 bg-[color:var(--color-gold)]" aria-hidden="true" />
                  画面观察
                </h3>
                <p className="text-[13.5px] leading-[1.85] text-[color:var(--color-ink)]/85">{active.visualObservation}</p>
              </section>

              <section className="mb-4 rounded border-l-2 bg-white/70 px-3 py-2.5" style={{ borderColor: experience.theme.accent }}>
                <h3 className="mb-1.5 flex items-center gap-2 text-[11px] font-medium tracking-[0.18em] text-[color:var(--color-ink)]/45">
                  <span className="h-px w-4 bg-[color:var(--color-gold)]" aria-hidden="true" />
                  文化解读
                </h3>
                <p className="text-[13.5px] leading-[1.9] text-[color:var(--color-ink)]/90">{active.culturalExplanation}</p>
              </section>

              <div className="mb-3 flex items-center gap-2 text-[11px] text-[color:var(--color-ink)]/45">
                <Link2 size={12} aria-hidden="true" />
                <span>{locationLabel[active.locationStatus]}</span>
                {active.reviewStatus === 'pending' && (
                  <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] text-amber-800">待复核</span>
                )}
              </div>

              <SourceChips sourceIds={active.sourceIds} />

              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={onNext}
                  className="inline-flex flex-1 items-center justify-center gap-1.5 rounded border border-[color:var(--color-gold)]/60 px-3 py-2 text-xs text-[color:var(--color-ink)]/75 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
                >
                  继续看下一处
                  <ChevronRight size={14} />
                </button>
                {active.relatedChapterId && (
                  <Link
                    to={`/story/${experience.id}#${active.relatedChapterId}`}
                    className="inline-flex items-center justify-center rounded px-3 py-2 text-xs text-white transition hover:opacity-90"
                    style={{ backgroundColor: experience.theme.accent }}
                  >
                    在故事里看
                  </Link>
                )}
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="index"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration }}
            >
              <p className="mb-1 font-serif text-base text-[color:var(--color-ink)]">从任意一处开始</p>
              <p className="mb-4 text-[12.5px] leading-relaxed text-[color:var(--color-ink)]/60">
                点击画面上的编号，或从下面选一处。每一处都先告诉你「画面里有什么」，再说「它为什么这样」。
              </p>
              <ol className="space-y-1.5">
                {experience.hotspots.map((hotspot, index) => (
                  <li key={hotspot.id}>
                    <button
                      type="button"
                      onClick={() => onSelect(hotspot.id)}
                      className="group flex w-full items-start gap-2.5 rounded px-2 py-2 text-left transition hover:bg-[color:var(--color-primary)]/5"
                    >
                      <span
                        className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[11px] text-[color:var(--color-ink)]/60 transition group-hover:border-transparent group-hover:text-white"
                        style={{ borderColor: 'rgba(63,43,31,0.25)' }}
                      >
                        {index + 1}
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate font-serif text-[13.5px] text-[color:var(--color-ink)]">
                          {hotspot.title}
                        </span>
                        <span className="block truncate text-[11.5px] text-[color:var(--color-ink)]/50">
                          {hotspot.shortDescription}
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ol>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="shrink-0 border-t border-[color:var(--color-gold)]/25 px-4 py-2.5 text-[11px] leading-relaxed text-[color:var(--color-ink)]/45">
        {experience.animation.capabilityNote}
      </div>
    </aside>
  );
}

export default KnowledgePanel;