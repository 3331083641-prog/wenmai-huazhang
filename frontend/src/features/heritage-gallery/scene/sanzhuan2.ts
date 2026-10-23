/**
 * 三渲二（cel / toon）运行时材质转换：把 Blender 导出的 GLB 场景改写成
 * 「阶梯色带 + 墨线轮廓」的动画片质感。
 *
 * 一、色带（bands）
 *   每个 `M_<key>` 材质换成 MeshToonMaterial，并把 gradientMap 设为一张
 *   3 级的 DataTexture（0.55 / 0.80 / 1.0，需求文档原为 0.42 / 0.74 / 1.0，
 *   暗档抬高见下方 THREE_TONE_STOPS 注释）。MeshToonMaterial 只采样这张
 *   贴图、不做插值，于是明暗被切成几块硬边色阶，正是「三渲二」的三层调子。
 *   20 个颜色键共用同一张渐变贴图，26 个网格因此只共享 <= 20 个材质，
 *   避免每个网格一套材质带来的状态切换与显存抖动。
 *
 * 二、轮廓（outline）
 *   用经典的「背面外扩」（inverted hull）：同一几何体再画一遍，材质取
 *   BackSide，顶点沿法线外推。这里既没有复制几何体，也没有用「放大一倍的
 *   克隆」，原因有两个：
 *     - 本场景的网格是 Blender 里按材质合并出来的，单个网格的原点往往不在
 *       部件中心（MERGE_* 系列尤其明显）。缩放克隆以物体原点为中心放大，
 *       偏离中心的部分线宽会明显变粗甚至整体错位，合并几何体没法描边。
 *     - 缩放克隆会在切线方向变粗、纵深方向错位，近景夸张、远景糊成一片，
 *       无法保证屏幕上恒定的墨线粗细。
 *   所以在 onBeforeCompile 注入的顶点着色器里按「视空间法线」位移，位移量
 *   = 目标像素宽 × 该顶点处「一像素对应的世界长度」：
 *     - 透视相机：worldPerPixel = 2 * tan(fov / 2) / viewportHeight * viewDepth，
 *       乘上 viewDepth 后轮廓在屏幕上恒为固定像素宽，推拉镜头都不变；
 *     - 正交相机：worldPerPixel = (top - bottom) / zoom / viewportHeight。
 *   outline.onBeforeRender 每帧读取当前相机更新 uniform，因此在纯函数式
 *   模块里也能稳定保持 1.2~2.5 CSS 像素线宽（默认 1.6）。位移只发生在视空间，
 *   与物体原点无关，合并几何体同样能正确包边。
 *   深度方面只替换 `<project_vertex>`，保留其后的 `<logdepthbuf_vertex>`，
 *   所以开启 logarithmicDepthBuffer 时依然成立（对数深度基于改写后的
 *   gl_Position 继续计算）；也因此不需要 polygonOffset —— 外扩后的背面上
 *   本来就在正面之下，再加 polygonOffset 反而会把掠射角处的描边推没。
 *
 * 说明：所有材质都在模块内缓存并被多处共享，因此本模块只创建、不修改外部
 * 传入的材质；释放请统一调用 disposeToonResources()。
 */

import * as THREE from 'three';

/** 单次 applySanzhuan2 的统计结果。 */
export interface ApplyToonResult {
  /** 被改写的网格数量。 */
  meshes: number;
  /** 本次用到的不同 toon 材质数量（受调色板键数量上限约束）。 */
  materials: number;
  /** 改写后存在的墨线轮廓网格数量（幂等调用不会翻倍）。 */
  outlined: number;
}

/** 三渲二转换可选项。 */
export interface ToonOption {
  /** 是否生成墨线轮廓，默认 true；false 时完全跳过轮廓创建。 */
  outline?: boolean;
  /** 轮廓线宽（CSS 像素），默认 1.6，建议 1.2~2.5。 */
  outlineWidthPx?: number;
  /** 色带级数，默认 3（三渲二的三层调子）。 */
  gradientSteps?: number;
  /** 材质名无法匹配调色板时的兜底键，默认 'stone'。 */
  fallbackKey?: string;
  /** 是否对屋瓦 / 木构压暗基础色，默认 true。 */
  shadingBias?: boolean;
}

/**
 * 调色板：sRGB 0..1，键与 Blender 材质 `M_<key>` 的后缀一一对应。
 * 注意这里是 sRGB 数值，进入 three.js 工作色彩空间时会做一次转换。
 */
