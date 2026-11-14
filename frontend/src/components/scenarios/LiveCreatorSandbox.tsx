import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { Sparkles, SlidersHorizontal, ShieldCheck, ArrowRight, CheckCircle2 } from 'lucide-react';

interface StylePreset {
  id: string;
  name: string;
  tag: string;
  prompt: string;
  image: string;
  hash: string;
  accent: string;
  swatches: string[];
}

const STYLES: StylePreset[] = [
  {
    id: 'zhuxianzhen',
    name: '朱仙镇年画',
    tag: '版刻设色',
    prompt: '五子闹钟馗瑞兽图，粗犷质朴的黑道墨线，朱砂大红与槐黄矿物设色，门神神韵与民间吉庆氛围',
    image: '/zhuxianzhen.png',
    hash: 'sha256:7b9c3f1e...4a20d1',
    accent: '#9E241B',
    swatches: ['#A0241A', '#DF9B34', '#3E5C46', '#221915'],
  },
  {
    id: 'songhua',
    name: '宋画青绿',
    tag: '工笔重彩',
    prompt: '千里江山层峦叠嶂，三矾九染石青石绿，细密水纹与宋代文人高古气韵，绢本设色光泽',
    image: '/songhua.png',
    hash: 'sha256:3d8a92f0...c4e18b',
    accent: '#2A685D',
    swatches: ['#235C52', '#3D8271', '#C6A363', '#41352A'],
  },
  {
    id: 'bianxiu',
    name: '开封汴绣',
    tag: '丝光针法',
    prompt: '牡丹锦鸡双面绣长卷，滚针打籽与乱针绣工艺，真丝劈丝光泽，平齐顺畅的丝织经纬质感',
    image: '/bianxiu.png',
    hash: 'sha256:9f4e22c8...58d30e',
    accent: '#A8483B',
    swatches: ['#A8483B', '#DB9E79', '#5B7E6F', '#FAF2E6'],
  },
  {
    id: 'qinghua',
    name: '青花瓷纹样',
    tag: '釉里苏麻离青',
    prompt: '永乐宣德青花缠枝莲纹，苏麻离青料自然铁锈斑锡光，白釉肥腴泛青，浑厚苍翠的钴蓝渲染',
    image: '/qinghua.png',
    hash: 'sha256:1a5c88b4...f99017',
    accent: '#1E4B82',
    swatches: ['#1B4375', '#3A6BA5', '#9BBEDB', '#E8EEF5'],
  },
  {
    id: 'jianzhi',
    name: '中国剪纸',
    tag: '镂空光影',
    prompt: '北方民间喜庆窗花，月牙纹与锯齿纹精密剪刻，阴阳相济的镂空虚实构图，纯正宣纸红韵',
    image: '/jianzhi.png',
    hash: 'sha256:6e0d4a99...3b7c42',
    accent: '#B82E22',
    swatches: ['#B82E22', '#D34433', '#E8B67D', '#FFFFFF'],
  },
];

