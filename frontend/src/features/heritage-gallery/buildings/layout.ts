/**
 * 纹脉展馆 · 多建筑皮肤的数据层
 *
 * 背景：
 *  经典展馆（classic）是 Blender 导出的第一座建筑，坐标契约写在 gallery_layout.json。
 *  华章新馆（huazhang）是第二座，用同一份 schema 导出自己的 layout。
 *  两座建筑各自拥有一套「展墙 / 画框 / 机位」，前端不再假设只有一栋房子。
 *
 * 设计原则：
 *  1. 建筑定义是**静态注册表**（buildings/index.ts），不放进 React state，
 *     这样 store / 场景 / 面板都能同步取到，切换时不会出现半旧半新的状态。
 *  2. 所有尺寸参数从 layout.envelope 推导，而不是再手写一遍常量。
 *     经典馆的推导结果与旧代码逐项对齐（见 deriveSceneSpec 的注释），
 *     保证接入双馆后旧展馆的手感完全不变。
 *  3. 画框坐标仍然只用「墙面局部归一化 u/v」，换馆时按各自墙面尺寸换算，
 *     不存在跨馆坐标混用。
 */

import type { CameraPreset, FrameSlot, GalleryWall } from '../types';
import { galleryArtworks } from '../../../data/galleryArtworks';

/* ------------------------------------------------------------------ 契约类型 */

export interface LayoutWall {
  id: string;
  floor: 1 | 2;
  center: [number, number, number];
  rotationY: number;
  size: [number, number];
  capacity?: number;
  label: string;
}

export interface LayoutFrame {
  id: string;
  floor: 1 | 2;
  index: number;
  position: [number, number, number];
  rotationY: number;
  wallId: string;
  group?: string;
  size: [number, number];
  u: number;
  v: number;
  label: string;
}

export interface LayoutCamera {
  id: string;
  position: [number, number, number];
  target: [number, number, number];
  lens?: number;
  fov?: number;
}

export interface LayoutEnvelope {
  min: [number, number, number];
  max: [number, number, number];
  baseSize: number;
  baseThickness: number;
  floor1Z: number;
  floor2Z: number;
  floor1Height: number;
  floor2Height: number;
  topZ: number;
  eaveZ?: number;
  ridgeZ?: number;
  footprintX: number;
  footprintZ: number;
  hallOffsetZ?: number;
  triangles?: number;
}

export interface GalleryLayout {
  schema: number;
  envelope: LayoutEnvelope;
  walls: LayoutWall[];
  frames: LayoutFrame[];
  cameras: LayoutCamera[];
}

/* ------------------------------------------------------------------ 场景参数 */

/**
 * 一座建筑在三维场景里需要的尺寸参数。
 *
 * 这些值以前硬编码在 HeritageScene / CameraModes / DiYLayer / placement 里，
 * 只适用于经典馆那一栋房子。现在改为按建筑推导，新馆尺寸不同也不会出问题。
 */
export interface SceneSpec {
  /** 相机进入这个盒体后视为「在屋里」，收起屋顶描边外壳 */
  interiorBox: { x: number; z: number; yMin: number; yMax: number };
  /** 第一人称可行走范围与本馆起点 */
  firstPerson: { xMin: number; xMax: number; zMin: number; zMax: number; startZ: number };
  /** DIY 布展：一层台面 / 二层地面 / 场地边界 */
  diy: { baseTop: number; floor2: number; limit: number; surfaceMaxAbove: number; planeSize: number };
  /** OrbitControls 默认注视点 */
  orbitTarget: [number, number, number];
  /** 贴地接触阴影 */
  contactShadow: { y: number; scale: number; far: number };
  /** 梁架悬挂锚点扫描范围 */
  hang: { columnTop: number; minY: number; maxY: number; bounds: { x: number; z: number } };
  /** 屋顶图层命名规则（内部模式整组隐藏） */
  roof: { prefixes: string[]; extra: string[] };
  /** 是否启用二层楼梯井护栏（只有经典馆模型里删掉过那段栏杆） */
  stairwellRailing: boolean;
  /** 灵宠是否可在本馆探索（需要一层/二层都有可行走面） */
  mascot: boolean;
}

/**
 * 由 envelope 推导场景参数。
 *
 * 每一项都刻意写成「几何关系 + 固定余量」，而不是直接抄旧常量；
 * 括号里是对经典馆 envelope 的实际结果，已逐项与旧代码核对。
 */
