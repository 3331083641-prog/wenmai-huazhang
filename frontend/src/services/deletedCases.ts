/** Keep deleted runtime snapshots hidden until the next static rebuild too. */
export const DELETED_CASES_KEY = 'wenmai_deleted_runtime_case_ids_v1';

export function deletedCaseIds(): Set<string> {
  try {
    const values:unknown=JSON.parse(localStorage.getItem(DELETED_CASES_KEY)??'[]');
    return new Set(Array.isArray(values)?values.filter((item):item is string=>typeof item==='string'):[]);
  } catch { return new Set(); }
}

export function isCaseDeleted(id:string):boolean { return deletedCaseIds().has(id); }

export function markCaseDeleted(id:string):Set<string> {
  const ids=deletedCaseIds();ids.add(id);
  try { localStorage.setItem(DELETED_CASES_KEY,JSON.stringify([...ids])); } catch { /* in-memory UI still updates */ }
  return ids;
}
