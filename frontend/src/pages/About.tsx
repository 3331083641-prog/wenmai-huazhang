import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence, LayoutGroup } from 'motion/react';
import {
  ArrowRight,
  Sparkles,
  Cpu,
  Database,
  Eye,
  Compass,
  Layout,
  Server,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Layers,
  Palette,
  ShieldCheck,
  SlidersHorizontal,
  ChevronRight,
  Maximize2,
  Sparkle,
  Flame,
  Code2,
  Boxes,
  HelpCircle,
  type LucideIcon,
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
 * 六大核心能力定义
 */
interface CapabilityItem {
  id: number;
  number: string;
  tag: string;
  title: string;
  shortTitle: string;
  subtitle: string;
  summary: string;
  highlights: string[];
  badges: string[];
  image: string;
  alt: string;
  to: string;
  cta: string;
  accentColor: string;
  accentBg: string;
  accentBorder: string;
  icon: LucideIcon;
  previewNote: string;
  subShots?: { label: string; img: string }[];
}

const CAPABILITIES: CapabilityItem[] = [
  {
    id: 1,
    number: '01',
    tag: '智能生成',
    title: 'Qwen Image 3.0 可控智能生成',
    shortTitle: '智能视觉生成',
    subtitle: '云端多模态图像生成 · 结构化审美语法注入',
    summary:
      '以千年文脉为审美先验，支持文本主题与上限 10MB 的构图姿态参考图双驱动创作。服务端精准校验并真实返回 referenceImageUsed 凭据，确保推理过程透明可信。',
    highlights: [
      '文本主题与参考图双向约束，0% ~ 100% 风格强度精准可调',
      '提炼非遗核心构图与设色法则，毫秒级注入结构化 Prompt 语法',
      '云端原生接入阿里云百炼官方 Qwen Image 3.0，杜绝伪概念伪生成',
    ],
    badges: ['阿里云百炼 DashScope', 'Qwen Image 3.0', '10MB 参考图支持', '真实凭证校验'],
    image: creatorShot,
    alt: 'Qwen Image 3.0 创作工作台',
    to: '/creator',
    cta: '立即体验生成',
    accentColor: '#9E241B',
    accentBg: 'rgba(158, 36, 27, 0.08)',
    accentBorder: 'rgba(158, 36, 27, 0.28)',
    icon: Sparkles,
    previewNote: '双驱动多模态创作',
  },
  {
    id: 2,
    number: '02',
    tag: '视觉理解',
    title: 'Qwen3-VL 视觉理解与文化卡',
    shortTitle: '视觉理解与文化卡',
    subtitle: '本地轻量化多模态推理 · 自动文化特征深度解读',
    summary:
      '本地部署 Ollama Qwen3-VL 4B 视觉多模态大模型。成图后自动分析构图元素、色彩基调与非遗工艺特征，一键导出精致 CultureCard 文化说明卡。',
    highlights: [
      '本地部署 Ollama Qwen3-VL 4B 视觉多模态模型，保护创作者数据隐私',
      '自动化提取非遗工艺特征、色彩象征意涵与文创转化建议',
      '精美排版 CultureCard 说明卡，支持一键高清保存与印刷打样',
    ],
    badges: ['Ollama 本地部署', 'Qwen3-VL 4B', '自动化特征提取', 'CultureCard 导出'],
    image: cultureCardShot,
    alt: 'CultureCard 文化说明卡',
    to: '/creator',
    cta: '探索文化解读',
    accentColor: '#C5A059',
    accentBg: 'rgba(197, 160, 89, 0.12)',
    accentBorder: 'rgba(197, 160, 89, 0.35)',
    icon: Cpu,
    previewNote: '多模态意涵提炼',
  },
  {
    id: 3,
    number: '03',
    tag: '作品展厅',
    title: '作品展厅与自动保存管理',
    shortTitle: '作品展厅与存储',
    subtitle: '生成即入库 · 本地持久化管理 · 防误改哈希校验',
    summary:
      '彻底告别单次运行的临时页面。成图与元数据通过本地 Case Store 自动落盘入库，并自动构建互动赏析入口；内置 5 件已核验精选名作离线可览。',
    highlights: [
      'Case Store 本地持久化存储，原图、成图与参数元数据全生命周期管理',
      '内置 5 件官方精选核验名作，无网或无 API 环境下离线完整可用',
      'SHA-256 证据哈希追踪，具备作品来源筛选与防误改校验机制',
    ],
    badges: ['Case Store 本地存储', '5 件核验名作', 'SHA-256 审计', '离线完整可用'],
    image: galleryShot,
    alt: '作品展厅与作品管理',
    to: '/gallery',
    cta: '浏览作品展厅',
    accentColor: '#2B5F75',
    accentBg: 'rgba(43, 95, 117, 0.08)',
    accentBorder: 'rgba(43, 95, 117, 0.28)',
    icon: Database,
    previewNote: '全生命周期入库',
  },
  {
    id: 4,
    number: '04',
    tag: '互动赏析',
    title: '画中有话 · 一图一境 · 画境漫游',
    shortTitle: '三重沉浸互动',
    subtitle: '微观工艺热点 · 图文长卷叙事 · 2.5D 分层深度视差',
    summary:
      '突破传统静态图片展示，提供三重深度互动体验：探寻微观工法细节热点、品读三折屏风图文长卷、借助 2.5D GLSL 着色器实现推镜入画与视差环视。',
    highlights: [
      '画中有话：微观工艺细节热点交互，逐点拆解传统非遗工法精髓',
      '一图一境：典雅三折屏风图文长卷，沉浸式溯源文化意象与流变故事',
      '画境漫游：自定义 GLSL 伪深度分层着色器，支持鼠标视角环视推镜',
    ],
    badges: ['GLSL 自定义 Shader', '2.5D 深度视差', '图文长卷', '微观热点交互'],
    image: experienceShot,
    alt: '互动赏析与画境漫游',
    to: '/gallery',
    cta: '体验互动绘卷',
    accentColor: '#3B7A68',
    accentBg: 'rgba(59, 122, 104, 0.08)',
    accentBorder: 'rgba(59, 122, 104, 0.28)',
    icon: Eye,
    previewNote: '工艺细节与视差漫游',
    subShots: [
      { label: '画中有话 · 工艺热点', img: experienceShot },
      { label: '一图一境 · 图文长卷', img: storyShot },
      { label: '画境漫游 · 深度视差', img: wanderShot },
    ],
  },
  {
    id: 5,
    number: '05',
    tag: '空间展陈',
    title: '纹脉展馆与 DIY 沉浸式布展',
    shortTitle: '三维展馆与布展',
    subtitle: 'Three.js 双层中式虚拟展厅 · 自由换画布展 · 灵宠伴游',
    summary:
      '基于 Three.js 独立渲染完整双层中式实体木构建筑。创作者可自由漫游、将作品挂入 15 处画框、自由陈列 14 件传统道具，并支持昼夜光影切换与灵宠领路。',
    highlights: [
      'WebGL / Three.js 独立渲染经典中式木构双层建筑，支持第一/第三人称视角',
      '自由策展模式：15 处画框一键陈列生成作品，14 件传统器物随心摆放',
      '昼夜真实光影切换与灵宠“纹纹”智能寻路伴游导览系统',
    ],
    badges: ['Three.js / WebGL', '15 处画框策展', '14 件传统器物', '昼夜光影系统'],
    image: heritageInterior,
    alt: '纹脉展馆内景与布展模式',
    to: '/heritage-gallery',
    cta: '漫游三维展馆',
    accentColor: '#8B3A2B',
    accentBg: 'rgba(139, 58, 43, 0.08)',
    accentBorder: 'rgba(139, 58, 43, 0.28)',
    icon: Compass,
    previewNote: '双层木构实体漫游',
    subShots: [
      { label: '展馆内景 · 画框布展', img: heritageInterior },
      { label: '建筑外景 · 中式重檐', img: heritageExterior },
    ],
  },
  {
    id: 6,
    number: '06',
    tag: '文创转化',
    title: '文创转化工坊与 8 类载体打样',
    shortTitle: '文创转化工坊',
    subtitle: '自适应版式排版 · 材质真实感模拟 · 1600×1200 高清打样',
    summary:
      '打通数字艺术到文创生产力的最后一公里。一键将作品映射至文旅明信片、艺术海报、帆布袋、陶瓷杯垫等 8 类预设载体，自适应构图并导出高清打样图。',
    highlights: [
      '8 类精选文创载体：明信片、艺术海报、帆布袋、书签、陶瓷杯垫、手机壁纸等',
      '根据载体物理比例自适应版式构图与纹理光影材质模拟',
      '支持导出 1600×1200 像素的高清打样图，赋能文创设计前期快速推演',
    ],
    badges: ['8 类文创载体', '1600×1200 导出', '材质真实模拟', '自适应排版'],
    image: productShot,
    alt: '文创转化工坊与衍生打样',
    to: '/products',
    cta: '进入文创工坊',
    accentColor: '#B87333',
    accentBg: 'rgba(184, 115, 51, 0.08)',
    accentBorder: 'rgba(184, 115, 51, 0.28)',
    icon: Layout,
    previewNote: '8 类文创实体打样',
  },
];

/**
 * 五大传统文化视觉风格传统色彩图谱
 */
interface ColorSwatch {
  name: string;
  hex: string;
  role: string;
}

const STYLE_PALETTES: Record<string, ColorSwatch[]> = {
  zhuxianzhen: [
    { name: '辰砂朱红', hex: '#A92822', role: '门神主调' },
    { name: '栀子明黄', hex: '#D9A93F', role: '吉祥衬色' },
    { name: '松石碧绿', hex: '#3A7563', role: '套印对比' },
    { name: '焦茶水墨', hex: '#49392F', role: '轮廓骨架' },
  ],
  bianxiu: [
    { name: '茜草柔红', hex: '#A64C54', role: '花卉主线' },
    { name: '缃叶金丝', hex: '#C5A56B', role: '盘金刺绣' },
    { name: '苍筤冷绿', hex: '#4C6958', role: '枝叶掩映' },
    { name: '沉香绢褐', hex: '#51423E', role: '底料勾勒' },
  ],
  songhua: [
    { name: '研磨石青', hex: '#345C72', role: '青绿主峰' },
    { name: '天然石绿', hex: '#426C62', role: '层峦树木' },
    { name: '泥金点染', hex: '#B99A5B', role: '云烟勾金' },
    { name: '宋代楮皮', hex: '#EAE4D2', role: '古画底纸' },
  ],
  qinghua: [
    { name: '回青霁蓝', hex: '#2B5F75', role: '缠枝纹样' },
    { name: '苏麻离青', hex: '#1C3B5E', role: '铁锈沉斑' },
    { name: '影青淡蓝', hex: '#8EABC0', role: '水波晕染' },
    { name: '甜白瓷胎', hex: '#F5F9FB', role: '瓷体留白' },
  ],
  jianzhi: [
    { name: '传统剪纸红', hex: '#A52225', role: '镂空主体' },
    { name: '雄黄衬金', hex: '#D7B16A', role: '衬底装饰' },
    { name: '焦墨阴刻', hex: '#382727', role: '阴刻深衬' },
    { name: '暖调象牙白', hex: '#FFF8F1', role: '镂空映光' },
  ],
};

/**
 * 架构分层数据定义
 */
type ArchLayer = 'frontend' | 'backend' | 'ai' | 'storage';

interface ArchItem {
  id: ArchLayer;
  title: string;
  subtitle: string;
  icon: LucideIcon;
  desc: string;
  dataFlow: string;
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
    dataFlow: '用户意图输入 -> 实时视口交互 -> Three.js 场景渲染 -> GLSL 视差推镜',
    technologies: [
      { name: 'React 19 + TypeScript', role: '核心组件系统与强类型数据链路', badge: '正式' },
      { name: 'Tailwind CSS + Motion', role: '中式文化美学设计系统与流畅微动效', badge: '正式' },
      { name: 'Three.js / React Three Fiber', role: '纹脉展馆双层建筑与器物布展引擎', badge: '正式' },
      { name: 'GLSL Custom Shader', role: '画境漫游伪深度与分层视差摄像机渲染', badge: '正式' },
    ],
    boundaryNote:
      '画境漫游基于深度图与前景分割实现 2.5D 视差推镜效果，并非对画作进行完整三维实景摄影测量建模；三维展馆为 WebGL 虚拟空间，非线下博物馆实景孪生系统。',
  },
  {
    id: 'backend',
    title: '后端服务与任务流水线',
    subtitle: 'Backend Services & Persistent Job Pipelines',
    icon: Server,
    desc: '基于 Python 3.12 与 FastAPI 构建轻量化高性能服务端。提供图像生成转发、本地大模型视觉分析、作品持久化存储（Case Store）以及异步互动资源构建流水线（Interactive Jobs）。',
    dataFlow: '接收前端 Prompt -> 校验参考图 -> 调度大模型 -> 自动元数据落盘',
    technologies: [
      { name: 'FastAPI + Uvicorn', role: '异步高吞吐 API 服务与跨域中继', badge: '正式' },
      { name: 'Case Store (Local)', role: '生成结果、原图、成图与元数据自动落盘入库', badge: '正式' },
      { name: 'Interactive Jobs', role: '自动构建画中有话、一图一境与画境漫游数据', badge: '正式' },
      { name: 'Prompt Builder', role: '文化风格结构化语法注入与权重约束构建', badge: '正式' },
    ],
    boundaryNote:
      '系统采用本地文件持久化元数据管理，不依赖外部大型关系型数据库或云端托管账户系统，保障本地单机可完整便携交付与离线运行。',
  },
  {
    id: 'ai',
    title: 'AI 多模态大模型矩阵',
    subtitle: 'Multi-Modal Foundation Models & Local Vision',
    icon: Cpu,
    desc: '采用「云端多模态图像生成 + 本地轻量化视觉大模型解读」的混合 AI 协同架构。云端对接阿里云百炼官方 Qwen Image 3.0，本地部署 Ollama Qwen3-VL 4B 视觉多模态模型，兼顾生成品质与隐私可控性。',
    dataFlow: '云端 DashScope 生成成图 -> 本地 Qwen3-VL 提取工艺特征 -> 生成文化说明卡',
    technologies: [
      { name: 'Qwen Image 3.0 (DashScope)', role: '文本主题 + 参考图 + 风格约束双驱动图像生成', badge: '云端 API' },
      { name: 'Qwen3-VL:4b (Ollama Local)', role: '本地自动化视觉特征提取、文化意涵解读与文化卡生成', badge: '本地推理' },
      { name: 'DashScope Wanx (Fallback)', role: '通义万相云端图像备用生成支持', badge: '备用' },
      { name: 'Rule-based Template Engine', role: 'AI 服务未配置或离线时的优雅回退兜底', badge: '离线兜底' },
    ],
    boundaryNote:
      '本项目直接调用通义千问官方 Qwen Image 3.0 与 Qwen3-VL 开源权重，未声称自研或全参数微调基础大模型。Prompt Visual Features 来自项目团队对非遗文献与代表作的人工结构化提炼。',
  },
  {
    id: 'storage',
    title: '资产组织与离线闭环',
    subtitle: 'Asset Management & Offline Delivery Loop',
    icon: Database,
    desc: '所有内置作品、文化说明卡、三维展馆模型（GLB）、互动绘卷分层图（WebP）均经过编译期打包与本地校验。即使在无公网网络或无 API 密钥的环境下，用户仍可完整浏览五大风格、作品展厅、三维展馆与全部互动赏析功能。',
    dataFlow: '静态资源指纹打包 -> 本地 SHA-256 完整性校验 -> 离线零依赖交付',
    technologies: [
      { name: 'GLB 3D Assets', role: 'Blender 烘焙并优化的中式两层展馆及 14 件器物道具', badge: '本地资产' },
      { name: 'WebP Multi-layer Maps', role: '互动赏析的分层剪影、前景切片与深度预览纹理', badge: '本地资产' },
      { name: 'Vite Glob & Assets', role: '静态资源指纹打包与统一相对路径分发', badge: '构建规范' },
      { name: 'SHA-256 Evidence Tracking', role: '作品与参考图哈希校验与真实生成证据追溯', badge: '防伪审计' },
    ],
    boundaryNote:
      '演示作品均为项目真实流水线在 2026 年生成并归档的真实输出，未用非真实概念图冒充生成结果，各项素材遵循开源与用户授权合规边界。',
  },
];

