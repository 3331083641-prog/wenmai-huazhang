import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '../lib/utils';
import { Leaf, Menu, X } from 'lucide-react';

/**
 * 全站唯一导航顺序：风格库 → 智能生成 → 作品展厅 → 纹脉展馆 → 文创转化 → 应用场景 → 关于项目。
 * 首页不设导航项，由左侧品牌 Logo 回到 `/`。
 * 纹脉展馆（/heritage-gallery）与画境漫游（/wander/:id）在 App.tsx 里渲染于 MainLayout 之外，
 * 因此沉浸式页面本来就不会出现这根导航条 —— 不要为了“补全导航”把它们挪进布局。
 */
const NAV_ITEMS = [
  { name: '风格库', path: '/styles' },
  { name: '智能生成', path: '/creator' },
  { name: '作品展厅', path: '/gallery' },
  { name: '纹脉展馆', path: '/heritage-gallery' },
  { name: '文创转化', path: '/products' },
  { name: '应用场景', path: '/scenarios' },
  { name: '关于项目', path: '/about' },
];

export default function Navbar() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => setMobileOpen(false), [location.pathname]);

  // 子路由（如 /experience/:id）应继续高亮其所属的展厅条目
  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(`${path}/`);

  return (
    <header className="fixed inset-x-0 top-0 z-50 h-16 border-b border-primary/10 bg-paper/90 backdrop-blur-md">
      <div className="mx-auto flex h-full max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link to="/" className="group flex shrink-0 items-center gap-2 text-primary" aria-label="纹脉华章 首页">
          <Leaf className="h-6 w-6 transition-transform group-hover:-rotate-6" />
          <span className="font-serif text-lg font-bold tracking-[0.12em] sm:text-xl">纹脉华章</span>
        </Link>

        {/* 桌面：单行七项，统一 64px 行高，当前项只用朱红字色 + 金色短底线标示 */}
        <nav className="hidden h-full items-center lg:flex" aria-label="主导航">
          {NAV_ITEMS.map((item) => {
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'relative inline-flex h-full items-center whitespace-nowrap px-3 text-[13.5px] font-medium tracking-wide transition-colors',
                  active ? 'text-primary' : 'text-ink/70 hover:text-primary',
                )}
              >
                {item.name}
                <span
                  aria-hidden="true"
                  className={cn(
                    'pointer-events-none absolute inset-x-3 bottom-[15px] h-[2px] rounded-full transition-opacity duration-200',
                    active ? 'bg-gold opacity-100' : 'opacity-0',
                  )}
                />
              </Link>
            );
          })}
        </nav>

        <div className="hidden shrink-0 items-center gap-2 lg:flex">
          <Link
            to="/creator"
            className="inline-flex items-center rounded-full bg-primary px-4 py-1.5 text-[13px] font-medium text-white shadow-[0_4px_10px_rgba(158,36,27,0.2)] transition-colors hover:bg-primary-dark"
          >
            开始创作
          </Link>
        </div>

        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-md text-primary transition-colors hover:bg-primary/5 lg:hidden"
          aria-label={mobileOpen ? '关闭导航菜单' : '打开导航菜单'}
          aria-expanded={mobileOpen}
          aria-controls="mobile-navigation"
          onClick={() => setMobileOpen((open) => !open)}
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {mobileOpen && (
        <nav
          id="mobile-navigation"
          aria-label="移动端导航"
          className="absolute inset-x-0 top-full max-h-[calc(100vh-4rem)] overflow-y-auto border-b border-primary/10 bg-paper px-4 pb-4 pt-1 shadow-lg lg:hidden"
        >
          {NAV_ITEMS.map((item) => {
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileOpen(false)}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'flex items-center justify-between border-b border-primary/5 py-3 text-sm font-medium transition-colors last:border-b-0',
                  active ? 'text-primary' : 'text-ink/75 hover:text-primary',
                )}
              >
                {item.name}
                {active && <span className="h-1.5 w-1.5 rounded-full bg-gold" />}
              </Link>
            );
          })}
          <Link
            to="/creator"
            onClick={() => setMobileOpen(false)}
            className="mt-3 block rounded-full bg-primary py-2.5 text-center text-sm font-medium text-white shadow-[0_4px_10px_rgba(158,36,27,0.2)]"
          >
            开始创作
          </Link>
        </nav>
      )}
    </header>
  );
}