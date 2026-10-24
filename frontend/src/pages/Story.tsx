import { Link } from 'react-router-dom';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import { ArrowLeft, ArrowRight, BookOpen, Check, Compass, Copy, Download, Image as ImageIcon } from 'lucide-react';
import { experiences } from '../data/experiences';
import { useExperience } from '../hooks/useExperience';
import type { CultureExperience } from '../features/culture-experience/types';
import { useContainedImage } from '../features/culture-experience/hooks/useContainedImage';
import SourceChips from '../features/culture-experience/components/SourceChips';
import ExperienceErrorBoundary from '../features/culture-experience/components/ExperienceErrorBoundary';
import { ExperienceModeSwitch, hasWanderMode } from '../features/culture-experience/components/ExperienceModeSwitch';

/** 章节镜头：把焦点放在容器中心（与 CSS translate → scale 的顺序一致）。 */
function cameraTransform(scale: number, focusX: number, focusY: number): string {
  return `translate(${(0.5 - focusX) * scale * 100}%, ${(0.5 - focusY) * scale * 100}%) scale(${scale})`;
}

/** /story/:id —— 「一图一境」互动故事页。滚动驱动镜头，但不劫持滚动。 */
function StoryContent({ experience }: { experience: CultureExperience }) {
  const { hash } = useLocation();
  const [activeChapter, setActiveChapter] = useState(experience.chapters[0]?.id ?? '');
  const [copied, setCopied] = useState(false);
  const prefersReduced = useReducedMotion();
  const reducedMotion = Boolean(prefersReduced);

  const { containerRef, imageBox } = useContainedImage(experience.artworkSize);
  const chapterRefs = useRef(new Map<string, HTMLElement | null>());

  const chapter = useMemo(
    () => experience.chapters.find((item) => item.id === activeChapter) ?? experience.chapters[0],
    [activeChapter, experience.chapters]
  );

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        const id = visible?.target.getAttribute('data-chapter-id');
        if (id) setActiveChapter(id);
      },
      { rootMargin: '-38% 0px -38% 0px', threshold: [0.05, 0.3, 0.6, 0.95] }
    );
    chapterRefs.current.forEach((element) => element && observer.observe(element));
    return () => observer.disconnect();
  }, [experience.chapters]);

  const scrollToChapter = useCallback((id: string) => {
    const element = chapterRefs.current.get(id);
    element?.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'center' });
  }, [reducedMotion]);

  useEffect(() => {
    const id = hash.slice(1);
    if (!id) return;
    const chapter = experience.chapters.find((item) => item.id === id || `chapter-${item.index}` === id);
    if (chapter) scrollToChapter(chapter.id);
  }, [hash, experience.chapters, scrollToChapter]);

  const copyLink = async () => {
    const url = window.location.href;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2200);
    } catch {
      window.prompt('复制这个地址：', url);
    }
  };

  const exportStory = () => {
    const payload = {
      kind: 'wenmai-culture-experience',
      version: '2.0',
      exportedAt: new Date().toISOString(),
      experience: {
        id: experience.id,
        styleName: experience.styleName,
        title: experience.title,
        subtitle: experience.subtitle,
        lead: experience.lead,
        artwork: { url: new URL(experience.artworkUrl, window.location.href).href, ...experience.artworkSize },
        hotspots: experience.hotspots,
        chapters: experience.chapters,
        provenance: experience.provenance,
      },
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' });
    const anchor = document.createElement('a');
    anchor.href = URL.createObjectURL(blob);
    anchor.download = `wenmai-${experience.id}.json`;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(anchor.href);
  };

  const focusHotspots = chapter
    ? experience.hotspots.filter((hotspot) => chapter.focusHotspotIds.includes(hotspot.id))
    : [];

  return (
    <div className="pb-20">
      {/* 第一幕：题名 */}
      <header className="relative overflow-hidden">
        <div
          className="absolute inset-0 -z-10"
          style={{
            background: `radial-gradient(120% 90% at 15% 0%, ${experience.theme.accent}14 0%, transparent 55%), radial-gradient(90% 80% at 85% 10%, ${experience.theme.gold}1f 0%, transparent 60%)`,
          }}
          aria-hidden="true"
        />
        <div className="mx-auto max-w-[1180px] px-4 pb-8 pt-24 sm:px-8">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <Link
              to="/gallery"
              className="inline-flex items-center gap-1.5 text-[12px] text-[color:var(--color-ink)]/55 transition hover:text-[color:var(--color-primary)]"
            >
              <ArrowLeft size={13} />
              作品展厅
            </Link>
            <ExperienceModeSwitch
              experienceId={experience.id}
              current="story"
              hasWorld={hasWanderMode(experience.animation)}
            />
          </div>

          <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_420px] lg:items-end">
            <div>
              <p className="text-[11px] tracking-[0.36em] text-[color:var(--color-ink)]/45">
                {experience.styleName} · 一图一境
              </p>
              <h1 className="mt-2 font-serif text-[clamp(2rem,5vw,3.2rem)] leading-[1.15] text-[color:var(--color-ink)]">
                {experience.title}
              </h1>
              <p className="mt-3 max-w-xl border-l-2 pl-4 text-[13.5px] leading-[1.9] text-[color:var(--color-ink)]/70"
                 style={{ borderColor: experience.theme.accent }}>
                {experience.lead}
              </p>

              <div className="mt-6 flex flex-wrap items-center gap-2.5">
                <Link
                  to={`/experience/${experience.id}`}
                  className="inline-flex items-center gap-1.5 rounded px-4 py-2 text-[13px] text-white transition hover:opacity-90"
                  style={{ backgroundColor: experience.theme.accent }}
                >
                  <ImageIcon size={14} />
                  进入画中探索
                </Link>
                {hasWanderMode(experience.animation) && (
                  <Link
                    to={`/wander/${experience.id}`}
                    data-testid="story-to-wander"
                    className="inline-flex items-center gap-1.5 rounded px-4 py-2 text-[13px] font-medium text-[color:var(--color-primary)] ring-1 ring-inset ring-[color:var(--color-primary)]/45 transition hover:bg-[color:var(--color-primary)] hover:text-white hover:ring-[color:var(--color-primary)]"
                  >
                    <Compass size={14} />
                    走进画境漫游
                  </Link>
                )}
                <button
                  type="button" onClick={() => scrollToChapter(experience.chapters[0]?.id ?? '')}
                  className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/60 px-4 py-2 text-[13px] text-[color:var(--color-ink)]/75 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
                >
                  <BookOpen size={14} />
                  从第一折读起
                </button>
                <span className="text-[11.5px] text-[color:var(--color-ink)]/45">
                  {experience.chapters.length} 折 · {experience.hotspots.length} 处线索
                </span>
              </div>
            </div>

            <div className="relative">
              <div className="rounded-lg border border-[color:var(--color-gold)]/45 bg-white/40 p-2 shadow-[0_18px_50px_rgba(63,43,31,0.1)]">
                <img
                  src={experience.artworkUrl}
                  alt={`${experience.title} 全幅`}
                  className="block aspect-square w-full rounded-sm object-cover"
                />
              </div>
              <p className="mt-2 text-right text-[10.5px] text-[color:var(--color-ink)]/40">
                {experience.artworkSize.width}×{experience.artworkSize.height} · 本地生成图
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* 第二幕：滚动章节 + 粘性画面 */}
      <section className="mx-auto mt-4 max-w-[1180px] px-4 sm:px-8">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="hidden lg:block">
            <div className="sticky top-24">
              <div
                className="relative aspect-square w-full overflow-hidden rounded-lg border border-[color:var(--color-gold)]/40"
                style={{ backgroundColor: '#1b1613' }}
                ref={containerRef}
              >
                <div
                  className="absolute inset-0 origin-center"
                  style={{
                    transform: cameraTransform(
                      chapter?.frame.scale ?? 1,
                      chapter?.frame.focusX ?? 0.5,
                      chapter?.frame.focusY ?? 0.5
                    ),
                    transition: reducedMotion ? 'none' : 'transform 700ms cubic-bezier(0.22,0.61,0.36,1)',
                  }}
                >
                  <img
                    src={experience.artworkUrl}
                    alt=""
                    aria-hidden="true"
                    className="absolute inset-0 h-full w-full object-contain"
                  />
                  {imageBox.width > 0 &&
                    focusHotspots.map((hotspot) => {
                      const centre =
                        'points' in hotspot.geometry
                          ? {
                              x:
                                hotspot.geometry.points.reduce((acc, point) => acc + point[0], 0) /
                                hotspot.geometry.points.length,
                              y:
                                hotspot.geometry.points.reduce((acc, point) => acc + point[1], 0) /
                                hotspot.geometry.points.length,
                            }
                          : 'r' in hotspot.geometry
                            ? { x: hotspot.geometry.cx, y: hotspot.geometry.cy }
                            : {
                                x: hotspot.geometry.x + hotspot.geometry.width / 2,
                                y: hotspot.geometry.y + hotspot.geometry.height / 2,
                              };
                      const size = 0.014 * Math.min(imageBox.width, imageBox.height) * 2;
                      return (
                        <span
                          key={hotspot.id}
                          className="absolute rounded-full border-2"
                          style={{
                            left: imageBox.x + centre.x * imageBox.width,
                            top: imageBox.y + centre.y * imageBox.height,
                            width: Math.max(10, size),
                            height: Math.max(10, size),
                            transform: 'translate(-50%, -50%)',
                            borderColor: experience.theme.gold,
                            boxShadow: `0 0 0 6px ${experience.theme.gold}22`,
                          }}
                          aria-hidden="true"
                        />
                      );
                    })}
                </div>

                <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-end justify-between gap-2 bg-gradient-to-t from-black/55 to-transparent px-3 pb-2.5 pt-10">
                  <span className="text-[11px] text-white/80">{chapter?.title}</span>
                  <span className="shrink-0 text-[10px] tracking-widest text-white/45">
                    {chapter?.index} / {experience.chapters.length}
                  </span>
                </div>
              </div>

              <nav className="mt-3 flex items-center gap-1.5" aria-label="章节导航">
                {experience.chapters.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => scrollToChapter(item.id)}
                    className="h-1.5 flex-1 rounded-full transition"
                    style={{
                      backgroundColor: item.id === chapter?.id ? experience.theme.accent : 'rgba(63,43,31,0.15)',
                    }}
                    aria-label={`跳到第 ${item.index} 折：${item.title}`}
                    aria-current={item.id === chapter?.id}
                  />
                ))}
              </nav>
            </div>
          </div>

          <div className="space-y-14 lg:py-6">
            {/* 窄屏：画面贴在章节列顶部一起粘住，镜头仍跟着当前章节走 */}
            <div className="sticky top-[64px] z-20 -mx-4 bg-[#FBF6EB]/95 px-4 pb-1 pt-2 backdrop-blur sm:-mx-8 sm:px-8 lg:hidden">
              <div
                className="relative mx-auto aspect-square h-[30vh] max-h-[280px] overflow-hidden rounded-md border border-[color:var(--color-gold)]/40"
                style={{ backgroundColor: '#1b1613' }}
              >
                <div
                  className="absolute inset-0 origin-center"
                  style={{
                    transform: cameraTransform(
                      chapter?.frame.scale ?? 1,
                      chapter?.frame.focusX ?? 0.5,
                      chapter?.frame.focusY ?? 0.5
                    ),
                    transition: reducedMotion ? 'none' : 'transform 700ms cubic-bezier(0.22,0.61,0.36,1)',
                  }}
                >
                  <img
                    src={experience.artworkUrl}
                    alt={`${experience.styleName}《${experience.title}》当前章节取景`}
                    className="absolute inset-0 h-full w-full object-contain"
                  />
                </div>
                <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-end justify-between gap-2 bg-gradient-to-t from-black/50 to-transparent px-2.5 pb-1.5 pt-8">
                  <span className="truncate text-[10.5px] text-white/85">{chapter?.title}</span>
                  <span className="shrink-0 text-[10px] tracking-widest text-white/45">
                    {chapter?.index} / {experience.chapters.length}
                  </span>
                </div>
              </div>
            </div>

            {experience.chapters.map((item) => (
              <article
                key={item.id}
                id={`chapter-${item.index}`}
                data-chapter-id={item.id}
                ref={(element) => {
                  chapterRefs.current.set(item.id, element);
                }}
                className="scroll-mt-28"
              >
                <p className="text-[11px] tracking-[0.28em] text-[color:var(--color-ink)]/45">{item.eyebrow}</p>
                <h2 className="mt-1.5 font-serif text-[1.55rem] leading-snug text-[color:var(--color-ink)]">
                  {item.title}
                </h2>
                <p className="mt-3 text-[14px] leading-[2] text-[color:var(--color-ink)]/80">{item.body}</p>

                <div className="mt-4 flex flex-wrap gap-1.5">
                  {experience.hotspots
                    .filter((hotspot) => item.focusHotspotIds.includes(hotspot.id))
                    .map((hotspot) => (
                      <Link
                        key={hotspot.id}
                        to={`/experience/${experience.id}`}
                        className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--color-gold)]/50 bg-white/60 px-2.5 py-1 text-[11.5px] text-[color:var(--color-ink)]/70 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
                      >
                        <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: experience.theme.accent }} />
                        {hotspot.title}
                      </Link>
                    ))}
                </div>

                {item.sourceIds.length > 0 && (
                  <div className="mt-3">
                    <SourceChips sourceIds={item.sourceIds} />
                  </div>
                )}
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* 第四幕：带走 */}
      <section className="mx-auto mt-16 max-w-[1180px] px-4 sm:px-8">
        <div
          className="rounded-lg border border-[color:var(--color-gold)]/45 p-5 sm:p-6"
          style={{ backgroundColor: `${experience.theme.paper}` }}
        >
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-xl">
              <h2 className="font-serif text-lg text-[color:var(--color-ink)]">把这一卷带走</h2>
              <p className="mt-2 text-[12.5px] leading-relaxed text-[color:var(--color-ink)]/65">
                本轮不设云端账号与共享服务：可以复制当前页面地址，或导出一份自带画面地址与全部解读的
                JSON。两种方式都只依赖本机站点，不生成任何跨设备分享链接。
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={copyLink}
                className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/60 bg-white/70 px-3.5 py-2 text-[12.5px] text-[color:var(--color-ink)]/80 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
                {copied ? '已复制' : '复制本页地址'}
              </button>
              <button
                type="button"
                onClick={exportStory}
                className="inline-flex items-center gap-1.5 rounded px-3.5 py-2 text-[12.5px] text-white transition hover:opacity-90"
                style={{ backgroundColor: experience.theme.accent }}
              >
                <Download size={14} />
                导出故事 JSON
              </button>
            </div>
          </div>

          <div className="mt-5 grid gap-2 border-t border-[color:var(--color-gold)]/30 pt-4 text-[11.5px] text-[color:var(--color-ink)]/50 sm:grid-cols-2">
            <p>数据来源：{experience.visualAnalysis.source}</p>
            <p>热点定位：{experience.provenance.hotspotMethod}</p>
          </div>
        </div>
      </section>

      {/* 读完三折后的下一站：同一件作品的画境漫游。
          「下一卷」现在挪到画境漫游底部——读完故事先走进这一卷的画里，看完再换卷，
          顺序才是 互动画境 → 一图一境 → 画境漫游 → 下一卷。 */}
      {hasWanderMode(experience.animation) ? (
        <section className="mx-auto mt-10 max-w-[1180px] px-4 sm:px-8">
          <Link
            to={`/wander/${experience.id}`}
            data-testid="story-bottom-next-wander"
            className="group flex flex-wrap items-center justify-between gap-4 rounded-lg border border-[color:var(--color-gold)]/45 bg-white/55 px-5 py-4 transition hover:border-[color:var(--color-primary)]/50"
          >
            <span className="min-w-0">
              <span className="block text-[11px] tracking-[0.26em] text-[color:var(--color-ink)]/45">接着</span>
              <span className="mt-1 block font-serif text-lg text-[color:var(--color-ink)]">
                走进《{experience.title}》的画境
              </span>
              <span className="mt-1 block max-w-xl text-[12px] leading-relaxed text-[color:var(--color-ink)]/55">
                镜头会推进画中：近景先掠过，中景与远景按各自深度错开。看完这一卷，在画境底部再换下一卷。
              </span>
            </span>
            <span
              className="inline-flex items-center gap-1.5 rounded px-4 py-2 text-[13px] text-white transition group-hover:opacity-90"
              style={{ backgroundColor: experience.theme.accent }}
            >
              <Compass size={14} />
              开始画境漫游
            </span>
          </Link>
        </section>
      ) : (
        <NextExperience currentId={experience.id} accent={experience.theme.accent} />
      )}
    </div>
  );
}

