import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import {
  MonitorPlay,
  GraduationCap,
  ShoppingBag,
  PenTool,
  Eye,
  Smartphone,
  Sparkles,
  ArrowRight,
  Compass,
  Frame,
  Palette,
  Layers,
  FileText,
  Package,
  Coffee,
  Scissors,
  SlidersHorizontal,
  ShieldCheck,
  Search,
  Scroll,
  Move3d,
  Share2,
  Flame,
  CheckCircle2,
  type LucideIcon,
} from 'lucide-react';

import { uiPreviews } from '../data/uiPreviews';
import { TiltCard } from '../components/scenarios/TiltCard';
import { LiveCreatorSandbox } from '../components/scenarios/LiveCreatorSandbox';
import { InteractiveHotspotStage } from '../components/scenarios/InteractiveHotspotStage';
import { CultureCardDeck } from '../components/scenarios/CultureCardDeck';

const { products: productShot } = uiPreviews;

type FeatureBadge = {
  label: string;
  detail: string;
};

type ScenarioTab = {
  id: string;
  label: string;
  shot: string;
  alt: string;
  badge?: string;
};

type Scenario = {
  id: string;
  number: string;
  icon: LucideIcon;
  tag: string;
  title: string;
  subtitle: string;
  summary: string;
  badges: FeatureBadge[];
  to: string;
  cta: string;
  shot?: string;
  alt?: string;
  tabs?: ScenarioTab[];
  customRenderer?: 'creator' | 'hotspots' | 'culture-card';
};

