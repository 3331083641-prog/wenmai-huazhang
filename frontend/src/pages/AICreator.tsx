import React, { useState, useRef, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { cn } from '../lib/utils';
import { ImagePlus, Download, ArrowRight, Wand2, RefreshCw, RotateCw, Crop, ZoomIn, ZoomOut, Check } from 'lucide-react';
import { STYLES } from '../data/styleLibrary';
import { BackendHealth, buildLocalCultureCard, checkBackendHealth, generateImage, GeneratePayload, GenerateResponse } from '../services/generationService';
import CultureCard from '../components/creator/CultureCard';

const GENERATION_STEPS = [
  "正在整理主题与参考图...",
  "正在整理风格生成提示词...",
  "正在调用生成引擎...",
  "正在保存生成作品...",
  "正在整理文化风格说明...",
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
  
  const [prompt, setPrompt] = useState('一名大学生站在开封古城门前，微笑着挥手，身后是宋代城楼与祥云纹样...');
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
              const restoredPayload: GeneratePayload = {
                theme: parsed.theme || '传统文化主题创作',
                style: parsed.style || 'zhuxianzhen',
                styleName: parsed.styleName || '',
                outputType: parsed.outputType || 'poster',
                styleStrength: typeof parsed.styleStrength === 'number' ? parsed.styleStrength : 0.65,
                compositionMode: parsed.compositionMode || 'portrait',
                negativePrompt: parsed.negativePrompt || null,
                uploadedImage: null,
                generationProvider: 'dashscope_qwen_image',
              };
              // The form reflects the same request as the restored result so
              // users do not see one style selected while another style is shown.
              setPrompt(restoredPayload.theme);
              setNegativePrompt(restoredPayload.negativePrompt || '');
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
    checkBackendHealth()
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
    };
    localStorage.setItem('wenmai_latest_result', JSON.stringify(resultToSave));
  };

  const handleGenerate = async () => {
    if (generationLockRef.current) return;
    generationLockRef.current = true;
    setIsGenerating(true);
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
    
    // Animate steps
    let currentStep = 0;
    let stepInterval: number | null = window.setInterval(() => {
      currentStep++;
      if (currentStep < GENERATION_STEPS.length - 1) {
        setGenerationStep(currentStep);
      }
    }, 1500);

    try {
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
      anchor.download = `wenmai_generated_${styleSlug}_${filenameTimestamp()}.png`;
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
    <div className="flex flex-col lg:flex-row min-h-[calc(100vh-64px)] w-full">
      {/* Container to enforce exact max-w-7xl constraint overall but stretching inside */}
      <div className="flex-1 flex flex-col lg:flex-row w-full max-w-7xl mx-auto border-x border-primary/5 shadow-2xl bg-paper">
         
         {/* Left Workspace */}
         <div className="lg:w-[50%] flex flex-col border-r border-primary/10 bg-white">
            <div className="h-20 bg-rice-paper relative overflow-hidden flex items-center px-6 border-b border-primary/10">
               <div className="absolute inset-0 bg-[url('/songhua.png')] bg-cover bg-center opacity-10 filter sepia"></div>
               <h2 className="text-xl font-serif text-primary relative z-10 flex items-center gap-2">
                 <Wand2 className="w-5 h-5 text-gold" /> 
                 国风智能创作工作台
               </h2>
               <div className="ml-auto text-xs text-ink/70 font-mono text-right relative z-10">
                 {backendStatus === 'connected' ? (
                   <div className="text-green-700">
                     后端已连接
                     <div className="text-[10px] text-ink/50">AI模型：{backendHealth?.model || 'Qwen Image 3.0'} · {backendHealth?.providers?.dashscope_qwen_image?.available ? '可用' : '状态待确认'}</div>
                   </div>
                 ) : backendStatus === 'checking' ? (
                   <div className="text-ink/50">正在检查后端...</div>
                 ) : (
                   <div className="text-primary">
                     后端未连接
                     <div className="text-[10px] text-ink/60">启动：D:\wenmai-huazhang\scripts\start_backend.bat</div>
                   </div>
                 )}
               </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
              {/* Prompt Area */}
              <div className="mb-6">
                <div className="flex justify-between items-end mb-2">
                   <h3 className="chinese-plaque text-sm">输入创作主题</h3>
                   <div className="text-[10px] text-ink/40">支持中英文</div>
                </div>
                <textarea
                  className="w-full h-24 p-3 bg-paper/50 border border-primary/20 rounded focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all text-sm shadow-inner text-ink/90 resize-none hover:border-primary/40"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="描述你想生成的场景、人物或故事..."
                />
                <p className="mt-2 text-[11px] text-ink/45">主题文本将与所选文化风格共同进入本次生成提示。</p>
                
                <div className="mt-4">
                   <div className="flex justify-between items-end mb-2">
                      <h3 className="text-xs font-serif text-ink/80 flex items-center gap-2">负向提示词 (排除元素) <span className="text-[10px] text-primary/60 font-sans border border-primary/20 px-1 rounded">可选参数</span></h3>
                   </div>
                   <input
                     className="w-full p-2.5 bg-paper/50 border border-primary/20 rounded focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all text-sm shadow-inner text-ink/90 hover:border-primary/40"
                     value={negativePrompt}
                     onChange={(e) => setNegativePrompt(e.target.value)}
                     placeholder="例如：现代建筑、现代服饰、文字、水印..."
                   />
                </div>
              </div>

              {/* Upload Image Area */}
              <div className="mb-6">
                <div className="flex justify-between items-end mb-2">
                   <h3 className="chinese-plaque text-sm flex items-center gap-2">上传参考图 <span className="text-[10px] text-primary/60 font-sans border border-primary/20 px-1 rounded">可选参数</span></h3>
                </div>
                <div 
                  className={cn(
                    "border border-dashed rounded-lg p-5 flex flex-col items-center justify-center text-center cursor-pointer transition-all relative overflow-hidden group",
                    isDragActive ? "border-primary bg-primary/5" : "border-primary/30 bg-paper/30 hover:bg-white hover:border-primary"
                  )}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" accept="image/png, image/jpeg, image/jpg" />
                  
                  {isUploading ? (
                     <div className="flex items-center gap-2 text-primary">
                        <RefreshCw className="w-5 h-5 animate-spin" />
                        <span className="text-sm">读取图片中...</span>
                     </div>
                  ) : previewUrl ? (
                    <div className="relative w-full flex items-center justify-center gap-4">
                      <div className="w-20 h-20 rounded shadow-inner overflow-hidden border border-primary/20 relative group-hover:shadow-md transition-shadow">
                        <img src={previewUrl} alt="ref" className="w-full h-full object-cover" />
                      </div>
                      <div className="text-left flex-1">
                         <div className="text-sm font-medium text-ink">✓ 参考图已加入本次生成</div>
                         <div className="text-xs text-ink/50 mt-1 mb-2">参考图将发送至 Qwen Image 3.0，为主体、构图或视觉内容提供参考。</div>
                         <div className="text-xs text-primary underline underline-offset-2">点击更换</div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center">
                      <ImagePlus className="w-6 h-6 text-primary/40 mb-2 group-hover:text-primary transition-colors" />
                      <p className="text-sm font-medium text-ink/70">拖拽或点击上传</p>
                      <p className="text-[10px] text-ink/40 mt-1">支持 PNG/JPG，≤10 MB；参考图将参与本次 Qwen Image 3.0 生成</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Style Selection */}
              <div className="mb-6">
                <div className="flex justify-between items-end mb-2">
                   <h3 className="chinese-plaque text-sm">选择核心风格基调</h3>
                   {currentStyleData && <div className="text-[10px] text-gold font-medium bg-gold/10 px-1.5 rounded">正在使用: {currentStyleData.name}</div>}
                </div>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
                  {STYLES.map(style => (
                    <button
                      type="button"
                      key={style.id}
                      onClick={() => setSelectedStyle(style.id)}
                      aria-pressed={selectedStyle === style.id}
                      aria-label={`选择${style.name}`}
                      className={cn(
                        "relative cursor-pointer rounded-xl border-2 flex flex-col items-center justify-center py-3 px-2 gap-2 text-center transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2",
                        selectedStyle === style.id 
                          ? "border-primary bg-white shadow-[0_5px_18px_rgba(158,36,27,0.14)] ring-1 ring-primary/20" 
                          : "border-black/5 bg-paper/50 hover:bg-white hover:border-primary/40"
                      )}
                    >
                      {selectedStyle === style.id && <span className="absolute right-1.5 top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-white"><Check className="h-3 w-3" /></span>}
                      <img src={style.img || '/zhuxianzhen.png'} alt="" className="h-12 w-12 rounded-full object-cover shadow-sm ring-2 ring-white" />
                      <span className={cn("text-xs font-semibold leading-snug", selectedStyle === style.id ? "text-primary" : "text-ink/65")}>
                        {style.name}
                      </span>
                    </button>
                  ))}
                </div>
                {currentStyleData && (
                  <div aria-live="polite" className="mt-3 rounded-xl border border-gold/30 bg-gradient-to-r from-[#fff9ef] to-white px-4 py-3 shadow-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-serif text-sm font-semibold text-primary">{currentStyleData.name}</span>
                      <span className="rounded-full bg-gold/10 px-2.5 py-1 text-[10px] font-medium text-[#8b6a30]">风格特征已写入生成提示</span>
                    </div>
                    <p className="mt-1.5 text-xs leading-relaxed text-ink/65">{currentStyleData.shortDescription}</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {currentStyleData.visualFeatures.slice(0, 3).map((feature) => <span key={feature} className="rounded-full border border-primary/10 bg-white/80 px-2 py-1 text-[10px] text-ink/65">{feature}</span>)}
                    </div>
                  </div>
                )}
              </div>

              {/* Generation Settings */}
              <div className="mb-6">
                <h3 className="chinese-plaque text-sm mb-2">系统参数</h3>
                <div className="bg-rice-paper border border-primary/10 rounded-lg p-4 space-y-4 shadow-inner">
                   <div>
                     <div className="flex justify-between text-xs mb-1.5 font-medium"><span className="text-ink/80" title="调整传统文化视觉特征在生成提示中的约束程度。">风格影响强度</span><span className="text-primary">{styleStrength}%</span></div>
                     <input type="range" min="0" max="100" value={styleStrength} onChange={(e) => setStyleStrength(parseInt(e.target.value))} className="w-full accent-primary h-1.5 bg-black/5 rounded-full appearance-none outline-none" />
                     <div className="flex justify-between text-[10px] text-ink/40 mt-1"><span>轻度融入</span><span>强化风格</span></div>
                     <p className="mt-1 text-[10px] text-ink/45">调整传统文化视觉特征在生成提示中的约束程度。</p>
                   </div>
                   
                   <div className="flex gap-4">
                      <div className="flex-1">
                         <label className="block text-[10px] text-ink/60 mb-1">构图提示模式</label>
                         <select value={composition} onChange={(e) => setComposition(e.target.value)} className="w-full p-2 bg-white border border-primary/20 rounded shadow-sm text-xs focus:outline-none focus:border-primary">
                            <option value="portrait">竖向主体布局</option>
                            <option value="landscape">横向层次布局</option>
                            <option value="object">主体居中留白</option>
                         </select>
                         <p className="text-[10px] text-ink/45 mt-1">构图描述写入提示词；输出尺寸由后端服务配置决定。</p>
                      </div>
                      <div className="flex-1">
                         <label className="block text-[10px] text-ink/60 mb-1">应用场景提示</label>
                         <select value={outputType} onChange={(e) => setOutputType(e.target.value)} className="w-full p-2 bg-white border border-primary/20 rounded shadow-sm text-xs focus:outline-none focus:border-primary">
                            <option value="poster">数字艺术海报</option>
                            <option value="postcard">文旅明信片</option>
                            <option value="bag">文创帆布袋</option>
                            <option value="bookmark">文创书签</option>
                            <option value="coaster">陶瓷杯垫</option>
                            <option value="social">手机分享图</option>
                            <option value="screen">数字展陈屏</option>
                            <option value="ticket">景区纪念票</option>
                         </select>
                      </div>
                   </div>
                </div>
              </div>
            </div>

            {/* Gen Action */}
            <div className="p-4 border-t border-primary/10 bg-white">
              <details className="mb-3 rounded border border-primary/10 bg-rice-paper/60 p-3 text-xs text-ink/70">
                <summary className="cursor-pointer font-medium text-primary">本次请求参数预览</summary>
                <div className="mt-2 grid grid-cols-2 gap-2">
                  <div className="col-span-2 truncate" title={prompt}>当前主题：{prompt || '未填写'}</div>
                  <div>当前风格：{currentStyleData?.name || selectedStyle}</div>
                   <div>风格影响强度：{styleStrength}%（通过提示词约束表达）</div>
                   <div>生成路径：{uploadedImageBase64 ? 'Qwen Image 3.0 参考图创作' : 'Qwen Image 3.0 文本创作'}</div>
                  <div>输出类型：{outputType}</div>
                  <div>构图提示：{composition}</div>
                  <div className="col-span-2 truncate" title={negativePrompt || '未设置'}>负面提示词：{negativePrompt || '未设置'}</div>
                </div>
              </details>
              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="w-full py-3.5 btn-chinese disabled:opacity-80 disabled:cursor-not-allowed group relative overflow-hidden"
              >
                {isGenerating && (
                  <motion.div className="absolute inset-y-0 left-0 bg-gold/40" initial={{ width: "0%" }} animate={{ width: `${(generationStep / (GENERATION_STEPS.length - 1)) * 100}%` }} transition={{ ease: "linear" }} />
                )}
                <div className="relative flex items-center justify-center gap-2 text-white font-medium text-base z-10">
                  {isGenerating ? (
                    <><RefreshCw className="w-4 h-4 animate-spin text-gold" /><span>{GENERATION_STEPS[generationStep]}</span></>
                  ) : (
                    <><Wand2 className="w-4 h-4 text-gold group-hover:scale-110 transition-transform" /><span>AI 生成视觉作品</span></>
                  )}
                </div>
              </button>
            </div>
         </div>

         {/* Right Result Area */}
         <div className="lg:w-[50%] bg-rice-paper flex flex-col relative z-0">
           {!hasResult ? (
             <div className="flex-1 flex flex-col items-center justify-center p-10 relative">
                <div className="w-full max-w-sm aspect-[3/4] border-2 border-dashed border-primary/20 rounded-xl bg-white/40 flex flex-col items-center justify-center p-8 text-center relative overflow-hidden group">
                   <div className="absolute inset-0 bg-gradient-to-t from-primary/5 to-transparent pointer-events-none"></div>
                   <div className="w-16 h-16 rounded-full bg-white shadow-sm border border-black/5 flex items-center justify-center mb-4 text-primary/30 group-hover:scale-105 group-hover:text-primary/50 transition-all">
                      <ImagePlus className="w-8 h-8" />
                   </div>
                   <h3 className="font-serif text-lg text-ink/70 mb-2">{connectionNotice ? '生成未完成' : isGenerating ? '正在生成视觉作品' : '作品暂未生成'}</h3>
                   <p className={cn("text-xs leading-relaxed max-w-[220px]", connectionNotice ? "text-primary" : "text-ink/50")}>
                     {connectionNotice || (isGenerating ? GENERATION_STEPS[generationStep] : '填写主题并设置创作参数后，提交至当前图像生成服务。')}
                   </p>
                </div>
                
                {historyImages.length > 0 && (
                  <div className="absolute bottom-6 left-6 right-6">
                     <div className="text-xs text-ink/40 mb-2 flex items-center gap-2">
                        <div className="h-px bg-black/10 flex-1"></div>
                        <span className="uppercase tracking-wider">最近生成预览 · 当前浏览器</span>
                     </div>
                     <div className="flex gap-3">
                        {historyImages.map((img, i) => (
                           <div key={i} className="w-12 h-16 rounded shadow-sm border border-white p-0.5 bg-paper overflow-hidden opacity-60 hover:opacity-100 cursor-pointer transition-opacity">
                              <img src={img} className="w-full h-full object-cover" alt="" />
                           </div>
                        ))}
                     </div>
                  </div>
                )}
             </div>
           ) : (
             <div className="flex-1 overflow-y-auto scrollbar-thin flex flex-col">
                 <div className="flex items-center gap-2 border-b border-black/5 bg-white/60 px-6 py-3 text-xs text-ink/55 backdrop-blur">
                   <span className="h-1.5 w-1.5 rounded-full bg-green-600" />{getModeLabel(mode)}完成 · Qwen Image 3.0
                 </div>

                                <div className="flex-1 overflow-y-auto scrollbar-thin p-5 sm:p-7 lg:p-8">
                  <div className="mx-auto flex w-full max-w-4xl flex-col items-center">
                    <div className="mb-5 flex w-full flex-wrap items-center justify-between gap-3 rounded-xl border border-primary/10 bg-white/80 px-4 py-3 text-xs text-ink/65">
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                        <span className="inline-flex items-center gap-2 font-medium text-ink"><span className="h-2 w-2 rounded-full bg-green-600" />AI生成作品</span>
                        <span>{getModeLabel(mode)}</span><span>生成引擎：Qwen Image 3.0</span>
                      </div>
                      {resultData?.referenceImageUsed === true && <span className="inline-flex items-center gap-1.5 rounded-full bg-green-50 px-3 py-1.5 font-medium text-green-800">✓ 用户参考图已参与模型推理</span>}
                      {resultPayload?.uploadedImage && resultData?.referenceImageUsed !== true && <span className="rounded-full bg-amber-50 px-3 py-1.5 text-amber-800">参考图已提交，服务未确认参与</span>}
                    </div>
                    {connectionNotice && <div className="mb-4 w-full rounded-lg border border-primary/15 bg-primary/5 px-4 py-2 text-sm text-primary">{connectionNotice}</div>}
                    {resultData?.error && <div className="mb-4 w-full rounded-lg border border-primary/15 bg-primary/5 px-4 py-2 text-sm text-primary">{resultData.error}</div>}
                    {resultData?.realProviderError && <div className="mb-4 w-full rounded-lg border border-primary/15 bg-primary/5 px-4 py-2 text-sm text-primary">生成服务错误：{resultData.realProviderError}</div>}

                    <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} className="w-full max-w-[520px]">
                      <div className="group relative mx-auto aspect-[3/4] w-full overflow-hidden rounded-xl border-[6px] border-white bg-[#eee7dc] shadow-[0_16px_44px_rgba(70,42,30,0.15)]">
                        <img src={resultImage} alt="Qwen Image 3.0生成作品" className="h-full w-full object-contain" style={{ transform: `rotate(${rotation}deg) scale(${scale})` }} onLoad={() => { if (resultImage) { setImageLoadState('loaded'); setImageLoadError(null); } }} onError={() => { setImageLoadState('error'); setImageLoadError('生成图片暂时无法加载，请确认后端图片服务仍在运行。'); }} />
                        {imageLoadState === 'loading' && <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/75 text-sm text-ink/65"><RefreshCw className="mr-2 h-4 w-4 animate-spin" />作品加载中…</div>}
                        {imageLoadState === 'error' && <div className="absolute inset-x-3 bottom-3 z-20 rounded-lg border border-primary/20 bg-white/95 p-3 text-xs text-primary">{imageLoadError || '图片加载失败'}</div>}
                        <div className="pointer-events-none absolute inset-2 rounded-lg border border-gold/40" />
                        <div className="absolute right-3 top-3 z-20 flex flex-col gap-1.5 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                          {[
                            { icon: RotateCw, title: '旋转', act: handleRotate },
                            { icon: Crop, title: '裁剪预览', act: () => setIsCropping(true) },
                            { icon: ZoomIn, title: '放大', act: handleZoomIn },
                            { icon: ZoomOut, title: '缩小', act: handleZoomOut },
                          ].map((tool) => <button key={tool.title} type="button" onClick={tool.act} title={tool.title} className="flex h-8 w-8 items-center justify-center rounded-lg border border-black/5 bg-white/95 text-primary shadow-sm transition hover:bg-primary hover:text-white"><tool.icon className="h-4 w-4" /></button>)}
                        </div>
                        {isCropping && <div className="absolute inset-0 z-30 flex flex-col bg-black/60"><div className="relative flex-1 p-6"><div className="relative h-full w-full border border-dashed border-white shadow-[0_0_0_99rem_rgba(0,0,0,0.4)]" /></div><div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 gap-2"><button type="button" onClick={() => setIsCropping(false)} className="rounded bg-white px-3 py-2 text-xs shadow">取消</button><button type="button" onClick={() => setIsCropping(false)} className="rounded bg-primary px-3 py-2 text-xs text-white shadow">完成</button></div></div>}
                      </div>
                    </motion.div>

                    <div className="mt-4 grid w-full max-w-[520px] grid-cols-1 gap-3 sm:grid-cols-2">
                      <button type="button" onClick={() => void handleDownloadResult()} disabled={isDownloadingResult} className="inline-flex items-center justify-center gap-2 rounded-lg border border-primary/20 bg-white px-4 py-3 text-sm font-semibold text-primary shadow-sm transition hover:bg-primary hover:text-white disabled:cursor-wait disabled:opacity-70">{isDownloadingResult ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}{isDownloadingResult ? '下载中…' : '下载生成原图'}</button>
                      <button type="button" onClick={() => navigate('/products')} className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-primary/90"><ArrowRight className="h-4 w-4" />前往文创预览</button>
                    </div>
                    {downloadStatus && <p role="status" aria-live="polite" className="mt-2 w-full max-w-[520px] text-center text-xs text-ink/60">{downloadStatus}</p>}

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
                      <details className="border-t border-black/5 px-4 py-3"><summary className="cursor-pointer text-xs font-medium text-ink/55">开发者信息</summary><div className="mt-3 grid gap-2 text-xs text-ink/55 sm:grid-cols-2"><div>Provider：{resultData?.provider || 'dashscope_qwen_image'}</div><div>Engine：{resultData?.engine || '—'}</div><div>Request ID：{requestId || '—'}</div><div>用户输入图像数量：{resultData?.referenceImageUsed ? 1 : 0}</div></div></details>
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
