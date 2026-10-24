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
import galleryExterior from '../../../docs/screenshots/vnext/gallery-exterior.jpg';

/**
 * 首页「进入画里，再看一遍」的三件互动作品
 * 取各自作品的成图（experience.artworkUrl），保证在 16:10 槽位内比例一致
 */
const INTERACTIVE_ENTRIES = [
  {
    to: '/experience/zhuxianzhen-ruimao',
    experienceId: 'zhuxianzhen-ruimao',
    tag: '画中有话',
    styleBadge: '朱仙镇木版年画',
    title: '瑞猫迎春',
    desc: '在年画上点开六处线索，看粗黑墨线与矿物套色如何勾勒吉祥瑞猫与传统门神构图。',
  },
  {
    to: '/story/bianxiu-xiutu',
    experienceId: 'bianxiu-xiutu',
    tag: '一图一境',
    styleBadge: '汴绣纹样',
    title: '绣兔牡丹',
    desc: '顺着三折叙事往下读汴绣：丝线如何当笔、色阶如何自然过渡，以及宋绣典雅温润之美的传承。',
  },
  {
    to: '/wander/songhua-yunhe',
    experienceId: 'songhua-yunhe',
    tag: '画境漫游',
    styleBadge: '宋画青绿山水',
    title: '云鹤临水楼',
    desc: '推进镜头沉浸入画：近景苍松翠石掠过、远峦重重退开，自由环顾漫游，探寻画中隐秘细节。',
  },
];

/**
 * 全面补齐的平台核心能力矩阵
 */
const CORE_CAPABILITIES = [
  {
    icon: Palette,
    title: '五大传统视觉风格库',
    desc: '严选朱仙镇木版年画、汴绣纹样、宋画青绿山水、青花瓷纹样与中国剪纸，提炼色彩、构图、纹样与笔法特征，为 AI 创作提供结构化文化约束。',
    tag: '风格体系',
  },
  {
    icon: Sparkles,
    title: 'Qwen Image 3.0 多模态创作',
    desc: '支持「输入文本主题 + 传统文化参考图 + 风格强度约束」，实现可控的多模态视觉生成，真实回报参考图参与推理的置信状态。',
    tag: '智能生成',
  },
  {
    icon: Cpu,
    title: 'Qwen3-VL 视觉理解与文化卡',
    desc: '接入本地多模态大模型，对生成作品进行自动视觉特征提取、文化意涵解读与应用建议，一键导出精致排版的双语 CultureCard。',
    tag: '文化解读',
  },
  {
    icon: Eye,
    title: '作品展厅与多维互动',
    desc: '作品生成即落盘，自动加入作品展厅；后台流水线自动构建画中有话、一图一境与 2.5D 画境漫游，无需重启即可多维度深度赏析。',
    tag: '互动赏析',
  },
  {
    icon: Boxes,
    title: '三维纹脉展馆与布展 DIY',
    desc: '双层中式虚拟艺术展馆，支持自由漫游、15 处自定义画框换画、14 件历史器物陈设布置、昼夜光影切换与灵宠纹纹伴游引导。',
    tag: '虚拟空间',
  },
  {
    icon: Layout,
    title: '文创转化与多载体打样',
    desc: '将作品一键映射到文旅明信片、数字海报、帆布袋、书签、杯垫、手机壁纸等 8 类预设载体，支持按比例预览并导出高清应用图。',
    tag: '文创应用',
  },
];

