import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import {
  ArrowRight,
  Compass,
  Frame,
  MonitorPlay,
  GraduationCap,
  Palette,
  Layers,
  FileText,
  ShoppingBag,
  Package,
  Coffee,
  Scissors,
  PenTool,
  Sparkles,
  SlidersHorizontal,
  ShieldCheck,
  Eye,
  Search,
  Scroll,
  Move3d,
  Smartphone,
  Share2,
  Flame,
  type LucideIcon,
} from 'lucide-react';

import creatorShot from '../../../docs/screenshots/creation-workspace.png';
import experienceShot from '../../../docs/interactive_v2/screens/exp-zxz-selected.png';
import cultureCardShot from '../../../docs/screenshots/culture-card.png';
import interiorShot from '../../../docs/screenshots/heritage-interior.png';
import productShot from '../../../docs/screenshots/creative-products.png';
import wanderShot from '../../../docs/screenshots/vnext/wander.jpg';
import storyShot from '../../../docs/screenshots/vnext/story.jpg';

type FeatureItem = {
  icon: LucideIcon;
  title: string;
  desc: string;
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
  summary: string;
  features: FeatureItem[];
  to?: string;
  cta?: string;
  shot?: string;
  alt?: string;
  tabs?: ScenarioTab[];
};

/**
 * 经过精炼重构的 6 大应用场景
 * 视觉突出、文字精炼、层次分明、动效生动
 */
