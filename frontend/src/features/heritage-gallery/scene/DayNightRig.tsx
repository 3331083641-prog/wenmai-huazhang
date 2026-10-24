/**
 * 纹脉展馆 · 时段光照与天空（白天 / 黄昏 / 夜晚）
 *
 * 设计取向：
 *  - 天穹不是 HDRI，也不是 drei 的 Sky（ACESFilmic 下会过曝），
 *    而是一个内翻的大球 + 只有 4px 宽的竖向渐变贴图：三个色标（天顶/地平线/地面）
 *    就能拉开三种气候，切时段只改贴图与灯光参数，不重建 Canvas。
 *  - 每种时段 7 个光源（半球 + 环境 + 主光 + 补光 + 3 盏室内暖光），
 *    只有主光投影：多光源投影在这套三渲二材质上只会把画面弄脏。
 *  - 曝光不在这里改 renderer —— `useTimeExposure(time)` 只给数值，
 *    由 Canvas 的 onCreated / effect 应用，组件保持幂等。
 *
 * 所有预设集中放在 TIME_PRESETS，消费方只依赖 id 与其字段，不关心内部实现。
 */

import { useEffect, useMemo, useRef } from 'react';
import type { JSX } from 'react';
import { useThree } from '@react-three/fiber';
import * as THREE from 'three';

import { EXHIBIT_WASHERS } from './lookdev';

/* ------------------------------------------------------------------ 契约类型 */

export type TimeOfDay = 'day' | 'dusk' | 'night';

export interface TimePreset {
  id: TimeOfDay;
  label: string;
  skyTop: string;
  skyHorizon: string;
  skyGround: string;
  sunColor: string;
  sunIntensity: number;
  sunPosition: [number, number, number];
  ambient: string;
  ambientIntensity: number;
  hemisphereSky: string;
  hemisphereGround: string;
  hemisphereIntensity: number;
  fill: string;
  fillIntensity: number;
  fogColor: string;
  fogNear: number;
  fogFar: number;
  /** 建议的 renderer.toneMappingExposure */
  exposure: number;
  /** 室内暖光强度倍率 0-1.6 */
  interior: number;
  /** 夜晚星空 */
  stars: boolean;
  /** 轮廓光（逆光边缘）：给屋脊与柱身一条亮边，白天不能抢主光 */
  rimColor: string;
  rimIntensity: number;
  /** PMREM 环境贴图里地面的反弹色（木地板/石台基的暖反光） */
  envGround: string;
  /** scene.environmentIntensity：金属/漆面/瓷器的反射强弱 */
  envIntensity: number;
}

/* ------------------------------------------------------------------ 预设 */

/**
 * 三种时段。
 *
 *  - day：主光沿用参考图的西北向斜射（阴影方向与十张参考图一致），
 *         但压掉了一点灰白的环境光、抬高了天顶饱和度，比旧版更通透。
 *  - dusk：主光角度压到 20° 上下，暖橙低角度光拉出长影；补光偏紫，天顶紫、地平线橙。
 *  - night：主光换成冷月（低强度、仍投影），补光更冷，
 *          室内暖光倍率拉到 1.45 让窗格透出灯光；天顶压成深蓝、地平线留一点冷灰。
 */
