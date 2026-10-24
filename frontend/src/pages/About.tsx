import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import {
  ArrowRight,
  Boxes,
  BookOpen,
  Code2,
  Cpu,
  Database,
  Eye,
  Layers,
  Palette,
  Server,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Compass,
  Monitor,
  Layout,
  ExternalLink,
} from 'lucide-react';
import { STYLES } from '../data/styleLibrary';

import creatorShot from '../../../docs/screenshots/creation-workspace.png';
import galleryShot from '../../../docs/screenshots/gallery.png';
import experienceShot from '../../../docs/screenshots/interactive-artwork.png';
import storyShot from '../../../docs/screenshots/story-reading.png';
import wanderShot from '../../../docs/screenshots/painting-world.png';
import heritageExterior from '../../../docs/screenshots/vnext/gallery-exterior.jpg';
import heritageInterior from '../../../docs/screenshots/heritage-interior.png';
import productShot from '../../../docs/screenshots/creative-products.png';
import cultureCardShot from '../../../docs/screenshots/culture-card.png';

/**
 * 架构分层数据定义
 */
type ArchLayer = 'frontend' | 'backend' | 'ai' | 'storage';

interface ArchItem {
  id: ArchLayer;
  title: string;
  subtitle: string;
  icon: typeof Server;
  desc: string;
  technologies: { name: string; role: string; badge: string }[];
  boundaryNote: string;
}

const ARCH_LAYERS: ArchItem[] = [
  {
    id: 'frontend',
    title: '前端呈现与交互体系',
    subtitle: 'Frontend Presentation & 3D Interactive Core',
    icon: Layout,
    desc: '基于 React 19、TypeScript 与 Vite 架构，结合 Tailwind CSS 与 Motion 构建富有中国传统美学的响应式界面。三维纹脉展馆采用 Three.js 与 React Three Fiber 独立渲染，画境漫游采用基于自定义 GLSL 着色器的 2.5D 深度视差分层渲染引擎。',
    technologies: [
      { name: 'React 19 + TypeScript', role: '核心组件系统与强类型数据链路', badge: '正式' },
      { name: 'Tailwind CSS + Motion', role: '中式文化美学设计系统与流畅微动效', badge: '正式' },
      { name: 'Three.js / React Three Fiber', role: '纹脉展馆双层建筑与器物布展引擎', badge: '正式' },
      { name: 'GLSL Custom Shader', role: '画境漫游伪深度与分层视差摄像机渲染', badge: '正式' },
    ],
    boundaryNote: '画境漫游基于深度图与前景分割实现 2.5D 视差推镜效果，并非对画作进行完整三维实景摄影测量建模；三维展馆为 WebGL 虚拟空间，非线下博物馆实景孪生系统。',
  },
  {
    id: 'backend',
    title: '后端服务与任务流水线',
    subtitle: 'Backend Services & Persistent Job Pipelines',
    icon: Server,
    desc: '基于 Python 3.12 与 FastAPI 构建轻量化高性能服务端。提供图像生成转发、本地大模型视觉分析、作品持久化存储（Case Store）以及异步互动资源构建流水线（Interactive Jobs）。',
    technologies: [
      { name: 'FastAPI + Uvicorn', role: '异步高吞吐 API 服务与跨域中继', badge: '正式' },
      { name: 'Case Store (Local)', role: '生成结果、原图、成图与元数据自动落盘入库', badge: '正式' },
      { name: 'Interactive Jobs', role: '自动构建画中有话、一图一境与画境漫游数据', badge: '正式' },
      { name: 'Prompt Builder', role: '文化风格结构化语法注入与权重约束构建', badge: '正式' },
    ],
    boundaryNote: '系统采用本地文件持久化元数据管理，不依赖外部大型关系型数据库或云端托管账户系统，保障本地单机可完整便携交付与离线运行。',
  },
  {
    id: 'ai',
    title: 'AI 多模态大模型矩阵',
    subtitle: 'Multi-Modal Foundation Models & Local Vision',
    icon: Cpu,
    desc: '采用「云端多模态图像生成 + 本地轻量化视觉大模型解读」的混合 AI 协同架构。云端对接阿里云百炼官方 Qwen Image 3.0，本地部署 Ollama Qwen3-VL 4B 视觉多模态模型，兼顾生成品质与隐私可控性。',
    technologies: [
      { name: 'Qwen Image 3.0 (DashScope)', role: '文本主题 + 参考图 + 风格约束双驱动图像生成', badge: '云端 API' },
      { name: 'Qwen3-VL:4b (Ollama Local)', role: '本地自动化视觉特征提取、文化意涵解读与文化卡生成', badge: '本地推理' },
      { name: 'DashScope Wanx (Fallback)', role: '通义万相云端图像备用生成支持', badge: '备用' },
      { name: 'Rule-based Template Engine', role: 'AI 服务未配置或离线时的优雅回退兜底', badge: '离线兜底' },
    ],
    boundaryNote: '本项目直接调用通义千问官方 Qwen Image 3.0 与 Qwen3-VL 开源权重，未声称自研或全参数微调基础大模型。Prompt Visual Features 来自项目团队对非遗文献与代表作的人工结构化提炼。',
  },
  {
    id: 'storage',
    title: '资产组织与离线闭环',
    subtitle: 'Asset Management & Offline Delivery Loop',
    icon: Database,
    desc: '所有内置作品、文化说明卡、三维展馆模型（GLB）、互动绘卷分层图（WebP）均经过编译期打包与本地校验。即使在无公网网络或无 API 密钥的环境下，用户仍可完整浏览五大风格、作品展厅、三维展馆与全部互动赏析功能。',
    technologies: [
      { name: 'GLB 3D Assets', role: 'Blender 烘焙并优化的中式两层展馆及 14 件器物道具', badge: '本地资产' },
      { name: 'WebP Multi-layer Maps', role: '互动赏析的分层剪影、前景切片与深度预览纹理', badge: '本地资产' },
      { name: 'Vite Glob & Assets', role: '静态资源指纹打包与统一相对路径分发', badge: '构建规范' },
      { name: 'SHA-256 Evidence Tracking', role: '作品与参考图哈希校验与真实生成证据追溯', badge: '防伪审计' },
    ],
    boundaryNote: '演示作品均为项目真实流水线在 2026 年生成并归档的真实输出，未用非真实概念图冒充生成结果，各项素材遵循开源与用户授权合规边界。',
  },
];

