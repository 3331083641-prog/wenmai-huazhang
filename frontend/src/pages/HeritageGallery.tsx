/**
 * 纹脉展馆 · 页面（双建筑皮肤）
 *
 * 控件分层：
 *  - 默认只露三类主入口：探索模式 / 布展模式 / 视角；
 *  - 右上角是图标级工具：建筑风格 / 环境 / 帮助 / 沉浸；
 *  - 机位预设收进「视角」，昼夜收进「环境」，重置布展只出现在布展模式二级菜单；
 *  - 建筑风格是新增的一级入口：点开选「经典展馆 / 华章新馆」，
 *    切换前先把目标 GLB 下载并解析完，再换场景，全程有遮罩，不白屏、不重叠。
 *
 * 数据来源：当前建筑的 layout（画框 / 展墙 / 机位）与按建筑分桶的布展 store。
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import type { JSX, ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  Building2,
  ChevronDown,
  Compass,
  Eye,
  EyeOff,
  Frame,
  Info,
  Landmark,
  Layers,
  Loader2,
  Moon,
  PackageOpen,
  PawPrint,
  RotateCcw,
  Sun,
  Sunset,
  Trash2,
} from 'lucide-react';
import { HeritageScene } from '../features/heritage-gallery/scene/HeritageScene';
import { GalleryPanel } from '../features/heritage-gallery/components/GalleryPanel';
import { DiYPanel } from '../features/heritage-gallery/components/DiYPanel';
import { BuildingSwitch } from '../features/heritage-gallery/components/BuildingSwitch';
import { TimeSwitch } from '../features/heritage-gallery/components/TimeSwitch';
import { ViewModeSwitch, VIEW_MODES, type ViewMode } from '../features/heritage-gallery/components/ViewModeSwitch';
import { ArtworkDetail } from '../features/heritage-gallery/components/ArtworkDetail';
import { resolveArtworkId, useActivePlan, useCurationStore } from '../features/heritage-gallery/state/curationStore';
import { useDiyCount, useDiyStore } from '../features/heritage-gallery/state/diyStore';
import { useDoorStore } from '../features/heritage-gallery/state/doorStore';
import { useFrameHoverStore } from '../features/heritage-gallery/state/frameHoverStore';
import { useBuildingStore } from '../features/heritage-gallery/state/buildingStore';
import { BUILDINGS, getBuilding } from '../features/heritage-gallery/buildings';
import { preloadBuildingModel, warmupBuildingModel } from '../features/heritage-gallery/scene/modelCache';
import { ASSET_BY_ID, ASSET_GROUP_LABEL } from '../features/heritage-gallery/props/assets/assetCatalog';
import { refreshGalleryPool, useGalleryPool } from '../data/galleryPool';
import { TIME_PRESETS, type TimeOfDay } from '../features/heritage-gallery/scene/DayNightRig';
import type { GalleryMode } from '../features/heritage-gallery/types';
import type { MascotView } from '../features/heritage-gallery/mascot/MascotCompanion';

/** 菜单标识：主入口三类 + 右上角四个工具 */
type MenuId = 'explore' | 'curation' | 'view' | 'building' | 'environment' | 'help';

/** 探索模式下的两种取景 */
const SCENE_MODES: {
  id: Extract<GalleryMode, 'exterior' | 'interior'>;
  label: string;
  hint: string;
  icon: typeof Compass;
}[] = [
  { id: 'exterior', label: '外观', hint: '屋顶完整，绕建筑旋转', icon: Building2 },
  { id: 'interior', label: '内部', hint: '收起屋顶，进入两层展厅', icon: Layers },
];

/** 机位分两组：建筑外部与室内（顺序与 Blender 相机集合一致） */
const EXTERIOR_PRESETS = new Set(['exterior', 'front', 'back', 'left', 'right', 'top']);
const INTERIOR_PRESETS = new Set(['floor1', 'floor2', 'ceiling', 'eave']);

const TIME_ICONS: Record<TimeOfDay, typeof Sun> = { day: Sun, dusk: Sunset, night: Moon };

const panelClass =
  'pointer-events-auto w-[min(86vw,286px)] rounded-xl border border-[color:var(--color-gold)]/45 bg-[#FBF6EB]/97 p-2.5 shadow-[0_18px_50px_rgba(63,43,31,0.24)] backdrop-blur';

