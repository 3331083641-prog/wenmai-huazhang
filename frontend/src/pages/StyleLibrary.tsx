import { useState } from 'react';
import { ArrowRight, Info, Filter, Palette, Image as ImageIcon } from 'lucide-react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { cn } from '../lib/utils';
import { STYLES } from '../data/styleLibrary';

const CATEGORIES = ['全部', '年画', '山水', '刺绣', '陶瓷', '剪纸'];

export default function StyleLibrary() {
  const [activeCategory, setActiveCategory] = useState('全部');
  const [hoveredStyle, setHoveredStyle] = useState<string | null>(null);

  const filteredStyles = activeCategory === '全部' 
    ? STYLES 
    : STYLES.filter(s => s.tag === activeCategory);

  return (
    <div className="max-w-7xl mx-auto px-6 py-12 md:py-20">
      <div className="text-center mb-16">
        <h1 className="text-4xl md:text-5xl font-serif text-primary mb-6 flex items-center justify-center gap-3">
           <Palette className="w-8 h-8 text-gold" /> 传统文化视觉风格库
        </h1>
        <p className="text-lg text-ink/70 max-w-2xl mx-auto leading-relaxed">
          平台围绕民间工艺、传统绘画与器物装饰等视觉门类，整理色彩、构图和纹样参考，为主题创作与生成提示词提供风格选择。
        </p>
      </div>

      {/* Filter Row */}
      <div className="flex flex-wrap items-center justify-center gap-3 mb-12">
        <Filter className="w-5 h-5 text-ink/40 mr-2" />
        {CATEGORIES.map(category => (
          <button
            key={category}
            onClick={() => setActiveCategory(category)}
            className={cn(
              "px-5 py-2 rounded-full text-sm font-medium transition-all duration-300",
              activeCategory === category 
                ? "bg-primary text-white shadow-md" 
                : "bg-white border border-primary/20 text-ink/70 hover:border-primary hover:text-primary"
            )}
          >
            {category}
          </button>
        ))}
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 md:gap-10 mb-20">
        <AnimatePresence mode="popLayout">
          {filteredStyles.map((style, i) => (
            <motion.div 
              layout
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.4 }}
              key={style.id} 
              className={cn(
                "group bg-rice-paper rounded-2xl overflow-hidden shadow-sm border transition-all duration-300 cursor-pointer",
                hoveredStyle === style.id ? "shadow-[0_10px_30px_rgba(158,36,27,0.15)] border-primary/50 -translate-y-2" : "border-border-red/10 hover:border-primary/30"
              )}
              onMouseEnter={() => setHoveredStyle(style.id)}
              onMouseLeave={() => setHoveredStyle(null)}
            >
              <div className="aspect-[4/3] relative overflow-hidden bg-black">
                <img 
                  src={style.img || '/zhuxianzhen.png'} 
                  alt={style.name} 
                  className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105 opacity-90 group-hover:opacity-100"
                />
                <div className="absolute inset-0 border-[6px] border-white/10 pointer-events-none z-10 m-2 rounded-lg"></div>
                <div className="absolute top-4 left-4 flex gap-2 z-20">
                  {style.tags.map(tag => (
                    <span key={tag} className="px-2.5 py-1 text-xs font-medium bg-black/40 backdrop-blur-md text-white rounded shadow-sm border border-white/20">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
              
              <div className="p-6 relative">
                {/* Decorative corner */}
                <div className="absolute top-0 right-0 w-12 h-12 bg-primary/5 rounded-bl-[40px] -z-10"></div>
                
                <h3 className="text-xl font-serif font-bold text-ink mb-3 group-hover:text-primary transition-colors flex items-center justify-between">
                  {style.name}
                  <Link to={`/creator?style=${style.id}`} className="text-sm font-sans font-medium text-primary bg-primary/10 px-3 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                    开始创作 <ArrowRight className="w-3 h-3" />
                  </Link>
                </h3>
                <div className="mb-2">
                  <span className="inline-flex px-2 py-1 text-xs text-primary bg-primary/5 border border-primary/10 rounded">{style.categoryLabel}</span>
                </div>
                <p className="text-sm text-ink/70 leading-relaxed mb-4 min-h-[60px]">
                  {style.desc}
                </p>
                
                <div className="pt-4 border-t border-primary/10 flex items-start gap-2">
                   <Info className="w-4 h-4 text-gold shrink-0 mt-0.5" />
                   <p className="text-xs text-ink/60 leading-relaxed">
                     <span className="font-medium text-ink/80">应用参考：</span>
                     {style.scene}
                   </p>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-primary/10 p-8 md:p-12 mb-16 relative overflow-hidden">
        <div className="absolute right-0 top-0 w-1/3 h-full bg-gradient-to-l from-primary/5 to-transparent pointer-events-none"></div>
        <h2 className="text-2xl font-serif text-primary mb-8 flex items-center gap-3">
          <ImageIcon className="w-6 h-6 text-gold" />
          创作方向指引
        </h2>
        <div className="grid md:grid-cols-3 gap-6">
          <div className="p-5 bg-rice-paper rounded-xl border border-primary/5 hover:shadow-md transition-shadow">
             <div className="text-gold font-serif text-lg font-bold mb-2">01. 按视觉特征选风格</div>
             <p className="text-sm text-ink/70 leading-relaxed">年画与剪纸可提供更鲜明的红色对比参考；汴绣与青花可用于细密纹样和蓝白装饰方向。生成效果仍受模型输出影响。</p>
          </div>
          <div className="p-5 bg-rice-paper rounded-xl border border-primary/5 hover:shadow-md transition-shadow">
             <div className="text-gold font-serif text-lg font-bold mb-2">02. 调整风格提示强度</div>
             <p className="text-sm text-ink/70 leading-relaxed">工作台会将滑杆值转换为轻、中、强三档风格描述并加入提示词；它不控制姿态、结构网络，也不保证精确复现参考风格。</p>
          </div>
          <div className="p-5 bg-rice-paper rounded-xl border border-primary/5 hover:shadow-md transition-shadow">
             <div className="text-gold font-serif text-lg font-bold mb-2">03. 补充具体创作描述</div>
             <p className="text-sm text-ink/70 leading-relaxed">在主题中写明色彩、纹样、主体和画面方向，有助于形成更明确的生成提示。当前说明卡来自本地预设条目，不包含外部知识检索或 AI 考证。</p>
          </div>
        </div>
      </div>

      <div className="text-center">
        <Link
          to="/creator"
          className="inline-flex items-center gap-2 px-8 py-4 btn-chinese text-lg font-medium shadow-lg hover:-translate-y-1"
        >
          前往工作台开始创作
          <ArrowRight className="w-5 h-5" />
        </Link>
      </div>
    </div>
  );
}
