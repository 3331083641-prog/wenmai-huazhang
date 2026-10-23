import type { VisionAnalysis } from './generationService';

/**
 * 只做类型导入，避免把 generationService 的顶层 `import.meta.env` 带进 Node 测试环境。
 * 这里自己解析后端地址，浏览器与构建产物行为一致。
 */
const API_BASE_URL: string = (() => {
  try {
    const env = (import.meta as unknown as { env?: Record<string, string> }).env;
    return String(env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
  } catch {
    return 'http://127.0.0.1:8000';
  }
})();

/**
 * 展厅的案例来源有两种：
 *  - curated：随仓库一起提交的五件真实案例（编译期打包，离线可用，带互动解读）
 *  - runtime：后端 /generate 成功后自动落盘的案例（运行期通过 /cases 拉取）
 *
 * 两者用同一套字段渲染，保证「新生成的图看起来和老案例一样」。
 */
export interface GalleryCase {
  caseId: string;
  caseOrigin: 'curated' | 'runtime';
  experienceId?: string;
  styleId: string;
  styleName: string;
  artworkTitle: string;
  theme: string;
  generatedAt: string;
  styleStrength: number;
  analysisSource: string;
  provider?: string;
  model?: string;
  visionAnalysis: VisionAnalysis;
  cultureCard?: Record<string, string>;
  referenceUrl?: string;
  imageUrl: string;
  cardUrl?: string;
}

const EMPTY_ANALYSIS: VisionAnalysis = {
  title: '',
  observed_subjects: [],
  theme_summary: '',
  dominant_colors: [],
  composition: '',
  visual_features: [],
  style_interpretation: '',
  culture_interpretation: '',
  recommended_scenes: [],
  theme_alignment: '中',
  style_alignment: '基本',
};

function asText(value: unknown): string {
  return typeof value === 'string' ? value : value == null ? '' : String(value);
}

function asList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => asText(item).trim()).filter(Boolean);
}

function asAlignment<T extends string>(value: unknown, allowed: readonly T[], fallback: T): T {
  const text = asText(value);
  return (allowed as readonly string[]).includes(text) ? (text as T) : fallback;
}

/** 把后端/打包数据整理成渲染需要的形状；缺字段一律降级，不抛错。 */
export function normalizeAnalysis(raw: unknown): VisionAnalysis {
  if (!raw || typeof raw !== 'object') return { ...EMPTY_ANALYSIS };
  const source = raw as Record<string, unknown>;
  return {
    title: asText(source.title),
    observed_subjects: asList(source.observed_subjects),
    theme_summary: asText(source.theme_summary),
    dominant_colors: asList(source.dominant_colors),
    composition: asText(source.composition),
    visual_features: asList(source.visual_features),
    style_interpretation: asText(source.style_interpretation),
    culture_interpretation: asText(source.culture_interpretation),
    recommended_scenes: asList(source.recommended_scenes),
    theme_alignment: asAlignment(source.theme_alignment, ['高', '中', '低'] as const, '中'),
    style_alignment: asAlignment(source.style_alignment, ['明显', '基本', '较弱'] as const, '基本'),
  };
}

export function normalizeCase(raw: Record<string, unknown>): GalleryCase | null {
  const imageUrl = asText(raw.imageUrl);
  if (!imageUrl) return null;
  const caseId = asText(raw.caseId) || asText(raw.styleId);
  if (!caseId) return null;
  return {
    caseId,
    caseOrigin: raw.caseOrigin === 'runtime' ? 'runtime' : 'curated',
    experienceId: asText(raw.experienceId) || undefined,
    styleId: asText(raw.styleId),
    styleName: asText(raw.styleName) || '传统风格',
    artworkTitle: asText(raw.artworkTitle) || asText(raw.theme) || '未命名作品',
    theme: asText(raw.theme),
    generatedAt: asText(raw.generatedAt),
    styleStrength: Number(raw.styleStrength ?? 0.65),
    analysisSource: asText(raw.analysisSource) || 'template_fallback',
    provider: asText(raw.provider) || undefined,
    model: asText(raw.model) || undefined,
    visionAnalysis: normalizeAnalysis(raw.visionAnalysis),
    cultureCard: raw.cultureCard && typeof raw.cultureCard === 'object'
      ? (raw.cultureCard as Record<string, string>)
      : undefined,
    referenceUrl: asText(raw.referenceUrl) || undefined,
    imageUrl,
    cardUrl: asText(raw.cardUrl) || undefined,
  };
}

/** 内置案例优先，运行期案例按 caseId 去重后追加。 */
export function mergeCases(base: GalleryCase[], incoming: GalleryCase[]): GalleryCase[] {
  const seen = new Set(base.map((item) => item.caseId));
  const extra = incoming.filter((item) => !seen.has(item.caseId));
  // 运行期案例按生成时间倒序，最新的一件排在最前
  return [...extra, ...base];
}

export interface FetchCasesOptions {
  timeoutMs?: number;
  signal?: AbortSignal;
}

/**
 * 拉取运行期案例。
 * 后端没启动 / 静态部署时这里会**抛错**——由调用方决定降级方式：
 * 展厅会退回只显示内置五件并给出一句提示，离线能力不因为新功能而退化。
 */
export async function fetchRuntimeCases(options: FetchCasesOptions = {}): Promise<GalleryCase[]> {
  const { timeoutMs = 2500, signal } = options;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  const onAbort = () => controller.abort();
  signal?.addEventListener('abort', onAbort);
  try {
    const response = await fetch(`${API_BASE_URL}/cases`, {
      method: 'GET',
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) throw new Error(`cases api ${response.status}`);
    const payload = (await response.json()) as { cases?: unknown };
    const list = Array.isArray(payload.cases) ? payload.cases : [];
    const cases: GalleryCase[] = [];
    for (const entry of list) {
      if (!entry || typeof entry !== 'object') continue;
      const normalized = normalizeCase(entry as Record<string, unknown>);
      // 只收运行期案例；内置五件已经随包提供，避免重复渲染
      if (normalized && normalized.caseOrigin === 'runtime') cases.push(normalized);
    }
    return cases;
  } finally {
    window.clearTimeout(timer);
    signal?.removeEventListener('abort', onAbort);
  }
}