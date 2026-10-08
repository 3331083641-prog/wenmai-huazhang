import { motion } from 'motion/react';
import { Monitor, Store, Smartphone } from 'lucide-react';

const SCENARIOS = [
  {
    id: 'screen',
    icon: Monitor,
    title: '数字展陈大屏',
    subtitle: '数字展陈效果示意',
    desc: '展示生成作品在数字展陈大屏中的排版设想。本页面为静态场景示意，当前不包含小程序、二维码上传或实时大屏同步功能。',
    target: '方案对象：博物馆 / 非遗展示中心 / 校园文化展厅',
    value: '为文化主题展览提供数字视觉呈现与互动设计参考。'
  },
  {
    id: 'store',
    icon: Store,
    title: '文旅景区文创商店',
    subtitle: '文创载体效果示意',
    desc: '展示生成作品映射到明信片等文创载体后的视觉构想。页面未接入景区终端、打印设备或商品交易服务。',
    target: '方案对象：景区文创空间 / 地方文化活动 / 旅游服务场景',
    value: '为文创概念设计和活动展示提供版式参考。'
  },
  {
    id: 'social',
    icon: Smartphone,
    title: '线上传播与社交分享',
    subtitle: '线上展示效果示意',
    desc: '以手机界面示意作品在社交媒体中的展示方式。当前不生成分享链接或可扫描二维码，发布与传播由用户自行完成。',
    target: '方案对象：传统文化爱好者 / 校园社团 / 线上内容创作者',
    value: '为文化内容的数字排版与社交平台发布提供视觉参考。'
  }
];

