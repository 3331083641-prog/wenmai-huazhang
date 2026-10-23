/** Resolve public assets for both local development and a Pages subpath. */
export function publicUrl(path: string): string {
  if (/^(?:https?:|data:|blob:|\/\/)/.test(path)) return path;
  const base = import.meta.env.BASE_URL || '/';
  // Imported Vite assets already contain BASE_URL. Do not prepend it twice.
  if (path.startsWith(base)) return path;
  const normalized = path.replace(/^\//, '');
  return `${base.replace(/\/$/, '')}/${normalized}`;
}