export const TOON_PALETTE: Record<string, [number, number, number]> = {
  roof_tile: [0.322, 0.365, 0.408],
  roof_tile_b: [0.372, 0.412, 0.448],
  roof_slate: [0.212, 0.243, 0.278],
  roof_ridge: [0.259, 0.29, 0.325],
  timber: [0.545, 0.353, 0.235],
  timber_dark: [0.29, 0.18, 0.125],
  timber_warm: [0.639, 0.427, 0.271],
  wood_light: [0.706, 0.514, 0.337],
  wall: [0.937, 0.902, 0.831],
  wall_shadow: [0.812, 0.768, 0.694],
  stone: [0.725, 0.706, 0.655],
  stone_dark: [0.545, 0.529, 0.49],
  stone_warm: [0.784, 0.753, 0.69],
  paving: [0.659, 0.643, 0.604],
  paving_b: [0.706, 0.678, 0.628],
  gravel: [0.76, 0.735, 0.678],
  red: [0.698, 0.227, 0.173],
  red_deep: [0.478, 0.145, 0.114],
  gold: [0.71, 0.545, 0.216],
  gold_light: [0.847, 0.702, 0.365],
  plant: [0.31, 0.478, 0.227],
  plant_dark: [0.212, 0.345, 0.161],
  plant_light: [0.408, 0.565, 0.259],
  bamboo: [0.435, 0.545, 0.239],
  flower: [0.792, 0.4, 0.412],
  porcelain: [0.855, 0.888, 0.871],
  porcelain_bl: [0.235, 0.353, 0.545],
  ink: [0.125, 0.11, 0.106],
  paper: [0.965, 0.945, 0.902],
  lamp_glow: [1, 0.737, 0.443],
};

/** 材质名无法匹配时使用的兜底调色板键。 */
const DEFAULT_FALLBACK_KEY = 'stone';

/** 兜底三元组，避免在严格索引检查下取到 undefined。 */
const FALLBACK_TRIPLE: [number, number, number] = [0.725, 0.706, 0.655];

/**
 * 逐键明暗偏置：屋瓦与木构整体压暗，墙 / 纸略提亮，
 * 让 3 级色带在同一盏灯下仍然分出清晰的三个层次，而不是全挤在亮部。
 */
const KEY_SHADING_BIAS: Record<string, number> = {
  roof_tile: 0.9,
  roof_tile_b: 0.9,
  roof_slate: 0.88,
  roof_ridge: 0.9,
  timber: 0.94,
  timber_dark: 0.97,
  timber_warm: 0.94,
  wood_light: 0.94,
  wall: 1.04,
  wall_shadow: 1,
  paper: 1.04,
  stone: 0.97,
  stone_dark: 0.98,
  stone_warm: 0.98,
  paving: 0.96,
  paving_b: 1,
  gravel: 1.02,
  red: 0.98,
  red_deep: 0.99,
  gold: 1,
  gold_light: 1.04,
  plant: 0.96,
  plant_dark: 0.98,
  plant_light: 1,
  bamboo: 0.98,
  flower: 1.02,
  porcelain: 1.06,
  porcelain_bl: 0.98,
  ink: 1,
  lamp_glow: 1,
};

/** 材质名前缀，Blender 侧统一为 M_<key>。 */
const KEY_PREFIX = 'M_';

/** 墨线颜色：比 ink 更暗更暖，避免纯黑描边。 */
const OUTLINE_COLOR = 0x1a1208;

const DEFAULT_OUTLINE_WIDTH_PX = 1.6;
const MIN_OUTLINE_WIDTH_PX = 0.5;
const MAX_OUTLINE_WIDTH_PX = 6;

const DEFAULT_GRADIENT_STEPS = 3;
const MIN_GRADIENT_STEPS = 2;
const MAX_GRADIENT_STEPS = 8;

/**
 * 3 级色带的固定调子。需求文档给的是 0.42 / 0.74 / 1.0；本轮把最暗一档抬到 0.55，
 * 因为 0.42 在室内机位（梁架、檐下、二层仰视）会把背光面整片压死，
 * 只留一条线还看得见。抬到 0.55 后仍保持三级硬边，但暗部留得住材质本色。
 */
const THREE_TONE_STOPS: readonly number[] = [0.55, 0.80, 1];
const TONE_FLOOR = 0.55;

const SANZHUAN2_FLAG = 'sanzhuan2';

/** 共享渐变贴图缓存，按级数索引。 */
const gradientCache = new Map<number, THREE.DataTexture>();