export function LiveCreatorSandbox() {
  const [selectedStyle, setSelectedStyle] = useState<StylePreset>(STYLES[0]);
  const [strength, setStrength] = useState<number>(80);

  return (
    <div className="flex flex-col h-full bg-[#1A1614] text-white/90 rounded-2xl sm:rounded-3xl border border-gold/30 shadow-2xl overflow-hidden font-sans">
      {/* ── 顶部控制台标题条 ─────────────────────────────── */}
      <div className="flex items-center justify-between px-4 sm:px-6 py-3 border-b border-white/10 bg-[#241E1A]/80 backdrop-blur-md">
        <div className="flex items-center gap-2.5">
          <span className="flex h-2.5 w-2.5 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
          <span className="font-serif text-xs sm:text-sm tracking-wide text-white/90 font-medium">
            Qwen 3.0 美学底座 · 多模态可控生成工作台
          </span>
        </div>
        <div className="hidden sm:flex items-center gap-2 text-[11px] text-white/50 font-mono">
          <span>Seed #829410</span>
          <span>·</span>
          <span>28 Steps</span>
        </div>
      </div>

      {/* ── 主体工作台区域：左侧预览，右侧参数控制器 ───────────── */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-0 flex-1">
        {/* 左侧成图画布 */}
        <div className="md:col-span-7 relative min-h-[260px] sm:min-h-[340px] flex items-center justify-center p-4 sm:p-6 bg-radial from-[#2C241F] to-[#120E0D] overflow-hidden">
          {/* 背景精细方格标尺 */}
          <div
            className="absolute inset-0 opacity-[0.06] pointer-events-none"
            style={{
              backgroundImage:
                'linear-gradient(to right, white 1px, transparent 1px), linear-gradient(to bottom, white 1px, transparent 1px)',
              backgroundSize: '24px 24px',
            }}
          />

          {/* 实时艺术图层展示 */}
          <div className="relative w-full max-w-[280px] sm:max-w-[320px] aspect-square rounded-2xl overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.6)] border border-white/15 group">
            <AnimatePresence mode="wait">
              <motion.img
                key={selectedStyle.id}
                src={selectedStyle.image}
                alt={selectedStyle.name}
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 1.04 }}
                transition={{ duration: 0.45, ease: 'easeOut' }}
                className="w-full h-full object-cover"
              />
            </AnimatePresence>

            {/* 浮动画质与风格标签 */}
            <div className="absolute top-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-black/70 backdrop-blur-md text-[11px] border border-white/15 text-white/95">
              <Sparkles className="w-3 h-3 text-gold" />
              <span>{selectedStyle.name}</span>
              <span className="text-white/40">·</span>
              <span className="text-gold">{selectedStyle.tag}</span>
            </div>

            {/* 底部色卡指示 */}
            <div className="absolute bottom-3 right-3 flex items-center gap-1 p-1 rounded-full bg-black/60 backdrop-blur-md border border-white/10">
              {selectedStyle.swatches.map((color, idx) => (
                <span
                  key={idx}
                  className="w-3 h-3 rounded-full border border-white/30"
                  style={{ backgroundColor: color }}
                  title={color}
                />
              ))}
            </div>
          </div>
        </div>

        {/* 右侧交互控制器面板 */}
        <div className="md:col-span-5 p-4 sm:p-5 flex flex-col justify-between bg-[#201A17]/90 border-t md:border-t-0 md:border-l border-white/10">
          <div>
            {/* 1. 五大流派切换按钮组 */}
            <div className="mb-4">
              <label className="text-[11px] tracking-wider uppercase text-gold/80 font-mono block mb-2 font-medium">
                1. 传统文化基因注入
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
                {STYLES.map((st) => {
                  const active = st.id === selectedStyle.id;
                  return (
                    <button
                      key={st.id}
                      type="button"
                      onClick={() => setSelectedStyle(st)}
                      className={`px-2.5 py-2 rounded-xl text-xs font-serif text-left transition-all cursor-pointer border ${
                        active
                          ? 'bg-primary text-white border-gold/70 shadow-sm'
                          : 'bg-white/5 text-white/70 border-white/10 hover:bg-white/10 hover:text-white'
                      }`}
                    >
                      <div className="font-bold flex items-center justify-between">
                        <span>{st.name}</span>
                        {active && <CheckCircle2 className="w-3 h-3 text-gold" />}
                      </div>
                      <span className="text-[10px] opacity-70 block">{st.tag}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 2. 风格强度滑块 */}
            <div className="mb-4 p-3 rounded-xl bg-white/5 border border-white/10">
              <div className="flex items-center justify-between text-xs mb-2">
                <span className="flex items-center gap-1.5 text-white/80 font-serif">
                  <SlidersHorizontal className="w-3.5 h-3.5 text-gold" />
                  风格影响权重
                </span>
                <span className="font-mono text-gold font-bold">{strength}%</span>
              </div>
              <input
                type="range"
                min="10"
                max="100"
                value={strength}
                onChange={(e) => setStrength(Number(e.target.value))}
                className="w-full accent-primary h-1.5 bg-white/20 rounded-lg cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-white/40 mt-1 font-mono">
                <span>自由构图 10%</span>
                <span>平衡 50%</span>
                <span>纯正传统 100%</span>
              </div>
            </div>

            {/* 3. 动态提示词解析 */}
            <div className="mb-3 text-[11px] leading-relaxed text-white/60 p-2.5 rounded-lg bg-black/40 border border-white/5 font-mono line-clamp-2">
              <span className="text-gold/90 font-bold">PROMPT: </span>
              {selectedStyle.prompt}
            </div>
          </div>

          {/* 底部存证与直达入口 */}
          <div className="pt-3 border-t border-white/10 flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 text-[11px] text-white/50 font-mono">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>{selectedStyle.hash}</span>
            </div>
            <Link
              to="/creator"
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-gold text-[#1F1710] font-serif text-xs font-bold hover:bg-gold/90 transition-colors shrink-0"
            >
              <span>进入创作</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
