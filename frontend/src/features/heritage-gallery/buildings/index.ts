/**
 * 建筑皮肤注册表
 *
 * 加第三座、第四座展馆时只需要：
 *  1. 新建 `xxx.ts`，导出 layout / config / scene / modelUrl；
 *  2. 在下面的 BUILDINGS 里追加一条；
 *  3. 把 GLB 放进 `public/models/`。
 * 场景、状态、面板、切换 UI 全部自动适配，不需要改组件。
 */

import type { GalleryConfig, GalleryLayout, SceneSpec } from './layout';
import { CLASSIC_LAYOUT, CLASSIC_MODEL_URL, classicConfig, classicScene } from './classic';
import { HUAZHANG_LAYOUT, HUAZHANG_MODEL_URL, huazhangConfig, huazhangScene } from './huazhang';

export type BuildingId = string;

export interface BuildingPreview {
  /** 卡片主渐变的两端颜色 */
  from: string;
  to: string;
  /** 缩略图里天空/背景的底色 */
  sky: string;
  /** 建筑剪影的填充色 */
  ink: string;
}

export interface BuildingDef {
  id: BuildingId;
  /** 完整名称（切换面板标题） */
  name: string;
  /** 短名（按钮上的文字） */
  shortName: string;
  /** 一句话定位 */
  tagline: string;
  /** 面板里的说明 */
  description: string;
  /** 未加载时的占位描述，也用于加载遮罩 */
  loadingLabel: string;
  modelUrl: string;
  layout: GalleryLayout;
  config: GalleryConfig;
  scene: SceneSpec;
  preview: BuildingPreview;
}

export const BUILDINGS: BuildingDef[] = [
  {
    id: 'classic',
    name: '经典展馆',
    shortName: '经典',
    tagline: '重檐古建 · 两层微缩',
    description: '最初建成的两层展馆，木作、瓦面与檐下细节一应俱全。',
    loadingLabel: '正在载入经典展馆',
    modelUrl: CLASSIC_MODEL_URL,
    layout: CLASSIC_LAYOUT,
    config: classicConfig,
    scene: classicScene,
    preview: { from: '#8a7a63', to: '#cfc0a5', sky: '#bfd9e8', ink: '#3f342a' },
  },
  {
    id: 'huazhang',
    name: '华章新馆',
    shortName: '华章',
    tagline: '重檐庑殿 · 通高中庭',
    description: '新设计的美术馆：通高中庭、采光天窗、双层展廊与完整陈设。',
    loadingLabel: '正在载入华章新馆',
    modelUrl: HUAZHANG_MODEL_URL,
    layout: HUAZHANG_LAYOUT,
    config: huazhangConfig,
    scene: huazhangScene,
    preview: { from: '#3f5f5c', to: '#c9a96a', sky: '#c9dce6', ink: '#22302f' },
  },
];

export const DEFAULT_BUILDING_ID: BuildingId = 'classic';

const BUILDING_MAP = new Map<string, BuildingDef>(BUILDINGS.map((def) => [def.id, def]));

/** 取建筑定义；未知 id 回退到默认馆，绝不让页面因为脏持久化数据白屏 */
export function getBuilding(id: string | null | undefined): BuildingDef {
  if (id && BUILDING_MAP.has(id)) return BUILDING_MAP.get(id) as BuildingDef;
  return BUILDING_MAP.get(DEFAULT_BUILDING_ID) as BuildingDef;
}

export function isKnownBuilding(id: string | null | undefined): boolean {
  return Boolean(id && BUILDING_MAP.has(id));
}

export type { GalleryConfig, GalleryLayout, SceneSpec };