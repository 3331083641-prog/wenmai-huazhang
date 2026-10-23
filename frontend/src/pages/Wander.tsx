import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useReducedMotion } from 'motion/react';
import { ArrowLeft, BookOpen, Eye, Layers, MousePointer2, RotateCcw } from 'lucide-react';
import { getExperience } from '../data/experiences';
import { clamp } from '../features/culture-experience/utils/geometry';
import { publicUrl } from '../features/culture-experience/utils/assets';
import ExperienceErrorBoundary from '../features/culture-experience/components/ExperienceErrorBoundary';
import PaintingWorld from '../features/painting-world/PaintingWorld';

/** 三个视点预设，对应「远眺 / 平视 / 临水」三种看法。 */
const VIEWS = [
  { id: 'far', label: '远眺', tiltX: 2, tiltY: -4, zoom: 0.94, note: '整体轮廓最先被读到，山势与水面连成一片。' },
  { id: 'level', label: '平视', tiltX: 0, tiltY: 0, zoom: 1, note: '正对画面，最接近看画时的自然姿态。' },
  { id: 'near', label: '临水', tiltX: 6, tiltY: 5, zoom: 1.1, note: '俯身靠近，前景的松石与水面压过来。' },
] as const;

/** 与舞台 CSS 的 perspective 保持一致，用于抵消透视带来的层间缩放差。 */
const PERSPECTIVE = 1400;
/** 单层最大前后位移（px）。越小越稳，越大越「立体」。 */
const LAYER_GAP = 46;

