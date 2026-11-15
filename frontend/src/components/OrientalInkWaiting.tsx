import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ImagePlus, AlertCircle, RefreshCw, Sparkles } from 'lucide-react';

interface OrientalInkWaitingProps {
  isGenerating: boolean;
  hasResult: boolean;
  imageLoadState: 'idle' | 'loading' | 'loaded' | 'error';
  connectionNotice: string | null;
  errorMessage?: string | null;
  onRetry?: () => void;
  selectedStyleName?: string;
}

/**
 * 东方数智创作的三重自然意境阶段（不伪造百分比，采用周期性自然诗意循环）
 */
const POETIC_PHASES = [
  {
    stage: '壹',
    title: '研墨理绪',
    desc: '解析文化语义，凝练传统意象先验',
    accent: '#9E241B',
  },
  {
    stage: '贰',
    title: '引纹入脉',
    desc: '熔铸非遗构图法则，织就传统骨骼脉络',
    accent: '#D2A14A',
  },
  {
    stage: '叁',
    title: '丹青聚境',
    desc: '调和五彩矿物色阶，点染数字生宣华章',
    accent: '#2B5F75',
  },
];

export default function OrientalInkWaiting({
  isGenerating,
  hasResult,
  imageLoadState,
  connectionNotice,
  errorMessage,
  onRetry,
  selectedStyleName = '传统文化风格',
}: OrientalInkWaitingProps) {
  const [phaseIndex, setPhaseIndex] = useState(0);

  // 自然呼吸式意境更迭（每 3.8 秒舒缓切换，绝不显示虚假进度条与百分比）
  useEffect(() => {
    if (!isGenerating) {
      setPhaseIndex(0);
      return;
    }
    const timer = setInterval(() => {
      setPhaseIndex((prev) => (prev + 1) % POETIC_PHASES.length);
    }, 3800);
    return () => clearInterval(timer);
  }, [isGenerating]);

  const currentPhase = POETIC_PHASES[phaseIndex];

  // 1. 错误或服务异常状态
  if (connectionNotice || errorMessage) {
    return (
      <div className="w-full max-w-sm aspect-[3/4] border-2 border-primary/30 rounded-2xl bg-[#FFF9F7] p-8 text-center flex flex-col items-center justify-center shadow-sm relative overflow-hidden">
        <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/25 flex items-center justify-center text-primary mb-4 shadow-xs">
          <AlertCircle className="w-7 h-7" />
        </div>
        <span className="chinese-seal text-[10px] mb-2">服务提示</span>
        <h4 className="font-serif font-bold text-base text-ink mb-2">
          {connectionNotice ? '创作服务连接提示' : '作品生成遇到阻碍'}
        </h4>
        <p className="text-xs text-ink/70 leading-relaxed max-w-[260px] font-sans mb-5">
          {connectionNotice || errorMessage || '服务暂未响应，请检查网络配置或重试。'}
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="px-4 py-2 rounded-xl btn-chinese text-xs font-serif flex items-center gap-1.5 shadow-xs hover:shadow-md transition-all cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5 text-gold" />
            <span>重新尝试</span>
          </button>
        )}
      </div>
    );
  }

  // 2. 正在生成中（正在笔墨生辉 · 纯 CSS/SVG/Motion 墨韵水墨扩散动画）
  if (isGenerating) {
    return (
      <div className="w-full max-w-sm aspect-[3/4] border border-gold/40 rounded-2xl bg-[#FAF5EC] p-8 text-center flex flex-col items-center justify-between shadow-[0_16px_40px_rgba(63,43,31,0.06)] relative overflow-hidden">
        {/* 背景柔和宣纸晕染 */}
        <div className="absolute inset-0 bg-gradient-to-b from-gold/5 via-transparent to-primary/5 pointer-events-none" />

        {/* 顶部状态标识 */}
        <div className="relative z-10 flex items-center gap-2">
          <span className="chinese-seal text-[9px] bg-primary">丹青</span>
          <span className="text-xs font-serif text-ink/75 tracking-wider">
            正在凝练「{selectedStyleName}」意境
          </span>
        </div>

        {/* 核心动效：传统云纹印圈与水墨晕染绽放 */}
        <div className="relative w-56 h-56 flex items-center justify-center my-auto">
          {/* 外层多重水墨晕染扩散脉冲 */}
          <motion.div
            className="absolute inset-0 rounded-full bg-primary/10 blur-xl"
            animate={{
              scale: [0.85, 1.25, 0.95],
              opacity: [0.2, 0.45, 0.25],
            }}
            transition={{
              duration: 4.2,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
          <motion.div
            className="absolute inset-2 rounded-full bg-gold/15 blur-lg"
            animate={{
              scale: [1.1, 0.9, 1.15],
              opacity: [0.3, 0.6, 0.35],
            }}
            transition={{
              duration: 3.6,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />

          {/* 真实敦煌飞天与水墨流云绽放精灵（GPT Image 2 无损透明素材） */}
          <motion.div
            className="absolute inset-0 flex items-center justify-center pointer-events-none z-0"
            animate={{ rotate: 360, scale: [0.94, 1.05, 0.94] }}
            transition={{
              rotate: { duration: 36, repeat: Infinity, ease: 'linear' },
              scale: { duration: 5, repeat: Infinity, ease: 'easeInOut' },
            }}
          >
            <picture>
              <source
                type="image/webp"
                srcSet={import.meta.env.BASE_URL + "visuals/vnext/ui-img-05-ink-bloom-sprite.webp"}
              />
              <img
                src={import.meta.env.BASE_URL + "visuals/vnext/ui-img-05-ink-bloom-sprite.png"}
                alt="水墨流云绽放"
                className="w-48 h-48 object-contain drop-shadow-[0_10px_25px_rgba(210,161,74,0.35)]"
              />
            </picture>
          </motion.div>

          {/* SVG 传统祥云回纹环，带有顺时针漫步与虚线描边呼吸 */}
          <svg className="w-52 h-52 absolute z-10 pointer-events-none" viewBox="0 0 100 100">
            {/* 外圈金丝回纹 */}
            <motion.circle
              cx="50"
              cy="50"
              r="46"
              fill="none"
              stroke="#D2A14A"
              strokeWidth="1"
              strokeDasharray="4 6"
              animate={{ rotate: 360 }}
              transition={{ duration: 24, repeat: Infinity, ease: 'linear' }}
              style={{ originX: '50px', originY: '50px' }}
            />
            {/* 中圈朱砂脉络环 */}
            <motion.circle
              cx="50"
              cy="50"
              r="34"
              fill="none"
              stroke="#9E241B"
              strokeWidth="0.8"
              strokeDasharray="8 4 2 4"
              animate={{ rotate: -360 }}
              transition={{ duration: 18, repeat: Infinity, ease: 'linear' }}
              style={{ originX: '50px', originY: '50px' }}
            />
          </svg>

          {/* 中央文房笔锋与朱砂印徽 */}
          <motion.div
            className="relative z-20 w-16 h-16 rounded-2xl bg-white/95 border border-gold/50 shadow-md flex flex-col items-center justify-center p-2 backdrop-blur-md"
            animate={{
              scale: [0.96, 1.04, 0.96],
            }}
            transition={{
              duration: 2.8,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          >
            <Sparkles className="w-6 h-6 text-gold mb-0.5 animate-pulse" />
            <span className="text-[9px] font-serif text-primary font-bold">运笔中</span>
          </motion.div>
        </div>

        {/* 底部自然诗意意境阶段切换（真实无虚伪数字） */}
        <div className="relative z-10 w-full min-h-[64px] flex flex-col items-center justify-center">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentPhase.stage}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.4 }}
              className="flex flex-col items-center text-center"
            >
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-[10px] font-serif px-1.5 py-0.2 rounded bg-gold/20 text-ink/80">
                  卷{currentPhase.stage}
                </span>
                <span className="text-sm font-serif font-bold text-ink">
                  {currentPhase.title}
                </span>
              </div>
              <p className="text-[11px] text-ink/65 font-sans leading-relaxed">
                {currentPhase.desc}
              </p>
            </motion.div>
          </AnimatePresence>
          <p className="text-[9px] text-ink/40 font-serif mt-2 tracking-wider">
            画面为创作等待动效，非实时生成进度
          </p>
        </div>
      </div>
    );
  }

  // 3. 成图已出，高清晰度图片正在网络加载中（轻纱揭幕）
  if (hasResult && imageLoadState === 'loading') {
    return (
      <div className="w-full max-w-sm aspect-[3/4] border border-gold/40 rounded-2xl bg-[#FAF5EC] p-8 text-center flex flex-col items-center justify-center shadow-sm relative overflow-hidden">
        <motion.div
          className="w-16 h-16 rounded-full border-2 border-dashed border-gold flex items-center justify-center text-gold mb-4"
          animate={{ rotate: 360 }}
          transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
        >
          <Sparkles className="w-8 h-8 text-primary" />
        </motion.div>
        <span className="chinese-seal text-[10px] mb-2">轻纱揭幕</span>
        <h4 className="font-serif font-bold text-base text-ink mb-1">
          华章已就 · 正在高清装裱
        </h4>
        <p className="text-xs text-ink/60 font-sans max-w-[220px]">
          渲染管线已完成，正在自展陈网络调入全彩数字生宣画幅...
        </p>
      </div>
    );
  }

  // 4. 默认静息状态（画案待题 · 传统素绢空间）
  return (
    <div className="w-full max-w-sm aspect-[3/4] border-2 border-dashed border-gold/45 rounded-2xl bg-white/60 flex flex-col items-center justify-center p-8 text-center relative overflow-hidden group shadow-sm">
      <div className="absolute inset-0 bg-gradient-to-t from-gold/10 via-transparent to-transparent pointer-events-none" />
      <picture>
        <source
          type="image/webp"
          srcSet={import.meta.env.BASE_URL + "visuals/vnext/ui-img-05-ink-bloom-sprite.webp"}
        />
        <img
          src={import.meta.env.BASE_URL + "visuals/vnext/ui-img-05-ink-bloom-sprite.png"}
          alt=""
          className="absolute w-64 h-64 object-contain opacity-15 pointer-events-none group-hover:scale-105 group-hover:opacity-25 transition-all duration-700"
        />
      </picture>
      <div className="w-16 h-16 rounded-2xl bg-white shadow-xs border border-gold/40 flex items-center justify-center mb-4 text-gold group-hover:scale-105 group-hover:text-primary transition-all relative z-10">
        <ImagePlus className="w-8 h-8 text-primary/60" />
      </div>
      <h3 className="font-serif text-lg font-bold text-ink mb-2 relative z-10">
        画案待题 · 视觉呈现
      </h3>
      <p className="text-xs leading-relaxed max-w-[240px] font-sans text-ink/60 relative z-10">
        在左侧输入创作主题并选择文化风格约束后，点击开始创作。成图将在此处以数字画轴形式展开。
      </p>
    </div>
  );
}