export const TIME_PRESETS: Record<TimeOfDay, TimePreset> = {
  day: {
    id: 'day',
    label: '白天',
    skyTop: '#5FA3CE',
    skyHorizon: '#DCEBF2',
    skyGround: '#EFE7D6',
    sunColor: '#FFF4E2',
    // 主光从 2.35 降到 1.95：让出高光余量，白灰泥墙与石台基不再一片死白，
    // 体量交给半球光与补光去撑，而不是靠主光硬顶。
    sunIntensity: 1.95,
    sunPosition: [13, 21, -9],
    ambient: '#C9D8EA',
    ambientIntensity: 0.32,
    hemisphereSky: '#C6DEF2',
    hemisphereGround: '#6E5A46',
    hemisphereIntensity: 0.92,
    fill: '#BFD4EA',
    fillIntensity: 0.48,
    fogColor: '#D9E8EF',
    fogNear: 78,
    fogFar: 275,
    exposure: 1.02,
    interior: 0.52,
    stars: false,
    rimColor: '#EAF3FF',
    rimIntensity: 0.3,
    envGround: '#8A7256',
    envIntensity: 0.62,
  },
  dusk: {
    id: 'dusk',
    label: '黄昏',
    skyTop: '#46508F',
    skyHorizon: '#F5A05E',
    skyGround: '#6A4A5B',
    sunColor: '#FF9B4A',
    sunIntensity: 2.35,
    sunPosition: [15, 5.6, 8],
    ambient: '#7B6E86',
    ambientIntensity: 0.4,
    hemisphereSky: '#F0A874',
    hemisphereGround: '#4E3B48',
    hemisphereIntensity: 0.8,
    fill: '#7E86C0',
    fillIntensity: 0.52,
    fogColor: '#D89C74',
    fogNear: 60,
    fogFar: 225,
    exposure: 1.04,
    interior: 0.88,
    stars: false,
    rimColor: '#C79BE0',
    rimIntensity: 0.36,
    envGround: '#6B4A44',
    envIntensity: 0.56,
  },
  night: {
    id: 'night',
    label: '夜晚',
    skyTop: '#0B1430',
    skyHorizon: '#1E2E52',
    skyGround: '#141C30',
    sunColor: '#C4D6F2',
    sunIntensity: 1.0,
    sunPosition: [-11, 19, 7],
    ambient: '#4A5C80',
    // 夜里最怕「整栋黑成剪影」：环境光与补光都往上抬，让屋瓦、栏杆还留得住轮廓
    ambientIntensity: 0.72,
    hemisphereSky: '#3A4F7C',
    hemisphereGround: '#3F3A44',
    hemisphereIntensity: 0.98,
    fill: '#7089BE',
    fillIntensity: 0.82,
    fogColor: '#17203A',
    fogNear: 66,
    fogFar: 245,
    exposure: 1.18,
    interior: 1.32,
    stars: true,
    rimColor: '#8FAEE4',
    rimIntensity: 0.5,
    envGround: '#2A3348',
    envIntensity: 0.8,
  },
};

/** 给 Canvas 设置曝光用；不含任何 hook，可以在 onCreated / effect / 事件里直接调用 */
export function useTimeExposure(time: TimeOfDay): number {
  return TIME_PRESETS[time].exposure;
}

/* ------------------------------------------------------------------ 天空 */

/** 天穹半径：远小于 Canvas 的 far(320)，又远大于 orbit 的 maxDistance(52) */
const SKY_SCALE = 180;

const skyTextureCache = new Map<TimeOfDay, THREE.CanvasTexture>();

/**
 * 竖向渐变贴图。
 *
 * 球体 UV：v=1 在天顶、v=0 在脚底；CanvasTexture 默认 flipY，所以画布第一行对应天顶。
 * 因此画布从上到下依次是 天顶 → 地平线(0.5) → 地面。
 */
function makeSkyTexture(preset: TimePreset): THREE.CanvasTexture {
  const height = 256;
  const canvas = document.createElement('canvas');
  canvas.width = 2;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, preset.skyTop);
    // 天顶色在 0.35 之前几乎不变，天空才有「穹」的感觉而不是一团渐变
    gradient.addColorStop(0.35, preset.skyTop);
    gradient.addColorStop(0.5, preset.skyHorizon);
    // 地平线附近留一条窄的暖/冷带，建筑轮廓压上去更清楚
    gradient.addColorStop(0.64, preset.skyHorizon);
    gradient.addColorStop(0.86, preset.skyGround);
    gradient.addColorStop(1, preset.skyGround);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 2, height);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  // 大球只有 32 段，开 mipmap 会在两极出现明显的横向接缝
  texture.generateMipmaps = false;
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  return texture;
}

function skyTextureFor(time: TimeOfDay): THREE.CanvasTexture {
  const cached = skyTextureCache.get(time);
  if (cached) return cached;
  const texture = makeSkyTexture(TIME_PRESETS[time]);
  skyTextureCache.set(time, texture);
  return texture;
}

/**
 * 同一张渐变色也用来生成 PMREM 环境贴图（GalleryEnvironment）。
 * 导出成公开 API，避免环境球再画一份渐变色标、两处天色对不上。
 */
export const createSkyTexture = skyTextureFor;

/** 释放缓存的天空贴图（仅在整页卸载时调用，正常切时段不需要） */
export function disposeSkyTextures(): void {
  skyTextureCache.forEach((texture) => texture.dispose());
  skyTextureCache.clear();
}

