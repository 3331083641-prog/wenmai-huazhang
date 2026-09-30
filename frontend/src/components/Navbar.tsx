import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '../lib/utils';
import { Leaf, Menu, X } from 'lucide-react';

const NAV_ITEMS = [
  { name: '首页', path: '/' },
  { name: '风格库', path: '/styles' },
  { name: '智能生成', path: '/creator' },
  { name: '文创转化', path: '/products' },
  { name: '应用场景', path: '/scenarios' },
  { name: '关于项目', path: '/about' },
];

export default function Navbar() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => setMobileOpen(false), [location.pathname]);

  return (
    <header className="fixed top-0 left-0 right-0 h-16 bg-paper/90 backdrop-blur-md border-b-[rgba(184,66,46,0.1)] z-50">
      <div className="max-w-7xl mx-auto px-6 h-full flex items-center justify-between border-b border-border-red/10">
        <Link to="/" className="flex items-center gap-2 text-primary">
          <Leaf className="w-6 h-6" />
          <span className="font-serif font-bold text-xl tracking-wider">纹脉华章</span>
        </Link>
        <nav className="hidden md:flex items-center gap-8">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "text-sm font-medium transition-colors hover:text-primary",
                location.pathname === item.path ? "text-primary border-b-2 border-primary py-1" : "text-ink/80"
              )}
            >
              {item.name}
            </Link>
          ))}
        </nav>
        <div className="hidden md:block">
          <Link
            to="/creator"
            className="px-5 py-2 rounded-full bg-primary text-white text-sm font-medium hover:bg-primary-dark transition-all shadow-[0_4px_10px_rgba(158,36,27,0.2)]"
          >
            进入工作台
          </Link>
        </div>
        <button
          type="button"
          className="md:hidden inline-flex items-center justify-center w-10 h-10 rounded-md text-primary hover:bg-primary/5 transition-colors"
          aria-label={mobileOpen ? '关闭导航菜单' : '打开导航菜单'}
          aria-expanded={mobileOpen}
          aria-controls="mobile-navigation"
          onClick={() => setMobileOpen(open => !open)}
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>
      {mobileOpen && (
        <nav id="mobile-navigation" className="md:hidden absolute top-full inset-x-0 bg-paper border-b border-primary/10 shadow-lg px-6 py-3">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              onClick={() => setMobileOpen(false)}
              className={cn(
                'block py-3 text-sm font-medium border-b border-primary/5 last:border-b-0 transition-colors',
                location.pathname === item.path ? 'text-primary' : 'text-ink/80 hover:text-primary'
              )}
            >
              {item.name}
            </Link>
          ))}
          <Link
            to="/creator"
            onClick={() => setMobileOpen(false)}
            className="mt-3 block rounded-full bg-primary text-white text-sm font-medium text-center py-2.5 shadow-[0_4px_10px_rgba(158,36,27,0.2)]"
          >
            进入工作台
          </Link>
        </nav>
      )}
    </header>
  );
}