const SceneMockup = ({ id }: { id: string }) => {
  switch (id) {
    case 'screen':
      return (
        <div className="w-full h-full bg-[#111] relative overflow-hidden flex items-center justify-center">
            {/* Museum Gallery Background */}
            <div className="absolute inset-0 bg-gradient-to-b from-gray-900 via-gray-800 to-[#1a1a1a]"></div>
            
            {/* Spotlight Effects */}
            <div className="absolute top-0 left-1/4 w-32 h-64 bg-white/10 blur-[50px] -skew-x-12"></div>
            <div className="absolute top-0 right-1/4 w-32 h-64 bg-white/10 blur-[50px] -skew-x-12"></div>
            
            {/* Floor reflection */}
            <div className="absolute bottom-0 left-0 right-0 h-1/4 bg-black/40 blur-md"></div>

            {/* Giant Screen */}
            <div className="w-[85%] aspect-video bg-black rounded shadow-[0_0_50px_rgba(255,255,255,0.1)] border border-gray-800 flex overflow-hidden relative z-10 transform perspective-[1000px] rotateX-[2deg]">
                <img src={import.meta.env.BASE_URL + "songhua.png"} className="w-full h-full object-cover opacity-90 mix-blend-screen" alt="" />
                {/* Screen Glow */}
                <div className="absolute inset-0 shadow-[inset_0_0_20px_rgba(0,0,0,0.8)] pointer-events-none"></div>
                <div className="absolute inset-0 bg-gradient-to-tr from-primary/20 to-transparent mix-blend-overlay pointer-events-none"></div>
                {/* Fake UI overlays on the screen */}
                <div className="absolute bottom-4 left-4 flex gap-2">
                   <div className="w-12 h-16 bg-white/10 border border-white/20 rounded-sm"></div>
                   <div className="w-12 h-16 bg-white/10 border border-white/20 rounded-sm"></div>
                   <div className="w-12 h-16 bg-white/10 border border-white/20 rounded-sm"></div>
                </div>
                <div className="absolute top-4 right-4 text-white/50 text-xs font-mono">SCENE PREVIEW</div>
            </div>

            {/* Simple silhouettes to give scale */}
            <div className="absolute bottom-4 left-1/4 w-12 h-24 bg-black/80 rounded-t-full z-20 blur-[2px]"></div>
            <div className="absolute bottom-2 right-1/3 w-10 h-20 bg-black/90 rounded-t-full z-20 blur-[1px]"></div>
        </div>
      );
    case 'store':
      return (
        <div className="w-full h-full bg-[#E5DACE] relative overflow-hidden flex items-center justify-center p-8">
            {/* Store Shelves Background */}
            <div className="absolute inset-0 bg-[#F2EDE4]"></div>
            <div className="absolute top-1/3 w-full h-[10px] bg-[#D4C3AC] shadow-md z-0"></div>
            <div className="absolute top-2/3 w-full h-[10px] bg-[#D4C3AC] shadow-md z-0"></div>

            {/* Shelf Items */}
            {/* Top Shelf Canvas Bag */}
            <div className="absolute top-[8%] left-10 w-24 aspect-[3/4] bg-white rounded shadow-md z-10 flex flex-col items-center justify-end pb-2 transform -rotate-2">
                <div className="w-1/2 h-4 border-t-[3px] border-x-[3px] border-[#D4C3AC] rounded-t-[0.5rem] absolute -top-4"></div>
                <img src={import.meta.env.BASE_URL + "zhuxianzhen.png"} className="w-[85%] aspect-square object-cover opacity-90" alt="" />
            </div>

            {/* Top Shelf Postcards */}
            <div className="absolute top-[20%] right-16 w-32 h-12 bg-white rounded shadow-sm z-10 p-1 flex gap-1">
               <img src={import.meta.env.BASE_URL + "qinghua.png"} className="w-1/2 h-full object-cover" alt="" />
               <img src={import.meta.env.BASE_URL + "jianzhi.png"} className="w-1/2 h-full object-cover" alt="" />
            </div>

            {/* Middle shelf Box */}
            <div className="absolute top-[42%] left-1/3 w-32 aspect-video bg-[#fafafa] rounded shadow-lg z-10 border border-[#e0e0e0] flex items-center justify-center p-2 transform rotate-2">
               <img src={import.meta.env.BASE_URL + "songhua.png"} className="w-full h-full object-cover" alt="" />
            </div>

            {/* Middle shelf Cup/Coaster */}
            <div className="absolute top-[50%] right-24 w-12 h-16 bg-white rounded shadow-md z-10">
                <div className="w-full h-4 bg-gray-100 rounded-t border-b border-gray-200"></div>
                <div className="p-1.5 h-full flex items-center">
                    <img src={import.meta.env.BASE_URL + "bianxiu.png"} className="w-full aspect-square rounded-full object-cover border border-primary/20" alt="" />
                </div>
            </div>

            {/* Lighting */}
            <div className="absolute inset-0 bg-gradient-to-b from-[#F9F6F0]/80 via-transparent to-black/20 pointer-events-none z-30"></div>
        </div>
      );
    case 'social':
       return (
        <div className="w-full h-full bg-[#f0f2f5] relative overflow-hidden flex items-center justify-center p-8">
            {/* Phone Mockup */}
             <div className="h-full aspect-[9/19] bg-white rounded-[2rem] shadow-[0_20px_50px_rgba(0,0,0,0.15)] border-[6px] border-gray-800 p-2 relative z-10 flex flex-col transform rotate-[-5deg] scale-105 transition-transform hover:rotate-0 hover:scale-110 duration-500">
                {/* Header */}
                <div className="flex items-center gap-2 p-2">
                   <div className="w-6 h-6 rounded-full bg-gray-200 border-2 border-primary/20 p-px">
                       <div className="w-full h-full rounded-full bg-primary/40"></div>
                   </div>
                   <div className="flex-1 space-y-1">
                      <div className="w-16 h-2 bg-gray-300 rounded"></div>
                      <div className="w-10 h-1.5 bg-gray-200 rounded"></div>
                   </div>
                   <div className="w-5 h-1.5 bg-gray-200 rounded-full"></div>
                </div>

                {/* Content Image */}
                <div className="w-full aspect-square bg-gray-100 mt-2 relative overflow-hidden rounded-md">
                   <img src={import.meta.env.BASE_URL + "jianzhi.png"} className="w-full h-full object-cover" alt="" />
                </div>

                {/* Engagement Bar */}
                <div className="flex gap-3 px-2 py-3">
                   <div className="w-5 h-5 rounded-full border-2 border-primary"></div>
                   <div className="w-5 h-5 rounded-full border-2 border-gray-300"></div>
                   <div className="w-5 h-5 rounded-full border-2 border-gray-300"></div>
                   <div className="ml-auto w-5 h-5 rounded-full border-2 border-gray-300"></div>
                </div>

                 {/* Caption */}
                 <div className="px-2 space-y-1.5">
                    <div className="w-[80%] h-2 bg-gray-300 rounded"></div>
                    <div className="w-[60%] h-2 bg-gray-200 rounded"></div>
                    <div className="flex gap-1 mt-2">
                       <span className="text-[#9E241B] text-[8px] font-bold bg-red-50 px-1 py-0.5 rounded">#中国非遗</span>
                       <span className="text-[#9E241B] text-[8px] font-bold bg-red-50 px-1 py-0.5 rounded">#AI文创</span>
                    </div>
                 </div>

                 {/* Footer / QR */}
                 <div className="mt-auto p-3 border-t border-gray-100 flex items-center justify-between bg-primary/5">
                    <div className="text-[9px] text-ink/70">线上展示效果示意</div>
                    <div title="静态装饰图案，不可扫描" aria-label="静态装饰图案，不可扫描" className="w-8 h-8 p-0.5 bg-white shadow-sm border border-black/5 rounded flex flex-wrap gap-px opacity-50">
                        {/* fake QR */}
                        {[...Array(9)].map((_, i) => <div key={i} className="w-[30%] aspect-square bg-primary/80"></div>)}
                    </div>
                 </div>
             </div>

             {/* Background Float Elements */}
             <div className="absolute top-6 -right-6 w-32 aspect-[3/4] bg-white p-2 shadow-xl rounded transform rotate-12 z-0 border border-black/5">
                <img src={import.meta.env.BASE_URL + "zhuxianzhen.png"} className="w-full h-full object-cover opacity-80" alt="" />
             </div>
             <div className="absolute -bottom-4 left-4 w-24 aspect-[3/4] bg-white p-2 shadow-xl rounded transform -rotate-12 z-0 border border-black/5">
                <img src={import.meta.env.BASE_URL + "bianxiu.png"} className="w-full h-full object-cover opacity-80" alt="" />
             </div>
        </div>
       );
    default:
      return null;
  }
};

