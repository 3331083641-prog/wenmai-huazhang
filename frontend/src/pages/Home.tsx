import { projectBrand } from '../data/projectBrand';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Sparkles,
  BookOpen,
  PenTool,
  Layout,
  Palette,
  Eye,
  Boxes,
  Compass,
  Layers,
  ChevronRight,
  Cpu,
} from 'lucide-react';
import { motion } from 'motion/react';
import { experienceById } from '../data/experiences';
import { uiPreviews } from '../data/uiPreviews';

/**
 * 首页「进入画里，再看一遍」的三件互动作品
 * 严格保留原有数据与成图引用
 */
const INTERACTIVE_ENTRIES = [
  {
    to: '/experience/zhuxianzhen-ruimao',
    experienceId: 'zhuxianzhen-ruimao',
    tag: '画中有话',
    styleBadge: '朱仙镇木版年画',
    title: '瑞猫迎春',
    desc: '在年画上点开六处线索，看粗黑墨线与矿物套色如何勾勒吉祥瑞兽与传统门神构图。',
    dynasty: '中原民间非遗',
  },
  {
    to: '/story/bianxiu-xiutu',
    experienceId: 'bianxiu-xiutu',
    tag: '一图一境',
    styleBadge: '汴绣纹样',
    title: '绣兔牡丹',
    desc: '顺着三折叙事品读汴绣：看丝线如何当笔、色阶如何自然晕染，感悟宋绣典雅温润之美的传承。',
    dynasty: '宋韵宫廷名绣',
  },
  {
    to: '/wander/songhua-yunhe',
    experienceId: 'songhua-yunhe',
    tag: '画境漫游',
    styleBadge: '宋画青绿山水',
    title: '云鹤临水楼',
    desc: '推进镜头沉浸入画：近景苍松翠石掠过、远峦重重退开，自由环顾漫游，探寻画中隐秘细节。',
    dynasty: '千里江山意境',
  },
];

/**
 * 平台核心能力矩阵
 */
const CORE_CAPABILITIES = [
  {
    icon: Palette,
    title: '五大传统视觉风格库',
    desc: '严选朱仙镇木版年画、汴绣纹样、宋画青绿山水、青花瓷纹样与中国剪纸，提炼色彩、构图、纹样与笔法特征，为 AI 创作提供结构化文化约束。',
    tag: '风格体系',
    badge: '典藏传承',
  },
  {
    icon: Sparkles,
    title: 'Qwen Image 3.0 多模态创作',
    desc: '支持「输入文本主题 + 传统文化参考图 + 风格强度约束」，实现可控的多模态视觉生成，真实回报参考图参与推理的置信状态。',
    tag: '智能生成',
    badge: '百炼大模型',
  },
  {
    icon: Cpu,
    title: 'Qwen3-VL 视觉理解与文化卡',
    desc: '接入本地多模态大模型，对生成作品进行自动视觉特征提取、文化意涵解读与应用建议，一键导出精致排版的双语 CultureCard。',
    tag: '文化解读',
    badge: '端侧推理',
  },
  {
    icon: Eye,
    title: '作品展厅与多维互动',
    desc: '作品生成即落盘，自动加入作品展厅；后台流水线自动构建画中有话、一图一境与 2.5D 画境漫游，无需重启即可多维度深度赏析。',
    tag: '互动赏析',
    badge: '沉浸共创',
  },
  {
    icon: Boxes,
    title: '三维纹脉展馆与布展 DIY',
    desc: '五馆水院虚拟艺术展馆，支持自由漫游、30 处自定义画框换画、传统器物陈设布置、昼夜光影切换与开关门、楼梯通行与水中游动。',
    tag: '虚拟空间',
    badge: 'Three.js 60FPS',
  },
  {
    icon: Layout,
    title: '文创转化与多载体打样',
    desc: '将作品一键映射到文旅明信片、数字海报、帆布袋、书签、杯垫、手机壁纸等 8 类预设载体，支持按比例预览并导出高清应用图。',
    tag: '文创应用',
    badge: '即时打样',
  },
];

