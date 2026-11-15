import { projectBrand } from '../data/projectBrand';
import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '../lib/utils';
import { Menu, X, Sparkles, Compass } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

/**
 * 全站唯一导航项定义（保留全部原有目标与顺序）
 */
const NAV_ITEMS = [
  { name: '首页', path: '/', en: 'Home' },
  { name: '风格库', path: '/styles', en: 'Styles' },
  { name: '智能生成', path: '/creator', en: 'Creator' },
  { name: '作品展厅', path: '/gallery', en: 'Gallery' },
  { name: '纹脉展馆', path: '/heritage-gallery', en: 'Pavilion' },
  { name: '文创转化', path: '/products', en: 'Studio' },
  { name: '应用场景', path: '/scenarios', en: 'Scenarios' },
  { name: '关于项目', path: '/about', en: 'About' },
];

export default function Navbar() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const isActive = (path: string) =>
    path === '/'
      ? location.pathname === '/'
      : location.pathname === path || location.pathname.startsWith(`${path}/`);

  return (
    <header
      className={cn(
        'fixed inset-x-0 top-0 z-50 transition-all duration-300',
        scrolled
          ? 'h-16 bg-[#F8EEDC]/92 backdrop-blur-md border-b border-gold/30 shadow-[0_8px_30px_rgba(63,43,31,0.06)]'
          : 'h-18 bg-[#F8EEDC]/80 backdrop-blur-sm border-b border-gold/15 shadow-none'
      )}
    >
      <div className="mx-auto flex h-full max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
        {/* Brand Area */}
        <Link
          to="/"
          className="group flex shrink-0 items-center gap-2.5 text-primary focus-visible:outline-none"
          aria-label={`${projectBrand.fullName} 首页`}
        >
          <div className="relative flex h-8 w-8 items-center justify-center rounded-lg border border-gold/40 bg-white/70 shadow-xs transition-transform duration-300 group-hover:-rotate-3 group-hover:scale-105">
            <img
              src="/leaf-logo.png"
              alt=""
              aria-hidden="true"
              className="h-5 w-5 object-contain"
            />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="font-serif text-lg font-bold tracking-[0.14em] text-ink sm:text-xl transition-colors group-hover:text-primary">
                {projectBrand.name}
              </span>
              <span className="chinese-seal text-[10px] hidden sm:inline-flex">华章</span>
            </div>
            <span className="text-[10px] tracking-[0.2em] font-serif text-primary/70 uppercase scale-90 origin-left hidden md:inline">
              Wenmai Huazhang
            </span>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden h-full items-center gap-1 xl:gap-2 lg:flex" aria-label="主导航">
          {NAV_ITEMS.map((item) => {
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'relative inline-flex h-full items-center px-3 py-1 text-[13.5px] font-medium tracking-wide transition-colors group',
                  active
                    ? 'text-primary font-semibold'
                    : 'text-ink/75 hover:text-primary'
                )}
              >
                <span className="relative z-10">{item.name}</span>
                {active ? (
                  <motion.div
                    layoutId="navbar-active-pill"
                    className="absolute inset-x-2 bottom-3.5 h-[2.5px] rounded-full bg-gradient-to-r from-primary via-gold to-primary"
                    transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                  />
                ) : (
                  <span className="pointer-events-none absolute inset-x-3 bottom-3.5 h-[1.5px] scale-x-0 rounded-full bg-primary/40 opacity-0 transition-all duration-200 group-hover:scale-x-100 group-hover:opacity-100" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Right CTA */}
        <div className="hidden shrink-0 items-center gap-3 lg:flex">
          <Link
            to="/heritage-gallery"
            className="inline-flex items-center gap-1.5 rounded-full border border-gold/40 bg-white/70 px-3.5 py-1.5 text-xs font-serif text-ink/80 transition-all hover:border-primary/40 hover:bg-white hover:text-primary"
          >
            <Compass className="h-3.5 w-3.5 text-gold" />
            <span>三维展馆</span>
          </Link>
          <Link
            to="/creator"
            className="group relative inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-primary to-primary-dark px-4 py-1.5 text-xs font-medium text-white shadow-[0_4px_12px_rgba(158,36,27,0.25)] transition-all hover:shadow-[0_6px_18px_rgba(158,36,27,0.35)] hover:-translate-y-0.5"
          >
            <Sparkles className="h-3.5 w-3.5 text-gold animate-pulse" />
            <span>立即共创</span>
          </Link>
        </div>

        {/* Mobile Toggle Button */}
        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-gold/30 bg-white/60 text-primary transition-colors hover:bg-white lg:hidden"
          aria-label={mobileOpen ? '关闭导航菜单' : '打开导航菜单'}
          aria-expanded={mobileOpen}
          aria-controls="mobile-navigation"
          onClick={() => setMobileOpen((open) => !open)}
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile Drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.nav
            id="mobile-navigation"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            aria-label="移动端导航"
            className="border-b border-gold/30 bg-[#F8EEDC]/98 px-5 pb-6 pt-3 shadow-2xl backdrop-blur-xl lg:hidden"
          >
            <div className="grid grid-cols-2 gap-2.5 mb-4">
              {NAV_ITEMS.map((item) => {
                const active = isActive(item.path);
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    aria-current={active ? 'page' : undefined}
                    className={cn(
                      'flex flex-col rounded-xl p-3 border transition-all',
                      active
                        ? 'border-primary/40 bg-white text-primary shadow-xs font-semibold'
                        : 'border-gold/20 bg-white/50 text-ink/80 hover:bg-white hover:text-primary'
                    )}
                  >
                    <span className="font-serif text-sm">{item.name}</span>
                    <span className="text-[10px] text-ink/40 font-mono tracking-wider">{item.en}</span>
                  </Link>
                );
              })}
            </div>
            <div className="pt-2 border-t border-gold/20 flex gap-2">
              <Link
                to="/creator"
                className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-xl bg-primary py-2.5 text-xs font-medium text-white shadow-sm"
              >
                <Sparkles className="h-3.5 w-3.5 text-gold" />
                <span>开始智能生成</span>
              </Link>
              <Link
                to="/heritage-gallery"
                className="inline-flex items-center justify-center gap-1 rounded-xl border border-gold/40 bg-white/80 px-4 py-2.5 text-xs font-serif text-ink"
              >
                <Compass className="h-3.5 w-3.5 text-gold" />
                <span>三维展馆</span>
              </Link>
            </div>
          </motion.nav>
        )}
      </AnimatePresence>
    </header>
  );
}