export default function Scenarios() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-12 md:py-20">
      <div className="text-center mb-16">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/20 bg-primary/5 text-primary text-sm font-medium mb-6">应用场景方案 · 静态示意</div>
        <h1 className="text-4xl md:text-5xl font-serif text-primary font-bold mb-6">多场景应用方案</h1>
        <p className="text-lg text-ink/80 max-w-3xl mx-auto leading-relaxed">
          围绕数字展陈、文旅文创与社交传播，展示生成作品在不同文化场景中的应用方式。以下内容为效果预览，当前未在外部场馆或商业系统部署。
        </p>
      </div>

      <div className="bg-rice-paper rounded-2xl p-6 md:p-8 mb-20 shadow-sm border border-gold/20 flex flex-wrap justify-around items-center gap-6">
         <div className="text-center">
            <h3 className="font-bold text-primary font-serif text-xl mb-1">01. 数字展陈</h3>
            <p className="text-sm text-ink/60">场景布局预览</p>
         </div>
         <div className="w-px h-12 bg-black/10 hidden md:block"></div>
         <div className="text-center">
            <h3 className="font-bold text-primary font-serif text-xl mb-1">02. 实体零售</h3>
            <p className="text-sm text-ink/60">文创载体方案</p>
         </div>
         <div className="w-px h-12 bg-black/10 hidden md:block"></div>
         <div className="text-center">
            <h3 className="font-bold text-primary font-serif text-xl mb-1">03. 社交传播</h3>
            <p className="text-sm text-ink/60">线上内容展示方案</p>
         </div>
      </div>

      <div className="space-y-32 mb-24">
        {SCENARIOS.map((scenario, index) => {
          const Icon = scenario.icon;
          const isEven = index % 2 === 0;
          return (
            <motion.div 
              key={index}
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.8 }}
              className={`flex flex-col gap-12 items-center ${isEven ? 'lg:flex-row' : 'lg:flex-row-reverse'}`}
            >
              <div className="lg:w-1/2 relative">
                <div className="absolute inset-0 bg-primary/5 -m-6 rounded-3xl -z-10 transform rotate-3"></div>
                <div className="relative rounded-2xl overflow-hidden shadow-[0_10px_40px_rgba(158,36,27,0.15)] border-4 border-white aspect-[4/3]">
                  <SceneMockup id={scenario.id} />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent pointer-events-none"></div>
                  <div className="absolute bottom-6 left-6 text-white flex items-center gap-3">
                    <div className="p-2 bg-white/20 backdrop-blur-md rounded-lg">
                      <Icon className="w-6 h-6" />
                    </div>
                    <span className="font-medium tracking-wide">Scene {index + 1}</span>
                  </div>
                </div>
              </div>
              
              <div className="lg:w-1/2 px-4 lg:px-12">
                <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-gold/10 text-gold font-medium mb-6 text-sm border border-gold/20">
                  <Icon className="w-4 h-4" /> {scenario.subtitle}
                </div>
                <h2 className="text-3xl font-serif font-bold text-ink mb-6 leading-tight">{scenario.title}</h2>
                <div className="w-12 h-1 bg-primary mb-6"></div>
                <p className="text-lg text-ink/70 leading-relaxed mb-8">
                  {scenario.desc}
                </p>
                <div className="bg-rice-paper p-5 rounded-lg border border-primary/10 space-y-3">
                   <div className="flex items-start gap-4 text-sm">
                      <div className="w-16 font-bold text-ink shrink-0 font-serif">适用对象</div>
                      <div className="text-ink/80">{scenario.target}</div>
                   </div>
                   <div className="w-full h-px bg-primary/10"></div>
                   <div className="flex items-start gap-4 text-sm">
                      <div className="w-16 font-bold text-ink shrink-0 font-serif">核心价值</div>
                      <div className="text-primary font-medium">{scenario.value}</div>
                   </div>
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Deployment Flow */}
      <div className="mb-20">
        <h3 className="text-2xl font-serif text-center text-primary mb-3">场景部署参考流程</h3>
        <p className="text-sm text-ink/60 text-center mb-8">以下为后续实施路径示意，不代表当前已部署能力。</p>
        <div className="bg-white p-8 md:p-12 rounded-3xl border border-black/5 shadow-sm relative">
           <div className="flex flex-col md:flex-row justify-between items-center gap-6 relative z-10">
              {[
                { n: "1", t: "前端创作界面部署", d: "配置网页访问与页面内容" },
                { n: "2", t: "AI生成服务接入", d: "配置服务端接口与模型权限" },
                { n: "3", t: "展示终端适配", d: "按需求适配大屏或其他媒介" },
                { n: "4", t: "数据与隐私配置", d: "明确文件留存和用户告知" }
              ].map((step, i, arr) => (
                <div key={i} className="flex flex-col md:flex-row items-center gap-4 flex-1 group">
                   <div className="flex flex-col items-center text-center">
                      <div className="w-14 h-14 rounded-full bg-primary/5 text-primary font-serif font-bold text-xl flex items-center justify-center mb-3 border border-primary/20 group-hover:bg-primary group-hover:text-white transition-colors">{step.n}</div>
                      <div className="font-bold text-ink text-sm mb-1">{step.t}</div>
                      <div className="text-xs text-ink/50">{step.d}</div>
                   </div>
                   {i < arr.length - 1 && (
                     <div className="hidden md:block flex-1 h-px bg-primary/20 w-full relative -top-6">
                        <div className="absolute right-0 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-primary/40"></div>
                     </div>
                   )}
                </div>
              ))}
           </div>
        </div>
      </div>

      {/* Extensible apps */}
      <div>
        <h3 className="chinese-plaque text-lg mb-6">可探索的应用方向（规划）</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
           {['校园美育互动展览', '非遗研学配套课程', '地方旅游节庆活动', '智慧博物馆导览'].map((item, i) => (
              <div key={i} className="bg-white p-4 rounded-xl shadow-sm border border-primary/5 text-center hover:-translate-y-1 hover:shadow-md transition-all">
                 <div className="text-sm font-medium text-ink">{item}</div>
              </div>
           ))}
        </div>
      </div>
    </div>
  );
}
