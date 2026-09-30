/// <reference types="vite/client" />
import { STYLES, CultureCard } from '../data/styleLibrary';

export interface GeneratePayload {
  theme: string;
  style: string;
  styleName: string;
  outputType: string;
  styleStrength: number;
  compositionMode: string;
  negativePrompt: string | null;
  uploadedImage: string | null;
  generationProvider?: 'dashscope_qwen_image';
}

export interface ImageAnalysis {
  subject: string;
  scene: string;
  colors: string;
  composition: string;
  transferableElements: string;
  hasUploadedImage?: string;
  savedPath?: string;
  width?: string;
  height?: string;
  brightness?: string;
  dominantColor?: string;
}

export interface BackendHealth {
  status: string;
  provider?: string;
  generationProvider: string;
  model?: string | null;
  localVisionAnalysis?: {
    enabled: boolean;
    available: boolean;
    provider: string;
    model: string;
    message: string;
  };
  allowMockFallback: boolean;
  providers?: Record<string, Record<string, unknown>>;
  message?: string;
}

export interface VisionAnalysis {
  title: string;
  observed_subjects: string[];
  theme_summary: string;
  dominant_colors: string[];
  composition: string;
  visual_features: string[];
  style_interpretation: string;
  culture_interpretation: string;
  recommended_scenes: string[];
  theme_alignment: '高' | '中' | '低';
  style_alignment: '明显' | '基本' | '较弱';
}

export interface GenerateResponse {
  success: boolean;
  imageUrl: string;
  enhancedPrompt: string;
  mode: string;
  provider?: string;
  model?: string | null;
  referenceImageUsed?: boolean;
  styleReferenceUsed?: boolean;
  analysisSource?: 'qwen3_vl' | 'template_fallback' | string;
  visionAnalysis?: VisionAnalysis | null;
  visionAnalysisError?: string | null;
  cultureCard?: CultureCard;
  imageAnalysis?: ImageAnalysis | null;
  error?: string | null;
  realProviderError?: string | null;
  debug?: Record<string, unknown> | null;
  usedStyleRef?: string | null;
  engine?: string | null;
  device?: string | null;
  steps?: number | null;
  width?: number | null;
  height?: number | null;
  localPath?: string | null;
}

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const GENERATE_TIMEOUT_MS = 300_000;

export class BackendConnectionError extends Error {
  constructor(message = "前端无法连接后端 FastAPI，请确认 http://127.0.0.1:8000/health 是否可打开。") {
    super(message);
    this.name = "BackendConnectionError";
  }
}

class ApiResponseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiResponseError";
  }
}

const OUTPUT_TYPE_SCENARIOS: Record<string, string> = {
  poster: "数字海报视觉稿",
  postcard: "文旅明信片效果预览",
  bag: "帆布袋图案视觉设计",
  bookmark: "文创书签视觉设计",
  coaster: "陶瓷杯垫图案预览",
  social: "手机分享图版式示意",
  screen: "数字展陈屏效果示意",
  ticket: "纪念票版式示意",
};

export async function checkBackendHealth(): Promise<BackendHealth> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, { method: "GET" });
    if (!response.ok) {
      throw new ApiResponseError(`后端 /health 返回 HTTP ${response.status}`);
    }
    return await response.json() as BackendHealth;
  } catch (error) {
    if (error instanceof ApiResponseError) {
      throw error;
    }
    throw new BackendConnectionError();
  }
}

