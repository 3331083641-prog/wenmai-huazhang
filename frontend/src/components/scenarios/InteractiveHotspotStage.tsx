import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { Search, Scroll, Move3d, ArrowRight, Eye, Sparkles } from 'lucide-react';

interface Hotspot {
  id: string;
  x: number; // percentage
  y: number; // percentage
  title: string;
  category: string;
  desc: string;
}

const HOTSPOTS: Hotspot[] = [
  {
    id: 'spot-1',
    x: 48,
    y: 28,
    title: '额顶云冠与童子开脸',
    category: '造型美学',
    desc: '面如满月，双目微合含笑。采用传统木版水印技法，朱砂点唇，彰显中原民间版画敦厚淳朴的祈福神采。',
  },
  {
    id: 'spot-2',
    x: 35,
    y: 65,
    title: '抱鲤献瑞与黑道墨线',
    category: '刀法技艺',
    desc: '刀法遒劲挺拔，黑线顿挫分明。肥硕红鲤跃然而出，线条刚劲沉稳，体现朱仙镇年画独特的刻版骨法。',
  },
  {
    id: 'spot-3',
    x: 72,
    y: 52,
    title: '传统矿物天然套印',
    category: '设色谱系',
    desc: '以槐米煮黄、红花熬色、苏木染赤。五色互衬，浓艳沉着，久经岁月风霜而不褪色。',
  },
];

const MODES = [
  { id: 'hotspots', label: '画中有话 · 热点', icon: Search, badge: '微观热点视觉解读' },
  { id: 'scroll', label: '一图一境 · 长卷', icon: Scroll, badge: '三折图文阅读长卷' },
  { id: 'parallax', label: '画境漫游 · 2.5D', icon: Move3d, badge: '2.5D 深度视差漫游' },
];