const dockButtonClass = (active: boolean) =>
  `inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-[11.5px] transition ${
    active
      ? 'bg-[color:var(--color-primary)] text-white'
      : 'text-[color:var(--color-ink)]/70 hover:bg-black/5 hover:text-[color:var(--color-ink)]'
  }`;

/* ------------------------------------------------------------------ 微分件 */

/** 菜单里的一行操作 */
function MenuRow({
  icon,
  label,
  hint,
  active,
  testId,
  onClick,
}: {
  icon: ReactNode;
  label: string;
  hint?: string;
  active?: boolean;
  testId?: string;
  onClick: () => void;
}): JSX.Element {
  return (
    <button
      type="button"
      data-testid={testId}
      onClick={onClick}
      className={`flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left transition ${
        active
          ? 'bg-[color:var(--color-primary)]/12 text-[color:var(--color-primary)]'
          : 'text-[color:var(--color-ink)]/75 hover:bg-black/5'
      }`}
    >
      <span className="mt-0.5 shrink-0 text-[color:var(--color-primary)]/80">{icon}</span>
      <span className="min-w-0">
        <span className="block text-[12px] leading-tight">{label}</span>
        {hint && (
          <span className="mt-0.5 block text-[10px] leading-snug text-[color:var(--color-ink)]/45">{hint}</span>
        )}
      </span>
    </button>
  );
}

/** 菜单小标题 */
function MenuLabel({ children }: { children: ReactNode }): JSX.Element {
  return (
    <p className="mb-1 mt-1.5 px-1 text-[9.5px] tracking-[0.22em] text-[color:var(--color-ink)]/40 first:mt-0">
      {children}
    </p>
  );
}

/** 机位小标签 */
function PresetChip({
  preset,
  active,
  onClick,
}: {
  preset: { id: string; label: string };
  active: boolean;
  onClick: () => void;
}): JSX.Element {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`rounded px-2 py-1 text-[11px] transition ${
        active
          ? 'bg-[color:var(--color-primary)] text-white'
          : 'text-[color:var(--color-ink)]/65 hover:bg-black/5 hover:text-[color:var(--color-ink)]'
      }`}
    >
      {preset.label}
    </button>
  );
}

/* ------------------------------------------------------------------ 页面 */

