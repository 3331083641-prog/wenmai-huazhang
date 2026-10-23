/**
 * public/ 下资源的解析。
 * 静态展示模式会用非根 base（GitHub Pages 子路径），所以不能写死 '/interactive/...'。
 */
export function publicUrl(path: string): string {
  const base = import.meta.env.BASE_URL || '/';
  const normalized = path.replace(/^\//, '');
  return `${base.replace(/\/$/, '')}/${normalized}`;
}