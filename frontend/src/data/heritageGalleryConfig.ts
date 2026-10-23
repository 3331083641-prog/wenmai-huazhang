/**
 * 纹脉展馆 · 场景契约（由 Blender 导出，不要手写坐标）
 *
 * 数据来源：`assets/gallery3d/exports/gallery_layout.json`
 * 生成脚本：`assets/gallery3d/scripts/export_layout.py`
 *
 * 为什么不再手写常量：
 *  展墙位置、画框锚点、机位全部来自 .blend 里真实的物体变换，
 *  模型改一版，这里跟着重新导出即可，不会出现「网页里的墙和模型里的墙差 6cm」。
 *
 * 坐标系：three.js（Y 向上）。导出脚本已把 Blender 的 Z-up 转成 (x, z, -y)。
 *  rotationY 约定：法线 = (sin(rotY), 0, cos(rotY))，即画框默认朝 +Z 时 rotY = 0。
 */

import type { CameraPreset, FrameSlot, GalleryWall } from '../features/heritage-gallery/types';
import { galleryArtworks } from './galleryArtworks';
import layoutJson from '../features/heritage-gallery/data/gallery_layout.json';

interface LayoutWall {
  id: string;
  floor: 1 | 2;
  center: [number, number, number];
  rotationY: number;
  size: [number, number];
  capacity: number;
  label: string;
}

interface LayoutFrame {
  id: string;
  floor: 1 | 2;
  index: number;
  position: [number, number, number];
  rotationY: number;
  group: string;
  size: [number, number];
  wallId: string;
  u: number;
  v: number;
  label: string;
}

interface LayoutCamera {
  id: string;
  position: [number, number, number];
  target: [number, number, number];
  lens: number;
  fov: number;
}

interface Layout {
  envelope: {
    min: [number, number, number];
    max: [number, number, number];
    baseSize: number;
    baseThickness: number;
    floor1Height: number;
    floor2Height: number;
    topZ: number;
    footprintX: number;
    footprintZ: number;
  };
  walls: LayoutWall[];
  frames: LayoutFrame[];
  cameras: LayoutCamera[];
}

const layout = layoutJson as unknown as Layout;

/* ------------------------------------------------------------------ 尺寸 */

export const BASE_SIZE = layout.envelope.baseSize;
export const BASE_THICKNESS = layout.envelope.baseThickness;
export const FLOOR_HEIGHT = layout.envelope.floor1Height;
export const FLOOR2_HEIGHT = layout.envelope.floor2Height;
export const FOOTPRINT_X = layout.envelope.footprintX;
export const FOOTPRINT_Z = layout.envelope.footprintZ;
export const WALL_THICKNESS = 0.16;
export const TOP_Z = layout.envelope.topZ;
export const MODEL_BOUNDS = {
  min: layout.envelope.min,
  max: layout.envelope.max,
};

/* ------------------------------------------------------------------ 展墙 */

export const galleryWalls: GalleryWall[] = layout.walls.map((wall) => ({
  id: wall.id,
  floor: wall.floor,
  center: wall.center,
  rotationY: wall.rotationY,
  size: wall.size,
  capacity: wall.capacity ?? Math.max(1, Math.floor(wall.size[0] / 1.05)),
  label: wall.label,
}));

export const wallById = new Map(galleryWalls.map((wall) => [wall.id, wall]));

/* ------------------------------------------------------------------ 画框 */

/** 画面与外框的比值：玻璃/卡纸留边，画面略小于外框 */
export const FRAME_IMAGE_RATIO = 0.74;

/**
 * 默认挂画：按「真实案例」的顺序轮转，绝不硬编码不存在的作品 id。
 * 空字符串表示留白画框（布展时由用户自己挑）。
 */
function defaultArtworkFor(index: number, total: number): string {
  if (galleryArtworks.length === 0) return '';
  // 15 个框、案例数量通常更少，按顺序循环并让每 5 个框留一个空框
  if (index % 5 === 4) return '';
  const artwork = galleryArtworks[index % galleryArtworks.length];
  return artwork ? artwork.id : '';
}