export default function HeritageGallery() {
  const [presetId, setPresetId] = useState('exterior');
  const [mode, setMode] = useState<GalleryMode>('exterior');
  const [immersive, setImmersive] = useState(false);
  const [time, setTime] = useState<TimeOfDay>('day');
  const [viewMode, setViewMode] = useState<ViewMode>('third');
  const [mascotActive, setMascotActive] = useState(false);
  /** 一次只开一个面板；默认 null = 全部收起，先看到场景 */
  const [menu, setMenu] = useState<MenuId | null>(null);
  // 作品池 = 内置精选 + 运行期新生成（Case Service 拉取，失败回退缓存）
  const galleryPool = useGalleryPool();

  /* ---- 建筑皮肤 ---- */
  const activeBuildingId = useBuildingStore((state) => state.active);
  const setActiveBuilding = useBuildingStore((state) => state.setActive);
  const building = useMemo(() => getBuilding(activeBuildingId), [activeBuildingId]);
  const config = building.config;
  const plan = useActivePlan();

  /** 切换在途：目标建筑 id + 下载进度 */
  const [pendingBuilding, setPendingBuilding] = useState<string | null>(null);
  const [switchProgress, setSwitchProgress] = useState(0);
  const [switchError, setSwitchError] = useState('');
  /** 首次进入也要等模型，避免露出空场地 */
  const [sceneReady, setSceneReady] = useState(false);

  useEffect(() => {
    setSceneReady(false);
  }, [activeBuildingId]);

  useEffect(() => {
    void refreshGalleryPool();
  }, []);

  const panelOpen = useDiyStore((state) => state.panelOpen);
  const setPanelOpen = useDiyStore((state) => state.setPanelOpen);
  const diyCount = useDiyCount();
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
      setMenu(null);
    },
    [selectFrame],
  );

  const handleClose = useCallback(() => selectFrame(null), [selectFrame]);

  /** 探索模式：外观 / 内部 */
  const handleSceneMode = useCallback((next: 'exterior' | 'interior') => {
    setMode(next);
    setPresetId((current) => {
      const allowed = next === 'exterior' ? EXTERIOR_PRESETS : INTERIOR_PRESETS;
      return allowed.has(current) ? current : next === 'exterior' ? 'exterior' : 'floor1';
    });
    setMenu(null);
  }, []);

  /** 布展模式：一次点进厅内，面板是二级菜单里再开 */
  const enterCuration = useCallback(() => {
    setMascotActive(false);
    setMode('curation');
    setPresetId((current) => (current === 'floor2' ? current : 'floor1'));
    setMenu('curation');
  }, []);

  /** 机位：不在布展里时按机位自动切外观 / 内部 */
  const handlePreset = useCallback(
    (next: string) => {
      setPresetId(next);
      if (mode !== 'curation') {
        setMode(INTERIOR_PRESETS.has(next) ? 'interior' : 'exterior');
      }
      setMenu(null);
    },
    [mode],
  );

  /**
   * 视角：唯一一套第一/第三人称切换。
   * 灵宠探索时「第一人称」就是角色第一视角，不再是另一套开关；
   * 选「电影」会先退出探索（电影机位要接管相机，两者不能同时）。
   */
  const handleViewMode = useCallback(
    (next: ViewMode) => {
      if (mascotActive && next === 'cinema') setMascotActive(false);
      setViewMode(next);
      setMenu(null);
    },
    [mascotActive],
  );

  /** 灵宠按 V 键切视角：同样落到这套 viewMode 上 */
  const handleMascotView = useCallback((next: MascotView) => {
    setViewMode(next === 'first' ? 'first' : 'third');
  }, []);

  const wakeMascot = useCallback(() => {
    setMascotActive(true);
    setViewMode('third');
    setPanelOpen(false);
    selectFrame(null);
    setMenu(null);
  }, [selectFrame, setPanelOpen]);

  const exitMascot = useCallback(() => {
    setMascotActive(false);
    setMenu(null);
  }, []);

  /** 角色靠近展品：用现有 CultureCard（ArtworkDetail）展示，不新编文化知识 */
  const handleMascotExhibit = useCallback(
    (frameId: string) => {
      const artworkId = resolveArtworkId(plan.assignments, frameId, activeBuildingId);
      if (artworkId) openDetail(artworkId);
    },
    [plan.assignments, openDetail, activeBuildingId],
  );

  /* ---------------------------------------------------------- 建筑切换 */

  /**
   * 切换建筑：先把目标馆的 GLB 下载解析完，再换 active。
   * 这样渲染阶段永远命中缓存，旧建筑不会提前卸载，新建筑也不会以半成品出现。
   */
  const handleBuildingSelect = useCallback(
    async (id: string) => {
      if (pendingBuilding) return;
      if (id === activeBuildingId) {
        setMenu(null);
        return;
      }
      const target = getBuilding(id);
      setMenu(null);
      setSwitchError('');
      setPendingBuilding(id);
      setSwitchProgress(0);
      // 先把场景 UI 收干净：换馆后仍停在上一个馆的「二层特写」会很怪
      setMascotActive(false);
      selectFrame(null);
      setPanelOpen(false);
      setPresetId('exterior');
      setMode('exterior');
      setViewMode('third');
      try {
        await preloadBuildingModel(target.modelUrl, (ratio) => setSwitchProgress(ratio));
        setSwitchProgress(1);
        setActiveBuilding(id);
        // 真正收起遮罩交给场景 onReady，避免「状态已切、画面还没画」的一帧空白
      } catch {
        setPendingBuilding(null);
        setSwitchError('建筑资源加载失败，请检查网络后重试');
      }
    },
    [activeBuildingId, pendingBuilding, selectFrame, setActiveBuilding, setPanelOpen],
  );

  const handleSceneReady = useCallback(() => {
    setSceneReady(true);
    setPendingBuilding(null);
    setSwitchProgress(1);
  }, []);

  // 悬停建筑卡时顺手预热：真的点下去时大概率已经在缓存里
  const handleBuildingHover = useCallback((id: string) => {
    if (id === activeBuildingId) return;
    warmupBuildingModel(getBuilding(id).modelUrl);
  }, [activeBuildingId]);

  useEffect(() => {
    if (!switchError) return undefined;
    const timer = window.setTimeout(() => setSwitchError(''), 4200);
    return () => window.clearTimeout(timer);
  }, [switchError]);

  // 落位提示（吸附失败 / 降级到地面）自动消失，不长期占屏
  const placeHint = useDiyStore((state) => state.placeHint);
  const setPlaceHint = useDiyStore((state) => state.setPlaceHint);
  useEffect(() => {
    if (!placeHint) return undefined;
    const timer = window.setTimeout(() => setPlaceHint(''), 3200);
    return () => window.clearTimeout(timer);
  }, [placeHint, setPlaceHint]);

  // Esc 统一处理：先收菜单，再退沉浸
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      if (menu) {
        setMenu(null);
        return;
      }
      if (immersive) setImmersive(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [menu, immersive]);

  const currentArtworkId = selectedFrameId
    ? resolveArtworkId(plan.assignments, selectedFrameId, activeBuildingId)
    : '';
  const frames = config.frames;
  const placed = frames.filter((slot) =>
    Boolean(resolveArtworkId(plan.assignments, slot.id, activeBuildingId)),
  ).length;
  const mascotView: MascotView = viewMode === 'first' ? 'first' : 'third';
  const timeLabel = TIME_PRESETS[time].label;
  const viewLabel = VIEW_MODES.find((entry) => entry.id === viewMode)?.label ?? '第三人称';
  const currentPresetLabel = config.cameras.find((preset) => preset.id === presetId)?.label ?? '外观';
  const TimeIcon = TIME_ICONS[time];

  const exteriorPresets = useMemo(
    () => config.cameras.filter((preset) => EXTERIOR_PRESETS.has(preset.id)),
    [config],
  );
  const interiorPresets = useMemo(
    () => config.cameras.filter((preset) => INTERIOR_PRESETS.has(preset.id)),
    [config],
  );

  const toggleMenu = useCallback((id: MenuId) => {
    setMenu((current) => (current === id ? null : id));
  }, []);

  /** 探索模式入口：从布展里点它先退回看展，然后展开菜单 */
  const openExploreMenu = useCallback(() => {
    if (mode === 'curation') {
      setMode('exterior');
      setPresetId((current) => (EXTERIOR_PRESETS.has(current) ? current : 'exterior'));
    }
    toggleMenu('explore');
  }, [mode, toggleMenu]);

  /** 遮罩：首次进入 + 正在切换 */
  const maskVisible = !sceneReady || pendingBuilding !== null;
  const maskLabel = pendingBuilding ? getBuilding(pendingBuilding).loadingLabel : building.loadingLabel;

  return (
    <div className="relative h-[100dvh] w-full overflow-hidden bg-[#BFD9E8]">
      {/* 3D 场景 */}
      <div className="absolute inset-0">
        <HeritageScene
          building={building}
          presetId={presetId}
          mode={mode}
          time={time}
          viewMode={viewMode}
          diy={mode === 'curation'}
          level={presetId === 'floor2' ? 2 : 1}
          onFrameSelect={handleFrameSelect}
          onReady={handleSceneReady}
          mascot={{
            active: mascotActive,
            view: mascotView,
            onExit: exitMascot,
            onViewChange: handleMascotView,
            onExhibit: handleMascotExhibit,
          }}
        />
      </div>

      {/* 加载 / 切换遮罩：旧建筑卸载前先把新建筑准备好，所以这里不是白屏而是一层雾面 */}
      <div
        aria-hidden={!maskVisible}
        data-testid="gallery-loading-mask"
        className={`pointer-events-none absolute inset-0 z-[60] flex items-center justify-center transition-opacity duration-500 ${
          maskVisible ? 'opacity-100' : 'opacity-0'
        }`}
      >
        <div className="pointer-events-auto flex w-[min(84vw,320px)] flex-col items-center gap-3 rounded-2xl border border-[color:var(--color-gold)]/40 bg-[#FBF6EB]/95 px-6 py-5 text-center shadow-[0_24px_70px_rgba(63,43,31,0.3)] backdrop-blur-md">
          <Loader2 size={20} className="animate-spin text-[color:var(--color-primary)]/80" />
          <div>
            <p className="font-serif text-[14px] text-[color:var(--color-ink)]">{maskLabel}</p>
            <p className="mt-1 text-[10.5px] leading-relaxed text-[color:var(--color-ink)]/50">
              {pendingBuilding ? '正在展开新的展厅空间…' : '正在展开建筑与展陈…'}
            </p>
          </div>
          <span className="block h-[3px] w-full overflow-hidden rounded-full bg-black/10">
            <span
              className="block h-full rounded-full bg-[color:var(--color-primary)] transition-[width] duration-300"
              style={{ width: `${Math.round((pendingBuilding ? switchProgress : 0.45) * 100)}%` }}
            />
          </span>
        </div>
      </div>

      {/* 切换失败提示 */}
      {switchError && (
        <div className="pointer-events-none absolute left-1/2 top-[84px] z-[70] -translate-x-1/2">
          <div className="rounded-full border border-[color:var(--color-primary)]/45 bg-[#FBF6EB]/97 px-3.5 py-1.5 text-[11.5px] text-[color:var(--color-primary)] shadow-lg">
            {switchError}
          </div>
        </div>
      )}

      {/* 菜单打开时的空白背板：点场景即收起，不打断看展 */}
      {menu && (
        <div
          className="absolute inset-0 z-10"
          onPointerDown={() => setMenu(null)}
          onContextMenu={(event) => {
            event.preventDefault();
            setMenu(null);
          }}
        />
      )}

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
                {building.name} · {frames.length} 个画框 · {galleryPool.length} 件作品可布展
              </p>
              <p className="mt-1 text-[10px] tabular-nums tracking-wide text-[color:var(--color-ink)]/45">
                已布展 {placed}/{frames.length}
              </p>
            </div>
          </header>

          {/* 右上：建筑风格 / 环境 / 帮助 / 沉浸 */}
          <div className="absolute right-3 top-3 z-30 flex items-center gap-1 rounded-xl border border-[color:var(--color-gold)]/35 bg-[#FBF6EB]/85 p-1 backdrop-blur-md sm:right-5 sm:top-5">
            <button
              type="button"
              onClick={() => toggleMenu('building')}
              aria-label={`建筑风格（当前${building.name}）`}
              title={`建筑风格 · 当前${building.name}`}
              data-testid="building-switch-button"
              className={dockButtonClass(menu === 'building')}
            >
              <Landmark size={12} />
              <span className="hidden sm:inline">建筑</span>
            </button>
            <button
              type="button"
              onClick={() => toggleMenu('environment')}
              aria-label={`环境（当前${timeLabel}）`}
              title={`环境 · 当前${timeLabel}`}
              className={dockButtonClass(menu === 'environment')}
            >
              <TimeIcon size={12} />
              <span className="hidden sm:inline">环境</span>
            </button>
            <button
              type="button"
              onClick={() => toggleMenu('help')}
              aria-label="帮助与操作说明"
              title="帮助与操作说明"
              className={dockButtonClass(menu === 'help')}
            >
              <Info size={12} />
              <span className="hidden sm:inline">帮助</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setMenu(null);
                setImmersive(true);
              }}
              aria-label="沉浸模式（隐藏全部界面）"
              title="沉浸模式"
              className={dockButtonClass(false)}
            >
              <EyeOff size={12} />
            </button>

            {/* 建筑风格面板 */}
            {menu === 'building' && (
              <div className="absolute right-0 top-[calc(100%+6px)] z-30">
                <div className={panelClass}>
                  <BuildingSwitch
                    buildings={BUILDINGS}
                    activeId={activeBuildingId}
                    pendingId={pendingBuilding}
                    progress={switchProgress}
                    onSelect={(id) => void handleBuildingSelect(id)}
                    onHover={handleBuildingHover}
                  />
                </div>
              </div>
            )}

            {/* 环境面板：昼夜 */}
            {menu === 'environment' && (
              <div className="absolute right-0 top-[calc(100%+6px)] z-30">
                <div className={panelClass}>
                  <MenuLabel>环境 · 昼夜</MenuLabel>
                  <TimeSwitch value={time} onChange={setTime} />
                  <p className="mt-1.5 px-1 text-[10px] leading-snug text-[color:var(--color-ink)]/45">
                    切换时段只改光照、曝光与环境反射，不重建场景。
                  </p>
                </div>
              </div>
            )}

            {/* 帮助面板：原「操作提示条 + 眼睛按钮」合并到这里 */}
            {menu === 'help' && (
              <div className="absolute right-0 top-[calc(100%+6px)] z-30">
                <div className={`${panelClass} w-[min(88vw,300px)]`}>
                  <MenuLabel>操作说明</MenuLabel>
                  <ul className="space-y-1 px-1 text-[11px] leading-relaxed text-[color:var(--color-ink)]/70">
                    <li>· 拖拽旋转，滚轮缩放，右键拖拽平移</li>
                    <li>· 点画框打开图库换画；点门扇开关门</li>
                    <li>· 布展模式：从器物库拖入场景，点选落位，右键删除</li>
                    <li>· 视角里的「第一人称」：点击画面锁定鼠标，Esc 解锁</li>
                    <li>· 灵宠探索：W/S 前后、A/D 转向、Shift 小跑、E 看展品、V 切视角、Esc 退出</li>
                    <li>· 右上「建筑」可切换经典展馆 / 华章新馆，两馆布展各自保存</li>
                    <li>· 沉浸模式用 Esc 或右上角按钮退出</li>
                  </ul>
                  <p className="mt-2 border-t border-[color:var(--color-gold)]/25 px-1 pt-1.5 text-[10px] leading-snug text-[color:var(--color-ink)]/45">
                    灵宠「纹纹」在探索模式菜单里唤出；靠近画框会自动打开文化卡。
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* 左下：三类主入口 + 各自的二级菜单 */}
          <div className="absolute bottom-0 left-0 z-20 p-4 sm:p-6">
            <div className="relative flex flex-col items-start">
              {menu === 'explore' && (
                <div className={`${panelClass} absolute bottom-[calc(100%+8px)] left-0 z-30`}>
                  <MenuLabel>探索模式 · 取景</MenuLabel>
                  {SCENE_MODES.map((item) => {
                    const Icon = item.icon;
                    return (
                      <MenuRow
                        key={item.id}
                        icon={<Icon size={12} />}
                        label={item.label}
                        hint={item.hint}
                        active={mode === item.id}
                        onClick={() => handleSceneMode(item.id)}
                      />
                    );
                  })}
                  <div className="my-1 border-t border-[color:var(--color-gold)]/25" />
                  <MenuLabel>灵宠</MenuLabel>
                  {mascotActive ? (
                    <MenuRow
                      icon={<PawPrint size={12} />}
                      label="退出灵宠探索"
                      hint="回到普通看展视角"
                      active
                      onClick={exitMascot}
                    />
                  ) : (
                    <MenuRow
                      icon={<PawPrint size={12} />}
                      label="唤出灵宠纹纹"
                      hint="进入第一/第三人称探索，靠近画框自动看展"
                      testId="mascot-wake"
                      onClick={wakeMascot}
                    />
                  )}
                </div>
              )}

              {menu === 'curation' && (
                <div className={`${panelClass} absolute bottom-[calc(100%+8px)] left-0 z-30`}>
                  <MenuLabel>布展模式</MenuLabel>
                  <MenuRow
                    icon={<PackageOpen size={12} />}
                    label={`器物库${diyCount > 0 ? ` · 已摆 ${diyCount}` : ''}`}
                    hint="打开右侧器物图库，拖入场景或点选落位"
                    active={panelOpen}
                    onClick={() => {
                      setPanelOpen(!panelOpen);
                      setMode('curation');
                      setMenu(null);
                    }}
                  />
                  <MenuRow
                    icon={<Frame size={12} />}
                    label="画框布展"
                    hint="点场景里的画框，从图库换画"
                    onClick={() => {
                      setMode('curation');
                      setMenu(null);
                    }}
                  />
                  <div className="my-1 border-t border-[color:var(--color-gold)]/25" />
                  <MenuLabel>重置</MenuLabel>
                  <MenuRow
                    icon={<RotateCcw size={12} />}
                    label="重置布展"
                    hint={`只重置${building.name}，另一座馆的布展保留`}
                    onClick={() => {
                      resetAll();
                      setMenu(null);
                    }}
                  />
                  <p className="mt-1 px-1 text-[10px] tabular-nums text-[color:var(--color-ink)]/45">
                    已布展 {placed}/{frames.length}
                  </p>
                </div>
              )}

              {menu === 'view' && (
                <div className={`${panelClass} absolute bottom-[calc(100%+8px)] left-0 z-30`}>
                  <MenuLabel>视角</MenuLabel>
                  <ViewModeSwitch value={viewMode} onChange={handleViewMode} />
                  <div className="my-1.5 border-t border-[color:var(--color-gold)]/25" />
                  <MenuLabel>建筑机位</MenuLabel>
                  <div className="flex flex-wrap gap-1 px-0.5">
                    {exteriorPresets.map((preset) => (
                      <PresetChip
                        key={preset.id}
                        preset={preset}
                        active={presetId === preset.id}
                        onClick={() => handlePreset(preset.id)}
                      />
                    ))}
                  </div>
                  <MenuLabel>室内机位</MenuLabel>
                  <div className="flex flex-wrap gap-1 px-0.5">
                    {interiorPresets.map((preset) => (
                      <PresetChip
                        key={preset.id}
                        preset={preset}
                        active={presetId === preset.id}
                        onClick={() => handlePreset(preset.id)}
                      />
                    ))}
                  </div>
                  <p className="mt-1.5 px-1 text-[10px] leading-snug text-[color:var(--color-ink)]/45">
                    当前：{currentPresetLabel} · {viewLabel}
                  </p>
                </div>
              )}

              {/* 主入口：默认只有这三个 */}
              <div className="pointer-events-auto flex items-center gap-1 rounded-xl border border-[color:var(--color-gold)]/35 bg-[#FBF6EB]/88 p-1 backdrop-blur-md">
                <button
                  type="button"
                  onClick={openExploreMenu}
                  aria-expanded={menu === 'explore'}
                  className={dockButtonClass(mode !== 'curation')}
                >
                  <Compass size={12} />
                  探索模式
                  <ChevronDown size={11} className="opacity-60" />
                </button>
                <button
                  type="button"
                  onClick={() => (menu === 'curation' ? setMenu(null) : enterCuration())}
                  aria-expanded={menu === 'curation'}
                  className={dockButtonClass(mode === 'curation')}
                >
                  <Frame size={12} />
                  布展模式
                  <ChevronDown size={11} className="opacity-60" />
                </button>
                <button
                  type="button"
                  onClick={() => toggleMenu('view')}
                  aria-expanded={menu === 'view'}
                  title={`视角 · ${viewLabel} · 机位 ${currentPresetLabel}`}
                  className={dockButtonClass(menu === 'view')}
                >
                  <Eye size={12} />
                  视角
                  <ChevronDown size={11} className="opacity-60" />
                </button>
              </div>
            </div>
          </div>

          {/* 灵宠探索 HUD：视角统一走「视角」菜单，这里不再单开一套第一/第三人称 */}
          {mascotActive && (
            <div
              data-testid="mascot-hud"
              className="absolute bottom-4 left-1/2 z-30 -translate-x-1/2 rounded-xl border border-[color:var(--color-gold)]/40 bg-[#FBF6EB]/92 px-3 py-2 text-center shadow-lg backdrop-blur-md"
            >
              <div className="flex items-center justify-center gap-2">
                <button
                  type="button"
                  onClick={() => toggleMenu('view')}
                  data-testid="mascot-view-toggle"
                  aria-label={`切换视角（当前${viewLabel}）`}
                  className="inline-flex items-center gap-1.5 rounded border border-[color:var(--color-gold)]/50 px-2.5 py-1 text-[11.5px] text-[color:var(--color-ink)]/75 transition hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]"
                >
                  <Eye size={11} />
                  视角 · {viewLabel}
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
                {building.id === 'classic'
                  ? '后侧折返楼梯可上二层；靠近画框会自动打开对应的文化卡'
                  : '本馆灵宠在地面层探索；靠近画框会自动打开对应的文化卡'}
              </p>
            </div>
          )}

          {/* 右侧图库 */}
          <GalleryPanel
            config={config}
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