/* ------------------------------------------------------------------ 星空 */

const STAR_COUNT = 520;
const STAR_RADIUS = 152;

let starGeometry: THREE.BufferGeometry | null = null;

/**
 * 星点位置：球面上按 y 均匀取点（面积均匀），限制在仰角 5°~80°，
 * 地平线附近留空，免得星点糊在屋脊轮廓上。
 * 用固定种子的线性同余，保证每次重建位置一致，不会「闪一下换片天」。
 */
function getStarGeometry(): THREE.BufferGeometry {
  if (starGeometry) return starGeometry;
  const positions = new Float32Array(STAR_COUNT * 3);
  const colors = new Float32Array(STAR_COUNT * 3);
  let seed = 20240917;
  const rand = () => {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 4294967296;
  };
  const cold = new THREE.Color('#DCE6FF');
  const warm = new THREE.Color('#FFF3DF');
  for (let i = 0; i < STAR_COUNT; i += 1) {
    const y = 0.08 + rand() * 0.84;
    const ring = Math.sqrt(Math.max(0, 1 - y * y));
    const angle = rand() * Math.PI * 2;
    const radius = STAR_RADIUS * (0.94 + rand() * 0.08);
    positions[i * 3] = Math.cos(angle) * ring * radius;
    positions[i * 3 + 1] = y * radius;
    positions[i * 3 + 2] = Math.sin(angle) * ring * radius;

    const brightness = 0.4 + rand() * 0.6;
    const color = cold.clone().lerp(warm, rand() * 0.55).multiplyScalar(brightness);
    colors[i * 3] = color.r;
    colors[i * 3 + 1] = color.g;
    colors[i * 3 + 2] = color.b;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  starGeometry = geometry;
  return geometry;
}

/** 夜间星点：只画点，不做逐帧动画，切回白天时整棵子树卸载 */
function NightStars(): JSX.Element {
  const geometry = useMemo(() => getStarGeometry(), []);
  return (
    <points geometry={geometry} renderOrder={-1} frustumCulled={false}>
      <pointsMaterial
        size={1.5}
        sizeAttenuation={false}
        vertexColors
        transparent
        opacity={0.85}
        depthWrite={false}
        toneMapped={false}
        fog={false}
      />
    </points>
  );
}

/* ------------------------------------------------------------------ 灯光 */

/** 阴影参数集中在这里：改一处就够，切换时段时元组引用不变，不会触发阴影图重建 */
const SHADOW_MAP_SIZE: [number, number] = [1536, 1536];
/**
 * 阴影相机范围：模型主体（建筑 + 台阶）投影在 ±11 m 内，旧值 ±11 但 far=60 会把
 * 大半深度精度浪费在远处。这里收到 ±11.5 / near 6 / far 55，
 * 同时把贴图从 2048 降到 1536（显存与填充率都省 44%），
 * 净效果是「每米纹素更多」——阴影边缘反而更实，不会更糊。
 */
const SHADOW_CAMERA: [number, number, number, number, number, number] = [-11.5, 11.5, 11.5, -11.5, 6, 55];

/**
 * 三盏室内暖光。位置沿用旧场景的手调值（一层、二层、顶棚洗光），
 * 强度用 base × preset.interior 缩放：白天几乎只补暗部，夜里让窗格透出灯光。
 *
 * 旧值（17 / 14 / 24）在 0.4~0.9 m 的近距上会把顶棚直接顶到 1.0 以上的雪白，
 * 这是「室内一片死白」的主因；现在整体下调，把亮度交给环境光与洗墙灯去铺。
 */
const INTERIOR_LIGHTS: {
  position: [number, number, number];
  base: number;
  distance: number;
  color: string;
}[] = [
  { position: [0, 2.6, 0.4], base: 8.5, distance: 11, color: '#ffd4a4' },
  { position: [0, 5.05, -0.6], base: 6.5, distance: 10, color: '#ffdcb8' },
  { position: [0, 4.85, -0.2], base: 9, distance: 5.4, color: '#ffeecd' },
];

/* ------------------------------------------------------------------ 组件 */

/**
 * 洗墙灯：给主展墙（作品最密的三面）一盏无阴影的软边 spot。
 * spotLight 的 target 必须是场景里的对象，所以在挂载时手动塞进 scene、
 * 卸载时取出来——不这么做，灯会朝着默认的 (0,0,0) 打，墙面照不到。
 */
function WallWasher({
  position,
  target,
  color,
  intensity,
  distance,
  angle,
}: {
  position: [number, number, number];
  target: [number, number, number];
  color: string;
  intensity: number;
  distance: number;
  angle: number;
}): JSX.Element {
  const light = useRef<THREE.SpotLight>(null);
  const { scene } = useThree();
  useEffect(() => {
    const spot = light.current;
    if (!spot) return undefined;
    spot.target.position.set(...target);
    scene.add(spot.target);
    return () => {
      scene.remove(spot.target);
    };
  }, [scene, target]);
  return (
    <spotLight
      ref={light}
      position={position}
      color={color}
      intensity={intensity}
      distance={distance}
      angle={angle}
      penumbra={0.9}
      decay={2}
      castShadow={false}
    />
  );
}

/**
 * 时段灯光总成：天空球 + 雾 + 光源。
 *
 * 幂等：只把 preset 的数值挂到已有对象上（颜色/强度/位置都是对象属性），
 * 切换 time 不会重建 Canvas，也不会重建灯光/阴影对象。
 */
export function DayNightRig({ time }: { time: TimeOfDay }): JSX.Element {
  const preset = TIME_PRESETS[time];
  const skyTexture = useMemo(() => skyTextureFor(time), [time]);
  const exposureIndex = time === 'day' ? 0 : time === 'dusk' ? 1 : 2;

  return (
    <>
      {/* 雾挂在 scene 上：远处衰减成天色，天穹材质关掉 fog，避免球被自身雾色糊掉 */}
      <fog attach="fog" args={[preset.fogColor, preset.fogNear, preset.fogFar]} />

      <mesh name="time-sky-dome" scale={SKY_SCALE} renderOrder={-2}>
        <sphereGeometry args={[1, 32, 16]} />
        <meshBasicMaterial
          map={skyTexture}
          side={THREE.BackSide}
          depthWrite={false}
          toneMapped={false}
          fog={false}
        />
      </mesh>

      {preset.stars && <NightStars />}

      {/* 半球光：三渲二只有 4 级色带，天光不够整片会压暗，所以它承担主要底光 */}
      <hemisphereLight
        color={preset.hemisphereSky}
        groundColor={preset.hemisphereGround}
        intensity={preset.hemisphereIntensity}
      />

      {/* 环境光：只压死黑，不做主光 */}
      <ambientLight color={preset.ambient} intensity={preset.ambientIntensity} />

      {/* 主光：唯一投影的光源。方向与参考图阴影一致（白天西北向），夜晚是冷月 */}
      <directionalLight
        position={preset.sunPosition}
        color={preset.sunColor}
        intensity={preset.sunIntensity}
        castShadow
        shadow-mapSize={SHADOW_MAP_SIZE}
        shadow-bias={-0.0005}
        shadow-normalBias={0.03}
        shadow-radius={4}
      >
        <orthographicCamera attach="shadow-camera" args={SHADOW_CAMERA} />
      </directionalLight>

      {/* 补光：不提阴影，只把背光面从死黑里拉回来 */}
      <directionalLight position={[-12, 9, 13]} color={preset.fill} intensity={preset.fillIntensity} />

      {/* 轮廓光：从主光反方向斜后方打，给屋脊/柱身一条细亮边，夜里靠它保住剪影层次 */}
      <directionalLight position={[-6, 12, 14]} color={preset.rimColor} intensity={preset.rimIntensity} />

      {/* 室内暖光：大范围低强度，靠衰减铺开，不打硬斑点 */}
      {INTERIOR_LIGHTS.map((light) => (
        <pointLight
          key={light.position.join(',')}
          position={light.position}
          color={light.color}
          intensity={light.base * preset.interior}
          distance={light.distance}
          decay={2}
        />
      ))}

      {/* 展品重点照明：作品最密的三面主墙，强度按时段给 */}
      {EXHIBIT_WASHERS.map((washer) => (
        <WallWasher
          key={washer.key}
          position={washer.position}
          target={washer.target}
          color={washer.color}
          intensity={washer.intensity[exposureIndex]}
          distance={washer.distance}
          angle={washer.angle}
        />
      ))}
    </>
  );
}