/**
 * 能力矩阵清单与边界状态
 */
interface CapabilityRow {
  module: string;
  feature: string;
  status: 'ready_offline' | 'ready_cloud' | 'ready_local' | 'experimental' | 'concept';
  statusLabel: string;
  implementationDetail: string;
}

const CAPABILITY_MATRIX: CapabilityRow[] = [
  {
    module: '传统风格库',
    feature: '五大传统视觉风格约束与知识库',
    status: 'ready_offline',
    statusLabel: '已就绪 · 离线可用',
    implementationDetail: '朱仙镇年画、汴绣、宋画青绿山水、青花瓷与剪纸的构图、配色与纹样特征完全本地化内置。',
  },
  {
    module: '智能生成',
    feature: 'Qwen Image 3.0 主题与参考图创作',
    status: 'ready_cloud',
    statusLabel: '已就绪 · 需配置云端密钥',
    implementationDetail: '调用阿里云 DashScope qwen-image-3.0，支持主题文本、上限 10MB 参考图与风格强度约束参数。',
  },
  {
    module: '视觉解读',
    feature: '本地 Qwen3-VL 读图生成 CultureCard',
    status: 'ready_local',
    statusLabel: '已就绪 · 需运行本地模型',
    implementationDetail: '通过本地 Ollama 运行 qwen3-vl:4b-instruct 自动提取文化视觉特征；未启动时回退至模板。',
  },
  {
    module: '作品展厅',
    feature: '作品自动落盘、筛选管理与全生命周期',
    status: 'ready_offline',
    statusLabel: '已就绪 · 离线可用',
    implementationDetail: '内置 5 件已核验精选作品离线可览；新生成作品通过后端落盘并在前端通过 caseId 统一关联。',
  },
  {
    module: '互动赏析',
    feature: '画中有话（热点）、一图一境（图文长卷）',
    status: 'ready_offline',
    statusLabel: '已就绪 · 离线可用',
    implementationDetail: '内置作品已逐点复核坐标与叙事；新生成作品可在后台流水线中自动提取候选热点。',
  },
  {
    module: '画境漫游',
    feature: '2.5D 分层深度视差漫游',
    status: 'ready_offline',
    statusLabel: '已就绪 · 离线可用',
    implementationDetail: '基于自定义着色器实现伪深度推镜漫游；新作品构建依赖本地生成深度图脚本。',
  },
  {
    module: '纹脉展馆',
    feature: '两层三维虚拟展馆漫游与器物 DIY 布展',
    status: 'ready_offline',
    statusLabel: '已就绪 · 离线可用',
    implementationDetail: 'Three.js 实体渲染，支持 15 个画框自由换画、14 件器物拖拽摆放、昼夜光影切换与灵宠伴游。',
  },
  {
    module: '文创转化',
    feature: '8 类文创载体预览与高清导出',
    status: 'ready_offline',
    statusLabel: '已就绪 · 离线可用',
    implementationDetail: '文旅明信片、数字海报、帆布袋等 8 类载体比例实时排版，支持导出 1600×1200 PNG。',
  },
  {
    module: '外部场景',
    feature: '物理场馆大屏联动与文创供应链打样',
    status: 'concept',
    statusLabel: '应用构想 · 未对外部署',
    implementationDetail: '应用场景页展示的外部物理大屏与景区零售系统属于落地设想，未对接实体印厂或交易系统。',
  },
];

