import { motion, AnimatePresence } from 'motion/react';
import { Check, Download, LoaderCircle, ShoppingBag, Frame, Smartphone, MonitorPlay, Ticket } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { cn } from '../lib/utils';
import { STYLES } from '../data/styleLibrary';
import { resolveGeneratedImageUrl } from '../services/generationService';

const PRODUCTS = [
  { id: 'postcard', name: '文旅明信片', icon: Frame },
  { id: 'poster', name: '数字海报', icon: Frame },
  { id: 'bag', name: '帆布袋', icon: ShoppingBag },
  { id: 'bookmark', name: '文创书签', icon: Frame },
  { id: 'coaster', name: '陶瓷杯垫', icon: Frame },
  { id: 'social', name: '手机分享图', icon: Smartphone },
  { id: 'screen', name: '数字展陈屏', icon: MonitorPlay },
  { id: 'ticket', name: '景区纪念票', icon: Ticket },
];

const DEFAULT_SOURCE_IMAGE = STYLES[0]?.img || '/songhua.png';
const getSourceLabel = (provider?: string, mode?: string) => {
  const source = provider || mode || '';
  if (source === 'dashscope_qwen_image') return '当前图像来源：Qwen Image 3.0（DashScope）';
  return source ? '当前作品：本地生成记录' : '当前作品：最近一次生成';
};