export async function generateImage(payload: GeneratePayload): Promise<GenerateResponse> {
  await checkBackendHealth();

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), GENERATE_TIMEOUT_MS);
  const requestBody: GeneratePayload = {
    theme: payload.theme,
    style: payload.style,
    styleName: payload.styleName,
    outputType: payload.outputType,
    styleStrength: payload.styleStrength,
    compositionMode: payload.compositionMode,
    negativePrompt: payload.negativePrompt,
    uploadedImage: payload.uploadedImage,
    generationProvider: payload.generationProvider || 'dashscope_qwen_image',
  };

  try {
    const response = await fetch(`${API_BASE_URL}/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
      signal: controller.signal,
    });

    const data = await parseGenerateResponse(response);
    if (!response.ok) {
      throw new ApiResponseError(data.error || `API error: ${response.status}`);
    }

    if (!data.success) {
      const debugText = data.debug ? ` Debug: ${JSON.stringify(data.debug)}` : "";
      throw new ApiResponseError((data.error || "后端生成失败。") + debugText);
    }

    if (!data.imageUrl || typeof data.enhancedPrompt !== "string" || !data.mode) {
      throw new ApiResponseError("API returned an invalid generation response");
    }

    return {
      success: data.success,
      imageUrl: resolveGeneratedImageUrl(data.imageUrl),
      enhancedPrompt: data.enhancedPrompt,
      mode: data.mode,
      provider: data.provider,
      model: data.model || null,
      referenceImageUsed: data.referenceImageUsed === true,
      styleReferenceUsed: data.styleReferenceUsed === true,
      analysisSource: data.analysisSource || 'template_fallback',
      visionAnalysis: data.visionAnalysis || null,
      visionAnalysisError: data.visionAnalysisError || null,
      cultureCard: data.cultureCard || buildLocalCultureCard(payload, data.imageAnalysis || null),
      imageAnalysis: data.imageAnalysis || null,
      error: data.error || null,
      realProviderError: data.realProviderError || null,
      debug: data.debug || null,
      usedStyleRef: data.usedStyleRef || null,
      engine: data.engine || null,
      device: data.device || null,
      steps: data.steps || null,
      width: data.width || null,
      height: data.height || null,
      localPath: data.localPath || null,
    };
  } catch (error) {
    if (error instanceof ApiResponseError) {
      throw error;
    }
    if ((error as Error).name === "AbortError") {
      throw new ApiResponseError("生成请求超时，请检查后端是否仍在运行，或稍后重试。");
    }
    throw new BackendConnectionError();
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function parseGenerateResponse(response: Response): Promise<GenerateResponse> {
  try {
    return await response.json() as GenerateResponse;
  } catch {
    return {
      success: false,
      imageUrl: "",
      enhancedPrompt: "",
      mode: "error",
      error: `API returned a non-JSON response: ${response.status}`,
    };
  }
}

export function buildLocalCultureCard(
  payload: GeneratePayload,
  imageAnalysis?: ImageAnalysis | null,
): CultureCard {
  const selectedStyle = STYLES.find(s => s.id === payload.style) || STYLES[0];
  const theme = payload.theme?.trim() || "传统文化主题创作";
  const applicationScenario = OUTPUT_TYPE_SCENARIOS[payload.outputType] || selectedStyle.scene || "文创衍生品应用";

  if (!imageAnalysis) {
    return {
      title: `${theme} · ${selectedStyle.name}`,
      cultureSource: selectedStyle.cultureSource,
      visualFeatures: selectedStyle.promptVisualFeatures,
      symbolicMeaning: selectedStyle.symbolicMeaning,
      applicationScenario,
    };
  }

  return {
    title: `${theme} · ${selectedStyle.name}`,
    cultureSource: selectedStyle.cultureSource,
    visualFeatures: `${selectedStyle.promptVisualFeatures}；参考图本地基础统计：${imageAnalysis.colors}；${imageAnalysis.composition}`,
    symbolicMeaning: selectedStyle.symbolicMeaning,
    applicationScenario: `${applicationScenario}；可迁移参考元素：${imageAnalysis.transferableElements}`,
  };
}

export function resolveGeneratedImageUrl(imageUrl: string): string {
  if (!imageUrl) {
    return imageUrl;
  }

  if (/^(https?:|data:|blob:)/.test(imageUrl)) {
    return imageUrl;
  }

  const normalizedPath = imageUrl.startsWith("/") ? imageUrl : `/${imageUrl}`;
  if (normalizedPath.startsWith("/outputs") || normalizedPath.startsWith("/style_refs")) {
    return `${API_BASE_URL}${normalizedPath}`;
  }

  return imageUrl;
}
