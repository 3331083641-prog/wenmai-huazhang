/**
 * 展馆可挂载的作品清单。
 *
 * 唯一来源：docs/examples/ 下随仓库提交的五组真实案例（与 savedCases.ts 同源）。
 * 不引入任何外部图片 —— 展馆里挂的每一张都必须能追溯到项目里的一份 metadata.json。
 *
 * 图片通过 import.meta.glob 在编译期打包成 URL，
 * 因此离线可用，也不依赖后端；子路径部署时由 Vite 统一处理。
 */

import { savedCases } from './savedCases';
import type { GalleryArtwork } from '../features/heritage-gallery/types';

/** 与现有互动体验一致的五种风格主题色 */
const STYLE_ACCENT: Record<string, string> = {
  zhuxianzhen: '#9E241B',
  bianxiu: '#A64C54',
  songhua: '#426C62',
  qinghua: '#315F88',
  jianzhi: '#A52225',
};

/**
 * 从现有 savedCases 派生出展馆作品。
 * 不复制字段、不另写一份文案 —— 案例元数据更新时展馆自动跟随。
 */
export const galleryArtworks: GalleryArtwork[] = savedCases.map((item) => ({
  id: item.caseId,
  title: item.artworkTitle,
  styleId: item.styleId,
  styleName: item.styleName,
  imageUrl: item.imageUrl,
  thumbUrl: item.imageUrl,
  cultureCardUrl: item.cardUrl,
  referenceUrl: item.referenceUrl,
  summary: item.visionAnalysis.culture_interpretation || item.visionAnalysis.theme_summary || '暂无文化解读。',
  features: item.visionAnalysis.visual_features.slice(0, 4),
  generatedAt: item.generatedAt,
  origin: item.caseOrigin,
  accent: STYLE_ACCENT[item.styleId] ?? '#9E241B',
}));

export const artworkById = new Map(galleryArtworks.map((item) => [item.id, item]));

export function getArtwork(id: string | undefined): GalleryArtwork | undefined {
  if (!id) return undefined;
  return artworkById.get(id);
}
