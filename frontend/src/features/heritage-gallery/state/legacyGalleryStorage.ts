/**
 * 国赛经典馆使用独立的布展存档。双展馆时期的 classic 分桶可以复制到此存档，
 * v15 使用的 v1 存档和原分桶均保留，以便恢复此前的布展。
 */

export const CONTEST_CURATION_KEY = 'wenmai-heritage-gallery-opc-v5';
const CURATION_V2 = 'wenmai-heritage-gallery-v2';
export const CONTEST_DIY_KEY = 'wenmai-gallery-diy-opc-v5';
const DIY_V2 = 'wenmai-gallery-diy-v2';

type Json = Record<string, unknown>;

function readJson(key: string): Json | null {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as Json) : null;
  } catch {
    return null;
  }
}

function writeJson(key: string, value: Json): void {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* 隐私模式或配额满：放弃迁移，不影响页面 */
  }
}

function pickState(parsed: Json | null): Json | null {
  if (!parsed) return null;
  const state = parsed.state;
  return state && typeof state === 'object' ? (state as Json) : parsed;
}

/** 复制 v2 的经典馆画框布展。 */
function migrateCuration(): boolean {
  if (window.localStorage.getItem(CONTEST_CURATION_KEY)) return false;
  const state = pickState(readJson(CURATION_V2));
  const plans = state?.plans as Json | undefined;
  const classic = plans?.classic as Json | undefined;
  if (!classic) return false;
  const assignments = (classic.assignments ?? {}) as Json;
  const positions = (classic.positions ?? {}) as Json;
  if (!Object.keys(assignments).length && !Object.keys(positions).length) return false;
  writeJson(CONTEST_CURATION_KEY, { state: { assignments, positions }, version: 1 });
  return true;
}

/** 复制 v2 的经典馆器物布展。 */
function migrateDiy(): boolean {
  if (window.localStorage.getItem(CONTEST_DIY_KEY)) return false;
  const state = pickState(readJson(DIY_V2));
  const byBuilding = state?.byBuilding as Json | undefined;
  const classic = byBuilding?.classic as Json | undefined;
  if (!classic) return false;
  const items = classic.items;
  if (!Array.isArray(items) || items.length === 0) return false;
  writeJson(CONTEST_DIY_KEY, {
    state: { items, roofTint: (classic.roofTint as string) ?? 'dai' },
    version: 1,
  });
  return true;
}

/**
 * 在 React 挂载前调用一次。
 * 返回迁移结果，便于排查（不参与 UI）。
 */
export function migrateLegacyGalleryStorage(): { curation: boolean; diy: boolean } {
  const result = { curation: false, diy: false };
  if (typeof window === 'undefined' || !window.localStorage) return result;
  try {
    result.curation = migrateCuration();
    result.diy = migrateDiy();
  } catch {
    /* 迁移失败不能阻塞展馆 */
  }
  return result;
}

export function getContestGalleryStorage(): Storage {
  migrateLegacyGalleryStorage();
  return localStorage;
}
