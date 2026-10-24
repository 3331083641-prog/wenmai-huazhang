import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Boxes,
  BookOpen,
  CloudCog,
  Eye,
  Frame,
  Heart,
  Images,
  Layers,
  Palette,
  Save,
  ShoppingBag,
  SlidersHorizontal,
  Sparkles,
  Target,
  Wand2,
} from 'lucide-react';
import { STYLES } from '../data/styleLibrary';

/**
 * 关于项目：固定 10 个方面，每个一屏内可读完，不写技术长文。
 * 数量类信息（15 个画框 / 14 件器物 / 2 层）以仓库现有配置为准，不臆造新数字。
 */
import cultureCardShot from '../../../docs/screenshots/culture-card.png';

function Block({
  no,
  icon,
  title,
  subtitle,
  children,
  className,
}: {
  no: string;
  icon: ReactNode;
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={className}>
      <div className="rounded-xl border border-primary/10 bg-white/70 p-4 sm:p-5">
        <div className="mb-2.5 flex items-baseline gap-2.5">
          <span className="font-serif text-[11px] tracking-widest text-primary/40">{no}</span>
          <span className="text-primary">{icon}</span>
          <h2 className="font-serif text-[16px] font-bold text-ink">{title}</h2>
          {subtitle && <span className="ml-auto hidden text-[11px] text-ink/35 sm:block">{subtitle}</span>}
        </div>
        <div className="text-[12.5px] leading-6 text-ink/65">{children}</div>
      </div>
    </section>
  );
}

const IMPLEMENTED = [
  '五种传统视觉风格条目：木版年画、汴绣、青绿山水、青花瓷纹样、剪纸，各自带色彩、构图、纹样与提示特征',
  'Qwen Image 3.0 文生图与参考图创作，可填主题、上限 10 MB 的参考图、风格影响强度、构图提示与负向提示',
  '生成结果回报参考图是否真正参与推理，风格强度以提示词约束而非暗改采样参数',
  '本机 Qwen3-VL 读图产出结构化视觉解读；服务不可用时回退为主题 + 风格条目模板，不阻断创作',
  '成图、参考图与文化说明卡由后端落盘为展厅案例，展厅里以「自动保存」状态出现',
  '三种互动赏析：画中有话（热点解读）、一图一境（分段图文）、画境漫游（第一人称入画）',
  '两层三维展馆：15 个画框、12 面墙、14 件可摆放器物，探索/布展双模式，昼夜与机位切换，灵宠领路',
  '八类文创载体版式预览，可导出 1600 × 1200 PNG 效果图',
];

const LIMITS = [
  '生成需要配置云端图像服务与密钥；未配置时只保留内置案例与互动内容',
  '没有账户、数据库与云端作品库，新作品要到展厅显示需本机后端在运行',
  '互动热点的坐标由视觉候选加人工裁切复核得到，新增作品默认先以「热点待标注」出现',
  '三维展馆、外部场馆、印厂与交易系统均未对接；应用场景页的外部件属于「应用构想」',
  '演示素材来源与授权由团队逐项核验，不主张第三方历史图像或文化作品的版权',
];

const EXTENSIONS = [
  '扩充传统视觉风格条目，并为每条文化描述补充可追溯来源',
  '多参考图融合与更细粒度的局部编辑',
  '文化知识检索增强，把说明卡与展馆讲解接上可引用资料',
  '多用户作品管理与文旅展示终端适配',
];