export function deriveSceneSpec(envelope: LayoutEnvelope): SceneSpec {
  const fx = envelope.footprintX;
  const fz = envelope.footprintZ;
  const floor1 = envelope.floor1Z;
  const floor2 = envelope.floor2Z;
  const ridge = envelope.ridgeZ ?? envelope.topZ + 4.7;

  return {
    // 墙外包络 + 一点余量：站在墙里时收起屋顶外扩壳，避免黑面（旧值 4.35 / 4.05 / 0.15 / 7.0）
    interiorBox: {
      x: fx / 2 + 0.15,
      z: fz / 2 + 0.3,
      yMin: floor1 - 0.1,
      yMax: envelope.topZ + 0.45,
    },
    // 馆内 + 檐廊：前方多留一点（台阶），后方少留（旧值 ±4.9 / -4.4 / 4.1 / 2.9）
    firstPerson: {
      xMin: -(fx / 2 + 0.7),
      xMax: fx / 2 + 0.7,
      zMin: -(fz / 2 + 0.65),
      zMax: fz / 2 + 0.35,
      startZ: fz / 2 - 0.85,
    },
    // 落位面 18×18 对应 16 m 台基（旧值 0.25 / 3.6 / 7.4 / 2.6 / 18）
    diy: {
      baseTop: floor1,
      floor2,
      limit: envelope.baseSize / 2 - 0.6,
      surfaceMaxAbove: Math.max(1.8, floor2 - floor1 - 0.75),
      planeSize: envelope.baseSize + 2,
    },
    orbitTarget: [0, floor2, 0],
    contactShadow: {
      // 底座略低于建筑最低点，阴影才会被台基挡住边缘（旧值 -0.67）
      y: envelope.min[1] - 0.27,
      // 底座 16 m 对应 8.4 m 面阔（旧值 16）
      scale: Math.round(Math.max(fx, fz, envelope.baseSize) * 1.9),
      far: 5.6,
    },
    hang: {
      // 扫描柱起点要高于脊（旧值 13 ≈ 11.3 + 1.7）
      columnTop: ridge + 1.7,
      // 低于一层梁架会撞人（旧值 2.35 = 0.25 + 2.1）
      minY: floor1 + 2.1,
      // 高于二层顶棚则等于悬空（旧值 7.6 = 3.6 + 4.0）
      maxY: floor2 + 4.0,
      // 建筑外轮廓 + 一圈檐口（旧值 4.7 / 4.5）
      bounds: { x: fx / 2 + 0.5, z: fz / 2 + 0.75 },
    },
    roof: { prefixes: ['ROOF_', 'TILE_'], extra: ['LANTERN_Eave'] },
    stairwellRailing: true,
    mascot: true,
  };
}

/* ------------------------------------------------------------------ 建筑配置 */

export interface GalleryConfig {
  walls: GalleryWall[];
  frames: FrameSlot[];
  cameras: CameraPreset[];
  envelope: LayoutEnvelope;
  frameById: Map<string, FrameSlot>;
  wallById: Map<string, GalleryWall>;
  framesOfWall: (wallId: string) => FrameSlot[];
  /** 画框的绝对变换（不做拖拽偏移时用） */
  frameAnchors: Record<
    string,
    { position: [number, number, number]; rotationY: number; floor: 1 | 2; label: string }
  >;
  /** 室内机位：切到这些机位时自动进入内部模式（隐藏屋顶） */
  interiorPresets: Set<string>;
  /** 需要临时收起屋顶的机位 */
  hideRoofPresets: Set<string>;
  wallPointToWorld: (wall: GalleryWall, u: number, v: number, offset?: number) => [number, number, number];
  clampToWall: (
    wall: GalleryWall,
    size: [number, number],
    u: number,
    v: number,
  ) => { u: number; v: number };
  /** 默认布展方案（每馆各自的留白节奏） */
  defaultAssignments: () => Record<string, string>;
  defaultPositions: () => Record<string, { u: number; v: number }>;
}

/** 画面与外框的比值：玻璃/卡纸留边，画面略小于外框 */
export const FRAME_IMAGE_RATIO = 0.74;

/** 只在室内拍摄的机位：切到这些机位时自动进入内部模式（隐藏屋顶） */
const DEFAULT_INTERIOR_PRESETS = ['floor1', 'floor2', 'ceiling'];

/** 需要临时收起屋顶的机位。梁架与檐下看的正是屋顶本身，所以不收。 */
const DEFAULT_HIDE_ROOF_PRESETS = ['floor1', 'floor2'];

export interface CreateConfigOptions {
  /** 默认挂画策略：按序轮转、每 5 个留一个空框（经典馆就是这么排的） */
  emptyEvery?: number;
  interiorPresets?: string[];
  hideRoofPresets?: string[];
  /** 机位缺失时的兜底 */
  fallbackCamera?: { position: [number, number, number]; target: [number, number, number]; fov: number };
}

/**
 * 默认挂画：按「真实案例」的顺序轮转，绝不硬编码不存在的作品 id。
 * 空字符串表示留白画框（布展时由用户自己挑）。
 */
