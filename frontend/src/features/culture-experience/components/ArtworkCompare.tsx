import { useState } from 'react';
import { MoveHorizontal } from 'lucide-react';

interface CompareProps {
  referenceUrl?: string;
  artworkUrl: string;
  title: string;
  accent: string;
}

/**
 * 原图 / 风格化 对照。
 * 用原生 range 承载拖拽与键盘（左右方向键），避免自己重实现一遍可访问性；
 * 视觉上的分割线只是它的投影。
 * 已按要求移除覆盖在画面四个边角上的冗余角标，保证作品画面纯净完整。
 */
export function ArtworkCompare({ referenceUrl, artworkUrl, title, accent }: CompareProps) {
  const [position, setPosition] = useState(52);

  if (!referenceUrl) {
    return (
      <div className="overflow-hidden rounded-xl border border-[color:var(--color-gold)]/35 bg-black/5 shadow-xs">
        <img src={artworkUrl} alt={`${title} 画面`} className="block h-auto w-full object-cover" loading="lazy" decoding="async" />
      </div>
    );
  }

  return (
    <div className="group relative overflow-hidden rounded-xl border border-[color:var(--color-gold)]/35 bg-black/5 shadow-xs">
      <div className="relative aspect-square w-full">
        <img
          src={referenceUrl}
          alt={`${title} 上传的参考图`}
          className="absolute inset-0 h-full w-full object-cover"
          loading="lazy"
          decoding="async"
        />
        <img
          src={artworkUrl}
          alt={`${title} 文化风格化结果`}
          className="absolute inset-0 h-full w-full object-cover"
          style={{ clipPath: `inset(0 0 0 ${position}%)` }}
          loading="lazy"
          decoding="async"
        />

        {/* 分隔线与拖动滑块 */}
        <div
          className="pointer-events-none absolute inset-y-0 w-[2px] bg-white/90 shadow-[0_0_8px_rgba(0,0,0,0.4)]"
          style={{ left: `${position}%` }}
          aria-hidden="true"
        >
          <span
            className="absolute left-1/2 top-1/2 flex h-8 w-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white/80 text-white shadow-xl transition group-hover:scale-110"
            style={{ backgroundColor: accent }}
          >
            <MoveHorizontal size={14} />
          </span>
        </div>

        <input
          type="range"
          min={0}
          max={100}
          step={0.5}
          value={position}
          onChange={(event) => setPosition(Number(event.target.value))}
          className="absolute inset-0 h-full w-full cursor-ew-resize opacity-0"
          aria-label={`${title}：拖动或用方向键对照参考图与风格化结果`}
        />
      </div>
      <div className="flex items-center justify-between px-3 py-1.5 text-xs text-[color:var(--color-ink)]/55 bg-white/50 border-t border-[color:var(--color-gold)]/20">
        <span className="font-serif">拖动左右滑动轴对照原图</span>
        <span className="tabular-nums font-mono text-[11px]">{Math.round(position)}% 风格化呈现</span>
      </div>
    </div>
  );
}

export default ArtworkCompare;
