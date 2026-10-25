import { useEffect, useMemo, useRef } from 'react';
import { useFrame, useLoader, useThree, type ThreeEvent } from '@react-three/fiber';
import * as THREE from 'three';
import { paintingFragmentShader, paintingVertexShader } from './shaders';
import { resolveWorldAsset, uvToPlane, type PaintingWorldManifest } from './world';
import { fitArtworkCamera, pickHotspotFromUv } from './geometry';

/** 画境运行期状态，DOM 层与探针都读这一个对象，避免两套真相。 */
export interface WorldRuntime {
  phase: 'idle' | 'entering' | 'inside';
  progress: number;
  yawDeg: number;
  pitchDeg: number;
  distance: number;
  targetYawDeg: number;
  targetPitchDeg: number;
  targetDistance: number;
  /** 入画停稳后的距离，视角复位用它（由 CameraRig 写入）。 */
  restDistance: number;
  frozen: boolean;
  fps: number;
  degraded: boolean;
  selectedId: string | null;
  hoveredId: string | null;
  hotspots: Array<{ id: string; x: number; y: number; visible: boolean; depth: number }>;
  frame: number;
  /** 着色器参数。验收时要能「同机位只改一项」来做因果对照。 */
  tuning: { amplitude: number; haze: number; mist: number; ripple: number; sway: number; showCutout: number };
}

export interface WorldControl {
  enter: () => void;
  exit: () => void;
  reset: () => void;
  setYawDeg: (v: number) => void;
  setPitchDeg: (v: number) => void;
  setDistance: (v: number) => void;
  setFrozen: (v: boolean) => void;
  select: (id: string | null) => void;
  runtime: WorldRuntime;
}

const PIVOT = new THREE.Vector3(0, 0, 0);

export function createRuntime(): WorldRuntime {
  return {
    phase: 'idle',
    progress: 0,
    yawDeg: 0,
    pitchDeg: 0,
    distance: 0,
    targetYawDeg: 0,
    targetPitchDeg: 0,
    targetDistance: 0,
    restDistance: 0,
    frozen: false,
    fps: 0,
    degraded: false,
    selectedId: null,
    hoveredId: null,
    hotspots: [],
    frame: 0,
    tuning: { amplitude: 0.42, haze: 0.10, mist: 0.26, ripple: 1, sway: 1, showCutout: 1 },
  };
}

/** 缓出，用在中段更快、末段收住，符合「推进后停稳」的观感。 */
const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

function texturesFor(manifest: PaintingWorldManifest, baseUrl: string) {
  return [
    resolveWorldAsset(baseUrl, manifest.surface?.file ?? manifest.art.file),
    resolveWorldAsset(baseUrl, manifest.depth.file),
    resolveWorldAsset(baseUrl, manifest.masks.file),
    resolveWorldAsset(baseUrl, manifest.backdrop.file),
  ] as const;
}

/* -------------------------------------------------------------------------- */
/* 深度网格                                                                    */
/* -------------------------------------------------------------------------- */
function DepthMesh({
  manifest,
  art,
  depth,
  masks,
  uniforms,
  control,
  onHover,
}: {
  manifest: PaintingWorldManifest;
  art: THREE.Texture;
  depth: THREE.Texture;
  masks: THREE.Texture;
  uniforms: Record<string, THREE.IUniform>;
  control: WorldControl;
  onHover: (id: string | null) => void;
}) {
  const aspect = manifest.art.aspect;
  const height = manifest.camera.plane_height;
  const width = height * aspect;

  // 分段数折中：192×128 已能让 768px 宽的深度贴图逐像素起伏，
  // 再高只是在顶点着色器里多烧 GPU，看不出差别。
  const geometry = useMemo(
    () => new THREE.PlaneGeometry(width, height, 192, 128),
    [width, height]
  );
  useEffect(() => () => geometry.dispose(), [geometry]);

  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: paintingVertexShader,
        fragmentShader: paintingFragmentShader,
        uniforms,
      }),
    [uniforms]
  );
  useEffect(() => () => material.dispose(), [material]);

  /** 命中哪一处热点：取 uv 距离最近且落在半径内的那个。 */
  const pickAt = (event: ThreeEvent<PointerEvent | MouseEvent>): string | null => {
    const uv = event.uv;
    if (!uv) return null;
    return pickHotspotFromUv(manifest.hotspots, uv.x, uv.y);
  };

  return (
    <mesh
      geometry={geometry}
      material={material}
      onPointerMove={(event) => {
        event.stopPropagation();
        onHover(pickAt(event));
      }}
      onPointerOut={() => onHover(null)}
      onClick={(event) => {
        event.stopPropagation();
        const id = pickAt(event);
        if (id) control.select(id);
      }}
    />
  );
}