/** toon 材质缓存：`key|steps|bias` -> 材质，26 个网格共享 <= 20 个材质。 */
const toonMaterialCache = new Map<string, THREE.MeshToonMaterial>();

interface OutlineUniforms {
  uSanzhuanOutlineWidthPx: { value: number };
  uSanzhuanOutlinePixelScale: { value: number };
  uSanzhuanOutlineOrthoScale: { value: number };
  uSanzhuanOutlineIsOrtho: { value: number };
}

interface OutlineRig {
  material: THREE.MeshBasicMaterial;
  uniforms: OutlineUniforms;
}

/** 轮廓材质按线宽缓存（通常只有一种线宽，即一个共享材质）。 */
const outlineRigCache = new Map<number, OutlineRig>();

/** 网格 -> 它的轮廓网格，保证幂等调用不会叠加第二层描边。 */
let outlineByMesh = new WeakMap<THREE.Mesh, THREE.Mesh>();

/**
 * 取某个网格的墨线轮廓网格（没有就返回 undefined）。
 * 背面外推的轮廓是从外面看的补丁：相机走进它内部时，看到的是壳的内表面，
 * 会变成一大片不受光的平色块。室内机位需要把它关掉，见 HeritageScene。
 */
export function getOutlineMesh(mesh: THREE.Mesh): THREE.Mesh | undefined {
  return outlineByMesh.get(mesh);
}

/**
 * 轮廓网格 -> 当前使用的 rig。用 WeakMap 而不是闭包捕获，
 * 这样 disposeToonResources() 之后重新 apply 时，复用的旧轮廓能指向新 rig，
 * 不会继续渲染已释放的材质 / 贴图。
 */
let outlineRigByMesh = new WeakMap<THREE.Mesh, OutlineRig>();

/** 每帧读取 renderer 尺寸用的临时向量，避免逐帧分配。 */
const sizeScratch = new THREE.Vector2();

const OUTLINE_UNIFORM_DECLARATION = /* glsl */ `
uniform float uSanzhuanOutlineWidthPx;
uniform float uSanzhuanOutlinePixelScale;
uniform float uSanzhuanOutlineOrthoScale;
uniform float uSanzhuanOutlineIsOrtho;
`;

/**
 * 在视空间沿法线外推；位移量 = 目标像素宽 × 当前顶点处的「世界单位 / 像素」。
 * 透视相机下 worldPerPixel 与视深成正比，所以乘上 -viewZ 之后屏幕上恒为一个
 * 固定像素宽；正交相机用常量比例。这样与物体原点、合并几何体都无关。
 */
const OUTLINE_VERTEX_EXPAND = /* glsl */ `
  vec4 sanzhuanOutlineViewPosition = modelViewMatrix * vec4( transformed, 1.0 );
  float sanzhuanOutlineWorldPerPixel = mix(
    uSanzhuanOutlinePixelScale * max( -sanzhuanOutlineViewPosition.z, 0.0001 ),
    uSanzhuanOutlineOrthoScale,
    step( 0.5, uSanzhuanOutlineIsOrtho )
  );
  sanzhuanOutlineViewPosition.xyz += normalize( normalMatrix * normal ) * ( sanzhuanOutlineWorldPerPixel * uSanzhuanOutlineWidthPx );
`;

/**
 * 用外推后的视空间坐标直接出裁剪坐标；同时保留 mvPosition 以兼容其后的
 * <fog_vertex>，且不破坏 <logdepthbuf_vertex> 的位置。
 */
const OUTLINE_VERTEX_PROJECT = /* glsl */ `
  vec4 mvPosition = sanzhuanOutlineViewPosition;
  gl_Position = projectionMatrix * mvPosition;
`;

