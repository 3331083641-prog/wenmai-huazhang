import { Link, useLocation } from 'react-router-dom';
import { cn } from '../lib/utils';
import { Leaf, Home, Palette, Wand2, Archive, FolderHeart, Info } from 'lucide-react';

const MENU_ITEMS = [
  { name: '首页', path: '/', icon: Home },
  { name: '风格库', path: '/styles', icon: Palette },
  { name: '智能生成', path: '/creator', icon: Wand2 },
  { name: '文创转化', path: '/products', icon: Archive },
  { name: '关于项目', path: '/about', icon: Info },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside className="w-64 bg-ink text-paper h-full flex flex-col shadow-[4px_0_15px_rgba(0,0,0,0.1)] relative z-20">
      <div className="h-20 flex items-center px-6 border-b border-primary/20">
        <Link to="/" className="flex items-center gap-2 text-gold">
          <Leaf className="w-7 h-7" />
          <span className="font-serif font-bold text-xl tracking-widest">纹脉华章</span>
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto py-6">
        <nav className="flex flex-col gap-2 px-4">
          {MENU_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-300",
                  isActive
                    ? "bg-primary text-white shadow-[0_4px_12px_rgba(158,36,27,0.3)] font-medium"
                    : "text-paper/70 hover:bg-white/5 hover:text-white"
                )}
              >
                <Icon className={cn("w-5 h-5", isActive ? "text-gold" : "")} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="p-4 border-t border-primary/20">
        <div className="bg-white/5 rounded-lg p-4 text-center">
          <p className="text-xs text-gold/80 mb-2">当前图像生成服务</p>
          <div className="text-sm font-medium">阿里云百炼 · Qwen Image 3.0</div>
        </div>
      </div>
    </aside>
  );
}
