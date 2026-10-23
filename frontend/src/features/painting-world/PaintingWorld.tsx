import { Link } from 'react-router-dom';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Canvas } from '@react-three/fiber';
import { useReducedMotion } from 'motion/react';
import { ArrowLeft, ArrowRight, Compass, Info, Move, RotateCcw, X } from 'lucide-react';
import type { CultureExperience, CultureHotspot } from '../culture-experience/types';
import { publicUrl } from '../culture-experience/utils/assets';
import { ExperienceModeSwitch } from '../culture-experience/components/ExperienceModeSwitch';
import { experiences } from '../../data/experiences';
import {
  loadWorldManifest,
  type PaintingWorldManifest,
} from './world';
import {
  createRuntime,
  WorldScene,
  type WorldControl,
  type WorldRuntime,
} from './WorldScene';

/** 低于这个帧率持续 2.5 秒，就落回静态视差——宁可简单，不要卡。 */
const FPS_FLOOR = 24;
const FPS_WINDOW_MS = 2500;

function supportsWebGL2(): boolean {
  try {
    const canvas = document.createElement('canvas');
    return Boolean(canvas.getContext('webgl2'));
  } catch {
    return false;
  }
}

/** 首屏就能判定的「弱设备」：核显/集显常见的低并发 + 低内存。 */
function looksLowPower(): boolean {
  const nav = navigator as Navigator & { deviceMemory?: number; hardwareConcurrency?: number };
  const mem = nav.deviceMemory ?? 8;
  const cores = nav.hardwareConcurrency ?? 8;
  return mem <= 4 || cores <= 4;
}

function hotspotStyle(shape: CultureHotspot['shape']) {
  return shape === 'circle' ? 'rounded-full' : 'rounded-sm';
}

