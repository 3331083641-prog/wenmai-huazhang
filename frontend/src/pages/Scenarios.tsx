import { Link } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import {
  ArrowRight,
  Eye,
  GraduationCap,
  Landmark,
  Monitor,
  PenTool,
  ShoppingBag,
  Smartphone,
  Store,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

/**
 * 应用场景 = 平台现在真能跑通的部分（真实截图 + 站内跳转）+ 尚未对外部署的构想。
 *
 * 展示结构：每个场景占满一整行，桌面端图文左右交替，滚动进入视口时图片与文字
 * 分别柔和浮现；手机端统一图片在上、文字在下。状态角标已取消，能力边界写在正文里。
 */
import creatorShot from '../../../docs/screenshots/creation-workspace.png';
import experienceShot from '../../../docs/interactive_v2/screens/exp-zxz-selected.png';
import cultureCardShot from '../../../docs/screenshots/culture-card.png';
import interiorShot from '../../../docs/screenshots/heritage-interior.png';
import productShot from '../../../docs/screenshots/creative-products.png';

type Scenario = {
  id: string;
  icon: LucideIcon;
  category: string;
  title: string;
  status: 'live' | 'concept';
  desc: string;
  target: string;
  value: string;
  to?: string;
  cta?: string;
  shot?: string;
  alt?: string;
  /** upper：竖向截图从参数区开始；默认取画面中部 */
  position?: 'center' | 'upper';
};

const SCENARIOS: Scenario[] = [
  {
    id: 'screen',
    icon: Monitor,
    category: '数字展陈',
    title: '数字展陈大屏',
    status: 'concept',
    desc: '展示生成作品在数字展陈大屏中的排版设想。大屏、作品与说明牌均为前端构图，本页不包含小程序、二维码上传或实时大屏同步。',
    target: '博物馆 / 非遗展示中心 / 校园文化展厅',
    value: '为文化主题展览提供数字视觉呈现与互动设计参考。',
  },
  {
    id: 'store',
    icon: Store,
    category: '文旅零售',
    title: '文旅景区文创商店',
    status: 'concept',
    desc: '展示作品映射到明信片、帆布袋、杯垫等载体后的陈列构想。页面未接入景区终端、打印设备或商品交易服务。',
    target: '景区文创空间 / 地方文化活动 / 旅游服务场景',
    value: '为文创概念设计和陈列版式提供参考。',
  },
  {
    id: 'social',
    icon: Smartphone,
    category: '社交传播',
    title: '线上传播与社交分享',
    status: 'concept',
    desc: '以手机界面示意作品在社交媒体中的展示方式。当前不生成分享链接或可扫描二维码，发布与传播由用户自行完成。',
    target: '传统文化爱好者 / 校园社团 / 内容创作者',
    value: '为文化内容的数字排版与社交平台发布提供视觉参考。',
  },
  {
    id: 'education',
    icon: GraduationCap,
    category: '非遗美育',
    title: '非遗与美育教学',
    status: 'live',
    desc: '把五种风格的色彩、构图与纹样条目当作可讲的教学材料：先读风格，再让学生用同一主题生成不同风格的作品做对比，最后用文化说明卡与分段解读讲清工艺背景。',
    target: '高校设计课 / 中小学美育 / 非遗研学',
    value: '风格条目可直接投屏讲解，作品与解读可以并排对比。',
    to: '/styles',
    cta: '进入风格库',
    shot: cultureCardShot,
    alt: '文化说明卡：视觉解读、风格来源与工艺要点',
  },
  {
    id: 'museum',
    icon: Landmark,
    category: '虚拟展陈',
    title: '数字美术馆与虚拟展陈',
    status: 'live',
    desc: '两层三维展馆可直接当作小型数字展厅：作品挂上画框、器物摆进展柜，探索模式自由走动，布展模式换画与调整位置，昼夜与机位切换用来做不同气氛的预设。',
    target: '校园展陈 / 非遗数字馆 / 线上开放日',
    value: '不用建模软件，也能把一批作品组织成可参观的空间。',
    to: '/heritage-gallery',
    cta: '进入三维展馆',
    shot: interiorShot,
    alt: '纹脉展馆内景：画框、展柜与器物',
  },
  {
    id: 'personal',
    icon: PenTool,
    category: '个人创作',
    title: '个人创作与主题练习',
    status: 'live',
    desc: '单人即可完成从主题到成品的闭环：写主题、可选上传参考图、调整风格影响强度、补充构图与负向提示，出图后自动保存，随时回到展厅接着看。',
    target: '学生作业 / 个人兴趣创作 / 教学示范',
    value: '降低传统视觉风格的门槛，同时保留参数级控制。',
    to: '/creator',
    cta: '打开生成工作台',
    shot: creatorShot,
    alt: '智能生成工作台：主题、参考图与风格参数',
    position: 'upper',
  },
  {
    id: 'appreciate',
    icon: Eye,
    category: '互动导览',
    title: '互动欣赏与文化导览',
    status: 'live',
    desc: '同一件作品有三种读法：热点解读（画中有话）、分段图文（一图一境）、第一人称入画（画境漫游）。适合展览现场的扫码讲解，也适合课前自主浏览。',
    target: '展览导览 / 课堂导入 / 公众普及',
    value: '把「看一张画」变成有路径的阅读，且可离线打开。',
    to: '/experience/zhuxianzhen-ruimao',
    cta: '体验画中有话',
    shot: experienceShot,
    alt: '画中有话：年画热点与解读面板',
  },
  {
    id: 'design',
    icon: ShoppingBag,
    category: '文创设计',
    title: '文创设计与载体打样',
    status: 'live',
    desc: '把作品映射到八类载体做版式预览，并导出 1600×1200 PNG；适合在打样前快速筛掉不合适的构图与配色。',
    target: '文创工作室 / 校园文创 / 活动物料',
    value: '从作品到载体版式只需一次选择，减少重复排版。',
    to: '/products',
    cta: '打开文创转化',
    shot: productShot,
    alt: '文创转化：作品映射到明信片等载体',
    position: 'upper',
  },
];

/**
 * 原有三类场景的静态示意（未部署，纯前端构图，不接外部系统）。
 * 内部商品、手机、海报、卡片是独立 DOM，可以各自响应悬停；真实截图不做假热区。
 */
const SceneMockup = ({ id }: { id: string }) => {
  switch (id) {
    case 'screen':
      return (
        <div className="group/scene relative flex h-full w-full items-center justify-center overflow-hidden bg-[#111]">
          <div className="absolute inset-0 bg-gradient-to-b from-gray-900 via-gray-800 to-[#1a1a1a]" />
          <div className="absolute left-1/4 top-0 h-64 w-32 -skew-x-12 bg-white/10 blur-[50px] transition-opacity duration-500 group-hover/scene:opacity-80" />
          <div className="absolute right-1/4 top-0 h-64 w-32 -skew-x-12 bg-white/10 blur-[50px] transition-opacity duration-500 group-hover/scene:opacity-80" />
          <div className="absolute bottom-0 left-0 right-0 h-1/4 bg-black/40 blur-md" />
          <div className="relative z-10 flex aspect-video w-[85%] overflow-hidden rounded border border-gray-800 bg-black shadow-[0_0_50px_rgba(255,255,255,0.1)] transition-all duration-500 group-hover/scene:shadow-[0_0_70px_rgba(255,255,255,0.18)]">
            <img
              src={import.meta.env.BASE_URL + 'songhua.png'}
              className="h-full w-full object-cover opacity-90 mix-blend-screen transition-transform duration-700 ease-out group-hover/scene:scale-[1.03]"
              alt=""
            />
            <div className="pointer-events-none absolute inset-0 shadow-[inset_0_0_20px_rgba(0,0,0,0.8)]" />
            <div className="absolute bottom-4 left-4 flex gap-2">
              {[0, 1, 2].map((item) => (
                <div
                  key={item}
                  className="h-16 w-12 rounded-sm border border-white/20 bg-white/10 transition-transform duration-500 scenario-lift-sm hover:border-white/40 hover:bg-white/20"
                />
              ))}
            </div>
            <div className="absolute right-4 top-4 font-mono text-xs text-white/50">SCENE PREVIEW</div>
          </div>
          <div className="absolute bottom-4 left-1/4 z-20 h-24 w-12 rounded-t-full bg-black/80 blur-[2px]" />
          <div className="absolute bottom-2 right-1/3 z-20 h-20 w-10 rounded-t-full bg-black/90 blur-[1px]" />
        </div>
      );
    case 'store':
      return (
        <div className="group/scene relative flex h-full w-full items-center justify-center overflow-hidden bg-[#E5DACE] p-8">
          <div className="absolute inset-0 bg-[#F2EDE4]" />
          <div className="absolute top-1/3 z-0 h-[10px] w-full bg-[#D4C3AC] shadow-md" />
          <div className="absolute top-2/3 z-0 h-[10px] w-full bg-[#D4C3AC] shadow-md" />
          <div className="absolute left-10 top-[8%] z-10 flex aspect-[3/4] w-24 -rotate-2 flex-col items-center justify-end rounded bg-white pb-2 shadow-md transition-all duration-500 ease-out scenario-lift">
            <div className="absolute -top-4 h-4 w-1/2 rounded-t-lg border-x-[3px] border-t-[3px] border-[#D4C3AC]" />
            <img src={import.meta.env.BASE_URL + 'zhuxianzhen.png'} className="aspect-square w-[85%] object-cover opacity-90" alt="" />
          </div>
          <div className="absolute right-16 top-[20%] z-10 flex h-12 w-32 gap-1 rounded bg-white p-1 shadow-sm transition-all duration-500 ease-out scenario-lift-sm">
            <img src={import.meta.env.BASE_URL + 'qinghua.png'} className="h-full w-1/2 object-cover" alt="" />
            <img src={import.meta.env.BASE_URL + 'jianzhi.png'} className="h-full w-1/2 object-cover" alt="" />
          </div>
          <div className="absolute left-1/3 top-[42%] z-10 flex aspect-video w-32 rotate-2 items-center justify-center rounded border border-[#e0e0e0] bg-[#fafafa] p-2 shadow-lg transition-all duration-500 ease-out scenario-float">
            <img src={import.meta.env.BASE_URL + 'songhua.png'} className="h-full w-full object-cover" alt="" />
          </div>
          <div className="absolute right-24 top-[50%] z-10 h-16 w-12 rounded bg-white shadow-md transition-all duration-500 ease-out scenario-lift-sm">
            <div className="h-4 w-full rounded-t border-b border-gray-200 bg-gray-100" />
            <div className="flex h-full items-center p-1.5">
              <img src={import.meta.env.BASE_URL + 'bianxiu.png'} className="aspect-square w-full rounded-full border border-primary/20 object-cover" alt="" />
            </div>
          </div>
          <div className="pointer-events-none absolute inset-0 z-30 bg-gradient-to-b from-[#F9F6F0]/80 via-transparent to-black/20" />
        </div>
      );
    case 'social':
      return (
        <div className="group/scene relative flex h-full w-full items-center justify-center overflow-hidden bg-[#f0f2f5] p-8">
          <div className="relative z-10 flex h-full aspect-[9/19] -rotate-[5deg] scale-105 flex-col rounded-[2rem] border-[6px] border-gray-800 bg-white p-2 shadow-[0_20px_50px_rgba(0,0,0,0.15)] scenario-phone">
            <div className="flex items-center gap-2 p-2">
              <div className="h-6 w-6 rounded-full border-2 border-primary/20 bg-gray-200 p-px">
                <div className="h-full w-full rounded-full bg-primary/40" />
              </div>
              <div className="flex-1 space-y-1">
                <div className="h-2 w-16 rounded bg-gray-300" />
                <div className="h-1.5 w-10 rounded bg-gray-200" />
              </div>
              <div className="h-1.5 w-5 rounded-full bg-gray-200" />
            </div>
            <div className="relative mt-2 aspect-square w-full overflow-hidden rounded-md bg-gray-100">
              <img
                src={import.meta.env.BASE_URL + 'jianzhi.png'}
                className="h-full w-full object-cover transition-transform duration-700 ease-out group-hover/scene:scale-[1.03]"
                alt=""
              />
            </div>
            <div className="flex gap-3 px-2 py-3">
              <div className="h-5 w-5 rounded-full border-2 border-primary" />
              <div className="h-5 w-5 rounded-full border-2 border-gray-300" />
              <div className="h-5 w-5 rounded-full border-2 border-gray-300" />
              <div className="ml-auto h-5 w-5 rounded-full border-2 border-gray-300" />
            </div>
            <div className="space-y-1.5 px-2">
              <div className="h-2 w-[80%] rounded bg-gray-300" />
              <div className="h-2 w-[60%] rounded bg-gray-200" />
              <div className="mt-2 flex gap-1">
                <span className="rounded bg-red-50 px-1 py-0.5 text-[8px] font-bold text-[#9E241B]">#中国非遗</span>
                <span className="rounded bg-red-50 px-1 py-0.5 text-[8px] font-bold text-[#9E241B]">#AI文创</span>
              </div>
            </div>
            <div className="mt-auto flex items-center justify-between border-t border-gray-100 bg-primary/5 p-3">
              <div className="text-[9px] text-ink/70">线上展示效果示意</div>
              <div
                title="静态装饰图案，不可扫描"
                aria-label="静态装饰图案，不可扫描"
                className="flex h-8 w-8 flex-wrap gap-px rounded border border-black/5 bg-white p-0.5 opacity-50 shadow-sm"
              >
                {[...Array(9)].map((_, i) => (
                  <div key={i} className="aspect-square w-[30%] bg-primary/80" />
                ))}
              </div>
            </div>
          </div>
          <div className="absolute -right-6 top-6 z-0 aspect-[3/4] w-32 rotate-12 rounded border border-black/5 bg-white p-2 shadow-xl transition-all duration-500 ease-out scenario-float">
            <img src={import.meta.env.BASE_URL + 'zhuxianzhen.png'} className="h-full w-full object-cover opacity-80" alt="" />
          </div>
          <div className="absolute -bottom-4 left-4 z-0 aspect-[3/4] w-24 -rotate-12 rounded border border-black/5 bg-white p-2 shadow-xl transition-all duration-500 ease-out scenario-float">
            <img src={import.meta.env.BASE_URL + 'bianxiu.png'} className="h-full w-full object-cover opacity-80" alt="" />
          </div>
        </div>
      );
    default:
      return null;
  }
};

const FLOW = [
  { t: '选择风格', to: '/styles' },
  { t: 'AI 生成', to: '/creator' },
  { t: '作品展厅', to: '/gallery' },
  { t: '互动赏析', to: '/experience/zhuxianzhen-ruimao' },
  { t: '纹脉展馆', to: '/heritage-gallery' },
  { t: '文创转化', to: '/products' },
];

const DEPLOY_STEPS = [
  { n: '1', t: '前端页面部署', d: '配置网页访问与页面内容' },
  { n: '2', t: '生成服务接入', d: '配置服务端接口与模型权限' },
  { n: '3', t: '展示终端适配', d: '按需适配大屏或其他媒介' },
  { n: '4', t: '数据与隐私配置', d: '明确文件留存与用户告知' },
];

/** 一组场景：图片与文字分开，桌面左右交替，手机图片在上。 */
function ScenarioSection({ scenario, index }: { scenario: Scenario; index: number }) {
  const Icon = scenario.icon;
  const reduced = Boolean(useReducedMotion());
  const imageLeft = index % 2 === 0;
  const live = scenario.status === 'live';
  const number = String(index + 1).padStart(2, '0');

  return (
    <motion.section
      initial={reduced ? false : { opacity: 0, y: 46 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-100px' }}
      transition={{ duration: reduced ? 0 : 0.8, ease: [0.22, 1, 0.36, 1] }}
      className={`flex flex-col items-center gap-9 lg:gap-14 ${imageLeft ? 'lg:flex-row' : 'lg:flex-row-reverse'}`}
    >
      <motion.div
        initial={reduced ? false : { opacity: 0, x: imageLeft ? -34 : 34 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true, margin: '-100px' }}
        transition={{ duration: reduced ? 0 : 0.75, delay: reduced ? 0 : 0.08, ease: [0.22, 1, 0.36, 1] }}
        className="w-full lg:w-[55%]"
      >
        <div className="group relative">
          <div className="absolute -inset-2.5 -z-10 rotate-[1.4deg] rounded-[1.6rem] bg-primary/[0.06]" aria-hidden="true" />
          <div className="relative overflow-hidden rounded-2xl border-[6px] border-white bg-white shadow-[0_18px_50px_rgba(63,43,31,0.14)] transition-shadow duration-500 group-hover:shadow-[0_24px_64px_rgba(63,43,31,0.2)]">
            <div className={`relative aspect-[16/10] overflow-hidden bg-ink/5 ${live && scenario.shot ? 'scenario-media' : ''}`}>
              {live && scenario.shot ? (
                <img
                  src={scenario.shot}
                  alt={scenario.alt ?? scenario.title}
                  loading="lazy"
                  className={`h-full w-full object-cover transition-transform duration-[600ms] ease-out group-hover:scale-[1.04] ${
                    scenario.position === 'upper' ? 'object-[center_12%]' : 'object-center'
                  }`}
                />
              ) : (
                <SceneMockup id={scenario.id} />
              )}
            </div>
            <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-black/45 to-transparent" aria-hidden="true" />
            <div className="pointer-events-none absolute bottom-4 left-4 flex items-center gap-2.5 text-white/90">
              <span className="flex h-8 w-8 items-center justify-center rounded-md border border-white/25 bg-white/15 backdrop-blur-sm">
                <Icon className="h-4 w-4" />
              </span>
              <span className="text-[11px] tracking-[0.28em]">SCENE {number}</span>
            </div>
          </div>
        </div>
      </motion.div>

      <motion.div
        initial={reduced ? false : { opacity: 0, x: imageLeft ? 34 : -34 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true, margin: '-100px' }}
        transition={{ duration: reduced ? 0 : 0.75, delay: reduced ? 0 : 0.2, ease: [0.22, 1, 0.36, 1] }}
        className="w-full lg:w-[45%] lg:px-4"
      >
        <p className="text-[11px] tracking-[0.34em] text-gold">SCENE {number} · {scenario.category}</p>
        <div className="mt-3 flex items-center gap-2 text-primary">
          <Icon className="h-4 w-4" />
          <span className="text-[12px] font-medium tracking-wider">{scenario.category}</span>
        </div>
        <h2 className="mt-2 font-serif text-[clamp(1.6rem,2.6vw,2.2rem)] font-bold leading-tight text-ink">
          {scenario.title}
        </h2>
        <div className="mt-4 h-px w-12 bg-primary/60" aria-hidden="true" />
        <p className="mt-5 text-[13.5px] leading-[1.95] text-ink/70">{scenario.desc}</p>

        <dl className="mt-6 space-y-3 border-t border-primary/10 pt-5 text-[12.5px] leading-6">
          <div className="flex gap-4">
            <dt className="w-16 shrink-0 font-serif font-semibold text-ink/45">适用对象</dt>
            <dd className="text-ink/75">{scenario.target}</dd>
          </div>
          <div className="flex gap-4">
            <dt className="w-16 shrink-0 font-serif font-semibold text-ink/45">核心价值</dt>
            <dd className="text-primary/85">{scenario.value}</dd>
          </div>
        </dl>

        {live && scenario.to ? (
          <Link
            to={scenario.to}
            className="mt-6 inline-flex items-center gap-1.5 text-[13px] text-primary transition-all hover:gap-3"
          >
            {scenario.cta ?? '进入体验'}
            <ArrowRight className="h-4 w-4" />
          </Link>
        ) : (
          <p className="mt-6 text-[11.5px] leading-5 text-ink/40">
            外部落地需另行对接；当前为前端静态示意，不代表已部署。
          </p>
        )}
      </motion.div>
    </motion.section>
  );
}

export default function Scenarios() {
  return (
    <main className="mx-auto max-w-[1240px] px-5 pb-20 pt-28 sm:px-8 md:pb-28">

      <style>{`
        .scenario-media img { transition: transform .55s cubic-bezier(.22,1,.36,1); }
        .scenario-media:hover img { transform: scale(1.04); }
        .scenario-lift, .scenario-lift-sm, .scenario-card, .scenario-float, .scenario-phone {
          transition: translate .45s cubic-bezier(.22,1,.36,1), scale .45s cubic-bezier(.22,1,.36,1),
            rotate .45s cubic-bezier(.22,1,.36,1), box-shadow .45s ease;
        }
        .scenario-lift:hover { translate: 0 -8px; scale: 1.04; box-shadow: 0 18px 38px rgba(63,43,31,.22); }
        .scenario-lift-sm:hover { translate: 0 -5px; scale: 1.03; box-shadow: 0 14px 30px rgba(63,43,31,.18); }
        .scenario-card:hover { rotate: 0deg; translate: 0 -7px; scale: 1.04; box-shadow: 0 22px 46px rgba(63,43,31,.24); }
        .scenario-float:hover { rotate: 0deg; translate: 0 -8px; scale: 1.05; box-shadow: 0 22px 46px rgba(63,43,31,.24); }
        .scenario-phone:hover { rotate: 0deg; scale: 1.06; }
      `}</style>
      <header className="mx-auto mb-16 max-w-3xl text-center md:mb-24">
        <p className="text-[11px] tracking-[0.34em] text-primary/70">SCENARIOS</p>
        <h1 className="mt-4 font-serif text-4xl font-bold text-primary sm:text-5xl">多场景应用</h1>
        <p className="mx-auto mt-6 max-w-2xl text-[14px] leading-[1.95] text-ink/70">
          从传统视觉风格的创作，到作品保存、互动赏析、三维展陈与文创载体预览，
          纹脉华章把一条完整的文化内容链路放进不同场景。下面八组场景中，部分已可在平台内直接体验，
          部分仍是面向场馆、商店与教学的外部应用构想，已在正文中分别说明。
        </p>
      </header>

      <div className="space-y-28 md:space-y-36">
        {SCENARIOS.map((scenario, index) => (
          <ScenarioSection key={scenario.id} scenario={scenario} index={index} />
        ))}
      </div>

      <section className="mt-24 border-t border-primary/10 pt-10 md:mt-32">
        <div className="mb-5 text-center">
          <p className="text-[11px] tracking-[0.3em] text-primary/60">ONE CONTINUOUS PATH</p>
          <h2 className="mt-2 font-serif text-xl text-ink md:text-2xl">从风格选择到文创转化</h2>
        </div>
        <ol className="flex flex-wrap items-center justify-center gap-x-2 gap-y-3">
          {FLOW.map((step, index) => (
            <li key={step.t} className="flex items-center gap-2">
              <Link
                to={step.to}
                className="rounded-full border border-primary/15 bg-white/70 px-3.5 py-1.5 text-[12.5px] text-ink/75 transition-colors hover:border-primary/40 hover:text-primary"
              >
                {step.t}
              </Link>
              {index < FLOW.length - 1 && <ArrowRight className="h-3.5 w-3.5 text-primary/30" />}
            </li>
          ))}
        </ol>

        <details className="mx-auto mt-10 max-w-3xl rounded-lg border border-primary/10 bg-white/50 px-4 py-3">
          <summary className="cursor-pointer text-[12.5px] text-ink/60 transition-colors hover:text-primary">
            对外部署参考流程（规划，未部署）
          </summary>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {DEPLOY_STEPS.map((step) => (
              <div key={step.n} className="rounded-lg border border-primary/10 bg-white p-3">
                <div className="font-serif text-[13px] font-bold text-primary">{step.n}. {step.t}</div>
                <div className="mt-1 text-[11.5px] leading-5 text-ink/50">{step.d}</div>
              </div>
            ))}
          </div>
        </details>

        <p className="mx-auto mt-8 max-w-3xl text-center text-[11px] leading-5 text-ink/40">
          本页图片为项目页面的真实截图；未部署场景为前端静态构图，不连接场馆、印厂或交易系统。
          {' '}
          <Link to="/about" className="text-primary/70 hover:text-primary">了解当前能力边界</Link>
        </p>
      </section>
    </main>
  );
}