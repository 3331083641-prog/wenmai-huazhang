/**
 * DIY 器物层：摆放、拖动、选中、屋顶换瓦色。
 *
 * 交互约定：
 *  - 面板里点/拖一件器物 -> pendingPropId；在场景里点一下落位（带落位预览）。
 *  - 已摆好的器物可直接拖动；点空白处取消选中。
 *  - placement 决定落位方式：
 *      floor   落在落位面（一层台面 / 二层回廊）
 *      surface 吸附到已摆器物 / 展柜 / 模型台面的顶面，并记录 parentInstanceId
 *      hang    吸附到梁架锚点，没有锚点直接拒绝，不允许悬空
 *  - 屋顶瓦色只替换 tile / tile_d 两种材质，其余材质不动。
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

import { PROP_COLORS } from './props/catalog';
import { AssetInstance } from '../props/assets/AssetInstance';
import { AssetPreview, getPropDef, isAssetId } from '../props/assets/assetProps';
import { ASSET_BY_ID } from '../props/assets/assetCatalog';
import { ROOF_TINTS, useDiyItems, useDiyStore, useRoofTint } from '../state/diyStore';
import {
  findHangTarget,
  findNearbyItemTop,
  findSurfaceTarget,
  HANG_HINT,
  SURFACE_HINT,
  type SurfaceTarget,
} from './placement';
import type { SceneSpec } from '../buildings';

const SNAP_PX = 56;

type PlacementKind = 'floor' | 'surface' | 'hang';

interface Placed {
  x: number;
  y: number;
  z: number;
  parentInstanceId?: string;
  carrier?: string;
  surfaceId?: string;
}

interface DiYLayerProps {
  enabled: boolean;
  /** 1 = 台面/一层；2 = 二层回廊 */
  level: number;
  /** 模型网格，用于墙面吸附与梁架锚点 */
  wallMeshes: THREE.Object3D[];
  roofMeshes: THREE.Object3D[];
  /** 当前建筑的尺寸参数（台面标高、场地边界、悬挂范围） */
  spec: SceneSpec;
  onDragStateChange: (dragging: boolean) => void;
}

function placementOf(propId: string): PlacementKind {
  return getPropDef(propId)?.placement ?? 'floor';
}

/** 悬挂件按目录高度挂到梁下：包围盒高度与目录高度的差值在厘米级 */
function hangHeightOf(propId: string): number {
  return ASSET_BY_ID.get(propId)?.height ?? getPropDef(propId)?.height ?? 0.9;
}

