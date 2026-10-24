import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import {
  ArrowRight,
  Eye,
  GraduationCap,
  Landmark,
  PenTool,
  ShoppingBag,
  Smartphone,
  Sparkles,
  CheckCircle2,
  Bookmark,
  Share2,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import creatorShot from '../../../docs/screenshots/creation-workspace.png';
import experienceShot from '../../../docs/interactive_v2/screens/exp-zxz-selected.png';
import cultureCardShot from '../../../docs/screenshots/culture-card.png';
import interiorShot from '../../../docs/screenshots/heritage-interior.png';
import productShot from '../../../docs/screenshots/creative-products.png';

type ScenarioTab = {
  id: string;
  label: string;
  shot: string;
  alt: string;
  badge?: string;
  isLive?: boolean;
};

type Scenario = {
  id: string;
  number: string;
  icon: LucideIcon;
  category: string;
  title: string;
  subtitle: string;
  status: 'live' | 'concept';
  statusText: string;
  desc: string;
  target: string;
  value: string;
  highlights: string[];
  to?: string;
  cta?: string;
  shot?: string;
  alt?: string;
  position?: 'center' | 'upper';
  tabs?: ScenarioTab[];
};

/**
 * 经过精炼去重后的 6 大代表性应用场景
 * 涵盖：空间展陈、美育研学、文创衍生、智能创作、多维导览、社交传播
 */
const SCENARIOS: Scenario[] = [
  {
    id: 'museum-exhibition',
    number: '01',
    icon: Landmark,
    category: '空间展陈 · 虚拟艺术',
    title: '沉浸式数字展陈与虚拟展馆',
    subtitle: '实体三维空间漫游 · 自由换画布展 · 展陈大屏呈现',
    status: 'live',
    statusText: '已上线 · 真实三维场景',
    desc: '纹脉华章两层中式三维展馆可直接作为数字化艺术展示空间。用户既可以在第一/第三人称视角下自由漫游，也能进入布展模式将作品挂入 15 处自定义画框、陈设 14 件传统器物道具，并支持昼夜光影切换与展陈大屏投影，免去传统复杂建模的高昂门槛。',
    target: '博物馆数字展厅 / 文化馆数字空间 / 校园美育展 / 线上开放日',
    value: '无需 3D 建模专业软件，一键将生成作品转化为可漫游、可布展的虚拟文化展厅。',
    highlights: ['两层中式空间自由漫游', '15 处画框与 14 件器物自定义陈设', '昼夜光影与灵宠伴游交互'],
    to: '/heritage-gallery',
    cta: '进入三维展馆',
    shot: interiorShot,
    alt: '纹脉展馆内景：画框、展柜与器物陈列',
    tabs: [
      {
        id: '3d-live',
        label: '3D 展馆实景',
        shot: interiorShot,
        alt: '纹脉展馆内景：画框、展柜与器物陈列',
        badge: '系统实景 · Three.js 展馆',
        isLive: true,
      },
      {
        id: 'screen-concept',
        label: '环幕展陈大屏',
        shot: import.meta.env.BASE_URL + 'scenarios/museum-screen-concept.jpg',
        alt: '现代顶级美术馆沉浸式数字艺术展厅全景（宋画青绿山水）',
        badge: '空间展陈构想 · 超高清环幕',
        isLive: false,
      },
    ],
  },
  {
    id: 'heritage-education',
    number: '02',
    icon: GraduationCap,
    category: '美育教学 · 非遗研学',
    title: '非遗活化与现代美育教学',
    subtitle: '工艺特征解构 · 同主题多风格对比 · 结构化文化卡',
    status: 'live',
    statusText: '已上线 · 课件化工具',
    desc: '将朱仙镇年画、汴绣、宋画青绿山水、青花瓷与剪纸的色彩、构图、线条特征转化为结构化教学资源。课堂上可引导学生以同一文化主题（如“春日生机”）分别生成不同风格作品进行并排比对，结合本地视觉大模型生成的 CultureCard 深入剖析非遗技艺渊源。',
    target: '高校艺术设计专业 / 中小学美术素养课堂 / 非遗研学营地 / 文化普及讲座',
    value: '让传统视觉风格可分解、可生成、可对比讲解，使传统美育教学生动有趣。',
    highlights: ['五大风格结构化视觉特征', '同一主题并排多风格比对', '双语 CultureCard 工艺背景解析'],
    to: '/styles',
    cta: '浏览风格知识库',
    shot: cultureCardShot,
    alt: '文化说明卡：视觉解读、风格来源与工艺要点',
  },
  {
    id: 'creative-products',
    number: '03',
    icon: ShoppingBag,
    category: '文创衍生 · 载体打样',
    title: '文旅文创衍生与载体打样',
    subtitle: '8 类预设载体映射 · 实时排版效果 · 高清打样导出',
    status: 'live',
    statusText: '已上线 · 实时渲染导出',
    desc: '彻底打通从文化画作到实体衍生品的链路。系统内置文旅明信片、数字海报、帆布袋、文创书签、陶瓷杯垫、景区纪念票等 8 类预设文创载体，按各载体物理比例智能排版并模拟材质光影，支持一键导出 1600×1200 像素的高清效果图，大幅降低文创前期试错与打样成本。',
    target: '景区文创设计工坊 / 校园文化周边 / 地方文旅部门 / 独立设计师',
    value: '从单张文化作品到全套文创系列仅需数秒，打样前快速验证视觉效果。',
    highlights: ['8 类生活美学与景区纪念载体', '符合载体比例的自适应排版', '1600×1200 高清效果图导出'],
    to: '/products',
    cta: '进入文创转化工坊',
    shot: productShot,
    alt: '文创转化工坊：多载体排版与效果预览',
    position: 'upper',
    tabs: [
      {
        id: 'studio-live',
        label: '工坊实时排版',
        shot: productShot,
        alt: '文创转化工坊：多载体排版与效果预览',
        badge: '系统功能 · 8 类载体打样',
        isLive: true,
      },
      {
        id: 'box-concept',
        label: '年画伴手礼盒',
        shot: import.meta.env.BASE_URL + 'scenarios/product-package-concept.jpg',
        alt: '朱仙镇年画瑞猫节庆礼盒与利是封包装打样',
        badge: '国潮包装概念 · 烫金起鼓',
        isLive: false,
      },
      {
        id: 'coaster-concept',
        label: '青花茶席杯垫',
        shot: import.meta.env.BASE_URL + 'scenarios/product-coaster-lifestyle.jpg',
        alt: '青花瓷缠枝纹吸水杯垫与生活美学茶席',
        badge: '生活器物概念 · 新中式茶道',
        isLive: false,
      },
      {
        id: 'embroidery-concept',
        label: '汴绣真丝团扇',
        shot: import.meta.env.BASE_URL + 'scenarios/product-embroidery-lifestyle.jpg',
        alt: '宋代汴绣双面绣丝绸真丝团扇与长巾',
        badge: '丝织非遗概念 · 劈丝刺绣',
        isLive: false,
      },
    ],
  },
  {
    id: 'creative-studio',
    number: '04',
    icon: PenTool,
    category: '智能创作 · 个人工坊',
    title: '文化主题智能创作工坊',
    subtitle: '主题 + 参考图双驱动 · 风格强度可控 · 作品自动落盘',
    status: 'live',
    statusText: '已上线 · Qwen 3.0 链路',
    desc: '面向个人创作者与设计工作者的轻量化工作台。用户只需输入创作主题，可按需上传构图参考图，选择风格影响强度（0% ~ 100%）并补充正负向提示词。生成结果真实回报参考图参与推理的状态证据，成图、原图与元数据自动保存落盘，并在展厅构建全套互动。',
    target: '设计类学生作业 / 文化内容创作者 / 传统文化爱好者 / 概念设计师',
    value: '零代码降低文化艺术创作门槛，同时为专业创作者保留参数级微调掌控力。',
    highlights: ['阿里百炼 Qwen Image 3.0', '多模态参考图双驱动', '自动落盘入库与全生命周期追踪'],
    to: '/creator',
    cta: '打开生成工作台',
    shot: creatorShot,
    alt: '智能生成工作台：主题输入、参考图与风格参数',
    position: 'upper',
  },
  {
    id: 'interactive-guide',
    number: '05',
    icon: Eye,
    category: '互动赏析 · 深度导览',
    title: '多维交互深度赏析与文化导览',
    subtitle: '画中有话 · 一图一境 · 画境漫游 2.5D 入画',
    status: 'live',
    statusText: '已上线 · 离线可赏析',
    desc: '彻底告别走马观花式的静态看画。同一件作品提供三种深层交互体验：在「画中有话」中点击微观热点探索笔墨线索；在「一图一境」中顺着三折图文长卷品味文化传承；在「画境漫游」中借助 2.5D 分层深度着色器推镜入画，实现视角与焦点的动态交互。',
    target: '特展现场数字扫码导览 / 展馆互动触控屏 / 课前自主研读 / 公众文化普及',
    value: '把传统艺术品转化为层次丰富、有探究路径的互动叙事，离线环境亦可畅享。',
    highlights: ['热点微观视觉解读', '三折图文阅读长卷', '2.5D 深度视差漫游体验'],
    to: '/experience/zhuxianzhen-ruimao',
    cta: '体验画中有话',
    shot: experienceShot,
    alt: '画中有话：朱仙镇年画热点解读界面',
  },
  {
    id: 'social-dissemination',
    number: '06',
    icon: Smartphone,
    category: '文博传播 · 社交分享',
    title: '文博数字化线上传播与社交分享',
    subtitle: '移动端沉浸适配 · 视觉卡片社交传播 · 文博破圈触达',
    status: 'concept',
    statusText: '应用构想 · 视觉示意',
    desc: '探索数字文化资产在当代移动社交环境中的传播范式。通过定制符合手机竖屏浏览体验的数字文化海报、微信朋友圈分享图、小红书图文模板等，结合平台自动生成的文化解说要点，让年轻人以更轻量、更高颜值的形式在社交圈分享中国传统文化审美。',
    target: '青年传统文化社群 / 文博新媒体运营 / 传统节日社交分享 / 校园文化传播',
    value: '赋予传统文化更符合当代数字媒介的视觉形态，助力优秀传统文化破圈传播。',
    highlights: ['符合手机竖屏黄金视角的视觉规范', '文化卡与社交图文模板设计', '轻量化无门槛的社交裂变模式'],
    to: '/styles',
    cta: '查看视觉风格素材',
    shot: import.meta.env.BASE_URL + 'scenarios/social-mobile-concept.jpg',
    alt: '极简智能手机展示宋代汝窑天青釉文化知识日签卡',
  },
];

export default function Scenarios() {
  const shouldReduceMotion = useReducedMotion();
  const [activeTabs, setActiveTabs] = useState<Record<string, string>>({
    'museum-exhibition': '3d-live',
    'creative-products': 'studio-live',
  });

  return (
    <div className="max-w-7xl mx-auto px-6 py-12 md:py-20 lg:py-24">
      {/* ── 页面标题区 ──────────────────────────────────────────── */}
      <header className="mb-20 text-center max-w-4xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-primary/20 bg-primary/5 text-primary text-xs md:text-sm font-medium mb-5">
          <Sparkles className="w-4 h-4 text-gold" />
          场景赋能 · 价值闭环
        </div>
        <h1 className="text-4xl sm:text-5xl font-serif font-bold text-ink mb-6 leading-tight">
          应用场景与文化实践
        </h1>
        <p className="text-base sm:text-lg text-ink/70 leading-relaxed font-sans">
          从三维虚拟展馆、美育教学研学、文创衍生打样，到个人智能创作工坊、多维深度导览与社交媒体传播。
          <span className="text-primary font-medium"> 纹脉华章 </span>
          不仅是一套创作工具，更是让传统文化视觉语言融入当代多元生活的数字化桥梁。
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3 text-xs text-ink/60">
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white border border-gold/30 shadow-xs">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            5 大场景真实上线运行
          </span>
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white border border-primary/20 shadow-xs">
            <Bookmark className="w-3.5 h-3.5 text-primary" />
            1 项文博社交传播构想
          </span>
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white border border-gold/30 shadow-xs">
            <Share2 className="w-3.5 h-3.5 text-gold" />
            完整支持桌面与移动端浏览
          </span>
        </div>
      </header>

      {/* ── 纵向交错长廊：每组占满一行，滚动逐组浮现 ────────────── */}
      <div className="space-y-24 md:space-y-32">
        {SCENARIOS.map((item, index) => {
          const isEven = index % 2 === 0;
          const Icon = item.icon;
          const activeTabId = activeTabs[item.id] || (item.tabs ? item.tabs[0].id : '');
          const currentTab = item.tabs?.find((t) => t.id === activeTabId) || item.tabs?.[0];
          const displayShot = currentTab?.shot || item.shot;
          const displayAlt = currentTab?.alt || item.alt || item.title;
          const displayBadge = currentTab?.badge || (item.status === 'live' ? '实景运行 · 系统界面' : '应用构想 · 视觉示意');

          return (
            <motion.article
              key={item.id}
              initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              className={`grid lg:grid-cols-12 gap-8 lg:gap-14 items-center ${
                isEven ? '' : 'lg:grid-flow-dense'
              }`}
            >
              {/* ── 图片侧展示 ────────────────────────────────────── */}
              <div
                className={`lg:col-span-7 ${
                  isEven ? 'lg:order-2' : 'lg:order-1'
                }`}
              >
                <div className="group relative aspect-[16/10] overflow-hidden rounded-2xl border-2 border-white/90 shadow-xl bg-[#F7F4EE]">
                  {/* 可交互切换标签（若该场景提供多维度实景 / 样机对比） */}
                  {item.tabs && (
                    <div className="absolute top-3 left-3 right-3 sm:right-auto z-30 flex flex-wrap items-center gap-1.5 p-1 rounded-xl bg-black/60 backdrop-blur-md border border-white/20 shadow-lg">
                      {item.tabs.map((tab) => {
                        const isSelected = tab.id === activeTabId;
                        return (
                          <button
                            key={tab.id}
                            type="button"
                            onClick={() => setActiveTabs((prev) => ({ ...prev, [item.id]: tab.id }))}
                            className={`px-2.5 py-1 rounded-lg text-xs font-serif transition-all cursor-pointer ${
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
                    <div className="absolute top-3.5 left-3.5 z-20 px-3 py-1 rounded-xl bg-black/60 backdrop-blur-md border border-white/20 shadow-lg text-xs font-serif text-white/95">
                      文化日签 · 汝窑天青釉
                    </div>
                  )}

                  {displayShot && (
                    <img
                      src={displayShot}
                      alt={displayAlt}
                      className={`w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.03] ${
                        item.position === 'upper' && !item.tabs ? 'object-top' : 'object-center'
                      }`}
                      loading="lazy"
                    />
                  )}

                  {/* 悬停光晕与状态角标 */}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent pointer-events-none"></div>
                  <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between text-white text-xs z-20">
                    <span className="font-serif tracking-wider bg-black/55 backdrop-blur-md px-3 py-1 rounded-md border border-white/20">
                      {displayBadge}
                    </span>
                    <span className="font-mono text-[11px] text-white/80 hidden sm:inline bg-black/40 backdrop-blur-xs px-2 py-0.5 rounded">
                      SCENARIO {item.number}
                    </span>
                  </div>
                </div>
              </div>

              {/* ── 文字说明侧 ────────────────────────────────────── */}
              <div
                className={`lg:col-span-5 flex flex-col justify-center ${
                  isEven ? 'lg:order-1' : 'lg:order-2'
                }`}
              >
                {/* 序号与分类 */}
                <div className="flex items-center gap-3 mb-3">
                  <span className="font-mono text-sm font-bold text-gold tracking-widest">
                    {item.number}
                  </span>
                  <span className="w-8 h-px bg-gold/40"></span>
                  <div className="inline-flex items-center gap-1.5 text-xs font-serif font-medium text-primary">
                    <Icon className="w-3.5 h-3.5 text-primary" />
                    {item.category}
                  </div>
                  <span
                    className={`ml-auto text-[10.5px] px-2.5 py-0.5 rounded-full font-medium ${
                      item.status === 'live'
                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        : 'bg-amber-50 text-amber-800 border border-amber-200'
                    }`}
                  >
                    {item.statusText}
                  </span>
                </div>

                {/* 标题与副标题 */}
                <h2 className="text-2xl sm:text-3xl font-serif font-bold text-ink mb-2 leading-tight">
                  {item.title}
                </h2>
                <p className="text-xs sm:text-sm font-serif text-primary/85 mb-4">
                  {item.subtitle}
                </p>

                {/* 正文详细描述 */}
                <p className="text-sm sm:text-[15px] leading-relaxed text-ink/75 mb-6 font-sans">
                  {item.desc}
                </p>

                {/* 特性要点 */}
                <div className="space-y-2 mb-6">
                  {item.highlights.map((point, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-xs sm:text-sm text-ink/80">
                      <span className="w-1.5 h-1.5 rounded-full bg-gold mt-1.5 shrink-0"></span>
                      <span>{point}</span>
                    </div>
                  ))}
                </div>

                {/* 适用对象与价值 */}
                <div className="p-4 rounded-xl bg-primary/5 border border-primary/10 mb-6 text-xs leading-relaxed space-y-1.5">
                  <div>
                    <span className="font-bold text-ink/90 font-serif">适用对象：</span>
                    <span className="text-ink/70">{item.target}</span>
                  </div>
                  <div>
                    <span className="font-bold text-ink/90 font-serif">核心价值：</span>
                    <span className="text-primary font-medium">{item.value}</span>
                  </div>
                </div>

                {/* 跳转操作按钮 */}
                {item.to && (
                  <Link
                    to={item.to}
                    className="group inline-flex items-center gap-2 px-6 py-3 rounded-xl btn-chinese text-sm font-serif shadow-xs hover:shadow-md transition-all w-fit"
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
      <div className="mt-28 p-8 md:p-12 rounded-3xl bg-gradient-to-r from-primary/10 via-gold/10 to-primary/5 border border-primary/20 text-center max-w-4xl mx-auto shadow-xs">
        <h3 className="font-serif text-2xl font-bold text-ink mb-3">
          开启你的传统文化智能创作之旅
        </h3>
        <p className="text-sm text-ink/70 max-w-xl mx-auto mb-6">
          五大传统文化视觉风格已就绪，立即体验从创意输入、多模态智能生成到三维展馆布展的完整流程。
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
            to="/gallery"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-primary/30 text-primary font-serif text-sm bg-white hover:bg-primary/5 transition-all"
          >
            浏览作品展厅
          </Link>
        </div>
      </div>
    </div>
  );
}
