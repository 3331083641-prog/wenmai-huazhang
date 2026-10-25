/**
 * 展馆画作的运行时注册表。
 *
 * 内置五件来自编译期数据；新生成作品由 galleryPool 在运行期注册进来。
 * 画框、详情面板、布展校验都只通过 id 查这里，绝不按风格猜作品。
 */
import { galleryArtworks } from './galleryArtworks';
import { isCaseDeleted } from '../services/deletedCases';
import type { GalleryArtwork } from '../features/heritage-gallery/types';

const registry = new Map<string, GalleryArtwork>();
const RUNTIME_STORAGE_KEY = 'wenmai_gallery_runtime_artworks_v1';

function loadCachedRuntime(): GalleryArtwork[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(RUNTIME_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is GalleryArtwork => {
      if (!item || typeof item !== 'object') return false;
      const candidate = item as GalleryArtwork;
      return Boolean(candidate.id && candidate.imageUrl && candidate.title && !isCaseDeleted(candidate.id));
    });
  } catch {
    return [];
  }
}

export function resetArtworkRegistry(items: GalleryArtwork[]): void {
  registry.clear();
  for (const item of items) {
    if (item?.id) registry.set(item.id, item);
  }
}

export function findArtwork(id: string | undefined): GalleryArtwork | undefined {
  if (!id) return undefined;
  return registry.get(id);
}

export function listArtworks(): GalleryArtwork[] {
  return Array.from(registry.values());
}

// 先用「内置 + 上次缓存的新作品」兜底：刷新页面后，已挂上新作品的画框
// 不会因为后端还没返回而变成空框。
resetArtworkRegistry([...loadCachedRuntime(), ...galleryArtworks]);