function clampNumber(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

function normalizeSteps(steps: number): number {
  return Math.round(clampNumber(steps, MIN_GRADIENT_STEPS, MAX_GRADIENT_STEPS));
}

function normalizeOutlineWidth(widthPx: number): number {
  // 保留两位小数，让 Map 缓存键稳定。
  return Math.round(clampNumber(widthPx, MIN_OUTLINE_WIDTH_PX, MAX_OUTLINE_WIDTH_PX) * 100) / 100;
}

/** 第 index 级色带的亮度（单调递增，0~1）。 */
function toneAt(index: number, steps: number): number {
  if (steps === 3) {
    const stop = THREE_TONE_STOPS[index];
    return typeof stop === 'number' ? stop : 1;
  }
  return TONE_FLOOR + ((1 - TONE_FLOOR) * index) / (steps - 1);
}

/**
 * 生成 / 取用 toon 阶梯渐变贴图。
 *
 * 贴图为 steps x 1 的 RGBA 字节纹理，NearestFilter + 不生成 mipmap，
 * 于是采样结果是硬切换而非平滑过渡。同一级数返回同一个实例（被所有 toon
 * 材质共享），请勿直接 dispose，统一走 disposeToonResources()。
 */
export function createToonGradient(steps = DEFAULT_GRADIENT_STEPS): THREE.DataTexture {
  const count = normalizeSteps(steps);
  const cached = gradientCache.get(count);
  if (cached) return cached;

  const data = new Uint8Array(count * 4);
  for (let i = 0; i < count; i += 1) {
    const level = Math.round(clampNumber(toneAt(i, count), 0, 1) * 255);
    const offset = i * 4;
    data[offset] = level;
    data[offset + 1] = level;
    data[offset + 2] = level;
    data[offset + 3] = 255;
  }

  const texture = new THREE.DataTexture(data, count, 1, THREE.RGBAFormat, THREE.UnsignedByteType);
  texture.name = `sanzhuan2-gradient-${count}`;
  texture.magFilter = THREE.NearestFilter;
  texture.minFilter = THREE.NearestFilter;
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.generateMipmaps = false;
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.needsUpdate = true;

  gradientCache.set(count, texture);
  return texture;
}

function shadingFactor(key: string, biasEnabled: boolean): number {
  if (!biasEnabled) return 1;
  const bias = KEY_SHADING_BIAS[key];
  return typeof bias === 'number' ? bias : 1;
}

/** 调色板 sRGB -> three.js 工作色彩空间（线性）的颜色。
 *
 * 关键：优先使用 GLB 自带的基色（source），调色板只在材质没有可用颜色时兜底。
 * 上一版无条件用调色板替换，等于把 Blender 里调好的青灰瓦、暖褐木、米灰石
 * 全部换成一整套浅米色，整馆被洗成"石膏模型"——这是前端发白的真正原因。
 */
function toonColor(key: string, biasEnabled: boolean, source?: THREE.Color | null): THREE.Color {
  const factor = shadingFactor(key, biasEnabled);
  if (source) {
    // 基色是作者给的实际颜色，只按材质语义做一点点明度收敛（<=1），不改色相。
    return new THREE.Color(
      clampNumber(source.r * factor, 0, 1),
      clampNumber(source.g * factor, 0, 1),
      clampNumber(source.b * factor, 0, 1),
    );
  }
  const base = TOON_PALETTE[key] ?? FALLBACK_TRIPLE;
  return new THREE.Color().setRGB(
    clampNumber(base[0] * factor, 0, 1),
    clampNumber(base[1] * factor, 0, 1),
    clampNumber(base[2] * factor, 0, 1),
    THREE.SRGBColorSpace,
  );
}

/** 取材质基色：GLB 的 PBR 材质、Blender 导出的 emissive 都需要认。 */
function materialBaseColor(material: THREE.Material | null | undefined): THREE.Color | null {
  if (!material) return null;
  const typed = material as THREE.MeshStandardMaterial;
  if (!typed.color) return null;
  const c = typed.color;
  // 完全黑色通常是"占位"，交给调色板兜底，避免整块变黑。
  if (c.r + c.g + c.b < 1e-4) return null;
  return c;
}

function getToonMaterial(
  key: string,
  steps: number,
  biasEnabled: boolean,
  base: THREE.Color | null = null,
  alpha = 1,
): THREE.MeshToonMaterial {
  const tint = base ? `${base.getHexString()}` : 'palette';
  const alphaKey = alpha < 0.99 ? alpha.toFixed(2) : 'opaque';
  const cacheKey = `${key}|${steps}|${biasEnabled ? 1 : 0}|${tint}|${alphaKey}`;
  const cached = toonMaterialCache.get(cacheKey);
  if (cached) return cached;

  const color = toonColor(key, biasEnabled, base);
  const material = new THREE.MeshToonMaterial({
    color,
    gradientMap: createToonGradient(steps),
    name: `${KEY_PREFIX}${key}`,
  });
  material.userData.toonKey = key;
  material.userData[SANZHUAN2_FLAG] = true;

  // Transparency must survive the conversion. Dropping it turned the display
  // cases into opaque boxes and made the lit window panels read as plaster.
  if (alphaKey !== 'opaque') {
    material.transparent = true;
    material.opacity = alpha;
    material.depthWrite = false;
  }

  // 灯具：保留自发光，否则夜里整排灯笼是一块死色。
  if (key === 'lamp_glow' || key === 'lantern') {
    material.emissive.copy(color);
    material.emissiveIntensity = 0.8;
  }

  toonMaterialCache.set(cacheKey, material);
  return material;
}

function getOutlineRig(widthPx: number): OutlineRig {
  const cached = outlineRigCache.get(widthPx);
  if (cached) return cached;

  const uniforms: OutlineUniforms = {
    uSanzhuanOutlineWidthPx: { value: widthPx },
    uSanzhuanOutlinePixelScale: { value: 0.002 },
    uSanzhuanOutlineOrthoScale: { value: 0.002 },
    uSanzhuanOutlineIsOrtho: { value: 0 },
  };

  const material = new THREE.MeshBasicMaterial({
    color: OUTLINE_COLOR,
    side: THREE.BackSide,
    depthWrite: false,
    transparent: false,
    fog: false,
  });
  material.name = `${KEY_PREFIX}outline`;
  material.userData.toonKey = 'outline';
  material.userData[SANZHUAN2_FLAG] = true;

  material.onBeforeCompile = (shader) => {
    shader.uniforms.uSanzhuanOutlineWidthPx = uniforms.uSanzhuanOutlineWidthPx;
    shader.uniforms.uSanzhuanOutlinePixelScale = uniforms.uSanzhuanOutlinePixelScale;
    shader.uniforms.uSanzhuanOutlineOrthoScale = uniforms.uSanzhuanOutlineOrthoScale;
    shader.uniforms.uSanzhuanOutlineIsOrtho = uniforms.uSanzhuanOutlineIsOrtho;

    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', `#include <common>${OUTLINE_UNIFORM_DECLARATION}`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>${OUTLINE_VERTEX_EXPAND}`)
      .replace('#include <project_vertex>', OUTLINE_VERTEX_PROJECT);
  };

  const rig: OutlineRig = { material, uniforms };
  outlineRigCache.set(widthPx, rig);
  return rig;
}

function materialKey(material: THREE.Material | null | undefined, fallbackKey: string): string {
  const name = material?.name ?? '';
  const candidate = name.startsWith(KEY_PREFIX) ? name.slice(KEY_PREFIX.length) : name;
  if (candidate.length > 0 && Object.prototype.hasOwnProperty.call(TOON_PALETTE, candidate)) {
    return candidate;
  }
  return fallbackKey;
}

function resolveFallbackKey(key: string | undefined): string {
  if (key && Object.prototype.hasOwnProperty.call(TOON_PALETTE, key)) return key;
  return DEFAULT_FALLBACK_KEY;
}

function findExistingOutline(mesh: THREE.Mesh): THREE.Mesh | null {
  const remembered = outlineByMesh.get(mesh);
  if (remembered && remembered.parent === mesh) return remembered;
  for (const child of mesh.children) {
    if (child instanceof THREE.Mesh && child.userData.isOutline === true && child.parent === mesh) {
      outlineByMesh.set(mesh, child);
      return child;
    }
  }
  return null;
}

/** 每帧按当前相机刷新线宽换算系数；uniform 由 WeakMap 取，便于更换 rig。 */
function refreshOutlineUniforms(outline: THREE.Mesh, renderer: THREE.WebGLRenderer, camera: THREE.Camera): void {
  const rig = outlineRigByMesh.get(outline);
  if (!rig) return;
  const size = renderer.getSize(sizeScratch);
  const height = Math.max(1, size.y);
  if (camera instanceof THREE.PerspectiveCamera) {
    rig.uniforms.uSanzhuanOutlineIsOrtho.value = 0;
    rig.uniforms.uSanzhuanOutlinePixelScale.value =
      (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) * 0.5)) / height;
  } else if (camera instanceof THREE.OrthographicCamera) {
    rig.uniforms.uSanzhuanOutlineIsOrtho.value = 1;
    rig.uniforms.uSanzhuanOutlineOrthoScale.value =
      Math.abs(camera.top - camera.bottom) / Math.max(camera.zoom, 1e-6) / height;
  }
}

