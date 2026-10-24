import { Link } from 'react-router-dom';
import {
  ArrowRight,
  BookOpen,
  Boxes,
  Eye,
  Frame,
  Landmark,
  Palette,
  Save,
  ShoppingBag,
  Sparkles,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { STYLES } from '../data/styleLibrary';

/**
 * 首页配图一律用真实素材，不做虚构界面：
 * - 五种风格图只从 data/styleLibrary.ts 的 STYLES 取（id: zhuxianzhen/bianxiu/songhua/qinghua/jianzhi），
 *   保证「朱仙镇木版年画、汴绣纹样、宋画青绿山水、青花瓷纹样、中国剪纸」一一对应，不再漏掉剪纸。
 * - 功能分区用仓库里已有的真实页面截图（docs/ 下随项目提交的实拍图），文件缺失时构建会直接报错，
 *   因此不会出现「图没了还假装有」的情况。
 */
import creatorShot from '../../../docs/screenshots/creation-workspace.png';
import galleryShot from '../../../docs/interactive_v2/screens/gallery-autosave-runtime.png';
import experienceShot from '../../../docs/interactive_v2/screens/exp-zxz-selected.png';
import storyShot from '../../../docs/screenshots/story-reading.png';
import wanderShot from '../../../docs/interactive_v2/screens/wander-songhua.png';
import heritageShot from '../../../docs/screenshots/heritage-gallery.png';
import interiorShot from '../../../docs/screenshots/heritage-interior.png';
import productShot from '../../../docs/screenshots/creative-products.png';

/** 首页右侧五格的排版参数：A 为竖幅主格，其余四格拼在右半区，比例各不相同但裁切规则统一。 */
const HERO_TILE_CLASS = [
  'col-span-2 aspect-[16/10] sm:col-span-6 sm:row-span-6 sm:aspect-auto',
  'col-span-1 aspect-[3/4] sm:col-span-6 sm:row-span-2 sm:aspect-auto',
  'col-span-1 aspect-[3/4] sm:col-span-3 sm:row-span-2 sm:aspect-auto',
  'col-span-1 aspect-[3/4] sm:col-span-3 sm:row-span-2 sm:aspect-auto',
  'col-span-1 aspect-[3/4] sm:col-span-6 sm:row-span-2 sm:aspect-auto',
];

const JOURNEY = [
  { step: '01', title: '选择风格', desc: '五种传统视觉语言任选其一', to: '/styles', icon: Palette },
  { step: '02', title: 'AI 生成', desc: '主题 + 参考图 + 风格强度', to: '/creator', icon: Sparkles },
  { step: '03', title: '保存作品', desc: '生成即落盘，进入作品展厅', to: '/gallery', icon: Save },
  { step: '04', title: '互动赏析', desc: '热点解读 · 图文阅读 · 漫游', to: '/experience/zhuxianzhen-ruimao', icon: Eye },
  { step: '05', title: '三维布展', desc: '两层展馆，换画与摆器物', to: '/heritage-gallery', icon: Boxes },
  { step: '06', title: '文创应用', desc: '八类载体预览并导出', to: '/products', icon: ShoppingBag },
];

const INTERACTIVE_ENTRIES = [
  {
    tag: '画中有话',
    title: '瑞猫迎春',
    desc: '在同一张年画上点开六处线索，看墨线、套色与边框如何组织画面。',
    to: '/experience/zhuxianzhen-ruimao',
    experienceId: 'zhuxianzhen-ruimao',
    shot: experienceShot,
    alt: '画中有话：朱仙镇木版年画《瑞猫迎春》的热点解读界面',
  },
  {
    tag: '一图一境',
    title: '绣兔牡丹',
    desc: '顺着三折往下读汴绣：一根线怎么当笔用、色阶为什么不是调出来的。',
    to: '/story/bianxiu-xiutu',
    experienceId: 'bianxiu-xiutu',
    shot: storyShot,
    alt: '一图一境：汴绣《绣兔牡丹》的图文阅读页',
  },
  {
    tag: '画境漫游',
    title: '云鹤临水楼',
    desc: '走进宋画青绿山水，可转头、前后移动，也能点开画中线索。',
    to: '/wander/songhua-yunhe',
    experienceId: 'songhua-yunhe',
    shot: wanderShot,
    alt: '画境漫游：置身《云鹤临水楼》的沉浸画面',
  },
];

/**
 * 真实截图统一槽位：16:9。
 * 横向截图用 16:9 裁切，正好把截图顶部那一条站内导航切掉（旧版导航文案不再出现在首页上）；
 * 竖向截图（创作工作台）用 upper 让画面从参数区开始。
 */
function Shot({
  src,
  alt,
  className,
  position = 'center',
}: {
  src: string;
  alt: string;
  className?: string;
  position?: 'center' | 'upper';
}) {
  return (
    <div className={cn('relative overflow-hidden rounded-md bg-ink/5', 'aspect-[16/9]', className)}>
      <img
        src={src}
        alt={alt}
        loading="lazy"
        className={cn(
          'h-full w-full object-cover transition-transform duration-[600ms] group-hover:scale-[1.02]',
          position === 'upper' ? 'object-[center_12%]' : 'object-center',
        )}
      />
    </div>
  );
}

export default function Home() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 md:py-16">
      {/* ── 品牌主视觉：一体化平台 ───────────────────────────────── */}
      <section className="grid items-center gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-12">
        <div className="max-w-xl">
          <p className="inline-flex flex-wrap items-center gap-x-2 gap-y-1 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-[12px] font-medium text-primary">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            传统文化 · 智能创作 · 互动赏析 · 沉浸展陈 · 文创应用
          </p>
          <h1 className="mt-5 font-serif text-4xl font-bold leading-tight text-ink sm:text-5xl">
            纹脉华章
          </h1>
          <p className="mt-3 border-b-2 border-gold/70 pb-3 font-serif text-xl text-primary sm:text-2xl">
            传统文化视觉智能创作与数字应用一体化平台
          </p>
          <p className="mt-5 text-[15px] leading-7 text-ink/70">
            以五种传统视觉风格作为生成约束，先做出作品；作品自动存进作品展厅，可做热点解读、图文阅读与画境漫游；
            再进两层三维展馆布展，最后落到八类文创载体。创作、赏析、展陈与应用在同一条链路上完成，
            让传统文化从<span className="font-semibold text-primary">「被观看」走向「被共创」</span>。
          </p>
          <div className="mt-7 flex flex-wrap items-center gap-3">
            <Link to="/creator" className="btn-chinese group inline-flex items-center gap-2 px-6 py-2.5 text-[15px]">
              立即体验生成
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
            <Link
              to="/gallery"
              className="inline-flex items-center gap-2 rounded border border-primary px-6 py-2.5 text-[15px] font-medium text-primary transition-colors hover:bg-primary/5"
            >
              逛作品展厅
            </Link>
          </div>
          <ul className="mt-7 grid max-w-md grid-cols-2 gap-2 text-[12.5px] text-ink/60 sm:grid-cols-4">
            {['智能创作', '互动赏析', '沉浸展陈', '文创应用'].map((item) => (
              <li key={item} className="flex items-center gap-1.5">
                <span className="h-1 w-1 rounded-full bg-gold" />
                {item}
              </li>
            ))}
          </ul>
        </div>

        {/* 五格画廊拼贴：一格一种风格，顺序即 STYLES 顺序 */}
        <div className="grid h-auto grid-cols-2 gap-2.5 sm:h-[420px] sm:grid-cols-12 sm:grid-rows-6 lg:h-[500px]">
          {STYLES.map((style, index) => (
            <Link
              key={style.id}
              to="/styles"
              className={cn(
                'group relative overflow-hidden rounded-lg bg-ink/5 ring-1 ring-primary/10 transition-shadow hover:shadow-lg hover:ring-primary/25',
                HERO_TILE_CLASS[index],
              )}
              aria-label={`${style.name} · 查看风格库`}
            >
              <img
                src={style.img}
                alt={style.name}
                className="h-full w-full object-cover transition-transform duration-[700ms] group-hover:scale-[1.04]"
                loading={index === 0 ? 'eager' : 'lazy'}
              />
              <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink/75 via-ink/20 to-transparent p-2.5 pt-8">
                <p className={cn('font-serif text-white', index === 0 ? 'text-sm sm:text-base' : 'text-[12px]')}>
                  {style.name}
                </p>
                <p className="mt-0.5 hidden text-[10.5px] text-white/70 sm:block">{style.tag}</p>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ── 五大风格 ──────────────────────────────────────────── */}
      <section className="mt-16 md:mt-20">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] tracking-[0.3em] text-primary/70">STYLE LIBRARY</p>
            <h2 className="mt-1 font-serif text-2xl text-ink md:text-3xl">五种传统视觉语言</h2>
            <p className="mt-2 max-w-2xl text-[13.5px] leading-6 text-ink/60">
              每种风格都是一组可读的色彩、构图与纹样条目，直接转化为生成提示，而不是套一层滤镜。
            </p>
          </div>
          <Link to="/styles" className="inline-flex items-center gap-1.5 text-[13px] text-primary transition-all hover:gap-2.5">
            进入风格库
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {STYLES.map((style) => (
            <Link
              key={style.id}
              to="/styles"
              className="group flex items-start gap-3 rounded-lg border border-primary/10 bg-rice-paper p-3 transition-all hover:-translate-y-0.5 hover:border-primary/25 hover:shadow-md"
            >
              <img
                src={style.img}
                alt={style.name}
                className="h-14 w-11 shrink-0 rounded object-cover ring-1 ring-primary/10"
                loading="lazy"
              />
              <div className="min-w-0">
                <h3 className="font-serif text-[13.5px] font-semibold leading-tight text-ink">{style.name}</h3>
                <p className="mt-0.5 text-[11px] text-primary/70">{style.tag}</p>
                <p className="mt-1.5 line-clamp-2 text-[11.5px] leading-5 text-ink/55">
                  {style.visualFeatures.slice(0, 3).join(' · ')}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ── 创作旅程 ──────────────────────────────────────────── */}
      <section className="mt-16 md:mt-20">
        <div className="mb-5">
          <p className="text-[11px] tracking-[0.3em] text-primary/70">CREATION JOURNEY</p>
          <h2 className="mt-1 font-serif text-2xl text-ink md:text-3xl">一条能走通的创作旅程</h2>
          <p className="mt-2 max-w-2xl text-[13.5px] leading-6 text-ink/60">
            六步都在站内可点，不是流程图上的概念。
          </p>
        </div>
        <ol className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          {JOURNEY.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.step}>
                <Link
                  to={item.to}
                  className="group flex h-full flex-col rounded-lg border border-primary/10 bg-white/60 p-3.5 transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-serif text-[11px] tracking-widest text-primary/50">{item.step}</span>
                    <Icon className="h-4 w-4 text-primary/60 transition-colors group-hover:text-primary" />
                  </div>
                  <span className="mt-2 font-serif text-[14px] font-semibold text-ink">{item.title}</span>
                  <span className="mt-1 text-[11.5px] leading-5 text-ink/55">{item.desc}</span>
                </Link>
              </li>
            );
          })}
        </ol>
      </section>

      {/* ── AI 生成 + 自动保存/展厅 ─────────────────────────────── */}
      <section className="mt-16 grid gap-5 md:mt-20 lg:grid-cols-2">
        <article className="group rounded-2xl border border-primary/10 bg-white/70 p-4 shadow-sm transition-shadow hover:shadow-lg sm:p-5">
          <div className="mb-4 flex items-center gap-2 text-primary">
            <Sparkles className="h-4 w-4" />
            <h2 className="font-serif text-lg font-bold">AI 生成与参考图控制</h2>
          </div>
          <Shot
            src={creatorShot}
            alt="智能生成工作台：主题输入、参考图上传与风格参数"
            position="upper"
          />
          <p className="mt-4 text-[13px] leading-6 text-ink/65">
            填入主题、可选上传参考图（PNG/JPG，≤10 MB），再调风格影响强度、构图提示与负向提示词；
            服务端把参数组织成提示后调用 Qwen Image 3.0 出图，并在结果里回报参考图是否真正参与推理。
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {['主题描述', '参考图上传', '风格影响强度', '构图提示', '负向提示'].map((tag) => (
              <span key={tag} className="rounded-sm border border-primary/15 bg-primary/5 px-2 py-0.5 text-[11px] text-primary/80">
                {tag}
              </span>
            ))}
          </div>
          <Link to="/creator" className="mt-4 inline-flex items-center gap-1.5 text-[13px] text-primary hover:gap-2.5 transition-all">
            打开生成工作台
            <ArrowRight className="h-4 w-4" />
          </Link>
        </article>

        <article className="group rounded-2xl border border-primary/10 bg-white/70 p-4 shadow-sm transition-shadow hover:shadow-lg sm:p-5">
          <div className="mb-4 flex items-center gap-2 text-primary">
            <Save className="h-4 w-4" />
            <h2 className="font-serif text-lg font-bold">自动保存与作品展厅</h2>
          </div>
          <Shot src={galleryShot} alt="作品展厅：自动保存的作品与内置案例并列展示" />
          <p className="mt-4 text-[13px] leading-6 text-ink/65">
            生成成功即由后端落盘为展厅案例：参考图、成图与文化说明卡一起保存，展厅里以「自动保存」状态出现；
            需要互动热点时再补标注。五件内置作品不连后端也能离线浏览。
          </p>
          <ul className="mt-3 space-y-1.5 text-[12px] text-ink/60">
            <li>· 每件作品带风格来源与生成参数说明，可回看</li>
            <li>· 新作品要显示在展厅，需要本机后端在运行</li>
          </ul>
          <Link to="/gallery" className="mt-4 inline-flex items-center gap-1.5 text-[13px] text-primary hover:gap-2.5 transition-all">
            进入作品展厅
            <ArrowRight className="h-4 w-4" />
          </Link>
        </article>
      </section>

      {/* ── 三种互动赏析 ──────────────────────────────────────── */}
      <section className="mt-16 md:mt-20">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] tracking-[0.3em] text-primary/70">INTERACTION</p>
            <h2 className="mt-1 font-serif text-2xl text-ink md:text-3xl">同一件作品，三种读法</h2>
          </div>
          <Link to="/gallery" className="inline-flex items-center gap-1.5 text-[13px] text-primary transition-all hover:gap-2.5">
            更多互动作品
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {INTERACTIVE_ENTRIES.map((item) => (
            <Link
              key={item.tag}
              to={item.to}
              className="group flex flex-col overflow-hidden rounded-lg border border-primary/15 bg-white/60 shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg"
            >
              <div className="relative">
                <Shot src={item.shot} alt={item.alt} />
                <span className="absolute left-2.5 top-2.5 rounded-sm bg-white/90 px-2 py-0.5 text-[10.5px] tracking-wider text-primary backdrop-blur">
                  {item.tag}
                </span>
              </div>
              <div className="flex flex-1 flex-col p-4">
                <h3 className="font-serif text-base text-ink">{item.title}</h3>
                <p className="mt-1.5 text-[12.5px] leading-6 text-ink/60">{item.desc}</p>
                <span className="mt-auto inline-flex items-center gap-1.5 pt-3 text-[12px] text-primary opacity-80 transition group-hover:gap-2.5 group-hover:opacity-100">
                  走进去
                  <ArrowRight className="h-3.5 w-3.5" />
                </span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ── 沉浸展陈 + 文创应用 ───────────────────────────────── */}
      <section className="mt-16 grid gap-5 md:mt-20 lg:grid-cols-2">
        <article className="group overflow-hidden rounded-2xl border border-primary/10 bg-white/70 shadow-sm transition-shadow hover:shadow-lg">
          <div className="relative">
            <Shot src={interiorShot} alt="纹脉展馆一层内景：画框、器物与展柜" />
            <div className="absolute bottom-3 right-3 hidden w-[34%] overflow-hidden rounded border-2 border-white/85 shadow-lg sm:block">
              <img src={heritageShot} alt="纹脉展馆建筑外观" className="aspect-[4/3] w-full object-cover" loading="lazy" />
            </div>
          </div>
          <div className="p-4 sm:p-5">
            <div className="mb-2 flex items-center gap-2 text-primary">
              <Landmark className="h-4 w-4" />
              <h2 className="font-serif text-lg font-bold">纹脉展馆 · 沉浸展陈</h2>
            </div>
            <p className="text-[13px] leading-6 text-ink/65">
              两层微缩展馆把作品真正挂上墙：探索模式可走、可看、可切第一/第三人称，靠近画框自动弹出文化卡；
              布展模式能点画框换画、拖动位置，并从器物图库摆放展陈道具；昼夜与机位可切换，灵宠可领路。
            </p>
            <Link to="/heritage-gallery" className="mt-4 inline-flex items-center gap-1.5 text-[13px] text-primary hover:gap-2.5 transition-all">
              进入三维展馆
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </article>

        <article className="group overflow-hidden rounded-2xl border border-primary/10 bg-white/70 shadow-sm transition-shadow hover:shadow-lg">
          <Shot src={productShot} alt="文创转化：作品映射到明信片、海报等载体" position="upper" />
          <div className="p-4 sm:p-5">
            <div className="mb-2 flex items-center gap-2 text-primary">
              <ShoppingBag className="h-4 w-4" />
              <h2 className="font-serif text-lg font-bold">文创转化 · 载体预览</h2>
            </div>
            <p className="text-[13px] leading-6 text-ink/65">
              把最近一件生成作品映射到八类预设载体——文旅明信片、数字海报、帆布袋、文创书签、陶瓷杯垫、
              手机分享图、数字展陈屏与景区纪念票，按载体比例预览版式，并可导出 1600×1200 的 PNG 效果图。
            </p>
            <p className="mt-2 text-[11.5px] leading-5 text-ink/45">
              为设计预览用途；不含实体生产、订单或印刷服务。
            </p>
            <Link to="/products" className="mt-4 inline-flex items-center gap-1.5 text-[13px] text-primary hover:gap-2.5 transition-all">
              打开文创转化
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </article>
      </section>

      {/* ── 数据与小入口 ──────────────────────────────────────── */}
      <section className="mt-14 rounded-xl bg-primary px-6 py-7 text-white shadow-[0_10px_30px_rgba(158,36,27,0.2)]">
        <div className="flex flex-wrap items-center justify-between gap-6">
          {[
            { v: '5 种', l: '传统视觉风格条目' },
            { v: '8 类', l: '文创载体预览模板' },
            { v: '5 件', l: '内置作品与互动解读' },
            { v: '2 层', l: '三维展馆与布展器物' },
          ].map((stat) => (
            <div key={stat.l} className="flex-1 text-center">
              <div className="font-serif text-2xl font-bold text-gold md:text-3xl">{stat.v}</div>
              <div className="mt-1 text-[12px] text-white/85">{stat.l}</div>
            </div>
          ))}
        </div>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 border-t border-white/15 pt-5 text-[12.5px]">
          <Link to="/scenarios" className="inline-flex items-center gap-1.5 text-white/90 hover:text-gold transition-colors">
            <Boxes className="h-3.5 w-3.5" /> 应用场景与落地路径
          </Link>
          <Link to="/about" className="inline-flex items-center gap-1.5 text-white/90 hover:text-gold transition-colors">
            <BookOpen className="h-3.5 w-3.5" /> 关于项目与能力边界
          </Link>
          <span className="inline-flex items-center gap-1.5 text-white/55">
            <Frame className="h-3.5 w-3.5" /> 生成需配置云端图像服务，展厅与互动可离线浏览
          </span>
        </div>
      </section>
    </div>
  );
}