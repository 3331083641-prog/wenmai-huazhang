// @ts-nocheck
/**
 * 把 14 件非遗器物接进原有器物库（不新建第二套目录）。
 *
 * 原有 15 件程序化器物仍在 catalog.tsx；这里只追加 'asset' 分类的条目，
 * 并提供 getPropDef() 合并查询，DiYPanel / DiYLayer / diyStore 都用它。
 */

import { useMemo } from 'react';
import * as THREE from 'three';

import { PROP_BUILDERS } from './library.gen';
import { ASSET_DEFS, ASSET_BY_ID, ASSET_GROUP_LABEL, isAssetId } from './assetCatalog';
import { PROP_CATALOG, type PropDef } from '../../scene/props/catalog';

/** 静态预览：只建模型，不挂互动（面板缩略图、落位 ghost 用） */
export function AssetPreview({ assetId }: { assetId: string }) {
  const object = useMemo(() => {
    const build = PROP_BUILDERS[assetId];
    if (!build) return null;
    const root = build();
    const box = new THREE.Box3().setFromObject(root);
    root.position.y = -box.min.y;
    return root;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assetId]);

  if (!object) return null;
  return <primitive object={object} />;
}

/** 开发期审计钩子：逐件构建、量包围盒、数网格，供浏览器端脚本验收 */
if (import.meta.env.DEV && typeof window !== 'undefined') {
  (window as unknown as Record<string, unknown>).__wenmaiAudit = () => {
    const out: Array<Record<string, unknown>> = [];
    for (const def of ASSET_DEFS) {
      const t0 = performance.now();
      try {
        const root = PROP_BUILDERS[def.id]();
        const box = new THREE.Box3().setFromObject(root);
        let meshes = 0;
        let materials = new Set<unknown>();
        let triangles = 0;
        root.traverse((o) => {
          const m = o as THREE.Mesh;
          if (!m.isMesh) return;
          meshes += 1;
          const geo = m.geometry as THREE.BufferGeometry;
          const idx = geo.getIndex();
          const pos = geo.getAttribute('position');
          triangles += idx ? idx.count / 3 : (pos ? pos.count / 3 : 0);
          const mat = m.material as THREE.Material | THREE.Material[];
          for (const item of Array.isArray(mat) ? mat : [mat]) materials.add(item);
        });
        out.push({
          id: def.id, name: def.name, ok: true, ms: Math.round(performance.now() - t0),
          meshes, triangles: Math.round(triangles), materials: materials.size,
          size: [Number((box.max.x - box.min.x).toFixed(3)), Number((box.max.y - box.min.y).toFixed(3)), Number((box.max.z - box.min.z).toFixed(3))],
          y: [Number(box.min.y.toFixed(3)), Number(box.max.y.toFixed(3))],
        });
      } catch (error) {
        out.push({ id: def.id, name: def.name, ok: false, error: String(error) });
      }
    }
    return out;
  };
}

export const ASSET_PROP_ENTRIES: PropDef[] = ASSET_DEFS.map((def) => ({
  id: def.id,
  name: def.name,
  category: 'asset',
  footprint: def.footprint,
  height: def.height,
  // 悬挂件也按 ground 处理：真正决定吸附方式的是 placement，
  // 归到 wall 会被墙面吸附逻辑接管，宫灯就会贴到墙上。
  mount: 'ground',
  placement: def.placement,
  note: def.note,
  Component: () => <AssetPreview assetId={def.id} />,
}));

export const ALL_PROP_CATALOG: PropDef[] = [...PROP_CATALOG, ...ASSET_PROP_ENTRIES];

const ALL_BY_ID = new Map(ALL_PROP_CATALOG.map((def) => [def.id, def]));

export function getPropDef(id: string): PropDef | undefined {
  return ALL_BY_ID.get(id);
}

export { ASSET_DEFS, ASSET_BY_ID, ASSET_GROUP_LABEL, isAssetId };