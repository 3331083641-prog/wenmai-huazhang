/**
 * 运行期作品 → 互动体验的加载器。
 *
 * 背景：内置五件作品的体验是编译期模块；新生成作品的 experience.json 在
 * docs/examples/<caseId>/ 下，不能靠 import.meta.glob 及时出现。这里改为
 * 运行期请求 `GET /cases/<caseId>`，由后端返回这件作品**自己的**体验数据、
 * 图片地址与资产地址，再用同一套 schema 校验、挂上 URL。
 *
 * 约束：
 *  - 只用 caseId 取数据，不按 styleId 猜测作品身份；
 *  - 校验失败不静默伪造，返回 null，由页面显示「数据不完整」并可返回展厅；
 *  - 同一 caseId 的内存缓存避免三个页面来回请求。
 */
import type { CultureExperience, CultureExperienceDraft } from '../features/culture-experience/types';
import { parseExperienceDraft } from '../features/culture-experience/schema';
import { fetchCaseDetail } from '../services/caseService';
import { isCaseDeleted } from '../services/deletedCases';

const cache = new Map<string, CultureExperience>();
const inflight = new Map<string, Promise<CultureExperience | null>>();

export function getRuntimeExperience(id: string | undefined): CultureExperience | undefined {
  return id ? cache.get(id) : undefined;
}

export function clearRuntimeExperience(id?: string): void {
  if (id) cache.delete(id);
  else cache.clear();
}

export async function loadRuntimeExperience(id: string, refresh = false): Promise<CultureExperience | null> {
  if (!id || isCaseDeleted(id)) return null;
  const cached = cache.get(id);
  if (cached && !refresh) return cached;

  const running = inflight.get(id);
  if (running) return running;

  const task = (async () => {
    const detail = await fetchCaseDetail(id);
    if (!detail || !detail.experience) return null;
    const raw = detail.experience;
    const styleId = String(raw.styleId || detail.case.styleId || '');
    const animation = raw.animation as CultureExperienceDraft['animation'];
    // 资源的唯一可信来源是 Case Service 返回的这件作品自己的地址。
    const draft = {
      ...raw,
      animation: animation?.mode === 'world' && detail.case.worldUrl
        ? { ...animation, world: { ...animation.world, url: detail.case.worldUrl } } : animation,
      artworkUrl: detail.case.imageUrl,
      referenceUrl: detail.case.referenceUrl ?? '',
      cultureCardUrl: detail.case.cardUrl ?? '',
    } as unknown as CultureExperienceDraft;
    const parsed = parseExperienceDraft(draft, styleId);
    const experience: CultureExperience = {
      ...parsed,
      artworkUrl: detail.case.imageUrl,
      referenceUrl: detail.case.referenceUrl || undefined,
      cultureCardUrl: detail.case.cardUrl || undefined,
    };
    cache.set(id, experience);
    return experience;
  })()
    .catch((error) => {
      console.warn(`[runtime-experience] ${id} 加载失败`, error);
      return null;
    })
    .finally(() => {
      inflight.delete(id);
    });

  inflight.set(id, task);
  return task;
}
