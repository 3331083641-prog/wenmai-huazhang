/**
 * 作品详情：像展签，不是普通弹窗。
 *
 * 内容全部来自项目里已有的作品元数据（metadata.json 的 visionAnalysis），
 * 不新编文案，也不做无法核实的断言。
 */

import { useEffect } from 'react';
import { X, BookOpen, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { findArtwork } from '../../../data/artworkRegistry';
import { experienceByStyle } from '../../../data/experiences';

interface ArtworkDetailProps {
  artworkId: string | null;
  onClose: () => void;
}

export function ArtworkDetail({ artworkId, onClose }: ArtworkDetailProps) {
  const artwork = findArtwork(artworkId ?? undefined);
  // 精选作品按风格对应已核验的体验；运行期作品必须用自己的 caseId，
  // 绝不能拿同风格的旧体验来冒充这件新作品。
  const experience = artwork && artwork.origin === 'curated'
    ? experienceByStyle.get(artwork.styleId)
    : undefined;
  const experienceHref = experience?.id ?? artwork?.id ?? '';

  useEffect(() => {
    if (!artworkId) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [artworkId, onClose]);

  if (!artwork) return null;

  return (
    <div className="pointer-events-auto absolute inset-x-0 bottom-0 z-40 mx-auto w-[min(94vw,720px)] px-3 pb-3">
      <div className="chinese-border overflow-hidden rounded-lg border border-[color:var(--color-gold)]/50 bg-[#FBF6EB]/96 shadow-[0_18px_50px_rgba(63,43,31,0.22)] backdrop-blur-md">
        <div className="flex items-start justify-between gap-3 border-b border-[color:var(--color-gold)]/30 px-4 py-3">
          <div className="min-w-0">
            <p className="text-[10px] tracking-[0.28em]" style={{ color: artwork.accent }}>
              {artwork.styleName} · 展签
            </p>
            <h2 className="mt-1 font-serif text-lg text-[color:var(--color-ink)]">{artwork.title}</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭详情"
            className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[color:var(--color-ink)]/45 transition hover:bg-black/5"
          >
            <X size={15} />
          </button>
        </div>

        <div className="grid gap-3 p-4 sm:grid-cols-[132px_1fr]">
          <img
            src={artwork.imageUrl}
            alt={artwork.title}
            className="h-[132px] w-[132px] rounded object-cover shadow-sm"
            style={{ boxShadow: `0 0 0 1px ${artwork.accent}33` }}
          />

          <div className="min-w-0 space-y-2.5">
            <section>
              <h3 className="text-[10.5px] tracking-[0.2em] text-[color:var(--color-ink)]/40">文化解读</h3>
              <p className="mt-1 text-[12px] leading-relaxed text-[color:var(--color-ink)]/75">{artwork.summary}</p>
            </section>

            {artwork.features.length > 0 && (
              <section>
                <h3 className="text-[10.5px] tracking-[0.2em] text-[color:var(--color-ink)]/40">视觉特征</h3>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {artwork.features.map((feature) => (
                    <span
                      key={feature}
                      className="rounded border border-[color:var(--color-gold)]/45 px-1.5 py-0.5 text-[10.5px] text-[color:var(--color-ink)]/60"
                    >
                      {feature}
                    </span>
                  ))}
                </div>
              </section>
            )}

            <section className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10.5px] text-[color:var(--color-ink)]/45">
              <span>生成于 {artwork.generatedAt.slice(0, 10)}</span>
              <span>{artwork.origin === 'curated' ? '随项目提交的精选作品' : '运行期自动保存'}</span>
            </section>
          </div>
        </div>

        {/* 与既有互动体验联动，不重复造内容 */}
        <div className="flex flex-wrap items-center gap-2 border-t border-[color:var(--color-gold)]/30 px-4 py-3">
          {(experience || artwork.origin === 'runtime') ? (
            <>
              <Link
                to={`/experience/${experienceHref}`}
                className="inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-[11.5px] text-white transition hover:opacity-90"
                style={{ backgroundColor: artwork.accent }}
              >
                {experience ? '进入互动画境' : '打开这件作品的互动'}
                <ArrowRight size={12} />
              </Link>
              <Link
                to={`/story/${experienceHref}`}
                className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/55 px-3 py-1.5 text-[11.5px] text-[color:var(--color-ink)]/70 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
              >
                <BookOpen size={12} />
                一图一境
              </Link>
            </>
          ) : (
            <span className="text-[11px] text-[color:var(--color-ink)]/40">
              这件作品还没有可用的互动解读。
            </span>
          )}
          <Link
            to="/gallery"
            className="ml-auto text-[11px] text-[color:var(--color-ink)]/45 underline decoration-dotted underline-offset-4 transition hover:text-[color:var(--color-primary)]"
          >
            在展厅中查看
          </Link>
        </div>
      </div>
    </div>
  );
}
