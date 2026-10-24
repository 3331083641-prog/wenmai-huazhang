/**
 * 纹脉展馆的可挂画作品池：内置精选 + 运行期新生成作品。
 *
 * - 运行期作品通过 Case Service 拉取，按 caseId 注册，绝不按 styleId 合并；
 * - 缓存在 localStorage，刷新后画框仍能解析上次挂的新作品；
 * - 后端不可用（GitHub Pages 静态演示）时保留缓存并回退到内置五件，不白屏。
 */
import { useSyncExternalStore } from 'react';
import { galleryArtworks as curatedArtworks } from './galleryArtworks';
import { resetArtworkRegistry } from './artworkRegistry';
import { fetchRuntimeCases, type GalleryCase } from '../services/caseService';
import type { GalleryArtwork } from '../features/heritage-gallery/types';

const STORAGE_KEY = 'wenmai_gallery_runtime_artworks_v1';

const STYLE_ACCENT: Record<string, string> = {
  zhuxianzhen: '#9E241B',
  bianxiu: '#A64C54',
  songhua: '#426C62',
  qinghua: '#315F88',
  jianzhi: '#A52225',
};

function caseToArtwork(item: GalleryCase): GalleryArtwork | null {
  if (!item.caseId || !item.imageUrl) return null;
  return {
    id: item.caseId,
    title: item.artworkTitle,
    styleId: item.styleId,
    styleName: item.styleName,
    imageUrl: item.imageUrl,
    thumbUrl: item.imageUrl,
    cultureCardUrl: item.cardUrl,
    referenceUrl: item.referenceUrl,
    summary:
      item.visionAnalysis.culture_interpretation ||
      item.visionAnalysis.theme_summary ||
      '运行期自动保存的新作品。',
    features: item.visionAnalysis.visual_features.slice(0, 4),
    generatedAt: item.generatedAt,
    origin: 'runtime',
    accent: STYLE_ACCENT[item.styleId] ?? '#9E241B',
  };
}

function loadCached(): GalleryArtwork[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is GalleryArtwork => {
      if (!item || typeof item !== 'object') return false;
      const candidate = item as GalleryArtwork;
      return Boolean(candidate.id && candidate.imageUrl && candidate.title);
    });
  } catch {
    return [];
  }
}

let runtimeArtworks: GalleryArtwork[] = loadCached();
const listeners = new Set<() => void>();
let snapshot: GalleryArtwork[] = [];
let inflight: Promise<GalleryArtwork[]> | null = null;

function publish(): void {
  const seen = new Set(curatedArtworks.map((item) => item.id));
  const extras = runtimeArtworks.filter((item) => !seen.has(item.id));
  snapshot = [...extras, ...curatedArtworks];
  resetArtworkRegistry(snapshot);
  for (const listener of listeners) listener();
}

publish();

export function getGallerySnapshot(): GalleryArtwork[] {
  return snapshot;
}

export function getRuntimeArtworkCount(): number {
  return Math.max(0, snapshot.length - curatedArtworks.length);
}

export function subscribeGalleryPool(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useGalleryPool(): GalleryArtwork[] {
  return useSyncExternalStore(subscribeGalleryPool, getGallerySnapshot, getGallerySnapshot);
}

/** 拉取运行期作品并更新画作池；失败时保留现有内容（静态部署可离线）。 */
export async function refreshGalleryPool(): Promise<GalleryArtwork[]> {
  if (inflight) return inflight;
  inflight = (async () => {
    try {
      const cases = await fetchRuntimeCases({ timeoutMs: 4000 });
      runtimeArtworks = cases
        .map(caseToArtwork)
        .filter((item): item is GalleryArtwork => Boolean(item));
      if (typeof window !== 'undefined') {
        try {
          window.localStorage.setItem(STORAGE_KEY, JSON.stringify(runtimeArtworks));
        } catch {
          // 配额不足时仍保留内存态
        }
      }
      publish();
    } catch (error) {
      console.warn('[gallery-pool] 运行期作品拉取失败，保留当前作品池', error);
    }
    return snapshot;
  })().finally(() => {
    inflight = null;
  });
  return inflight;
}