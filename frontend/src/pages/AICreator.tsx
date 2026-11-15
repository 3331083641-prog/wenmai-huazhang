import React, { useState, useRef, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { cn } from '../lib/utils';
import { ImagePlus, Download, ArrowRight, Wand2, RefreshCw, RotateCw, Crop, ZoomIn, ZoomOut, Check, Sparkles } from 'lucide-react';
import { STYLES } from '../data/styleLibrary';
import { projectBrand } from '../data/projectBrand';
import { BackendHealth, buildLocalCultureCard, checkBackendHealth, generateImage, GeneratePayload, GenerateResponse } from '../services/generationService';
import CultureCard from '../components/creator/CultureCard';
import OrientalInkWaiting from '../components/OrientalInkWaiting';

const GENERATION_STEPS = [
  "正在整理主题与参考图...",
  "正在整理风格生成提示词...",
  "正在调用生成引擎...",
  "正在等待生成结果...",
  "生成与文化分析进行中，请稍候...",
  "完成"
];

const getModeLabel = (mode: string) => {
  if (mode === 'image_to_image') return '参考图创作';
  return '文本创作';
};
const filenameTimestamp = (date = new Date()) => {
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}_${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`;
};
const fileToBase64 = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        resolve(reader.result);
      } else {
        reject(new Error('图片解析失败'));
      }
    };
    reader.onerror = () => reject(reader.error || new Error('图片解析失败'));
    reader.readAsDataURL(file);
  });
};

export default function AICreator() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialStyle = searchParams.get('style') || 'zhuxianzhen';
  
  const [savedExample, setSavedExample] = useState(false);
  const [prompt, setPrompt] = useState('一名大学生站在开封古城门前，微笑着挥手，身后是宋代城楼与祥云纹样...');
  const [subjectLock, setSubjectLock] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [selectedStyle, setSelectedStyle] = useState(initialStyle);
  const [outputType, setOutputType] = useState('poster');
  const [composition, setComposition] = useState('portrait');
  const [styleStrength, setStyleStrength] = useState(65);
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDownloadingResult, setIsDownloadingResult] = useState(false);
  const [generationStep, setGenerationStep] = useState(0);
  const [hasResult, setHasResult] = useState(false);
  const [resultData, setResultData] = useState<GenerateResponse | null>(null);
  const [resultImage, setResultImage] = useState('');
  const [enhancedPrompt, setEnhancedPrompt] = useState('');
  const [mode, setMode] = useState<string>('text_to_image');
  const [resultPayload, setResultPayload] = useState<GeneratePayload | null>(null);
  const [resultCreatedAt, setResultCreatedAt] = useState('');
  const [connectionNotice, setConnectionNotice] = useState<string | null>(null);
  const [downloadStatus, setDownloadStatus] = useState<string | null>(null);
  const [backendHealth, setBackendHealth] = useState<BackendHealth | null>(null);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');
  const [imageLoadState, setImageLoadState] = useState<'idle' | 'loading' | 'loaded' | 'error'>('idle');
  const [imageLoadError, setImageLoadError] = useState<string | null>(null);
  const [savedCase, setSavedCase] = useState<GenerateResponse['savedCase']>(null);
  const [autoSaveError, setAutoSaveError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const generationLockRef = useRef(false);
  const [isDragActive, setIsDragActive] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [uploadedImageBase64, setUploadedImageBase64] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const [rotation, setRotation] = useState(0);
  const [scale, setScale] = useState(1);
  const [isCropping, setIsCropping] = useState(false);

  // For history
  const [historyImages, setHistoryImages] = useState<string[]>([]);
  
  useEffect(() => {
     const saved = localStorage.getItem('wenmai_latest_result');
     if (saved) {
        try {
           const parsed = JSON.parse(saved);
           if (parsed && parsed.imageUrl) {
              setHistoryImages([parsed.imageUrl]);
              setSavedExample(parsed.savedExample === true);
              if (parsed.referencePreviewUrl) setPreviewUrl(parsed.referencePreviewUrl);
              const restoredPayload: GeneratePayload = {
                theme: parsed.theme || '传统文化主题创作',
                style: parsed.style || 'zhuxianzhen',
                styleName: parsed.styleName || '',
                outputType: parsed.outputType || 'poster',
                styleStrength: typeof parsed.styleStrength === 'number' ? parsed.styleStrength : 0.65,
                compositionMode: parsed.compositionMode || 'portrait',
                negativePrompt: parsed.negativePrompt || null,
                subjectLock: parsed.subjectLock || null,
                uploadedImage: null,
                generationProvider: 'dashscope_qwen_image',
              };
              // The form reflects the same request as the restored result so
              // users do not see one style selected while another style is shown.
              setPrompt(restoredPayload.theme);
              setNegativePrompt(restoredPayload.negativePrompt || '');
              setSubjectLock(restoredPayload.subjectLock || '');
              setSelectedStyle(restoredPayload.style);
              setOutputType(restoredPayload.outputType);
              setComposition(restoredPayload.compositionMode);
              setStyleStrength(Math.round(restoredPayload.styleStrength * 100));
              const restoredMode = parsed.mode || (parsed.referenceImageUsed ? 'image_to_image' : 'text_to_image');
              const restoredCard = parsed.cultureCard || buildLocalCultureCard(restoredPayload, parsed.imageAnalysis || null);
              setResultPayload(restoredPayload);
              setResultImage(parsed.imageUrl);
              setResultCreatedAt(parsed.createdAt || new Date().toISOString());
              setEnhancedPrompt(parsed.enhancedPrompt || '');
              setMode(restoredMode);
              setResultData({
                success: true,
                imageUrl: parsed.imageUrl,
                enhancedPrompt: parsed.enhancedPrompt || '',
                mode: restoredMode,
                provider: parsed.provider,
                model: parsed.model || 'qwen-image-3.0',
                referenceImageUsed: parsed.referenceImageUsed === true,
                analysisSource: parsed.analysisSource || 'template_fallback',
                visionAnalysis: parsed.visionAnalysis || null,
                cultureCard: restoredCard,
                imageAnalysis: parsed.imageAnalysis || null,
                engine: parsed.engine || null,
              });
              setImageLoadState('loading');
              setHasResult(true);
           }
        } catch(e) {}
     }
  }, []);

  useEffect(() => {
    let cancelled = false;
    setBackendStatus('checking');
    (import.meta.env.VITE_STATIC_SHOWCASE === 'true' ? Promise.reject(new Error('在线浏览模式：实时生成请下载项目后在本机启动。')) : checkBackendHealth())
      .then((health) => {
        if (cancelled) return;
        setBackendHealth(health);
        setBackendStatus('connected');
        setConnectionNotice(null);
      })
      .catch((error) => {
        if (cancelled) return;
        setBackendHealth(null);
        setBackendStatus('disconnected');
        setConnectionNotice(error instanceof Error ? error.message : '后端未连接，请先启动 FastAPI。');
      });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const handleRotate = () => setRotation(r => r + 90);
  const handleZoomIn = () => setScale(s => Math.min(s + 0.2, 3));
  const handleZoomOut = () => setScale(s => Math.max(s - 0.2, 0.5));

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(true);
  };
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);
  };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!file.type.match('image/(jpeg|png|jpg)')) {
      alert('仅支持 PNG 和 JPG 格式');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      alert('参考图不能超过 10 MB');
      return;
    }
    setIsUploading(true);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setUploadedImageBase64(null);

    const nextPreviewUrl = URL.createObjectURL(file);
    setPreviewUrl(nextPreviewUrl);

    try {
      const base64 = await fileToBase64(file);
      setPreviewUrl(nextPreviewUrl);
      setUploadedImageBase64(base64);
      setIsUploading(false);
    } catch {
      URL.revokeObjectURL(nextPreviewUrl);
      setPreviewUrl(null);
      setIsUploading(false);
      alert('图片解析失败，请重新上传');
    }
  };

  const currentStyleData = STYLES.find(s => s.id === selectedStyle);

  const commitGenerationResult = (payload: GeneratePayload, response: GenerateResponse) => {
    const nextCultureCard = response.cultureCard || buildLocalCultureCard(payload, response.imageAnalysis || null);
    const nextResult: GenerateResponse = {
      ...response,
      cultureCard: nextCultureCard,
    };

    const createdAt = new Date().toISOString();
    setResultPayload(payload);
    setResultCreatedAt(createdAt);
    setResultImage(nextResult.imageUrl);
    setImageLoadState(nextResult.imageUrl ? 'loading' : 'error');
    setImageLoadError(nextResult.imageUrl ? null : '后端没有返回可加载的图片地址。');
    setEnhancedPrompt(nextResult.enhancedPrompt);
    setMode(nextResult.mode);
    setResultData(nextResult);
    setHasResult(true);
    setHistoryImages(prev => [nextResult.imageUrl, ...prev].slice(0, 3));

    const resultToSave = {
       theme: payload.theme,
       style: payload.style,
       styleName: payload.styleName,
       outputType: payload.outputType,
       styleStrength: payload.styleStrength,
       compositionMode: payload.compositionMode,
       imageUrl: nextResult.imageUrl,
       enhancedPrompt: nextResult.enhancedPrompt,
       mode: nextResult.mode,
       provider: nextResult.provider || nextResult.mode,
       generationProvider: payload.generationProvider || 'dashscope_qwen_image',
       engine: nextResult.engine || null,
       model: nextResult.model || null,
       referenceImageUsed: nextResult.referenceImageUsed === true,
       styleReferenceUsed: nextResult.styleReferenceUsed === true,
       analysisSource: nextResult.analysisSource || 'template_fallback',
       visionAnalysis: nextResult.visionAnalysis || null,
       cultureCard: nextCultureCard,
       imageAnalysis: nextResult.imageAnalysis || null,
       realProviderError: nextResult.realProviderError || null,
       createdAt,
       negativePrompt: payload.negativePrompt,
       subjectLock: payload.subjectLock || null,
    };
    localStorage.setItem('wenmai_latest_result', JSON.stringify(resultToSave));

    // 后端已把这次结果落盘成展厅案例；这里只做提示，不重复上传
    setSavedCase(nextResult.savedCase ?? null);
    setAutoSaveError(nextResult.autoSave?.enabled && !nextResult.autoSave.saved ? (nextResult.autoSave.error || '自动保存未完成') : null);
  };

  const handleGenerate = async () => {
    if (generationLockRef.current) return;
    generationLockRef.current = true;
    setIsGenerating(true);
    setSavedExample(false);
    setHasResult(false);
    setResultData(null);
    setResultImage('');
    setEnhancedPrompt('');
    setGenerationStep(0);
    setRotation(0);
    setScale(1);
    setIsCropping(false);
    setConnectionNotice(null);
    setImageLoadState('idle');
    setImageLoadError(null);
    setSavedCase(null);
    setAutoSaveError(null);
    
    // Animate steps
    let currentStep = 0;
    let stepInterval: number | null = window.setInterval(() => {
      currentStep++;
      if (currentStep < GENERATION_STEPS.length - 1) {
        setGenerationStep(currentStep);
      }
    }, 1500);

    try {
        if (import.meta.env.VITE_STATIC_SHOWCASE === 'true') throw new Error('在线浏览模式不执行实时推理。请下载源码，在本机配置个人 API Key 后运行。');
        const health = await checkBackendHealth();
        setBackendHealth(health);
        setBackendStatus('connected');
        const payload: GeneratePayload = {
            theme: prompt,
            style: selectedStyle,
            styleName: currentStyleData?.name || '',
            outputType: outputType,
            styleStrength: styleStrength / 100,
            compositionMode: composition,
            negativePrompt: negativePrompt || null,
            subjectLock: subjectLock.trim() || null,
            uploadedImage: uploadedImageBase64,
            generationProvider: 'dashscope_qwen_image',
        };
        
        const res = await generateImage(payload);
        
        setGenerationStep(GENERATION_STEPS.length - 1); // Finished

        if (!res.success) {
          setConnectionNotice(res.error || '真实生成失败，请检查后端配置。');
          alert(res.error || '真实生成失败，请检查后端配置。');
          return;
        }
        
        commitGenerationResult(payload, res);

    } catch (error) {
        const message = error instanceof Error ? error.message : "生成出现异常，请稍后重试";
        if (/FastAPI|health|后端/.test(message)) {
          setBackendStatus('disconnected');
        }
        setConnectionNotice(message);
        alert(message);
    } finally {
        if (stepInterval !== null) {
          window.clearInterval(stepInterval);
          stepInterval = null;
        }
        generationLockRef.current = false;
        setIsGenerating(false);
    }
  };

  const handleDownloadResult = async () => {
    if (!resultImage || isDownloadingResult) return;
    setIsDownloadingResult(true);
    try {
      const response = await fetch(resultImage, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const imageBlob = await response.blob();
      const objectUrl = URL.createObjectURL(imageBlob);
      const anchor = document.createElement('a');
      anchor.href = objectUrl;
      const styleSlug = (resultPayload?.style || 'traditional').replace(/[^a-z0-9_-]/gi, '_');
      anchor.download = `${projectBrand.filePrefix}_generated_${styleSlug}_${filenameTimestamp()}.png`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      setDownloadStatus('生成原图已下载。');
      window.setTimeout(() => setDownloadStatus(null), 3000);
    } catch {
      setDownloadStatus('图片下载失败，请确认生成图片仍可从本地后端访问。');
      window.setTimeout(() => setDownloadStatus(null), 5000);
    } finally {
      setIsDownloadingResult(false);
    }
  };

  const resultStyleData = STYLES.find((style) => style.id === resultPayload?.style) || STYLES[0];
  const resultGeneratedAt = resultCreatedAt || new Date().toISOString();
  const resultCultureSummary = resultPayload
    ? resultData?.visionAnalysis?.culture_interpretation || `以“${resultPayload.theme.trim().slice(0, 24) || '传统文化主题'}”为创作主题，参考${resultStyleData.name}的${resultStyleData.visualFeatures.slice(0, 3).join('、')}等视觉语言进行数字再创作。`
    : '';
  const requestId = typeof resultData?.debug?.dashscopeRequestId === 'string'
    ? resultData.debug.dashscopeRequestId
    : typeof resultData?.debug?.request_id === 'string' ? resultData.debug.request_id : null;

  return (
    <div className="flex flex-col lg:flex-row min-h-[calc(100vh-64px)] w-full bg-paper">
      {/* Container to enforce exact max-w-7xl constraint overall but stretching inside */}
      <div className="flex-1 flex flex-col lg:flex-row w-full max-w-7xl mx-auto border-x border-gold/20 shadow-[0_20px_50px_rgba(63,43,31,0.06)] bg-[#FCF7EE]">
         
         {/* Left Workspace (文房画案) */}
         <div className="lg:w-[50%] flex flex-col border-r border-gold/25 bg-white/70 backdrop-blur-sm">
            <div className="h-20 bg-gradient-to-r from-[#FAF3E6] via-[#FCF8F0] to-[#FAF3E6] relative overflow-hidden flex items-center px-6 border-b border-gold/30">
               <div className="absolute inset-0 bg-cover bg-center opacity-8 filter sepia pointer-events-none" style={{backgroundImage: `url(${import.meta.env.BASE_URL}songhua.png)`}}></div>
               <div className="relative z-10 flex items-center gap-3">
                 <motion.div
                   className="w-14 h-14 shrink-0 cursor-pointer -my-2 group relative"
                   animate={{ y: [-2, 2], rotate: [-2, 2] }}
                   transition={{ duration: 4.5, repeat: Infinity, ease: 'easeInOut' }}
                   whileHover={{ scale: 1.15, rotate: 6 }}
                   whileTap={{ scale: 0.95 }}
                   onClick={() => {
                     if (!prompt) {
                       setPrompt("宋画青绿长卷，远岫晴云，江流清澈，舟楫掩映松石间，天然矿物石青石绿");
                     }
                   }}
                   title="东方数字艺术灵笔 · 点击注入意境灵感"
                 >
                   <img
                     src={import.meta.env.BASE_URL + "visuals/vnext/ui-img-01-cultural-brush.png"}
                     alt="东方数字艺术灵笔"
                     className="w-full h-full object-contain drop-shadow-[0_8px_18px_rgba(210,161,74,0.4)]"
                   />
                 </motion.div>
                 <div>
                   <h2 className="text-lg font-serif font-bold text-ink flex items-center gap-2">
                     国风智能创作工作台
                     <span className="chinese-seal text-[9px]">文房</span>
                   </h2>
                   <p className="text-[10px] text-ink/50 font-serif">Qwen Image 3.0 多模态创作引擎 · 灵笔在案</p>
                 </div>
               </div>
               <div className="ml-auto text-xs font-mono text-right relative z-10">
                 {backendStatus === 'connected' ? (
                   <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-[11px]">
                     <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse" />
                     <span>已连接 · {backendHealth?.model || 'Qwen Image 3.0'}</span>
                   </div>
                 ) : backendStatus === 'checking' ? (
                   <div className="text-ink/50 text-[11px]">检查模型连接中...</div>
                 ) : (
                   <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-primary/5 border border-primary/20 text-primary text-[11px]">
                     <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                     <span>未启动本地后端服务</span>
                   </div>
                 )}
               </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
              {savedExample && (
                <p role="status" className="mb-4 rounded-xl border border-gold/40 bg-white/80 p-3.5 text-xs text-primary font-serif shadow-xs">
                  已保存的作品 · 当前未执行实时推理。参考图预览为原始输入；重新生成需再次选择上传文件。
                </p>
              )}
              <section className="mb-6 rounded-xl border border-gold/30 bg-white/70 p-4 text-xs font-serif text-ink/75 shadow-xs" aria-label="模型服务状态">
                <div className="flex items-center justify-between mb-2 pb-2 border-b border-gold/20">
                  <span className="font-bold text-ink">双模态模型服务状态</span>
                  <span className="text-[10px] text-ink/50">本地与云端协同</span>
                </div>
                <p>图像生成 · Qwen Image 3.0：<span className="font-sans font-medium text-primary">{backendStatus === 'disconnected' ? '当前不可用' : backendStatus === 'checking' ? '检查中' : backendHealth?.providers?.dashscope_qwen_image?.hasApiKey === false ? '未配置' : backendHealth?.providers?.dashscope_qwen_image?.available ? '已连接（配置就绪）' : '当前不可用'}</span></p>
                <p className="mt-1.5">文化理解 · Qwen3-VL：<span className="font-sans font-medium text-primary">{backendHealth?.localVisionAnalysis?.available ? '本地可用' : '本地未启动或模型未安装'}</span></p>
                <p className="mt-2.5 text-[11px] text-ink/55 font-sans leading-relaxed">实时图像生成需配置阿里云百炼服务及个人 API Key。无模型也可<Link className="text-primary underline ml-1" to="/gallery">查看已保存的精选作品</Link>。</p>
              </section>

              {/* Prompt Area (题墨案) */}
              <div className="mb-6 rounded-xl border border-gold/30 bg-white/80 p-4 shadow-xs">
                <div className="flex justify-between items-center mb-2.5">
                   <h3 className="chinese-plaque text-xs py-1">输入创作主题</h3>
                   <div className="text-[10px] text-ink/45 font-mono">支持中英文提示</div>
                </div>
                <textarea
                  className="w-full h-24 p-3 bg-paper/40 border border-gold/30 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all text-xs sm:text-sm text-ink/90 resize-none hover:border-primary/40 leading-relaxed font-sans"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="描述你想生成的场景、人物、故事或纹样意象..."
                />
                <p className="mt-2 text-[10.5px] text-ink/50 font-serif">主题文本将与所选传统文化视觉风格共同编译为结构化提示词。</p>

                <div className="mt-4 pt-3 border-t border-gold/20">
                  <label htmlFor="subject-lock" className="mb-1.5 flex items-center gap-2 text-xs font-serif font-bold text-ink/80">
                    画面主体约束 <span className="rounded border border-primary/25 px-1.5 py-0.2 text-[9px] font-sans text-primary/70">可选参数</span>
                  </label>
                  <input
                    id="subject-lock"
                    value={subjectLock}
                    onChange={(e) => setSubjectLock(e.target.value)}
                    maxLength={120}
                    className="w-full rounded-lg border border-gold/30 bg-paper/40 p-2 text-xs sm:text-sm text-ink/90 transition-all hover:border-primary/40 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                    placeholder="例如：一只狸花猫，保持猫的身份与主要外形"
                  />
                  <p className="mt-1 text-[10px] text-ink/45 font-serif">填写后主体身份优先于装饰风格约束；未填时不增加额外限制。</p>
                </div>
                
                <div className="mt-4 pt-3 border-t border-gold/20">
                   <div className="flex justify-between items-center mb-1.5">
                      <h3 className="text-xs font-serif font-bold text-ink/80 flex items-center gap-2">
                        负向提示词 (排除元素) <span className="text-[9px] text-primary/70 font-sans border border-primary/25 px-1.5 py-0.2 rounded">可选参数</span>
                      </h3>
                   </div>
                   <input
                     className="w-full p-2 bg-paper/40 border border-gold/30 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all text-xs sm:text-sm text-ink/90 hover:border-primary/40"
                     value={negativePrompt}
                     onChange={(e) => setNegativePrompt(e.target.value)}
                     placeholder="例如：现代建筑、现代服饰、文字、水印..."
                   />
                </div>
              </div>

              {/* Upload Image Area (参考画样) */}
              <div className="mb-6 rounded-xl border border-gold/30 bg-white/80 p-4 shadow-xs">
                <div className="flex justify-between items-center mb-2.5">
                   <h3 className="chinese-plaque text-xs py-1 flex items-center gap-2">
                     上传参考图 <span className="text-[9px] text-primary/70 font-sans border border-primary/25 px-1.5 py-0.2 rounded">可选参数</span>
                   </h3>
                   <span className="text-[10px] text-ink/45 font-serif">构图姿态约束</span>
                </div>
                <div 
                  className={cn(
                    "border-2 border-dashed rounded-xl p-5 flex flex-col items-center justify-center text-center cursor-pointer transition-all relative overflow-hidden group",
                    isDragActive ? "border-primary bg-primary/8" : "border-gold/40 bg-paper/30 hover:bg-white hover:border-primary/60"
                  )}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" accept="image/png, image/jpeg, image/jpg" />
                  
                  {isUploading ? (
                     <div className="flex items-center gap-2 text-primary py-2 font-serif">
                        <RefreshCw className="w-5 h-5 animate-spin text-gold" />
                        <span className="text-xs">正在解析参考图样...</span>
                     </div>
                  ) : previewUrl ? (
                    <div className="relative w-full flex items-center justify-center gap-4">
                      <div className="w-20 h-20 rounded-lg shadow-sm overflow-hidden border-2 border-white relative group-hover:shadow-md transition-shadow shrink-0 bg-black/5">
                        <img src={previewUrl} alt="ref" className="w-full h-full object-cover" />
                      </div>
                      <div className="text-left flex-1">
                         <div className="text-xs font-serif font-bold text-ink flex items-center gap-1.5">
                           <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                           参考图已加入本次生成
                         </div>
                         <div className="text-[11px] text-ink/60 mt-1 mb-2 font-sans leading-relaxed">
                           参考图将连同构图姿态特征发送至 Qwen Image 3.0 多模态模型。
                         </div>
                         <div className="text-xs text-primary underline underline-offset-2 font-serif hover:text-primary-dark">
                           点击重新选择画样
                         </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center py-2">
                      <div className="w-10 h-10 rounded-full bg-gold/15 flex items-center justify-center mb-2 text-gold group-hover:scale-110 transition-transform">
                        <ImagePlus className="w-5 h-5 text-primary" />
                      </div>
                      <p className="text-xs font-serif font-bold text-ink/80">拖拽或点击上传参考画样</p>
                      <p className="text-[10px] text-ink/45 mt-1 font-sans">支持 PNG / JPG，≤10 MB；参与本次 Qwen Image 3.0 多模态推理</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Style Selection (五色设色) */}
              <div className="mb-6 rounded-xl border border-gold/30 bg-white/80 p-4 shadow-xs">
                <div className="flex justify-between items-center mb-2.5">
                   <h3 className="chinese-plaque text-xs py-1">选择核心风格基调</h3>
                   {currentStyleData && <div className="text-[10px] text-primary font-serif font-bold bg-primary/10 border border-primary/20 px-2 py-0.5 rounded-full">当前：{currentStyleData.name}</div>}
                </div>
                <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 xl:grid-cols-5">
                  {STYLES.map(style => (
                    <button
                      type="button"
                      key={style.id}
                      onClick={() => setSelectedStyle(style.id)}
                      aria-pressed={selectedStyle === style.id}
                      aria-label={`选择${style.name}`}
                      className={cn(
                        "relative cursor-pointer rounded-xl border-2 flex flex-col items-center justify-center py-3 px-2 gap-2 text-center transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
                        selectedStyle === style.id 
                          ? "border-primary bg-primary/5 shadow-[0_6px_20px_rgba(158,36,27,0.18)] ring-1 ring-primary/30" 
                          : "border-gold/20 bg-paper/30 hover:bg-white hover:border-gold/50"
                      )}
                    >
                      {selectedStyle === style.id && (
                        <span className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-white text-[9px] shadow-xs">
                          <Check className="h-2.5 w-2.5" />
                        </span>
                      )}
                      <img src={style.img || '/zhuxianzhen.png'} alt="" className="h-12 w-12 rounded-full object-cover shadow-sm ring-2 ring-white border border-gold/30" />
                      <span className={cn("text-xs font-serif font-bold leading-snug", selectedStyle === style.id ? "text-primary" : "text-ink/75")}>
                        {style.name}
                      </span>
                    </button>
                  ))}
                </div>
                {currentStyleData && (
                  <div aria-live="polite" className="mt-3.5 rounded-xl border border-gold/35 bg-gradient-to-r from-[#FFFBF5] via-[#FFF9EE] to-white p-3.5 shadow-xs">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-serif text-xs font-bold text-primary flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-gold" />
                        {currentStyleData.name}
                      </span>
                      <span className="rounded-full bg-gold/15 px-2.5 py-0.5 text-[10px] font-serif font-bold text-[#8b6a30]">
                        风格先验已写入 Prompt
                      </span>
                    </div>
                    <p className="mt-1.5 text-[11px] leading-relaxed text-ink/70 font-sans">{currentStyleData.shortDescription}</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {currentStyleData.visualFeatures.slice(0, 3).map((feature) => (
                        <span key={feature} className="rounded-md border border-gold/30 bg-white/90 px-2 py-0.5 text-[10px] font-serif text-ink/70 shadow-xs">
                          {feature}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Generation Settings (笔墨干湿与载体) */}
              <div className="mb-6 rounded-xl border border-gold/30 bg-white/80 p-4 shadow-xs">
                <h3 className="chinese-plaque text-xs py-1 mb-3">系统参数调优</h3>
                <div className="bg-paper/40 border border-gold/25 rounded-xl p-4 space-y-4 shadow-inner">
                   <div>
                     <div className="flex justify-between text-xs mb-1.5 font-serif font-bold">
                       <span className="text-ink/80" title="调整传统文化视觉特征在生成提示中的约束程度。">风格先验约束强度</span>
                       <span className="text-primary font-mono">{styleStrength}%</span>
                     </div>
                     <input
                       type="range"
                       min="0"
                       max="100"
                       value={styleStrength}
                       onChange={(e) => setStyleStrength(parseInt(e.target.value))}
                       className="w-full accent-primary h-2 bg-black/8 rounded-full appearance-none outline-none cursor-pointer"
                     />
                     <div className="flex justify-between text-[10px] text-ink/45 mt-1 font-serif">
                       <span>轻度融入 · 现代意象</span>
                       <span>高纯度融入 · 典籍厚重</span>
                     </div>
                   </div>
                   
                   <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-gold/20">
                      <div>
                         <label className="block text-[11px] font-serif font-bold text-ink/70 mb-1.5">构图意境模式</label>
                         <select
                           value={composition}
                           onChange={(e) => setComposition(e.target.value)}
                           className="w-full p-2 bg-white border border-gold/35 rounded-lg shadow-xs text-xs font-serif text-ink focus:outline-none focus:border-primary"
                         >
                            <option value="portrait">竖向立轴 · 主体突显</option>
                            <option value="landscape">横向长卷 · 层次延展</option>
                            <option value="object">器物特写 · 留白写意</option>
                         </select>
                      </div>
                      <div>
                         <label className="block text-[11px] font-serif font-bold text-ink/70 mb-1.5">文创应用载体预设</label>
                         <select
                           value={outputType}
                           onChange={(e) => setOutputType(e.target.value)}
                           className="w-full p-2 bg-white border border-gold/35 rounded-lg shadow-xs text-xs font-serif text-ink focus:outline-none focus:border-primary"
                         >
                            <option value="poster">数字艺术海报</option>
                            <option value="postcard">文旅典藏明信片</option>
                            <option value="bag">国潮帆布袋</option>
                            <option value="bookmark">金石文创书签</option>
                            <option value="coaster">青花陶瓷杯垫</option>
                            <option value="social">手机壁纸与日签</option>
                            <option value="screen">环幕数字展陈屏</option>
                            <option value="ticket">景区纪念门票</option>
                         </select>
                      </div>
                   </div>
                </div>
              </div>
            </div>

            {/* Gen Action */}
            <div className="p-4 border-t border-gold/30 bg-[#FAF4E8]">
              <details className="mb-3 rounded-xl border border-gold/30 bg-white/80 p-3 text-xs text-ink/75 font-serif shadow-xs">
                <summary className="cursor-pointer font-bold text-primary flex items-center justify-between">
                  <span>本次请求参数明细</span>
                  <span className="text-[10px] text-ink/40 font-mono">展开核验</span>
                </summary>
                <div className="mt-2.5 grid grid-cols-2 gap-2 text-[11px] pt-2 border-t border-gold/20 font-sans">
                  <div className="col-span-2 truncate" title={prompt}>主题：{prompt || '未填写'}</div>
                  {subjectLock.trim() && <div className="col-span-2 truncate" title={subjectLock}>主体约束：{subjectLock}</div>}
                  <div>风格：{currentStyleData?.name || selectedStyle}</div>
                  <div>约束强度：{styleStrength}%</div>
                  <div>推理路径：{uploadedImageBase64 ? '参考图图生图' : '文生图'}</div>
                  <div>输出载体：{outputType}</div>
                  <div className="col-span-2 truncate" title={negativePrompt || '未设置'}>负向约束：{negativePrompt || '无'}</div>
                </div>
              </details>

              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="w-full py-4 btn-chinese disabled:opacity-90 disabled:cursor-not-allowed group relative overflow-hidden rounded-xl shadow-[0_8px_24px_rgba(158,36,27,0.25)] hover:shadow-[0_12px_32px_rgba(158,36,27,0.35)] transition-all"
              >
                {isGenerating && (
                  <motion.div
                    className="absolute inset-0 bg-gradient-to-r from-transparent via-gold/30 to-transparent pointer-events-none"
                    animate={{ x: ['-100%', '100%'] }}
                    transition={{ repeat: Infinity, duration: 1.8, ease: "linear" }}
                  />
                )}
                <div className="relative flex items-center justify-center gap-2 text-white font-serif font-bold text-base z-10 tracking-wider">
                  {isGenerating ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin text-gold" />
                      <span>正在丹青运笔 · 笔墨生辉中...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5 text-gold group-hover:rotate-12 transition-transform" />
                      <span>笔墨生辉 · 开始智能创作</span>
                    </>
                  )}
                </div>
              </button>
            </div>
         </div>

         {/* Right Result Area (展陈画境) */}
         <div className="lg:w-[50%] bg-[#FAF4E8] flex flex-col relative z-0">
           {!hasResult ? (
             <div className="flex-1 flex flex-col items-center justify-center p-8 sm:p-12 relative">
                <OrientalInkWaiting
                  isGenerating={isGenerating}
                  hasResult={hasResult}
                  imageLoadState={imageLoadState}
                  connectionNotice={connectionNotice}
                  errorMessage={null}
                  onRetry={handleGenerate}
                  selectedStyleName={currentStyleData?.name || selectedStyle}
                />
                
                {historyImages.length > 0 && (
                  <div className="absolute bottom-6 left-6 right-6">
                     <div className="text-xs text-ink/50 mb-2 flex items-center gap-2 font-serif">
                        <div className="h-px bg-gold/30 flex-1"></div>
                        <span className="tracking-wider">最近生成记录 · 浏览器本地沙箱</span>
                        <div className="h-px bg-gold/30 flex-1"></div>
                     </div>
                     <div className="flex gap-3 justify-center">
                        {historyImages.map((img, i) => (
                           <div key={i} className="w-12 h-16 rounded-lg shadow-xs border-2 border-white p-0.5 bg-paper overflow-hidden opacity-70 hover:opacity-100 cursor-pointer transition-all hover:scale-105">
                              <img src={img} className="w-full h-full object-cover" alt="" />
                           </div>
                        ))}
                     </div>
                  </div>
                )}
             </div>
           ) : (
             <div className="flex-1 overflow-y-auto scrollbar-thin flex flex-col">
                 <div className="flex items-center justify-between border-b border-gold/30 bg-white/75 px-6 py-3 text-xs text-ink/70 backdrop-blur-sm">
                   <div className="flex items-center gap-2 font-serif">
                     <span className="h-2 w-2 rounded-full bg-emerald-600 animate-pulse" />
                     <span className="font-bold text-ink">{getModeLabel(mode)}完成</span>
                     <span className="text-ink/40">|</span>
                     <span>Qwen Image 3.0</span>
                   </div>
                   <span className="chinese-seal text-[9px]">落款成图</span>
                 </div>

                 <div className="flex-1 overflow-y-auto scrollbar-thin p-5 sm:p-7 lg:p-8">
                  <div className="mx-auto flex w-full max-w-4xl flex-col items-center">
                    <div className="mb-5 flex w-full flex-wrap items-center justify-between gap-3 rounded-xl border border-gold/35 bg-white/90 px-4 py-3 text-xs text-ink/75 shadow-xs">
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 font-serif">
                        <span className="inline-flex items-center gap-1.5 font-bold text-ink">
                          <Sparkles className="w-3.5 h-3.5 text-gold" />
                          AI 生成新作品
                        </span>
                        <span>{getModeLabel(mode)}</span>
                        <span>引擎：Qwen Image 3.0</span>
                      </div>
                      {resultData?.referenceImageUsed === true && (
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1 font-serif font-bold text-emerald-800 text-[11px]">
                          ✓ 参考图已参与推理
                        </span>
                      )}
                      {resultPayload?.uploadedImage && resultData?.referenceImageUsed !== true && (
                        <span className="rounded-full bg-amber-50 border border-amber-200 px-3 py-1 text-amber-800 text-[11px]">
                          参考图已提交，服务未确认
                        </span>
                      )}
                    </div>
                    {connectionNotice && <div className="mb-4 w-full rounded-xl border border-primary/20 bg-primary/5 px-4 py-2.5 text-xs text-primary">{connectionNotice}</div>}
                    {resultData?.error && <div className="mb-4 w-full rounded-xl border border-primary/20 bg-primary/5 px-4 py-2.5 text-xs text-primary">{resultData.error}</div>}

                    {/* 装裱展陈画框 */}
                    <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} className="w-full max-w-[520px]">
                      <div className="group relative mx-auto aspect-[3/4] w-full overflow-hidden rounded-2xl border-[6px] border-white bg-[#eee7dc] shadow-[0_20px_50px_rgba(70,42,30,0.18)]">
                        <img
                          src={resultImage}
                          alt="Qwen Image 3.0生成作品"
                          className="h-full w-full object-contain"
                          style={{ transform: `rotate(${rotation}deg) scale(${scale})` }}
                          onLoad={() => { if (resultImage) { setImageLoadState('loaded'); setImageLoadError(null); } }}
                          onError={() => { setImageLoadState('error'); setImageLoadError('生成图片暂时无法加载，请确认后端图片服务仍在运行。'); }}
                        />
                        {imageLoadState === 'loading' && (
                          <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/80 font-serif text-sm text-primary">
                            <RefreshCw className="mr-2 h-4 w-4 animate-spin text-gold" />作品装裱中…
                          </div>
                        )}
                        {imageLoadState === 'error' && (
                          <div className="absolute inset-x-3 bottom-3 z-20 rounded-xl border border-primary/25 bg-white/95 p-3 text-xs text-primary shadow-lg">
                            {imageLoadError || '图片加载失败'}
                          </div>
                        )}
                        <div className="pointer-events-none absolute inset-2 rounded-xl border border-gold/40" />
                        <div className="absolute right-3 top-3 z-20 flex flex-col gap-1.5 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                          {[
                            { icon: RotateCw, title: '旋转', act: handleRotate },
                            { icon: Crop, title: '裁剪预览', act: () => setIsCropping(true) },
                            { icon: ZoomIn, title: '放大', act: handleZoomIn },
                            { icon: ZoomOut, title: '缩小', act: handleZoomOut },
                          ].map((tool) => (
                            <button
                              key={tool.title}
                              type="button"
                              onClick={tool.act}
                              title={tool.title}
                              className="flex h-8 w-8 items-center justify-center rounded-lg border border-gold/40 bg-white/95 text-primary shadow-xs transition hover:bg-primary hover:text-white"
                            >
                              <tool.icon className="h-4 w-4" />
                            </button>
                          ))}
                        </div>
                        {isCropping && (
                          <div className="absolute inset-0 z-30 flex flex-col bg-black/60">
                            <div className="relative flex-1 p-6">
                              <div className="relative h-full w-full border border-dashed border-white shadow-[0_0_0_99rem_rgba(0,0,0,0.4)]" />
                            </div>
                            <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 gap-2">
                              <button type="button" onClick={() => setIsCropping(false)} className="rounded-lg bg-white px-3 py-1.5 text-xs font-serif shadow">取消</button>
                              <button type="button" onClick={() => setIsCropping(false)} className="rounded-lg bg-primary px-3 py-1.5 text-xs font-serif text-white shadow">完成</button>
                            </div>
                          </div>
                        )}
                      </div>
                    </motion.div>

                    {/* 行动按钮群 */}
                    <div className="mt-5 grid w-full max-w-[520px] grid-cols-1 gap-3 sm:grid-cols-2">
                      <button
                        type="button"
                        onClick={() => void handleDownloadResult()}
                        disabled={isDownloadingResult}
                        className="inline-flex items-center justify-center gap-2 rounded-xl border border-gold/40 bg-white px-4 py-3 text-xs sm:text-sm font-serif font-bold text-primary shadow-xs transition hover:bg-primary hover:text-white disabled:cursor-wait disabled:opacity-70"
                      >
                        {isDownloadingResult ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                        {isDownloadingResult ? '下载中…' : '下载高清原图'}
                      </button>
                      <button
                        type="button"
                        onClick={() => navigate('/products')}
                        className="inline-flex items-center justify-center gap-2 rounded-xl btn-chinese px-4 py-3 text-xs sm:text-sm font-serif font-bold shadow-xs hover:shadow-md transition-all"
                      >
                        <span>前往文创工坊预览</span>
                        <ArrowRight className="h-4 w-4" />
                      </button>
                    </div>
                    {downloadStatus && <p role="status" aria-live="polite" className="mt-2 w-full max-w-[520px] text-center text-xs font-serif text-ink/70">{downloadStatus}</p>}

                    {savedCase && (
                      <div
                        role="status"
                        aria-live="polite"
                        className="mt-3 flex w-full max-w-[520px] flex-wrap items-center justify-center gap-x-3 gap-y-1 rounded-lg border border-gold/45 bg-white/75 px-3 py-2 text-xs text-ink/70"
                      >
                        <span className="inline-flex items-center gap-1.5 font-medium text-ink/75">
                          <Check className="h-3.5 w-3.5 text-primary" />
                          已自动存入作品展厅
                        </span>
                        <button
                          type="button"
                          onClick={() => navigate(`/gallery#case-${savedCase.caseId}`)}
                          className="underline decoration-dotted underline-offset-4 transition hover:text-primary"
                        >
                          查看《{savedCase.artworkTitle}》
                        </button>
                        <span className="text-ink/40">参考图 · 成图 · 文化卡已一并保存</span>
                      </div>
                    )}
                    {autoSaveError && (
                      <p role="status" className="mt-2 w-full max-w-[520px] text-center text-xs text-ink/50">
                        图片已生成，但自动保存未完成（{autoSaveError}）。可在展厅刷新后确认。
                      </p>
                    )}

                    <div className="mt-7 w-full">
                      {resultPayload && resultImage && <CultureCard imageUrl={resultImage} theme={resultPayload.theme} styleId={resultPayload.style} styleName={resultStyleData.name} visualFeatures={resultData?.visionAnalysis?.visual_features || resultStyleData.visualFeatures} cultureSummary={resultCultureSummary} recommendedScenes={resultData?.visionAnalysis?.recommended_scenes || resultStyleData.recommendedScenes} generatedAt={resultGeneratedAt} analysis={resultData?.visionAnalysis || null} analysisSource={resultData?.analysisSource || 'template_fallback'} />}
                    </div>

                    <details className="mt-5 w-full overflow-hidden rounded-xl border border-primary/10 bg-white">
                      <summary className="cursor-pointer list-none px-5 py-4 text-sm font-semibold text-ink/75"><span className="flex items-center justify-between gap-3"><span>查看生成详情</span><span className="text-xs font-normal text-ink/45">模型、模式与参数</span></span></summary>
                      <div className="grid gap-2 border-t border-black/5 p-4 text-xs sm:grid-cols-2">
                        <div className="rounded-lg bg-paper/70 px-3 py-2"><span className="text-ink/45">模型</span><span className="ml-2 font-medium text-ink/75">{resultData?.model || 'Qwen Image 3.0'}</span></div>
                        <div className="rounded-lg bg-paper/70 px-3 py-2"><span className="text-ink/45">生成模式</span><span className="ml-2 font-medium text-ink/75">{getModeLabel(mode)}</span></div>
                        <div className="rounded-lg bg-paper/70 px-3 py-2"><span className="text-ink/45">AI服务</span><span className="ml-2 font-medium text-ink/75">阿里云百炼</span></div>
                        <div className="rounded-lg bg-paper/70 px-3 py-2"><span className="text-ink/45">图像参考</span><span className="ml-2 font-medium text-ink/75">{resultData?.referenceImageUsed === true ? '用户参考图已参与' : '未使用'}</span></div>
                        <div className="rounded-lg bg-paper/70 px-3 py-2"><span className="text-ink/45">风格影响强度</span><span className="ml-2 font-medium text-ink/75">{Math.round((resultPayload?.styleStrength || 0) * 100)}% · Prompt约束</span></div>
                        <div className="rounded-lg bg-paper/70 px-3 py-2"><span className="text-ink/45">构图模式</span><span className="ml-2 font-medium text-ink/75">{resultPayload?.compositionMode || '—'}</span></div>
                        <div className="rounded-lg bg-paper/70 px-3 py-2 sm:col-span-2"><span className="text-ink/45">生成时间</span><span className="ml-2 font-medium text-ink/75">{new Date(resultGeneratedAt).toLocaleString('zh-CN')}</span></div>
                      </div>
                      {enhancedPrompt && <details className="border-t border-black/5 px-4 py-3"><summary className="cursor-pointer text-xs font-medium text-ink/55">查看本次生成 Prompt</summary><pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-paper p-3 text-[11px] leading-relaxed text-ink/65">{enhancedPrompt}</pre></details>}
                    </details>
                  </div>
                </div>
              </div>
           )}
         </div>
      </div>
    </div>
  );
}
