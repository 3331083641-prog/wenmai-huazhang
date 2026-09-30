import { Link } from 'react-router-dom';
import { ArrowRight, Sparkles, BookOpen, PenTool, Layout, Palette, Smartphone } from 'lucide-react';
import { motion } from 'motion/react';

const FEATURES = [
  { icon: Palette, title: '传统文化视觉风格库', desc: '围绕朱仙镇木版年画、汴绣、宋画青绿山水、青花瓷纹样与中国剪纸，整理色彩、构图、纹样与视觉语言，为 AI 生成提供结构化风格约束。' },
  { icon: Sparkles, title: '多模态 AI 视觉生成', desc: '接入阿里云百炼 Qwen Image 3.0，支持文本主题与参考图共同驱动生成，并结合文化风格特征构建生成约束。' },
  { icon: Smartphone, title: '可控文化风格创作', desc: '用户可选择传统文化视觉风格、构图方向与风格影响强度，系统将相关参数转化为生成 Prompt，形成不同程度的文化视觉表达。' },
  { icon: Layout, title: '文创衍生与场景预览', desc: '将 AI 生成作品映射到明信片、海报、帆布袋、数字展陈等典型载体，用于文创设计与传播效果预览。' },
];

export default function Home() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-12 md:py-20 lg:py-24">
      {/* Hero Section */}
      <div className="grid lg:grid-cols-2 gap-12 lg:gap-8 items-center mb-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="max-w-2xl"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/20 bg-primary/5 text-primary text-sm font-medium mb-6">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
            2026 iCAN大学生创新创业大赛 · AI应用创新挑战赛 · 软件赛道
          </div>
          <h1 className="text-5xl md:text-6xl font-serif font-bold leading-tight mb-6 text-ink">
            纹脉华章 <br />
            <span className="text-3xl md:text-4xl text-primary font-medium border-b-2 border-gold pb-1 inline-block mt-4">
              传统文化视觉智能创作与文创应用平台
            </span>
          </h1>
          <p className="text-lg md:text-xl text-ink/70 mb-10 leading-relaxed">
            以人工智能图像生成服务为核心，结合用户主题、传统文化视觉风格与创作提示，辅助完成数字作品创作，并提供文创载体和传播场景的效果预览。让传统文化从<span className="font-semibold text-primary">“被观看”走向“被共创”</span>。
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <Link
              to="/creator"
              className="group relative inline-flex items-center gap-2 px-8 py-3.5 btn-chinese text-lg transition-all"
            >
              <span className="relative">立即体验生成</span>
              <ArrowRight className="relative w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link
              to="/styles"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded border border-primary text-primary font-medium text-lg hover:bg-primary/5 transition-colors"
            >
              查看风格库
            </Link>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, delay: 0.2 }}
          className="relative lg:ml-auto w-full h-[500px]"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-[#9E241B]/10 to-transparent rounded-full blur-[80px]"></div>
          
          <div className="relative w-full h-full">
            {/* Main Center Image */}
            <div className="absolute top-[10%] left-[15%] w-[60%] aspect-[3/4] rounded-xl overflow-hidden shadow-2xl border-4 border-white/80 z-20 group hover:-translate-y-2 transition-transform duration-500">
               <img src="/zhuxianzhen.png" className="w-full h-full object-cover" alt="木版年画" />
               <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur px-3 py-1.5 rounded-sm shadow-sm chinese-plaque !py-1 !text-xs">
                 朱仙镇木版年画
               </div>
            </div>

            {/* Top Right Float */}
            <div className="absolute top-[5%] right-[5%] w-[40%] aspect-square rounded-xl overflow-hidden shadow-xl border-4 border-white/60 z-10 opacity-90 group hover:opacity-100 hover:-translate-y-2 transition-all duration-500">
               <img src="/songhua.png" className="w-full h-full object-cover" alt="宋画" />
            </div>

            {/* Bottom Right Float */}
            <div className="absolute bottom-[10%] right-[10%] w-[45%] aspect-[4/3] rounded-xl overflow-hidden shadow-xl border-4 border-white/60 z-30 opacity-90 group hover:opacity-100 hover:-translate-y-2 transition-all duration-500">
               <img src="/bianxiu.png" className="w-full h-full object-cover" alt="汴绣" />
            </div>

            {/* Bottom Left Float */}
            <div className="absolute bottom-[5%] left-[5%] w-[35%] aspect-square rounded-full overflow-hidden shadow-xl border-[6px] border-white z-40 opacity-95 group hover:-rotate-6 transition-all duration-500">
               <img src="/qinghua.png" className="w-full h-full object-cover" alt="青花" />
            </div>
          </div>
          
          {/* Floating badge */}
          <div className="absolute top-1/2 -right-4 -translate-y-1/2 bg-white/90 backdrop-blur-md p-4 rounded-xl shadow-[0_10px_30px_rgba(158,36,27,0.15)] flex items-center gap-4 z-50">
            <div className="w-12 h-12 rounded-full bg-gold/10 flex items-center justify-center">
              <Sparkles className="text-gold w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-primary/70 mb-0.5">传统视觉风格</p>
              <p className="font-bold text-sm text-ink">AI 图像生成</p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Recommended Styles Quick View */}
      <div className="mb-24 flex items-center gap-6 justify-center">
         <span className="text-sm font-serif text-ink/50">传统文化风格：</span>
         {['/zhuxianzhen.png', '/songhua.png', '/bianxiu.png', '/qinghua.png', '/jianzhi.png'].map((src, idx) => (
           <Link key={idx} to="/styles" className="w-12 h-12 rounded-full border-2 border-primary/20 overflow-hidden shadow-sm hover:scale-110 hover:border-primary transition-all">
             <img src={src} className="w-full h-full object-cover" alt="style thumbnails" />
           </Link>
         ))}
      </div>

      {/* Core Features */}
      <div className="mb-24">
        <h2 className="text-3xl font-serif text-center mb-12 relative w-fit mx-auto">
          <span className="relative z-10 bg-paper px-4 text-primary">项目核心能力</span>
          <div className="absolute inset-0 flex items-center z-0">
            <div className="w-full border-t border-primary/20"></div>
          </div>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {FEATURES.map((feature, i) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="bg-rice-paper p-8 rounded-2xl shadow-sm border border-border-red/10 hover:shadow-lg hover:-translate-y-1 hover:border-primary/30 transition-all text-center group"
              >
                <div className="w-14 h-14 mx-auto rounded-full bg-primary/5 flex items-center justify-center mb-5 group-hover:bg-primary group-hover:text-white transition-colors text-primary border border-primary/10">
                  <Icon className="w-6 h-6" />
                </div>
                <h3 className="font-serif font-bold text-lg mb-3 text-ink/90">{feature.title}</h3>
                <p className="text-sm text-ink/70 leading-relaxed">{feature.desc}</p>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Workflow */}
      <div className="bg-primary/5 border border-primary/10 rounded-3xl p-8 md:p-12 relative overflow-hidden mb-24">
        <div className="absolute top-0 right-0 w-64 h-64 bg-gold/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-primary/10 rounded-full blur-3xl"></div>
        
        <h2 className="text-2xl font-serif text-center mb-12 text-primary">智能交互工作流</h2>
        
        <div className="flex flex-col lg:flex-row justify-between items-center gap-6 relative z-10 w-full max-w-5xl mx-auto">
          {[
            { title: '创作主题 / 参考图输入', icon: PenTool },
            { title: '文化风格与参数选择', icon: Palette },
            { title: 'Qwen Image 3.0 多模态生成', icon: Sparkles },
            { title: '文化说明与作品解读', icon: BookOpen },
            { title: '文创应用效果预览', icon: Layout }
          ].map((step, i, arr) => {
            const Icon = step.icon;
            return(
            <div key={i} className="flex flex-col lg:flex-row items-center gap-4 flex-1 w-full lg:w-auto group">
              <div className="flex flex-col items-center text-center w-full">
                <div className="w-16 h-16 rounded-full bg-white shadow-[0_4px_15px_rgba(158,36,27,0.1)] border border-primary/20 flex items-center justify-center text-primary mb-4 relative z-10 group-hover:scale-110 group-hover:bg-primary group-hover:text-white transition-all duration-300">
                  <Icon className="w-7 h-7" />
                </div>
                <span className="text-sm font-medium whitespace-nowrap text-ink/80">{step.title}</span>
              </div>
              {i < arr.length - 1 && (
                <div className="hidden lg:block flex-1 h-[2px] bg-primary/20 w-full relative -top-4">
                  <div className="absolute right-0 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-primary/50"></div>
                </div>
              )}
              {i < arr.length - 1 && (
                <ArrowRight className="lg:hidden text-primary/30 my-3" />
              )}
            </div>
          )})}
        </div>
      </div>

      {/* Use Cases Preview */}
      <div className="mb-20">
         <div className="flex items-center gap-4 mb-8">
            <h2 className="text-2xl font-serif font-bold text-primary">文创与传播场景示意</h2>
            <div className="flex-1 h-px bg-gradient-to-r from-primary/20 to-transparent"></div>
            <Link to="/products" className="text-sm text-ink/50 hover:text-primary transition-colors flex items-center gap-1">
              查看全部 <ArrowRight className="w-4 h-4" />
            </Link>
         </div>
         <div className="grid md:grid-cols-3 gap-6">
            <div className="aspect-[4/3] rounded-xl overflow-hidden shadow-sm hover:shadow-lg transition-all group relative cursor-pointer">
                <img src="/zhuxianzhen.png" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" alt="文创应用"/>
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent"></div>
                <div className="absolute bottom-4 left-4 text-white">
                   <div className="text-sm font-medium">海报版式示意</div>
                </div>
            </div>
            <div className="aspect-[4/3] rounded-xl overflow-hidden shadow-sm hover:shadow-lg transition-all group relative cursor-pointer">
                <div className="w-full h-full bg-[#f0ede6] flex items-center justify-center relative p-8 group-hover:scale-105 transition-transform duration-700">
                   <div className="w-2/3 aspect-square rounded-full border-4 border-white shadow-xl overflow-hidden z-10 shrink-0">
                      <img src="/qinghua.png" className="w-full h-full object-cover mix-blend-multiply" alt="杯垫"/>
                   </div>
                </div>
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent"></div>
                <div className="absolute bottom-4 left-4 text-white">
                   <div className="text-sm font-medium">文创载体效果预览</div>
                </div>
            </div>
            <div className="aspect-[4/3] rounded-xl overflow-hidden shadow-sm hover:shadow-lg transition-all group relative cursor-pointer">
                <div className="w-full h-full bg-[#111] flex items-center justify-center relative p-6 group-hover:scale-105 transition-transform duration-700">
                    <div className="w-full aspect-video bg-black rounded shadow-[0_0_20px_rgba(255,255,255,0.1)] border border-gray-800 flex overflow-hidden">
                       <img src="/songhua.png" className="w-full h-full object-cover opacity-80" alt="展陈"/>
                    </div>
                </div>
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent"></div>
                <div className="absolute bottom-4 left-4 text-white">
                   <div className="text-sm font-medium">数字展陈场景示意</div>
                </div>
            </div>
         </div>
      </div>

      {/* Stats Bar */}
      <div className="bg-primary text-white rounded-xl py-10 px-6 flex justify-around flex-wrap gap-8 items-center relative overflow-hidden shadow-[0_10px_30px_rgba(158,36,27,0.2)]">
          <div className={`absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.1'/%3E%3C/svg%3E")]`}></div>
          {[
            { v: "5种", l: "传统视觉风格条目" },
            { v: "8类", l: "文创载体预览模板" },
            { v: "3类", l: "应用场景示意" },
            { v: "1项", l: "当前云端图像生成服务" }
          ].map((stat, i) => (
             <div key={i} className="text-center relative z-10 flex flex-col items-center">
                <div className="text-3xl md:text-4xl font-serif font-bold text-gold drop-shadow-md mb-2">{stat.v}</div>
                <div className="text-sm opacity-90">{stat.l}</div>
             </div>
          ))}
      </div>

    </div>
  );
}
