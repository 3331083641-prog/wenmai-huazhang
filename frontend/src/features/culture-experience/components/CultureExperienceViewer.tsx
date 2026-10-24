import { Link } from 'react-router-dom';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useReducedMotion } from 'motion/react';
import { ArrowLeft, Info } from 'lucide-react';
import type { CultureExperience } from '../types';
import { clamp } from '../utils/geometry';
import { useContainedImage } from '../hooks/useContainedImage';
import HotspotLayer from './HotspotLayer';
import KnowledgePanel from './KnowledgePanel';
import ViewToolbar from './ViewToolbar';
import { ExperienceModeSwitch, hasWanderMode } from './ExperienceModeSwitch';

const ZOOM_STEPS = [1, 1.5, 2, 3] as const;

/** 仓库未安装 @types/react，用最小结构类型描述指针事件。 */
interface PointerLike {
  pointerId: number;
  clientX: number;
  clientY: number;
  currentTarget: HTMLElement;
  target: EventTarget | null;
}

interface ViewerProps {
  experience: CultureExperience;
}

/**
 * 「画中有话」主体：可缩放、可拖动、可逐处探索的静帧画作。
 *
 * 三条设计底线：
 *   1. 画面永不自动移动；所有镜头与缩放都由用户动作触发。
 *   2. 热点几何只依赖归一化坐标，任何视口都严丝合缝。
 *   3. 选中即读出「画面观察 → 文化解读 → 来源」，三段不混排。
 */
