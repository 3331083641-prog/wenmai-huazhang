/**
 * 三渲二（toon / NPR）材质与调色板。
 *
 * 做法：
 *  - 所有实体表面用 MeshToonMaterial + 3~4 级阶梯渐变贴图，
 *    得到动画片里那种「明暗分成几块」的干净效果，而不是 PBR 的连续过渡。
 *  - 轮廓不靠后期描边（那需要额外依赖且容易糊），
 *    而是用「背面外扩」的经典做法：同一几何体再画一遍，
 *    材质 BackSide + 略微放大，得到稳定的墨线轮廓。
 *  - 阴影只开一盏方向光，软阴影，避免多层硬阴影把画面弄脏。
 *
 * 全部材质在模块内缓存，避免每帧重建导致显存抖动。
 */

import * as THREE from 'three';

/** 东方色板：低饱和、暖调，与站内宣纸/朱砂体系一致 */
export const PALETTE = {
  paper: '#F5EAD6',
  paperDeep: '#EADCC0',
  ink: '#3A2A20',
  outline: '#2E211A',
  /** 木构 */
  wood: '#B8763F',
  woodDark: '#8A5330',
  /** 朱红柱与檐下 */
  vermilion: '#A8352A',
  vermilionDark: '#7E241C',
  /** 瓦面：黛青 */
  tile: '#4A5A5E',
  tileDark: '#36444A',
  /** 石阶与地面 */
  stone: '#C9BFAE',
  stoneDark: '#A99C87',
  /** 街面石板 */
  paving: '#B9AE9C',
  pavingAlt: '#A79B88',
  /** 植被 */
  leaf: '#6F8F5B',
  leafDark: '#54703F',
  /** 灯笼暖光 */
  lantern: '#E8A33D',
  /** 天空 */
  sky: '#BFD9E8',
  skyTop: '#8FBBD6',
} as const;

/**
 * 阶梯渐变贴图：MeshToonMaterial 用它决定明暗分层。
 * 4 级比 2 级更有体积感，又不至于像写实渐变。
 */
function makeToonGradient(steps = 4): THREE.DataTexture {
  const data = new Uint8Array(steps);
  for (let i = 0; i < steps; i += 1) {
    // 从 0.55 到 1.0，保证暗部不会死黑
    data[i] = Math.round(255 * (0.55 + (0.45 * i) / (steps - 1)));
  }
  const texture = new THREE.DataTexture(data, steps, 1, THREE.RedFormat);
  texture.minFilter = THREE.NearestFilter;
  texture.magFilter = THREE.NearestFilter;
  texture.generateMipmaps = false;
  texture.needsUpdate = true;
  return texture;
}

let gradientCache: THREE.DataTexture | null = null;
function gradient(): THREE.DataTexture {
  if (!gradientCache) gradientCache = makeToonGradient(4);
  return gradientCache;
}

const materialCache = new Map<string, THREE.MeshToonMaterial>();

/** 取得（并缓存）一个 toon 材质 */
export function toonMaterial(
  color: string,
  options: { emissive?: string; emissiveIntensity?: number; transparent?: boolean; opacity?: number } = {},
): THREE.MeshToonMaterial {
  const key = `${color}|${options.emissive ?? ''}|${options.emissiveIntensity ?? 0}|${options.transparent ?? false}|${options.opacity ?? 1}`;
  const cached = materialCache.get(key);
  if (cached) return cached;

  const material = new THREE.MeshToonMaterial({
    color: new THREE.Color(color),
    gradientMap: gradient(),
    transparent: options.transparent ?? false,
    opacity: options.opacity ?? 1,
  });
  if (options.emissive) {
    material.emissive = new THREE.Color(options.emissive);
    material.emissiveIntensity = options.emissiveIntensity ?? 1;
  }
  materialCache.set(key, material);
  return material;
}

/**
 * 轮廓材质：BackSide + 轻微外扩。
 * depthWrite 关闭可避免轮廓在自遮挡处出现黑色脏边。
 */
export const outlineMaterial = new THREE.MeshBasicMaterial({
  color: new THREE.Color(PALETTE.outline),
  side: THREE.BackSide,
});

export function disposeMaterialCache(): void {
  materialCache.forEach((material) => material.dispose());
  materialCache.clear();
  gradientCache?.dispose();
  gradientCache = null;
}

/** 天空渐变用的垂直渐变贴图 */
export function makeSkyTexture(): THREE.CanvasTexture {
  const size = 512;
  const canvas = document.createElement('canvas');
  canvas.width = 4;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    const grad = ctx.createLinearGradient(0, 0, 0, size);
    // 顶部深一点的晴空蓝，近地平线转为暖白
    grad.addColorStop(0, '#6FA8CC');
    grad.addColorStop(0.28, '#8FBEDC');
    grad.addColorStop(0.52, '#B4D5E8');
    grad.addColorStop(0.74, '#D8E7EE');
    grad.addColorStop(1, '#F3EEE2');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 4, size);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  return texture;
}

/** 石板路纹理：程序化生成，不引入外部图片 */
export function makePavingTexture(): THREE.CanvasTexture {
  const size = 256;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    ctx.fillStyle = PALETTE.paving;
    ctx.fillRect(0, 0, size, size);
    // 石板分缝
    ctx.strokeStyle = 'rgba(90, 78, 64, 0.35)';
    ctx.lineWidth = 2;
    const rows = 4;
    const cols = 4;
    for (let r = 0; r <= rows; r += 1) {
      const y = (r * size) / rows;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(size, y);
      ctx.stroke();
    }
    for (let r = 0; r < rows; r += 1) {
      const offset = r % 2 === 0 ? 0 : size / cols / 2;
      for (let c = 0; c <= cols; c += 1) {
        const x = (c * size) / cols + offset;
        const y0 = (r * size) / rows;
        const y1 = ((r + 1) * size) / rows;
        ctx.beginPath();
        ctx.moveTo(x, y0);
        ctx.lineTo(x, y1);
        ctx.stroke();
      }
    }
    // 轻微色斑，避免大面积纯色
    for (let i = 0; i < 90; i += 1) {
      ctx.fillStyle = `rgba(120, 106, 88, ${0.03 + Math.random() * 0.05})`;
      const r = 4 + Math.random() * 14;
      ctx.beginPath();
      ctx.arc(Math.random() * size, Math.random() * size, r, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}