/* -------------------------------------------------------------------------- */
/* 近景抠像：入画时从视野一侧掠过                                              */
/* -------------------------------------------------------------------------- */
function NearCutout({
  manifest,
  baseUrl,
  control,
}: {
  manifest: PaintingWorldManifest;
  baseUrl: string;
  control: WorldControl;
}) {
  const cut = manifest.cutouts[0];
  const url = cut ? resolveWorldAsset(baseUrl, cut.file) : null;
  const tex = useLoader(THREE.TextureLoader, url ?? resolveWorldAsset(baseUrl, manifest.art.file));

  const meshRef = useRef<THREE.Mesh | null>(null);
  const aspect = manifest.art.aspect;
  const H = manifest.camera.plane_height;
  const amp = manifest.camera.depth_amplitude;

  useEffect(() => {
    if (!tex) return;
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 4;
  }, [tex]);

  const dims = useMemo(() => {
    if (!cut) return { w: 0, h: 0, cx: 0, cy: 0, z: 0 };
    const [bx, by, bw, bh] = cut.bbox_norm;
    const w = bw * aspect * H;
    const h = bh * H;
    return {
      w,
      h,
      cx: (bx + bw / 2 - 0.5) * aspect * H,
      cy: (0.5 - (by + bh / 2)) * H,
      // 略微比最近的网格再往前一点，保证它真的「在镜头前」
      z: amp * (cut.depth ?? 1.06),
    };
  }, [cut, aspect, H, amp]);

  useFrame((state) => {
    const mesh = meshRef.current;
    if (!mesh || !cut) return;
    mesh.visible = control.runtime.tuning.showCutout > 0.5;
    // 极轻的呼吸式位移：让它读作「前景枝叶」而不是贴纸
    const t = state.clock.elapsedTime;
    mesh.position.z = dims.z + Math.sin(t * 1.1) * 0.004;
    mesh.position.x = dims.cx + Math.cos(t * 0.7) * 0.0022;
  });

  if (!cut) return null;
  return (
    <mesh ref={meshRef} position={[dims.cx, dims.cy, dims.z]} renderOrder={2}
      onClick={(event) => {
        if (!event.uv) return;
        event.stopPropagation();
        const [bx, by, bw, bh] = cut.bbox_norm;
        const x = bx + event.uv.x * bw;
        const y = by + (1-event.uv.y) * bh;
        const id = pickHotspotFromUv(manifest.hotspots, x, 1-y);
        if (id) control.select(id);
      }}>
      <planeGeometry args={[dims.w, dims.h]} />
      <meshBasicMaterial map={tex} transparent depthWrite={false} toneMapped={false} />
    </mesh>
  );
}

/* -------------------------------------------------------------------------- */
/* 兜底背景                                                                    */
/* -------------------------------------------------------------------------- */
function Backdrop({
  manifest,
  tex,
  control,
}: {
  manifest: PaintingWorldManifest;
  tex: THREE.Texture;
  control: WorldControl;
}) {
  const H = manifest.camera.plane_height;
  const W = H * manifest.art.aspect;
  const matRef = useRef<THREE.MeshBasicMaterial | null>(null);

  useFrame(() => {
    const mat = matRef.current;
    if (!mat) return;
    // 画外时为 0：透出纸色，画作像一张悬在纸上的画；
    // 入画过程中渐显，保证斜看时画面边缘之外仍有东西接着。
    const p = control.runtime.phase === 'idle' ? 0 : 0.06 + 0.94 * control.runtime.progress;
    mat.opacity = mat.opacity + (p - mat.opacity) * 0.12;
  });

  return (
    <mesh position={[0, 0, -0.55]} renderOrder={-1}>
      <planeGeometry args={[W * 2.2, H * 2.2]} />
      <meshBasicMaterial
        ref={matRef}
        map={tex}
        transparent
        opacity={0}
        depthWrite={false}
        toneMapped={false}
      />
    </mesh>
  );
}

