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

const STATIC_SHOWCASE = (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_STATIC_SHOWCASE === 'true';

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
  folder?: string;
  worldUrl?: string;
  hasExperience?: boolean;
  hasWorld?: boolean;
  interaction?: CaseInteraction;
}

export type InteractionStatus = 'none' | 'queued' | 'processing' | 'ready' | 'partial' | 'failed';

export interface InteractionStages {
  hotspots: boolean;
  story: boolean;
  world: boolean;
}

export interface InteractiveJob {
  caseId?: string;
  status?: string;
  attempts?: number;
  error?: string;
  message?: string;
  elapsedSec?: number;
  updatedAt?: string;
  stages?: Partial<InteractionStages>;
  assets?: { experience?: string; world?: string; worldFiles?: string[] };
}

/** 后端只用一个结构描述「这件作品的三种互动到底到了哪一步」。 */
export interface CaseInteraction {
  status: InteractionStatus;
  stages: InteractionStages;
  hasExperience: boolean;
  hasWorld: boolean;
  experienceId: string;
  job?: InteractiveJob | null;
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
  const caseId = asText(raw.caseId) || asText(raw.folder);
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
    folder: asText(raw.folder) || undefined,
    worldUrl: asText(raw.worldUrl) || undefined,
    hasExperience: Boolean(raw.hasExperience),
    hasWorld: Boolean(raw.hasWorld),
    interaction: normalizeInteraction(raw.interaction),
  };
}

const INTERACTION_STATUSES: InteractionStatus[] = ['none', 'queued', 'processing', 'ready', 'partial', 'failed'];

function normalizeInteraction(raw: unknown): CaseInteraction | undefined {
  if (!raw || typeof raw !== 'object') return undefined;
  const source = raw as Record<string, unknown>;
  const status = asText(source.status) as InteractionStatus;
  const stagesRaw = (source.stages && typeof source.stages === 'object' ? source.stages : {}) as Record<string, unknown>;
  const jobRaw = source.job && typeof source.job === 'object' ? (source.job as InteractiveJob) : null;
  return {
    status: INTERACTION_STATUSES.includes(status) ? status : 'none',
    stages: {
      hotspots: Boolean(stagesRaw.hotspots),
      story: Boolean(stagesRaw.story),
      world: Boolean(stagesRaw.world),
    },
    hasExperience: Boolean(source.hasExperience),
    hasWorld: Boolean(source.hasWorld),
    experienceId: asText(source.experienceId),
    job: jobRaw,
  };
}

/** 精选案例保留本地定义；运行期案例优先采用后端最新状态。 */
export function mergeCases(base: GalleryCase[], incoming: GalleryCase[]): GalleryCase[] {
  const seen = new Set(base.map((item) => item.caseId));
  const extra = incoming.filter((item) => !seen.has(item.caseId));
  // 运行期案例按生成时间倒序，最新的一件排在最前
  const latest = new Map(incoming.map((item) => [item.caseId, item]));
  return [...extra, ...base.map((item) => item.caseOrigin === 'runtime'
    ? latest.get(item.caseId) ?? item : item)];
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
  if (STATIC_SHOWCASE) throw new Error('静态演示使用已打包的作品，不连接本机后端');
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

export interface CaseDetail {
  case: GalleryCase;
  experience: Record<string, unknown> | null;
  interaction?: CaseInteraction;
}

const DEFAULT_DETAIL_TIMEOUT = 6000;

/**
 * 单件作品的运行期详情。
 *
 * 这是「新作品立刻能用互动」的关键：不依赖 Vite 重新编译，也不需要改源码。
 * 作品身份只认 caseId；返回的 experience 是这件作品自己的 experience.json。
 */
export async function fetchCaseDetail(
  caseId: string,
  options: FetchCasesOptions = {},
): Promise<CaseDetail | null> {
  if (STATIC_SHOWCASE) return null;
  const { timeoutMs = DEFAULT_DETAIL_TIMEOUT, signal } = options;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  const onAbort = () => controller.abort();
  signal?.addEventListener('abort', onAbort);
  try {
    const response = await fetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}`, {
      method: 'GET',
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    });
    if (response.status === 404) return null;
    if (!response.ok) throw new Error(`case detail api ${response.status}`);
    const payload = (await response.json()) as {
      case?: unknown;
      experience?: unknown;
      interaction?: unknown;
    };
    if (!payload.case || typeof payload.case !== 'object') return null;
    const normalized = normalizeCase(payload.case as Record<string, unknown>);
    if (!normalized) return null;
    const interaction = normalizeInteraction(payload.interaction);
    if (interaction) normalized.interaction = interaction;
    return {
      case: normalized,
      experience: payload.experience && typeof payload.experience === 'object'
        ? (payload.experience as Record<string, unknown>)
        : null,
      interaction,
    };
  } finally {
    window.clearTimeout(timer);
    signal?.removeEventListener('abort', onAbort);
  }
}

/** 显式重试：只对运行期案例开放，后端会拒绝覆盖内置精选项。 */
export async function rebuildCaseInteractions(caseId: string): Promise<InteractiveJob | null> {
  const response = await fetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/interactions/rebuild`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    let detail = `rebuild api ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (body?.detail) detail = String(body.detail);
    } catch {
      // keep the status message
    }
    throw new Error(detail);
  }
  const payload = (await response.json()) as { job?: InteractiveJob };
  return payload.job ?? null;
}

/** Delete only after the caller confirms the exact runtime work. */
export async function deleteRuntimeCase(caseId:string):Promise<void> {
  if (STATIC_SHOWCASE) throw new Error('在线展示不可删除作品，请在本地运行项目。');
  const response=await fetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}`,{
    method:'DELETE',headers:{Accept:'application/json'},
  });
  if (!response.ok) {
    const body=await response.json().catch(()=>null) as {detail?:string}|null;
    throw new Error(body?.detail??'删除失败，请确认后端服务正常。');
  }
}
