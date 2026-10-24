/**
 * 建筑模型：加载、克隆、材质观感与图层分组。
 *
 * 模型来自 Blender（经典馆 `wenmai_gallery_v5.glb`，华章新馆 `wenmai_gallery_huazhang.glb`），
 * 每座建筑各自一份 GLB 与一份 layout 契约。
 *
 * 这里只做四件事：
 *  1. 从 modelCache 取已加载的 GLB 并克隆一份（材质与几何仍然共享，省显存）；
 *  2. 剥掉 GLB 里带进来的相机节点，避免它们参与射线/包围盒计算；
 *  3. 交给观感模块微调材质（scene/lookdev.ts）；
 *  4. 按各自的命名规则分组屋顶，供「外观 / 内部」模式显隐。
 *
 * 坐标、展墙、画框锚点都不在这里读 GLB，而是读各自建筑导出的 layout JSON ——
 * 单一数据源，避免网页和模型各写一套坐标。
 */

import { useMemo } from 'react';
import * as THREE from 'three';

import { applySanzhuan2, disposeToonResources, getOutlineMesh } from './sanzhuan2';
import { applyLookDev } from './lookdev';
import { useBuildingModel } from './modelCache';
import type { BuildingDef } from '../buildings';

// The V5 GLB already carries authored PBR colours. The legacy toon pass
// overwrote them with a near-white ramp and washed the whole hall out, so it is
// switched off until it ramps the GLB base colour instead of replacing it.
const TOON_ENABLED = false;

/** 相机节点前缀：Blender 工作参考，网页用 layout 里的机位 */
const CAMERA_PREFIX = 'CAM_';

export interface GalleryLayers {
  /** 屋顶相关网格，内部模式隐藏 */
  roof: THREE.Object3D[];
  /** 屋顶网格的墨线轮廓，相机进入室内后要隐藏（背面外推壳从内侧看是黑板） */
  roofOutlines: THREE.Mesh[];
  /** 全部可渲染网格，用于统计与调整 */
  meshes: THREE.Mesh[];
}

export interface GalleryAssets {
  /** 建筑定义 id，切换时用来确认「渲染的确实是当前馆」 */
  buildingId: string;
  root: THREE.Group;
  layers: GalleryLayers;
  stats: {
    meshes: number;
    materials: number;
    triangles: number;
    /** 观感表覆盖到的材质份数 */
    lookDevMaterials: number;
    /** 命中观感规则的材质份数 */
    lookDevTweaked: number;
  };
}

/** 按当前建筑的屋顶命名规则判断一个网格是不是屋面 */
export function makeRoofMatcher(building: BuildingDef): (name: string) => boolean {
  const prefixes = building.scene.roof.prefixes;
  const extra = new Set(building.scene.roof.extra);
  return (name: string): boolean => {
    if (!name) return false;
    if (extra.has(name)) return true;
    return prefixes.some((prefix) => name.startsWith(prefix));
  };
}

function prepare(source: THREE.Group, building: BuildingDef): GalleryAssets {
  const root = source.clone(true);
  const roof: THREE.Object3D[] = [];
  const meshes: THREE.Mesh[] = [];
  const cameras: THREE.Object3D[] = [];
  const isRoofPart = makeRoofMatcher(building);

  root.traverse((object) => {
    if ((object as THREE.Camera).isCamera || object.name.startsWith(CAMERA_PREFIX)) {
      cameras.push(object);
      return;
    }
    if (!(object as THREE.Mesh).isMesh) return;
    const mesh = object as THREE.Mesh;
    meshes.push(mesh);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    if (isRoofPart(mesh.name)) roof.push(mesh);
  });

  // 相机节点只是 Blender 的工作参考，网页里用布局 JSON 的机位
  for (const camera of cameras) camera.removeFromParent();

  const result = TOON_ENABLED ? applySanzhuan2(root) : { materials: 0 };
  // 观感（走 GLB 自带的 PBR 材质）：暖木/石材/铜/朱红/纸感逐材质微调，
  // 不新增材质、不改几何，参数表在 scene/lookdev.ts。
  const lookDev = applyLookDev(root);

  const roofOutlines = roof
    .map((object) => getOutlineMesh(object as THREE.Mesh))
    .filter((mesh): mesh is THREE.Mesh => Boolean(mesh));

  let triangles = 0;
  for (const mesh of meshes) {
    const geometry = mesh.geometry as THREE.BufferGeometry;
    const index = geometry.getIndex();
    const position = geometry.getAttribute('position');
    if (index) triangles += index.count / 3;
    else if (position) triangles += position.count / 3;
  }

  return {
    buildingId: building.id,
    root,
    layers: { roof, roofOutlines, meshes },
    stats: {
      meshes: meshes.length,
      materials: result.materials,
      triangles: Math.round(triangles),
      lookDevMaterials: lookDev.materials,
      lookDevTweaked: lookDev.tweaked,
    },
  };
}

/**
 * 加载并准备好一座建筑的模型。
 *
 * 返回 null 表示模型还没下载完——调用方据此显示加载态，
 * 而不是把一个空场景当成「已经加载好」。
 */
export function useBuildingAssets(building: BuildingDef): GalleryAssets | null {
  const gltf = useBuildingModel(building.modelUrl);
  return useMemo(() => {
    if (!gltf) return null;
    return prepare(gltf.scene as THREE.Group, building);
  }, [gltf, building]);
}

/** 卸载时释放三渲二模块里缓存的材质与渐变贴图 */
export function releaseGalleryAssets(): void {
  disposeToonResources();
}