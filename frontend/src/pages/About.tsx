import { motion } from 'motion/react';
import { Smartphone, Heart, Sparkles, BookOpen, Layers, Target, Compass, Palette, Images, SlidersHorizontal, LayoutTemplate, CloudCog, Eye } from 'lucide-react';

const implemented = [
  'React 19、Vite 6、TypeScript、Tailwind CSS 4、React Router 7 与 Motion 交互前端',
  'FastAPI、Pydantic、Uvicorn 与 Pillow 后端生成服务',
  '五类传统视觉风格条目：木版年画、汴绣、青绿山水、青花瓷纹样与剪纸',
  '阿里云百炼 Qwen Image 3.0 文生图与参考图创作',
  '生成成功后由本机 Ollama 上的 Qwen3-VL 读取图片并输出结构化视觉解读',
  '创作主题、风格特征、风格影响强度、负向提示与构图提示的 Prompt 组织',
  '生成作品展示、文化说明卡、浏览器本地生成记录；视觉分析不可用时使用模板回退',
  '文创载体效果预览与多场景静态示意',
];

const planned = [
  '增加传统视觉风格条目，并逐项核验文化描述与素材来源',
  '探索多参考图融合与更细粒度的局部编辑',
  '规划文化知识检索增强，为风格说明提供可追溯来源',
  '评估多用户作品管理与文旅展示终端适配',
];