function WanderContent({ experience }: { experience: NonNullable<ReturnType<typeof getExperience>> }) {
  const layers = experience.animation.layers ?? [];
  const prefersReduced = useReducedMotion();
  const [parallaxOn, setParallaxOn] = useState(!prefersReduced);
  const [view, setView] = useState<(typeof VIEWS)[number]['id']>('level');
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [showDisclosure, setShowDisclosure] = useState(false);
  const [activeLayer, setActiveLayer] = useState<string | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const frameRef = useRef<number | null>(null);

  const preset = VIEWS.find((item) => item.id === view) ?? VIEWS[1];

  useEffect(() => {
    if (prefersReduced) setParallaxOn(false);
  }, [prefersReduced]);

  const handlePointerMove = useCallback(
    (event: { clientX: number; clientY: number }) => {
      if (!parallaxOn) return;
      const element = stageRef.current;
      if (!element) return;
      if (frameRef.current !== null) return;
      const { clientX, clientY } = event;
      frameRef.current = window.requestAnimationFrame(() => {
        frameRef.current = null;
        const rect = element.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;
        const nx = (clientX - rect.left) / rect.width - 0.5;
        const ny = (clientY - rect.top) / rect.height - 0.5;
        setTilt({ x: clamp(-ny * 7, -7, 7), y: clamp(nx * 10, -10, 10) });
      });
    },
    [parallaxOn]
  );

  const resetTilt = useCallback(() => setTilt({ x: 0, y: 0 }), []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!parallaxOn) return;
      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) return;
      const stepValue = 1.5;
      if (event.key === 'ArrowLeft') setTilt((value) => ({ ...value, y: clamp(value.y - stepValue, -10, 10) }));
      else if (event.key === 'ArrowRight') setTilt((value) => ({ ...value, y: clamp(value.y + stepValue, -10, 10) }));
      else if (event.key === 'ArrowUp') setTilt((value) => ({ ...value, x: clamp(value.x + stepValue, -7, 7) }));
      else if (event.key === 'ArrowDown') setTilt((value) => ({ ...value, x: clamp(value.x - stepValue, -7, 7) }));
      else return;
      event.preventDefault();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [parallaxOn]);

  useEffect(() => () => {
    if (frameRef.current !== null) window.cancelAnimationFrame(frameRef.current);
  }, []);

  const rotation = parallaxOn ? tilt : { x: preset.tiltX, y: preset.tiltY };

  return (
    <div className="mx-auto w-full max-w-[1240px] px-4 pb-20 pt-24 sm:px-6">
      <header className="mb-5">
        <a
          href="/gallery"
          className="mb-2 inline-flex items-center gap-1.5 text-[12px] text-[color:var(--color-ink)]/55 transition hover:text-[color:var(--color-primary)]"
        >
          <ArrowLeft size={13} />
          文化作品展厅
        </a>
        <p className="text-[11px] tracking-[0.34em] text-[color:var(--color-ink)]/45">{experience.styleName} · 画境漫游</p>
        <h1 className="mt-1 font-serif text-2xl leading-tight text-[color:var(--color-ink)] sm:text-3xl">
          走进《{experience.title}》
        </h1>
        <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-[color:var(--color-ink)]/65">
          移动指针，画面会随视角轻轻倾侧：远山几乎不动，前景会先过来。这不是旋转的立体模型，而是把一幅画拆成三层平面后，
          让它们在空间里前后错开。
        </p>
      </header>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px] lg:items-start">
        <div>
          <div
            ref={stageRef}
            className="relative overflow-hidden rounded-lg border border-[color:var(--color-gold)]/40 bg-[#14100e] p-2 sm:p-3"
            onPointerMove={handlePointerMove}
            onPointerLeave={() => {
              resetTilt();
              setActiveLayer(null);
            }}
            style={{ perspective: '1400px' }}
          >
            <div
              className="relative mx-auto aspect-square w-full max-w-[720px]"
              style={{
                transformStyle: 'preserve-3d',
                transform: `rotateX(${rotation.x}deg) rotateY(${rotation.y}deg) scale(${preset.zoom})`,
                transition: parallaxOn ? 'transform 120ms linear' : 'transform 620ms cubic-bezier(0.22,0.61,0.36,1)',
              }}
            >
              {layers.length > 0 ? (
                layers.map((layer, index) => {
                  const depth = (layer.depth - 0.5) * 2; // -1..1
                  const z = depth * LAYER_GAP;
                  // 透视会让 z 不同的层自动放大/缩小。这里用反向缩放把「尺寸差」抵消掉，
                  // 只留下旋转时 z 带来的位移差（也就是视差），避免相邻两层一大一小叠出重影。
                  const compensate = (PERSPECTIVE - z) / PERSPECTIVE;
                  return (
                    <div
                      key={layer.id}
                      className="absolute inset-0 cursor-pointer"
                      style={{
                        transform: `translateZ(${z}px) scale(${compensate})`,
                        opacity: activeLayer && activeLayer !== layer.id ? 0.35 : 1,
                        transition: 'opacity 240ms ease',
                        filter:
                          layer.id === 'far'
                            ? 'saturate(0.96)'
                            : layer.id === 'near'
                              ? 'drop-shadow(0 6px 10px rgba(0,0,0,0.28))'
                              : undefined,
                        zIndex: index + 1,
                      }}
                      onPointerEnter={() => setActiveLayer(layer.id)}
                      onClick={() => setActiveLayer(layer.id)}
                    >
                      <img
                        src={publicUrl(layer.url)}
                        alt=""
                        aria-hidden={layer.id !== 'far'}
                        className="pointer-events-none absolute inset-0 h-full w-full object-contain"
                        draggable={false}
                        decoding="async"
                      />
                    </div>
                  );
                })
              ) : (
                <img
                  src={experience.artworkUrl}
                  alt={`${experience.title} 全幅`}
                  className="absolute inset-0 h-full w-full object-contain"
                />
              )}
            </div>

            <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-end justify-between gap-3 bg-gradient-to-t from-black/40 to-transparent px-3 pb-2.5 pt-10">
              <p className="text-[11px] text-white/80">
                {activeLayer
                  ? `正在看：${activeLayer === 'far' ? '背景 · 远山与云气' : activeLayer === 'mid' ? '中景 · 山体与楼阁' : '近景 · 松石与水面'}`
                  : '移动指针改变视角 · 点击某一层只看它'}
              </p>
              <p className="shrink-0 text-[10px] tracking-wider text-white/50">分层视差 · 非三维重建</p>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            {VIEWS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  setView(item.id);
                  resetTilt();
                }}
                className="rounded border px-3 py-1.5 text-[12px] transition"
                style={
                  view === item.id
                    ? { borderColor: experience.theme.accent, backgroundColor: `${experience.theme.accent}14`, color: experience.theme.accent }
                    : { borderColor: 'rgba(210,161,74,0.5)', color: 'rgba(63,43,31,0.7)' }
                }
                aria-pressed={view === item.id}
              >
                {item.label}
              </button>
            ))}

            <button
              type="button"
              onClick={() => {
                setParallaxOn((value) => !value);
                resetTilt();
              }}
              className="ml-1 inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/50 bg-white/60 px-3 py-1.5 text-[12px] text-[color:var(--color-ink)]/75 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
              aria-pressed={parallaxOn}
            >
              <Layers size={13} />
              {parallaxOn ? '视差已开启' : '视差已关闭'}
            </button>

            <button
              type="button"
              onClick={resetTilt}
              className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/50 bg-white/60 px-3 py-1.5 text-[12px] text-[color:var(--color-ink)]/75 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
            >
              <RotateCcw size={13} />
              摆正
            </button>

            <span className="ml-auto text-[11px] text-[color:var(--color-ink)]/45">方向键也可微调视角</span>
          </div>
        </div>

        <aside className="space-y-4">
          <div className="rounded-lg border border-[color:var(--color-gold)]/45 bg-[#FDFBF7] p-4">
            <h2 className="mb-2 flex items-center gap-1.5 font-serif text-sm text-[color:var(--color-ink)]">
              <MousePointer2 size={14} style={{ color: experience.theme.accent }} />
              这一刻在做什么
            </h2>
            <p className="text-[12.5px] leading-relaxed text-[color:var(--color-ink)]/70">{preset.note}</p>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-[11.5px] text-[color:var(--color-ink)]/55">
              <div>
                <dt className="opacity-70">水平倾角</dt>
                <dd className="tabular-nums text-[color:var(--color-ink)]/80">{rotation.y.toFixed(1)}°</dd>
              </div>
              <div>
                <dt className="opacity-70">垂直倾角</dt>
                <dd className="tabular-nums text-[color:var(--color-ink)]/80">{rotation.x.toFixed(1)}°</dd>
              </div>
              <div>
                <dt className="opacity-70">层数</dt>
                <dd className="tabular-nums text-[color:var(--color-ink)]/80">{layers.length} 层</dd>
              </div>
              <div>
                <dt className="opacity-70">视差</dt>
                <dd className="text-[color:var(--color-ink)]/80">{parallaxOn ? '跟随指针' : '已静止'}</dd>
              </div>
            </dl>
          </div>

          <div className="rounded-lg border border-[color:var(--color-gold)]/45 bg-white/55 p-4">
            <h2 className="mb-2 flex items-center gap-1.5 font-serif text-sm text-[color:var(--color-ink)]">
              <Eye size={14} style={{ color: experience.theme.accent }} />
              三层是怎么分的
            </h2>
            <ul className="space-y-1.5 text-[12px] leading-relaxed text-[color:var(--color-ink)]/70">
              {layers.map((layer) => (
                <li key={layer.id} className="flex items-start gap-2">
                  <span
                    className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full"
                    style={{ backgroundColor: layer.id === 'near' ? experience.theme.accent : experience.theme.gold }}
                  />
                  <span>
                    <b className="font-medium text-[color:var(--color-ink)]/85">
                      {layer.id === 'far' ? '背景' : layer.id === 'mid' ? '中景' : '近景'}
                    </b>
                    <span className="text-[color:var(--color-ink)]/50">
                      {' '}
                      · 画面 {Math.round(layer.maskFrom * 100)}%–{Math.round(layer.maskTo * 100)}% 区域
                    </span>
                  </span>
                </li>
              ))}
            </ul>
            <button
              type="button"
              onClick={() => setShowDisclosure((value) => !value)}
              className="mt-3 text-[11.5px] text-[color:var(--color-primary)] underline decoration-dotted underline-offset-4"
              aria-expanded={showDisclosure}
            >
              {showDisclosure ? '收起说明' : '这个分层是怎么来的？'}
            </button>
            {showDisclosure && (
              <div className="mt-2 space-y-2 border-t border-[color:var(--color-gold)]/30 pt-2 text-[11.5px] leading-relaxed text-[color:var(--color-ink)]/60">
                <p>{experience.provenance.designNote}</p>
                <p>{experience.animation.layerSource}</p>
                <p className="text-[color:var(--color-ink)]/45">
                  因此它只能被称为「基于图像分层的 2.5D 视差」，不是真实三维重建，也没有相机参数。
                </p>
              </div>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <a
              href={`/experience/${experience.id}`}
              className="inline-flex items-center justify-center gap-1.5 rounded border border-[color:var(--color-gold)]/60 px-3 py-2 text-[12.5px] text-[color:var(--color-ink)]/80 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
            >
              回到画中找线索
            </a>
            <a
              href={`/story/${experience.id}`}
              className="inline-flex items-center justify-center gap-1.5 rounded px-3 py-2 text-[12.5px] text-white transition hover:opacity-90"
              style={{ backgroundColor: experience.theme.accent }}
            >
              <BookOpen size={14} />
              读这一卷的故事
            </a>
          </div>
        </aside>
      </div>
    </div>
  );
}