export default function Home() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-12 md:py-20 lg:py-24">
      {/* ── Hero Section ────────────────────────────────────────── */}
      <div className="grid lg:grid-cols-2 gap-12 lg:gap-8 items-center mb-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="max-w-2xl"
        >
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-primary/20 bg-primary/5 text-primary text-xs md:text-sm font-medium mb-6">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
            传统文化视觉创作 · 智能理解 · 沉浸展陈 · 文创应用
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-serif font-bold leading-[1.2] mb-6 text-ink">
            纹脉华章 <br />
            <span className="text-2xl sm:text-3xl lg:text-4xl text-primary font-medium border-b-2 border-gold pb-1.5 inline-block mt-3">
              传统文化视觉智能创作与文创应用平台
            </span>
          </h1>
          <p className="text-base sm:text-lg lg:text-xl text-ink/75 mb-10 leading-relaxed font-sans">
            以人工智能多模态图像生成与视觉理解为核心，融汇传统文化经典视觉风格与现代数字艺术。让中华优秀传统文化从<span className="font-semibold text-primary">“被观看”走向“被共创”</span>，实现从创意灵感、智能创作、多维互动到三维虚拟展陈与文创落地的完整闭环。
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <Link
              to="/creator"
              className="group relative inline-flex items-center gap-2.5 px-8 py-3.5 btn-chinese text-base md:text-lg transition-all shadow-md hover:shadow-xl"
            >
              <span className="relative">立即体验生成</span>
              <ArrowRight className="relative w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link
              to="/styles"
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded border border-primary/30 text-primary font-medium text-base md:text-lg bg-white/60 hover:bg-primary/5 hover:border-primary transition-all"
            >
              浏览五大风格库
            </Link>
            <Link
              to="/heritage-gallery"
              className="inline-flex items-center gap-1.5 text-ink/65 hover:text-primary text-sm font-medium transition-colors ml-1"
            >
              <Compass className="w-4 h-4 text-gold" />
              进入三维展馆
            </Link>
          </div>
        </motion.div>

        {/* ── 右侧文化图片拼贴：保留经典的层叠与悬浮层次，修正五大风格完整展现 ── */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, delay: 0.2 }}
          className="relative lg:ml-auto w-full h-[520px]"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-[#9E241B]/12 via-gold/10 to-transparent rounded-full blur-[90px] pointer-events-none"></div>

          <div className="relative w-full h-full">
            {/* 风格 1：Main Center - 朱仙镇木版年画 (主体竖幅大图) */}
            <div className="absolute top-[8%] left-[16%] w-[58%] aspect-[3/4] rounded-2xl overflow-hidden shadow-2xl border-4 border-white/95 z-20 group hover:-translate-y-2 transition-all duration-500 bg-white">
              <img
                src={import.meta.env.BASE_URL + "zhuxianzhen.png"}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                alt="朱仙镇木版年画"
              />
              <div className="absolute bottom-3 left-3 bg-white/90 backdrop-blur-md px-2.5 py-1 rounded shadow-xs text-xs font-serif text-ink border border-primary/20">
                朱仙镇木版年画
              </div>
            </div>

            {/* 风格 2：Top Right Float - 宋画青绿山水 */}
            <div className="absolute top-[4%] right-[3%] w-[38%] aspect-square rounded-2xl overflow-hidden shadow-xl border-4 border-white/80 z-10 opacity-95 group hover:opacity-100 hover:-translate-y-2 transition-all duration-500 bg-white">
              <img
                src={import.meta.env.BASE_URL + "songhua.png"}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                alt="宋画青绿山水"
              />
              <div className="absolute bottom-2.5 right-2.5 bg-black/60 backdrop-blur px-2 py-0.5 rounded text-[11px] text-white/90 font-serif">
                宋画青绿山水
              </div>
            </div>

            {/* 风格 3：Bottom Right Float - 汴绣纹样 */}
            <div className="absolute bottom-[6%] right-[6%] w-[42%] aspect-[4/3] rounded-2xl overflow-hidden shadow-xl border-4 border-white/80 z-30 opacity-95 group hover:opacity-100 hover:-translate-y-2 transition-all duration-500 bg-white">
              <img
                src={import.meta.env.BASE_URL + "bianxiu.png"}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                alt="汴绣纹样"
              />
              <div className="absolute bottom-2.5 left-2.5 bg-white/90 backdrop-blur px-2 py-0.5 rounded text-[11px] text-ink font-serif border border-primary/10">
                汴绣纹样
              </div>
            </div>

            {/* 风格 4：Bottom Left Float - 青花瓷纹样 (圆形瓷盘) */}
            <div className="absolute bottom-[4%] left-[3%] w-[34%] aspect-square rounded-full overflow-hidden shadow-2xl border-[5px] border-white z-40 opacity-95 group hover:-rotate-6 hover:scale-105 transition-all duration-500 bg-white">
              <img
                src={import.meta.env.BASE_URL + "qinghua.png"}
                className="w-full h-full object-cover"
                alt="青花瓷纹样"
              />
              <div className="absolute inset-x-0 bottom-2.5 text-center">
                <span className="bg-primary/90 backdrop-blur-xs text-white text-[10.5px] px-2.5 py-0.5 rounded-full font-serif shadow-xs">
                  青花瓷纹样
                </span>
              </div>
            </div>

            {/* 风格 5：Top Left Float - 中国剪纸 (精修补充，使五大文化风格齐备，不破原有和谐构图) */}
            <div className="absolute top-[2%] left-[1%] w-[27%] aspect-square rounded-2xl overflow-hidden shadow-lg border-[3px] border-white/85 z-10 opacity-90 group hover:opacity-100 hover:scale-105 hover:-translate-y-1 transition-all duration-500 bg-[#FFF5F2]">
              <img
                src={import.meta.env.BASE_URL + "jianzhi.png"}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                alt="中国剪纸"
              />
              <div className="absolute top-2 left-2 bg-[#9E241B]/90 backdrop-blur-xs text-white text-[10px] px-1.5 py-0.5 rounded-xs font-serif shadow-xs">
                中国剪纸
              </div>
            </div>
          </div>

          {/* Floating cultural badge */}
          <div className="absolute top-1/2 -right-3 -translate-y-1/2 bg-white/95 backdrop-blur-md px-4 py-3.5 rounded-xl shadow-[0_12px_32px_rgba(158,36,27,0.18)] flex items-center gap-3.5 z-50 border border-gold/30">
            <div className="w-11 h-11 rounded-full bg-gold/15 flex items-center justify-center shrink-0">
              <Sparkles className="text-gold w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] text-primary/70 tracking-wider">五大传统风格</p>
              <p className="font-serif font-bold text-sm text-ink">Qwen 3.0 智能生成</p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* ── 五大传统风格快捷栏 ───────────────────────────────────── */}
      <div className="mb-24 bg-white/50 border border-gold/25 rounded-2xl p-6 shadow-xs">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-4 bg-primary rounded-full"></span>
            <span className="text-sm font-serif font-bold text-ink/80 tracking-wide">
              五大传统文化视觉风格：
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-4 sm:gap-6 justify-center">
            {[
              { id: 'zhuxianzhen', name: '朱仙镇木版年画', img: 'zhuxianzhen.png' },
              { id: 'bianxiu', name: '汴绣纹样', img: 'bianxiu.png' },
              { id: 'songhua', name: '宋画青绿山水', img: 'songhua.png' },
              { id: 'qinghua', name: '青花瓷纹样', img: 'qinghua.png' },
              { id: 'jianzhi', name: '中国剪纸', img: 'jianzhi.png' },
            ].map((style) => (
              <Link
                key={style.id}
                to="/styles"
                className="group flex items-center gap-2.5 px-3 py-1.5 rounded-full border border-primary/15 bg-white/80 hover:border-primary hover:bg-primary/5 hover:shadow-sm transition-all"
              >
                <div className="w-7 h-7 rounded-full overflow-hidden border border-gold/40 shrink-0">
                  <img
                    src={import.meta.env.BASE_URL + style.img}
                    className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
                    alt={style.name}
                  />
                </div>
                <span className="text-xs font-serif text-ink/75 group-hover:text-primary transition-colors">
                  {style.name}
                </span>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* ── 进入画里，再看一遍（三种互动体验精选） ─────────────────── */}
      <div className="mb-24">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="mb-1.5 text-xs font-medium tracking-[0.3em] text-primary/75">
              纹脉华章 · 多维文化赏析
            </p>
            <h2 className="font-serif text-2xl md:text-3xl font-bold text-ink">
              进入画里，再看一遍
            </h2>
          </div>
          <Link
            to="/gallery"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:gap-2.5 transition-all"
          >
            浏览作品展厅全部作品
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {INTERACTIVE_ENTRIES.map((item) => {
            const experience = experienceById.get(item.experienceId);
            const src = experience?.artworkUrl || '';
            return (
              <Link
                key={item.tag}
                to={item.to}
                className="group flex flex-col overflow-hidden rounded-2xl border border-primary/15 bg-white/70 shadow-xs transition duration-300 hover:-translate-y-1 hover:shadow-xl hover:border-primary/30"
              >
                <div className="relative aspect-[16/10] overflow-hidden bg-ink/5">
                  {src && (
                    <img
                      src={src}
                      alt={`${item.title} · ${experience?.styleName ?? ''}`}
                      className="h-full w-full object-cover transition duration-700 group-hover:scale-[1.04]"
                      loading="lazy"
                    />
                  )}
                  <span className="absolute left-3 top-3 rounded-md bg-white/95 px-2.5 py-1 text-[11px] font-medium tracking-wider text-primary backdrop-blur shadow-xs">
                    {item.tag}
                  </span>
                  <span className="absolute right-3 top-3 rounded-md bg-black/50 px-2 py-0.5 text-[10px] tracking-wider text-white backdrop-blur">
                    {item.styleBadge}
                  </span>
                </div>
                <div className="flex flex-1 flex-col p-5">
                  <h3 className="font-serif text-lg font-bold text-ink group-hover:text-primary transition-colors">
                    {item.title}
                  </h3>
                  <p className="mt-2 text-xs md:text-[13px] leading-relaxed text-ink/65 line-clamp-2">
                    {item.desc}
                  </p>
                  <div className="mt-4 pt-3 border-t border-primary/10 flex items-center justify-between">
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-primary transition group-hover:gap-2">
                      走进去体验
                      <ArrowRight className="h-3.5 w-3.5" />
                    </span>
                    <span className="text-[11px] text-ink/40 font-mono">
                      {experience?.hotspots?.length ? `${experience.hotspots.length} 处解读点` : '深度画境'}
                    </span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      {/* ── 新增：纹脉展馆沉浸介绍 ───────────────────────────────── */}
      <section className="mb-24 relative overflow-hidden rounded-3xl border border-gold/40 bg-gradient-to-br from-[#FCFBF8] via-[#FAF6F0] to-[#F5ECE0] p-8 md:p-12 shadow-sm">
        <div className="absolute -top-12 -right-12 w-80 h-80 bg-gold/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-12 -left-12 w-80 h-80 bg-primary/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10 grid lg:grid-cols-12 gap-8 lg:gap-12 items-center">
          {/* 左侧：精美大幅展馆外观建筑截图 */}
          <div className="lg:col-span-7">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="group relative aspect-[16/10] overflow-hidden rounded-2xl border-2 border-white shadow-2xl bg-black/10"
            >
              <img
                src={galleryExterior}
                alt="纹脉展馆建筑外观"
                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-[1.03]"
                loading="lazy"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent pointer-events-none"></div>
              <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between text-white">
                <span className="text-xs font-serif tracking-widest bg-black/40 backdrop-blur px-3 py-1 rounded">
                  实景渲染 · 纹脉数字化艺术展馆
                </span>
                <span className="text-xs opacity-80 font-mono hidden sm:inline">
                  Three.js 实体空间
                </span>
              </div>
            </motion.div>
          </div>

          {/* 右侧：文化韵味与功能介绍 */}
          <div className="lg:col-span-5 flex flex-col justify-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/20 bg-primary/5 text-primary text-xs font-medium w-fit mb-4">
              <Compass className="w-3.5 h-3.5 text-gold" />
              沉浸式三维文化展示空间
            </div>
            <h2 className="text-2xl md:text-3xl lg:text-4xl font-serif font-bold text-ink mb-4 leading-snug">
              纹脉展馆 <br />
              <span className="text-lg md:text-xl font-normal text-primary">
                虚拟漫游 · 自由布展 · 灵宠伴游
              </span>
            </h2>
            <p className="text-sm md:text-base text-ink/75 leading-relaxed mb-6 font-sans">
              纹脉展馆是纹脉华章的沉浸式三维文化展示空间。用户可以探索数字展馆、欣赏传统文化主题作品，并通过画框换画、器物布置等交互方式打造具有个人特色的虚拟艺术展厅。
            </p>

            <div className="grid grid-cols-2 gap-3 mb-8 text-xs text-ink/80 font-medium">
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-white/70 border border-primary/10">
                <span className="w-1.5 h-1.5 rounded-full bg-gold"></span>
                两层中式建筑格局
              </div>
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-white/70 border border-primary/10">
                <span className="w-1.5 h-1.5 rounded-full bg-gold"></span>
                15 处自定义展陈画框
              </div>
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-white/70 border border-primary/10">
                <span className="w-1.5 h-1.5 rounded-full bg-gold"></span>
                14 件传统器物道具
              </div>
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-white/70 border border-primary/10">
                <span className="w-1.5 h-1.5 rounded-full bg-gold"></span>
                昼夜光影与灵宠伴游
              </div>
            </div>

            <Link
              to="/heritage-gallery"
              className="group inline-flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-xl btn-chinese text-base font-serif shadow-md hover:shadow-xl transition-all w-fit"
            >
              <span>探索纹脉展馆</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── 平台核心能力（全面补齐，卡片轻盈有节奏） ─────────────── */}
      <div className="mb-24">
        <h2 className="text-3xl font-serif text-center mb-4 relative w-fit mx-auto text-ink">
          平台核心能力
        </h2>
        <p className="text-center text-sm md:text-base text-ink/60 max-w-2xl mx-auto mb-12">
          围绕传统文化视觉数字化创作，打通从创意输入、可控生成、自动解读到空间展陈与文创转化的全景闭环。
        </p>
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
                className="bg-rice-paper p-7 rounded-2xl shadow-xs border border-border-red/10 hover:shadow-lg hover:-translate-y-1 hover:border-primary/30 transition-all flex flex-col group"
              >
                <div className="flex items-center justify-between mb-5">
                  <div className="w-12 h-12 rounded-xl bg-primary/5 flex items-center justify-center group-hover:bg-primary group-hover:text-white transition-colors text-primary border border-primary/10">
                    <Icon className="w-6 h-6" />
                  </div>
                  <span className="text-[11px] font-serif text-primary/70 bg-primary/5 px-2.5 py-1 rounded-full border border-primary/10">
                    {feature.tag}
                  </span>
                </div>
                <h3 className="font-serif font-bold text-lg mb-2.5 text-ink group-hover:text-primary transition-colors">
                  {feature.title}
                </h3>
                <p className="text-xs md:text-sm text-ink/70 leading-relaxed font-sans flex-1">
                  {feature.desc}
                </p>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* ── 智能交互工作流 ───────────────────────────────────────── */}
      <div className="bg-primary/5 border border-primary/10 rounded-3xl p-8 md:p-12 relative overflow-hidden mb-24">
        <div className="absolute top-0 right-0 w-64 h-64 bg-gold/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-primary/10 rounded-full blur-3xl pointer-events-none"></div>

        <h2 className="text-2xl md:text-3xl font-serif text-center mb-3 text-primary font-bold">
          创作与应用全生命周期工作流
        </h2>
        <p className="text-center text-xs md:text-sm text-ink/60 max-w-xl mx-auto mb-12">
          从用户灵感到最终文创与空间展示，每一步清晰透明、环环相扣
        </p>

        <div className="flex flex-col lg:flex-row justify-between items-center gap-6 relative z-10 w-full max-w-5xl mx-auto">
          {[
            { step: '01', title: '创作主题 / 参考图输入', icon: PenTool },
            { step: '02', title: '传统视觉风格选择', icon: Palette },
            { step: '03', title: 'Qwen Image 智能生成', icon: Sparkles },
            { step: '04', title: '自动解读与 CultureCard', icon: BookOpen },
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
                  <div className="w-14 h-14 rounded-2xl bg-white shadow-sm border border-primary/20 flex items-center justify-center text-primary mb-3 relative z-10 group-hover:scale-110 group-hover:bg-primary group-hover:text-white transition-all duration-300">
                    <Icon className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-mono text-gold font-bold tracking-wider mb-0.5">
                    STEP {item.step}
                  </span>
                  <span className="text-xs font-serif font-medium text-ink/80 leading-tight">
                    {item.title}
                  </span>
                </div>
                {i < arr.length - 1 && (
                  <div className="hidden lg:block flex-1 h-[2px] bg-primary/20 w-full relative -top-5">
                    <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-primary/60"></div>
                  </div>
                )}
                {i < arr.length - 1 && (
                  <ChevronRight className="lg:hidden text-primary/30 my-1 h-4 w-4" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── 文创与传播场景示意 ───────────────────────────────────── */}
      <div className="mb-20">
        <div className="flex items-center gap-4 mb-8">
          <div>
            <p className="text-xs tracking-[0.25em] text-primary/70 font-medium">应用落地</p>
            <h2 className="text-2xl font-serif font-bold text-ink">文创衍生与传播场景</h2>
          </div>
          <div className="flex-1 h-px bg-gradient-to-r from-primary/20 to-transparent"></div>
          <Link
            to="/products"
            className="text-sm text-ink/60 hover:text-primary transition-colors flex items-center gap-1 font-medium"
          >
            打开文创工坊 <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          <Link
            to="/products"
            className="aspect-[4/3] rounded-2xl overflow-hidden shadow-xs hover:shadow-xl transition-all group relative cursor-pointer border border-primary/10"
          >
            <img
              src={import.meta.env.BASE_URL + "zhuxianzhen.png"}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
              alt="文化海报"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent"></div>
            <div className="absolute bottom-4 left-4 right-4 text-white">
              <span className="text-[10px] tracking-widest text-gold uppercase font-serif">POSTER FORMAT</span>
              <div className="text-base font-serif font-bold">节庆与文创海报版式</div>
              <p className="text-xs text-white/75 mt-0.5">将年画质感映射至文旅宣传大片</p>
            </div>
          </Link>

          <Link
            to="/products"
            className="aspect-[4/3] rounded-2xl overflow-hidden shadow-xs hover:shadow-xl transition-all group relative cursor-pointer border border-primary/10"
          >
            <div className="w-full h-full bg-[#f4f1ea] flex items-center justify-center relative p-8 group-hover:scale-105 transition-transform duration-700">
              <div className="w-2/3 aspect-square rounded-full border-4 border-white shadow-xl overflow-hidden z-10 shrink-0">
                <img
                  src={import.meta.env.BASE_URL + "qinghua.png"}
                  className="w-full h-full object-cover mix-blend-multiply"
                  alt="陶瓷杯垫"
                />
              </div>
            </div>
            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent pointer-events-none"></div>
            <div className="absolute bottom-4 left-4 right-4 text-white">
              <span className="text-[10px] tracking-widest text-gold uppercase font-serif">MERCHANDISE</span>
              <div className="text-base font-serif font-bold">文创实体打样与生活美学</div>
              <p className="text-xs text-white/75 mt-0.5">青花瓷盘与杯垫纹样效果模拟</p>
            </div>
          </Link>

          <Link
            to="/heritage-gallery"
            className="aspect-[4/3] rounded-2xl overflow-hidden shadow-xs hover:shadow-xl transition-all group relative cursor-pointer border border-primary/10"
          >
            <div className="w-full h-full bg-[#18181b] flex items-center justify-center relative p-6 group-hover:scale-105 transition-transform duration-700">
              <div className="w-full aspect-video bg-black rounded-lg shadow-[0_0_25px_rgba(255,255,255,0.12)] border border-gray-800 flex overflow-hidden">
                <img
                  src={galleryExterior}
                  className="w-full h-full object-cover opacity-85"
                  alt="展陈大屏"
                />
              </div>
            </div>
            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent pointer-events-none"></div>
            <div className="absolute bottom-4 left-4 right-4 text-white">
              <span className="text-[10px] tracking-widest text-gold uppercase font-serif">EXHIBITION</span>
              <div className="text-base font-serif font-bold">数字美术馆与展陈大屏</div>
              <p className="text-xs text-white/75 mt-0.5">三维空间漫游与数字展陈映射</p>
            </div>
          </Link>
        </div>
      </div>

      {/* ── 底部数据横幅 ─────────────────────────────────────────── */}
      <div className="bg-primary text-white rounded-2xl py-10 px-6 flex justify-around flex-wrap gap-8 items-center relative overflow-hidden shadow-[0_12px_36px_rgba(158,36,27,0.22)]">
        <div
          className={`absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.08'/%3E%3C/svg%3E")] pointer-events-none`}
        ></div>
        {[
          { v: '5 种', l: '传统视觉风格条目' },
          { v: '8 类', l: '文创载体预览模板' },
          { v: '3 种', l: '多维交互深度赏析' },
          { v: '2 层', l: '三维实体感纹脉展馆' },
          { v: '100%', l: '本地与云端闭环创作' },
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
      </div>
    </div>
  );
}
