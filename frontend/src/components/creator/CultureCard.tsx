import { useMemo, useState } from 'react';
import { Download, LoaderCircle } from 'lucide-react';
import { STYLES, cultureCardThemes } from '../../data/styleLibrary';
import type { VisionAnalysis } from '../../services/generationService';

type CultureCardLayout = 'horizontal' | 'editorial' | 'stacked';

export interface CultureCardProps {
  imageUrl: string;
  theme: string;
  styleId: string;
  styleName: string;
  visualFeatures: string[];
  cultureSummary: string;
  recommendedScenes: string[];
  generatedAt: string;
  analysis?: VisionAnalysis | null;
  analysisSource?: string;
}

const stableHash = (value: string) => {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
};

const readableTheme = (value: string) => value.replace(/\s+/g, ' ').trim().slice(0, 34) || '传统文化主题创作';

const getFilenameTimestamp = (date: Date) => {
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}_${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`;
};

const roundedRect = (ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, radius: number) => {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, radius);
};

const containImage = (ctx: CanvasRenderingContext2D, image: ImageBitmap, x: number, y: number, w: number, h: number, background: string) => {
  ctx.fillStyle = background;
  ctx.fillRect(x, y, w, h);
  const scale = Math.min(w / image.width, h / image.height);
  const drawWidth = image.width * scale;
  const drawHeight = image.height * scale;
  ctx.drawImage(image, x + (w - drawWidth) / 2, y + (h - drawHeight) / 2, drawWidth, drawHeight);
};

const wrapCanvasText = (ctx: CanvasRenderingContext2D, text: string, x: number, y: number, maxWidth: number, lineHeight: number, maxLines: number) => {
  let line = '';
  let lineCount = 0;
  for (const char of text) {
    const nextLine = line + char;
    if (ctx.measureText(nextLine).width > maxWidth && line) {
      ctx.fillText(line, x, y + lineCount * lineHeight);
      line = char;
      lineCount += 1;
      if (lineCount >= maxLines) return;
    } else {
      line = nextLine;
    }
  }
  if (line && lineCount < maxLines) ctx.fillText(line, x, y + lineCount * lineHeight);
};

const drawCard = async (props: CultureCardProps) => {
  // The preview <img> may have been cached without an Origin header. Use a
  // unique request URL so export receives the backend's CORS-enabled response.
  const exportImageUrl = new URL(props.imageUrl, window.location.href);
  exportImageUrl.searchParams.set('culture_card_export', String(Date.now()));
  const response = await fetch(exportImageUrl.toString(), { cache: 'no-store' });
  if (!response.ok) throw new Error(`无法读取生成图片（HTTP ${response.status}）`);
  const blob = await response.blob();
  const image = await createImageBitmap(blob);
  try {
    const style = STYLES.find((item) => item.id === props.styleId);
    const themeKey = style?.cardTheme || 'zhuxianzhen';
    const palette = cultureCardThemes[themeKey];
    const canvas = document.createElement('canvas');
    canvas.width = 1080;
    canvas.height = 1440;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('浏览器无法创建图片画布');

    ctx.fillStyle = palette.paper;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = `${palette.primary}28`;
    ctx.lineWidth = 2;
    roundedRect(ctx, 26, 26, 1028, 1388, 26);
    ctx.stroke();
    ctx.strokeStyle = `${palette.secondary}99`;
    ctx.lineWidth = 3;
    roundedRect(ctx, 42, 42, 996, 1356, 20);
    ctx.stroke();

    // A restrained style-linked corner motif keeps the five variants related.
    ctx.fillStyle = palette.secondary;
    ctx.globalAlpha = 0.72;
    for (const [x, y, direction] of [[72, 72, 1], [1008, 72, -1], [72, 1368, 1], [1008, 1368, -1]] as const) {
      ctx.beginPath();
      ctx.arc(x, y, 13, Math.PI * 0.15, Math.PI * 0.85, direction < 0);
      ctx.strokeStyle = palette.secondary;
      ctx.lineWidth = 3;
      ctx.stroke();
      if (palette.motif === 'cutpaper' || palette.motif === 'auspicious') {
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    ctx.globalAlpha = 1;

    ctx.fillStyle = palette.primary;
    ctx.font = '700 27px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
    ctx.fillText('纹脉华章', 72, 100);
    ctx.fillStyle = palette.ink;
    ctx.font = '500 18px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
    ctx.fillText('文化解读 · 作品卡', 72, 134);
    ctx.textAlign = 'right';
    ctx.fillStyle = palette.primary;
    ctx.font = '600 19px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
    ctx.fillText(props.styleName, 1008, 105);
    ctx.textAlign = 'left';

    ctx.save();
    ctx.shadowColor = 'rgba(56, 42, 30, 0.14)';
    ctx.shadowBlur = 24;
    ctx.shadowOffsetY = 10;
    roundedRect(ctx, 72, 168, 936, 552, 18);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    ctx.restore();
    ctx.save();
    roundedRect(ctx, 78, 174, 924, 540, 13);
    ctx.clip();
    containImage(ctx, image, 78, 174, 924, 540, palette.paper);
    ctx.restore();

    ctx.fillStyle = palette.primary;
    ctx.font = '600 18px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
    ctx.fillText(props.analysis ? '画面主题' : '创作主题', 78, 770);
    ctx.fillStyle = palette.ink;
    ctx.font = '600 29px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
    wrapCanvasText(ctx, props.analysis?.title || readableTheme(props.theme), 78, 814, 924, 39, 1);
    if (props.analysis?.theme_summary) {
      ctx.fillStyle = palette.ink;
      ctx.font = '400 19px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
      wrapCanvasText(ctx, props.analysis.theme_summary, 78, 850, 924, 29, 1);
    } else {
      ctx.fillStyle = palette.ink;
      ctx.font = '400 18px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
      wrapCanvasText(ctx, `创作主题：${readableTheme(props.theme)}`, 78, 850, 924, 28, 1);
    }

    ctx.fillStyle = palette.primary;
    ctx.font = '600 18px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
    ctx.fillText(props.analysis ? `画面主体 · ${props.analysis.observed_subjects.slice(0, 3).join('、')}` : '风格特征', 78, 900);
    if (props.analysis) ctx.fillText('风格特征', 78, 940);
    const features = props.visualFeatures.slice(0, 4);
    let featureX = 78;
    let featureY = props.analysis ? 964 : 934;
    ctx.font = '500 17px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
    for (const feature of features) {
      const tagWidth = Math.ceil(ctx.measureText(feature).width) + 34;
      if (featureX + tagWidth > 1008) {
        featureX = 78;
        featureY += 52;
      }
      ctx.fillStyle = `${palette.primary}12`;
      roundedRect(ctx, featureX, featureY, tagWidth, 38, 19);
      ctx.fill();
      ctx.fillStyle = palette.primary;
      ctx.fillText(feature, featureX + 17, featureY + 25);
      featureX += tagWidth + 12;
    }

    const cultureY = featureY + 78;
    ctx.fillStyle = palette.primary;
    ctx.font = '600 18px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
    ctx.fillText('文化解读', 78, cultureY);
    ctx.fillStyle = palette.ink;
    ctx.font = '400 20px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
    wrapCanvasText(ctx, props.cultureSummary, 78, cultureY + 42, 924, 34, 4);

    const sceneY = 1244;
    ctx.fillStyle = palette.primary;
    ctx.font = '600 18px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
    ctx.fillText('推荐应用', 78, sceneY);
    ctx.fillStyle = palette.ink;
    ctx.font = '500 18px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
    ctx.fillText(props.recommendedScenes.slice(0, 3).join('  ·  '), 78, sceneY + 40);

    const generatedDate = new Date(props.generatedAt);
    ctx.strokeStyle = `${palette.secondary}88`;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(78, 1345);
    ctx.lineTo(1002, 1345);
    ctx.stroke();
    ctx.fillStyle = palette.ink;
    ctx.font = '400 15px "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
    ctx.fillText(`生成于 ${Number.isNaN(generatedDate.valueOf()) ? '—' : generatedDate.toLocaleString('zh-CN')}`, 78, 1376);
    ctx.textAlign = 'right';
    ctx.fillText('传统视觉文化 · 数字创作', 1002, 1376);
    ctx.textAlign = 'left';

    const png = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((result) => result ? resolve(result) : reject(new Error('PNG 图片导出失败')), 'image/png');
    });
    return png;
  } finally {
    image.close();
  }
};

export default function CultureCard(props: CultureCardProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadMessage, setDownloadMessage] = useState('');
  const style = STYLES.find((item) => item.id === props.styleId) || STYLES[0];
  const themeKey = style?.cardTheme || 'zhuxianzhen';
  const palette = cultureCardThemes[themeKey];
  const layout = useMemo<CultureCardLayout>(() => {
    const layouts: CultureCardLayout[] = ['horizontal', 'editorial', 'stacked'];
    const seed = `${props.theme}|${props.styleId}|${props.imageUrl}`;
    return layouts[stableHash(seed) % layouts.length];
  }, [props.theme, props.styleId, props.imageUrl]);

  const handleDownload = async () => {
    setIsDownloading(true);
    setDownloadMessage('正在导出高清文化卡…');
    try {
      const png = await drawCard(props);
      const objectUrl = URL.createObjectURL(png);
      const anchor = document.createElement('a');
      anchor.href = objectUrl;
      anchor.download = `wenmai_culture_card_${props.styleId}_${getFilenameTimestamp(new Date())}.png`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 15000);
      setDownloadMessage('文化说明卡已下载（1080 × 1440 PNG）');
    } catch (error) {
      setDownloadMessage(error instanceof Error ? error.message : '文化说明卡导出失败，请稍后重试。');
    } finally {
      setIsDownloading(false);
    }
  };

  const isEditorial = layout === 'editorial';
  const isStacked = layout === 'stacked';

  return (
    <section
      data-testid="culture-card"
      data-theme={themeKey}
      data-layout={layout}
      className="overflow-hidden rounded-2xl border bg-white shadow-[0_12px_36px_rgba(80,49,35,0.08)]"
      style={{ borderColor: `${palette.primary}30` }}
    >
      <div className="flex items-center justify-between gap-3 px-5 py-4 sm:px-6" style={{ background: `linear-gradient(115deg, ${palette.paper}, #fff 76%)` }}>
        <div>
          <div className="text-[10px] font-semibold tracking-[0.2em]" style={{ color: palette.primary }}>纹脉华章 · 作品解读</div>
          <h3 className="mt-1 font-serif text-lg font-bold text-ink sm:text-xl">{props.analysis?.title || '文化说明卡'}</h3>
        </div>
        <div className="rounded-full border px-3 py-1.5 text-xs font-medium" style={{ color: palette.primary, borderColor: `${palette.primary}35`, backgroundColor: `${palette.primary}0b` }}>
          {props.styleName}
        </div>
      </div>

      <div className={isEditorial ? 'border-t px-5 pb-5 pt-4 sm:px-6' : 'grid gap-5 border-t p-5 sm:grid-cols-[minmax(170px,0.78fr)_1.5fr] sm:p-6'}>
        <div className={isEditorial ? 'mb-5 grid grid-cols-[minmax(0,1.35fr)_minmax(120px,0.65fr)] gap-4' : ''}>
          <div className={`overflow-hidden rounded-xl border shadow-sm ${isEditorial ? 'aspect-[16/7]' : isStacked ? 'aspect-[16/8] sm:aspect-[4/3]' : 'aspect-[4/5]'}`} style={{ borderColor: `${palette.secondary}55`, backgroundColor: palette.paper }}>
            <img src={props.imageUrl} alt={`${props.styleName}风格生成作品`} className="h-full w-full object-contain" />
          </div>
          {isEditorial && (
            <div className="flex flex-col justify-center rounded-xl p-4" style={{ backgroundColor: palette.paper }}>
              <div className="text-xs" style={{ color: palette.primary }}>本次主题</div>
              <div className="mt-2 font-serif text-base font-semibold leading-relaxed text-ink">{readableTheme(props.theme)}</div>
              <div className="mt-3 h-px" style={{ backgroundColor: `${palette.secondary}66` }} />
              <div className="mt-3 text-[11px] leading-relaxed text-ink/60">{style?.category}</div>
            </div>
          )}
        </div>

        <div className="flex min-w-0 flex-col">
          {!isEditorial && (
            <div className="mb-4">
              <div className="text-[11px] font-medium" style={{ color: palette.primary }}>{props.analysis ? '画面主题' : '创作主题'}</div>
              <p className="mt-1 font-serif text-base font-semibold leading-relaxed text-ink">{props.analysis?.theme_summary || readableTheme(props.theme)}</p>
              {props.analysis && <p className="mt-1 text-[11px] leading-5 text-ink/50">创作输入：{readableTheme(props.theme)}</p>}
            </div>
          )}
          {props.analysis && (
            <div className="mb-4">
              <div className="text-[11px] font-medium" style={{ color: palette.primary }}>画面主体</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {props.analysis.observed_subjects.slice(0, 4).map((subject) => <span key={subject} className="rounded-full border px-2.5 py-1 text-[11px] text-ink/70" style={{ borderColor: `${palette.secondary}55`, backgroundColor: `${palette.secondary}10` }}>{subject}</span>)}
              </div>
            </div>
          )}
          <div>
            <div className="text-[11px] font-medium" style={{ color: palette.primary }}>风格特征</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {props.visualFeatures.slice(0, 4).map((feature) => (
                <span key={feature} className="rounded-full px-2.5 py-1 text-[11px]" style={{ color: palette.primary, backgroundColor: `${palette.primary}10` }}>{feature}</span>
              ))}
            </div>
          </div>
          <div className="mt-4 rounded-xl border-l-[3px] px-3.5 py-3" style={{ borderColor: palette.secondary, backgroundColor: palette.paper }}>
            <div className="text-[11px] font-medium" style={{ color: palette.primary }}>文化解读</div>
            <p className="mt-1.5 text-xs leading-6 text-ink/75">{props.cultureSummary}</p>
          </div>
          <div className="mt-4">
            <div className="text-[11px] font-medium" style={{ color: palette.primary }}>推荐应用</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {props.recommendedScenes.slice(0, 3).map((scene) => (
                <span key={scene} className="rounded-md border px-2 py-1 text-[11px] text-ink/65" style={{ borderColor: `${palette.secondary}55` }}>{scene}</span>
              ))}
            </div>
          </div>
          <div className="mt-auto flex items-end justify-between gap-3 pt-5">
            <span className="text-[10px] text-ink/40">{props.analysisSource === 'qwen3_vl' ? '本地 Qwen3-VL 已读取生成图' : '依据主题与平台风格条目生成'}</span>
            <button
              type="button"
              onClick={handleDownload}
              disabled={isDownloading}
              className="inline-flex shrink-0 items-center gap-2 rounded-lg px-3.5 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:brightness-105 disabled:cursor-wait disabled:opacity-70"
              style={{ backgroundColor: palette.primary }}
            >
              {isDownloading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              {isDownloading ? '导出中' : '下载文化说明卡'}
            </button>
          </div>
          {downloadMessage && <p aria-live="polite" className="mt-2 text-right text-[11px] text-ink/55">{downloadMessage}</p>}
        </div>
      </div>
      {props.analysis && (
        <details className="border-t px-5 py-3 sm:px-6" style={{ borderColor: `${palette.primary}18` }}>
          <summary className="cursor-pointer text-xs font-medium text-ink/55">查看作品解读详情</summary>
          <div className="mt-3 grid gap-3 text-xs sm:grid-cols-2">
            <div className="rounded-lg p-3" style={{ backgroundColor: palette.paper }}><span className="font-medium" style={{ color: palette.primary }}>主色观察</span><p className="mt-1 leading-5 text-ink/70">{props.analysis.dominant_colors.join('、')}</p></div>
            <div className="rounded-lg p-3" style={{ backgroundColor: palette.paper }}><span className="font-medium" style={{ color: palette.primary }}>构图观察</span><p className="mt-1 leading-5 text-ink/70">{props.analysis.composition}</p></div>
            <div className="rounded-lg p-3 sm:col-span-2" style={{ backgroundColor: palette.paper }}><span className="font-medium" style={{ color: palette.primary }}>风格观察</span><p className="mt-1 leading-5 text-ink/70">{props.analysis.style_interpretation}</p></div>
            <div className="text-[11px] text-ink/45">主题一致性观察：{props.analysis.theme_alignment} · 风格呈现观察：{props.analysis.style_alignment}</div>
          </div>
        </details>
      )}
    </section>
  );
}