export function Wander() {
  const { id } = useParams();
  const experience = getExperience(id);

  if (!experience) {
    return (
      <div className="mx-auto max-w-xl px-6 py-28 text-center">
        <p className="mb-3 text-[11px] tracking-[0.3em] text-[color:var(--color-ink)]/45">未找到作品</p>
        <h1 className="mb-5 font-serif text-2xl text-[color:var(--color-ink)]">
          展厅里暂时没有「{id}」这件作品
        </h1>
        <p className="mb-6 text-[13px] leading-relaxed text-[color:var(--color-ink)]/60">
          请回到展厅从五件案例里选一件。展厅里的作品都带真实生成图与文化说明。
        </p>
        <a
          href="/gallery"
          className="inline-flex items-center rounded border border-[color:var(--color-gold)] px-5 py-2 text-sm text-[color:var(--color-primary)] transition hover:bg-[color:var(--color-primary)] hover:text-white"
        >
          返回文化作品展厅
        </a>
      </div>
    );
  }

  // 画境：2.5D 分层视差（单图深度估计 + 分层错位）。三维版已移除。
  if (experience.animation.mode === 'world' && experience.animation.world?.url) {
    return (
      <ExperienceErrorBoundary fallbackLabel={experience.title}>
        <PaintingWorld experience={experience} />
      </ExperienceErrorBoundary>
    );
  }

  if (experience.animation.mode !== 'layered' || !experience.animation.layers?.length) {
    return (
      <div className="mx-auto max-w-xl px-6 py-28 text-center">
        <p className="mb-3 text-[11px] tracking-[0.3em] text-[color:var(--color-ink)]/45">暂未开放</p>
        <h1 className="mb-5 font-serif text-2xl text-[color:var(--color-ink)]">
          这一卷还没有可漫游的画境资产
        </h1>
        <p className="mb-6 text-[13px] leading-relaxed text-[color:var(--color-ink)]/60">
          画境需要为每件作品单独估计深度并烘焙资产，目前只完成了《云鹤临水楼》。
          其余作品仍可在「画中有话」里逐处探索。
        </p>
        <a
          href="/gallery"
          className="inline-flex items-center rounded border border-[color:var(--color-gold)] px-5 py-2 text-sm text-[color:var(--color-primary)] transition hover:bg-[color:var(--color-primary)] hover:text-white"
        >
          返回文化作品展厅
        </a>
      </div>
    );
  }

  return (
    <ExperienceErrorBoundary fallbackLabel={experience.title}>
      <WanderContent experience={experience} />
    </ExperienceErrorBoundary>
  );
}

export default Wander;