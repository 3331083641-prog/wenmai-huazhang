import { useState } from 'react';
import { ArrowRight, Info, Filter, Palette, Sparkles, BookOpen } from 'lucide-react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { cn } from '../lib/utils';
import { STYLES } from '../data/styleLibrary';

const CATEGORIES = [
  { id: '全部', label: '全部风格', count: STYLES.length },
  { id: '年画', label: '木版年画', count: STYLES.filter(s => s.tag === '年画').length },
  { id: '山水', label: '青绿山水', count: STYLES.filter(s => s.tag === '山水').length },
  { id: '刺绣', label: '传统刺绣', count: STYLES.filter(s => s.tag === '刺绣').length },
  { id: '陶瓷', label: '青花瓷饰', count: STYLES.filter(s => s.tag === '陶瓷').length },
  { id: '剪纸', label: '民间剪纸', count: STYLES.filter(s => s.tag === '剪纸').length },
];

/**
 * 风格专属色标梯次（彰显五大风格独特的设色哲学）
 */
const STYLE_PALETTES: Record<string, string[]> = {
  zhuxianzhen: ['#9E241B', '#D2A14A', '#2D4E35', '#24211E'],
  bianxiu: ['#A64C54', '#D89E78', '#6A7F6E', '#F6E5CC'],
  songhua: ['#2F5C54', '#557F70', '#C3A575', '#8C6F4B'],
  qinghua: ['#234B74', '#4D7DA8', '#99B9D4', '#F4F7FA'],
  jianzhi: ['#B82823', '#D6453D', '#FAF0EB', '#1F1B1A'],
};