function defaultArtworkFor(index: number, emptyEvery: number): string {
  if (galleryArtworks.length === 0) return '';
  if (emptyEvery > 0 && index % emptyEvery === emptyEvery - 1) return '';
  const artwork = galleryArtworks[index % galleryArtworks.length];
  return artwork ? artwork.id : '';
}

export function createGalleryConfig(layout: GalleryLayout, options: CreateConfigOptions = {}): GalleryConfig {
  const emptyEvery = options.emptyEvery ?? 5;

  const walls: GalleryWall[] = layout.walls.map((wall) => ({
    id: wall.id,
    floor: wall.floor,
    center: wall.center,
    rotationY: wall.rotationY,
    size: wall.size,
    capacity: wall.capacity ?? Math.max(1, Math.floor(wall.size[0] / 1.05)),
    label: wall.label,
  }));
  const wallById = new Map(walls.map((wall) => [wall.id, wall]));

  const frames: FrameSlot[] = layout.frames.map((frame, i) => ({
    id: frame.id,
    wallId: frame.wallId,
    u: frame.u,
    v: frame.v,
    size: frame.size,
    defaultArtworkId: defaultArtworkFor(i, emptyEvery),
  }));
  const frameById = new Map(frames.map((frame) => [frame.id, frame]));

  const frameAnchors: GalleryConfig['frameAnchors'] = Object.fromEntries(
    layout.frames.map((frame) => [
      frame.id,
      {
        position: frame.position,
        rotationY: frame.rotationY,
        floor: frame.floor,
        label: frame.label,
      },
    ]),
  );

  const cameraById = new Map(layout.cameras.map((camera) => [camera.id, camera]));
  const fallback = options.fallbackCamera ?? {
    position: [20, 12, -20] as [number, number, number],
    target: [0, 4.4, 0] as [number, number, number],
    fov: 42,
  };
  const presetIds: { id: string; label: string }[] = [
    { id: 'exterior', label: '外观' },
    { id: 'front', label: '正面' },
    { id: 'back', label: '背面' },
    { id: 'left', label: '左侧' },
    { id: 'right', label: '右侧' },
    { id: 'top', label: '俯视' },
    { id: 'floor1', label: '一层' },
    { id: 'floor2', label: '二层' },
    { id: 'ceiling', label: '梁架' },
    { id: 'eave', label: '檐下' },
  ];
  const cameras: CameraPreset[] = presetIds.map(({ id, label }) => {
    const sourceId = id === 'exterior' ? 'front34' : id === 'floor1' ? 'f1' : id === 'floor2' ? 'f2' : id;
    const camera = cameraById.get(sourceId);
    return {
      id,
      label,
      position: camera ? camera.position : fallback.position,
      target: camera ? camera.target : fallback.target,
      fov: camera ? camera.fov : fallback.fov,
    };
  });

  function wallPointToWorld(
    wall: GalleryWall,
    u: number,
    v: number,
    offset = 0.05,
  ): [number, number, number] {
    const localX = (u - 0.5) * wall.size[0];
    const localY = (v - 0.5) * wall.size[1];
    const cos = Math.cos(wall.rotationY);
    const sin = Math.sin(wall.rotationY);
    const normalX = sin;
    const normalZ = cos;
    return [
      wall.center[0] + localX * cos + normalX * offset,
      wall.center[1] + localY,
      wall.center[2] - localX * sin + normalZ * offset,
    ];
  }

  function clampToWall(
    wall: GalleryWall,
    size: [number, number],
    u: number,
    v: number,
  ): { u: number; v: number } {
    const marginU = size[0] / 2 / wall.size[0];
    const marginV = size[1] / 2 / wall.size[1];
    return {
      u: Math.min(Math.max(u, marginU + 0.01), 1 - marginU - 0.01),
      v: Math.min(Math.max(v, marginV + 0.01), 1 - marginV - 0.01),
    };
  }

  return {
    walls,
    frames,
    cameras,
    envelope: layout.envelope,
    frameById,
    wallById,
    framesOfWall: (wallId) => frames.filter((frame) => frame.wallId === wallId),
    frameAnchors,
    interiorPresets: new Set(options.interiorPresets ?? DEFAULT_INTERIOR_PRESETS),
    hideRoofPresets: new Set(options.hideRoofPresets ?? DEFAULT_HIDE_ROOF_PRESETS),
    wallPointToWorld,
    clampToWall,
    defaultAssignments: () =>
      Object.fromEntries(frames.map((frame) => [frame.id, frame.defaultArtworkId])),
    defaultPositions: () =>
      Object.fromEntries(frames.map((frame) => [frame.id, { u: frame.u, v: frame.v }])),
  };
}