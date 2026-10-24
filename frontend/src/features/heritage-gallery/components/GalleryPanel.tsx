/**
 * 右侧图库抽屉：策展选择册。
 *
 * 设计取向：
 *  - 半透明宣纸底 + 细金边，不是后台表格
 *  - 平时隐藏，点画框才滑出
 *  - 缩略图大、标题小、风格标签克制
 *  - 支持键盘 Esc 关闭、方向键浏览
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { X, Search, RotateCcw, Eraser, Info, ArrowRight } from 'lucide-react';
import { refreshGalleryPool, useGalleryPool } from '../../../data/galleryPool';
import type { GalleryConfig } from '../buildings/layout';
import type { GalleryArtwork } from '../types';

interface GalleryPanelProps {
  /** 当前建筑的画框/展墙配置：换馆后画框编号体系不同，必须按馆解析 */
  config: GalleryConfig;
  frameId: string | null;
  currentArtworkId: string;
  onPick: (artworkId: string) => void;
  onClear: () => void;
  onReset: () => void;
  onClose: () => void;
  onOpenDetail: (artworkId: string) => void;
}

export function GalleryPanel({
  config,
  frameId,
  currentArtworkId,
  onPick,
  onClear,
  onReset,
  onClose,
  onOpenDetail,
}: GalleryPanelProps) {
  const [query, setQuery] = useState('');
  const [styleFilter, setStyleFilter] = useState<string>('all');
  const panelRef = useRef<HTMLDivElement>(null);
  // 运行期新生成的作品也进入可选池；面板打开时拉一次，失败保留现有内容。
  const pool = useGalleryPool();

  useEffect(() => {
    if (frameId) void refreshGalleryPool();
  }, [frameId]);

  const frame = frameId ? config.frameById.get(frameId) : undefined;
  const wall = frame ? config.wallById.get(frame.wallId) : undefined;

  // Esc 关闭
  useEffect(() => {
    if (!frameId) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [frameId, onClose]);

  // 打开时把焦点移到面板，方便键盘操作
  useEffect(() => {
    if (frameId) panelRef.current?.focus();
  }, [frameId]);

  const styles = useMemo(() => {
    const seen = new Map<string, string>();
    for (const artwork of pool) {
      if (!seen.has(artwork.styleId)) seen.set(artwork.styleId, artwork.styleName);
    }
    return Array.from(seen.entries());
  }, [pool]);

  const filtered = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    return pool.filter((artwork) => {
      if (styleFilter !== 'all' && artwork.styleId !== styleFilter) return false;
      if (!keyword) return true;
      return (
        artwork.title.toLowerCase().includes(keyword) ||
        artwork.styleName.toLowerCase().includes(keyword) ||
        artwork.features.some((feature) => feature.toLowerCase().includes(keyword))
      );
    });
  }, [pool, query, styleFilter]);

  if (!frameId) return null;

  return (
    <div
      ref={panelRef}
      tabIndex={-1}
      role="dialog"
      aria-label="策展图库"
      className="pointer-events-auto absolute right-0 top-0 z-30 flex h-full w-[min(92vw,384px)] flex-col border-l border-[color:var(--color-gold)]/40 bg-[#FBF6EB]/94 shadow-[-12px_0_40px_rgba(63,43,31,0.14)] outline-none backdrop-blur-md"
    >
      {/* 头部 */}
      <div className="flex items-start justify-between gap-3 border-b border-[color:var(--color-gold)]/30 px-4 pb-3 pt-4">
        <div className="min-w-0">
          <p className="text-[10px] tracking-[0.28em] text-[color:var(--color-primary)]">策展 · 换画</p>
          <h2 className="mt-1 font-serif text-[15px] text-[color:var(--color-ink)]">
            {wall?.label ?? '画框'}
          </h2>
          <p className="mt-0.5 text-[11px] text-[color:var(--color-ink)]/50">
            {frame ? `画框 ${frame.id}` : ''} · 点击下方作品即可更换
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="关闭图库"
          className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[color:var(--color-ink)]/45 transition hover:bg-black/5 hover:text-[color:var(--color-ink)]"
        >
          <X size={15} />
        </button>
      </div>

      {/* 搜索与筛选 */}
      <div className="border-b border-[color:var(--color-gold)]/25 px-4 py-3">
        <div className="flex items-center gap-2 rounded border border-[color:var(--color-gold)]/40 bg-white/60 px-2 py-1.5">
          <Search size={13} className="shrink-0 text-[color:var(--color-ink)]/35" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索作品或风格"
            className="w-full bg-transparent text-[12px] text-[color:var(--color-ink)] outline-none placeholder:text-[color:var(--color-ink)]/35"
          />
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={() => setStyleFilter('all')}
            className={`rounded-full px-2 py-0.5 text-[10.5px] transition ${
              styleFilter === 'all'
                ? 'bg-[color:var(--color-primary)] text-white'
                : 'border border-[color:var(--color-gold)]/50 text-[color:var(--color-ink)]/60 hover:border-[color:var(--color-primary)]'
            }`}
          >
            全部
          </button>
          {styles.map(([id, name]) => (
            <button
              key={id}
              type="button"
              onClick={() => setStyleFilter(id)}
              className={`rounded-full px-2 py-0.5 text-[10.5px] transition ${
                styleFilter === id
                  ? 'bg-[color:var(--color-primary)] text-white'
                  : 'border border-[color:var(--color-gold)]/50 text-[color:var(--color-ink)]/60 hover:border-[color:var(--color-primary)]'
              }`}
            >
              {name}
            </button>
          ))}
        </div>
      </div>

      {/* 作品列表 */}
      <div className="flex-1 overflow-y-auto px-3 py-3">
        {filtered.length === 0 ? (
          <p className="px-2 py-8 text-center text-[12px] text-[color:var(--color-ink)]/45">
            没有匹配的作品，换个关键词试试。
          </p>
        ) : (
          <ul className="space-y-2">
            {filtered.map((artwork) => (
              <ArtworkRow
                key={artwork.id}
                artwork={artwork}
                active={artwork.id === currentArtworkId}
                onPick={() => onPick(artwork.id)}
                onDetail={() => onOpenDetail(artwork.id)}
              />
            ))}
          </ul>
        )}
      </div>

      {/* 底部操作 */}
      <div className="flex items-center gap-2 border-t border-[color:var(--color-gold)]/30 px-4 py-3">
        <button
          type="button"
          onClick={onReset}
          className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/50 px-2.5 py-1.5 text-[11.5px] text-[color:var(--color-ink)]/70 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
        >
          <RotateCcw size={12} />
          恢复默认
        </button>
        <button
          type="button"
          onClick={onClear}
          className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/50 px-2.5 py-1.5 text-[11.5px] text-[color:var(--color-ink)]/70 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
        >
          <Eraser size={12} />
          取下
        </button>
      </div>
    </div>
  );
}

