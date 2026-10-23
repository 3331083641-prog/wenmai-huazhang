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
 */
export function ArtworkCompare({ referenceUrl, artworkUrl, title, accent }: CompareProps) {
  const [position, setPosition] = useState(52);

  if (!referenceUrl) {
    return (
      <div className="overflow-hidden rounded border border-[color:var(--color-gold)]/35 bg-black/5">
        <img src={artworkUrl} alt={`${title} 画面`} className="block h-auto w-full" loading="lazy" decoding="async" />
      </div>
    );
  }

  return (
    <div className="group relative overflow-hidden rounded border border-[color:var(--color-gold)]/35 bg-black/5">
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

        <span className="pointer-events-none absolute left-2 top-2 rounded bg-black/55 px-1.5 py-0.5 text-[10px] tracking-wider text-white/85">
          参考图
        </span>
        <span className="pointer-events-none absolute right-2 top-2 rounded bg-black/55 px-1.5 py-0.5 text-[10px] tracking-wider text-white/85">
          文化风格化
        </span>

        <div
          className="pointer-events-none absolute inset-y-0 w-[2px] bg-white/85 shadow-[0_0_8px_rgba(0,0,0,0.35)]"
          style={{ left: `${position}%` }}
          aria-hidden="true"
        >
          <span
            className="absolute left-1/2 top-1/2 flex h-8 w-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white/70 text-white shadow-lg transition group-hover:scale-110"
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
          aria-label={`${title}：拖动或用方向键对照参考图与文化风格化结果`}
        />
      </div>
      <div className="flex items-center justify-between px-2.5 py-1.5 text-[10.5px] text-[color:var(--color-ink)]/50">
        <span>拖动分隔线对照</span>
        <span className="tabular-nums">{Math.round(position)}% 风格化</span>
      </div>
    </div>
  );
}

export default ArtworkCompare;