/**
 * 经典展馆 · 第一座建筑皮肤
 *
 * 模型与坐标全部沿用 Blender 导出的 V5 契约，不做任何改动。
 * 这里只是把「一份 layout」包装成「一份可切换的建筑定义」。
 */

import layoutJson from '../data/gallery_layout.json';
import { createGalleryConfig, deriveSceneSpec, type GalleryLayout, type GalleryConfig, type SceneSpec } from './layout';

export const CLASSIC_LAYOUT = layoutJson as unknown as GalleryLayout;

export const classicConfig: GalleryConfig = createGalleryConfig(CLASSIC_LAYOUT);

export const classicScene: SceneSpec = {
  ...deriveSceneSpec(CLASSIC_LAYOUT.envelope),
  // 经典馆模型里删掉过二层楼梯井的两段栏杆，由前端 StairwellRailing 补齐
  stairwellRailing: true,
  mascot: true,
};

/** 经典馆模型文件（与改造前完全一致，避免任何缓存/资源迁移风险） */
export const CLASSIC_MODEL_URL = `${import.meta.env.BASE_URL}models/wenmai_gallery_v5.glb?v=5w`;