/**
 * 能力矩阵清单与边界状态
 */
type CapabilityStatus = 'ready_offline' | 'ready_cloud' | 'ready_local' | 'concept';

interface CapabilityRow {
  module: string;
  feature: string;
  status: CapabilityStatus;
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
  // 6大能力矩阵当前主焦点卡片 ID (默认第 1 张)
  const [activeCapId, setActiveCapId] = useState<number>(1);
  // 画境漫游/三维展馆多图子视图切换
  const [selectedSubShot, setSelectedSubShot] = useState<string | null>(null);

  // 风格库选中 ID
  const [selectedStyle, setSelectedStyle] = useState<string>('zhuxianzhen');

  // 架构分层当前 Tab
  const [activeArchTab, setActiveArchTab] = useState<ArchLayer>('frontend');

  // 能力边界过滤
  const [capFilter, setCapFilter] = useState<'all' | CapabilityStatus>('all');

  // 当前主卡数据
  const activeCap = CAPABILITIES.find((c) => c.id === activeCapId) || CAPABILITIES[0];
  // 辅助卡片列表（保持自然序号排列，避免乱序）
  const auxiliaryCaps = CAPABILITIES.filter((c) => c.id !== activeCapId);

  const activeStyleData = STYLES.find((s) => s.id === selectedStyle) || STYLES[0];
  const activePalette = STYLE_PALETTES[selectedStyle] || STYLE_PALETTES.zhuxianzhen;
  const currentArch = ARCH_LAYERS.find((a) => a.id === activeArchTab) || ARCH_LAYERS[0];