export const frameSlots: FrameSlot[] = layout.frames.map((frame, i) => ({
  id: frame.id,
  wallId: frame.wallId,
  u: frame.u,
  v: frame.v,
  size: frame.size,
  defaultArtworkId: defaultArtworkFor(i, layout.frames.length),
}));

export const frameById = new Map(frameSlots.map((frame) => [frame.id, frame]));

/** 画框的绝对变换（不做拖拽偏移时用） */
export const frameAnchors: Record<
  string,
  { position: [number, number, number]; rotationY: number; floor: 1 | 2; label: string }
> = Object.fromEntries(
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

export function framesOfWall(wallId: string): FrameSlot[] {
  return frameSlots.filter((frame) => frame.wallId === wallId);
}

/* ------------------------------------------------------------------ 机位 */

const cameraById = new Map(layout.cameras.map((camera) => [camera.id, camera]));

function preset(
  id: string,
  label: string,
  source: string,
  fallback?: Partial<CameraPreset>,
): CameraPreset {
  const camera = cameraById.get(source);
  return {
    id,
    label,
    position: camera ? camera.position : (fallback?.position ?? [20, 12, -20]),
    target: camera ? camera.target : (fallback?.target ?? [0, 4.4, 0]),
    fov: camera ? camera.fov : (fallback?.fov ?? 42),
  };
}

/** 预设机位：外观 + 正/背/左/右 + 俯视 + 一层/二层 + 梁架 + 檐下 */
export const cameraPresets: CameraPreset[] = [
  preset('exterior', '外观', 'front34'),
  preset('front', '正面', 'front'),
  preset('back', '背面', 'back'),
  preset('left', '左侧', 'left'),
  preset('right', '右侧', 'right'),
  preset('top', '俯视', 'top'),
  preset('floor1', '一层', 'f1'),
  preset('floor2', '二层', 'f2'),
  preset('ceiling', '梁架', 'ceiling'),
  preset('eave', '檐下', 'eave'),
];

export const presetById = new Map(cameraPresets.map((preset) => [preset.id, preset]));

/** 只在室内拍摄的机位：切到这些机位时自动进入内部模式（隐藏屋顶） */
export const INTERIOR_PRESETS = new Set(['floor1', 'floor2', 'ceiling']);

/**
 * 需要临时收起屋顶的机位。
 * 只有「在房间里看」的一层/二层要收屋顶；梁架与檐下看的正是屋顶本身。
 */
export const HIDE_ROOF_PRESETS = new Set(['floor1', 'floor2']);

/* ------------------------------------------------------------------ 换算 */

/** 局部坐标 → 世界坐标（墙面自身坐标系） */
export function wallPointToWorld(
  wall: GalleryWall,
  u: number,
  v: number,
  offset = 0.05,
): [number, number, number] {
  const localX = (u - 0.5) * wall.size[0];
  const localY = (v - 0.5) * wall.size[1];
  const cos = Math.cos(wall.rotationY);
  const sin = Math.sin(wall.rotationY);
  // 墙面法线方向（朝向房间）：rotationY = 0 时为 +Z
  const normalX = sin;
  const normalZ = cos;
  return [
    wall.center[0] + localX * cos + normalX * offset,
    wall.center[1] + localY,
    wall.center[2] - localX * sin + normalZ * offset,
  ];
}

/** 把归一化坐标夹到墙面允许范围，避免画框贴边或越界 */
export function clampToWall(
  wall: GalleryWall,
  size: [number, number],
  u: number,
  v: number,
): { u: number; v: number } {
  const marginU = size[0] / 2 / wall.size[0];
  const marginV = size[1] / 2 / wall.size[1];
  const minU = marginU + 0.01;
  const maxU = 1 - marginU - 0.01;
  const minV = marginV + 0.01;
  const maxV = 1 - marginV - 0.01;
  return {
    u: Math.min(Math.max(u, minU), maxU),
    v: Math.min(Math.max(v, minV), maxV),
  };
}