export function InteractiveHotspotStage() {
  const [activeMode, setActiveMode] = useState<string>('hotspots');
  const [activeHotspot, setActiveHotspot] = useState<Hotspot>(HOTSPOTS[0]);
  const [tiltOffset, setTiltOffset] = useState({ x: 0, y: 0 });

  const handleParallaxMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (activeMode !== 'parallax') return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    setTiltOffset({ x: x * 24, y: y * 24 });
  };

  return (
    <div className="flex flex-col h-full bg-[#161210] text-white/90 rounded-2xl sm:rounded-3xl border border-gold/30 shadow-2xl overflow-hidden font-sans">
      {/* ── 顶部交互模式切换 ──────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 sm:px-6 py-3 border-b border-white/10 bg-[#221A16]/90 backdrop-blur-md">
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-black/50 border border-white/10">
          {MODES.map((mode) => {
            const active = mode.id === activeMode;
            const Icon = mode.icon;
            return (
              <button
                key={mode.id}
                type="button"
                onClick={() => setActiveMode(mode.id)}
                className={`relative px-3 py-1.5 rounded-lg text-xs font-serif transition-all flex items-center gap-1.5 cursor-pointer ${
                  active ? 'text-ink font-bold shadow-xs' : 'text-white/70 hover:text-white'
                }`}
              >
                {active && (
                  <motion.div
                    layoutId="hotspot-mode-pill"
                    className="absolute inset-0 bg-white rounded-lg"
                    transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                  />
                )}
                <span className="relative z-10 flex items-center gap-1.5">
                  <Icon className="w-3.5 h-3.5" />
                  {mode.label}
                </span>
              </button>
            );
          })}
        </div>
        <span className="text-[11px] font-serif tracking-wider text-gold/90 hidden sm:inline-block">
          {MODES.find((m) => m.id === activeMode)?.badge}
        </span>
      </div>

      {/* ── 主舞台区域 ────────────────────────────────────────── */}
      <div
        className="relative flex-1 min-h-[320px] sm:min-h-[380px] overflow-hidden flex items-center justify-center p-4 sm:p-6"
        onMouseMove={handleParallaxMove}
        onMouseLeave={() => setTiltOffset({ x: 0, y: 0 })}
      >
        {/* MODE 1: 微观热点探索 */}
        {activeMode === 'hotspots' && (
          <div className="relative w-full max-w-[340px] sm:max-w-[380px] aspect-[4/5] rounded-2xl overflow-hidden border border-white/20 shadow-2xl bg-[#261E1A]">
            <img
              src="/zhuxianzhen.png"
              alt="朱仙镇年画瑞猫图"
              className="w-full h-full object-cover select-none"
            />

            {/* 3 个脉冲式互动热点标记 */}
            {HOTSPOTS.map((spot, idx) => {
              const isSelected = spot.id === activeHotspot.id;
              return (
                <button
                  key={spot.id}
                  type="button"
                  onClick={() => setActiveHotspot(spot)}
                  onMouseEnter={() => setActiveHotspot(spot)}
                  style={{ left: `${spot.x}%`, top: `${spot.y}%` }}
                  aria-label={spot.title}
                  className="group absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer z-30 focus:outline-none"
                >
                  <span className="relative flex h-8 w-8 items-center justify-center">
                    <span
                      className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-60 ${
                        isSelected ? 'bg-gold' : 'bg-primary'
                      }`}
                    />
                    <span
                      className={`relative inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-serif font-bold text-white shadow-md border ${
                        isSelected
                          ? 'bg-gold text-[#1F1710] border-white scale-110'
                          : 'bg-primary border-gold/60 group-hover:scale-105'
                      } transition-all`}
                    >
                      0{idx + 1}
                    </span>
                  </span>
                </button>
              );
            })}

            {/* 悬浮微观解读卡 */}
            <AnimatePresence mode="wait">
              <motion.div
                key={activeHotspot.id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                transition={{ duration: 0.25 }}
                className="absolute bottom-3 inset-x-3 p-3.5 rounded-xl bg-black/80 backdrop-blur-md border border-gold/40 text-left z-40 shadow-xl"
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <div className="flex items-center gap-1.5">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-serif bg-gold text-[#1F1710] font-bold">
                      {activeHotspot.category}
                    </span>
                    <h5 className="font-serif font-bold text-xs text-white">
                      {activeHotspot.title}
                    </h5>
                  </div>
                  <span className="text-[10px] text-white/40 font-mono">点击热点探索</span>
                </div>
                <p className="text-[11px] leading-relaxed text-white/80 line-clamp-2">
                  {activeHotspot.desc}
                </p>
              </motion.div>
            </AnimatePresence>
          </div>
        )}

        {/* MODE 2: 一图一境 · 三折叙事长卷 */}
        {activeMode === 'scroll' && (
          <div className="w-full max-w-lg space-y-2.5">
            {[
              {
                fold: '折一',
                title: '起 · 寻脉探源',
                tag: '北宋古意',
                desc: '深入溯源开封朱仙镇木版年画源流，以粗犷质朴的黑道骨线锚定东方视觉基因。',
                pic: '/zhuxianzhen.png',
              },
              {
                fold: '折二',
                title: '承 · 考工知物',
                tag: '五彩套印',
                desc: '三矾九染与传统套印分色，考究矿物颜料设色法则，提炼结构化美育解析模型。',
                pic: '/songhua.png',
              },
              {
                fold: '折三',
                title: '转 · 现代活化',
                tag: '意境衍生',
                desc: '融入现代文创衍生品打样与 3D 沉浸式数字展陈，实现从静态观赏到多维共创。',
                pic: '/bianxiu.png',
              },
            ].map((card, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1, duration: 0.4 }}
                className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10 hover:border-gold/40 hover:bg-white/10 transition-all text-left group"
              >
                <div className="w-12 h-12 rounded-lg overflow-hidden shrink-0 border border-white/20">
                  <img src={card.pic} alt="" className="w-full h-full object-cover" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="font-serif text-xs font-bold text-gold">{card.fold}</span>
                    <span className="font-serif text-xs font-bold text-white">{card.title}</span>
                    <span className="px-1.5 py-0.2 rounded text-[10px] bg-white/10 text-white/60">
                      {card.tag}
                    </span>
                  </div>
                  <p className="text-[11px] leading-relaxed text-white/60 truncate group-hover:text-white/80 transition-colors">
                    {card.desc}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* MODE 3: 画境漫游 · 2.5D 深度视差 */}
        {activeMode === 'parallax' && (
          <div className="relative w-full max-w-md aspect-[16/10] rounded-2xl overflow-hidden border border-gold/40 bg-[#1F1713] flex items-center justify-center shadow-2xl cursor-grab">
            {/* 远景背景层 */}
            <motion.div
              className="absolute inset-0 scale-110"
              style={{
                x: tiltOffset.x * 0.25,
                y: tiltOffset.y * 0.25,
              }}
            >
              <img
                src="/scenarios/heritage-dusk.jpg"
                alt=""
                className="w-full h-full object-cover filter brightness-75 blur-[1px]"
              />
            </motion.div>

            {/* 中景画作层 */}
            <motion.div
              className="relative z-10 w-44 sm:w-52 aspect-[3/4] rounded-xl overflow-hidden border-2 border-gold shadow-[0_20px_50px_rgba(0,0,0,0.8)]"
              style={{
                x: tiltOffset.x * 0.75,
                y: tiltOffset.y * 0.75,
              }}
            >
              <img src="/songhua.png" alt="" className="w-full h-full object-cover" />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
              <span className="absolute bottom-2 left-2 text-[10px] font-serif text-white bg-black/60 px-2 py-0.5 rounded">
                千里江山 · 分层入画
              </span>
            </motion.div>

            {/* 前景悬浮提示徽标 */}
            <motion.div
              className="absolute bottom-3 inset-x-3 z-20 flex items-center justify-between p-2.5 rounded-xl bg-black/75 backdrop-blur-md border border-white/15 text-xs text-white"
              style={{
                x: tiltOffset.x * 1.1,
                y: tiltOffset.y * 1.1,
              }}
            >
              <div className="flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-gold animate-spin" />
                <span className="text-[11px] font-serif">移动指针体验 2.5D 视差推镜</span>
              </div>
              <span className="text-[10px] text-gold font-mono">Three.js Depth</span>
            </motion.div>
          </div>
        )}
      </div>

      {/* ── 底部快捷直达 ─────────────────────────────────────── */}
      <div className="px-4 sm:px-6 py-3 border-t border-white/10 bg-[#201915] flex items-center justify-between">
        <span className="text-[11px] text-white/50 font-serif">
          已收录 5 件经典传统文化作品深度交互解读
        </span>
        <Link
          to="/experience/zhuxianzhen-ruimao"
          className="inline-flex items-center gap-1.5 text-xs font-serif text-gold hover:text-white transition-colors"
        >
          <span>深度赏析《朱仙镇年画》</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}