export default function Home() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 md:py-16 lg:py-20">
      {/* ── 1. Hero 首屏：Scrolltide / Supahero 级文化殿堂叙事 ── */}
      <section className="relative grid lg:grid-cols-12 gap-12 lg:gap-8 items-center mb-24 md:mb-32">
        {/* 背景柔光晕染 */}
        <div className="absolute -top-12 -left-12 w-96 h-96 bg-primary/6 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute top-1/3 right-10 w-80 h-80 bg-gold/8 rounded-full blur-3xl pointer-events-none" />

        {/* 左侧：东方气韵大标题与排版 */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          className="lg:col-span-6 relative z-10"
        >
          {/* 文化标识胶囊 */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-gold/40 bg-white/70 shadow-xs mb-6 backdrop-blur-sm">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            <span className="text-xs font-serif font-medium text-ink/80 tracking-wider">
              传统文化视觉智能创作 · 沉浸展陈 · 文创应用
            </span>
          </div>

          {/* 巨幅主标题 */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-serif font-black tracking-tight leading-[1.18] mb-6 text-ink">
            {projectBrand.name}
            <div className="mt-3 flex items-center gap-3">
              <span className="text-xl sm:text-2xl lg:text-3xl font-medium text-primary">
                {projectBrand.subtitle}
              </span>
              <span className="chinese-seal text-[11px]">数字非遗</span>
            </div>
          </h1>

          {/* 核心阐释 */}
          <p className="text-base sm:text-lg text-ink/75 mb-8 leading-relaxed font-sans max-w-xl">
            以人工智能图像生成与多模态视觉理解为技术底座，融汇传统文化经典视觉风格与现代数字艺术。让千载华夏文脉从
            <span className="font-semibold text-primary">“被观看”走向“被共创”</span>
            ，打通灵感创作、深度赏析、三维展陈与文创落地的完整链路。
          </p>

          {/* 行动按钮群 */}
          <div className="flex flex-wrap items-center gap-4">
            <Link
              to="/creator"
              className="group relative inline-flex items-center gap-2 px-8 py-3.5 btn-chinese text-base font-serif shadow-[0_8px_24px_rgba(158,36,27,0.25)] hover:shadow-[0_12px_32px_rgba(158,36,27,0.35)] transition-all"
            >
              <Sparkles className="w-4 h-4 text-gold animate-pulse" />
              <span>立即体验创作</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>

            <Link
              to="/styles"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-lg border border-gold/50 bg-white/80 hover:bg-white hover:border-primary/50 text-ink/85 font-serif text-base shadow-xs hover:text-primary transition-all"
            >
              <Palette className="w-4 h-4 text-primary" />
              <span>浏览五大风格库</span>
            </Link>

            <Link
              to="/heritage-gallery"
              className="inline-flex items-center gap-1.5 text-xs font-serif text-ink/65 hover:text-primary transition-colors py-2 px-3 rounded-md hover:bg-black/5"
            >
              <Compass className="w-4 h-4 text-gold" />
              <span>进入三维虚拟展馆</span>
            </Link>
          </div>
        </motion.div>

        {/* 右侧：五大传统风格展陈画幅（3D 浮动层叠与细金宣纸微框） */}
        <motion.div
          initial={{ opacity: 0, scale: 0.94 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="lg:col-span-6 relative w-full h-[520px] sm:h-[560px]"
        >
          <div className="relative w-full h-full">
            {/* 风格 1：中央主体立轴大图 - 朱仙镇木版年画 */}
            <div className="absolute top-[8%] left-[16%] w-[56%] aspect-[3/4] rounded-2xl overflow-hidden shadow-[0_24px_60px_rgba(63,43,31,0.18)] border-[3.5px] border-white z-20 group hover:-translate-y-2 transition-all duration-500 bg-white">
              <img
                src={import.meta.env.BASE_URL + "zhuxianzhen.png"}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                alt="朱仙镇木版年画"
              />
              <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 via-black/20 to-transparent p-4 flex items-end justify-between text-white">
                <div>
                  <span className="text-[10px] tracking-widest text-gold uppercase font-serif">WOODBLOCK PRINT</span>
                  <div className="text-sm font-serif font-bold">朱仙镇木版年画</div>
                </div>
                <span className="chinese-seal text-[9px] bg-primary">非遗</span>
              </div>
            </div>

            {/* 风格 2：右上浮动画幅 - 宋画青绿山水 */}
            <div className="absolute top-[2%] right-[2%] w-[40%] aspect-[4/3] rounded-2xl overflow-hidden shadow-[0_16px_40px_rgba(63,43,31,0.12)] border-[3px] border-white/90 z-10 group hover:-translate-y-2 transition-all duration-500 bg-white">
              <img
                src={import.meta.env.BASE_URL + "songhua.png"}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                alt="宋画青绿山水"
              />
              <div className="absolute bottom-2.5 right-2.5 bg-black/60 backdrop-blur-md px-2.5 py-1 rounded text-[11px] text-white font-serif">
                宋画青绿山水
              </div>
            </div>

            {/* 风格 3：右下浮动画幅 - 汴绣纹样 */}
            <div className="absolute bottom-[4%] right-[4%] w-[42%] aspect-[4/3] rounded-2xl overflow-hidden shadow-[0_16px_40px_rgba(63,43,31,0.14)] border-[3px] border-white/90 z-30 group hover:-translate-y-2 transition-all duration-500 bg-white">
              <img
                src={import.meta.env.BASE_URL + "bianxiu.png"}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                alt="汴绣纹样"
              />
              <div className="absolute bottom-2.5 left-2.5 bg-white/90 backdrop-blur-md px-2.5 py-1 rounded text-[11px] text-ink font-serif border border-gold/30">
                汴绣纹样
              </div>
            </div>

            {/* 风格 4：左下青花瓷圆盘 */}
            <div className="absolute bottom-[2%] left-[2%] w-[35%] aspect-square rounded-full overflow-hidden shadow-[0_20px_50px_rgba(49,95,136,0.22)] border-[4px] border-white z-40 group hover:-rotate-6 hover:scale-105 transition-all duration-500 bg-white">
              <img
                src={import.meta.env.BASE_URL + "qinghua.png"}
                className="w-full h-full object-cover"
                alt="青花瓷纹样"
              />
              <div className="absolute inset-x-0 bottom-2 text-center">
                <span className="bg-[#315F88]/90 text-white text-[10px] px-2.5 py-0.5 rounded-full font-serif shadow-xs">
                  青花瓷纹样
                </span>
              </div>
            </div>

            {/* 风格 5：左上中国剪纸 */}
            <div className="absolute top-[3%] left-[1%] w-[28%] aspect-square rounded-2xl overflow-hidden shadow-[0_12px_32px_rgba(158,36,27,0.14)] border-[2.5px] border-white/90 z-10 group hover:scale-105 hover:-translate-y-1 transition-all duration-500 bg-[#FFF5F2]">
              <img
                src={import.meta.env.BASE_URL + "jianzhi.png"}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                alt="中国剪纸"
              />
              <div className="absolute top-2 left-2 bg-primary text-white text-[9px] px-1.5 py-0.5 rounded font-serif shadow-xs">
                中国剪纸
              </div>
            </div>

            {/* 悬浮美学标签 */}
            <div className="absolute top-1/2 -right-4 -translate-y-1/2 bg-white/95 backdrop-blur-md px-4 py-3 rounded-xl shadow-[0_12px_36px_rgba(158,36,27,0.18)] flex items-center gap-3 z-50 border border-gold/40">
              <div className="w-10 h-10 rounded-full bg-gold/15 flex items-center justify-center shrink-0">
                <Sparkles className="text-gold w-5 h-5" />
              </div>
              <div>
                <p className="text-[10px] text-primary/80 font-serif tracking-wider">五大传统风格</p>
                <p className="font-serif font-bold text-xs sm:text-sm text-ink">Qwen 3.0 智能生成</p>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* ── 2. 印鉴珍赏 · 五大传统风格快捷条幅 ───────────────────── */}
      <section className="mb-24 rounded-2xl border border-gold/35 bg-white/60 p-5 sm:p-6 shadow-[0_8px_30px_rgba(63,43,31,0.04)] backdrop-blur-sm">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2.5">
            <span className="chinese-seal text-[10px]">印鉴</span>
            <span className="text-sm font-serif font-bold text-ink tracking-wide">
              五大传统文化视觉风格：
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-3 sm:gap-4 justify-center">
            {[
              { id: 'zhuxianzhen', name: '朱仙镇木版年画', img: 'zhuxianzhen.png' },
              { id: 'bianxiu', name: '汴绣纹样', img: 'bianxiu.png' },
              { id: 'songhua', name: '宋画青绿山水', img: 'songhua.png' },
              { id: 'qinghua', name: '青花瓷纹样', img: 'qinghua.png' },
              { id: 'jianzhi', name: '中国剪纸', img: 'jianzhi.png' },
            ].map((style) => (
              <Link
                key={style.id}
                to={`/styles`}
                className="group flex items-center gap-2.5 px-3.5 py-1.5 rounded-full border border-gold/30 bg-white/90 hover:border-primary hover:bg-primary/5 hover:shadow-xs transition-all"
              >
                <div className="w-7 h-7 rounded-full overflow-hidden border border-gold/50 shrink-0">
                  <img
                    src={import.meta.env.BASE_URL + style.img}
                    className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
                    alt={style.name}
                  />
                </div>
                <span className="text-xs font-serif text-ink/80 group-hover:text-primary transition-colors">
                  {style.name}
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── 3. 进入画里，再看一遍（美术馆展签级互动赏析） ───────── */}
      <section className="mb-24 md:mb-32">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="w-1.5 h-3.5 bg-primary rounded-full" />
              <p className="text-xs font-serif tracking-[0.28em] text-primary">
                {projectBrand.name} · 多维文化赏析
              </p>
            </div>
            <h2 className="font-serif text-2xl md:text-3xl lg:text-4xl font-bold text-ink">
              进入画里，再看一遍
            </h2>
          </div>
          <Link
            to="/gallery"
            className="group inline-flex items-center gap-1.5 text-sm font-serif font-medium text-primary hover:text-primary-dark transition-all"
          >
            <span>浏览作品展厅全部作品</span>
            <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {INTERACTIVE_ENTRIES.map((item, index) => {
            const experience = experienceById.get(item.experienceId);
            const src = experience?.artworkUrl || '';
            return (
              <Link
                key={item.tag}
                to={item.to}
                className="group flex flex-col overflow-hidden rounded-2xl border border-gold/30 bg-white/80 shadow-[0_10px_30px_rgba(63,43,31,0.05)] transition-all duration-400 hover:-translate-y-1.5 hover:shadow-[0_20px_45px_rgba(158,36,27,0.12)] hover:border-primary/40"
              >
                {/* 展品画面 */}
                <div className="relative aspect-[16/10] overflow-hidden bg-ink/5">
                  {src && (
                    <img
                      src={src}
                      alt={`${item.title} · ${experience?.styleName ?? ''}`}
                      className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
                      loading="lazy"
                    />
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent pointer-events-none" />
                  <span className="absolute left-3 top-3 rounded-md bg-white/95 backdrop-blur-sm px-2.5 py-1 text-[11px] font-serif font-bold text-primary shadow-xs border border-gold/20">
                    {item.tag}
                  </span>
                  <span className="absolute right-3 top-3 rounded-md bg-black/60 backdrop-blur-sm px-2 py-0.5 text-[10px] tracking-wider text-white">
                    {item.styleBadge}
                  </span>
                </div>

                {/* 展签信息 */}
                <div className="flex flex-1 flex-col p-6">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[11px] font-serif text-primary/70">{item.dynasty}</span>
                    <span className="text-[10px] font-mono text-gold font-bold">EXHIBIT 0{index + 1}</span>
                  </div>
                  <h3 className="font-serif text-xl font-bold text-ink group-hover:text-primary transition-colors">
                    {item.title}
                  </h3>
                  <p className="mt-2.5 text-xs md:text-sm leading-relaxed text-ink/70 line-clamp-2">
                    {item.desc}
                  </p>

                  <div className="mt-5 pt-4 border-t border-gold/20 flex items-center justify-between">
                    <span className="inline-flex items-center gap-1.5 text-xs font-serif font-medium text-primary group-hover:gap-2.5 transition-all">
                      走进去沉浸赏析
                      <ArrowRight className="h-3.5 w-3.5" />
                    </span>
                    <span className="text-[11px] text-ink/45 font-mono">
                      {experience?.hotspots?.length ? `${experience.hotspots.length} 处微观线索` : '2.5D 画境漫游'}
                    </span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* ── 4. 纹脉展馆 · 沉浸三维数字空间 ───────────────────────── */}
      <section className="mb-24 md:mb-32 relative overflow-hidden rounded-3xl border border-gold/45 bg-gradient-to-br from-[#FCFBF8] via-[#FAF6F0] to-[#EFE4D2] p-8 md:p-12 shadow-[0_16px_50px_rgba(63,43,31,0.08)]">
        <div className="absolute -top-16 -right-16 w-96 h-96 bg-gold/15 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-16 -left-16 w-96 h-96 bg-primary/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 grid lg:grid-cols-12 gap-8 lg:gap-12 items-center">
          {/* 左侧：精美展馆建筑外观大图 */}
          <div className="lg:col-span-7">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="group relative aspect-[16/10] overflow-hidden rounded-2xl border-2 border-white shadow-2xl bg-black/10"
            >
              <img
                src={uiPreviews.heritageExterior}
                alt="纹脉展馆建筑外观"
                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-[1.03]"
                loading="lazy"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-transparent to-transparent pointer-events-none" />
              <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between text-white">
                <span className="text-xs font-serif tracking-widest bg-black/45 backdrop-blur-md px-3 py-1 rounded border border-white/20">
                  实景渲染 · 纹脉数字化艺术展馆
                </span>
                <span className="text-xs opacity-90 font-mono hidden sm:inline">
                  Three.js 60FPS 虚拟实体空间
                </span>
              </div>
            </motion.div>
          </div>

          {/* 右侧：文化韵味与功能介绍 */}
          <div className="lg:col-span-5 flex flex-col justify-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-gold/40 bg-white/70 text-primary text-xs font-serif font-medium w-fit mb-4">
              <Compass className="w-3.5 h-3.5 text-gold" />
              沉浸式三维虚拟艺术展馆
            </div>
            <h2 className="text-2xl md:text-3xl lg:text-4xl font-serif font-bold text-ink mb-4 leading-snug">
              纹脉展馆 <br />
              <span className="text-lg md:text-xl font-normal text-primary">
                虚拟漫游 · 自由布展 · 交互策展
              </span>
            </h2>
            <p className="text-sm md:text-base text-ink/75 leading-relaxed mb-6 font-sans">
              纹脉展馆是{projectBrand.name}的沉浸式三维文化展示空间。漫游水院中式古建、近距离赏析传统文化主题作品，并通过 30 处画框自由换画、器物陈设打造个人专属策展空间。
            </p>

            <div className="grid grid-cols-2 gap-3 mb-8 text-xs text-ink/80 font-serif">
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-white/80 border border-gold/30">
                <span className="w-1.5 h-1.5 rounded-full bg-gold" />
                五馆水院古建格局
              </div>
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-white/80 border border-gold/30">
                <span className="w-1.5 h-1.5 rounded-full bg-gold" />
                30 处自定义策展画框
              </div>
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-white/80 border border-gold/30">
                <span className="w-1.5 h-1.5 rounded-full bg-gold" />
                传统博古器物陈设
              </div>
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-white/80 border border-gold/30">
                <span className="w-1.5 h-1.5 rounded-full bg-gold" />
                昼夜晨昏光影流转
              </div>
            </div>

            <Link
              to="/heritage-gallery"
              className="group inline-flex items-center justify-center gap-2.5 px-7 py-3.5 rounded-xl btn-chinese text-base font-serif shadow-md hover:shadow-xl transition-all w-fit"
            >
              <span>漫游纹脉展馆</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── 5. 平台核心能力（东方微质感能力矩阵） ─────────────────── */}
      <section className="mb-24 md:mb-32">
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-2 mb-2">
            <span className="w-1.5 h-3.5 bg-primary rounded-full" />
            <span className="text-xs font-serif tracking-[0.25em] text-primary">CAPABILITIES</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-serif font-bold text-ink mb-3">
            平台核心能力
          </h2>
          <p className="text-sm md:text-base text-ink/65 max-w-2xl mx-auto">
            围绕传统文化视觉数字化创作，打通从创意输入、可控生成、自动解读到空间展陈与文创转化的全景闭环。
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {CORE_CAPABILITIES.map((feature, i) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.08 }}
                className="oriental-gallery-card p-7 rounded-2xl transition-all duration-300 hover:shadow-[0_16px_40px_rgba(158,36,27,0.12)] hover:-translate-y-1.5 hover:border-primary/40 flex flex-col group"
              >
                <div className="flex items-center justify-between mb-5">
                  <div className="w-12 h-12 rounded-xl bg-white shadow-xs flex items-center justify-center group-hover:bg-primary group-hover:text-white transition-all text-primary border border-gold/30">
                    <Icon className="w-6 h-6" />
                  </div>
                  <span className="text-[11px] font-serif text-primary/80 bg-primary/5 px-2.5 py-1 rounded-full border border-primary/15">
                    {feature.tag}
                  </span>
                </div>
                <h3 className="font-serif font-bold text-lg mb-2 text-ink group-hover:text-primary transition-colors">
                  {feature.title}
                </h3>
                <p className="text-xs md:text-sm text-ink/70 leading-relaxed font-sans flex-1">
                  {feature.desc}
                </p>
                <div className="mt-4 pt-3 border-t border-gold/20 flex items-center justify-between text-[11px] text-ink/50 font-serif">
                  <span>{feature.badge}</span>
                  <span className="text-gold font-mono">0{i + 1}</span>
                </div>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* ── 6. 创作与应用全生命周期工作流 ─────────────────────────── */}
      <section className="bg-white/60 border border-gold/35 rounded-3xl p-8 md:p-12 relative overflow-hidden mb-24 md:mb-32 shadow-[0_12px_40px_rgba(63,43,31,0.05)]">
        <div className="absolute top-0 right-0 w-80 h-80 bg-gold/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-80 h-80 bg-primary/8 rounded-full blur-3xl pointer-events-none" />

        <div className="text-center mb-12 relative z-10">
          <span className="chinese-seal text-[10px] mb-2">闭环</span>
          <h2 className="text-2xl md:text-3xl lg:text-4xl font-serif text-primary font-bold mb-2">
            创作与应用全生命周期工作流
          </h2>
          <p className="text-xs md:text-sm text-ink/65 max-w-xl mx-auto">
            从用户创意灵感到最终文创打样与空间展示，每一步透明可控、环环相扣
          </p>
        </div>

        <div className="flex flex-col lg:flex-row justify-between items-center gap-6 relative z-10 w-full max-w-5xl mx-auto">
          {[
            { step: '01', title: '创作主题与参考图', icon: PenTool },
            { step: '02', title: '传统视觉风格选择', icon: Palette },
            { step: '03', title: 'Qwen Image 智能生成', icon: Sparkles },
            { step: '04', title: '自动解读与文化卡', icon: BookOpen },
            { step: '05', title: '展厅入库与三维布展', icon: Boxes },
            { step: '06', title: '文创载体衍生应用', icon: Layout },
          ].map((item, i, arr) => {
            const Icon = item.icon;
            return (
              <div
                key={i}
                className="flex flex-col lg:flex-row items-center gap-3 flex-1 w-full lg:w-auto group"
              >
                <div className="flex flex-col items-center text-center w-full">
                  <div className="w-14 h-14 rounded-2xl bg-white shadow-xs border border-gold/40 flex items-center justify-center text-primary mb-3 relative z-10 group-hover:scale-110 group-hover:bg-primary group-hover:text-white transition-all duration-300">
                    <Icon className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-mono text-gold font-bold tracking-wider mb-0.5">
                    STEP {item.step}
                  </span>
                  <span className="text-xs font-serif font-medium text-ink/85 leading-tight">
                    {item.title}
                  </span>
                </div>
                {i < arr.length - 1 && (
                  <div className="hidden lg:block flex-1 h-[1.5px] bg-gold/40 w-full relative -top-5">
                    <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-primary" />
                  </div>
                )}
                {i < arr.length - 1 && (
                  <ChevronRight className="lg:hidden text-primary/40 my-1 h-4 w-4" />
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* ── 7. 文创衍生与空间展陈美学 ───────────────────────────── */}
      <section className="mb-24 md:mb-32">
        <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-1.5 h-3.5 bg-primary rounded-full" />
              <p className="text-xs tracking-[0.25em] text-primary/80 font-serif">MERCHANDISE & SPACE</p>
            </div>
            <h2 className="text-2xl md:text-3xl font-serif font-bold text-ink">
              文创衍生与空间展陈美学
            </h2>
          </div>
          <Link
            to="/products"
            className="text-sm font-serif text-primary hover:text-primary-dark transition-colors flex items-center gap-1 font-medium group"
          >
            <span>打开文创工坊</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <Link
            to="/products"
            className="aspect-[4/3] rounded-2xl overflow-hidden shadow-xs hover:shadow-xl transition-all group relative cursor-pointer border border-gold/30 bg-[#FAF7F2]"
          >
            <img
              src={import.meta.env.BASE_URL + "scenarios/product-package-concept.jpg"}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
              alt="朱仙镇年画瑞猫节庆礼盒"
              loading="lazy"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/25 to-transparent" />
            <div className="absolute bottom-4 left-4 right-4 text-white">
              <span className="text-[10px] tracking-widest text-gold uppercase font-serif">NEW YEAR PACKAGING</span>
              <div className="text-base font-serif font-bold">年画节庆礼盒包装</div>
              <p className="text-xs text-white/80 mt-0.5 line-clamp-1">瑞猫年画烫金浮雕与利是封</p>
            </div>
          </Link>

          <Link
            to="/products"
            className="aspect-[4/3] rounded-2xl overflow-hidden shadow-xs hover:shadow-xl transition-all group relative cursor-pointer border border-gold/30 bg-[#FAF7F2]"
          >
            <img
              src={import.meta.env.BASE_URL + "scenarios/product-coaster-lifestyle.jpg"}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
              alt="青花瓷杯垫茶席生活美学"
              loading="lazy"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/25 to-transparent" />
            <div className="absolute bottom-4 left-4 right-4 text-white">
              <span className="text-[10px] tracking-widest text-gold uppercase font-serif">TEA MERCHANDISE</span>
              <div className="text-base font-serif font-bold">青花瓷杯垫与茶席</div>
              <p className="text-xs text-white/80 mt-0.5 line-clamp-1">缠枝双蝶纹样与天然棉麻生活</p>
            </div>
          </Link>

          <Link
            to="/products"
            className="aspect-[4/3] rounded-2xl overflow-hidden shadow-xs hover:shadow-xl transition-all group relative cursor-pointer border border-gold/30 bg-[#FAF7F2]"
          >
            <img
              src={import.meta.env.BASE_URL + "scenarios/product-embroidery-lifestyle.jpg"}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
              alt="汴绣丝绸艺术团扇生活"
              loading="lazy"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/25 to-transparent" />
            <div className="absolute bottom-4 left-4 right-4 text-white">
              <span className="text-[10px] tracking-widest text-gold uppercase font-serif">SILK EMBROIDERY</span>
              <div className="text-base font-serif font-bold">汴绣真丝团扇与长巾</div>
              <p className="text-xs text-white/80 mt-0.5 line-clamp-1">双面劈丝牡丹与宋韵刺绣</p>
            </div>
          </Link>

          <Link
            to="/scenarios"
            className="aspect-[4/3] rounded-2xl overflow-hidden shadow-xs hover:shadow-xl transition-all group relative cursor-pointer border border-gold/30 bg-black"
          >
            <img
              src={import.meta.env.BASE_URL + "scenarios/museum-screen-concept.jpg"}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
              alt="环幕数字展陈大屏"
              loading="lazy"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/25 to-transparent" />
            <div className="absolute bottom-4 left-4 right-4 text-white">
              <span className="text-[10px] tracking-widest text-gold uppercase font-serif">DIGITAL EXHIBITION</span>
              <div className="text-base font-serif font-bold">环幕展陈与沉浸空间</div>
              <p className="text-xs text-white/80 mt-0.5 line-clamp-1">超高清曲面大屏空间全景展陈</p>
            </div>
          </Link>
        </div>
      </section>

      {/* ── 8. 底部金石落款数据横幅 ───────────────────────────────── */}
      <section className="bg-gradient-to-r from-primary-dark via-primary to-primary-dark text-white rounded-2xl py-12 px-6 flex justify-around flex-wrap gap-8 items-center relative overflow-hidden shadow-[0_16px_40px_rgba(158,36,27,0.28)] border border-gold/40">
        <div className="absolute inset-0 paper-noise pointer-events-none" />
        {[
          { v: '5 门类', l: '传统视觉风格条目' },
          { v: '8 载体', l: '文创实景打样模板' },
          { v: '3 维度', l: '多维交互深度赏析' },
          { v: '2 楼层', l: '实体感三维虚拟展馆' },
          { v: '100%', l: '多模态闭环生成与落盘' },
        ].map((stat, i) => (
          <div key={i} className="text-center relative z-10 flex flex-col items-center">
            <div className="text-3xl md:text-4xl font-serif font-bold text-gold drop-shadow-sm mb-1.5">
              {stat.v}
            </div>
            <div className="text-xs md:text-sm text-white/90 font-serif tracking-wider">
              {stat.l}
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