export default function PaintingWorld({ experience }: { experience: CultureExperience }) {
  const navigate = useNavigate();
  const prefersReduced = useReducedMotion();

  const [manifest, setManifest] = useState<PaintingWorldManifest | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [degraded, setDegraded] = useState(false);
  const [inside, setInside] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [fps, setFps] = useState(60);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [showNote, setShowNote] = useState(false);

  // 「下一卷」：从展厅那五件里按顺序取下一件。看完这一卷的画境，再换下一卷。
  const nextArtwork = useMemo(() => {
    const list = experiences;
    const index = list.findIndex((item) => item.id === experience.id);
    if (index < 0) return null;
    const next = list[(index + 1) % list.length];
    return next && next.id !== experience.id ? next : null;
  }, [experience.id]);

  // 探针是 useMemo 出来的，闭包会钉住首帧的 state；用 ref 让外部读到的永远是当前值
  const selectedRef = useRef<string | null>(null);
  const hoveredRef = useRef<string | null>(null);
  selectedRef.current = selectedId;
  hoveredRef.current = hoveredId;

  const controlRef = useRef<WorldControl | null>(null);
  if (controlRef.current === null) {
    const runtime = createRuntime();
    controlRef.current = {
      runtime,
      enter: () => {
        runtime.phase = 'entering';
        runtime.progress = 0;
      },
      exit: () => {
        runtime.phase = 'idle';
        runtime.progress = 0;
        runtime.targetYawDeg = 0;
        runtime.targetPitchDeg = 0;
        // 退出时一并收起热点面板与悬停态：否则回到画外，上一处线索的解读卡片
        // 还挂在入口卡片下面（实测可见），像是没退干净。
        setSelectedId(null);
        setHoveredId(null);
      },
      reset: () => {
        runtime.targetYawDeg = 0;
        runtime.targetPitchDeg = 0;
        // 停稳距离由 CameraRig 写入；没有就保持原地
        if (runtime.phase === 'inside' && runtime.restDistance > 0) {
          runtime.targetDistance = runtime.restDistance;
        }
      },
      setYawDeg: (v) => {
        runtime.targetYawDeg = v;
      },
      setPitchDeg: (v) => {
        runtime.targetPitchDeg = v;
      },
      setDistance: (v) => {
        runtime.targetDistance = v;
      },
      setFrozen: (v) => {
        runtime.frozen = v;
      },
      select: (id) => setSelectedId(id),
    };
  }
  const control = controlRef.current;

  const worldUrl = experience.animation.world?.url;

  useEffect(() => {
    if (!worldUrl) {
      setLoadError('这件作品还没有画境资产');
      return;
    }
    let alive = true;
    loadWorldManifest(worldUrl)
      .then((data) => {
        if (alive) setManifest(data);
      })
      .catch((err: unknown) => {
        if (alive) setLoadError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      alive = false;
    };
  }, [worldUrl]);

  // 降级判定：手动指定 > 系统偏好 > WebGL2 > 弱设备
  useEffect(() => {
    // ?static=1 是显式的「只看静态视差」入口：低性能设备、省流、以及验收降级路径都用它
    if (new URLSearchParams(window.location.search).get('static') === '1') {
      setDegraded(true);
      return;
    }
    if (prefersReduced) {
      setDegraded(true);
      return;
    }
    if (!supportsWebGL2()) {
      setDegraded(true);
      return;
    }
    if (looksLowPower()) setDegraded(true);
  }, [prefersReduced]);

  useEffect(() => {
    control.runtime.degraded = degraded;
  }, [control, degraded]);

  // 帧率兜底：连续 2.5 秒低于 24fps 就降级（只在进入后才判，避免首帧误判）
  const lowSince = useRef<number | null>(null);
  const handleFps = useCallback(
    (value: number) => {
      setFps(value);
      if (degraded || !inside) return;
      if (value < FPS_FLOOR) {
        lowSince.current = lowSince.current ?? Date.now();
        if (Date.now() - lowSince.current > FPS_WINDOW_MS) setDegraded(true);
      } else {
        lowSince.current = null;
      }
    },
    [degraded, inside]
  );

  // DOM 层跟随运行期状态：进入/退出由快照驱动，避免两套布尔打架
  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const phase = control.runtime.phase;
      setInside((prev) => (prev === (phase === 'inside') ? prev : phase === 'inside'));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [control]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (selectedId) setSelectedId(null);
        else navigate(`/experience/${experience.id}`);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [navigate, experience.id, selectedId]);

  // 调试/验收探针：所有结论都要能被外部测量，而不是我说好看就好看
  useEffect(() => {
    if (!manifest) return;
    const rt: WorldRuntime = control.runtime;
    const api = {
      slug: manifest.slug,
      manifest,
      runtime: rt,
      enter: () => control.enter(),
      exit: () => control.exit(),
      reset: () => control.reset(),
      setYawDeg: (v: number) => control.setYawDeg(v),
      setPitchDeg: (v: number) => control.setPitchDeg(v),
      setDistance: (v: number) => control.setDistance(v),
      freeze: (v: boolean) => control.setFrozen(v),
      setAmplitude: (v: number) => {
        control.runtime.tuning.amplitude = v;
      },
      setHaze: (v: number) => {
        control.runtime.tuning.haze = v;
      },
      setMist: (v: number) => {
        control.runtime.tuning.mist = v;
      },
      setCutout: (v: boolean) => {
        control.runtime.tuning.showCutout = v ? 1 : 0;
      },
      select: (id: string | null) => control.select(id),
      snapshot: () => ({
        phase: rt.phase,
        progress: Number(rt.progress.toFixed(4)),
        yawDeg: Number(rt.yawDeg.toFixed(3)),
        pitchDeg: Number(rt.pitchDeg.toFixed(3)),
        distance: Number(rt.distance.toFixed(4)),
        targetDistance: Number(rt.targetDistance.toFixed(4)),
        fps: Math.round(fps),
        degraded,
        frozen: rt.frozen,
        frame: rt.frame,
        selectedId: selectedRef.current,
        hoveredId: hoveredRef.current,
        hotspots: rt.hotspots,
        segments: { x: 192, y: 128 },
        amplitude: manifest.camera.depth_amplitude,
        depthModel: manifest.provenance.depth_model,
      }),
      /** 采集入场全过程，用来证明「连续推进、无跳变」。 */
      sampleEntry: (limit = 900) =>
        new Promise<Array<{ t: number; d: number; phase: string }>>((resolve) => {
          const out: Array<{ t: number; d: number; phase: string }> = [];
          const t0 = performance.now();
          const tick = () => {
            out.push({
              t: Math.round(performance.now() - t0),
              d: Number(rt.distance.toFixed(5)),
              phase: rt.phase,
            });
            if (rt.phase === 'inside' || out.length >= limit) resolve(out);
            else requestAnimationFrame(tick);
          };
          tick();
        }),
    };
    (window as unknown as { __paintingWorld?: unknown }).__paintingWorld = api;
    return () => {
      delete (window as unknown as { __paintingWorld?: unknown }).__paintingWorld;
    };
  }, [manifest, control, fps, degraded]);

  const selected = useMemo(
    () => experience.hotspots.find((h) => h.id === selectedId) ?? null,
    [experience.hotspots, selectedId]
  );
  const hovered = useMemo(
    () => experience.hotspots.find((h) => h.id === hoveredId) ?? null,
    [experience.hotspots, hoveredId]
  );

  const artworkSrc = experience.artworkUrl ? publicUrl(experience.artworkUrl) : '';

  /* ------------------------------ 降级：静态 + 简单视差 ------------------------------ */
  if (degraded) {
    const picked = experience.hotspots.find((h) => h.id === selectedId) ?? null;
    return (
      <div className="relative min-h-screen bg-[color:var(--color-paper)]">
        <div
          className="relative flex min-h-screen flex-col items-center justify-center gap-4 overflow-hidden py-16"
          onPointerMove={(event) => {
            const rect = event.currentTarget.getBoundingClientRect();
            setTilt({
              x: ((event.clientX - rect.left) / rect.width - 0.5) * 6,
              y: ((event.clientY - rect.top) / rect.height - 0.5) * 6,
            });
          }}
        >
          <div className="w-full max-w-3xl px-6">
            <p className="mb-1 text-center font-serif text-[11px] tracking-[0.42em] text-[color:var(--color-gold)]">
              画 境 漫 游
            </p>
            <p className="mb-3 text-center font-serif text-lg text-[color:var(--color-primary)]">
              {experience.title}
            </p>
            <div
              className="transition-transform duration-300 ease-out"
              style={{ transform: `perspective(1400px) rotateX(${tilt.y}deg) rotateY(${tilt.x}deg)` }}
            >
              <img src={artworkSrc} alt={experience.title} className="w-full rounded-sm shadow-xl" />
            </div>
          </div>

          {/* 降级也要能读画：热点退化成文字入口，内容与沉浸模式完全一致 */}
          <div className="flex max-w-3xl flex-wrap items-center justify-center gap-2 px-6">
            {experience.hotspots.map((spot) => (
              <button
                key={spot.id}
                onClick={() => setSelectedId(selectedId === spot.id ? null : spot.id)}
                className={
                  'rounded-full border px-3 py-1 text-[12px] transition-colors ' +
                  (selectedId === spot.id
                    ? 'border-[color:var(--color-gold)] bg-[color:var(--color-gold)]/12 text-[color:var(--color-primary)]'
                    : 'border-[color:var(--color-ink)]/15 text-[color:var(--color-ink)]/70 hover:border-[color:var(--color-gold)]/60')
                }
              >
                {spot.title}
              </button>
            ))}
          </div>

          {picked && (
            <div className="mx-6 max-w-2xl rounded border border-[color:var(--color-gold)]/30 bg-white/60 px-5 py-4 text-left">
              <p className="mb-1 text-[11px] tracking-[0.2em] text-[color:var(--color-gold)]">
                {picked.kicker}
              </p>
              <p className="mb-2 font-serif text-[15px] text-[color:var(--color-primary)]">{picked.title}</p>
              <p className="mb-2 text-[12.5px] leading-relaxed text-[color:var(--color-ink)]/75">
                {picked.visualObservation}
              </p>
              <p className="text-[12.5px] leading-relaxed text-[color:var(--color-ink)]/60">
                {picked.culturalExplanation}
              </p>
            </div>
          )}

          <p className="max-w-md px-6 text-center text-[12px] leading-relaxed text-[color:var(--color-ink)]/55">
            已切换为静态视差（设备性能不足或系统开启了「减少动态效果」）。画中线索仍可点开阅读。
          </p>

          <button
            onClick={() => navigate(`/experience/${experience.id}`)}
            className="absolute left-5 top-5 inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)] px-3 py-1.5 text-[13px] text-[color:var(--color-primary)]"
          >
            <ArrowLeft size={14} /> 退出画境
          </button>
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[color:var(--color-paper)] px-6">
        <div className="max-w-md text-center">
          <p className="mb-3 font-serif text-xl text-[color:var(--color-ink)]">画境暂时打不开</p>
          <p className="mb-6 text-[13px] text-[color:var(--color-ink)]/60">{loadError}</p>
          <button
            onClick={() => navigate(`/experience/${experience.id}`)}
            className="rounded border border-[color:var(--color-gold)] px-5 py-2 text-sm text-[color:var(--color-primary)]"
          >
            回到作品
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-[#F4F1E6]">
      {/* 画布：透明背景，衬一层纸色，画外状态看起来是「一张画悬在纸上」 */}
      <Canvas
        dpr={[1, 1.8]}
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
        camera={{
          fov: manifest?.camera.fov ?? 34,
          near: 0.02,
          far: 24,
          position: [0, 0, manifest ? manifest.camera.distance_fill * manifest.camera.entry.from_scale : 2.8],
        }}
        onPointerMissed={() => setSelectedId(null)}
      >
        {manifest ? (
          <WorldScene
            manifest={manifest}
            baseUrl={experience.animation.world?.url ?? ''}
            control={control}
            selectedId={selectedId}
            onHoverChange={setHoveredId}
            onFps={handleFps}
          />
        ) : null}
      </Canvas>

      {/* 纸纹与暗角：压在画布上，把「屏幕」做成「纸」 */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(120% 90% at 50% 45%, rgba(244,241,230,0) 52%, rgba(120,104,78,0.22) 100%)',
        }}
      />

      {/* 顶部：只留退出与说明 */}
      <div className="pointer-events-none absolute inset-x-0 top-0 flex items-start justify-between p-5">
        <button
          onClick={() => navigate(`/experience/${experience.id}`)}
          className="pointer-events-auto inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/70 bg-[color:var(--color-paper)]/80 px-3 py-1.5 text-[13px] text-[color:var(--color-primary)] backdrop-blur-sm transition hover:bg-[color:var(--color-paper)]"
        >
          <ArrowLeft size={14} /> 退出画境
        </button>
        {/* 三种看法互切：进了画境也能直接换到「互动画境 / 一图一境」 */}
        <ExperienceModeSwitch
          experienceId={experience.id}
          current="wander"
          variant="overlay"
          className="pointer-events-auto absolute left-1/2 top-4 -translate-x-1/2"
        />
        <div className="text-right">
          <p className="font-serif text-[15px] text-[color:var(--color-ink)]">{experience.title}</p>
          <p className="text-[11px] tracking-[0.22em] text-[color:var(--color-ink)]/45">
            {experience.styleName}
          </p>
        </div>
      </div>

      {/* 进入前：一句实话 + 一个按钮 */}
      {!inside ? (
        <div className="absolute inset-x-0 bottom-0 flex justify-center pb-10">
          <div className="w-full max-w-md rounded border border-[color:var(--color-gold)]/50 bg-[color:var(--color-paper)]/92 px-6 py-5 text-center shadow-lg backdrop-blur-sm">
            <p className="mb-1 text-[11px] tracking-[0.3em] text-[color:var(--color-ink)]/45">
              画 境 漫 游
            </p>
            <p className="mb-3 font-serif text-lg text-[color:var(--color-ink)]">
              走进《{experience.title}》
            </p>
            <p className="mb-4 text-[12px] leading-relaxed text-[color:var(--color-ink)]/62">
              {manifest?.cutouts?.length
                ? `镜头会沿画中深度推进：近处的${manifest.cutouts[0].label}先掠过，中景与远景按各自深度错开。`
                : '镜头会沿画中深度推进：近景、中景、远景按深度错开，各有各的移动速度。'}
              进入后可拖拽观察、滚轮前后，点击画中元素读它的来历。
            </p>
            <button
              onClick={() => {
                control.enter();
              }}
              className="inline-flex items-center gap-2 rounded bg-[color:var(--color-primary)] px-6 py-2.5 text-sm text-white transition hover:opacity-90"
            >
              <Compass size={15} /> 进入画境
            </button>
            <p className="mt-3 text-[10.5px] leading-relaxed text-[color:var(--color-ink)]/40">
              单图深度估计，有限视角：可以推进与小幅转头，不能绕到山石背后。
            </p>
            {nextArtwork ? (
              <Link
                to={`/story/${nextArtwork.id}`}
                className="mt-3 inline-flex items-center gap-1 text-[11.5px] text-[color:var(--color-ink)]/50 underline decoration-dotted underline-offset-4 transition hover:text-[color:var(--color-primary)]"
              >
                不进画境，直接走进下一卷《{nextArtwork.title}》
                <ArrowRight size={12} />
              </Link>
            ) : null}
          </div>
        </div>
      ) : (
        <>
          {/* 进入后：底部只留操作提示与复位 */}
          <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-end justify-between p-5">
            <div className="pointer-events-auto flex items-center gap-3 rounded border border-[color:var(--color-gold)]/35 bg-[color:var(--color-paper)]/78 px-3 py-2 text-[11.5px] text-[color:var(--color-ink)]/62 backdrop-blur-sm">
              <span className="inline-flex items-center gap-1">
                <Move size={12} /> 拖拽观察
              </span>
              <span className="inline-flex items-center gap-1">
                <Compass size={12} /> 滚轮前后
              </span>
              <span className="inline-flex items-center gap-1">
                <Info size={12} /> 点击元素
              </span>
            </div>
            <div className="pointer-events-auto flex items-center gap-2">
              <button
                onClick={() => control.reset()}
                className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/60 bg-[color:var(--color-paper)]/80 px-3 py-1.5 text-[12px] text-[color:var(--color-primary)] backdrop-blur-sm"
              >
                <RotateCcw size={13} /> 视角复位
              </button>
            </div>
          </div>

          {/* 热点：点画中元素，也可用这条可访问的列表 */}
          <div className="absolute right-5 top-24 flex max-w-[168px] flex-col gap-1.5">
            {experience.hotspots.map((spot) => (
              <button
                key={spot.id}
                onClick={() => setSelectedId(spot.id)}
                onMouseEnter={() => setHoveredId(spot.id)}
                onMouseLeave={() => setHoveredId(null)}
                className={`rounded border px-2.5 py-1.5 text-left text-[11.5px] transition ${
                  selectedId === spot.id
                    ? 'border-[color:var(--color-gold)] bg-[color:var(--color-paper)] text-[color:var(--color-primary)]'
                    : 'border-[color:var(--color-gold)]/30 bg-[color:var(--color-paper)]/70 text-[color:var(--color-ink)]/60 hover:border-[color:var(--color-gold)]/70'
                }`}
              >
                {spot.title}
                {hovered?.id === spot.id ? (
                  <span className="ml-1 text-[10px] text-[color:var(--color-ink)]/40">·</span>
                ) : null}
              </button>
            ))}
          </div>
        </>
      )}

      {/* 详情面板：文化解释就在这里 */}
      {selected ? (
        <div className="absolute bottom-24 left-5 w-[min(380px,calc(100vw-2.5rem))] overflow-hidden rounded border border-[color:var(--color-gold)]/55 bg-[color:var(--color-paper)]/95 shadow-xl backdrop-blur">
          <div className="flex items-start justify-between gap-3 border-b border-[color:var(--color-ink)]/10 px-4 py-3">
            <div>
              <p className="text-[10.5px] tracking-[0.26em] text-[color:var(--color-ink)]/45">
                {selected.kicker}
              </p>
              <h3 className="font-serif text-[17px] text-[color:var(--color-ink)]">{selected.title}</h3>
            </div>
            <button onClick={() => setSelectedId(null)} className="mt-0.5 text-[color:var(--color-ink)]/40">
              <X size={16} />
            </button>
          </div>
          <div className="max-h-[42vh] overflow-y-auto px-4 py-3 text-[12.5px] leading-relaxed text-[color:var(--color-ink)]/75">
            <p className="mb-2">{selected.shortDescription}</p>
            <p className="mb-3 text-[12px] text-[color:var(--color-ink)]/58">
              {selected.visualObservation}
            </p>
            <p className="mb-3">{selected.culturalExplanation}</p>
            {selected.sourceIds?.length ? (
              <p className="flex flex-wrap gap-1.5">
                {selected.sourceIds.map((id) => (
                  <span
                    key={id}
                    className="rounded border border-[color:var(--color-gold)]/40 px-1.5 py-0.5 text-[10px] text-[color:var(--color-ink)]/50"
                  >
                    {id}
                  </span>
                ))}
              </p>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* 画境底部：看完这一卷，换下一卷。
          用户的路线上「下一卷」原本挂在一图一境结尾，现在挪到这里——
          顺序是 互动画境 → 一图一境 → 画境漫游 → 下一卷。 */}
      {inside && !showNote && nextArtwork ? (
        <div className="pointer-events-none absolute inset-x-0 bottom-12 flex justify-center">
          <Link
            to={`/story/${nextArtwork.id}`}
            data-testid="wander-next-volume"
            title={`走进下一卷：${nextArtwork.title}`}
            className="pointer-events-auto inline-flex items-center gap-2 rounded-full border border-[color:var(--color-gold)]/60 bg-[color:var(--color-paper)]/88 px-4 py-2 text-[12px] text-[color:var(--color-ink)]/75 backdrop-blur-sm transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
          >
            <span className="text-[10px] tracking-[0.2em] text-[color:var(--color-ink)]/45">走进下一卷</span>
            <span className="font-serif text-[13px] text-[color:var(--color-ink)]">{nextArtwork.title}</span>
            <span className="hidden text-[10.5px] text-[color:var(--color-ink)]/45 sm:inline">{nextArtwork.styleName}</span>
            <ArrowRight size={14} />
          </Link>
        </div>
      ) : null}

      {/* 口径说明：默认收起，但一直存在 */}
      <button
        onClick={() => setShowNote((v) => !v)}
        className="absolute bottom-5 left-1/2 -translate-x-1/2 text-[10.5px] text-[color:var(--color-ink)]/35 underline decoration-dotted"
      >
        {showNote ? '收起说明' : '这个画境是怎么做的'}
      </button>
      {showNote ? (
        <div className="absolute bottom-12 left-1/2 w-[min(520px,calc(100vw-2.5rem))] -translate-x-1/2 rounded border border-[color:var(--color-gold)]/40 bg-[color:var(--color-paper)]/95 px-4 py-3 text-[11.5px] leading-relaxed text-[color:var(--color-ink)]/62 shadow-lg">
          用 {manifest?.provenance.depth_model ?? '单目深度模型'} 对原作估计相对深度，
          再把画面做成带位移的深度网格；云气、水纹、近景枝叶由着色器逐像素驱动。
          <span className="text-[color:var(--color-ink)]/45">
            {' '}这是有限视角的 2.5D 空间，不是三维重建，也不能绕视到物体背面。
          </span>
        </div>
      ) : null}

      {/* 未加载完的一层薄幕，避免白屏 */}
      {!manifest ? (
        <div className="absolute inset-0 flex items-center justify-center bg-[#F4F1E6]">
          <p className="animate-pulse text-[13px] tracking-[0.3em] text-[color:var(--color-ink)]/40">
            正在铺开画纸…
          </p>
        </div>
      ) : null}
    </div>
  );
}