export function CultureExperienceViewer({ experience }: ViewerProps) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [showRegions, setShowRegions] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  const prefersReduced = useReducedMotion();
  const reducedMotion = Boolean(prefersReduced);

  const { containerRef, imageBox } = useContainedImage(experience.artworkSize);
  const chipRefs = useRef(new Map<string, HTMLButtonElement | null>());
  const lastChipId = useRef<string | null>(null);
  const dragRef = useRef<{ id: number; startX: number; startY: number; baseX: number; baseY: number } | null>(null);

  const activeIndex = useMemo(
    () => experience.hotspots.findIndex((hotspot) => hotspot.id === activeId),
    [experience.hotspots, activeId]
  );
  const active = activeIndex >= 0 ? experience.hotspots[activeIndex] : null;

  const registerRef = useCallback((id: string, element: HTMLButtonElement | null) => {
    if (element) chipRefs.current.set(id, element);
    else chipRefs.current.delete(id);
  }, []);

  const clampOffset = useCallback(
    (value: { x: number; y: number }, level: number) => {
      const max = Math.max(0, (level - 1) * 50);
      return { x: clamp(value.x, -max, max), y: clamp(value.y, -max, max) };
    },
    []
  );

  const changeZoom = useCallback(
    (next: number) => {
      const level = clamp(next, 1, 3);
      setZoom(level);
      setOffset((current) => clampOffset(current, level));
    },
    [clampOffset]
  );

  const resetView = useCallback(() => {
    setZoom(1);
    setOffset({ x: 0, y: 0 });
  }, []);

  const select = useCallback((id: string) => {
    setActiveId(id);
    lastChipId.current = id;
  }, []);

  const close = useCallback(() => {
    setActiveId(null);
    const element = lastChipId.current ? chipRefs.current.get(lastChipId.current) : null;
    element?.focus({ preventScroll: true });
  }, []);

  const step = useCallback(
    (direction: 1 | -1) => {
      const total = experience.hotspots.length;
      if (total === 0) return;
      const current = activeIndex >= 0 ? activeIndex : direction === 1 ? -1 : 0;
      const next = (current + direction + total) % total;
      select(experience.hotspots[next].id);
    },
    [activeIndex, experience.hotspots, select]
  );

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) return;

      switch (event.key) {
        case 'ArrowRight':
          event.preventDefault();
          step(1);
          break;
        case 'ArrowLeft':
          event.preventDefault();
          step(-1);
          break;
        case 'Escape':
          if (activeId) close();
          else resetView();
          break;
        case '+':
        case '=':
          event.preventDefault();
          changeZoom(zoom * 1.5);
          break;
        case '-':
        case '_':
          event.preventDefault();
          changeZoom(zoom / 1.5);
          break;
        case '0':
          resetView();
          break;
        case 'h':
        case 'H':
          setShowRegions((value) => !value);
          break;
        default: {
          if (/^[1-9]$/.test(event.key)) {
            const index = Number(event.key) - 1;
            const hotspot = experience.hotspots[index];
            if (hotspot) select(hotspot.id);
          }
        }
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [activeId, changeZoom, close, experience.hotspots, resetView, select, step, zoom]);

  const handlePointerDown = (event: PointerLike) => {
    if (zoom <= 1) return;
    if ((event.target as HTMLElement).closest('button, a')) return;
    dragRef.current = {
      id: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      baseX: offset.x,
      baseY: offset.y,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: PointerLike) => {
    const drag = dragRef.current;
    if (!drag || drag.id !== event.pointerId) return;
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect || rect.width === 0 || rect.height === 0) return;
    const next = {
      x: drag.baseX + ((event.clientX - drag.startX) / rect.width) * 100,
      y: drag.baseY + ((event.clientY - drag.startY) / rect.height) * 100,
    };
    setOffset(clampOffset(next, zoom));
  };

  const handlePointerUp = (event: PointerLike) => {
    if (dragRef.current?.id !== event.pointerId) return;
    dragRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  /** 双击定位到点击处：先放大到 2.4 倍，再按归一化坐标把该点移到中心。 */
  const handleDoubleClick = (event: { clientX: number; clientY: number }) => {
    if (zoom > 1) {
      resetView();
      return;
    }
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect || imageBox.width === 0) return;
    const nx = clamp((event.clientX - rect.left - imageBox.x) / imageBox.width, 0, 1);
    const ny = clamp((event.clientY - rect.top - imageBox.y) / imageBox.height, 0, 1);
    const level = 2.4;
    setZoom(level);
    setOffset(clampOffset({ x: (0.5 - nx) * level * 100, y: (0.5 - ny) * level * 100 }, level));
  };

  return (
    <div className="mx-auto w-full max-w-[1400px] px-4 pb-14 pt-16 sm:px-6">
      <header className="mb-3 flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <Link
            to="/gallery"
            className="mb-2 inline-flex items-center gap-1.5 text-[12px] text-[color:var(--color-ink)]/55 transition hover:text-[color:var(--color-primary)]"
          >
            <ArrowLeft size={13} />
            作品展厅
          </Link>
          <p className="text-[11px] tracking-[0.34em] text-[color:var(--color-ink)]/45">
            {experience.styleName} · 画中有话
          </p>
          <h1 className="mt-1 font-serif text-2xl leading-tight text-[color:var(--color-ink)] sm:text-3xl">
            {experience.title}
            <span className="ml-3 align-middle text-[13px] font-normal tracking-wide text-[color:var(--color-ink)]/45">
              {experience.subtitle}
            </span>
          </h1>
          <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-[color:var(--color-ink)]/65">{experience.lead}</p>
        </div>
        <div className="flex shrink-0 flex-col items-start gap-2 sm:items-end">
          <ExperienceModeSwitch
            experienceId={experience.id}
            current="experience"
            hasWorld={hasWanderMode(experience.animation)}
          />
          <span className="text-[11px] text-[color:var(--color-ink)]/40">同一件作品，三种看法</span>
        </div>
      </header>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(320px,384px)] lg:items-start">
        <figure className="m-0">
          <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2">
            <p className="text-[11.5px] text-[color:var(--color-ink)]/50">
              {experience.hotspots.length} 处文化线索 · 每处都附来源
            </p>
            <ViewToolbar
              zoom={zoom}
              onZoomIn={() => changeZoom(ZOOM_STEPS.find((stepValue) => stepValue > zoom) ?? 3)}
              onZoomOut={() => changeZoom([...ZOOM_STEPS].reverse().find((stepValue) => stepValue < zoom) ?? 1)}
              onReset={resetView}
              showRegions={showRegions}
              onToggleRegions={() => setShowRegions((value) => !value)}
              onFit={resetView}
              storyHref={`/story/${experience.id}`}
              wanderHref={hasWanderMode(experience.animation) ? `/wander/${experience.id}` : undefined}
              accent={experience.theme.accent}
            />
          </div>
          <div
            className="rounded-lg border border-[color:var(--color-gold)]/40 p-2.5 shadow-[0_14px_40px_rgba(63,43,31,0.08)] sm:p-3.5"
            style={{ backgroundColor: `${experience.theme.paper}` }}
          >
            <div
              ref={containerRef}
              className="relative mx-auto aspect-square w-full touch-none select-none overflow-hidden rounded-sm bg-[#1c1713]"
              style={{
                // 让整幅画面在常见笔记本高度里完整露出，而不是被首屏截断
                width: 'min(100%, calc(100vh - 330px), 720px)',
                cursor: zoom > 1 ? (dragRef.current ? 'grabbing' : 'grab') : 'zoom-in',
              }}
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              onPointerCancel={handlePointerUp}
              onDoubleClick={handleDoubleClick}
              role="group"
              aria-label={`${experience.title} 互动画面，可用方向键在热点之间移动`}
            >
              <div
                className="absolute inset-0 origin-center"
                style={{
                  transform: `translate(${offset.x}%, ${offset.y}%) scale(${zoom})`,
                  transition: reducedMotion || dragRef.current ? 'none' : 'transform 320ms cubic-bezier(0.22,0.61,0.36,1)',
                }}
              >
                <img
                  src={experience.artworkUrl}
                  alt={`${experience.styleName}《${experience.title}》画面`}
                  className="pointer-events-none absolute inset-0 h-full w-full object-contain"
                  draggable={false}
                  decoding="async"
                />
                {imageBox.width > 0 && (
                  <div
                    className="absolute"
                    style={{ left: imageBox.x, top: imageBox.y, width: imageBox.width, height: imageBox.height }}
                  >
                    <HotspotLayer
                      hotspots={experience.hotspots}
                      activeId={activeId}
                      hoveredId={hoveredId}
                      showRegions={showRegions}
                      accent={experience.theme.accent}
                      gold={experience.theme.gold}
                      zoom={zoom}
                      onSelect={select}
                      onHover={setHoveredId}
                      registerRef={registerRef}
                    />
                  </div>
                )}
              </div>

              <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-center justify-between gap-2 bg-gradient-to-t from-black/45 to-transparent px-3 pb-2 pt-8">
                <p className="text-[11px] text-white/80">
                  {active ? `正在看：${active.title}` : '点击编号看这一处是什么 · 双击放大'}
                </p>
                <p className="shrink-0 text-[10px] tracking-wider text-white/55">
                  {experience.artworkSize.width}×{experience.artworkSize.height}
                </p>
              </div>
            </div>
          </div>

          <figcaption className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11.5px] text-[color:var(--color-ink)]/55">
            <span className="inline-flex items-center gap-1.5">
              <Info size={12} />
              {experience.hotspots.length} 处文化线索，每一处都附来源
            </span>
            <span className="hidden sm:inline">快捷键：← → 切换 · 1–9 直达 · +/− 缩放 · 0 复位 · H 显示位置框</span>
            <span className="sm:hidden">点编号即可查看</span>
          </figcaption>
        </figure>

        <div className="lg:sticky lg:top-24">
          <div className="h-[min(70vh,560px)] lg:h-[calc(100vh-16.5rem)]">
            <KnowledgePanel
              experience={experience}
              active={active}
              activeIndex={activeIndex}
              reducedMotion={reducedMotion}
              onSelect={select}
              onClose={close}
              onPrev={() => step(-1)}
              onNext={() => step(1)}
            />
          </div>
        </div>
      </div>

      <p className="sr-only" aria-live="polite">
        {active ? `第 ${activeIndex + 1} 处线索：${active.title}。${active.shortDescription}` : '未选择线索'}
      </p>
    </div>
  );
}

export default CultureExperienceViewer;