const fileTimestamp = (date = new Date()) => {
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}_${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`;
};

const roundedRect = (ctx: CanvasRenderingContext2D, x: number, y: number, width: number, height: number, radius: number) => {
  ctx.beginPath();
  ctx.roundRect(x, y, width, height, radius);
};

const drawCover = (ctx: CanvasRenderingContext2D, image: HTMLImageElement, x: number, y: number, width: number, height: number) => {
  const scale = Math.max(width / image.naturalWidth, height / image.naturalHeight);
  const cropWidth = width / scale;
  const cropHeight = height / scale;
  ctx.drawImage(image, (image.naturalWidth - cropWidth) / 2, (image.naturalHeight - cropHeight) / 2, cropWidth, cropHeight, x, y, width, height);
};

const loadImageBlob = async (url: string) => {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) throw new Error(`无法读取当前作品（HTTP ${response.status}）`);
  const objectUrl = URL.createObjectURL(await response.blob());
  try {
    const image = new Image();
    image.src = objectUrl;
    await image.decode();
    return await new Promise<HTMLImageElement>((resolve) => {
      // Keep the object URL alive until the canvas has been rendered.
      image.dataset.objectUrl = objectUrl;
      resolve(image);
    });
  } catch (error) {
    URL.revokeObjectURL(objectUrl);
    throw error;
  }
};

const renderProductExport = async (productId: string, imageUrl: string, productName: string) => {
  const image = await loadImageBlob(imageUrl);
  const canvas = document.createElement('canvas');
  canvas.width = 1600;
  canvas.height = 1200;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('浏览器无法创建图片画布');

  const paper = '#f3efe6';
  ctx.fillStyle = paper;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#9e241b';
  ctx.font = '600 26px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
  ctx.fillText('纹脉华章', 72, 76);
  ctx.textAlign = 'right';
  ctx.fillStyle = '#796c5c';
  ctx.font = '400 18px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
  ctx.fillText(`${productName} · 应用效果预览`, 1528, 74);
  ctx.textAlign = 'left';
  ctx.strokeStyle = '#d9cbb4';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(72, 100);
  ctx.lineTo(1528, 100);
  ctx.stroke();

  const shadow = (draw: () => void) => {
    ctx.save();
    ctx.shadowColor = 'rgba(45, 35, 24, 0.2)';
    ctx.shadowBlur = 28;
    ctx.shadowOffsetY = 18;
    draw();
    ctx.restore();
  };
  const fillRounded = (x: number, y: number, w: number, h: number, radius: number, color: string) => {
    roundedRect(ctx, x, y, w, h, radius);
    ctx.fillStyle = color;
    ctx.fill();
  };
  const clipArt = (x: number, y: number, w: number, h: number, radius = 0) => {
    ctx.save();
    if (radius) roundedRect(ctx, x, y, w, h, radius);
    else { ctx.beginPath(); ctx.rect(x, y, w, h); }
    ctx.clip();
    drawCover(ctx, image, x, y, w, h);
    ctx.restore();
  };

  switch (productId) {
    case 'postcard': {
      const x = 205, y = 270, w = 1190, h = 700;
      shadow(() => { fillRounded(x, y, w, h, 12, '#fffdf8'); });
      ctx.strokeStyle = '#ded4c3'; ctx.lineWidth = 2; ctx.strokeRect(x, y, w, h);
      clipArt(x + 28, y + 28, 735, h - 56, 5);
      ctx.strokeStyle = '#d4c6b2'; ctx.beginPath(); ctx.moveTo(x + 790, y + 28); ctx.lineTo(x + 790, y + h - 28); ctx.stroke();
      ctx.fillStyle = '#9e241b'; ctx.strokeStyle = '#c99b63'; ctx.lineWidth = 3; ctx.strokeRect(x + 835, y + 58, 100, 120); ctx.fillRect(x + 867, y + 90, 36, 56);
      ctx.strokeStyle = '#bdb5aa'; ctx.lineWidth = 3;
      for (let i = 0; i < 3; i += 1) { ctx.beginPath(); ctx.moveTo(x + 840, y + 480 + i * 38); ctx.lineTo(x + w - 55 - i * 48, y + 480 + i * 38); ctx.stroke(); }
      break;
    }
    case 'poster': {
      const x = 545, y = 190, w = 510, h = 820;
      shadow(() => { fillRounded(x - 18, y - 18, w + 36, h + 36, 7, '#fff'); });
      ctx.fillStyle = '#332c25'; ctx.fillRect(x - 8, y - 8, w + 16, h + 16);
      clipArt(x, y, w, h);
      break;
    }
    case 'bag': {
      const x = 535, y = 380, w = 530, h = 570;
      shadow(() => { ctx.strokeStyle = '#ded1bd'; ctx.lineWidth = 28; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(x + 150, y + 44); ctx.quadraticCurveTo(x + 155, y - 120, x + 265, y - 120); ctx.quadraticCurveTo(x + 375, y - 120, x + 380, y + 44); ctx.stroke(); });
      fillRounded(x, y, w, h, 30, '#e9dfce');
      ctx.save(); roundedRect(ctx, x + 36, y + 32, w - 72, h - 66, 18); ctx.clip();
      drawCover(ctx, image, x + 70, y + 86, w - 140, h - 176);
      ctx.fillStyle = 'rgba(255,255,255,.13)'; ctx.fillRect(x + 36, y + 32, w - 72, h - 66);
      ctx.restore();
      ctx.strokeStyle = 'rgba(134,109,76,.35)'; ctx.lineWidth = 2; roundedRect(ctx, x + 1, y + 1, w - 2, h - 2, 30); ctx.stroke();
      break;
    }
    case 'bookmark': {
      const x = 690, y = 245, w = 220, h = 750;
      shadow(() => { fillRounded(x, y, w, h, 10, '#fffaf0'); });
      ctx.strokeStyle = '#bb8a52'; ctx.lineWidth = 3; ctx.strokeRect(x + 8, y + 8, w - 16, h - 16);
      ctx.fillStyle = '#9e241b'; ctx.beginPath(); ctx.arc(800, y + 38, 15, 0, Math.PI * 2); ctx.fill();
      clipArt(x + 22, y + 75, w - 44, h - 180, 4);
      ctx.strokeStyle = '#9e241b'; ctx.lineWidth = 8; ctx.beginPath(); ctx.moveTo(800, y + h - 80); ctx.lineTo(800, y + h + 40); ctx.stroke();
      break;
    }
    case 'coaster': {
      const cx = 800, cy = 615, radius = 330;
      shadow(() => { ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2); ctx.fillStyle = '#fffdf7'; ctx.fill(); });
      ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, radius - 26, 0, Math.PI * 2); ctx.clip();
      drawCover(ctx, image, cx - radius + 26, cy - radius + 26, (radius - 26) * 2, (radius - 26) * 2);
      ctx.restore();
      ctx.strokeStyle = '#c4a77a'; ctx.lineWidth = 5; ctx.beginPath(); ctx.arc(cx, cy, radius - 12, 0, Math.PI * 2); ctx.stroke();
      break;
    }
    case 'social': {
      const x = 555, y = 165, w = 490, h = 900;
      shadow(() => { fillRounded(x, y, w, h, 66, '#242424'); });
      fillRounded(x + 18, y + 18, w - 36, h - 36, 52, '#f8f8f6');
      fillRounded(740, y + 18, 120, 34, 17, '#242424');
      clipArt(x + 38, y + 82, w - 76, 480, 8);
      ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(x + 70, y + 620, 27, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#d9d4cc'; ctx.fillRect(x + 118, y + 608, 170, 14);
      ctx.fillStyle = '#ece9e2'; ctx.fillRect(x + 40, y + 680, w - 80, 14); ctx.fillRect(x + 40, y + 714, w - 145, 14);
      ctx.fillStyle = '#f0ede6'; fillRounded(x + 40, y + 760, w - 80, 92, 12, '#f0ede6');
      break;
    }
    case 'screen': {
      const x = 195, y = 350, w = 1210, h = 680;
      shadow(() => { fillRounded(x, y, w, h, 26, '#171717'); });
      clipArt(x + 28, y + 26, w - 56, h - 54, 12);
      ctx.fillStyle = '#333'; ctx.fillRect(720, y + h, 160, 105); fillRounded(555, y + h + 100, 490, 24, 8, '#222');
      break;
    }
    case 'ticket': {
      const x = 170, y = 420, w = 1260, h = 400, split = x + 880;
      shadow(() => { fillRounded(x, y, w, h, 14, '#fffdf8'); });
      ctx.save(); roundedRect(ctx, x, y, w, h, 14); ctx.clip();
      clipArt(x + 18, y + 18, 844, h - 36);
      ctx.fillStyle = '#efe5d5'; ctx.fillRect(split, y, w - 880, h);
      ctx.restore();
      ctx.setLineDash([12, 10]); ctx.strokeStyle = '#b8aa98'; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(split, y + 10); ctx.lineTo(split, y + h - 10); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = paper; ctx.beginPath(); ctx.arc(split, y, 28, 0, Math.PI * 2); ctx.fill(); ctx.beginPath(); ctx.arc(split, y + h, 28, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#bd9d6d'; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(x + 1060, y + 110, 42, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = '#9e241b'; ctx.font = '600 32px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'; ctx.textAlign = 'center'; ctx.fillText('纪念票', x + 1060, y + 220); ctx.textAlign = 'left';
      break;
    }
    default:
      URL.revokeObjectURL(image.dataset.objectUrl || '');
      throw new Error('未知文创载体');
  }

  ctx.textAlign = 'center';
  ctx.fillStyle = '#9e241b';
  ctx.font = '600 22px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
  ctx.fillText(productName, canvas.width / 2, 1128);
  ctx.fillStyle = '#847966';
  ctx.font = '400 16px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
  ctx.fillText('基于当前 AI 生成作品的预设载体效果映射', canvas.width / 2, 1160);
  ctx.textAlign = 'left';

  try {
    return await new Promise<Blob>((resolve, reject) => canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error('PNG 图片导出失败')), 'image/png'));
  } finally {
    URL.revokeObjectURL(image.dataset.objectUrl || '');
  }
};

const renderMockup = (id: string, imageSrc: string) => {
  switch (id) {
    case 'postcard':
      return (
        <div className="w-[90%] aspect-[3/2] bg-[#F9F8F6] shadow-[0_4px_12px_rgba(0,0,0,0.08)] border border-black/5 p-3 flex relative z-10 transition-all duration-500 ease-out group-hover:scale-[1.05] group-hover:-translate-y-2 group-hover:rotate-2 group-hover:shadow-[0_15px_35px_rgba(0,0,0,0.15)] cursor-pointer active:scale-95 active:rotate-0">
          <div className="w-2/3 h-full border-r border-[#E0Dcd0] pr-3 overflow-hidden">
            <img src={imageSrc} alt="" className="w-full h-full object-cover shadow-sm opacity-90 transition-transform duration-700 group-hover:scale-110" />
          </div>
          <div className="w-1/3 h-full flex flex-col items-end justify-between pl-3 pb-1">
             <div className="w-5 h-6 border border-red-500/40 bg-red-50 flex items-center justify-center">
                <div className="w-3 h-4 border border-red-500/20"></div>
             </div>
             <div className="w-full flex-col flex gap-1.5">
                <div className="h-0.5 w-full bg-black/10"></div>
                <div className="h-0.5 w-full bg-black/10"></div>
                <div className="h-0.5 w-2/3 bg-black/10"></div>
             </div>
          </div>
        </div>
      );
    case 'poster':
      return (
        <div className="h-[90%] aspect-[3/4] bg-white shadow-[0_8px_20px_rgba(0,0,0,0.12)] border-[4px] border-gray-900 p-0.5 relative z-10 transition-transform group-hover:scale-[1.02] duration-500">
           <img src={imageSrc} alt="" className="w-full h-full object-cover" />
        </div>
      );
    case 'bag':
      return (
        <div className="w-full h-[95%] flex flex-col items-center justify-center mt-2 z-10 transition-transform group-hover:scale-[1.02] duration-500">
           <div className="w-1/2 h-8 border-t-[5px] border-x-[5px] border-[#E8E1D5] rounded-t-[1rem] mb-[-4px] z-0"></div>
           <div className="w-[70%] aspect-[4/5] bg-[#F2EDE4] shadow-[0_6px_16px_rgba(0,0,0,0.1)] rounded-b-xl z-10 p-4 pb-6 flex items-center justify-center relative overflow-hidden hover:shadow-lg transition-shadow">
              <div className="absolute inset-0 bg-gradient-to-tr from-black/5 to-white/40 mix-blend-overlay z-10"></div>
              <img src={imageSrc} alt="" className="w-full h-full object-cover mix-blend-multiply opacity-80" />
           </div>
        </div>
      );
    case 'bookmark':
      return (
        <div className="h-[95%] flex flex-col items-center py-1 z-10 transition-transform group-hover:scale-[1.02] duration-500">
           <div className="w-[3px] h-6 bg-[#B5332E] relative -mb-1 z-0">
              <div className="absolute top-4 left-1/2 -translate-x-1/2 w-4 h-1 bg-gold/80 rounded-sm z-10"></div>
              <div className="absolute top-5 left-1/2 -translate-x-1/2 w-3 h-8 bg-gradient-to-b from-[#A5231E] to-[#7A1712] rounded-b-sm"></div>
           </div>
           <div className="w-14 min-h-[140px] h-[85%] bg-rice-paper shadow-md border-x border-b border-primary/20 rounded-sm relative z-10 p-1 flex flex-col items-center shadow-[0_4px_12px_rgba(0,0,0,0.1)]">
               <div className="w-2.5 h-2.5 rounded-full border border-primary/30 mt-1 mb-2 bg-white flex-shrink-0"></div>
               <div className="w-full flex-1 relative overflow-hidden border border-primary/20 p-0.5 bg-white">
                 <img src={imageSrc} alt="" className="w-full h-full object-cover" />
               </div>
               <div className="h-4 border-l-2 border-primary/30 my-2 flex-shrink-0"></div>
           </div>
        </div>
      );
    case 'coaster':
      return (
        <div className="w-[65%] aspect-square rounded-full shadow-[0_8px_20px_rgba(0,0,0,0.15)] bg-[#F8F6F2] overflow-hidden border-[6px] border-[#F4EFEB] relative flex items-center justify-center z-10 transition-transform group-hover:scale-[1.02] duration-500">
            <div className="w-[90%] aspect-square rounded-full border border-primary/30 overflow-hidden relative">
                <img src={imageSrc} alt="" className="w-full h-full object-cover mix-blend-multiply opacity-90" />
            </div>
            <div className="absolute inset-0 rounded-full shadow-inner pointer-events-none border border-white/50"></div>
        </div>
      );
    case 'social':
      return (
        <div className="h-[90%] aspect-[9/19] bg-gray-800 rounded-[1.5rem] p-1.5 shadow-[0_10px_25px_rgba(0,0,0,0.2)] flex-shrink-0 flex items-center justify-center z-10 transition-transform group-hover:scale-[1.02] duration-500">
           <div className="w-full h-full bg-[#f8f9fa] rounded-[1.2rem] overflow-hidden relative shadow-inner">
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[40%] h-[14px] bg-gray-800 rounded-b-lg z-20 flex items-center justify-center">
                   <div className="w-1/4 h-1 bg-black/50 rounded-full"></div>
              </div>
              <div className="w-full h-[55%] relative bg-primary/10 overflow-hidden">
                  <img src={imageSrc} alt="" className="absolute inset-0 w-full h-full object-cover blur-sm opacity-40 mix-blend-overlay scale-110" />
                  <img src={imageSrc} alt="" className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[75%] aspect-[3/4] object-cover border-[2px] border-white shadow-md rounded" />
              </div>
              <div className="p-3 bg-white h-[45%] flex flex-col">
                 <div className="flex gap-2 mb-2">
                     <div className="w-5 h-5 rounded-full bg-primary/20 shrink-0"></div>
                     <div className="w-16 h-2 mt-1 bg-gray-200 rounded"></div>
                 </div>
                 <div className="w-full h-1.5 bg-gray-100 rounded mb-1.5"></div>
                 <div className="w-2/3 h-1.5 bg-gray-100 rounded mb-3"></div>
                 <div className="w-full flex-1 bg-gray-50 rounded border border-gray-100"></div>
              </div>
           </div>
        </div>
      );
    case 'screen':
      return (
        <div className="w-[85%] flex flex-col items-center z-10 transition-transform group-hover:scale-[1.02] duration-500">
           <div className="w-full aspect-video bg-[#1a1a1a] rounded-lg p-1.5 shadow-[0_8px_30px_rgba(0,0,0,0.25)] border-b-[4px] border-gray-900 border-x-2 border-t-2 relative">
               <div className="w-full h-full bg-black relative overflow-hidden">
                   <img src={imageSrc} alt="" className="absolute inset-0 w-full h-full object-cover" />
               </div>
           </div>
           <div className="w-[15%] h-4 bg-gradient-to-b from-gray-800 to-gray-700"></div>
           <div className="w-[45%] h-1.5 bg-gray-800 rounded-t-sm shadow-md"></div>
        </div>
      );
    case 'ticket':
      return (
        <div className="w-[90%] aspect-[2.5/1] bg-white shadow-[0_6px_16px_rgba(0,0,0,0.12)] flex relative overflow-hidden z-10 border border-black/5 transition-transform group-hover:scale-[1.02] duration-500">
           <div className="absolute top-0 left-[70%] -translate-x-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-paper shadow-inner border-b border-black/10 z-20"></div>
           <div className="absolute bottom-0 left-[70%] -translate-x-1/2 translate-y-1/2 w-4 h-4 rounded-full bg-paper shadow-inner border-t border-black/10 z-20"></div>
           <div className="absolute left-[70%] top-0 bottom-0 border-l-[2px] border-dashed border-gray-300 -translate-x-1/2 z-10"></div>
           
           <div className="w-[70%] h-full relative border-r border-black/5 bg-[#F9F8F6]">
              <img src={imageSrc} alt="" className="w-full h-full object-cover mix-blend-multiply opacity-90 p-0.5" />
           </div>
           
           <div className="w-[30%] h-full bg-[#E5DACE]/40 flex flex-col items-center justify-center p-2 relative">
              <div className="w-6 h-6 rounded-full border border-primary/20 mb-2 flex items-center justify-center">
                 <div className="w-2.5 h-2.5 bg-primary/20 rounded-full flex gap-px items-center justify-center">
                 </div>
              </div>
              <div className="mt-auto w-full flex flex-col gap-1 items-center">
                 <div className="w-[80%] h-0.5 bg-gray-300"></div>
                 <div className="w-[50%] h-0.5 bg-gray-300"></div>
              </div>
           </div>
        </div>
      );
    default:
      return null;
  }
};

export default function ProductStudio() {
  const navigate = useNavigate();
  const [sourceData, setSourceData] = useState<{
    imageUrl: string;
    title: string;
    theme: string;
    styleName: string;
    styleStrength?: number;
    provider?: string;
    mode?: string;
  } | null>(null);
  const [sourceImageError, setSourceImageError] = useState(false);
  
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [downloadingProductId, setDownloadingProductId] = useState<string | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem('wenmai_latest_result');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed && parsed.imageUrl) {
          setSourceData({
            imageUrl: resolveGeneratedImageUrl(parsed.imageUrl),
            title: parsed.cultureCard?.title || '生成艺术作品',
            theme: parsed.theme || parsed.cultureCard?.title || '最近一次生成作品',
            styleName: parsed.styleName || '源素材',
            styleStrength: typeof parsed.styleStrength === 'number' ? parsed.styleStrength : undefined,
            provider: parsed.provider || parsed.mode || 'unknown',
            mode: parsed.mode || 'unknown'
          });
        }
      } catch(e) {}
    }
  }, []);

  const handleSelectPreview = (id: string) => {
    const product = PRODUCTS.find(item => item.id === id);
    setSelectedProductId(id);
    setToast(`已选择${product?.name || '文创载体'}效果预览`);
    window.setTimeout(() => setToast(null), 2500);
  };

  const handleDownloadProduct = async (id: string) => {
    const product = PRODUCTS.find(item => item.id === id);
    if (!product || !sourceData || sourceImageError || downloadingProductId) return;
    setDownloadingProductId(id);
    setToast(`正在导出${product.name}效果图…`);
    try {
      const png = await renderProductExport(id, sourceData.imageUrl, product.name);
      const objectUrl = URL.createObjectURL(png);
      const anchor = document.createElement('a');
      anchor.href = objectUrl;
      anchor.download = `wenmai_${id}_${fileTimestamp()}.png`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1500);
      setToast(`${product.name}效果图已下载（1600 × 1200 PNG）`);
    } catch (error) {
      setToast(error instanceof Error ? error.message : '效果图导出失败，请稍后重试。');
    } finally {
      setDownloadingProductId(null);
      window.setTimeout(() => setToast(null), 3500);
    }
  };

  const displayImage = sourceImageError ? DEFAULT_SOURCE_IMAGE : (sourceData?.imageUrl || DEFAULT_SOURCE_IMAGE);

  return (
    <div className="max-w-7xl mx-auto px-6 py-12">
      <div className="text-center mb-16">
        <h1 className="text-4xl font-serif text-primary font-bold mb-4">文创衍生效果中心</h1>
        <p className="text-lg text-ink/80 max-w-2xl mx-auto">
          将最近一次生成作品映射到预设文创载体模板，预览其在数字海报、纪念品和传播画面中的视觉效果。此页面提供应用示意，不包含实体生产、订单或印刷服务。
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-12 mb-20">
        {/* Left: Origin Artwork */}
        <div className="lg:w-1/3">
          <div className="sticky top-24">
            <h3 className="chinese-plaque text-lg mb-4">源作品</h3>
            <div className="bg-white p-4 rounded bg-rice-paper shadow-sm border border-primary/20 chinese-border mt-2">
              <div className="rounded overflow-hidden aspect-[3/4] mb-4 border-[6px] border-white shadow-sm">
                <img 
                  src={displayImage} 
                  alt="当前生成作品" 
                  onError={(e) => { setSourceImageError(true); e.currentTarget.src = DEFAULT_SOURCE_IMAGE; }}
                  className="w-full h-full object-cover"
                />
              </div>
              <h4 className="font-serif font-bold text-lg text-primary text-center">{sourceData?.title || '开封宋韵印象'}</h4>
              <p className="text-xs text-ink/80 font-medium text-center mt-1">{sourceData?.theme || '示例源素材'}</p>
              <p className="text-xs text-ink/60 text-center mt-1 pb-2 border-b border-black/5">
                {sourceData?.styleName || '示例源素材'}
                {typeof sourceData?.styleStrength === 'number' ? ` · 强度 ${sourceData.styleStrength.toFixed(2)}` : ''}
              </p>
              {!sourceData ? (
                 <p className="text-xs text-ink/50 text-center mt-2 flex flex-col items-center gap-1">
                    当前为示例作品
                    <button onClick={()=>navigate('/creator')} className="text-primary hover:underline">前往智能生成页生成新作品</button>
                 </p>
              ) : (
                 <>
                   <p className="text-xs text-green-600 text-center mt-2 font-medium">{getSourceLabel(sourceData.provider, sourceData.mode)}</p>
                   <p className="text-[10px] text-ink/50 text-center mt-1 font-mono">mode: {sourceData.mode} · provider: {sourceData.provider}</p>
                   {sourceImageError && <p className="text-xs text-primary text-center mt-1 break-all">原图地址无法加载，已使用示例图兜底：{sourceData.imageUrl}</p>}
                 </>
              )}
            </div>
          </div>
        </div>

        {/* Right: Mockups Grid */}
        <div className="lg:w-2/3">
          <div className="bg-primary/5 border border-primary/10 rounded-lg p-4 mb-8 flex items-start gap-3">
             <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                <ShoppingBag className="w-4 h-4 text-primary" />
             </div>
             <div>
                <h4 className="font-bold text-ink mb-1">文创效果一键预览</h4>
                <p className="text-sm text-ink/70">作品会显示在预设的文创载体模板中，用于比较不同版式与媒介的视觉呈现；模板不是独立生成的产品图片。</p>
             </div>
          </div>
          <h3 className="chinese-plaque text-lg mb-4">文创载体效果预览</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-6">
            {PRODUCTS.map((product, i) => {
              const Icon = product.icon;
              return (
                <motion.div
                  key={product.id}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.4, delay: i * 0.1 }}
                  className="bg-white rounded-xl shadow-sm border border-border-red/10 overflow-hidden flex flex-col group hover:shadow-md transition-shadow"
                >
                  <div className="bg-paper p-4 flex-1 flex items-center justify-center relative overflow-hidden aspect-square">
                    <div className="absolute inset-0 bg-white/40 z-0 pointer-events-none"></div>
                    {renderMockup(product.id, displayImage)}
                  </div>
                  <div className="p-3 text-center border-t border-border-red/5">
                    <p className="text-sm font-medium text-ink flex items-center justify-center gap-1.5 mb-2">
                       <Icon className="w-3.5 h-3.5 text-primary/70" />
                       {product.name}
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                         onClick={() => handleSelectPreview(product.id)}
                         aria-pressed={selectedProductId === product.id}
                         className={cn("min-h-9 rounded border transition-colors text-[11px] font-medium flex items-center justify-center gap-1", selectedProductId === product.id ? "bg-primary text-white border-primary" : "bg-primary/5 hover:bg-primary text-primary hover:text-white border-primary/20 hover:border-primary")}
                      >
                        {selectedProductId === product.id ? <><Check className="w-3 h-3"/> 已选择</> : <>查看效果</>}
                      </button>
                      <button
                        onClick={() => void handleDownloadProduct(product.id)}
                        disabled={!sourceData || sourceImageError || downloadingProductId !== null}
                        className="min-h-9 rounded border border-primary/20 bg-white text-[11px] font-medium text-primary flex items-center justify-center gap-1 transition-colors hover:bg-primary hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
                        aria-label={`下载${product.name}效果图`}
                      >
                        {downloadingProductId === product.id ? <LoaderCircle className="h-3 w-3 animate-spin" /> : <Download className="h-3 w-3" />}
                        {downloadingProductId === product.id ? '导出中' : '下载效果图'}
                      </button>
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Recommended Bundles */}
      <div className="mb-20">
        <h3 className="chinese-plaque text-lg mb-8">推荐组合应用方案</h3>
        <div className="grid md:grid-cols-3 gap-6">
          <div className="bg-rice-paper p-6 rounded-2xl border border-primary/10 shadow-sm hover:shadow-md transition-shadow">
             <div className="w-12 h-12 bg-primary/5 rounded-full flex items-center justify-center mb-4 text-primary">
                <Smartphone className="w-5 h-5" />
             </div>
             <h4 className="font-bold text-ink mb-2">文旅线上传播组合</h4>
             <p className="text-sm text-ink/70 mb-4">数字海报 + 手机分享图 + 文化说明卡</p>
             <div className="text-xs text-primary/80 bg-primary/5 p-2 rounded">适合用于构思数字海报、手机分享图和文化说明卡的组合呈现。</div>
          </div>
          <div className="bg-rice-paper p-6 rounded-2xl border border-primary/10 shadow-sm hover:shadow-md transition-shadow">
             <div className="w-12 h-12 bg-primary/5 rounded-full flex items-center justify-center mb-4 text-primary">
                <ShoppingBag className="w-5 h-5" />
             </div>
             <h4 className="font-bold text-ink mb-2">景区实体零售组合</h4>
             <p className="text-sm text-ink/70 mb-4">帆布袋 + 明信片 + 陶瓷杯垫</p>
             <div className="text-xs text-primary/80 bg-primary/5 p-2 rounded">用于展示帆布袋、明信片与杯垫等载体的组合效果，实际制作需另行评估。</div>
          </div>
          <div className="bg-rice-paper p-6 rounded-2xl border border-primary/10 shadow-sm hover:shadow-md transition-shadow">
             <div className="w-12 h-12 bg-primary/5 rounded-full flex items-center justify-center mb-4 text-primary">
                <MonitorPlay className="w-5 h-5" />
             </div>
             <h4 className="font-bold text-ink mb-2">文博数字展陈组合</h4>
             <p className="text-sm text-ink/70 mb-4">大屏轮播 + 景区纪念票 + H5页面</p>
             <div className="text-xs text-primary/80 bg-primary/5 p-2 rounded">用于示意作品在展陈屏、纪念票和活动页面中的组合展示方式。</div>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-12 mb-12">
        {/* Advice */}
        <div className="bg-white p-8 border border-border-red/10 shadow-sm rounded-2xl">
           <h3 className="text-xl font-serif text-primary mb-6 flex items-center gap-2">
             <Frame className="w-5 h-5" /> 后续设计参考
           </h3>
           <ul className="space-y-4">
             <li className="flex items-start gap-3">
               <div className="w-1.5 h-1.5 rounded-full bg-gold mt-2 shrink-0"></div>
               <div><span className="font-bold text-sm text-ink">画面比例：</span><p className="text-sm text-ink/70 mt-1">模板采用不同载体比例进行界面预览；模型输出尺寸由后端服务配置决定，正式设计时需另行裁切与排版。</p></div>
             </li>
             <li className="flex items-start gap-3">
               <div className="w-1.5 h-1.5 rounded-full bg-gold mt-2 shrink-0"></div>
               <div><span className="font-bold text-sm text-ink">载体适配：</span><p className="text-sm text-ink/70 mt-1">当前效果用于比较不同载体中的构图观感，材质、工艺与印刷效果需要通过实际打样确认。</p></div>
             </li>
             <li className="flex items-start gap-3">
               <div className="w-1.5 h-1.5 rounded-full bg-gold mt-2 shrink-0"></div>
               <div><span className="font-bold text-sm text-ink">文件检查：</span><p className="text-sm text-ink/70 mt-1">下载原图后，请在后续设计环节核对尺寸、色彩配置文件与授权条件，再交由专业印制流程评估。</p></div>
             </li>
           </ul>
        </div>

        {/* Next Steps */}
        <div className="bg-primary p-8 rounded-2xl shadow-lg text-white relative border-[4px] border-white ring-1 ring-black/5 overflow-hidden">
           <div className={`absolute inset-0 bg-[url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.1'/%3E%3C/svg%3E")]`}></div>
           <h3 className="text-xl font-serif mb-8 text-gold flex items-center gap-2 relative z-10">
              文创应用流程
           </h3>
           <div className="space-y-6 relative z-10">
              {[
                { s: "STEP 01", t: "在创作工作台输入主题并生成视觉作品" },
                { s: "STEP 02", t: "选择文创载体或数字传播场景" },
                { s: "STEP 03", t: "查看预设模板中的载体效果示意" },
                { s: "STEP 04", t: "下载生成原图，供后续设计与展示" }
              ].map((step, i) => (
                <div key={i} className="flex items-center gap-4">
                   <div className="w-16 text-xs font-mono text-gold/70">{step.s}</div>
                   <div className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center shrink-0 border border-gold/30">
                     <div className="w-2 h-2 rounded-full bg-gold"></div>
                   </div>
                   <div className="text-sm flex-1">{step.t}</div>
                </div>
              ))}
           </div>
        </div>
      </div>
      
      {/* Toast Notification */}
      <AnimatePresence>
         {toast && (
            <motion.div 
               initial={{ opacity: 0, y: 50, x: '-50%' }}
               animate={{ opacity: 1, y: 0, x: '-50%' }}
               exit={{ opacity: 0, y: 20, x: '-50%' }}
               className="fixed bottom-8 left-1/2 bg-gray-900 text-white px-6 py-3 rounded-full shadow-2xl z-50 flex items-center gap-2"
            >
               <Check className="w-4 h-4 text-green-400" />
               <span className="text-sm font-medium">{toast}</span>
            </motion.div>
         )}
      </AnimatePresence>
    </div>
  );
}
