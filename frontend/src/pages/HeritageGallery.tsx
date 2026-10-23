/**
 * 纹脉展馆 · 页面
 *
 * 布局取向：3D 场景占满视口，UI 只保留最必要的角落
 *  - 左上：标题与一句说明
 *  - 左下：浏览模式 + 机位切换 + 布展工具
 *  - 右侧：图库抽屉（点画框才出现）
 *  - 右下：沉浸模式按钮（隐藏全部界面，只留一个「显示界面」）
 *
 * 不使用站内常规导航条覆盖场景：进入后由本页自己提供返回入口，
 * 保证沉浸感，同时不让人迷路。
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  RotateCcw,
  Trash2,
  MousePointerClick,
  Move,
  ZoomIn,
  Eye,
  EyeOff,
  Building2,
  Layers,
  Frame,
  PackageOpen,
} from 'lucide-react';
import { HeritageScene } from '../features/heritage-gallery/scene/HeritageScene';
import { GalleryPanel } from '../features/heritage-gallery/components/GalleryPanel';
import { DiYPanel } from '../features/heritage-gallery/components/DiYPanel';
import { TimeSwitch } from '../features/heritage-gallery/components/TimeSwitch';
import { ViewModeSwitch, type ViewMode } from '../features/heritage-gallery/components/ViewModeSwitch';
import { ArtworkDetail } from '../features/heritage-gallery/components/ArtworkDetail';
import { useCurationStore, resolveArtworkId } from '../features/heritage-gallery/state/curationStore';
import { useDiyStore } from '../features/heritage-gallery/state/diyStore';
import { useDoorStore } from '../features/heritage-gallery/state/doorStore';
import { useFrameHoverStore } from '../features/heritage-gallery/state/frameHoverStore';
import { ASSET_BY_ID, ASSET_GROUP_LABEL } from '../features/heritage-gallery/props/assets/assetCatalog';
import { cameraPresets, frameSlots } from '../data/heritageGalleryConfig';
import { galleryArtworks } from '../data/galleryArtworks';
import type { TimeOfDay } from '../features/heritage-gallery/scene/DayNightRig';
import type { GalleryMode } from '../features/heritage-gallery/types';
import type { MascotView } from '../features/heritage-gallery/mascot/MascotCompanion';

const MODES: { id: GalleryMode; label: string; icon: typeof Eye; hint: string }[] = [
  { id: 'exterior', label: '外观', icon: Building2, hint: '屋顶完整，绕建筑旋转' },
  { id: 'interior', label: '内部', icon: Layers, hint: '收起屋顶，进入两层展厅' },
  { id: 'curation', label: '布展', icon: Frame, hint: '点画框换画、拖动位置' },
];

/** 每种模式下提供的机位（顺序与 Blender 相机集合一致） */
const MODE_PRESETS: Record<GalleryMode, string[]> = {
  exterior: ['exterior', 'front', 'back', 'left', 'right', 'top'],
  interior: ['floor1', 'floor2', 'ceiling', 'eave'],
  curation: ['exterior', 'floor1', 'floor2'],
};