const SCENARIOS: Scenario[] = [
  {
    id: 'museum-exhibition',
    number: '01',
    icon: MonitorPlay,
    tag: '空间展陈',
    title: '三维数字展馆与空间展陈',
    summary:
      '为传统文化艺术构筑可漫游、可布展的中式三维虚拟美术馆。既能在两层实体建筑中换画布展，亦可全景投映至现代艺术馆超宽曲面大屏，实现虚拟沉浸与实体策展的交融。',
    features: [
      {
        icon: Compass,
        title: '双层空间漫游',
        desc: '第一/第三人称自由穿行，中式梁架格局与昼夜光影流转。',
      },
      {
        icon: Frame,
        title: '自由换画布展',
        desc: '15 处自定义画框一键陈列，14 件传统器物随心布置。',
      },
      {
        icon: MonitorPlay,
        title: '环幕空间映射',
        desc: '支持曲面超高清数字展厅投影，营造只此青绿的沉浸场域。',
      },
    ],
    to: '/heritage-gallery',
    cta: '探索三维展馆',
    tabs: [
      {
        id: 'screen-concept',
        label: '环幕空间展陈',
        shot: import.meta.env.BASE_URL + 'scenarios/museum-screen-concept.jpg',
        alt: '现代顶级美术馆沉浸式数字艺术展厅全景（宋画青绿山水）',
        badge: '数字展陈空间构想',
      },
      {
        id: '3d-live',
        label: '3D 展馆实景',
        shot: interiorShot,
        alt: '纹脉展馆内景：画框、展柜与器物陈列',
        badge: 'Three.js 虚拟空间实景',
      },
    ],
  },
  {
    id: 'heritage-education',
    number: '02',
    icon: GraduationCap,
    tag: '美育研学',
    title: '非遗活化与现代美育研学',
    summary:
      '将朱仙镇年画、汴绣、宋画、青花瓷与剪纸五大非遗的构图、配色与线条特征转化为结构化教学资源。课堂上一键同题多风格生成并排比对，结合结构化文化卡深度解析工艺脉络。',
    features: [
      {
        icon: Palette,
        title: '五大非遗解构',
        desc: '提取传统设色、版刻墨线与针法经纬，建立可视美育知识库。',
      },
      {
        icon: Layers,
        title: '同题多维比对',
        desc: '同一文化主题并排生成多种风格作品，直观讲解流变传承。',
      },
      {
        icon: FileText,
        title: '双语研学知识卡',
        desc: '深度解析作品工艺背景与文化典故，一键导出 CultureCard。',
      },
    ],
    to: '/styles',
    cta: '查阅风格知识库',
    tabs: [
      {
        id: 'card-view',
        label: '研学知识卡',
        shot: cultureCardShot,
        alt: '文化说明卡：视觉解读、风格来源与工艺要点',
        badge: '结构化美育课件工具',
      },
      {
        id: 'fan-view',
        label: '非遗实物典藏',
        shot: import.meta.env.BASE_URL + 'scenarios/product-embroidery-lifestyle.jpg',
        alt: '宋代汴绣双面绣丝绸真丝团扇与长巾',
        badge: '宋韵汴绣实物打样',
      },
    ],
  },
  {
    id: 'creative-products',
    number: '03',
    icon: ShoppingBag,
    tag: '生活美学',
    title: '文博衍生与实体器物打样',
    summary:
      '打通从数字文化画作到生活实物美学的完整链路。内置 8 类文创载体物理比例，从节日伴手礼盒到日常茶道器物，智能排版材质光影并导出 1600×1200 高清打样图。',
    features: [
      {
        icon: Package,
        title: '节庆礼盒包装',
        desc: '年画瑞猫图腾融入烫金起鼓特种纸礼盒，重塑国潮节日伴手礼。',
      },
      {
        icon: Coffee,
        title: '茶席生活器物',
        desc: '青花瓷缠枝纹样映射吸水杯垫与瓷碗，自然融入当代茶道美学。',
      },
      {
        icon: Scissors,
        title: '真丝非遗织造',
        desc: '汴绣双面绣丝绸团扇与长巾打样，呈现平齐顺畅的丝光质感。',
      },
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
        label: '工坊实时排版',
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
    summary:
      '专为东方美学打造的多模态可控生成工作台。支持创作主题与参考图双驱动，通过风格强度滑块自由调配传统基因渗透度，生成结果真实记录证据哈希并自动归档入库。',
    features: [
      {
        icon: Sparkles,
        title: 'Qwen 3.0 美学底座',
        desc: '阿里百炼多模态可控图像生成，纯正东方色彩与传统造型语法。',
      },
      {
        icon: SlidersHorizontal,
        title: '风格强度自由控',
        desc: '0% ~ 100% 细粒度调节风格影响度，兼顾构图自由与流派辨识度。',
      },
      {
        icon: ShieldCheck,
        title: '哈希证据全生命周期',
        desc: '原图与成图 SHA-256 存证防伪，成图元数据自动入库落盘。',
      },
    ],
    to: '/creator',
    cta: '打开生成工作台',
    shot: creatorShot,
    alt: '智能生成工作台：主题输入、参考图与风格参数',
  },
  {
    id: 'interactive-guide',
    number: '05',
    icon: Eye,
    tag: '深度导览',
    title: '多维交互深度赏析与文化导览',
    summary:
      '告别走马观花式的静态看画。通过“微观热点探索”、“三折长卷读史”与“2.5D 推镜入画”三种递进交互体验，让同一件传统艺术品绽放出立体多维的互动叙事魅力。',
    features: [
      {
        icon: Search,
        title: '画中有话微观探秘',
        desc: '点击画面隐秘热点，逐笔探寻线条神韵、历史典故与民俗寓意。',
      },
      {
        icon: Scroll,
        title: '一图一境长卷叙事',
        desc: '三折图文长卷随手势平滑延展，步步深入领略文脉传承历程。',
      },
      {
        icon: Move3d,
        title: '2.5D 深度视差漫游',
        desc: '独创分层深度着色器，随视角微移推镜入画，实现沉浸式游历。',
      },
    ],
    to: '/experience/zhuxianzhen-ruimao',
    cta: '体验深度赏析',
    tabs: [
      {
        id: 'hotspot-view',
        label: '画中有话 · 热点',
        shot: experienceShot,
        alt: '画中有话：朱仙镇年画热点解读界面',
        badge: '微观热点视觉解读',
      },
      {
        id: 'story-view',
        label: '一图一境 · 长卷',
        shot: storyShot,
        alt: '一图一境：三折图文长卷阅读界面',
        badge: '三折图文阅读长卷',
      },
      {
        id: 'wander-view',
        label: '画境漫游 · 2.5D',
        shot: wanderShot,
        alt: '画境漫游：2.5D 分层深度视差漫游界面',
        badge: '2.5D 深度视差漫游',
      },
    ],
  },
  {
    id: 'social-dissemination',
    number: '06',
    icon: Smartphone,
    tag: '文博破圈',
    title: '数字文博线上传播与社交日签',
    summary:
      '探索东方传统美学在当代青年移动社交生态中的传播范式。定制符合手机竖屏沉浸视域的文化日签卡与朋友圈图文模板，以更纯粹、高颜值的形式唤醒大众东方审美共鸣。',
    features: [
      {
        icon: Smartphone,
        title: '移动竖屏沉浸美学',
        desc: '专为手机黄金视域定制的高级日签海报，东方禅意与现代科技共生。',
      },
      {
        icon: Share2,
        title: '轻量社交图文裂变',
        desc: '结构化提炼非遗知识短篇，便于在小红书、微信等社交平台分享。',
      },
      {
        icon: Flame,
        title: '青年潮流文化破圈',
        desc: '褪去传统文博的刻板说教，让传统雅器与经典纹样成为审美日课。',
      },
    ],
    to: '/styles',
    cta: '查阅视觉风格库',
    shot: import.meta.env.BASE_URL + 'scenarios/social-mobile-concept.jpg',
    alt: '极简智能手机展示宋代汝窑天青釉文化知识日签卡',
  },
];

export default function Scenarios() {
  const shouldReduceMotion = useReducedMotion();
  const [activeTabs, setActiveTabs] = useState<Record<string, string>>({
    'museum-exhibition': 'screen-concept',
    'heritage-education': 'card-view',
    'creative-products': 'box-concept',
    'interactive-guide': 'hotspot-view',
  });

  return (
    <div className="max-w-7xl mx-auto px-6 py-12 md:py-20 lg:py-24">
      {/* ── 页面标题区 ──────────────────────────────────────────── */}
        <header className="mb-20 md:mb-28 text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-primary/20 bg-primary/5 text-primary text-xs md:text-sm font-medium mb-5 shadow-xs">
            <Sparkles className="w-3.5 h-3.5 text-gold" />
            东方意境 · 当代新生
          </div>
          <h1 className="text-4xl sm:text-5xl font-serif font-bold text-ink mb-5 leading-tight tracking-tight">
            文脉化境 · 多维应用场景
          </h1>
          <p className="text-base sm:text-lg text-ink/75 leading-relaxed font-sans">
            融古典艺术之美，入当代生活之境。从虚实相生的三维展陈、格物致知的美育研学，到器物焕新的文创打样与移动传播。
          </p>
        </header>

        {/* ── 纵向交错长廊：每组占满一行，滚动逐组浮现 ────────────── */}
        <div className="space-y-28 md:space-y-36">
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
                key={item.id}
                initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: 35 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-60px' }}
                transition={{ duration: 0.7, ease: 'easeOut' }}
                className={`relative grid lg:grid-cols-12 gap-8 lg:gap-14 items-center ${
                  isEven ? '' : 'lg:grid-flow-dense'
                }`}
              >
                {/* ── 背景大号宣纸水印编号 ──────────────────────────── */}
                <div
                  className={`absolute -top-12 font-serif font-black text-8xl lg:text-9xl text-gold/10 select-none pointer-events-none z-0 hidden sm:block ${
                    isEven ? 'right-4' : 'left-4'
                  }`}
                >
                  {item.number}
                </div>

                {/* ── 图片侧展示 ────────────────────────────────────── */}
                <div
                  className={`lg:col-span-7 relative z-10 ${
                    isEven ? 'lg:order-2' : 'lg:order-1'
                  }`}
                >
                  <div className="group relative aspect-[16/10] overflow-hidden rounded-2xl sm:rounded-3xl border border-white/80 shadow-xl bg-[#F7F4EE]">
                    {/* 可交互切换标签（若该场景提供多维度实景 / 样机对比） */}
                    {item.tabs && (
                      <div className="absolute top-3.5 left-3.5 right-3.5 sm:right-auto z-30 flex flex-wrap items-center gap-1.5 p-1 rounded-xl bg-black/60 backdrop-blur-md border border-white/20 shadow-lg">
                        {item.tabs.map((tab) => {
                          const isSelected = tab.id === activeTabId;
                          return (
                            <button
                              key={tab.id}
                              type="button"
                              onClick={() => setActiveTabs((prev) => ({ ...prev, [item.id]: tab.id }))}
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

                    {/* 针对社交传播日签卡的浮动标签 */}
                    {!item.tabs && item.id === 'social-dissemination' && (
                      <div className="absolute top-3.5 left-3.5 z-20 px-3.5 py-1.5 rounded-xl bg-black/60 backdrop-blur-md border border-white/20 shadow-lg text-xs font-serif text-white/95">
                        文化日签 · 汝窑天青釉
                      </div>
                    )}

                    {displayShot && (
                      <img
                        src={displayShot}
                        alt={displayAlt}
                        className="w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.03]"
                        loading="lazy"
                      />
                    )}

                    {/* 悬停光晕与状态角标 */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-transparent to-transparent pointer-events-none"></div>
                    <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between text-white text-xs z-20">
                      {displayBadge ? (
                        <span className="font-serif tracking-wider bg-black/55 backdrop-blur-md px-3 py-1 rounded-md border border-white/20">
                          {displayBadge}
                        </span>
                      ) : (
                        <span className="font-serif tracking-wider bg-black/55 backdrop-blur-md px-3 py-1 rounded-md border border-white/20">
                          {item.tag}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* ── 文字说明侧 ────────────────────────────────────── */}
                <div
                  className={`lg:col-span-5 flex flex-col justify-center relative z-10 ${
                    isEven ? 'lg:order-1' : 'lg:order-2'
                  }`}
                >
                  {/* 序号与分类 */}
                  <div className="flex items-center gap-3 mb-3">
                    <span className="font-mono text-base font-bold text-gold tracking-widest">
                      {item.number}
                    </span>
                    <span className="w-6 h-px bg-gold/40"></span>
                    <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-primary/20 bg-primary/5 text-primary text-xs font-serif font-medium tracking-wide">
                      <Icon className="w-3.5 h-3.5 text-primary" />
                      {item.tag}
                    </div>
                  </div>

                  {/* 标题 */}
                  <h2 className="text-2xl sm:text-3xl lg:text-[32px] font-serif font-bold text-ink mb-3 leading-snug tracking-tight">
                    {item.title}
                  </h2>

                  {/* 核心导言 */}
                  <p className="text-sm sm:text-[15px] leading-relaxed text-ink/75 mb-6 font-sans">
                    {item.summary}
                  </p>

                  {/* 三大特性徽章微卡片 */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-7">
                    {item.features.map((feat, idx) => {
                      const FeatIcon = feat.icon;
                      return (
                        <div
                          key={idx}
                          className="group/card relative p-3.5 rounded-xl bg-white/75 backdrop-blur-xs border border-primary/10 hover:border-gold/50 hover:bg-white hover:shadow-md transition-all duration-300 flex flex-col justify-between"
                        >
                          <div className="flex items-center gap-2 mb-1.5">
                            <div className="w-7 h-7 rounded-lg bg-primary/5 text-primary flex items-center justify-center shrink-0 group-hover/card:bg-primary group-hover/card:text-white transition-colors duration-300">
                              <FeatIcon className="w-3.5 h-3.5" />
                            </div>
                            <h4 className="font-serif font-bold text-xs sm:text-[13px] text-ink leading-tight">
                              {feat.title}
                            </h4>
                          </div>
                          <p className="text-[11px] leading-relaxed text-ink/65 line-clamp-2">
                            {feat.desc}
                          </p>
                        </div>
                      );
                    })}
                  </div>

                  {/* 跳转操作按钮 */}
                  {item.to && (
                    <Link
                      to={item.to}
                      className="group inline-flex items-center gap-2 px-6 py-2.5 rounded-xl btn-chinese text-sm font-serif shadow-xs hover:shadow-md transition-all w-fit"
                    >
                      <span>{item.cta}</span>
                      <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                    </Link>
                  )}
                </div>
              </motion.article>
            );
          })}
        </div>

        {/* ── 底部探索引导 ─────────────────────────────────────────── */}
        <div className="mt-28 relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#FAF6F0] via-white to-[#F5ECE0] border border-gold/40 p-8 sm:p-12 text-center max-w-4xl mx-auto shadow-sm">
          <div className="absolute top-0 right-0 w-64 h-64 bg-gold/10 rounded-full blur-3xl pointer-events-none"></div>
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-primary/10 rounded-full blur-3xl pointer-events-none"></div>

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