export default function About() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 md:py-16">
      <header className="mb-8 text-center">
        <p className="mb-3 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-[12px] font-medium text-primary">
          关于项目 · 能力清单与边界
        </p>
        <h1 className="font-serif text-3xl font-bold text-primary sm:text-4xl md:text-5xl">关于纹脉华章</h1>
        <p className="mx-auto mt-4 max-w-3xl text-[14px] leading-7 text-ink/70">
          一个把「传统视觉风格 → AI 创作 → 作品收藏 → 互动赏析 → 三维展陈 → 文创载体」串成一条链路的网页平台。
          下面按十个方面说明做了什么、怎么做的、以及现在还没做什么。
        </p>
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          {['智能创作', '互动赏析', '沉浸展陈', '文创应用'].map((tag) => (
            <span key={tag} className="rounded-full border border-gold/40 bg-rice-paper px-3 py-1 text-[11.5px] text-primary/80">
              {tag}
            </span>
          ))}
        </div>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <Block no="01" icon={<Target className="h-4 w-4" />} title="项目定位" subtitle="POSITIONING" className="lg:col-span-2">
          <p>
            面向传统文化数字创作与传播：让不具备绘画基础的人也能用传统视觉语言做出作品，并让作品在站内继续走完
            赏析与展陈。定位不是「又一个 AI 绘画框」，而是把生成结果当作可被反复阅读、布置与应用的内容资产。
          </p>
          <p className="mt-2 text-ink/55">
            受众：设计类与美育课堂、非遗展示与校园展陈、个人传统文化爱好者、文创方案早期推演。
          </p>
        </Block>

        <Block no="02" icon={<Layers className="h-4 w-4" />} title="已实现功能" subtitle="SHIPPED" className="lg:col-span-2">
          <ul className="grid gap-1.5 sm:grid-cols-2">
            {IMPLEMENTED.map((item) => (
              <li key={item} className="flex gap-2">
                <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-primary/60" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </Block>

        <Block no="03" icon={<Palette className="h-4 w-4" />} title="五种传统视觉风格" subtitle="STYLES">
          <ul className="space-y-2">
            {STYLES.map((style) => (
              <li key={style.id} className="flex items-start gap-2.5">
                <img src={style.img} alt={style.name} className="h-9 w-7 shrink-0 rounded object-cover ring-1 ring-primary/10" loading="lazy" />
                <div className="min-w-0">
                  <p className="font-serif text-[12.5px] font-semibold text-ink">{style.name}</p>
                  <p className="text-[11px] leading-5 text-ink/50">{style.visualFeatures.slice(0, 3).join(' · ')}</p>
                </div>
              </li>
            ))}
          </ul>
          <Link to="/styles" className="mt-3 inline-flex items-center gap-1.5 text-[12px] text-primary hover:gap-2.5 transition-all">
            查看风格库
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </Block>

        <Block no="04" icon={<Sparkles className="h-4 w-4" />} title="AI 生成与视觉理解" subtitle="GENERATION + VISION">
          <p>
            前端提交主题、参考图与参数，FastAPI 校验后组织成提示，调用 Qwen Image 3.0 出图；生成完成后由本机
            Ollama 上的 Qwen3-VL 读图，输出画面元素、工艺要点与关键词等结构化解读，再合成文化说明卡。
          </p>
          <p className="mt-2 text-ink/55">
            视觉服务不可用时按主题与风格条目生成模板说明，作品照常保留；参考图是否参与推理由服务端回报，不做推测。
          </p>
          <img
            src={cultureCardShot}
            alt="文化说明卡：视觉解读与风格来源"
            loading="lazy"
            className="mt-3 aspect-[16/9] w-full rounded object-cover object-top ring-1 ring-primary/10"
          />
        </Block>

        <Block no="05" icon={<Save className="h-4 w-4" />} title="作品展厅与自动保存" subtitle="ARCHIVE">
          <p>
            生成成功后后端把成图、参考图与文化卡一起落盘成案例目录，展厅按时间读取并以「自动保存」标记；
            五件内置作品可离线打开。当前作品是文件级存档，没有账户与云端数据库。
          </p>
          <ul className="mt-2 space-y-1 text-[11.5px] text-ink/50">
            <li>· 内置 5 件作品含完整互动数据</li>
            <li>· 自动保存作品的热点需事后标注</li>
          </ul>
          <Link to="/gallery" className="mt-3 inline-flex items-center gap-1.5 text-[12px] text-primary hover:gap-2.5 transition-all">
            进入作品展厅
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </Block>

        <Block no="06" icon={<Eye className="h-4 w-4" />} title="三种互动赏析方式" subtitle="INTERACTION">
          <ul className="space-y-2">
            {[
              { name: '画中有话', desc: '在画面上点开热点，逐点看墨线、套色与纹样', to: '/experience/zhuxianzhen-ruimao' },
              { name: '一图一境', desc: '分段图文往下读工艺背景与观看顺序', to: '/story/bianxiu-xiutu' },
              { name: '画境漫游', desc: '第一人称走进画面，可转头、前后移动', to: '/wander/songhua-yunhe' },
            ].map((item) => (
              <li key={item.name}>
                <Link to={item.to} className="group flex items-start gap-2 rounded-md px-1 py-1 transition-colors hover:bg-primary/5">
                  <BookOpen className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary/60" />
                  <span>
                    <span className="font-serif text-[12.5px] font-semibold text-ink group-hover:text-primary">{item.name}</span>
                    <span className="ml-1.5 text-[11.5px] text-ink/55">{item.desc}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </Block>

        <Block no="07" icon={<Boxes className="h-4 w-4" />} title="三维展馆与布展 DIY" subtitle="3D GALLERY">
          <p>
            两层微缩展馆按展厅尺寸建模：15 个画框分布在 12 面墙上，探索模式可走动、切第一/第三人称、靠近画框弹出文化卡；
            布展模式能点画框换画、拖动位置，并从 14 件非遗器物中摆放道具，昼夜与机位可切换。
          </p>
          <p className="mt-2 text-[11.5px] text-ink/50">
            展馆与漫游页为沉浸式全屏，不套站内导航；返回入口在页面左上角。
          </p>
          <Link to="/heritage-gallery" className="mt-3 inline-flex items-center gap-1.5 text-[12px] text-primary hover:gap-2.5 transition-all">
            进入三维展馆
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </Block>

        <Block no="08" icon={<ShoppingBag className="h-4 w-4" />} title="文创价值" subtitle="VALUE">
          <ul className="space-y-1.5">
            <li>· 作品可直接映射到八类载体，做打样前的版式筛选</li>
            <li>· 风格条目与说明卡可作为课堂讲解材料</li>
            <li>· 展馆布展能把一批作品组织成可参观的线上展厅</li>
          </ul>
          <p className="mt-2 text-[11.5px] text-ink/45">
            提供的是预览与导出，不含实体生产、订单、印刷或销售服务。
          </p>
          <Link to="/products" className="mt-3 inline-flex items-center gap-1.5 text-[12px] text-primary hover:gap-2.5 transition-all">
            打开文创转化
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </Block>

        <Block no="09" icon={<CloudCog className="h-4 w-4" />} title="技术架构简图" subtitle="ARCHITECTURE" className="lg:col-span-2">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
            {[
              { icon: <SlidersHorizontal className="h-4 w-4" />, t: '前端页面', d: 'React 19 · Vite · TS · Tailwind 4 · Router 7' },
              { icon: <CloudCog className="h-4 w-4" />, t: '生成服务', d: 'FastAPI · Pydantic · 提示组织与校验' },
              { icon: <Wand2 className="h-4 w-4" />, t: '图像生成', d: 'Qwen Image 3.0 文生图 / 参考图创作' },
              { icon: <Eye className="h-4 w-4" />, t: '视觉解读', d: '本机 Ollama · Qwen3-VL 读图' },
              { icon: <Images className="h-4 w-4" />, t: '文件存档', d: '案例目录落盘 → 展厅 / 展馆 / 文创' },
            ].map((node) => (
              <div key={node.t} className="rounded-lg border border-primary/10 bg-rice-paper px-3 py-2.5 text-center">
                <div className="mx-auto mb-1.5 flex h-7 w-7 items-center justify-center rounded-full bg-primary/5 text-primary">
                  {node.icon}
                </div>
                <div className="text-[12px] font-semibold text-ink">{node.t}</div>
                <div className="mt-0.5 text-[10.5px] leading-4 text-ink/50">{node.d}</div>
              </div>
            ))}
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-primary/10 bg-primary/5 px-3 py-2 text-[11px] text-ink/55">
            <span className="inline-flex items-center gap-1.5 text-primary/80">
              <Boxes className="h-3.5 w-3.5" /> 三维部分
            </span>
            three.js · React Three Fiber · drei（GLB 展馆模型 + 画框 / 器物 / 灵宠）
            <span className="inline-flex items-center gap-1.5 text-primary/80">
              <Frame className="h-3.5 w-3.5" /> 输出
            </span>
            PNG 效果图 · 展厅案例 · 展馆布展
          </div>
        </Block>

        <Block no="10" icon={<Heart className="h-4 w-4" />} title="限制与扩展方向" subtitle="LIMITS & NEXT" className="lg:col-span-2">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="mb-1.5 font-serif text-[12px] font-semibold text-primary/80">当前限制</p>
              <ul className="space-y-1.5">
                {LIMITS.map((item) => (
                  <li key={item} className="flex gap-2 text-ink/60">
                    <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-ink/30" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="mb-1.5 font-serif text-[12px] font-semibold text-primary/80">后续扩展</p>
              <ul className="space-y-1.5">
                {EXTENSIONS.map((item) => (
                  <li key={item} className="flex gap-2 text-ink/60">
                    <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-gold" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Block>
      </div>

      <div className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-[12px] text-ink/50">
        <Link to="/creator" className="inline-flex items-center gap-1.5 text-primary/80 hover:text-primary transition-colors">
          <Sparkles className="h-3.5 w-3.5" /> 开始创作
        </Link>
        <Link to="/scenarios" className="inline-flex items-center gap-1.5 text-primary/80 hover:text-primary transition-colors">
          <Boxes className="h-3.5 w-3.5" /> 应用场景
        </Link>
        <span>图片为项目页面真实截图；数量以当前仓库配置为准。</span>
      </div>
    </div>
  );
}