const SCENARIOS: Scenario[] = [
  {
    id: 'museum-exhibition',
    number: '01',
    icon: MonitorPlay,
    tag: '空间展陈',
    title: '三维数字展馆与空间展陈',
    subtitle: 'SPATIAL EXHIBITION · 虚拟水院与环幕映射',
    summary:
      '构筑可自由漫游、虚实布展的五馆水院中式虚拟美术馆。支持第一/第三人称自由穿行与昼夜光影流转，开放 30 处画框支持一键策展换画，让典藏艺术从展柜走向三维时空。',
    badges: [
      { label: 'Three.js 60FPS 实时渲染', detail: '中式水院木构梁架昼夜晨昏光影' },
      { label: '30 处画框自由布展', detail: '从器物展柜到立轴画框随心策展' },
      { label: '沉浸环幕空间映射', detail: '适配大型曲面大屏与数字展厅构想' },
    ],
    to: '/heritage-gallery',
    cta: '漫游三维展馆',
    tabs: [
      {
        id: '3d-dusk',
        label: '3D 展馆暮色水院',
        shot: import.meta.env.BASE_URL + 'scenarios/heritage-dusk.jpg',
        alt: '纹脉展馆暮色光影：五馆水院倒影与中式暖阳夜景',
        badge: 'Three.js 暮色光影实景',
      },
      {
        id: 'screen-concept',
        label: '数字环幕沉浸空间',
        shot: import.meta.env.BASE_URL + 'scenarios/museum-screen-concept.jpg',
        alt: '现代顶级美术馆沉浸式数字艺术展厅全景（宋画青绿山水）',
        badge: '曲面大屏空间展陈构想',
      },
      {
        id: '3d-gallery',
        label: '3D 展馆全景昼光',
        shot: import.meta.env.BASE_URL + 'scenarios/heritage-gallery.jpg',
        alt: '纹脉展馆外景：湖畔水院与中式大木梁架建筑全景',
        badge: '昼光水院建筑全景',
      },
    ],
  },
  {
    id: 'heritage-education',
    number: '02',
    icon: GraduationCap,
    tag: '美育研学',
    title: '非遗活化与现代美育研学',
    subtitle: 'HERITAGE EDUCATION · 知识图谱与工艺解构',
    summary:
      '将年画、汴绣、宋画、青花瓷与剪纸五大传统流派的构图、设色与线条转化为可视化的结构化美育课件。支持同题多风格比对，并可一键导出包含设色谱系与典藏文献的高清 CultureCard 知识卡。',
    badges: [
      { label: '五大传统流派解构', detail: '设色图谱、版刻墨线与真丝经纬' },
      { label: '同题跨流派对比', detail: '同一主题切换风格逐次生成与比对' },
      { label: '结构化研学课件卡', detail: '一键导出标准 CultureCard 美育卡' },
    ],
    to: '/styles',
    cta: '查阅风格知识库',
    customRenderer: 'culture-card',
  },
  {
    id: 'creative-products',
    number: '03',
    icon: ShoppingBag,
    tag: '生活美学',
    title: '文博衍生与实体器物打样',
    subtitle: 'CREATIVE DERIVATIVES · 物理比例与工艺还原',
    summary:
      '打通从数字画作到生活实物美学的完整链路。内置 8 类文创载体真实物理比例与材质贴图，智能排版材质光影，从节日礼盒到茶席器物，一键导出 1600×1200 生产级打样图。',
    badges: [
      { label: '8 类文创载体比例', detail: '伴手礼盒、茶具、扇面、瓷器等' },
      { label: '真实材质质感渲染', detail: '特种纸烫金、真丝双面绣透光与釉面光泽' },
      { label: '生产级高清打样导出', detail: '1600×1200 高清预览便于打样生产' },
    ],
    to: '/products',
    cta: '进入文创工坊',
    tabs: [
      {
        id: 'box-concept',
        label: '年画伴手礼盒',
        shot: import.meta.env.BASE_URL + 'scenarios/product-package-concept.jpg',
        alt: '朱仙镇年画瑞猫节庆礼盒与利是封包装打样',
        badge: '国潮包装打样概念',
      },
      {
        id: 'coaster-concept',
        label: '青花茶席杯垫',
        shot: import.meta.env.BASE_URL + 'scenarios/product-coaster-lifestyle.jpg',
        alt: '青花瓷缠枝纹吸水杯垫与生活美学茶席',
        badge: '生活器物打样概念',
      },
      {
        id: 'embroidery-concept',
        label: '汴绣真丝团扇',
        shot: import.meta.env.BASE_URL + 'scenarios/product-embroidery-lifestyle.jpg',
        alt: '宋代汴绣双面绣丝绸真丝团扇与长巾',
        badge: '丝织非遗打样概念',
      },
      {
        id: 'studio-live',
        label: '工坊多载体排版',
        shot: productShot,
        alt: '文创转化工坊：多载体排版与效果预览',
        badge: '8 类载体实时排版',
      },
    ],
  },
  {
    id: 'creative-studio',
    number: '04',
    icon: PenTool,
    tag: '智能工坊',
    title: '文化主题智能创作工坊',
    subtitle: 'INTELLIGENT WORKSHOP · 多模态生成与全生命周期存证',
    summary:
      '专为东方美学打造的多模态可控生成工作台。支持创作主题与参考图双轮驱动，通过风格强度滑块自由调配传统基因浓度，生成全过程锚定数字存证哈希并自动入库。',
    badges: [
      { label: 'Qwen 3.0 美学底座', detail: '阿里百炼多模态模型调优东方造型语法' },
      { label: '0%~100% 细粒度控制', detail: '自由调节风格影响度，平衡创新与传统' },
      { label: 'SHA-256 全链路存证', detail: '元数据与成图哈希实时落盘防伪追溯' },
    ],
    to: '/creator',
    cta: '打开生成工作台',
    customRenderer: 'creator',
  },
  {
    id: 'interactive-guide',
    number: '05',
    icon: Eye,
    tag: '深度导览',
    title: '多维交互深度赏析与文化导览',
    subtitle: 'INTERACTIVE READING · 热点探秘、长卷读史与2.5D入画',
    summary:
      '打破走马观花式的静态看画。通过“微观热点探索”、“三折长卷读史”与“2.5D 推镜入画”三种递进交互体验，让同一件传统艺术品绽放出立体多维的互动叙事魅力。',
    badges: [
      { label: '画中有话微观探秘', detail: '点击画面隐秘热点，逐笔探寻线条神韵' },
      { label: '一图一境长卷叙事', detail: '三折图文长卷随手势平滑延展' },
      { label: '2.5D 深度视差漫游', detail: '单图深度估计与视差微移推镜入画' },
    ],
    to: '/experience/zhuxianzhen-ruimao',
    cta: '体验深度赏析',
    customRenderer: 'hotspots',
  },
  {
    id: 'social-dissemination',
    number: '06',
    icon: Smartphone,
    tag: '文博破圈',
    title: '数字文博线上传播与社交日签',
    subtitle: 'SOCIAL DISSEMINATION · 移动端黄金视域与审美普及',
    summary:
      '探索东方传统美学在当代青年移动社交生态中的传播范式。定制符合手机竖屏沉浸视域的文化日签卡与朋友圈图文模板，以更纯粹、高颜值的形式唤醒大众东方审美共鸣。',
    badges: [
      { label: '移动竖屏沉浸视域', detail: '专为手机黄金比例定制的高级日签' },
      { label: '轻量社交图文裂变', detail: '结构化提炼非遗知识短篇，便于微信传播' },
      { label: '青年审美日常化', detail: '传统雅器与经典纹样化身掌上美学课' },
    ],
    to: '/styles',
    cta: '查阅视觉风格库',
    tabs: [
      {
        id: 'mobile-sky',
        label: '天青釉 · 文化日签',
        shot: import.meta.env.BASE_URL + 'scenarios/social-mobile-concept.jpg',
        alt: '极简智能手机展示宋代汝窑天青釉文化知识日签卡',
        badge: '手机黄金视域日签',
      },
    ],
  },
];