function createOutlineMesh(source: THREE.Mesh, rig: OutlineRig, key: string): THREE.Mesh {
  const outline = new THREE.Mesh(source.geometry, rig.material);
  outline.name = `${source.name || 'mesh'}__sanzhuan2_outline`;
  outline.castShadow = false;
  outline.receiveShadow = false;
  outline.renderOrder = source.renderOrder;
  // 与父网格共用同一几何体、且局部矩阵保持单位阵：世界变换自然与父级一致。
  outline.matrixAutoUpdate = false;
  outline.userData.isOutline = true;
  outline.userData[SANZHUAN2_FLAG] = true;
  outline.userData.toonKey = key;
  // 轮廓永远不参与拾取，否则会挡住画框 / 展品的射线交互。
  outline.raycast = () => {};

  outlineRigByMesh.set(outline, rig);
  outline.onBeforeRender = (renderer, _scene, camera) => {
    refreshOutlineUniforms(outline, renderer, camera);
  };

  return outline;
}

/**
 * 把 `root` 内所有网格的材质改写成按原 `M_<key>` 命名的 toon 材质，
 * 并补一层法线外扩的背面轮廓。
 *
 * - 幂等：重复调用不会叠加第二层轮廓，也不会重复创建材质。
 * - 不修改任何外部材质（只替换 mesh.material 的引用）。
 * - 不改动几何体、不合并、不拷贝；保留原 castShadow / receiveShadow。
 */
