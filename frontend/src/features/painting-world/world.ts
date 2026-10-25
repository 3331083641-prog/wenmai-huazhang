/**
 * 画境清单（world.json）的类型与解析。
 *
 * 清单由 scripts/interactive/build_painting_world.py 生成，是「画作 → 可漫游空间」
 * 的唯一契约：贴图、深度、遮罩、抠像、热点坐标与相机范围都写在这里，
 * 前端不自己猜任何数值。
 */

export interface WorldArt {
  file: string;
  width: number;
  height: number;
  aspect: number;
}

export interface WorldDepth {
  file: string;
  width: number;
  height: number;
  /** 深度曲线 gamma：<1 时把中景拉开，避免中景几乎不动。 */
  gamma: number;
}

export interface WorldMasks {
  file: string;
  width: number;
  height: number;
  coverage: { water: number; mist: number; foliage: number };
}

export interface WorldCutout {
  id: string;
  label: string;
  file: string;
  bbox_norm: number[];
  size: number[];
  alpha_coverage: number;
  depth?: number;
  relief_file?: string;
  negativeSpacePreserved?:boolean;
}

export interface WorldHotspot {
  id: string;
  /** 归一化坐标，原点左上。 */
  x: number;
  y: number;
  /** 最终采用的深度（0..1，1=最近）。 */
  depth: number;
  /** 深度模型的原始读数，便于核对是否被人工校正过。 */
  depth_measured: number;
  depth_overridden: boolean;
  relief_delta?: number;
}

export interface WorldCamera {
  fov: number;
  framing_margin?:number;
  plane_height: number;
  plane_width: number;
  /** 相机退到多远时画面刚好铺满视口。 */
  distance_fill: number;
  depth_amplitude: number;
  yaw_limit_deg: number;
  pitch_limit_deg: number;
  dolly_near: number;
  dolly_far: number;
  entry: { from_scale: number; duration_ms: number };
}

export interface PaintingWorldManifest {
  version: number;
  slug: string;
  title: string;
  art: WorldArt;
  surface?: { file: string } | null;
  depth: WorldDepth;
  backdrop: { file: string };
  masks: WorldMasks;
  cutouts: WorldCutout[];
  hotspots: WorldHotspot[];
  camera: WorldCamera;
  tuning?: Partial<WorldTuning>;
  provenance: { depth_model: string; depth_generated_at: string; note: string; asset_revision?: string };
}

export interface WorldTuning {
  haze: number; mist: number; ripple: number; sway: number;
  subject_relief: number; cutout_motion: number;
  paper_flex:number;
}

export function worldTuning(manifest: PaintingWorldManifest): WorldTuning {
  const defaults:WorldTuning={haze:.1,mist:.26,ripple:1,sway:1,subject_relief:0,cutout_motion:1,paper_flex:0};
  const limits:Record<keyof WorldTuning,number>={haze:.12,mist:.35,ripple:1,sway:1,subject_relief:.1,cutout_motion:1,paper_flex:.006};
  const result={...defaults};
  for (const key of Object.keys(defaults) as Array<keyof WorldTuning>) {
    const value=manifest.tuning?.[key];
    if (typeof value==='number' && Number.isFinite(value)) result[key]=Math.max(0,Math.min(limits[key],value));
  }
  return result;
}

export function hotspotWorldZ(spot:WorldHotspot,manifest:PaintingWorldManifest):number {
  return spot.depth*manifest.camera.depth_amplitude+(spot.relief_delta??0)*worldTuning(manifest).subject_relief;
}

/** 把清单里的相对文件名拼成可加载的 URL。
 *
 * 注意必须带 BASE_URL：清单里的路径是相对 `public/` 的，
 * 但页面路由是 `/wander/:id`，直接交给 TextureLoader 会解析成
 * `/wander/interactive/...` → 404（这一版踩过）。
 */
export function resolveWorldAsset(baseUrl: string, file: string): string {
  if (/^(https?:|data:|\/\/)/.test(file)) return file;
  const idx = baseUrl.lastIndexOf('/');
  const dir = idx >= 0 ? baseUrl.slice(0, idx + 1) : '';
  const revision = new URLSearchParams(baseUrl.split('?')[1] ?? '').get('v');
  return withBase(`${dir}${file}`) + (revision ? `?v=${encodeURIComponent(revision)}` : '');
}

/** 与 publicUrl 行为一致的兜底：Vite BASE_URL 不是根目录时也能用。 */
export function withBase(path: string): string {
  if (/^(https?:|data:|\/\/)/.test(path)) return path;
  const base = (import.meta as unknown as { env?: Record<string, string> }).env?.BASE_URL || '/';
  const clean = path.replace(/^\/+/, '');
  return base.endsWith('/') ? `${base}${clean}` : `${base}/${clean}`;
}

export async function loadWorldManifest(path: string): Promise<PaintingWorldManifest> {
  const res = await fetch(withBase(path), { cache: 'no-store' });
  if (!res.ok) throw new Error(`画境清单读取失败：${res.status} ${path}`);
  const data = (await res.json()) as PaintingWorldManifest;
  if (!data?.art?.file || !data?.depth?.file) throw new Error('画境清单缺少贴图或深度');
  return data;
}

/** 归一化坐标 → 平面局部坐标（平面高 1、宽 aspect，原点居中，y 向上）。 */
export function uvToPlane(nx: number, ny: number, aspect: number, height: number) {
  return {
    x: (nx - 0.5) * aspect * height,
    y: (0.5 - ny) * height,
  };
}
