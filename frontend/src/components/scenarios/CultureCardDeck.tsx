import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { FileText, Palette, Scissors, ArrowRight, CheckCircle2, ZoomIn } from 'lucide-react';

interface CardOption {
  id: string;
  name: string;
  tag: string;
  src: string;
  alt: string;
  ratio: 'portrait' | 'landscape';
  points: string[];
}

const CARDS: CardOption[] = [
  {
    id: 'songhua-card',
    name: '宋画青绿研学卡',
    tag: '工笔重彩设色',
    src: '/scenarios/culture-card-songhua.png',
    alt: '宋画青绿山水美育研学知识卡：构图、设色与工艺要点',
    ratio: 'portrait',
    points: ['三矾九染矿物设色', '高古远景山峦水纹', '馆藏考证结构化归档'],
  },
  {
    id: 'bianxiu-card',
    name: '开封汴绣工艺卡',
    tag: '非遗丝光针法',
    src: '/scenarios/culture-card-bianxiu.png',
    alt: '开封汴绣双面绣研学卡：滚针、乱针与真丝丝光',
    ratio: 'portrait',
    points: ['平齐顺畅真丝针法', '双面异色绣艺解构', '工美大匠针谱还原'],
  },
  {
    id: 'embroidery-product',
    name: '宋韵真丝衍生实物',
    tag: '实物工艺打样',
    src: '/scenarios/product-embroidery-lifestyle.jpg',
    alt: '宋代汴绣真丝团扇与长巾实物生活美学实拍',
    ratio: 'landscape',
    points: ['非遗手作打样标准', '真丝双面绣透光测试', '当代雅致生活融入'],
  },
];

export function CultureCardDeck() {
  const [selectedCard, setSelectedCard] = useState<CardOption>(CARDS[0]);

  return (
    <div className="flex flex-col h-full bg-[#FAF7F2] text-ink rounded-2xl sm:rounded-3xl border border-gold/35 shadow-xl overflow-hidden font-sans">
      {/* ── 顶部切换导航 ──────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 sm:px-6 py-3 border-b border-primary/10 bg-white/70 backdrop-blur-md">
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-primary/5 border border-primary/10">
          {CARDS.map((item) => {
            const active = item.id === selectedCard.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setSelectedCard(item)}
                className={`relative px-3 py-1.5 rounded-lg text-xs font-serif transition-all cursor-pointer ${
                  active ? 'text-primary font-bold shadow-xs' : 'text-ink/70 hover:text-primary'
                }`}
              >
                {active && (
                  <motion.div
                    layoutId="culture-card-pill"
                    className="absolute inset-0 bg-white rounded-lg border border-primary/15"
                    transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                  />
                )}
                <span className="relative z-10">{item.name}</span>
              </button>
            );
          })}
        </div>
        <span className="text-[11px] font-serif text-primary/80 font-medium hidden sm:inline-block">
          {selectedCard.tag}
        </span>
      </div>

      {/* ── 主体展示台 ────────────────────────────────────── */}
      <div className="relative flex-1 min-h-[340px] sm:min-h-[400px] p-4 sm:p-6 flex items-center justify-center bg-radial from-[#FFFDF9] to-[#F5ECE0] overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.div
            key={selectedCard.id}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.05 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
            className={`relative rounded-xl overflow-hidden shadow-2xl border border-gold/40 bg-white group ${
              selectedCard.ratio === 'portrait'
                ? 'w-full max-w-[280px] sm:max-w-[310px] aspect-[3/4]'
                : 'w-full max-w-[460px] aspect-[16/10]'
            }`}
          >
            <img
              src={selectedCard.src}
              alt={selectedCard.alt}
              className="w-full h-full object-cover select-none group-hover:scale-105 transition-transform duration-700"
            />

            {/* 底部浮动亮点解读条 */}
            <div className="absolute inset-x-0 bottom-0 p-3 bg-gradient-to-t from-black/80 via-black/40 to-transparent text-white text-xs">
              <div className="flex flex-wrap gap-1.5">
                {selectedCard.points.map((pt, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 text-[10px] font-serif bg-white/15 backdrop-blur-md px-2 py-0.5 rounded-full border border-white/20"
                  >
                    <CheckCircle2 className="w-2.5 h-2.5 text-gold" />
                    {pt}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* ── 底部行动引导 ──────────────────────────────────── */}
      <div className="px-4 sm:px-6 py-3 border-t border-primary/10 bg-white/60 flex items-center justify-between">
        <span className="text-[11px] text-ink/60 font-serif">
          五大传统文化风格教学课件与非遗知识图谱
        </span>
        <Link
          to="/styles"
          className="inline-flex items-center gap-1.5 text-xs font-serif text-primary hover:text-primary-dark font-medium transition-colors"
        >
          <span>查阅风格知识库</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}
