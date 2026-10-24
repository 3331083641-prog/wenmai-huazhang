/**
 * 华章新馆 · 第二座建筑皮肤（本轮新建）
 *
 * 与经典馆完全独立：
 *  - 独立的 GLB（`public/models/wenmai_gallery_huazhang.glb`）
 *  - 独立的 layout（`buildings/layouts/huazhang_layout.json`，schema 2）
 *  - 独立的场景尺寸参数（更高、更宽，楼梯井护栏由模型自带）
 *
 * layout 由 `assets/gallery3d/scripts/v6/build_huazhang.py` 从 .blend 直接导出，
 * 前端不手写任何建筑坐标。
 */

import layoutJson from './layouts/huazhang_layout.json';
import { createGalleryConfig, deriveSceneSpec, type GalleryLayout, type GalleryConfig, type SceneSpec } from './layout';

export const HUAZHANG_LAYOUT = layoutJson as unknown as GalleryLayout;

export const huazhangConfig: GalleryConfig = createGalleryConfig(HUAZHANG_LAYOUT, {
  // 24 个画框：每 6 个留一个空框，给 DIY 留出呼吸感，也不至于整面墙全空
  emptyEvery: 6,
  // 新馆中庭通高，梁架机位也在室内，一并收起屋顶
  interiorPresets: ['floor1', 'floor2', 'ceiling'],
  hideRoofPresets: ['floor1', 'floor2'],
});

export const huazhangScene: SceneSpec = {
  ...deriveSceneSpec(HUAZHANG_LAYOUT.envelope),
  // 新馆的楼梯井护栏是模型里真实建出来的，前端不再补画
  stairwellRailing: false,
  mascot: true,
};

export const HUAZHANG_MODEL_URL = `${import.meta.env.BASE_URL}models/wenmai_gallery_huazhang.glb?v=1`;