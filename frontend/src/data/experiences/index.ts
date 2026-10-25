/**
 * 体验数据装配层。
 *
 * 五件作品的图片资源沿用既有 savedCases 的 glob 导入方式（docs/examples/*），
 * 因此这些页面在完全离线、没有后端的情况下也能打开。
 * 作者态数据（data/experiences/*.ts）只管内容与几何，
 * URL 在这里统一注入，避免把 hash 化的资源路径写死在内容文件里。
 */

import { savedCases } from '../savedCases';
import { autoArtworkById, autoExperiences } from '../autoExperiences';
import { parseExperienceDraft, validateExperienceDraft } from '../../features/culture-experience/schema';
import type {
  CultureExperience,
  CultureExperienceDraft,
  CultureSource,
} from '../../features/culture-experience/types';
import zhuxianzhenExperience from './zhuxianzhen';
import bianxiuExperience from './bianxiu';
import songhuaExperience from './songhua';
import qinghuaExperience from './qinghua';
import jianzhiExperience from './jianzhi';
import sourcesJson from '../../../../culture_knowledge/sources.json';

const curatedDrafts: CultureExperienceDraft[] = [
  zhuxianzhenExperience,
  bianxiuExperience,
  songhuaExperience,
  qinghuaExperience,
  jianzhiExperience,
];
export const curatedExperienceIds = new Set(curatedDrafts.map((item) => item.id));
const drafts: CultureExperienceDraft[] = [
  ...curatedDrafts,
  // 流水线自动入库的案例：docs/examples/<case>/experience.json
  ...autoExperiences.map((item) => item.draft),
];

const caseByStyle = new Map(savedCases.map((item) => [item.styleId, item]));

function hydrate(draft: CultureExperienceDraft): CultureExperience {
  // 自动入库的案例必须用自己目录里的图：它们的 styleId 与精选案例相同，
  // 如果走 caseByStyle 就会拿到精选案例那张图，标题和图立刻错位。
  const autoArtwork = autoArtworkById.get(draft.id);
  const saved = autoArtwork ? undefined : caseByStyle.get(draft.styleId);
  return {
    ...draft,
    artworkUrl: autoArtwork ?? saved?.imageUrl ?? '',
    referenceUrl: autoArtwork ? undefined : saved?.referenceUrl,
    cultureCardUrl: autoArtwork ? undefined : saved?.cardUrl,
  };
}

/**
 * 校验并装配。开发期校验失败直接抛错，问题会由 ErrorBoundary 显示出来，
 * 而不是让页面带着错误坐标静默渲染 —— 那样最难排查。
 */
export const experiences: CultureExperience[] = drafts.map((draft) => {
  try {
    return hydrate(parseExperienceDraft(draft, draft.styleId));
  } catch (error) {
    if (import.meta.env.DEV) throw error;
    console.error('[culture-experience] 数据校验失败，已跳过该作品', error);
    return hydrate(draft);
  }
});

export const experienceById = new Map(experiences.map((item) => [item.id, item]));
export const experienceByStyle = new Map(experiences.filter((item) => curatedExperienceIds.has(item.id))
  .map((item) => [item.styleId, item]));

export function getExperience(id: string | undefined): CultureExperience | undefined {
  if (!id) return undefined;
  return experienceById.get(id) ?? experienceByStyle.get(id);
}

/** 文化来源注册表（与 culture_knowledge/sources.json 同源，不复制内容）。 */
const registry = sourcesJson as { version: string; updatedAt: string; sources: CultureSource[] };
export const cultureSources = registry.sources;
export const cultureSourcesVersion = registry.version;

const sourceIndex = new Map(cultureSources.map((source) => [source.id, source]));

export function getSource(id: string): CultureSource | undefined {
  return sourceIndex.get(id);
}

export function resolveSources(ids: string[]): CultureSource[] {
  return ids.map((id) => sourceIndex.get(id)).filter((item): item is CultureSource => Boolean(item));
}

/** 数据自检：返回所有作品的校验问题，供测试与「数据说明」面板使用。 */
export function auditExperienceData(): Array<{ id: string; issues: string[] }> {
  return drafts.map((draft) => ({
    id: draft.id,
    issues: validateExperienceDraft(draft).issues.map((issue) => `${issue.path}: ${issue.message}`),
  }));
}
