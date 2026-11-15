import { projectBrand } from '../data/projectBrand';
import { Link } from 'react-router-dom';
import { APP_VERSION } from '../version';
import { Sparkles, Compass, Palette, Layout, ShieldCheck, Cpu } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="relative mt-auto border-t border-gold/30 bg-[#F5ECE0] text-ink overflow-hidden">
      {/* 宣纸微噪点与光晕背景 */}
      <div className="absolute inset-0 paper-noise pointer-events-none" />
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-gold/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-10 w-80 h-80 bg-primary/8 rounded-full blur-3xl pointer-events-none" />

      <div className="relative mx-auto max-w-7xl px-6 py-14 lg:py-16">
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-12 lg:gap-8 mb-12">
          {/* 左侧：品牌与文化卷尾跋文 */}
          <div className="lg:col-span-6 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-gold/50 bg-white/80 shadow-xs">
                  <img src="/leaf-logo.png" alt="" className="h-6 w-6 object-contain" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-serif text-2xl font-bold tracking-[0.12em] text-ink">
                      {projectBrand.name}
                    </span>
                    <span className="chinese-seal text-[11px]">文脉相承</span>
                  </div>
                  <p className="font-serif text-xs text-primary/80 tracking-wider">
                    {projectBrand.subtitle}
                  </p>
                </div>
              </div>

              <p className="max-w-md text-sm text-ink/75 leading-relaxed font-sans mb-6">
                让中华优秀传统文化从<span className="text-primary font-medium">“被观看”走向“被共创”</span>。
                平台以多模态生成大模型与端侧视觉理解为支点，贯通主题创作、多维深度赏析、三维虚拟展陈与文创转化全流程。
              </p>
            </div>

            {/* 技术基石徽标 */}
            <div className="flex flex-wrap items-center gap-2 pt-4 border-t border-gold/25 text-xs text-ink/70">
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/70 border border-gold/30">
                <Sparkles className="w-3 h-3 text-gold" /> Qwen Image 3.0
              </span>
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/70 border border-gold/30">
                <Cpu className="w-3 h-3 text-primary" /> 本地 Qwen3-VL
              </span>
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/70 border border-gold/30">
                <Compass className="w-3 h-3 text-gold" /> Three.js 虚拟展馆
              </span>
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/70 border border-gold/30">
                <ShieldCheck className="w-3 h-3 text-emerald-700" /> 本地沙箱持久化
              </span>
            </div>
          </div>

          {/* 右侧：功能导航与展陈通道 */}
          <div className="lg:col-span-6 grid grid-cols-2 sm:grid-cols-3 gap-6">
            <div>
              <p className="font-serif text-xs font-bold tracking-[0.2em] text-primary uppercase mb-4">
                文化与创作
              </p>
              <ul className="space-y-2.5 text-xs font-serif text-ink/75">
                <li>
                  <Link to="/styles" className="hover:text-primary transition-colors">
                    五大传统风格库
                  </Link>
                </li>
                <li>
                  <Link to="/creator" className="hover:text-primary transition-colors flex items-center gap-1">
                    智能生成工作台
                    <span className="text-[10px] text-gold font-mono">NEW</span>
                  </Link>
                </li>
                <li>
                  <Link to="/gallery" className="hover:text-primary transition-colors">
                    作品展厅与案例
                  </Link>
                </li>
                <li>
                  <Link to="/creator?mode=ref" className="hover:text-primary transition-colors">
                    参考图控色共创
                  </Link>
                </li>
              </ul>
            </div>

            <div>
              <p className="font-serif text-xs font-bold tracking-[0.2em] text-primary uppercase mb-4">
                展陈与应用
              </p>
              <ul className="space-y-2.5 text-xs font-serif text-ink/75">
                <li>
                  <Link to="/heritage-gallery" className="hover:text-primary transition-colors">
                    三维纹脉虚拟展馆
                  </Link>
                </li>
                <li>
                  <Link to="/products" className="hover:text-primary transition-colors">
                    文创工坊与衍生打样
                  </Link>
                </li>
                <li>
                  <Link to="/scenarios" className="hover:text-primary transition-colors">
                    空间展陈与生活美学
                  </Link>
                </li>
                <li>
                  <Link to="/wander/songhua-yunhe" className="hover:text-primary transition-colors">
                    2.5D 青绿山水漫游
                  </Link>
                </li>
              </ul>
            </div>

            <div className="col-span-2 sm:col-span-1">
              <p className="font-serif text-xs font-bold tracking-[0.2em] text-primary uppercase mb-4">
                项目与标准
              </p>
              <ul className="space-y-2.5 text-xs font-serif text-ink/75">
                <li>
                  <Link to="/about" className="hover:text-primary transition-colors">
                    技术架构与定位
                  </Link>
                </li>
                <li>
                  <Link to="/about#security" className="hover:text-primary transition-colors">
                    非遗与文案纪律
                  </Link>
                </li>
                <li>
                  <a
                    href="https://github.com/3331083641-prog/wenmai-huazhang"
                    target="_blank"
                    rel="noreferrer"
                    className="hover:text-primary transition-colors"
                  >
                    GitHub 源码仓库
                  </a>
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* 底部版权与版本核验注记 */}
        <div className="pt-8 border-t border-gold/30 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-ink/60">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-primary/70" />
            <span>© 2026 {projectBrand.name}项目团队 · 传统文化视觉智能创作与文创应用平台</span>
          </div>
          <div className="flex items-center gap-3 font-mono text-[11px] text-ink/50">
            <span className="px-2 py-0.5 rounded bg-white/60 border border-gold/20">
              {APP_VERSION.version}
            </span>
            <span className="hidden md:inline">{APP_VERSION.releaseName}</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