export default function HeritageGallery() {
  const [presetId, setPresetId] = useState('exterior');
  const [mode, setMode] = useState<GalleryMode>('exterior');
  const [showHints, setShowHints] = useState(true);
  const [immersive, setImmersive] = useState(false);
  const [time, setTime] = useState<TimeOfDay>('day');
  const [viewMode, setViewMode] = useState<ViewMode>('third');
  const [mascotActive, setMascotActive] = useState(false);
  const [mascotView, setMascotView] = useState<MascotView>('third');
  const panelOpen = useDiyStore((state) => state.panelOpen);
  const setPanelOpen = useDiyStore((state) => state.setPanelOpen);
  const diyCount = useDiyStore((state) => state.items.length);
  useEffect(() => {
    const onInfo = (event: Event) => {
      const detail = (event as CustomEvent<{ assetId?: string }>).detail;
      const id = detail?.assetId;
      if (!id) return;
      const current = useDiyStore.getState().infoAssetId;
      useDiyStore.getState().setInfoAsset(current === id ? null : id);
    };
    window.addEventListener('wenmai:asset-info', onInfo);
    return () => window.removeEventListener('wenmai:asset-info', onInfo);
  }, []);
  const doorHover = useDoorStore((state) => state.hover);
  const doorOpen = useDoorStore((state) => state.open);
  const doorX = useDoorStore((state) => state.x);
  const doorY = useDoorStore((state) => state.y);
  const hoverFrameId = useFrameHoverStore((state) => state.frameId);
  const hoverFrameX = useFrameHoverStore((state) => state.x);
  const hoverFrameY = useFrameHoverStore((state) => state.y);
  const hoverFrameTitle = useFrameHoverStore((state) => state.title);
  const hoverAssetKey = useDiyStore((state) => state.hoverAssetKey);
  const hoverAssetName = useDiyStore((state) => state.hoverAssetName);
  const infoAssetId = useDiyStore((state) => state.infoAssetId);
  const setInfoAsset = useDiyStore((state) => state.setInfoAsset);
  const contextMenu = useDiyStore((state) => state.contextMenu);
  const closeContextMenu = useDiyStore((state) => state.closeContextMenu);
  const removeDiyItem = useDiyStore((state) => state.removeItem);

  const assignments = useCurationStore((state) => state.assignments);
  const selectedFrameId = useCurationStore((state) => state.selectedFrameId);
  const detailArtworkId = useCurationStore((state) => state.detailArtworkId);
  const selectFrame = useCurationStore((state) => state.selectFrame);
  const assignArtwork = useCurationStore((state) => state.assignArtwork);
  const clearFrame = useCurationStore((state) => state.clearFrame);
  const resetFrame = useCurationStore((state) => state.resetFrame);
  const resetAll = useCurationStore((state) => state.resetAll);
  const openDetail = useCurationStore((state) => state.openDetail);

  const handleFrameSelect = useCallback(
    (frameId: string) => {
      selectFrame(frameId);
      setMode('curation');
      setShowHints(false);
    },
    [selectFrame],
  );

  const handleClose = useCallback(() => selectFrame(null), [selectFrame]);

  const handleMode = useCallback((next: GalleryMode) => {
    setMode(next);
    // 切模式时落到该模式的主机位，避免停在一个不合法的视角。
    // 布展必须进厅：外观机位离建筑几十米，落位会打到馆外的台基上。
    const options = MODE_PRESETS[next];
    setPresetId((current) => {
      if (next === 'curation' && !['floor1', 'floor2'].includes(current)) return 'floor1';
      return options.includes(current) ? current : options[0];
    });
  }, []);

  // 落位提示（吸附失败 / 降级到地面）自动消失，不长期占屏
  const placeHint = useDiyStore((state) => state.placeHint);
  const setPlaceHint = useDiyStore((state) => state.setPlaceHint);
  useEffect(() => {
    if (!placeHint) return undefined;
    const timer = window.setTimeout(() => setPlaceHint(''), 3200);
    return () => window.clearTimeout(timer);
  }, [placeHint, setPlaceHint]);

  // 首次进入 8 秒后自动收起提示，不长期占据画面
  useEffect(() => {
    const timer = window.setTimeout(() => setShowHints(false), 8000);
    return () => window.clearTimeout(timer);
  }, []);

  // 沉浸模式统一用 Esc 退出
  useEffect(() => {
    if (!immersive) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setImmersive(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [immersive]);

  const currentArtworkId = selectedFrameId ? resolveArtworkId(assignments, selectedFrameId) : '';
  const visiblePresets = useMemo(
    () => cameraPresets.filter((preset) => MODE_PRESETS[mode].includes(preset.id)),
    [mode],
  );
  const placed = frameSlots.filter((slot) => Boolean(resolveArtworkId(assignments, slot.id))).length;

  /** 唤醒吉祥物：收起提示与布展面板，交给角色探索模式 */
  const wakeMascot = useCallback(() => {
    setMascotActive(true);
    setMascotView('third');
    setShowHints(false);
    setPanelOpen(false);
    selectFrame(null);
  }, [selectFrame, setPanelOpen]);

  const exitMascot = useCallback(() => {
    setMascotActive(false);
    setShowHints(true);
  }, []);

  /** 角色靠近展品：用现有 CultureCard（ArtworkDetail）展示，不新编文化知识 */
  const handleMascotExhibit = useCallback(
    (frameId: string) => {
      const artworkId = resolveArtworkId(assignments, frameId);
      if (artworkId) openDetail(artworkId);
    },
    [assignments, openDetail],
  );

  return (
    <div className="relative h-[100dvh] w-full overflow-hidden bg-[#BFD9E8]">
      {/* 3D 场景 */}
      <div className="absolute inset-0">
        <HeritageScene
          presetId={presetId}
          mode={mode}
          time={time}
          viewMode={viewMode}
          diy={mode === 'curation'}
          level={presetId === 'floor2' ? 2 : 1}
          onFrameSelect={handleFrameSelect}
          mascot={{
            active: mascotActive,
            view: mascotView,
            onExit: exitMascot,
            onViewChange: setMascotView,
            onExhibit: handleMascotExhibit,
          }}
        />
      </div>

      {/* 已摆器物右键菜单：删除这件器物 */}
      {contextMenu && (
        <>
          <div
            className="absolute inset-0 z-40"
            onPointerDown={() => closeContextMenu()}
            onContextMenu={(event) => {
              event.preventDefault();
              closeContextMenu();
            }}
          />
          <div
            className="pointer-events-auto absolute z-50 w-[168px] overflow-hidden rounded-md border border-[color:var(--color-gold)]/45 bg-[#FBF6EB]/98 shadow-[0_14px_40px_rgba(63,43,31,0.26)] backdrop-blur"
            style={{
              left: Math.min(contextMenu.x, (typeof window !== 'undefined' ? window.innerWidth : 1440) - 184),
              top: Math.min(contextMenu.y, (typeof window !== 'undefined' ? window.innerHeight : 900) - 132),
            }}
          >
            <div className="border-b border-[color:var(--color-gold)]/25 px-2.5 py-1.5 text-[10.5px] text-[color:var(--color-ink)]/55">
              {contextMenu.name}
            </div>
            <button
              type="button"
              onClick={() => {
                removeDiyItem(contextMenu.key);
                closeContextMenu();
              }}
              className="flex w-full items-center gap-2 px-2.5 py-2 text-left text-[12px] text-[color:var(--color-primary)] transition hover:bg-[color:var(--color-primary)]/10"
            >
              <Trash2 size={12} />
              删除这件器物
            </button>
            <button
              type="button"
              onClick={() => closeContextMenu()}
              className="flex w-full items-center gap-2 border-t border-[color:var(--color-gold)]/20 px-2.5 py-1.5 text-left text-[11.5px] text-[color:var(--color-ink)]/55 transition hover:bg-black/5"
            >
              取消
            </button>
          </div>
        </>
      )}

      {/* 器物悬停提示：告诉用户「再点一下就能互动」 */}
      {hoverAssetKey && !hoverFrameId && !doorHover && (
        <div className="pointer-events-none absolute bottom-[86px] left-1/2 z-20 -translate-x-1/2">
          <div className="whitespace-nowrap rounded-full border border-[color:var(--color-gold)]/60 bg-[#FBF6EB]/95 px-3 py-1 text-[11.5px] text-[color:var(--color-ink)]/80 shadow-[0_4px_14px_rgba(63,43,31,0.18)] backdrop-blur-sm">
            点击互动 · {hoverAssetName}
          </div>
        </div>
      )}

      {/* 落位提示：悬挂件找不到梁架锚点时拒绝放置，台面件落空时说明已落地 */}
      {placeHint && (
        <div className="pointer-events-none absolute bottom-[124px] left-1/2 z-30 -translate-x-1/2">
          <div className="whitespace-nowrap rounded-full border border-[color:var(--color-primary)]/45 bg-[#FBF6EB]/97 px-3 py-1 text-[11.5px] text-[color:var(--color-primary)] shadow-[0_6px_18px_rgba(63,43,31,0.2)] backdrop-blur-sm">
            {placeHint}
          </div>
        </div>
      )}

      {/* 画框悬停提示：告诉用户可以点它换画 */}
      {hoverFrameId && !doorHover && (
        <div
          className="pointer-events-none absolute z-20 -translate-x-1/2 -translate-y-[calc(100%+18px)]"
          style={{ left: hoverFrameX, top: hoverFrameY }}
        >
          <div className="whitespace-nowrap rounded-full border border-[color:var(--color-gold)]/60 bg-[#FBF6EB]/95 px-3 py-1 text-[11.5px] text-[color:var(--color-ink)]/80 shadow-[0_4px_14px_rgba(63,43,31,0.18)] backdrop-blur-sm">
            点击更换图画{hoverFrameTitle ? ` · ${hoverFrameTitle}` : ''}
          </div>
        </div>
      )}

      {/* 门的悬停提示：鼠标移到门扇上出现「点击开门 / 点击关门」 */}
      {doorHover && viewMode === 'third' && (
        <div
          className="pointer-events-none absolute z-20 -translate-x-1/2 -translate-y-[calc(100%+18px)]"
          style={{ left: doorX, top: doorY }}
        >
          <div className="whitespace-nowrap rounded-full border border-[color:var(--color-gold)]/60 bg-[#FBF6EB]/95 px-3 py-1 text-[11.5px] text-[color:var(--color-ink)]/80 shadow-[0_4px_14px_rgba(63,43,31,0.18)] backdrop-blur-sm">
            {doorOpen ? '点击关门' : '点击开门'}
          </div>
        </div>
      )}

      {/* 展签架弹出的文化解读卡 */}
      {infoAssetId && ASSET_BY_ID.get(infoAssetId) && (
        <div className="pointer-events-auto absolute left-1/2 top-1/2 z-40 w-[min(88vw,340px)] -translate-x-1/2 -translate-y-1/2 rounded-lg border border-[color:var(--color-gold)]/45 bg-[#FBF6EB]/97 p-4 shadow-[0_18px_60px_rgba(63,43,31,0.28)] backdrop-blur">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[10px] tracking-[0.24em] text-[color:var(--color-primary)]">
                {ASSET_GROUP_LABEL[ASSET_BY_ID.get(infoAssetId)!.group]}
              </p>
              <h3 className="mt-1 font-serif text-[16px] text-[color:var(--color-ink)]">
                {ASSET_BY_ID.get(infoAssetId)!.name}
              </h3>
            </div>
            <button
              type="button"
              onClick={() => setInfoAsset(null)}
              className="rounded-full px-2 py-0.5 text-[11px] text-[color:var(--color-ink)]/50 hover:bg-black/5"
            >
              关闭
            </button>
          </div>
          <p className="mt-2.5 text-[12px] leading-relaxed text-[color:var(--color-ink)]/70">
            {ASSET_BY_ID.get(infoAssetId)!.note}
          </p>
          <p className="mt-2 border-t border-[color:var(--color-gold)]/25 pt-2 text-[11px] text-[color:var(--color-ink)]/55">
            互动：{ASSET_BY_ID.get(infoAssetId)!.interaction}
          </p>
        </div>
      )}

      {/* 第一人称准星 */}
      {viewMode === 'first' && (
        <div className="pointer-events-none absolute inset-0 z-10 grid place-items-center">
          <div className="h-3.5 w-3.5 rounded-full border border-white/70 shadow-[0_0_6px_rgba(0,0,0,0.45)]" />
        </div>
      )}

      {immersive ? (
        <button
          type="button"
          onClick={() => setImmersive(false)}
          className="absolute right-4 top-4 z-30 inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-black/35 px-3 py-1.5 text-[11px] text-white/80 backdrop-blur-md transition hover:bg-black/50"
        >
          <Eye size={12} />
          显示界面
        </button>
      ) : (
        <>
          {/* 左上：标题 */}
          <header className="pointer-events-none absolute left-0 top-0 z-20 p-4 sm:p-6">
            <div className="pointer-events-auto max-w-[300px] rounded-lg border border-[color:var(--color-gold)]/35 bg-[#FBF6EB]/85 px-3.5 py-2.5 backdrop-blur-md">
              <Link
                to="/"
                className="inline-flex items-center gap-1.5 text-[10.5px] tracking-[0.2em] text-[color:var(--color-primary)] transition hover:gap-2.5"
              >
                <ArrowLeft size={11} />
                纹脉华章
              </Link>
              <h1 className="mt-1 font-serif text-[17px] leading-tight text-[color:var(--color-ink)]">纹脉展馆</h1>
              <p className="mt-0.5 text-[10.5px] leading-relaxed text-[color:var(--color-ink)]/55">
                两层微缩展馆 · {frameSlots.length} 个画框 · {galleryArtworks.length} 件真实案例可布展
              </p>
              <p className="mt-1 text-[10px] tabular-nums tracking-wide text-[color:var(--color-ink)]/45">
                已布展 {placed}/{frameSlots.length}
              </p>
            </div>
          </header>

          {/* 左下：模式、机位与布展工具 */}
          <div className="absolute bottom-0 left-0 z-20 p-4 sm:p-6">
            <div className="pointer-events-auto flex flex-col gap-2">
              <div className="flex items-center gap-1 rounded-lg border border-[color:var(--color-gold)]/35 bg-[#FBF6EB]/85 p-1 backdrop-blur-md">
                {MODES.map((item) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      title={item.hint}
                      onClick={() => handleMode(item.id)}
                      className={`inline-flex items-center gap-1 rounded px-2.5 py-1 text-[11.5px] transition ${
                        mode === item.id
                          ? 'bg-[color:var(--color-primary)] text-white'
                          : 'text-[color:var(--color-ink)]/65 hover:bg-black/5'
                      }`}
                    >
                      <Icon size={11} />
                      {item.label}
                    </button>
                  );
                })}
              </div>

              <div className="flex items-center gap-1 rounded-lg border border-[color:var(--color-gold)]/35 bg-[#FBF6EB]/85 p-1 backdrop-blur-md">
                {visiblePresets.map((preset) => (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => setPresetId(preset.id)}
                    className={`rounded px-2.5 py-1 text-[11.5px] transition ${
                      presetId === preset.id
                        ? 'bg-[color:var(--color-primary)] text-white'
                        : 'text-[color:var(--color-ink)]/65 hover:bg-black/5'
                    }`}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-1 rounded-lg border border-[color:var(--color-gold)]/35 bg-[#FBF6EB]/85 p-1 backdrop-blur-md">
                <button
                  type="button"
                  onClick={() => {
                    setPanelOpen(!panelOpen);
                    handleMode('curation');
                  }}
                  className={`inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-[11.5px] transition ${
                    panelOpen
                      ? 'bg-[color:var(--color-primary)] text-white'
                      : 'text-[color:var(--color-ink)]/65 hover:bg-black/5'
                  }`}
                >
                  <PackageOpen size={11} />
                  器物{diyCount > 0 ? ` · ${diyCount}` : ''}
                </button>
                <button
                  type="button"
                  onClick={resetAll}
                  className="inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-[11.5px] text-[color:var(--color-ink)]/65 transition hover:bg-black/5 hover:text-[color:var(--color-primary)]"
                >
                  <RotateCcw size={11} />
                  重置布展
                </button>
                <button
                  type="button"
                  onClick={() => setImmersive(true)}
                  className="inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-[11.5px] text-[color:var(--color-ink)]/65 transition hover:bg-black/5 hover:text-[color:var(--color-primary)]"
                >
                  <EyeOff size={11} />
                  沉浸模式
                </button>
                <button
                  type="button"
                  onClick={() => setShowHints((value) => !value)}
                  aria-label="操作提示"
                  className="flex h-6 w-6 items-center justify-center rounded text-[color:var(--color-ink)]/45 transition hover:bg-black/5"
                >
                  {showHints ? <Eye size={12} /> : <MousePointerClick size={12} />}
                </button>
              </div>

              <TimeSwitch value={time} onChange={setTime} />
              <ViewModeSwitch value={viewMode} onChange={setViewMode} />
            </div>
          </div>

          {/* 操作提示：短时显示，不长期占屏 */}
          {showHints && !mascotActive && (
            <div className="pointer-events-none absolute bottom-5 right-4 z-20 sm:right-6">
              <div className="flex items-center gap-3 rounded-full border border-[color:var(--color-gold)]/35 bg-[#FBF6EB]/88 px-4 py-1.5 text-[11px] text-[color:var(--color-ink)]/60 backdrop-blur-md">
                <span className="inline-flex items-center gap-1">
                  <Move size={11} />
                  拖拽旋转
                </span>
                <span className="inline-flex items-center gap-1">
                  <ZoomIn size={11} />
                  滚轮缩放
                </span>
                <span className="inline-flex items-center gap-1">
                  <MousePointerClick size={11} />
                  点画框换画
                </span>
              </div>
            </div>
          )}

          {/* 萌宠入口：展馆下方的空白区域，点一下就唤醒「纹纹」 */}
          {!mascotActive && (
            <button
              type="button"
              data-testid="mascot-wake"
              onClick={wakeMascot}
              className="group absolute bottom-1 left-1/2 z-20 w-[min(560px,74vw)] -translate-x-1/2 pb-2 pt-5 text-center"
            >
              <span className="inline-flex items-center gap-2 rounded-full border border-[color:var(--color-gold)]/50 bg-[#FBF6EB]/92 px-4 py-1.5 text-[12px] text-[color:var(--color-ink)]/70 shadow-sm backdrop-blur-md transition group-hover:border-[color:var(--color-primary)] group-hover:text-[color:var(--color-primary)]">
                <span className="text-[13px]">🐾</span>
                随意点击，唤醒展馆萌宠
                <span className="text-[10.5px] text-[color:var(--color-ink)]/45">纹纹 · 非遗灵猫</span>
              </span>
            </button>
          )}

          {/* 萌宠探索模式控制条 */}
          {mascotActive && (
            <div
              data-testid="mascot-hud"
              className="absolute bottom-4 left-1/2 z-30 -translate-x-1/2 rounded-xl border border-[color:var(--color-gold)]/40 bg-[#FBF6EB]/92 px-3 py-2 text-center shadow-lg backdrop-blur-md"
            >
              <div className="flex items-center justify-center gap-2">
                <button
                  type="button"
                  onClick={() => setMascotView(mascotView === 'third' ? 'first' : 'third')}
                  data-testid="mascot-view-toggle"
                  className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/50 px-2.5 py-1 text-[11.5px] text-[color:var(--color-ink)]/75 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
                >
                  <Eye size={11} />
                  {mascotView === 'third' ? '切到第一视角' : '切到第三视角'}
                </button>
                <button
                  type="button"
                  onClick={exitMascot}
                  data-testid="mascot-exit"
                  className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/50 px-2.5 py-1 text-[11.5px] text-[color:var(--color-ink)]/75 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
                >
                  <ArrowLeft size={11} />
                  退出探索
                </button>
              </div>
              <p className="mt-1 text-[10.5px] leading-relaxed text-[color:var(--color-ink)]/55">
                W / ↑ 前进 · S / ↓ 后退 · A / ← 左转 · D / → 右转 · Shift 小跑 · E 看展品 · V 切视角 · Esc 退出
              </p>
              <p className="text-[10px] text-[color:var(--color-ink)]/40">
                后侧折返楼梯可上二层；靠近画框会自动打开对应的文化卡
              </p>
            </div>
          )}

          {/* 右侧图库 */}
          <GalleryPanel
            frameId={selectedFrameId}
            currentArtworkId={currentArtworkId}
            onPick={(artworkId) => {
              if (selectedFrameId) assignArtwork(selectedFrameId, artworkId);
            }}
            onClear={() => {
              if (selectedFrameId) clearFrame(selectedFrameId);
            }}
            onReset={() => {
              if (selectedFrameId) resetFrame(selectedFrameId);
            }}
            onClose={handleClose}
            onOpenDetail={(artworkId) => openDetail(artworkId)}
          />

          {/* 右侧器物图库（DIY 布展） */}
          <DiYPanel />

          {/* 作品详情 */}
          <ArtworkDetail artworkId={detailArtworkId} onClose={() => openDetail(null)} />
        </>
      )}
    </div>
  );
}