/* -------------------------------------------------------------------------- */
/* 热点标记                                                                    */
/* -------------------------------------------------------------------------- */
function HotspotDots({
  manifest,
  control,
  selectedId,
}: {
  manifest: PaintingWorldManifest;
  control: WorldControl;
  selectedId: string | null;
}) {
  const amp = manifest.camera.depth_amplitude;
  const aspect = manifest.art.aspect;
  const H = manifest.camera.plane_height;

  return (
    <group>
      {manifest.hotspots.map((spot) => {
        const p = uvToPlane(spot.x, spot.y, aspect, H);
        const z = spot.depth * amp + 0.012;
        const active = selectedId === spot.id;
        return (
          <group key={spot.id} position={[p.x, p.y, z]}>
            <mesh
              onClick={(event) => {
                event.stopPropagation();
                control.select(spot.id);
              }}
              onPointerOver={(event) => {
                event.stopPropagation();
                control.runtime.hoveredId = spot.id;
                document.body.style.cursor = 'pointer';
              }}
              onPointerOut={() => {
                control.runtime.hoveredId = null;
                document.body.style.cursor = '';
              }}
            >
              <circleGeometry args={[active ? 0.026 : 0.018, 28]} />
              <meshBasicMaterial
                color={active ? '#B99A5B' : '#426C62'}
                transparent
                opacity={active ? 0.95 : 0.62}
                depthWrite={false}
                toneMapped={false}
              />
            </mesh>
            {/* 外圈：给一点「可点」的暗示，不做呼吸动画以免抢戏 */}
            <mesh>
              <ringGeometry args={[active ? 0.03 : 0.023, active ? 0.036 : 0.028, 32]} />
              <meshBasicMaterial
                color={active ? '#B99A5B' : '#F4F1E6'}
                transparent
                opacity={active ? 0.9 : 0.5}
                depthWrite={false}
                toneMapped={false}
              />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

/* -------------------------------------------------------------------------- */
/* 相机：入场推进 + 拖拽观察 + 有限前后移动                                     */
/* -------------------------------------------------------------------------- */
function CameraRig({
  manifest,
  control,
}: {
  manifest: PaintingWorldManifest;
  control: WorldControl;
}) {
  const { camera, gl, size } = useThree();
  const cam = manifest.camera;
  const framing = fitArtworkCamera({planeHeight:cam.plane_height,planeWidth:cam.plane_width,
    fov:cam.fov,amplitude:cam.depth_amplitude,width:size.width,height:size.height,
    entryScale:cam.entry.from_scale});
  const startDistance = framing.start;
  const insideDistance = framing.rest;
  const nearDistance = framing.near;

  /** 起手就把画外位置摆好，避免首帧闪一下 */
  const stateRef = useRef({
    distance: startDistance,
    yaw: 0,
    pitch: 0,
    entryStart: 0,
    entryFrom: startDistance,
    entryTo: insideDistance,
    active: false,
  });

  useEffect(() => {
    const rt = control.runtime;
    rt.distance = startDistance;
    rt.targetDistance = startDistance;
    rt.restDistance = insideDistance;
    if (!rt.degraded) {
      rt.phase = 'idle';
    }
  }, [control, startDistance, insideDistance]);

  // 拖拽 / 滚轮：直接改 target，由 useFrame 做阻尼跟随
  useEffect(() => {
    const el = gl.domElement;
    let dragging = false;
    let lastX = 0;
    let lastY = 0;

    const onDown = (event: PointerEvent) => {
      // 还没入场时不允许拖拽/滚轮：否则入场卡片还在，画面已经被推进了，
      // 用户会以为「点按钮之前画面就乱了」。
      if (control.runtime.phase !== 'inside') return;
      if (event.button !== 0) return;
      dragging = true;
      lastX = event.clientX;
      lastY = event.clientY;
      el.setPointerCapture?.(event.pointerId);
    };
    const onMove = (event: PointerEvent) => {
      if (!dragging) return;
      const rt = control.runtime;
      const dx = event.clientX - lastX;
      const dy = event.clientY - lastY;
      lastX = event.clientX;
      lastY = event.clientY;
      const yaw = clamp(rt.targetYawDeg - dx * 0.16, -cam.yaw_limit_deg, cam.yaw_limit_deg);
      const pitch = clamp(rt.targetPitchDeg + dy * 0.11, -cam.pitch_limit_deg, cam.pitch_limit_deg);
      rt.targetYawDeg = yaw;
      rt.targetPitchDeg = pitch;
    };
    const onUp = () => {
      dragging = false;
    };
    const onWheel = (event: WheelEvent) => {
      if (control.runtime.phase !== 'inside') return;
      event.preventDefault();
      const rt = control.runtime;
      const next = clamp(rt.targetDistance + event.deltaY * 0.0016, nearDistance, startDistance);
      rt.targetDistance = next;
    };

    el.addEventListener('pointerdown', onDown);
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => {
      el.removeEventListener('pointerdown', onDown);
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      el.removeEventListener('wheel', onWheel);
    };
  }, [gl, control, cam.yaw_limit_deg, cam.pitch_limit_deg, insideDistance, startDistance, nearDistance]);

  useFrame((state, delta) => {
    const rt = control.runtime;
    const s = stateRef.current;
    const dt = Math.min(delta, 0.05);

    // 入场：把 distance 从画外推到画内，单调、无回弹
    if (rt.phase === 'entering') {
      if (!s.active) {
        s.active = true;
        s.entryFrom = s.distance;
        s.entryTo = insideDistance;
        s.entryStart = state.clock.elapsedTime;
      }
      const dur = cam.entry.duration_ms / 1000;
      const t = Math.min(1, (state.clock.elapsedTime - s.entryStart) / dur);
      rt.progress = t;
      s.distance = s.entryFrom + (s.entryTo - s.entryFrom) * easeInOut(t);
      rt.targetDistance = s.distance;
      if (t >= 1) {
        rt.phase = 'inside';
        s.active = false;
      }
    } else {
      s.active = false;
    }

    // 阻尼跟随：越近越稳（近处角速度快，阻尼也要更强一点）
    const k = 1 - Math.exp(-dt * (s.distance < 1.0 ? 7.5 : 9.5));
    s.yaw += (rt.targetYawDeg - s.yaw) * k;
    s.pitch += (rt.targetPitchDeg - s.pitch) * k;
    s.distance += (rt.targetDistance - s.distance) * k;

    rt.yawDeg = s.yaw;
    rt.pitchDeg = s.pitch;
    rt.distance = s.distance;

    const yawRad = THREE.MathUtils.degToRad(s.yaw);
    const pitchRad = THREE.MathUtils.degToRad(s.pitch);
    camera.position.set(
      PIVOT.x + Math.sin(yawRad) * Math.cos(pitchRad) * s.distance,
      PIVOT.y + Math.sin(pitchRad) * s.distance,
      PIVOT.z + Math.cos(yawRad) * Math.cos(pitchRad) * s.distance
    );
    camera.lookAt(PIVOT);
    camera.updateMatrixWorld();
    rt.frame += 1;
  });

  return null;
}

function clamp(v: number, min: number, max: number) {
  return v < min ? min : v > max ? max : v;
}

/* -------------------------------------------------------------------------- */
export interface WorldSceneProps {
  manifest: PaintingWorldManifest;
  baseUrl: string;
  control: WorldControl;
  selectedId: string | null;
  onHoverChange: (id: string | null) => void;
  onFps: (fps: number) => void;
}

export function WorldScene({
  manifest,
  baseUrl,
  control,
  selectedId,
  onHoverChange,
  onFps,
}: WorldSceneProps) {
  const [artUrl, depthUrl, masksUrl, backdropUrl] = texturesFor(manifest, baseUrl);
  const [art, depth, masks, backdrop] = useLoader(THREE.TextureLoader, [
    artUrl,
    depthUrl,
    masksUrl,
    backdropUrl,
  ]);

  useEffect(() => {
    // 关键：自定义 ShaderMaterial 不会自动追加线性→sRGB 输出编码。
    // 若把贴图标成 sRGB（硬件解码成线性）再直接写出，整幅画会被压暗一档
    // （实测中心均值 120/98/69，明显偏离原作的设色）。
    // 这里全程按存储值处理：贴图 NoColorSpace，着色器输出即原图数值，
    // 屏幕上看到的就是原作的颜色，且与水/雾混色也保持在同一个色彩空间里。
    art.colorSpace = THREE.NoColorSpace;
    art.anisotropy = 8;
    backdrop.colorSpace = THREE.SRGBColorSpace;
    backdrop.anisotropy = 4;
    // 深度与遮罩必须当成数据读：一旦被当成 sRGB 解码，16 位打包就废了
    depth.colorSpace = THREE.NoColorSpace;
    depth.minFilter = THREE.LinearFilter;
    depth.magFilter = THREE.LinearFilter;
    depth.generateMipmaps = false;
    masks.colorSpace = THREE.NoColorSpace;
    masks.minFilter = THREE.LinearFilter;
    masks.magFilter = THREE.LinearFilter;
    masks.generateMipmaps = false;
  }, [art, depth, masks, backdrop]);

  const uniforms = useMemo<Record<string, THREE.IUniform>>(
    () => ({
      uArt: { value: art },
      uDepth: { value: depth },
      uMasks: { value: masks },
      uTime: { value: 0 },
      uAmplitude: { value: manifest.camera.depth_amplitude },
      // 空气透视只做「一点点」：实测 0.16 会把蓝通道抬高近 20，
      // 青绿设色被洗淡，这里收到 0.10，保留空间感又不改原作色。
      uHaze: { value: 0.10 },
      uMist: { value: 0.26 },
      uRipple: { value: 1.0 },
      uSway: { value: 1.0 },
      uPaper: { value: new THREE.Color('#F4F1E6') },
    }),
    [art, depth, masks, manifest.camera.depth_amplitude]
  );

  const frames = useRef({ count: 0, elapsed: 0 });

  // 清单里的振幅先落进 runtime.tuning，之后一切调节都写这一个对象
  useEffect(() => {
    const t = control.runtime.tuning;
    t.amplitude = manifest.camera.depth_amplitude;
    t.haze = 0.10;
    t.mist = 0.26;
    t.ripple = 1;
    t.sway = 1;
  }, [control, manifest.camera.depth_amplitude]);

  useFrame((state, delta) => {
    const rt = control.runtime;
    if (!rt.frozen) {
      uniforms.uTime.value = state.clock.elapsedTime;
    }
    // 参数每帧从 runtime 同步：验收可实时改一项看因果
    uniforms.uAmplitude.value = rt.tuning.amplitude;
    uniforms.uHaze.value = rt.tuning.haze;
    uniforms.uMist.value = rt.tuning.mist;
    uniforms.uRipple.value = rt.tuning.ripple;
    uniforms.uSway.value = rt.tuning.sway;
    // 热点投影到屏幕坐标，供 DOM 层与探针使用
    const cam = state.camera;
    const H = manifest.camera.plane_height;
    const W = H * manifest.art.aspect;
    const v = new THREE.Vector3();
    rt.hotspots = manifest.hotspots.map((spot) => {
      v.set((spot.x - 0.5) * W, (0.5 - spot.y) * H, spot.depth * manifest.camera.depth_amplitude);
      v.project(cam);
      return {
        id: spot.id,
        x: (v.x + 1) / 2,
        y: (1 - v.y) / 2,
        visible: v.z > -1 && v.z < 1 && Math.abs(v.x) < 1.05 && Math.abs(v.y) < 1.05,
        depth: spot.depth,
      };
    });

    frames.current.count += 1;
    frames.current.elapsed += delta;
    if (frames.current.elapsed >= 0.5) {
      onFps(frames.current.count / frames.current.elapsed);
      frames.current.count = 0;
      frames.current.elapsed = 0;
    }
  });

  return (
    <>
      <Backdrop manifest={manifest} tex={backdrop} control={control} />
      <DepthMesh
        manifest={manifest}
        art={art}
        depth={depth}
        masks={masks}
        uniforms={uniforms}
        control={control}
        onHover={onHoverChange}
      />
      <NearCutout manifest={manifest} baseUrl={baseUrl} control={control} />
      <HotspotDots manifest={manifest} control={control} selectedId={selectedId} />
      <CameraRig manifest={manifest} control={control} />
    </>
  );
}