export default function About() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-12 md:py-20 lg:py-24">
      <div className="mb-16 text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-sm font-medium text-primary">
          <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
          2026 iCAN大学生创新创业大赛 · AI应用创新挑战赛 · 软件赛道
        </div>
        <h1 className="mb-6 font-serif text-4xl font-bold text-primary md:text-5xl">关于纹脉华章</h1>
        <p className="mx-auto max-w-4xl text-base leading-8 text-ink/75 md:text-lg">
          纹脉华章面向传统文化数字创作与传播场景，探索人工智能生成技术在传统视觉表达、文创设计和数字传播中的应用。平台通过主题输入、参考图、文化风格选择与生成参数控制，帮助用户创作具有传统视觉特征的数字作品，并预览其在文创与传播场景中的应用效果。
        </p>
      </div>

      <section className="mb-20">
        <h2 className="mb-8 text-center font-serif text-3xl text-primary">当前核心能力</h2>
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
          {[
            { icon: Palette, title: '文化视觉风格库', text: '整理五类传统文化视觉风格的色彩、构图、纹样和视觉语言，供创作选择与提示组织。' },
            { icon: Sparkles, title: '多模态视觉生成', text: '通过 FastAPI 调用阿里云百炼 Qwen Image 3.0，支持文本主题与用户参考图共同驱动视觉生成。' },
            { icon: SlidersHorizontal, title: '风格参数控制', text: '风格影响强度会真实改变 Prompt 中的文化视觉约束程度，并与构图和应用场景提示共同进入生成请求。' },
            { icon: LayoutTemplate, title: '作品解读与应用预览', text: '本机 Qwen3-VL 读取生成图并结合项目风格资料输出解读；服务暂不可用时以主题和风格条目模板回退。' },
          ].map((item, index) => {
            const Icon = item.icon;
            return (
              <motion.article key={item.title} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.4, delay: index * 0.08 }} className="rounded-2xl border border-primary/10 bg-white p-6 shadow-sm">
                <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-full bg-primary/5 text-primary"><Icon className="h-5 w-5" /></div>
                <h3 className="mb-2 font-serif text-lg font-bold text-ink">{item.title}</h3>
                <p className="text-sm leading-6 text-ink/65">{item.text}</p>
              </motion.article>
            );
          })}
        </div>
      </section>

      <section className="mb-20 rounded-3xl border border-primary/10 bg-rice-paper p-6 md:p-10">
        <div className="mb-8 text-center">
          <p className="mb-2 text-xs font-semibold tracking-[0.22em] text-gold-dark">CURRENT TECHNICAL FLOW</p>
          <h2 className="font-serif text-2xl font-bold text-primary md:text-3xl">从创作输入到应用预览</h2>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {[
            { icon: Smartphone, title: 'React / Vite', note: '主题、参考图与参数输入' },
            { icon: CloudCog, title: 'FastAPI', note: '请求校验与 Prompt 组织' },
            { icon: Images, title: 'Qwen Image 3.0', note: '文本与用户参考图驱动生成' },
            { icon: Eye, title: '本地 Qwen3-VL', note: '读取生成图片并返回视觉解读 JSON' },
            { icon: BookOpen, title: 'CultureCard', note: '文化说明卡与文创效果预览' },
          ].map((item, index) => {
            const Icon = item.icon;
            return (
              <div key={item.title} className="relative rounded-xl border border-white bg-white/90 p-5 text-center shadow-sm">
                <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-primary/5 text-primary"><Icon className="h-5 w-5" /></div>
                <div className="font-semibold text-ink">{item.title}</div>
                <div className="mt-1 text-xs leading-5 text-ink/55">{item.note}</div>
                {index < 4 && <span className="absolute -right-2.5 top-1/2 z-10 hidden -translate-y-1/2 rounded-full bg-rice-paper px-1 text-primary lg:block">›</span>}
              </div>
            );
          })}
        </div>
        <p className="mt-5 text-center text-xs leading-5 text-ink/50">用户上传参考图会随生成请求传入 Qwen Image 3.0；生成后的真实作品再交给本机 Qwen3-VL 解读。若本地视觉服务不可用，作品仍保留并使用主题与风格条目模板生成说明。</p>
      </section>

      <section className="mb-20 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-2xl border border-primary/10 bg-white p-7 md:p-9">
          <div className="mb-6 flex items-center gap-3 text-primary"><Layers className="h-6 w-6" /><h2 className="font-serif text-2xl font-bold">当前已实现</h2></div>
          <ul className="grid gap-3 sm:grid-cols-2">
            {implemented.map((item) => <li key={item} className="flex gap-3 rounded-lg bg-paper/65 p-3 text-sm leading-6 text-ink/75"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />{item}</li>)}
          </ul>
        </div>
        <div className="rounded-2xl bg-primary p-7 text-white shadow-lg md:p-9">
          <div className="mb-6 flex items-center gap-3 text-gold"><Compass className="h-6 w-6" /><h2 className="font-serif text-2xl font-bold text-white">后续拓展规划</h2></div>
          <p className="mb-5 text-sm leading-6 text-white/75">以下为后续方向，当前版本尚未实现。</p>
          <ul className="space-y-4">
            {planned.map((item) => <li key={item} className="flex gap-3 text-sm leading-6 text-white/90"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-gold" />{item}</li>)}
          </ul>
        </div>
      </section>

      <section className="mb-20 grid gap-10 border-t border-black/10 pt-12 md:grid-cols-2">
        <div>
          <div className="mb-5 flex items-center gap-3 text-primary"><Heart className="h-7 w-7" /><h2 className="font-serif text-2xl">项目应用价值</h2></div>
          <div className="space-y-3 text-sm leading-6 text-ink/70">
            <p className="rounded-xl bg-rice-paper p-4">为传统视觉文化的数字表达与公众参与提供创作工具。</p>
            <p className="rounded-xl bg-rice-paper p-4">通过生成结果与载体预览，辅助文创概念设计和视觉沟通。</p>
            <p className="rounded-xl bg-rice-paper p-4">可用于校园美育和文化传播活动的创作演示；当前没有校园部署或成效数据。</p>
          </div>
        </div>
        <div className="rounded-2xl border border-primary/15 bg-white p-6">
          <h2 className="mb-4 flex items-center gap-2 font-serif text-xl text-primary"><Target className="h-5 w-5" />数据与服务说明</h2>
          <ul className="space-y-3 text-sm leading-6 text-ink/70">
            <li>生成图片保存在后端本机目录，最近生成记录保存在当前浏览器；当前没有数据库、账户或云端作品库。</li>
            <li>文创页面为预设载体效果预览，应用场景页面为展示示意，不连接商品交易、印刷生产或实际场馆。</li>
            <li>项目调用的第三方模型服务与开源组件遵循相应服务条款和许可；团队工作侧重产品设计、风格条目组织、Prompt 流程、系统集成与交互实现。</li>
            <li>演示素材的来源与授权状态由项目团队逐项核验。本项目不主张拥有第三方历史图像或文化作品的版权。</li>
          </ul>
        </div>
      </section>

      <section className="rounded-2xl border border-gold/25 bg-white p-6 md:p-8">
        <h2 className="mb-5 font-serif text-xl font-bold text-primary">技术栈</h2>
        <div className="grid gap-4 text-sm sm:grid-cols-2">
          <div className="rounded-xl bg-paper p-4"><span className="font-semibold text-ink">前端</span><p className="mt-1 leading-6 text-ink/65">React 19 · Vite 6 · TypeScript · Tailwind CSS 4 · React Router 7 · Motion</p></div>
          <div className="rounded-xl bg-paper p-4"><span className="font-semibold text-ink">后端与生成服务</span><p className="mt-1 leading-6 text-ink/65">FastAPI · Pydantic · Uvicorn · Pillow · DashScope / Qwen Image 3.0 · Ollama / Qwen3-VL</p></div>
        </div>
      </section>
    </div>
  );
}