function NextExperience({ currentId, accent }: { currentId: string; accent: string }) {
  const index = experiences.findIndex((item) => item.id === currentId);
  const next = experiences[(index + 1) % experiences.length];
  if (!next || next.id === currentId) return null;
  return (
    <section className="mx-auto mt-10 max-w-[1180px] px-4 sm:px-8">
      <Link
        to={`/story/${next.id}`}
        className="group flex items-center justify-between gap-4 rounded-lg border border-[color:var(--color-gold)]/35 bg-white/45 px-4 py-3.5 transition hover:border-[color:var(--color-primary)]/50"
      >
        <span>
          <span className="block text-[11px] tracking-[0.24em] text-[color:var(--color-ink)]/45">下一卷</span>
          <span className="mt-0.5 block font-serif text-base text-[color:var(--color-ink)]">
            {next.title} · {next.styleName}
          </span>
        </span>
        <span
          className="flex h-9 w-9 items-center justify-center rounded-full text-white transition group-hover:translate-x-0.5"
          style={{ backgroundColor: accent }}
        >
          <ArrowRight size={16} />
        </span>
      </Link>
    </section>
  );
}

export function Story() {
  const { id } = useParams();
  const { experience, state, retry } = useExperience(id);

  if (state === 'loading') {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-xl flex-col items-center justify-center px-6 text-center">
        <p className="text-[13px] text-[color:var(--color-ink)]/60">
          正在读取这件作品的章节叙事……
        </p>
      </div>
    );
  }

  if (!experience) {
    return (
      <div className="mx-auto max-w-xl px-6 py-28 text-center">
        <p className="mb-3 text-[11px] tracking-[0.3em] text-[color:var(--color-ink)]/45">
          {state === 'error' ? '读取失败' : '未找到这一卷'}
        </p>
        <h1 className="mb-5 font-serif text-2xl text-[color:var(--color-ink)]">
          展厅里暂时没有「{id}」这件作品的章节叙事
        </h1>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/gallery"
            className="inline-flex items-center rounded border border-[color:var(--color-gold)] px-5 py-2 text-sm text-[color:var(--color-primary)] transition hover:bg-[color:var(--color-primary)] hover:text-white"
          >
            返回作品展厅
          </Link>
          {state === 'error' && (
            <button
              type="button"
              onClick={retry}
              className="rounded border border-[color:var(--color-gold)]/60 px-4 py-2 text-sm text-[color:var(--color-ink)]/70 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
            >
              重试
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <ExperienceErrorBoundary fallbackLabel={experience.title}>
      <StoryContent experience={experience} />
    </ExperienceErrorBoundary>
  );
}

export default Story;