function ArtworkRow({
  artwork,
  active,
  onPick,
  onDetail,
}: {
  artwork: GalleryArtwork;
  active: boolean;
  onPick: () => void;
  onDetail: () => void;
}) {
  return (
    <li>
      <div
        className={`group flex gap-2.5 rounded border p-2 transition ${
          active
            ? 'border-[color:var(--color-primary)]/60 bg-white/80'
            : 'border-transparent hover:border-[color:var(--color-gold)]/50 hover:bg-white/55'
        }`}
      >
        <button type="button" onClick={onPick} className="flex flex-1 gap-2.5 text-left">
          <img
            src={artwork.thumbUrl}
            alt={artwork.title}
            loading="lazy"
            className="h-14 w-14 shrink-0 rounded object-cover"
            style={{ boxShadow: `0 0 0 1px ${artwork.accent}22` }}
          />
          <span className="min-w-0 flex-1">
            <span className="block truncate font-serif text-[12.5px] text-[color:var(--color-ink)]">
              {artwork.title}
            </span>
            <span className="mt-0.5 block text-[10.5px]" style={{ color: artwork.accent }}>
              {artwork.styleName}
              {artwork.origin === 'runtime' && (
                <span className="ml-1 rounded-full bg-[color:var(--color-gold)]/20 px-1.5 py-px text-[9px] text-[color:var(--color-ink)]/60">
                  新生成
                </span>
              )}
            </span>
            <span className="mt-0.5 line-clamp-1 block text-[10.5px] text-[color:var(--color-ink)]/45">
              {artwork.features.slice(0, 2).join(' · ') || artwork.summary.slice(0, 20)}
            </span>
          </span>
        </button>
        <button
          type="button"
          onClick={onDetail}
          aria-label={`查看《${artwork.title}》详情`}
          className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[color:var(--color-ink)]/30 transition hover:bg-black/5 hover:text-[color:var(--color-primary)]"
        >
          <Info size={13} />
        </button>
      </div>
    </li>
  );
}
