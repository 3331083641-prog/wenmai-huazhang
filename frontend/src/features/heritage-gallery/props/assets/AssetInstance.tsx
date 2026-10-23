// @ts-nocheck
/**
 * 场景里的单件非遗器物实例。
 *
 * 职责：
 *  1. 按 catalogId 现场构建模型（PROP_BUILDERS），每个实例克隆一份材质，
 *     避免「点亮一盏灯，全场同款一起亮」；
 *  2. 计算真实包围盒，把模型底面对齐到实例原点（落地/落桌面不悬空）；
 *  3. 创建该件的互动控制器，点击触发；编辑模式下点击只选中、不互动；
 *  4. 悬停时把「点击可互动」的提示写进 store。
 */

import { useEffect, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

import { PROP_BUILDERS } from './library.gen';
import { ASSET_BY_ID } from './assetCatalog';
import { createController, type ControllerMode, type PropController } from './interactions';
import { useDiyStore, type DiyItem } from '../../state/diyStore';

const MODE: Record<string, ControllerMode> = {
  DIY_A01: 'generic',
  DIY_A02: 'generic',
  DIY_A04: 'generic',
  DIY_A05: 'glow',
  DIY_A07: 'generic',
  DIY_A09: 'info',
  DIY_B02: 'generic',
  DIY_C02: 'generic',
  DIY_D01: 'generic',
  DIY_D04: 'generic',
  DIY_E01: 'spin',
  DIY_E02: 'generic',
  DIY_E05: 'glow',
  DIY_F05: 'generic',
};

/** 把瓷器瓶身挂到一个以支座顶面为原点的枢轴上，旋转时支座不动 */
function mountVasePivot(root: THREE.Object3D) {
  // React 严格模式下 effect 会跑两次：不幂等就会生成两个同名枢轴，
  // 控制器转到的是前一个空枢轴，瓶身纹丝不动。已存在就直接复用。
  const existing = root.getObjectByName('Vase_Spin_Pivot');
  if (existing) return existing as THREE.Group;
  const names = ['Meiping_Outer_Glaze', 'Meiping_Inner_WhiteGlaze', 'Meiping_Foot_Bisque'];
  const parts = names.map((name) => root.getObjectByName(name)).filter(Boolean) as THREE.Object3D[];
  if (!parts.length) return null;
  const box = new THREE.Box3();
  for (const part of parts) box.expandByObject(part);
  const pivot = new THREE.Group();
  pivot.name = 'Vase_Spin_Pivot';
  pivot.position.set(0, box.min.y, 0);
  root.add(pivot);
  for (const part of parts) {
    const world = part.getWorldPosition(new THREE.Vector3());
    root.remove(part);
    pivot.add(part);
    part.position.copy(root.worldToLocal(world.clone())).sub(pivot.position);
  }
  return pivot;
}

export function AssetInstance({
  item,
  selected,
  editMode,
}: {
  item: DiyItem;
  selected: boolean;
  editMode: boolean;
}) {
  const def = ASSET_BY_ID.get(item.propId);
  const group = useRef<THREE.Group>(null);
  const controller = useRef<PropController | null>(null);
  const downAt = useRef<{ x: number; y: number } | null>(null);

  // 构建模型（每个实例独立一份几何/材质），并把底面对齐到 y=0
  const root = useMemo(() => {
    const build = PROP_BUILDERS[item.propId];
    if (!build) return null;
    const obj = build();
    obj.traverse((child) => {
      const mesh = child as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      if (mesh.material) {
        mesh.material = Array.isArray(mesh.material)
          ? mesh.material.map((m: THREE.Material) => m.clone())
          : (mesh.material as THREE.Material).clone();
      }
    });
    const box = new THREE.Box3().setFromObject(obj);
    obj.position.y = -box.min.y;
    return obj;
  }, [item.propId]);

  useEffect(() => {
    if (!root) return undefined;
    const mode = MODE[item.propId] ?? 'generic';
    let pivotName: string | undefined;
    if (item.propId === 'DIY_E01') {
      const pivot = mountVasePivot(root);
      pivotName = pivot?.name;
    }
    controller.current = createController(item.propId, root, mode, {
      pivotName: pivotName ?? 'Vase_Spin_Pivot',
      infoId: item.propId,
      // 莲花灯点亮时流苏要摆；青花灯只要亮，别整盏打转
      glowMotion: item.propId === 'DIY_A05',
    });
    controller.current.restore(item.interactionState as never);
    return () => {
      controller.current?.dispose();
      controller.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [root, item.propId]);

  // 只有处于互动状态时才推进控制器（静止时不产生任何计算）
  useFrame((_, dt) => {
    controller.current?.update(Math.min(dt, 0.05));
  });

  if (!root || !def) return null;

  return (
    <group
      ref={group}
      onPointerDown={(event) => {
        downAt.current = { x: event.nativeEvent.clientX, y: event.nativeEvent.clientY };
      }}
      onPointerUp={(event) => {
        const start = downAt.current;
        downAt.current = null;
        if (!start) return;
        const moved = Math.hypot(event.nativeEvent.clientX - start.x, event.nativeEvent.clientY - start.y);
        if (moved > 5) return; // 拖动/转场景不算点击
        event.stopPropagation();
        // 编辑态 / 正在取件落位时，点击只选中，不触发互动
        if (editMode || useDiyStore.getState().pendingPropId) {
          useDiyStore.getState().selectItem(item.key);
          return;
        }
        controller.current?.trigger();
        // 互动状态随布展一起保存（灯亮/门开），刷新后按约定恢复
        useDiyStore.getState().updateItem(item.key, {
          interactionState: controller.current?.serialize() ?? null,
        });
      }}
      onContextMenu={(event) => {
        event.stopPropagation();
        (event.nativeEvent as MouseEvent).preventDefault();
        useDiyStore.getState().openContextMenu({
          key: item.key,
          name: def.name,
          x: event.nativeEvent.clientX,
          y: event.nativeEvent.clientY,
        });
      }}
      onPointerOver={() => {
        useDiyStore.getState().setHoverAsset(item.key, def.name);
        document.body.style.cursor = 'pointer';
      }}
      onPointerOut={() => {
        useDiyStore.getState().setHoverAsset(null);
        document.body.style.cursor = '';
      }}
    >
      <primitive object={root} />
      {selected && (
        <mesh position={[0, 0.012, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[Math.max(0.3, def.footprint[0] * 0.62), Math.max(0.34, def.footprint[0] * 0.68), 40]} />
          <meshBasicMaterial color="#C9A15A" transparent opacity={0.9} side={THREE.DoubleSide} depthWrite={false} />
        </mesh>
      )}
    </group>
  );
}