export default function StyleLibrary() {
  const [activeCategory, setActiveCategory] = useState('全部');

  const filteredStyles = activeCategory === '全部'
    ? STYLES
    : STYLES.filter(s => s.tag === activeCategory);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 md:py-16">
      {/* 头部：典雅题匾与书卷叙事 */}
      <div className="text-center max-w-3xl mx-auto mb-14">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-gold/40 bg-white/70 shadow-xs mb-4">
          <Palette className="w-3.5 h-3.5 text-gold" />
          <span className="text-xs font-serif font-medium text-ink/80 tracking-widest">
            传统文化视觉风格基因库
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-serif font-bold text-ink mb-4 flex items-center justify-center gap-3">
          五大传统文化视觉风格库
        </h1>
        <p className="text-sm sm:text-base text-ink/75 leading-relaxed font-sans">
          平台深入民间工艺、传统绘画与器物装饰等五大核心视觉门类，系统提炼设色谱系、构图法则与纹样肌理，为 AI 创作工作台提供精确的文化语义先验约束。
        </p>
      </div>

      {/* 签条式分类筛选栏 */}
      <div className="flex flex-wrap items-center justify-center gap-2.5 sm:gap-3 mb-14">
        <div className="hidden sm:flex items-center gap-1.5 text-xs font-serif text-ink/50 mr-2">
          <Filter className="w-3.5 h-3.5 text-gold" />
          <span>门类甄选：</span>
        </div>
        {CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setActiveCategory(cat.id)}
            className={cn(
              "px-4 py-2 rounded-xl text-xs sm:text-sm font-serif transition-all duration-300 flex items-center gap-1.5 shadow-xs cursor-pointer",
              activeCategory === cat.id
                ? "bg-primary text-white shadow-[0_6px_18px_rgba(158,36,27,0.25)] border border-gold/50"
                : "bg-white/80 border border-gold/25 text-ink/75 hover:border-primary/40 hover:bg-white hover:text-primary"
            )}
          >
            <span>{cat.label}</span>
            <span className={cn(
              "text-[10px] px-1.5 py-0.2 rounded-full font-mono",
              activeCategory === cat.id ? "bg-white/20 text-white" : "bg-black/5 text-ink/50"
            )}>
              {cat.count}
            </span>
          </button>
        ))}
      </div>

      {/* Refero 灵感画廊美学卡片瀑布流 */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 md:gap-10 mb-20">
        <AnimatePresence mode="popLayout">
          {filteredStyles.map((style, i) => {
            const palette = STYLE_PALETTES[style.id] || ['#9E241B', '#D2A14A', '#2D4E35'];
            return (
              <motion.div
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.45, delay: i * 0.05 }}
                key={style.id}
                className="oriental-gallery-card rounded-2xl overflow-hidden shadow-[0_10px_30px_rgba(63,43,31,0.06)] hover:shadow-[0_20px_45px_rgba(158,36,27,0.14)] hover:-translate-y-1.5 transition-all duration-400 flex flex-col group"
              >
                {/* 典藏画幅区域 */}
                <div className="aspect-[4/3] relative overflow-hidden bg-black/5">
                  <img
                    src={style.img || '/zhuxianzhen.png'}
                    alt={style.name}
                    className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent pointer-events-none" />

                  {/* 顶部标签 */}
                  <div className="absolute top-3.5 left-3.5 flex flex-wrap gap-1.5 z-20">
                    {style.tags.map(tag => (
                      <span
                        key={tag}
                        className="px-2 py-0.5 text-[11px] font-serif bg-black/50 backdrop-blur-md text-white rounded-md border border-white/20 shadow-xs"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>

                  {/* 设色特征谱 */}
                  <div className="absolute bottom-3 right-3 flex items-center gap-1.5 bg-black/45 backdrop-blur-md px-2.5 py-1 rounded-full border border-white/20 z-20">
                    <span className="text-[10px] text-white/80 font-serif mr-1">特征色：</span>
                    {palette.map((color, idx) => (
                      <span
                        key={idx}
                        className="w-3 h-3 rounded-full border border-white/40 shadow-xs"
                        style={{ backgroundColor: color }}
                        title={color}
                      />
                    ))}
                  </div>
                </div>

                {/* 文字解读与信息层 */}
                <div className="p-6 flex-1 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-serif font-medium text-primary bg-primary/8 px-2.5 py-0.5 rounded border border-primary/15">
                        {style.categoryLabel}
                      </span>
                      <span className="text-[10px] font-mono text-gold font-bold">STYLE 0{i + 1}</span>
                    </div>

                    <h3 className="text-xl font-serif font-bold text-ink mb-2.5 group-hover:text-primary transition-colors">
                      {style.name}
                    </h3>

                    <p className="text-xs sm:text-sm text-ink/70 leading-relaxed line-clamp-3 mb-4 font-sans">
                      {style.desc}
                    </p>
                  </div>

                  {/* 特征说明与直观行动按钮（不再隐藏在悬停里） */}
                  <div>
                    <div className="p-3 rounded-xl bg-white/70 border border-gold/20 flex items-start gap-2 mb-4">
                      <Info className="w-4 h-4 text-gold shrink-0 mt-0.5" />
                      <p className="text-[11px] text-ink/65 leading-relaxed font-sans line-clamp-2">
                        {style.shortDescription || style.visualFeatures.join(' · ')}
                      </p>
                    </div>

                    <div className="pt-3 border-t border-gold/20 flex items-center justify-between gap-3">
                      <Link
                        to={`/creator?style=${style.id}`}
                        className="flex-1 inline-flex items-center justify-center gap-1.5 py-2.5 px-4 rounded-xl btn-chinese text-xs font-serif shadow-xs hover:shadow-md transition-all"
                      >
                        <Sparkles className="w-3.5 h-3.5 text-gold" />
                        <span>选用此风格共创</span>
                      </Link>

                      <Link
                        to="/gallery"
                        className="inline-flex items-center justify-center py-2.5 px-3 rounded-xl border border-gold/40 bg-white/80 hover:bg-white text-xs font-serif text-ink/75 hover:text-primary transition-all"
                      >
                        <span>赏析成图</span>
                      </Link>
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