export function applySanzhuan2(root: THREE.Object3D, opts: ToonOption = {}): ApplyToonResult {
  const outlineEnabled = opts.outline !== false;
  const widthPx = normalizeOutlineWidth(opts.outlineWidthPx ?? DEFAULT_OUTLINE_WIDTH_PX);
  const steps = normalizeSteps(opts.gradientSteps ?? DEFAULT_GRADIENT_STEPS);
  const biasEnabled = opts.shadingBias !== false;
  const fallbackKey = resolveFallbackKey(opts.fallbackKey);

  const rig = outlineEnabled ? getOutlineRig(widthPx) : null;

  const targets: THREE.Mesh[] = [];
  root.traverse((object) => {
    if (!(object instanceof THREE.Mesh)) return;
    // 跳过本模块自己生成的轮廓壳，避免二次进入。
    if (object.userData.isOutline === true) return;
    targets.push(object);
  });

  const usedMaterials = new Set<THREE.MeshToonMaterial>();
  let outlined = 0;

  for (const mesh of targets) {
    const source = mesh.material;
    const slots: THREE.Material[] = Array.isArray(source) ? source : [source];
    const keys = slots.length > 0 ? slots.map((slot) => materialKey(slot, fallbackKey)) : [fallbackKey];

    const toonSlots: THREE.MeshToonMaterial[] = [];
    for (let i = 0; i < keys.length; i += 1) {
      const slot = slots[i] ?? null;
      const alpha = slot && slot.transparent ? clampNumber(slot.opacity ?? 1, 0.02, 1) : 1;
      const material = getToonMaterial(keys[i] as string, steps, biasEnabled, materialBaseColor(slot), alpha);
      usedMaterials.add(material);
      toonSlots.push(material);
    }

    let primary = toonSlots[0];
    if (!primary) {
      primary = getToonMaterial(fallbackKey, steps, biasEnabled);
      usedMaterials.add(primary);
    }

    if (Array.isArray(source)) {
      mesh.material = toonSlots;
    } else {
      mesh.material = primary;
    }

    if (!rig) continue;

    const existing = findExistingOutline(mesh);
    if (existing) {
      // 复用旧轮廓（保证不叠加），但把材质 / 几何体 / rig 刷新到当前状态，
      // 这样 disposeToonResources() 之后重新 apply 也能恢复正常。
      existing.geometry = mesh.geometry;
      existing.material = rig.material;
      existing.userData.toonKey = keys[0] ?? fallbackKey;
      outlineRigByMesh.set(existing, rig);
      outlined += 1;
      continue;
    }

    const outline = createOutlineMesh(mesh, rig, keys[0] ?? fallbackKey);
    mesh.add(outline);
    outlineByMesh.set(mesh, outline);
    outlined += 1;
  }

  return {
    meshes: targets.length,
    materials: usedMaterials.size,
    outlined,
  };
}

/** 释放本模块创建的共享材质 / 渐变贴图（不触碰几何体与外部材质）。 */
export function disposeToonResources(): void {
  toonMaterialCache.forEach((material) => material.dispose());
  toonMaterialCache.clear();

  outlineRigCache.forEach((rig) => rig.material.dispose());
  outlineRigCache.clear();

  gradientCache.forEach((texture) => texture.dispose());
  gradientCache.clear();

  outlineByMesh = new WeakMap<THREE.Mesh, THREE.Mesh>();
  outlineRigByMesh = new WeakMap<THREE.Mesh, OutlineRig>();
}