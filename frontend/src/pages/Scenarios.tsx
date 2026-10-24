import { Link } from 'react-router-dom';
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
import { cn } from '../lib/utils';

/**
 * 应用场景 = 平台现在真能跑通的部分（真实截图 + 站内跳转）+ 尚未对外部署的构想（静态示意）。
 * 两类必须分开标注，不能把「示意」写成「已部署」。
 */
import creatorShot from '../../../docs/screenshots/creation-workspace.png';
import experienceShot from '../../../docs/interactive_v2/screens/exp-zxz-selected.png';
import cultureCardShot from '../../../docs/screenshots/culture-card.png';
import interiorShot from '../../../docs/screenshots/heritage-interior.png';
import productShot from '../../../docs/screenshots/creative-products.png';

type Scenario = {
  id: string;
  icon: LucideIcon;
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
    title: '数字展陈大屏',
    status: 'concept',
    desc: '展示生成作品在数字展陈大屏中的排版设想。本页为静态场景示意，当前不包含小程序、二维码上传或实时大屏同步功能。',
    target: '博物馆 / 非遗展示中心 / 校园文化展厅',
    value: '为文化主题展览提供数字视觉呈现与互动设计参考。',
  },
  {
    id: 'store',
    icon: Store,
    title: '文旅景区文创商店',
    status: 'concept',
    desc: '展示生成作品映射到明信片、帆布袋等载体后的视觉构想。页面未接入景区终端、打印设备或商品交易服务。',
    target: '景区文创空间 / 地方文化活动 / 旅游服务场景',
    value: '为文创概念设计和陈列版式提供参考。',
  },
  {
    id: 'social',
    icon: Smartphone,
    title: '线上传播与社交分享',
    status: 'concept',
    desc: '以手机界面示意作品在社交媒体中的展示方式。当前不生成分享链接或可扫描二维码，发布与传播由用户自行完成。',
    target: '传统文化爱好者 / 校园社团 / 内容创作者',
    value: '为文化内容的数字排版与社交平台发布提供视觉参考。',
  },
  {
    id: 'education',
    icon: GraduationCap,
    title: '非遗与美育教学',
    status: 'live',
    desc: '把五种风格的色彩、构图与纹样条目当作可讲的教学材料：课堂上先读风格，再让学生用同一主题生成不同风格的作品做对比，最后用文化说明卡与三段解读讲清工艺背景。',
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
    title: '数字美术馆与虚拟展陈',
    status: 'live',
    desc: '两层三维展馆可直接当作小型数字展厅使用：作品挂上画框、器物摆进展柜，探索模式自由走动，布展模式换画与调整位置，昼夜与机位切换用来做不同气氛的预设。',
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
    title: '个人创作与主题练习',
    status: 'live',
    desc: '单人即可完成从主题到成品的闭环：写主题、可选上传参考图、拉风格影响强度、加构图与负向提示，出图后自动保存，随时回到展厅接着看。',
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

/** 原有三类场景的静态示意（未部署，纯前端构图，不接外部系统）。 */
const SceneMockup = ({ id }: { id: string }) => {
  switch (id) {
    case 'screen':
      return (
        <div className="relative flex h-full w-full items-center justify-center overflow-hidden bg-[#111]">
          <div className="absolute inset-0 bg-gradient-to-b from-gray-900 via-gray-800 to-[#1a1a1a]" />
          <div className="absolute left-1/4 top-0 h-64 w-32 -skew-x-12 bg-white/10 blur-[50px]" />
          <div className="absolute right-1/4 top-0 h-64 w-32 -skew-x-12 bg-white/10 blur-[50px]" />
          <div className="absolute bottom-0 left-0 right-0 h-1/4 bg-black/40 blur-md" />
          <div className="relative z-10 flex aspect-video w-[85%] overflow-hidden rounded border border-gray-800 bg-black shadow-[0_0_50px_rgba(255,255,255,0.1)]">
            <img
              src={import.meta.env.BASE_URL + 'songhua.png'}
              className="h-full w-full object-cover opacity-90 mix-blend-screen"
              alt=""
            />
            <div className="pointer-events-none absolute inset-0 shadow-[inset_0_0_20px_rgba(0,0,0,0.8)]" />
            <div className="absolute bottom-4 left-4 flex gap-2">
              <div className="h-16 w-12 rounded-sm border border-white/20 bg-white/10" />
              <div className="h-16 w-12 rounded-sm border border-white/20 bg-white/10" />
              <div className="h-16 w-12 rounded-sm border border-white/20 bg-white/10" />
            </div>
            <div className="absolute right-4 top-4 font-mono text-xs text-white/50">SCENE PREVIEW</div>
          </div>
          <div className="absolute bottom-4 left-1/4 z-20 h-24 w-12 rounded-t-full bg-black/80 blur-[2px]" />
          <div className="absolute bottom-2 right-1/3 z-20 h-20 w-10 rounded-t-full bg-black/90 blur-[1px]" />
        </div>
      );
    case 'store':
      return (
        <div className="relative flex h-full w-full items-center justify-center overflow-hidden bg-[#E5DACE] p-8">
          <div className="absolute inset-0 bg-[#F2EDE4]" />
          <div className="absolute top-1/3 z-0 h-[10px] w-full bg-[#D4C3AC] shadow-md" />
          <div className="absolute top-2/3 z-0 h-[10px] w-full bg-[#D4C3AC] shadow-md" />
          <div className="absolute left-10 top-[8%] z-10 flex aspect-[3/4] w-24 -rotate-2 flex-col items-center justify-end rounded bg-white pb-2 shadow-md">
            <div className="absolute -top-4 h-4 w-1/2 rounded-t-lg border-x-[3px] border-t-[3px] border-[#D4C3AC]" />
            <img src={import.meta.env.BASE_URL + 'zhuxianzhen.png'} className="aspect-square w-[85%] object-cover opacity-90" alt="" />
          </div>
          <div className="absolute right-16 top-[20%] z-10 flex h-12 w-32 gap-1 rounded bg-white p-1 shadow-sm">
            <img src={import.meta.env.BASE_URL + 'qinghua.png'} className="h-full w-1/2 object-cover" alt="" />
            <img src={import.meta.env.BASE_URL + 'jianzhi.png'} className="h-full w-1/2 object-cover" alt="" />
          </div>
          <div className="absolute left-1/3 top-[42%] z-10 flex aspect-video w-32 rotate-2 items-center justify-center rounded border border-[#e0e0e0] bg-[#fafafa] p-2 shadow-lg">
            <img src={import.meta.env.BASE_URL + 'songhua.png'} className="h-full w-full object-cover" alt="" />
          </div>
          <div className="absolute right-24 top-[50%] z-10 h-16 w-12 rounded bg-white shadow-md">
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
        <div className="relative flex h-full w-full items-center justify-center overflow-hidden bg-[#f0f2f5] p-8">
          <div className="relative z-10 flex h-full aspect-[9/19] -rotate-[5deg] scale-105 flex-col rounded-[2rem] border-[6px] border-gray-800 bg-white p-2 shadow-[0_20px_50px_rgba(0,0,0,0.15)] transition-transform duration-500 hover:rotate-0 hover:scale-110">
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
              <img src={import.meta.env.BASE_URL + 'jianzhi.png'} className="h-full w-full object-cover" alt="" />
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
          <div className="absolute -right-6 top-6 z-0 aspect-[3/4] w-32 rotate-12 rounded border border-black/5 bg-white p-2 shadow-xl">
            <img src={import.meta.env.BASE_URL + 'zhuxianzhen.png'} className="h-full w-full object-cover opacity-80" alt="" />
          </div>
          <div className="absolute -bottom-4 left-4 z-0 aspect-[3/4] w-24 -rotate-12 rounded border border-black/5 bg-white p-2 shadow-xl">
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
  { t: '自动保存', to: '/gallery' },
  { t: '互动赏析', to: '/experience/zhuxianzhen-ruimao' },
  { t: '三维布展', to: '/heritage-gallery' },
  { t: '文创导出', to: '/products' },
];

export default function Scenarios() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 md:py-16">
      <header className="mb-10 text-center">
        <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-[12px] font-medium text-primary">
          应用场景 · 已实现能力 + 应用构想
        </p>
        <h1 className="font-serif text-3xl font-bold text-primary sm:text-4xl md:text-5xl">多场景应用</h1>
        <p className="mx-auto mt-4 max-w-3xl text-[14px] leading-7 text-ink/70">
          分成两类：<span className="font-semibold text-primary">平台现在就能跑通</span>的部分，配真实页面截图并可直接点进对应功能；
          <span className="font-semibold text-primary">尚未对外部署</span>的外部场景，标为「应用构想」，只是前端静态示意，不连接场馆、印厂或交易系统。
        </p>
      </header>

      <div className="mb-10 grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          { v: '5 个', l: '平台已具备的场景' },
          { v: '3 个', l: '外部应用构想' },
          { v: '3 类', l: '互动赏析方式' },
          { v: '8 类', l: '可预览的文创载体' },
        ].map((item) => (
          <div key={item.l} className="rounded-xl border border-gold/25 bg-rice-paper px-3 py-4 text-center">
            <div className="font-serif text-xl font-bold text-primary">{item.v}</div>
            <div className="mt-1 text-[11.5px] text-ink/55">{item.l}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {SCENARIOS.map((scenario) => {
          const Icon = scenario.icon;
          const live = scenario.status === 'live';
          return (
            <article
              key={scenario.id}
              className={cn(
                'flex flex-col overflow-hidden rounded-xl border bg-white/70 shadow-sm transition-shadow hover:shadow-lg',
                live ? 'border-primary/15' : 'border-ink/10',
              )}
            >
              <div className="relative">
                <div className={cn('relative overflow-hidden bg-ink/5', live ? 'aspect-[16/9]' : 'aspect-[4/3]')}>
                  {live && scenario.shot ? (
                    <img
                      src={scenario.shot}
                      alt={scenario.alt ?? scenario.title}
                      loading="lazy"
                      className={cn(
                        'h-full w-full object-cover',
                        scenario.position === 'upper' ? 'object-[center_12%]' : 'object-center',
                      )}
                    />
                  ) : (
                    <SceneMockup id={scenario.id} />
                  )}
                </div>
                <span
                  className={cn(
                    'absolute left-2.5 top-2.5 rounded-sm px-2 py-0.5 text-[10.5px] tracking-wider backdrop-blur',
                    live ? 'bg-primary/90 text-white' : 'bg-white/90 text-ink/70',
                  )}
                >
                  {live ? '平台已具备 · 可进入' : '应用构想 · 未部署'}
                </span>
              </div>

              <div className="flex flex-1 flex-col p-4">
                <div className="mb-2 flex items-center gap-2 text-primary">
                  <Icon className="h-4 w-4" />
                  <h2 className="font-serif text-[15px] font-bold text-ink">{scenario.title}</h2>
                </div>
                <p className="text-[12.5px] leading-6 text-ink/65">{scenario.desc}</p>
                <dl className="mt-3 space-y-1.5 border-t border-primary/10 pt-3 text-[11.5px] leading-5">
                  <div className="flex gap-2">
                    <dt className="w-14 shrink-0 font-serif text-ink/45">适用对象</dt>
                    <dd className="text-ink/70">{scenario.target}</dd>
                  </div>
                  <div className="flex gap-2">
                    <dt className="w-14 shrink-0 font-serif text-ink/45">核心价值</dt>
                    <dd className="text-primary/85">{scenario.value}</dd>
                  </div>
                </dl>
                {live && scenario.to ? (
                  <Link
                    to={scenario.to}
                    className="mt-3 inline-flex items-center gap-1.5 text-[12.5px] text-primary transition-all hover:gap-2.5"
                  >
                    {scenario.cta ?? '进入'}
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                ) : (
                  <span className="mt-3 text-[11.5px] text-ink/40">外部落地需另行对接，本页仅作示意</span>
                )}
              </div>
            </article>
          );
        })}
      </div>

      {/* 当前可用路径 */}
      <section className="mt-14 rounded-2xl border border-primary/10 bg-rice-paper p-5 sm:p-7">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] tracking-[0.3em] text-primary/70">CURRENT FLOW</p>
            <h2 className="mt-1 font-serif text-xl text-ink md:text-2xl">现在就能走通的路径</h2>
          </div>
          <Link to="/creator" className="inline-flex items-center gap-1.5 text-[12.5px] text-primary hover:gap-2.5 transition-all">
            从第一步开始
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
        <ol className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-6">
          {FLOW.map((step, index) => (
            <li key={step.t}>
              <Link
                to={step.to}
                className="group flex h-full items-center gap-2.5 rounded-lg border border-primary/10 bg-white/70 px-3 py-2.5 transition-all hover:border-primary/30 hover:shadow-sm"
              >
                <span className="font-serif text-[11px] text-primary/40">{String(index + 1).padStart(2, '0')}</span>
                <span className="text-[12.5px] font-medium text-ink/80 group-hover:text-primary">{step.t}</span>
              </Link>
            </li>
          ))}
        </ol>
        <p className="mt-4 text-[11.5px] leading-5 text-ink/45">
          注：生成环节需要配置云端图像服务；展厅、三种互动与文创预览在无后端时也能打开内置作品。
        </p>
      </section>

      {/* 部署参考流程（规划） */}
      <section className="mt-10">
        <h3 className="mb-1 font-serif text-lg text-primary">对外部署参考流程（规划）</h3>
        <p className="mb-4 text-[12px] text-ink/50">以下为后续实施路径，不代表当前已部署能力。</p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { n: '1', t: '前端页面部署', d: '配置网页访问与页面内容' },
            { n: '2', t: '生成服务接入', d: '配置服务端接口与模型权限' },
            { n: '3', t: '展示终端适配', d: '按需适配大屏或其他媒介' },
            { n: '4', t: '数据与隐私配置', d: '明确文件留存与用户告知' },
          ].map((step) => (
            <div key={step.n} className="rounded-xl border border-primary/10 bg-white p-4">
              <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-full border border-primary/20 bg-primary/5 font-serif text-sm font-bold text-primary">
                {step.n}
              </div>
              <div className="text-[13px] font-semibold text-ink">{step.t}</div>
              <div className="mt-1 text-[11.5px] leading-5 text-ink/55">{step.d}</div>
            </div>
          ))}
        </div>
      </section>

      <p className="mt-8 text-center text-[11px] leading-5 text-ink/40">
        本页图片为项目页面的真实截图（docs 内随仓库提交），构想类画面为前端静态示意。
        {' '}
        <Link to="/about" className="text-primary/70 hover:text-primary">
          了解当前能力边界
        </Link>
      </p>
    </div>
  );
}