export default function Scenarios() {
  const shouldReduceMotion = useReducedMotion();
  const [activeTabs, setActiveTabs] = useState<Record<string, string>>({
    'museum-exhibition': '3d-dusk',
    'creative-products': 'box-concept',
    'social-dissemination': 'mobile-sky',
  });

  const scrollToScenario = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12 md:py-20 lg:py-24">
      {/* ── 页面主标题区 ────────────────────────────────────────── */}
      <header className="mb-14 sm:mb-20 text-center max-w-3xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-gold/40 bg-white/70 backdrop-blur-md text-primary text-xs sm:text-sm font-medium mb-5 shadow-xs"
        >
          <Sparkles className="w-3.5 h-3.5 text-gold" />
          <span>东方意境 · 当代新生</span>
          <span className="w-1.5 h-1.5 rounded-full bg-gold" />
          <span className="font-serif text-ink/70">6 大数字赋能场景</span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.1 }}
          className="text-4xl sm:text-5xl lg:text-6xl font-serif font-bold text-ink mb-5 leading-[1.15] tracking-tight"
        >
          文脉化境 · 多维应用场景
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="text-base sm:text-lg text-ink/75 leading-relaxed font-sans max-w-2xl mx-auto"
        >
          融古典艺术之美，入当代生活之境。从虚实相生的三维展陈、格物致知的美育研学，到器物焕新的文创打样与移动传播。
        </motion.p>

        {/* ── Scrolltide 风格快捷场景导览磁贴条 ────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-2 p-1.5 rounded-2xl bg-white/60 backdrop-blur-md border border-gold/30 shadow-xs max-w-2xl mx-auto"
        >
          {SCENARIOS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => scrollToScenario(item.id)}
              className="px-3 py-1.5 rounded-xl text-xs font-serif text-ink/80 hover:text-primary hover:bg-white transition-all cursor-pointer flex items-center gap-1.5 border border-transparent hover:border-gold/30"
            >
              <span className="font-mono text-gold text-[11px] font-bold">{item.number}</span>
              <span>{item.tag}</span>
            </button>
          ))}
        </motion.div>
      </header>

      {/* ── 纵向交错长廊：滚动逐组浮现 ────────────────────────────── */}
      <div className="space-y-24 md:space-y-32">
        {SCENARIOS.map((item, index) => {
          const isEven = index % 2 === 0;
          const Icon = item.icon;
          const activeTabId = activeTabs[item.id] || (item.tabs ? item.tabs[0].id : '');
          const currentTab = item.tabs?.find((t) => t.id === activeTabId) || item.tabs?.[0];
          const displayShot = currentTab?.shot || item.shot;
          const displayAlt = currentTab?.alt || item.alt || item.title;
          const displayBadge = currentTab?.badge;

          return (
            <motion.article
              id={item.id}
              key={item.id}
              initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: 35 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
              className={`relative grid lg:grid-cols-12 gap-8 lg:gap-12 items-center ${
                isEven ? '' : 'lg:grid-flow-dense'
              }`}
            >
              {/* 背景古风数字水印 */}
              <div
                className={`absolute -top-10 font-serif font-black text-8xl lg:text-9xl text-gold/10 select-none pointer-events-none z-0 hidden sm:block ${
                  isEven ? 'right-2' : 'left-2'
                }`}
              >
                {item.number}
              </div>

              {/* ── 左/右侧：高级交互或图片视觉展示台 ────────────── */}
              <div
                className={`lg:col-span-7 relative z-10 w-full ${
                  isEven ? 'lg:order-2' : 'lg:order-1'
                }`}
              >
                {/* 针对智能创作工坊：使用实时多模态沙盒 */}
                {item.customRenderer === 'creator' && <LiveCreatorSandbox />}

                {/* 针对多维深度赏析：使用微观热点+长卷+2.5D综合交互台 */}
                {item.customRenderer === 'hotspots' && <InteractiveHotspotStage />}

                {/* 针对美育研学：使用无损高清知识卡展开台 */}
                {item.customRenderer === 'culture-card' && <CultureCardDeck />}

                {/* 常规场景：使用 TiltCard 3D 悬浮视差画框 */}
                {!item.customRenderer && (
                  <TiltCard className="aspect-[16/10] group">
                    {/* 顶部多角度切换标签 */}
                    {item.tabs && item.tabs.length > 1 && (
                      <div className="absolute top-3.5 left-3.5 z-30 flex flex-wrap items-center gap-1.5 p-1 rounded-xl bg-black/60 backdrop-blur-md border border-white/20 shadow-lg">
                        {item.tabs.map((tab) => {
                          const isSelected = tab.id === activeTabId;
                          return (
                            <button
                              key={tab.id}
                              type="button"
                              onClick={() =>
                                setActiveTabs((prev) => ({ ...prev, [item.id]: tab.id }))
                              }
                              className={`px-3 py-1 rounded-lg text-xs font-serif transition-all cursor-pointer ${
                                isSelected
                                  ? 'bg-white text-ink font-bold shadow-xs'
                                  : 'text-white/80 hover:text-white hover:bg-white/10'
                              }`}
                            >
                              {tab.label}
                            </button>
                          );
                        })}
                      </div>
                    )}

                    {displayShot && (
                      <img
                        src={displayShot}
                        alt={displayAlt}
                        className="w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.04]"
                        loading="lazy"
                      />
                    )}

                    {/* 悬停微光与底部状态徽标 */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent pointer-events-none" />
                    <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between text-white text-xs z-20">
                      <span className="font-serif tracking-wider bg-black/55 backdrop-blur-md px-3 py-1 rounded-lg border border-white/20">
                        {displayBadge || item.tag}
                      </span>
                    </div>
                  </TiltCard>
                )}
              </div>

              {/* ── 说明侧：精炼信息架构与微卡片 ─────────────────── */}
              <div
                className={`lg:col-span-5 flex flex-col justify-center relative z-10 ${
                  isEven ? 'lg:order-1' : 'lg:order-2'
                }`}
              >
                {/* 序号与分类标牌 */}
                <div className="flex items-center gap-2.5 mb-2.5">
                  <span className="font-mono text-base font-bold text-gold tracking-widest">
                    {item.number}
                  </span>
                  <span className="w-5 h-px bg-gold/50" />
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-primary/25 bg-primary/5 text-primary text-xs font-serif font-medium tracking-wide">
                    <Icon className="w-3.5 h-3.5 text-primary" />
                    {item.tag}
                  </div>
                </div>

                {/* 场景主标题 */}
                <h2 className="text-2xl sm:text-3xl font-serif font-bold text-ink mb-1.5 leading-snug tracking-tight">
                  {item.title}
                </h2>

                {/* 副标题微标 */}
                <p className="text-[11px] font-mono tracking-wider text-gold font-medium mb-3 uppercase">
                  {item.subtitle}
                </p>

                {/* 精简导言：清晰自信，消除冗长 */}
                <p className="text-sm sm:text-[14.5px] leading-relaxed text-ink/80 mb-5 font-sans">
                  {item.summary}
                </p>

                {/* 结构化亮点微卡片 */}
                <div className="space-y-2 mb-6">
                  {item.badges.map((badge, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded-xl bg-white/70 backdrop-blur-xs border border-primary/10 hover:border-gold/50 hover:bg-white transition-all flex items-start gap-2.5"
                    >
                      <CheckCircle2 className="w-4 h-4 text-gold shrink-0 mt-0.5" />
                      <div>
                        <div className="font-serif font-bold text-xs text-ink">{badge.label}</div>
                        <div className="text-[11px] text-ink/65 leading-tight mt-0.5">
                          {badge.detail}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* 跳转操作按钮 */}
                <Link
                  to={item.to}
                  className="group inline-flex items-center gap-2 px-6 py-2.5 rounded-xl btn-chinese text-sm font-serif shadow-xs hover:shadow-md transition-all w-fit"
                >
                  <span>{item.cta}</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </Link>
              </div>
            </motion.article>
          );
        })}
      </div>

      {/* ── 底部创作旅程引导 ─────────────────────────────────────── */}
      <div className="mt-28 relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#FAF6F0] via-white to-[#F5ECE0] border border-gold/40 p-8 sm:p-12 text-center max-w-4xl mx-auto shadow-sm">
        <div className="absolute top-0 right-0 w-64 h-64 bg-gold/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-primary/10 rounded-full blur-3xl pointer-events-none" />

        <span className="inline-block text-xs font-serif text-primary/80 tracking-[0.25em] mb-2 uppercase">
          CREATIVE JOURNEY
        </span>
        <h3 className="font-serif text-2xl sm:text-3xl font-bold text-ink mb-3">
          开启你的传统文化智能创作之旅
        </h3>
        <p className="text-sm sm:text-base text-ink/70 max-w-xl mx-auto mb-8 font-sans">
          五大传统文化视觉语法已就绪，立即体验从创意输入、多模态生成、多维赏析到三维布展与文创转化的完整闭环。
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link
            to="/creator"
            className="inline-flex items-center gap-2 px-7 py-3 rounded-xl btn-chinese text-sm font-serif shadow-md hover:shadow-lg transition-all"
          >
            <span>立即体验生成</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            to="/heritage-gallery"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-primary/30 text-primary font-serif text-sm bg-white hover:bg-primary/5 transition-all shadow-xs"
          >
            漫游三维展馆
          </Link>
        </div>
      </div>
    </div>
  );
}