export default function About() {
  const [activeTab, setActiveTab] = useState<ArchLayer>('frontend');
  const [selectedStyle, setSelectedStyle] = useState<string>('zhuxianzhen');

  const currentArch = ARCH_LAYERS.find((a) => a.id === activeTab) || ARCH_LAYERS[0];
  const activeStyleData = STYLES.find((s) => s.id === selectedStyle) || STYLES[0];

  return (
    <div className="max-w-7xl mx-auto px-6 py-12 md:py-20 lg:py-24">
      {/* ── 品牌序章 · 纹脉立意 ─────────────────────────────────── */}
      <header className="mb-24 text-center max-w-4xl mx-auto">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-primary/20 bg-primary/5 text-primary text-xs md:text-sm font-medium mb-6">
          <Sparkles className="w-4 h-4 text-gold" />
          纹脉华章 · 品牌故事与全栈技术架构
        </div>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-serif font-bold text-ink mb-6 leading-tight">
          以数字智能活化千年文脉 <br />
          <span className="text-2xl sm:text-3xl lg:text-4xl text-primary font-medium mt-3 inline-block">
            让传统东方审美自然融入当代生活
          </span>
        </h1>
        <p className="text-base sm:text-lg text-ink/75 leading-relaxed font-sans mb-8">
          纹脉华章是一个集「传统文化视觉风格库、多模态 AI 智能创作、多维互动赏析、三维虚拟展陈与文创转化打样」于一体的文化智能创作平台。
          我们致力于让不具备专业绘画技巧的文化爱好者、学生与设计师，也能借助先进的 AI 多模态模型，
          <span className="text-primary font-medium"> 将古典审美语法转化为鲜活的数字资产与文创衍生品</span>。
        </p>

        {/* 核心亮点徽章 */}
        <div className="flex flex-wrap items-center justify-center gap-3 text-xs sm:text-sm">
          <span className="px-3.5 py-1.5 rounded-full bg-white border border-gold/30 text-ink/80 shadow-xs font-serif">
            五大传统非遗视觉体系
          </span>
          <span className="px-3.5 py-1.5 rounded-full bg-white border border-primary/20 text-primary shadow-xs font-serif">
            Qwen Image 3.0 云端可控生成
          </span>
          <span className="px-3.5 py-1.5 rounded-full bg-white border border-gold/30 text-ink/80 shadow-xs font-serif">
            本地 Qwen3-VL 视觉理解
          </span>
          <span className="px-3.5 py-1.5 rounded-full bg-white border border-primary/20 text-primary shadow-xs font-serif">
            Three.js 两层三维沉浸展馆
          </span>
          <span className="px-3.5 py-1.5 rounded-full bg-white border border-gold/30 text-ink/80 shadow-xs font-serif">
            8 类文创载体高清打样
          </span>
        </div>
      </header>

      {/* ── 文化之根 · 五大视觉语法体系 ───────────────────────────── */}
      <section className="mb-24">
        <div className="mb-10 text-center max-w-2xl mx-auto">
          <p className="text-xs font-medium tracking-[0.3em] text-primary/75 mb-2">CULTURAL ROOTS</p>
          <h2 className="text-3xl sm:text-4xl font-serif font-bold text-ink mb-3">
            文化之根 · 五大视觉语法体系
          </h2>
          <p className="text-sm text-ink/65 leading-relaxed">
            我们未止步于模糊的“中国风”概念，而是深入开封与中原历史文脉，提炼出五大代表性文化视觉规范，形成可量化、可注入 Prompt 的结构化生成约束。
          </p>
        </div>

        {/* 风格切换标签 */}
        <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3 mb-8">
          {STYLES.map((style) => (
            <button
              key={style.id}
              type="button"
              onClick={() => setSelectedStyle(style.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-serif transition-all ${
                selectedStyle === style.id
                  ? 'bg-primary text-white shadow-md'
                  : 'bg-white/80 border border-gold/30 text-ink/70 hover:border-primary hover:text-primary'
              }`}
            >
              <div className="w-5 h-5 rounded-full overflow-hidden border border-white/50 shrink-0">
                <img
                  src={style.img}
                  className="w-full h-full object-cover"
                  alt={style.name}
                />
              </div>
              <span>{style.name}</span>
            </button>
          ))}
        </div>

        {/* 选中风格详述卡片 */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeStyleData.id}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            transition={{ duration: 0.4 }}
            className="rounded-3xl border border-gold/30 bg-gradient-to-br from-[#FFFDF9] via-[#FAF6EE] to-[#F5ECE0] p-6 sm:p-10 shadow-sm grid lg:grid-cols-12 gap-8 items-center"
          >
            <div className="lg:col-span-5">
              <div className="aspect-[4/3] rounded-2xl overflow-hidden border-2 border-white shadow-lg bg-white">
                <img
                  src={activeStyleData.img}
                  alt={activeStyleData.name}
                  className="w-full h-full object-cover"
                />
              </div>
              <div className="mt-3 flex items-center justify-between text-xs text-ink/60 font-serif">
                <span>技艺类型：{activeStyleData.categoryLabel}</span>
                <Link to="/styles" className="text-primary hover:underline flex items-center gap-1">
                  探索风格库详情 <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>

            <div className="lg:col-span-7 space-y-4">
              <div className="flex items-center gap-3">
                <h3 className="text-2xl sm:text-3xl font-serif font-bold text-ink">
                  {activeStyleData.name}
                </h3>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary border border-primary/20">
                  {activeStyleData.tag}
                </span>
              </div>
              <p className="text-sm sm:text-base text-ink/75 leading-relaxed font-sans">
                {activeStyleData.shortDescription}
              </p>

              <div className="grid sm:grid-cols-2 gap-3 pt-2">
                <div className="p-3.5 rounded-xl bg-white/70 border border-primary/10 text-xs">
                  <span className="font-bold text-ink block mb-1 font-serif">视觉特征提炼：</span>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {activeStyleData.visualFeatures.map((f, i) => (
                      <span key={i} className="px-2 py-0.5 rounded bg-primary/5 text-primary border border-primary/15 text-[11px]">
                        {f}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-white/70 border border-primary/10 text-xs">
                  <span className="font-bold text-ink block mb-1 font-serif">文化象征与源流：</span>
                  <p className="text-ink/65 leading-relaxed text-[11.5px] line-clamp-3">
                    {activeStyleData.symbolicMeaning}
                  </p>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-white/50 border border-gold/20 text-xs text-ink/60 font-mono">
                <span className="font-bold text-ink/80 block mb-0.5 font-serif">Prompt 视觉语法约束：</span>
                {activeStyleData.promptVisualFeatures}
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </section>

      {/* ── 核心功能全景闭环图文叙事 ───────────────────────────────── */}
      <section className="mb-24">
        <div className="mb-14 text-center max-w-2xl mx-auto">
          <p className="text-xs font-medium tracking-[0.3em] text-primary/75 mb-2">FULL CAPABILITIES</p>
          <h2 className="text-3xl sm:text-4xl font-serif font-bold text-ink mb-3">
            六维全景能力图谱
          </h2>
          <p className="text-sm text-ink/65 leading-relaxed">
            不只是单一的 AI 绘图框，而是从创作输入、多模态推理、自动解读、多维互动、空间展陈到文创应用的全景闭环。
          </p>
        </div>

        <div className="space-y-16">
          {/* 功能 1 & 2：Qwen Image 3.0 创作 + 本地 Qwen3-VL 解读 */}
          <div className="grid lg:grid-cols-2 gap-8 items-center">
            <div className="p-8 rounded-3xl bg-white/80 border border-primary/15 shadow-sm space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary mb-3">
                <Sparkles className="w-6 h-6" />
              </div>
              <span className="text-xs font-mono font-bold text-gold tracking-widest block">PIPELINE 01</span>
              <h3 className="text-2xl font-serif font-bold text-ink">
                Qwen Image 3.0 可控多模态创作
              </h3>
              <p className="text-sm text-ink/70 leading-relaxed font-sans">
                接入阿里云百炼官方 Qwen Image 3.0 云端服务。用户可输入任意文化主题，支持上传最高 10MB 的构图或姿态参考图，自由调节 0% ~ 100% 风格约束强度。
                服务端精准校验并真实回报 <code className="text-xs bg-primary/5 px-1 py-0.5 rounded text-primary">referenceImageUsed</code> 证据，保证推理过程真实透明。
              </p>
              <div className="aspect-[16/10] rounded-xl overflow-hidden border border-primary/15 shadow-sm bg-black/5">
                <img src={creatorShot} alt="创作工作台" className="w-full h-full object-cover object-top" />
              </div>
            </div>

            <div className="p-8 rounded-3xl bg-white/80 border border-gold/30 shadow-sm space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-gold/15 flex items-center justify-center text-gold mb-3">
                <Cpu className="w-6 h-6" />
              </div>
              <span className="text-xs font-mono font-bold text-gold tracking-widest block">PIPELINE 02</span>
              <h3 className="text-2xl font-serif font-bold text-ink">
                本地 Qwen3-VL 视觉理解与文化卡
              </h3>
              <p className="text-sm text-ink/70 leading-relaxed font-sans">
                本地部署 Ollama Qwen3-VL 4B 视觉多模态大模型。成图后自动分析构图元素、色彩基调与非遗工艺特征，生成结构化文化意涵与文创建议。
                一键导出设计精致、可用于展示或打印的 CultureCard 视觉卡片，使每件作品都具备坚实的文化叙事底蕴。
              </p>
              <div className="aspect-[16/10] rounded-xl overflow-hidden border border-gold/25 shadow-sm bg-black/5">
                <img src={cultureCardShot} alt="文化说明卡" className="w-full h-full object-cover" />
              </div>
            </div>
          </div>

          {/* 功能 3 & 4：作品展厅落盘 + 三种沉浸式互动赏析 */}
          <div className="grid lg:grid-cols-2 gap-8 items-center">
            <div className="p-8 rounded-3xl bg-white/80 border border-primary/15 shadow-sm space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary mb-3">
                <Database className="w-6 h-6" />
              </div>
              <span className="text-xs font-mono font-bold text-gold tracking-widest block">PIPELINE 03</span>
              <h3 className="text-2xl font-serif font-bold text-ink">
                作品展厅与全生命周期自动入库
              </h3>
              <p className="text-sm text-ink/70 leading-relaxed font-sans">
                生成即入展，彻底告别单次运行的临时页面。成图与元数据由后端 Case Store 自动保存，并在作品展厅自动构建互动入口。
                内置 5 件已核验精选作品（瑞猫迎春、绣兔牡丹、云鹤临水楼、青花蝶韵、剪影灵狐），支持按风格和来源灵活筛选，且具备防误改校验机制。
              </p>
              <div className="aspect-[16/10] rounded-xl overflow-hidden border border-primary/15 shadow-sm bg-black/5">
                <img src={galleryShot} alt="作品展厅" className="w-full h-full object-cover" />
              </div>
            </div>

            <div className="p-8 rounded-3xl bg-white/80 border border-gold/30 shadow-sm space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-gold/15 flex items-center justify-center text-gold mb-3">
                <Eye className="w-6 h-6" />
              </div>
              <span className="text-xs font-mono font-bold text-gold tracking-widest block">PIPELINE 04</span>
              <h3 className="text-2xl font-serif font-bold text-ink">
                画中有话 · 一图一境 · 画境漫游
              </h3>
              <p className="text-sm text-ink/70 leading-relaxed font-sans">
                提供三重深度互动体验：在「画中有话」中探寻微观工艺细节热点；在「一图一境」中跟随三折图文长卷品味文化渊源；
                在「画境漫游」中借助 2.5D 分层深度着色器实现推镜入画与视角环视，全方位升华数字化文化作品的沉浸感。
              </p>
              <div className="grid grid-cols-3 gap-2 aspect-[16/10]">
                <div className="rounded-lg overflow-hidden border border-primary/15 shadow-xs">
                  <img src={experienceShot} alt="画中有话" className="w-full h-full object-cover" />
                </div>
                <div className="rounded-lg overflow-hidden border border-primary/15 shadow-xs">
                  <img src={storyShot} alt="一图一境" className="w-full h-full object-cover" />
                </div>
                <div className="rounded-lg overflow-hidden border border-primary/15 shadow-xs">
                  <img src={wanderShot} alt="画境漫游" className="w-full h-full object-cover" />
                </div>
              </div>
            </div>
          </div>

          {/* 功能 5 & 6：三维纹脉展馆 + 八类文创衍生打样 */}
          <div className="grid lg:grid-cols-2 gap-8 items-center">
            <div className="p-8 rounded-3xl bg-white/80 border border-primary/15 shadow-sm space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary mb-3">
                <Compass className="w-6 h-6" />
              </div>
              <span className="text-xs font-mono font-bold text-gold tracking-widest block">PIPELINE 05</span>
              <h3 className="text-2xl font-serif font-bold text-ink">
                两层三维纹脉展馆与 DIY 布展
              </h3>
              <p className="text-sm text-ink/70 leading-relaxed font-sans">
                基于 Three.js 打造的双层中式古典建筑数字展馆。支持第一/第三人称自由漫游，靠近画框自动唤起文化解读卡。
                在布展模式下，创作者可随时将自己的作品挂入 15 处画框、自由陈列 14 件传统器物道具，并支持昼夜光影切换与灵宠纹纹伴游领路。
              </p>
              <div className="aspect-[16/10] rounded-xl overflow-hidden border border-primary/15 shadow-sm bg-black/5">
                <img src={heritageInterior} alt="展馆内景" className="w-full h-full object-cover" />
              </div>
            </div>

            <div className="p-8 rounded-3xl bg-white/80 border border-gold/30 shadow-sm space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-gold/15 flex items-center justify-center text-gold mb-3">
                <Layout className="w-6 h-6" />
              </div>
              <span className="text-xs font-mono font-bold text-gold tracking-widest block">PIPELINE 06</span>
              <h3 className="text-2xl font-serif font-bold text-ink">
                文创转化工坊与 8 类载体打样
              </h3>
              <p className="text-sm text-ink/70 leading-relaxed font-sans">
                把数字艺术品直接转为文创生产力。支持一键将作品映射至文旅明信片、艺术海报、帆布袋、书签、陶瓷杯垫、手机壁纸等 8 类预设载体。
                根据载体自适应优化版式构图与材质模拟，并支持导出 1600×1200 像素的高清效果图，打通文创设计前期推演。
              </p>
              <div className="aspect-[16/10] rounded-xl overflow-hidden border border-gold/25 shadow-sm bg-black/5">
                <img src={productShot} alt="文创转化" className="w-full h-full object-cover object-top" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 全栈技术架构与可交互拓扑 ─────────────────────────────── */}
      <section className="mb-24">
        <div className="mb-10 text-center max-w-2xl mx-auto">
          <p className="text-xs font-medium tracking-[0.3em] text-primary/75 mb-2">TECHNICAL ARCHITECTURE</p>
          <h2 className="text-3xl sm:text-4xl font-serif font-bold text-ink mb-3">
            全栈技术架构与模块拓扑
          </h2>
          <p className="text-sm text-ink/65 leading-relaxed">
            点击下方各层级，深入了解纹脉华章系统的数据流转、技术选型与实际工程实现。
          </p>
        </div>

        {/* 架构层级导航 Tab */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          {ARCH_LAYERS.map((layer) => {
            const Icon = layer.icon;
            const isSelected = activeTab === layer.id;
            return (
              <button
                key={layer.id}
                type="button"
                onClick={() => setActiveTab(layer.id)}
                className={`p-4 rounded-2xl border text-left transition-all ${
                  isSelected
                    ? 'bg-primary text-white border-primary shadow-lg scale-[1.02]'
                    : 'bg-white/80 border-gold/30 text-ink/70 hover:border-primary/50 hover:bg-white'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <Icon className={`w-5 h-5 ${isSelected ? 'text-gold' : 'text-primary'}`} />
                  <span className={`text-[10px] font-mono uppercase ${isSelected ? 'text-white/80' : 'text-ink/40'}`}>
                    LAYER
                  </span>
                </div>
                <div className="font-serif font-bold text-sm sm:text-base leading-snug">
                  {layer.title}
                </div>
              </button>
            );
          })}
        </div>

        {/* 选中的架构层级详细展示 */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentArch.id}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            transition={{ duration: 0.35 }}
            className="rounded-3xl border border-primary/20 bg-white/95 p-6 sm:p-10 shadow-sm"
          >
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-primary/10 mb-6">
              <div>
                <h3 className="text-2xl font-serif font-bold text-ink mb-1">
                  {currentArch.title}
                </h3>
                <p className="text-xs font-mono text-primary/80 uppercase tracking-wider">
                  {currentArch.subtitle}
                </p>
              </div>
              <span className="px-3 py-1 rounded-full bg-primary/5 border border-primary/15 text-xs text-primary font-medium w-fit">
                工程已验证上线
              </span>
            </div>

            <p className="text-sm sm:text-base text-ink/75 leading-relaxed mb-8 font-sans">
              {currentArch.desc}
            </p>

            <div className="grid sm:grid-cols-2 gap-4 mb-8">
              {currentArch.technologies.map((tech, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-rice-paper/70 border border-primary/10 hover:border-primary/30 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono font-bold text-sm text-ink">{tech.name}</span>
                    <span className="text-[10.5px] px-2 py-0.5 rounded bg-primary/10 text-primary font-serif">
                      {tech.badge}
                    </span>
                  </div>
                  <p className="text-xs text-ink/65 leading-relaxed">{tech.role}</p>
                </div>
              ))}
            </div>

            <div className="p-4 rounded-xl bg-gold/10 border border-gold/30 text-xs text-ink/80 flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 text-primary shrink-0 mt-0.5" />
              <div>
                <span className="font-bold font-serif text-primary block mb-0.5">客观技术能力边界：</span>
                {currentArch.boundaryNote}
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </section>

      {/* ── 诚实透明 · 能力边界与技术说明 ───────────────────────── */}
      <section className="mb-24">
        <div className="mb-10 text-center max-w-2xl mx-auto">
          <p className="text-xs font-medium tracking-[0.3em] text-primary/75 mb-2">CAPABILITY & BOUNDARY MATRIX</p>
          <h2 className="text-3xl sm:text-4xl font-serif font-bold text-ink mb-3">
            诚实透明 · 项目能力边界矩阵
          </h2>
          <p className="text-sm text-ink/65 leading-relaxed">
            严谨区分「已就绪上线运行」、「需配置云端/本地大模型运行」与「尚未对外部署的应用构想」，不浮夸、不虚构。
          </p>
        </div>

        <div className="overflow-x-auto rounded-2xl border border-primary/15 bg-white shadow-xs">
          <table className="w-full text-left border-collapse text-xs sm:text-sm">
            <thead>
              <tr className="border-b border-primary/15 bg-primary/5 font-serif text-ink">
                <th className="py-3.5 px-4 font-bold">功能模块</th>
                <th className="py-3.5 px-4 font-bold">特性描述</th>
                <th className="py-3.5 px-4 font-bold">运行就绪状态</th>
                <th className="py-3.5 px-4 font-bold">真实实现细节与运行前提</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-primary/10">
              {CAPABILITY_MATRIX.map((row, idx) => (
                <tr key={idx} className="hover:bg-primary/[0.02] transition-colors">
                  <td className="py-3 px-4 font-serif font-bold text-ink/90 whitespace-nowrap">
                    {row.module}
                  </td>
                  <td className="py-3 px-4 text-ink/80 font-medium">
                    {row.feature}
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium ${
                        row.status === 'ready_offline'
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : row.status === 'ready_cloud'
                          ? 'bg-blue-50 text-blue-800 border border-blue-200'
                          : row.status === 'ready_local'
                          ? 'bg-purple-50 text-purple-800 border border-purple-200'
                          : 'bg-amber-50 text-amber-800 border border-amber-200'
                      }`}
                    >
                      <CheckCircle2 className="w-3 h-3" />
                      {row.statusLabel}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-xs text-ink/65 leading-relaxed">
                    {row.implementationDetail}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── 品牌尾章 · 开启创作 ─────────────────────────────────── */}
      <footer className="p-8 sm:p-14 rounded-3xl bg-gradient-to-br from-primary via-[#8A1F17] to-[#6A1610] text-white text-center relative overflow-hidden shadow-2xl">
        <div
          className={`absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.1'/%3E%3C/svg%3E")] pointer-events-none`}
        ></div>
        
        <div className="relative z-10 max-w-3xl mx-auto space-y-6">
          <span className="text-xs font-serif tracking-[0.3em] text-gold uppercase block">
            WENMAI HUAZHANG
          </span>
          <h2 className="text-3xl sm:text-4xl font-serif font-bold text-white leading-tight">
            文脉流芳，华章共创
          </h2>
          <p className="text-sm sm:text-base text-white/85 leading-relaxed font-sans max-w-2xl mx-auto">
            每一次创作，都是向千年文化艺术的致敬；每一处笔墨，都借由现代智能重新点亮。
            从今天起，走入画里，与传统文化共同创作属于当代的美学篇章。
          </p>

          <div className="pt-4 flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/creator"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-gold text-[#49392F] font-serif font-bold hover:bg-gold/90 shadow-lg hover:shadow-xl transition-all"
            >
              <span>立即体验智能生成</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/heritage-gallery"
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl border border-white/40 text-white font-serif hover:bg-white/10 transition-all"
            >
              探索三维纹脉展馆
            </Link>
            <Link
              to="/gallery"
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl border border-white/40 text-white font-serif hover:bg-white/10 transition-all"
            >
              浏览作品展厅
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
