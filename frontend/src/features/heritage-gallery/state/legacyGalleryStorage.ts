/**
 * 单展馆回归 · 本地布展数据兼容迁移
 *
 * 背景：双展馆版本曾把布展数据改成「按建筑分桶」并写入新的 localStorage key
 * （`wenmai-heritage-gallery-v2` / `wenmai-gallery-diy-v2`）。
 * 现在回到单展馆版本，store 读的是旧的 v1 key。如果用户在这期间布展过，
 * 直接回退会看到「布展全没了」——数据其实还在 v2 里，只是没人读。
 *
 * 这里做一次**只读→复制**的迁移（不改也不删 v2，方便再次回退）：
 *   v2 的 plans.classic      -> v1 { assignments, positions }
 *   v2 的 byBuilding.classic -> v1 { items, roofTint }
 *
 * 三条原则：
 *  1. 只在 v1 不存在时迁移，绝不覆盖用户已有的旧版布展；
 *  2. 任何异常都吞掉，迁移失败不能阻塞展馆加载；
 *  3. 迁移结果与 zustand persist 的存储格式完全一致（{ state, version }）。
 */

const CURATION_V1 = 'wenmai-heritage-gallery-v1';
const CURATION_V2 = 'wenmai-heritage-gallery-v2';
const DIY_V1 = 'wenmai-gallery-diy-v1';
const DIY_V2 = 'wenmai-gallery-diy-v2';
const BUILDING_KEY = 'wenmai-gallery-building-v1';

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

/** 画框布展：v2 的经典馆分桶 -> v1 */
function migrateCuration(): boolean {
  if (window.localStorage.getItem(CURATION_V1)) return false;
  const state = pickState(readJson(CURATION_V2));
  const plans = state?.plans as Json | undefined;
  const classic = plans?.classic as Json | undefined;
  if (!classic) return false;
  const assignments = (classic.assignments ?? {}) as Json;
  const positions = (classic.positions ?? {}) as Json;
  if (!Object.keys(assignments).length && !Object.keys(positions).length) return false;
  writeJson(CURATION_V1, { state: { assignments, positions }, version: 1 });
  return true;
}

/** 器物布展：v2 的经典馆分桶 -> v1 */
function migrateDiy(): boolean {
  if (window.localStorage.getItem(DIY_V1)) return false;
  const state = pickState(readJson(DIY_V2));
  const byBuilding = state?.byBuilding as Json | undefined;
  const classic = byBuilding?.classic as Json | undefined;
  if (!classic) return false;
  const items = classic.items;
  if (!Array.isArray(items) || items.length === 0) return false;
  writeJson(DIY_V1, {
    state: { items, roofTint: (classic.roofTint as string) ?? 'dai' },
    version: 1,
  });
  return true;
}

/** 建筑皮肤选择已废弃：清掉残留 key，避免以后误读 */
function clearObsoleteBuildingKey(): void {
  try {
    window.localStorage.removeItem(BUILDING_KEY);
  } catch {
    /* ignore */
  }
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
    clearObsoleteBuildingKey();
    if (result.curation || result.diy) {
      console.info('[gallery] 已把双展馆时期的经典馆布展迁移回单展馆存储', result);
    }
  } catch {
    /* 迁移失败不能阻塞展馆 */
  }
  return result;
}