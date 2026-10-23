import { Link } from 'react-router-dom';
import { BookOpen, ChevronDown, Compass, Eye, EyeOff, Maximize2, Minus, Plus, RotateCcw } from 'lucide-react';

interface ToolbarProps {
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
  showRegions: boolean;
  onToggleRegions: () => void;
  onFit: () => void;
  storyHref: string;
  /** 有画境资产时才给「走进画境」按钮，没有就不渲染，避免点了发现是空的 */
  wanderHref?: string;
  accent: string;
}

const buttonClass =
  'inline-flex h-9 w-9 items-center justify-center rounded border border-[color:var(--color-gold)]/45 bg-white/70 text-[color:var(--color-ink)]/70 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)] disabled:opacity-35 disabled:hover:border-[color:var(--color-gold)]/45';

/**
 * 观看工具条：所有能力都是「用户触发」，没有自动播放、没有自动运镜。
 * 放大/缩小/复位、显示位置框、进入故事。
 */
export function ViewToolbar({
  zoom,
  onZoomIn,
  onZoomOut,
  onReset,
  showRegions,
  onToggleRegions,
  onFit,
  storyHref,
  wanderHref,
  accent,
}: ToolbarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="flex items-center rounded border border-[color:var(--color-gold)]/45 bg-white/70">
        <button type="button" className={`${buttonClass} border-0 bg-transparent`} onClick={onZoomOut} aria-label="缩小画面" disabled={zoom <= 1}>
          <Minus size={15} />
        </button>
        <span className="min-w-[46px] text-center text-[11px] tabular-nums text-[color:var(--color-ink)]/60" aria-live="off">
          {Math.round(zoom * 100)}%
        </span>
        <button type="button" className={`${buttonClass} border-0 bg-transparent`} onClick={onZoomIn} aria-label="放大画面" disabled={zoom >= 3}>
          <Plus size={15} />
        </button>
      </div>

      <button type="button" className={buttonClass} onClick={onReset} aria-label="复位缩放与位置">
        <RotateCcw size={15} />
      </button>
      <button type="button" className={buttonClass} onClick={onFit} aria-label="以最适合的尺寸显示整幅画面">
        <Maximize2 size={15} />
      </button>
      <button
        type="button"
        className={`${buttonClass} ${showRegions ? 'border-[color:var(--color-primary)] text-[color:var(--color-primary)]' : ''}`}
        onClick={onToggleRegions}
        aria-label={showRegions ? '隐藏热点位置框' : '显示全部热点位置框'}
        aria-pressed={showRegions}
      >
        {showRegions ? <Eye size={15} /> : <EyeOff size={15} />}
      </button>

      <Link
        to={storyHref}
        className="ml-auto inline-flex h-9 items-center gap-1.5 rounded px-3 text-xs text-white transition hover:opacity-90"
        style={{ backgroundColor: accent }}
      >
        <BookOpen size={14} />
        读这一卷的故事
        <ChevronDown size={13} className="opacity-70" />
      </Link>

      {wanderHref && (
        <Link
          to={wanderHref}
          data-testid="experience-to-wander"
          className="inline-flex h-9 items-center gap-1.5 rounded border border-[color:var(--color-gold)]/60 bg-white/70 px-3 text-xs text-[color:var(--color-primary)] transition hover:border-[color:var(--color-primary)] hover:bg-[color:var(--color-primary)] hover:text-white"
        >
          <Compass size={14} />
          走进画境
        </Link>
      )}
    </div>
  );
}

export default ViewToolbar;