  const filteredCapMatrix =
    capFilter === 'all'
      ? CAPABILITY_MATRIX
      : CAPABILITY_MATRIX.filter((item) => item.status === capFilter);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 md:py-16 lg:py-20 overflow-hidden">
      {/* ── 顶部主视觉 · 品牌序章 ─────────────────────────────────── */}
      <header className="relative mb-20 md:mb-28 text-center max-w-4xl mx-auto">
        {/* 背景雅致中式卷轴水纹线 */}
        <div className="absolute inset-0 -top-8 flex items-center justify-center pointer-events-none opacity-20">
          <svg className="w-full h-48 md:h-64" viewBox="0 0 800 200" fill="none">
            <path
              d="M0,100 C150,150 250,50 400,100 C550,150 650,50 800,100"
              stroke="var(--color-gold)"
              strokeWidth="1.5"
              strokeDasharray="4 6"
            />
            <path
              d="M0,120 C200,60 300,160 500,110 C650,70 720,130 800,120"
              stroke="var(--color-primary)"
              strokeWidth="1"
              strokeOpacity="0.4"
            />
          </svg>
        </div>

        {/* 顶部标签 */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-primary/20 bg-primary/5 text-primary text-xs md:text-sm font-medium mb-6 backdrop-blur-xs"
        >
          <Sparkles className="w-4 h-4 text-gold" />
          <span className="font-serif tracking-wider">纹脉华章 · 文化科技创新实验空间</span>
        </motion.div>

        {/* 主标题 */}
        <motion.h1
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="text-3xl sm:text-5xl lg:text-6xl font-serif font-bold text-ink mb-5 leading-tight tracking-tight"
        >
          以数字智能活化千年文脉
          <span className="block text-xl sm:text-3xl lg:text-4xl text-primary font-medium mt-3">
            让传统东方审美自然融入当代生活
          </span>
        </motion.h1>

        {/* 精炼立意导言 */}
        <motion.p
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="text-sm sm:text-base md:text-lg text-ink/75 leading-relaxed font-sans max-w-3xl mx-auto mb-8"
        >
          纹脉华章融合
          <strong className="text-primary font-serif font-semibold"> Qwen Image 3.0 </strong>
          云端可控多模态生成、
          <strong className="text-primary font-serif font-semibold">本地 Qwen3-VL </strong>
          视觉理解、
          <strong className="text-primary font-serif font-semibold">Three.js </strong>
          双层中式虚拟展馆与
          <strong className="text-primary font-serif font-semibold"> 8 类文创转化打样</strong>
          ，构筑从灵感触发、多维赏析到实体布展的完整闭环。
        </motion.p>

        {/* 关键特性轻量徽章 */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="flex flex-wrap items-center justify-center gap-2.5 sm:gap-3 text-xs sm:text-sm"
        >
          <a
            href="#capabilities"
            className="px-3.5 py-1.5 rounded-full bg-white/90 hover:bg-white border border-gold/30 text-ink/80 shadow-xs font-serif transition-colors"
          >
            ✦ 六维能力矩阵
          </a>
          <a
            href="#styles"
            className="px-3.5 py-1.5 rounded-full bg-white/90 hover:bg-white border border-primary/20 text-primary shadow-xs font-serif transition-colors"
          >
            ✦ 五大非遗图鉴
          </a>
          <a
            href="#architecture"
            className="px-3.5 py-1.5 rounded-full bg-white/90 hover:bg-white border border-gold/30 text-ink/80 shadow-xs font-serif transition-colors"
          >
            ✦ 全栈架构拓扑
          </a>
          <a
            href="#boundary"
            className="px-3.5 py-1.5 rounded-full bg-white/90 hover:bg-white border border-primary/20 text-primary shadow-xs font-serif transition-colors"
          >
            ✦ 诚实能力边界
          </a>
        </motion.div>
      </header>

      {/* ── 核心设计：六大核心功能动态交互矩阵 ─────────────────────── */}
      <section id="capabilities" className="mb-28 md:mb-36 scroll-mt-24">
        {/* 区域标题与交互指引 */}
        <div className="mb-8 text-center max-w-2xl mx-auto">
          <p className="text-xs font-mono font-semibold tracking-[0.3em] text-primary/80 uppercase mb-2">
            DYNAMIC CAPABILITY MATRIX
          </p>
          <h2 className="text-2xl sm:text-4xl font-serif font-bold text-ink mb-3">
            六维全景能力图谱
          </h2>
          <p className="text-xs sm:text-sm text-ink/65 leading-relaxed">
            默认展开首要能力焦点，点击任意卡片即可平滑放大探索，其余卡片自适应重组。
          </p>
        </div>

        {/* 顶部快速导航 Pills */}
        <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-2.5 mb-8">
          {CAPABILITIES.map((cap) => {
            const isCurrent = cap.id === activeCapId;
            const Icon = cap.icon;
            return (
              <button
                key={cap.id}
                type="button"
                onClick={() => {
                  setActiveCapId(cap.id);
                  setSelectedSubShot(null);
                }}
                className={`group relative flex items-center gap-2 px-3 sm:px-4 py-2 rounded-xl text-xs sm:text-sm font-serif transition-all duration-300 ${
                  isCurrent
                    ? 'bg-primary text-white shadow-md shadow-primary/25 scale-[1.02]'
                    : 'bg-white/85 hover:bg-white text-ink/75 hover:text-primary border border-gold/30 hover:border-primary/40'
                }`}
              >
                <span
                  className={`text-[10px] font-mono font-bold ${
                    isCurrent ? 'text-gold' : 'text-primary'
                  }`}
                >
                  {cap.number}
                </span>
                <Icon
                  className={`w-3.5 h-3.5 ${
                    isCurrent ? 'text-white' : 'text-ink/60 group-hover:text-primary'
                  }`}
                />
                <span>{cap.shortTitle}</span>
                {isCurrent && (
                  <motion.div
                    layoutId="active-pill-border"
                    className="absolute inset-0 rounded-xl border-2 border-gold/60 pointer-events-none"
                    transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                  />
                )}
              </button>
            );
          })}
        </div>

        {/* 动态六卡 Bento 空间排布 */}
        <LayoutGroup id="capabilities-matrix-layout">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-5 items-stretch">
            {/* ── 1. 主焦点卡片 (Hero Expanded Card: 占 8 列，2 行高度) ── */}
            <motion.div
              key={`hero-${activeCap.id}`}
              layoutId={`card-container-${activeCap.id}`}
              layout
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="col-span-12 lg:col-span-8 lg:row-span-2 rounded-3xl bg-white/95 border-2 shadow-xl p-6 sm:p-8 flex flex-col justify-between relative overflow-hidden backdrop-blur-xs group"
              style={{ borderColor: activeCap.accentColor }}
            >
              {/* 背景微光环 */}
              <div
                className="absolute -top-24 -right-24 w-72 h-72 rounded-full blur-3xl pointer-events-none opacity-20"
                style={{ backgroundColor: activeCap.accentColor }}
              />

              {/* 卡片头部 */}
              <div className="flex items-start justify-between gap-4 mb-5">
                <div>
                  <div className="flex items-center gap-2 mb-1.5">
                    <span
                      className="font-mono text-xs font-bold px-2.5 py-0.5 rounded-full"
                      style={{
                        backgroundColor: activeCap.accentBg,
                        color: activeCap.accentColor,
                        border: `1px solid ${activeCap.accentBorder}`,
                      }}
                    >
                      PIPELINE {activeCap.number} · {activeCap.tag}
                    </span>
                    <span className="text-[11px] font-mono text-ink/50 uppercase tracking-widest hidden sm:inline">
                      CURRENT FOCUS
                    </span>
                  </div>
                  <h3 className="text-xl sm:text-2xl lg:text-3xl font-serif font-bold text-ink">
                    {activeCap.title}
                  </h3>
                  <p className="text-xs sm:text-sm text-ink/60 font-sans mt-0.5">
                    {activeCap.subtitle}
                  </p>
                </div>

                <div
                  className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 shadow-xs"
                  style={{
                    backgroundColor: activeCap.accentBg,
                    color: activeCap.accentColor,
                    border: `1px solid ${activeCap.accentBorder}`,
                  }}
                >
                  <activeCap.icon className="w-6 h-6" />
                </div>
              </div>

              {/* 卡片核心展示区：左右分栏（图片 + 详尽亮点） */}
              <div className="grid md:grid-cols-12 gap-6 items-center my-auto">
                {/* 左侧：代表性大图视觉 */}
                <div className="md:col-span-6 space-y-3">
                  <div className="aspect-[16/10] rounded-2xl overflow-hidden border border-black/10 shadow-md relative bg-black/5 chinese-border">
                    <motion.img
                      layoutId={`card-img-${activeCap.id}`}
                      src={selectedSubShot || activeCap.image}
                      alt={activeCap.alt}
                      className="w-full h-full object-cover object-top transition-transform duration-500 hover:scale-105"
                    />
                    <div className="absolute top-2.5 left-2.5 px-2.5 py-1 rounded-full bg-black/60 backdrop-blur-xs text-[10.5px] text-white/90 font-serif flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      运行实景截屏
                    </div>
                  </div>

                  {/* 多子图视图快速切换（针对互动赏析与展馆） */}
                  {activeCap.subShots && (
                    <div className="flex items-center gap-2 pt-1">
                      {activeCap.subShots.map((sub, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => setSelectedSubShot(sub.img)}
                          className={`text-[11px] px-2.5 py-1 rounded-lg font-serif transition-all ${
                            (selectedSubShot || activeCap.image) === sub.img
                              ? 'bg-ink text-white shadow-xs'
                              : 'bg-rice-paper text-ink/70 hover:bg-white border border-gold/30'
                          }`}
                        >
                          {sub.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* 右侧：精炼介绍与核心技术亮点 */}
                <div className="md:col-span-6 space-y-4">
                  <p className="text-sm sm:text-[15px] text-ink/80 leading-relaxed font-sans">
                    {activeCap.summary}
                  </p>

                  {/* 核心亮点清单 */}
                  <div className="space-y-2 pt-1">
                    {activeCap.highlights.map((item, idx) => (
                      <div key={idx} className="flex items-start gap-2.5 text-xs sm:text-[13px] text-ink/75">
                        <CheckCircle2
                          className="w-4 h-4 shrink-0 mt-0.5"
                          style={{ color: activeCap.accentColor }}
                        />
                        <span>{item}</span>
                      </div>
                    ))}
                  </div>

                  {/* 技术标签 */}
                  <div className="flex flex-wrap gap-1.5 pt-2">
                    {activeCap.badges.map((b, idx) => (
                      <span
                        key={idx}
                        className="text-[11px] px-2.5 py-1 rounded-md bg-rice-paper border border-primary/15 text-ink/70 font-mono"
                      >
                        {b}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* 卡片底栏：操作入口与探索提示 */}
              <div className="flex flex-wrap items-center justify-between gap-4 pt-6 border-t border-black/5 mt-6">
                <span className="text-xs text-ink/50 font-serif flex items-center gap-1.5">
                  <Sparkle className="w-3.5 h-3.5 text-gold" />
                  当前为主展示焦点 · 点击周围 5 张卡片可任意切换
                </span>

                <Link
                  to={activeCap.to}
                  className="btn-chinese inline-flex items-center gap-2 px-6 py-2.5 text-xs sm:text-sm font-serif shadow-sm hover:shadow-md transition-all group"
                >
                  <span>{activeCap.cta}</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </Link>
              </div>
            </motion.div>

            {/* ── 2. 其余五张辅助卡片（分布在周围，自然重排） ── */}
            {auxiliaryCaps.map((card, idx) => (
              <motion.div
                key={`aux-${card.id}`}
                layoutId={`card-container-${card.id}`}
                layout
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                onClick={() => {
                  setActiveCapId(card.id);
                  setSelectedSubShot(null);
                }}
                whileHover={{ y: -4, scale: 1.015 }}
                whileTap={{ scale: 0.98 }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setActiveCapId(card.id);
                    setSelectedSubShot(null);
                  }
                }}
                aria-label={`展开探索 ${card.title}`}
                className={`col-span-12 sm:col-span-6 lg:col-span-4 cursor-pointer rounded-2xl bg-white/85 hover:bg-white border transition-all duration-300 shadow-xs hover:shadow-lg p-5 flex flex-col justify-between group relative overflow-hidden focus:outline-none focus:ring-2 focus:ring-primary/50 ${
                  idx < 2 ? 'min-h-[240px]' : 'min-h-[210px]'
                }`}
                style={{ borderColor: 'rgba(210, 161, 74, 0.3)' }}
              >
                {/* 顶部简明信息 */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span
                      className="font-mono text-xs font-bold px-2 py-0.5 rounded-full"
                      style={{
                        backgroundColor: card.accentBg,
                        color: card.accentColor,
                        border: `1px solid ${card.accentBorder}`,
                      }}
                    >
                      {card.number} · {card.tag}
                    </span>
                    <card.icon
                      className="w-5 h-5 transition-transform duration-300 group-hover:scale-110 group-hover:rotate-6"
                      style={{ color: card.accentColor }}
                    />
                  </div>

                  <h4 className="font-serif font-bold text-base text-ink group-hover:text-primary transition-colors line-clamp-1">
                    {card.title}
                  </h4>
                  <p className="text-xs text-ink/65 line-clamp-2 mt-1 leading-relaxed font-sans">
                    {card.summary}
                  </p>
                </div>

                {/* 底部微缩预览图与点击提示 */}
                <div className="mt-4 pt-3 border-t border-black/5 flex items-center justify-between gap-3">
                  <div className="w-16 h-11 rounded-lg overflow-hidden border border-black/10 shrink-0 bg-black/5">
                    <motion.img
                      layoutId={`card-img-${card.id}`}
                      src={card.image}
                      alt={card.alt}
                      className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                    />
                  </div>

                  <span className="text-xs font-serif text-primary/80 group-hover:text-primary flex items-center gap-1 font-medium transition-colors">
                    点击放大探索
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                  </span>
                </div>
              </motion.div>
            ))}
          </div>
        </LayoutGroup>
      </section>

      {/* ── 文化之根 · 五大视觉语法体系（风格图鉴） ───────────────── */}
      <section id="styles" className="mb-28 md:mb-36 scroll-mt-24">
        <div className="mb-10 text-center max-w-2xl mx-auto">
          <p className="text-xs font-mono font-semibold tracking-[0.3em] text-primary/80 uppercase mb-2">
            CULTURAL GRAMMAR SPEC
          </p>
          <h2 className="text-2xl sm:text-4xl font-serif font-bold text-ink mb-3">
            文化之根 · 五大视觉语法体系
          </h2>
          <p className="text-xs sm:text-sm text-ink/65 leading-relaxed">
            深入中原与经典文脉提炼的结构化视觉规范，支持提取构图、设色与纹样特征，注入 AI 生成约束。
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
                  ? 'bg-primary text-white shadow-md scale-[1.02]'
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

        {/* 选中风格详述图鉴 */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeStyleData.id}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            transition={{ duration: 0.35 }}
            className="rounded-3xl border border-gold/40 bg-gradient-to-br from-[#FFFDF9] via-[#FAF6EE] to-[#F5ECE0] p-6 sm:p-10 shadow-sm grid lg:grid-cols-12 gap-8 items-center"
          >
            {/* 左侧：代表作装裱大图 */}
            <div className="lg:col-span-5 space-y-3">
              <div className="aspect-[4/3] rounded-2xl overflow-hidden border-2 border-white shadow-lg bg-white relative chinese-border">
                <img
                  src={activeStyleData.img}
                  alt={activeStyleData.name}
                  className="w-full h-full object-cover"
                />
              </div>
              <div className="flex items-center justify-between text-xs text-ink/65 font-serif px-1">
                <span>技艺属性：{activeStyleData.categoryLabel}</span>
                <Link
                  to={`/creator?style=${activeStyleData.id}`}
                  className="text-primary hover:underline font-medium flex items-center gap-1"
                >
                  以此风格创作 <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>

            {/* 右侧：传统色彩图谱 + 视觉特征 + 语法约束 */}
            <div className="lg:col-span-7 space-y-5">
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

              {/* 传统色彩图谱 (Authentic Chinese Color Swatches) */}
              <div className="p-3.5 rounded-xl bg-white/70 border border-gold/30">
                <span className="text-xs font-bold text-ink/80 block mb-2 font-serif">
                  传统美学色彩基调：
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {activePalette.map((c, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 p-1.5 rounded-lg bg-white/90 border border-black/5"
                    >
                      <span
                        className="w-4 h-4 rounded-full border border-black/10 shrink-0 shadow-2xs"
                        style={{ backgroundColor: c.hex }}
                      />
                      <div className="text-[11px] leading-tight">
                        <div className="font-serif text-ink font-medium">{c.name}</div>
                        <div className="text-ink/40 font-mono text-[9px]">{c.role}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 核心视觉特征 */}
              <div className="space-y-1.5">
                <span className="text-xs font-bold text-ink/80 block font-serif">
                  核心视觉语法提取：
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {activeStyleData.visualFeatures.map((f, i) => (
                    <span
                      key={i}
                      className="px-2.5 py-0.5 rounded-md bg-white/80 text-primary border border-primary/20 text-xs font-serif shadow-2xs"
                    >
                      {f}
                    </span>
                  ))}
                </div>
              </div>

              {/* 结构化 Prompt 注入语法 */}
              <div className="p-3.5 rounded-xl bg-white/60 border border-gold/25 text-xs">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-ink/80 font-serif">Prompt 视觉语法约束公式：</span>
                  <span className="text-[10px] font-mono text-ink/40">WEIGHT: 1.0</span>
                </div>
                <code className="block p-2 rounded bg-rice-paper text-ink/85 font-mono text-[11px] leading-relaxed border border-gold/20 break-all">
                  {activeStyleData.promptVisualFeatures}
                </code>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </section>

      {/* ── 全栈技术架构与模块拓扑 ───────────────────────────────── */}
      <section id="architecture" className="mb-28 md:mb-36 scroll-mt-24">
        <div className="mb-10 text-center max-w-2xl mx-auto">
          <p className="text-xs font-mono font-semibold tracking-[0.3em] text-primary/80 uppercase mb-2">
            SYSTEM ARCHITECTURE & TOPOLOGY
          </p>
          <h2 className="text-2xl sm:text-4xl font-serif font-bold text-ink mb-3">
            全栈技术架构与可交互拓扑
          </h2>
          <p className="text-xs sm:text-sm text-ink/65 leading-relaxed">
            点击不同系统层级，查看各模块的工程实现、数据流向与客观能力边界。
          </p>
        </div>

        {/* 拓扑流水线导航节点 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          {ARCH_LAYERS.map((layer, idx) => {
            const Icon = layer.icon;
            const isSelected = activeArchTab === layer.id;
            return (
              <button
                key={layer.id}
                type="button"
                onClick={() => setActiveArchTab(layer.id)}
                className={`p-4 rounded-2xl border text-left transition-all relative overflow-hidden group ${
                  isSelected
                    ? 'bg-primary text-white border-primary shadow-lg scale-[1.02]'
                    : 'bg-white/85 border-gold/30 text-ink/70 hover:border-primary/50 hover:bg-white'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <Icon className={`w-5 h-5 ${isSelected ? 'text-gold' : 'text-primary'}`} />
                  <span
                    className={`text-[10px] font-mono uppercase ${
                      isSelected ? 'text-white/80' : 'text-ink/40'
                    }`}
                  >
                    STAGE 0{idx + 1}
                  </span>
                </div>
                <div className="font-serif font-bold text-sm sm:text-base leading-snug">
                  {layer.title}
                </div>
                {isSelected && (
                  <div className="absolute bottom-0 left-0 right-0 h-1 bg-gold" />
                )}
              </button>
            );
          })}
        </div>

        {/* 选中的架构层级详细卡片 */}
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

            <p className="text-sm sm:text-base text-ink/75 leading-relaxed mb-6 font-sans">
              {currentArch.desc}
            </p>

            {/* 动态数据流连线示意 */}
            <div className="mb-6 p-3 rounded-xl bg-rice-paper border border-gold/30 flex items-center gap-3 text-xs">
              <span className="font-serif font-bold text-primary shrink-0">数据流转中枢：</span>
              <span className="font-mono text-ink/75 truncate">{currentArch.dataFlow}</span>
            </div>

            {/* 真实技术选型卡片 */}
            <div className="grid sm:grid-cols-2 gap-4 mb-6">
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

            {/* 客观能力边界说明 */}
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

      {/* ── 诚实透明 · 项目能力边界矩阵（轻量化交互卡片） ─────────── */}
      <section id="boundary" className="mb-24 md:mb-32 scroll-mt-24">
        <div className="mb-8 text-center max-w-2xl mx-auto">
          <p className="text-xs font-mono font-semibold tracking-[0.3em] text-primary/80 uppercase mb-2">
            TRANSPARENCY & BOUNDARIES
          </p>
          <h2 className="text-2xl sm:text-4xl font-serif font-bold text-ink mb-3">
            诚实透明 · 项目能力边界矩阵
          </h2>
          <p className="text-xs sm:text-sm text-ink/65 leading-relaxed">
            严谨区分「已就绪离线可用」、「需配置云端密钥/本地模型」与「尚未对外部署的应用构想」，不虚构、不夸大。
          </p>
        </div>

        {/* 状态过滤 Tab */}
        <div className="flex flex-wrap items-center justify-center gap-2 mb-6 text-xs font-serif">
          <button
            type="button"
            onClick={() => setCapFilter('all')}
            className={`px-3 py-1.5 rounded-full transition-all ${
              capFilter === 'all'
                ? 'bg-primary text-white shadow-xs'
                : 'bg-white/80 text-ink/70 hover:bg-white border border-gold/30'
            }`}
          >
            全部特性 ({CAPABILITY_MATRIX.length})
          </button>
          <button
            type="button"
            onClick={() => setCapFilter('ready_offline')}
            className={`px-3 py-1.5 rounded-full transition-all ${
              capFilter === 'ready_offline'
                ? 'bg-emerald-700 text-white shadow-xs'
                : 'bg-white/80 text-emerald-800 hover:bg-white border border-emerald-200'
            }`}
          >
            离线可用 (6)
          </button>
          <button
            type="button"
            onClick={() => setCapFilter('ready_cloud')}
            className={`px-3 py-1.5 rounded-full transition-all ${
              capFilter === 'ready_cloud'
                ? 'bg-blue-700 text-white shadow-xs'
                : 'bg-white/80 text-blue-800 hover:bg-white border border-blue-200'
            }`}
          >
            云端模型 (1)
          </button>
          <button
            type="button"
            onClick={() => setCapFilter('ready_local')}
            className={`px-3 py-1.5 rounded-full transition-all ${
              capFilter === 'ready_local'
                ? 'bg-purple-700 text-white shadow-xs'
                : 'bg-white/80 text-purple-800 hover:bg-white border border-purple-200'
            }`}
          >
            本地模型 (1)
          </button>
          <button
            type="button"
            onClick={() => setCapFilter('concept')}
            className={`px-3 py-1.5 rounded-full transition-all ${
              capFilter === 'concept'
                ? 'bg-amber-700 text-white shadow-xs'
                : 'bg-white/80 text-amber-800 hover:bg-white border border-amber-200'
            }`}
          >
            应用构想 (1)
          </button>
        </div>

        {/* 交互卡片网格取代死板大表格 */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCapMatrix.map((item, idx) => (
            <motion.div
              key={idx}
              layout
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.25 }}
              className="p-5 rounded-2xl bg-white/90 border border-primary/15 shadow-2xs hover:shadow-sm transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-xs font-serif font-bold text-primary/80">
                    {item.module}
                  </span>
                  <span
                    className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10.5px] font-medium ${
                      item.status === 'ready_offline'
                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        : item.status === 'ready_cloud'
                        ? 'bg-blue-50 text-blue-800 border border-blue-200'
                        : item.status === 'ready_local'
                        ? 'bg-purple-50 text-purple-800 border border-purple-200'
                        : 'bg-amber-50 text-amber-800 border border-amber-200'
                    }`}
                  >
                    <CheckCircle2 className="w-3 h-3" />
                    {item.statusLabel}
                  </span>
                </div>
                <h4 className="font-serif font-bold text-sm sm:text-base text-ink mb-1.5">
                  {item.feature}
                </h4>
              </div>
              <p className="text-xs text-ink/65 leading-relaxed font-sans mt-3 pt-3 border-t border-black/5">
                {item.implementationDetail}
              </p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── 品牌尾章 · 开启创作探索 ───────────────────────────────── */}
      <footer className="p-8 sm:p-14 rounded-3xl bg-gradient-to-br from-primary via-[#8A1F17] to-[#5C140E] text-white text-center relative overflow-hidden shadow-2xl">
        <div className="absolute inset-0 bg-white/5 pointer-events-none" />

        <div className="relative z-10 max-w-3xl mx-auto space-y-6">
          <span className="text-xs font-serif tracking-[0.35em] text-gold uppercase block">
            WENMAI HUAZHANG · CREATIVE PORTAL
          </span>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-serif font-bold text-white leading-tight">
            文脉流芳 · 华章共创
          </h2>
          <p className="text-sm sm:text-base text-white/85 leading-relaxed font-sans max-w-2xl mx-auto">
            每一次创作，都是向千年文化艺术的致敬；每一处笔墨，都借由现代智能重新点亮。
            从今天起，走入画里，与传统文化共同创作属于当代的美学篇章。
          </p>

          <div className="pt-4 flex flex-wrap items-center justify-center gap-3.5 sm:gap-4">
            <Link
              to="/creator"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-gold text-[#49392F] font-serif font-bold hover:bg-gold/90 shadow-lg hover:shadow-xl transition-all"
            >
              <Sparkles className="w-4 h-4 text-[#49392F]" />
              <span>立即体验智能创作</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/heritage-gallery"
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl border border-white/40 text-white font-serif hover:bg-white/10 transition-all shadow-sm"
            >
              <Compass className="w-4 h-4 text-gold" />
              <span>漫游三维纹脉展馆</span>
            </Link>
            <Link
              to="/gallery"
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl border border-white/40 text-white font-serif hover:bg-white/10 transition-all shadow-sm"
            >
              <Database className="w-4 h-4 text-gold" />
              <span>浏览精选作品展厅</span>
            </Link>
            <Link
              to="/scenarios"
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl border border-white/40 text-white font-serif hover:bg-white/10 transition-all shadow-sm"
            >
              <Layout className="w-4 h-4 text-gold" />
              <span>探索应用落地场景</span>
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