export function DiYLayer({ enabled, level, wallMeshes, roofMeshes, spec, onDragStateChange }: DiYLayerProps) {
  const items = useDiyItems();
  const selectedKey = useDiyStore((state) => state.selectedKey);
  const pendingPropId = useDiyStore((state) => state.pendingPropId);
  const roofTint = useRoofTint();
  const addItem = useDiyStore((state) => state.addItem);
  const updateItem = useDiyStore((state) => state.updateItem);
  const selectItem = useDiyStore((state) => state.selectItem);
  const setPending = useDiyStore((state) => state.setPending);
  const editMode = useDiyStore((state) => state.editMode);

  const BASE_TOP = spec.diy.baseTop;
  const FLOOR2 = spec.diy.floor2;
  const LIMIT = spec.diy.limit;
  const SURFACE_MAX_ABOVE = spec.diy.surfaceMaxAbove;
  const PLANE_SIZE = spec.diy.planeSize;

  const planeY = level === 2 ? FLOOR2 : BASE_TOP;
  const [ghost, setGhost] = useState<{ x: number; y: number; z: number } | null>(null);
  const dragRef = useRef<{ key: string; dx: number; dz: number; planeY: number } | null>(null);
  const placedRef = useRef<THREE.Group>(null);
  const { camera, gl, raycaster, size } = useThree();

  const pending = pendingPropId ? getPropDef(pendingPropId) : undefined;
  const pendingIsWall = pending?.mount === 'wall';
  const pendingKind: PlacementKind = pendingPropId ? placementOf(pendingPropId) : 'floor';

  const roofSet = useMemo(() => new Set<THREE.Object3D>(roofMeshes), [roofMeshes]);

  /* ---------------------------------------------------------- 屋顶瓦色 */
  const tintedRef = useRef(new Map<string, THREE.MeshStandardMaterial>());
  useEffect(() => {
    const tint = ROOF_TINTS.find((entry) => entry.id === roofTint)?.color ?? '#3D4B51';
    const base = new THREE.Color(tint);
    const dark = base.clone().multiplyScalar(0.74);
    for (const object of roofMeshes) {
      const mesh = object as THREE.Mesh;
      const raw = mesh.material as THREE.Material | THREE.Material[];
      const list = Array.isArray(raw) ? raw : [raw];
      const next = list.map((material) => {
        const name = material?.name ?? '';
        if (!/tile/i.test(name)) return material;
        const cache = tintedRef.current;
        let clone = cache.get(material.uuid);
        if (!clone) {
          clone = (material as THREE.MeshStandardMaterial).clone();
          cache.set(material.uuid, clone);
        }
        clone.color.copy(/tile_d/i.test(name) ? dark : base);
        clone.needsUpdate = true;
        return clone;
      });
      mesh.material = Array.isArray(raw) ? next : next[0];
    }
  }, [roofTint, roofMeshes]);

  /* ---------------------------------------------------------- 墙面吸附 */
  const hitWall = (ray: THREE.Ray): { point: THREE.Vector3; normal: THREE.Vector3 } | null => {
    if (!wallMeshes.length) return null;
    const probe = new THREE.Raycaster();
    probe.ray.copy(ray);
    const hits = probe.intersectObjects(wallMeshes, true);
    for (const hit of hits) {
      if (!hit.face) continue;
      const normal = hit.face.normal.clone()
        .applyNormalMatrix(new THREE.Matrix3().getNormalMatrix(hit.object.matrixWorld))
        .normalize();
      if (Math.abs(normal.y) > 0.55) continue;
      if (hit.distance > 30) continue;
      return { point: hit.point.clone(), normal };
    }
    return null;
  };

  const handleWallClick = useCallback(
    (ray: THREE.Ray) => {
      if (!pendingPropId) return false;
      const hit = hitWall(ray);
      if (!hit) return false;
      const normal = hit.normal;
      const rotY = Math.atan2(normal.x, normal.z);
      const item = buildItem(
        pendingPropId,
        hit.point.x + normal.x * 0.06,
        hit.point.y,
        hit.point.z + normal.z * 0.06,
        rotY,
      );
      if (item) addItem(item);
      return true;
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [pendingPropId, addItem],
  );

  /* ---------------------------------------------------------- 落位求解 */
  const clamp = (value: number) => Math.max(-LIMIT, Math.min(LIMIT, value));

  const solve = useCallback(
    (
      propId: string,
      ray: THREE.Ray,
      floorPoint: THREE.Vector3 | null,
      screen?: { x: number; y: number },
      excludeKey?: string,
    ): Placed | null => {
      const kind = placementOf(propId);
      const fallbackX = floorPoint ? clamp(floorPoint.x) : 0;
      const fallbackZ = floorPoint ? clamp(floorPoint.z) : 0;
      if (kind === 'hang') {
        const target = findHangTarget({ structural: wallMeshes, ray, floorPoint, spec: spec.hang });
        if (!target) return null;
        return {
          x: clamp(target.point.x),
          y: target.y - hangHeightOf(propId),
          z: clamp(target.point.z),
          carrier: target.carrier,
          surfaceId: 'hang',
        };
      }
      if (kind === 'surface') {
        const footprint = getPropDef(propId)?.footprint;
        let target: SurfaceTarget | null = findSurfaceTarget({
          ray,
          floorPoint,
          placedRoot: placedRef.current,
          structural: wallMeshes,
          roof: roofSet,
          minY: planeY,
          maxY: planeY + SURFACE_MAX_ABOVE,
          excludeKey,
          footprint,
          columnTop: spec.hang.columnTop,
        });
        if (!target && screen) {
          target = findNearbyItemTop({
            camera,
            size,
            screen,
            placedRoot: placedRef.current,
            maxPx: SNAP_PX,
            excludeKey,
          });
        }
        if (!target) {
          if (!floorPoint) return null;
          return { x: fallbackX, y: planeY, z: fallbackZ, surfaceId: 'floor' };
        }
        return {
          x: clamp(target.point.x),
          y: target.y,
          z: clamp(target.point.z),
          parentInstanceId: target.parentKey,
          carrier: target.carrier,
          surfaceId: target.source === 'prop' ? 'prop-top' : 'model-top',
        };
      }
      if (!floorPoint) return null;
      return { x: fallbackX, y: planeY, z: fallbackZ, surfaceId: 'floor' };
    },
    [wallMeshes, roofSet, planeY, camera, size],
  );

  /* ---------------------------------------------------------- 统一落位 */
  const commitPlacement = useCallback(
    (
      propId: string,
      ray: THREE.Ray,
      floorPoint: THREE.Vector3 | null,
      screen?: { x: number; y: number },
      excludeKey?: string,
    ) => {
      const kind = placementOf(propId);
      const placed = solve(propId, ray, floorPoint, screen, excludeKey);
      if (!placed) {
        useDiyStore.getState().setPlaceHint(kind === 'hang' ? HANG_HINT : SURFACE_HINT);
        return false;
      }
      if (kind === 'surface' && !placed.parentInstanceId) {
        // 没有台面可吸附时落到地面，并说明一句，避免用户以为吸附成功
        useDiyStore.getState().setPlaceHint(SURFACE_HINT);
      }
      const item = buildItem(propId, placed.x, placed.y, placed.z, 0, placed);
      if (item) addItem(item);
      return true;
    },
    [solve, addItem],
  );

  /* ---------------------------------------------------------- 拖放落位 */
  useFrame(() => {
    if (!enabled) return;
    const request = useDiyStore.getState().dropRequest;
    if (!request) return;
    useDiyStore.getState().setDropRequest(null);
    const def = getPropDef(request.propId);
    if (!def) return;
    const rect = gl.domElement.getBoundingClientRect();
    const ndc = new THREE.Vector2(
      ((request.clientX - rect.left) / rect.width) * 2 - 1,
      -((request.clientY - rect.top) / rect.height) * 2 + 1,
    );
    raycaster.setFromCamera(ndc, camera);
    if (def.mount === 'wall') {
      const hit = hitWall(raycaster.ray);
      if (!hit) return;
      const item = buildItem(
        def.id,
        hit.point.x + hit.normal.x * 0.06,
        hit.point.y,
        hit.point.z + hit.normal.z * 0.06,
        Math.atan2(hit.normal.x, hit.normal.z),
      );
      if (item) addItem(item);
      return;
    }
    const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -planeY);
    const point = new THREE.Vector3();
    const hasFloor = raycaster.ray.intersectPlane(plane, point);
    commitPlacement(def.id, raycaster.ray, hasFloor ? point : null, {
      x: request.clientX - rect.left,
      y: request.clientY - rect.top,
    });
  });

  /**
   * 落位点击走 canvas 原生事件，而不是落位面的 R3F 事件。
   *
   * 原因：落位面是地面上的 18 m 方片，点「器物上方/梁架」时射线朝天，
   * 根本打不到它，事件不会触发——面板选了件却点不动。改成在 canvas 上
   * 接管 pointerdown/up，任何位置都能算出一条世界射线。
   */
  useEffect(() => {
    if (!enabled || !pendingPropId) return undefined;
    const el = gl.domElement;
    let downAt: { x: number; y: number } | null = null;
    let lastMove = 0;

    const rayAt = (clientX: number, clientY: number) => {
      const rect = el.getBoundingClientRect();
      const ndc = new THREE.Vector2(
        ((clientX - rect.left) / rect.width) * 2 - 1,
        -((clientY - rect.top) / rect.height) * 2 + 1,
      );
      raycaster.setFromCamera(ndc, camera);
      return {
        ray: raycaster.ray.clone(),
        screen: { x: clientX - rect.left, y: clientY - rect.top },
      };
    };

    const onDown = (event: PointerEvent) => {
      downAt = { x: event.clientX, y: event.clientY };
    };

    const onUp = (event: PointerEvent) => {
      const start = downAt;
      downAt = null;
      if (!start) return;
      // 拖动场景不算落位点击
      if (Math.hypot(event.clientX - start.x, event.clientY - start.y) > 5) return;
      const { ray, screen } = rayAt(event.clientX, event.clientY);
      const floor = new THREE.Vector3();
      const hasFloor = ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 1, 0), -planeY), floor);
      if (pendingIsWall && handleWallClick(ray)) {
        setGhost(null);
        return;
      }
      commitPlacement(pendingPropId, ray, hasFloor ? floor : null, screen);
      setGhost(null);
    };

    const onMove = (event: PointerEvent) => {
      const now = performance.now();
      if (now - lastMove < 45) return;
      lastMove = now;
      if (dragRef.current) return;
      const { ray, screen } = rayAt(event.clientX, event.clientY);
      const floor = new THREE.Vector3();
      const hasFloor = ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 1, 0), -planeY), floor);
      const placed = solve(pendingPropId, ray, hasFloor ? floor : null, screen);
      setGhost(placed ? { x: placed.x, y: placed.y, z: placed.z } : null);
    };

    const onLeave = () => setGhost(null);

    el.addEventListener('pointerdown', onDown);
    el.addEventListener('pointerup', onUp);
    el.addEventListener('pointermove', onMove);
    el.addEventListener('pointerleave', onLeave);
    return () => {
      el.removeEventListener('pointerdown', onDown);
      el.removeEventListener('pointerup', onUp);
      el.removeEventListener('pointermove', onMove);
      el.removeEventListener('pointerleave', onLeave);
    };
  }, [enabled, pendingPropId, pendingIsWall, gl, camera, raycaster, planeY, solve, commitPlacement, handleWallClick]);

  const onPlaneDown = useCallback(
    (event: { stopPropagation: () => void }) => {
      if (!enabled) return;
      // 落位点击由 canvas 原生事件处理（见上面的 useEffect），这里只负责取消选中
      if (pendingPropId) {
        event.stopPropagation();
        return;
      }
      selectItem(null);
    },
    [enabled, pendingPropId, selectItem],
  );

  const onPlaneMove = useCallback(
    (event: { point: THREE.Vector3; ray: THREE.Ray }) => {
      if (!enabled) return;
      // 拖动改由 window pointermove 统一处理（见下方 useEffect），
      // 这里只保留墙面吸附的实时跟随，避免指针压在器物上就失去事件。
      const drag = dragRef.current;
      if (!drag) return;
      const item = useDiyStore.getState().current().items.find((entry) => entry.key === drag.key);
      if (!item || item.mount !== 'wall') return;
      const hit = hitWall(event.ray);
      if (!hit) return;
      updateItem(drag.key, {
        x: hit.point.x + hit.normal.x * 0.06,
        y: hit.point.y,
        z: hit.point.z + hit.normal.z * 0.06,
        rotY: Math.atan2(hit.normal.x, hit.normal.z),
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [enabled, updateItem],
  );

  // 拖动：window pointermove 驱动，指针在器物/地面/梁架上都跟手
  useEffect(() => {
    const move = (event: PointerEvent) => {
      const drag = dragRef.current;
      if (!drag) return;
      const item = useDiyStore.getState().current().items.find((entry) => entry.key === drag.key);
      if (!item || item.mount === 'wall') return;
      const rect = gl.domElement.getBoundingClientRect();
      const ndc = new THREE.Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -((event.clientY - rect.top) / rect.height) * 2 + 1,
      );
      raycaster.setFromCamera(ndc, camera);
      const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -drag.planeY);
      const point = new THREE.Vector3();
      if (!raycaster.ray.intersectPlane(plane, point)) return;
      updateItem(drag.key, { x: clamp(point.x + drag.dx), z: clamp(point.z + drag.dz) });
    };
    window.addEventListener('pointermove', move);
    return () => window.removeEventListener('pointermove', move);
  }, [gl, camera, raycaster, updateItem]);

  useEffect(() => {
    const stop = () => {
      if (dragRef.current) {
        dragRef.current = null;
        onDragStateChange(false);
      }
    };
    window.addEventListener('pointerup', stop);
    window.addEventListener('pointercancel', stop);
    return () => {
      window.removeEventListener('pointerup', stop);
      window.removeEventListener('pointercancel', stop);
    };
  }, [onDragStateChange]);

  // 退出 DIY 时清掉落位预览。注意不能无条件调用 setPending(null)：
// 那个 action 会顺手把面板打开，导致一进页面右侧面板自动弹出。
  useEffect(() => {
    if (!enabled) {
      setGhost(null);
      if (useDiyStore.getState().pendingPropId) setPending(null);
    }
  }, [enabled, setPending]);

  // 换层时把预览收掉，避免预览停在上一次的高度
  useEffect(() => setGhost(null), [level]);

  const ghostDef = ghost ? getPropDef(pendingPropId ?? '') : undefined;
  const GhostComp = ghostDef?.Component;

  return (
    <group>
      {/* 落位面：只接指针事件，不可见 */}
      {enabled && (
        <mesh
          position={[0, planeY - 0.004, 0]}
          rotation={[-Math.PI / 2, 0, 0]}
          onPointerDown={onPlaneDown as never}
          onPointerMove={onPlaneMove as never}
          onPointerLeave={() => setGhost(null)}
        >
          <planeGeometry args={[PLANE_SIZE, PLANE_SIZE]} />
          <meshBasicMaterial transparent opacity={0} depthWrite={false} />
        </mesh>
      )}

      {/* 已摆器物（带 diyKey，供顶面吸附识别承载物） */}
      <group ref={placedRef}>
        {items.map((item) => {
          const def = getPropDef(item.propId);
          if (!def) return null;
          const C = def.Component;
          const selected = item.key === selectedKey;
          const userData = { diyKey: item.key, diyName: def.name };
          if (isAssetId(item.propId)) {
            return (
              <group
                key={item.key}
                name={`diy-item-${item.key}`}
                userData={userData}
                position={[item.x, item.y, item.z]}
                rotation={[0, item.rotY, 0]}
                scale={item.scale}
              >
                <AssetInstance item={item} selected={selected} editMode={editMode} />
              </group>
            );
          }
          return (
            <group
              key={item.key}
              name={`diy-item-${item.key}`}
              userData={userData}
              position={[item.x, item.y, item.z]}
              rotation={[0, item.rotY, 0]}
              scale={item.scale}
              onPointerDown={(event) => {
                if (!enabled) return;
                event.stopPropagation();
                selectItem(item.key);
                // 用指针抓住的高度作为拖动平面：拖动全程由 window pointermove 驱动，
                // 不再依赖「指针必须落在落位面上」，否则指针停在器物身上就拖不动。
                dragRef.current = {
                  key: item.key,
                  dx: item.x - event.point.x,
                  dz: item.z - event.point.z,
                  planeY: event.point.y,
                };
                onDragStateChange(true);
              }}
            >
              <C variant={item.variant} />
              {selected && (
                <mesh position={[0, 0.012, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                  <ringGeometry args={[Math.max(0.32, def.footprint[0] * 0.62), Math.max(0.36, def.footprint[0] * 0.68), 40]} />
                  <meshBasicMaterial color="#C9A15A" transparent opacity={0.9} side={THREE.DoubleSide} depthWrite={false} />
                </mesh>
              )}
            </group>
          );
        })}
      </group>

      {/* 落位预览 */}
      {enabled && GhostComp && ghost && (
        <group position={[ghost.x, ghost.y, ghost.z]} rotation={[0, camera.rotation.y, 0]}>
          <GhostComp variant={0} />
          <mesh position={[0, 0.01, 0]} rotation={[-Math.PI / 2, 0, 0]}>
            <ringGeometry args={[0.42, 0.5, 36]} />
            <meshBasicMaterial color={PROP_COLORS.brass} transparent opacity={0.75} depthWrite={false} />
          </mesh>
        </group>
      )}
    </group>
  );
}

/** 与 diyStore.makeItem 等价，但避免从 store 里再导出一次函数 */
function buildItem(
  propId: string,
  x: number,
  y: number,
  z: number,
  rotY: number,
  placed?: Placed,
) {
  const def = getPropDef(propId);
  if (!def) return null;
  return {
    key: `diy-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`,
    propId,
    x,
    y,
    z,
    rotY,
    scale: 1,
    variant: 0,
    mount: def.mount,
    ...(placed?.parentInstanceId ? { parentInstanceId: placed.parentInstanceId } : {}),
    ...(placed?.carrier ? { carrier: placed.carrier } : {}),
    ...(placed?.surfaceId ? { surfaceId: placed.surfaceId } : {}),
  };
}