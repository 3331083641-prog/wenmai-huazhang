// @ts-nocheck
/**
 * 器物专属互动控制器（统一状态机）
 *
 * 设计要点：
 *  - 每件器物一个控制器实例，只操作「实例内部的局部零件」，绝不改摆放位置；
 *  - 状态机：idle → active（播放）→ closing（缓动回落）→ idle；
 *  - 关闭时把零件从当前姿态缓动回初始姿态，不会突然跳变；
 *  - 材质在实例化时已按实例克隆，互不干扰；
 *  - 4 种实现：generic（复用原 HTML 的 interact 闭包）、glow（灯光开合）、
 *    spin（只转指定枢轴）、info（弹出文化解读卡，不做三维动作）。
 */

import * as THREE from 'three';

export type ControllerMode = 'generic' | 'glow' | 'spin' | 'info';

export interface PropController {
  trigger: () => void;
  update: (dt: number) => void;
  isActive: () => boolean;
  serialize: () => { active: boolean };
  restore: (state?: { active?: boolean } | null) => void;
  dispose: () => void;
}

interface Pose {
  obj: THREE.Object3D;
  position: THREE.Vector3;
  quaternion: THREE.Quaternion;
  scale: THREE.Vector3;
}

interface GlowTarget {
  material: THREE.MeshStandardMaterial;
  base: number;
}

function snapshot(root: THREE.Object3D) {
  const poses: Pose[] = [];
  const glows: GlowTarget[] = [];
  root.traverse((obj) => {
    poses.push({
      obj,
      position: obj.position.clone(),
      quaternion: obj.quaternion.clone(),
      scale: obj.scale.clone(),
    });
    const mesh = obj as THREE.Mesh;
    if (!mesh.isMesh || !mesh.material) return;
    const list = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const material of list) {
      const std = material as THREE.MeshStandardMaterial;
      if (!std || !('emissive' in std)) continue;
      const base = std.emissiveIntensity ?? 0;
      if (base > 0.05) glows.push({ material: std, base });
    }
  });
  return { poses, glows };
}

function easeOutCubic(t: number) {
  return 1 - Math.pow(1 - t, 3);
}

export function createController(
  assetId: string,
  root: THREE.Object3D,
  mode: ControllerMode,
  payload?: { pivotName?: string; infoId?: string; glowMotion?: boolean },
): PropController {
  const rest = snapshot(root);
  const fn = (root.userData as { interact?: (t: number) => void }).interact;
  const pivot = payload?.pivotName ? root.getObjectByName(payload.pivotName) : null;

  let active = false;
  let clock = 0;
  let closing = 0;
  let fromPose: { position: THREE.Vector3; quaternion: THREE.Quaternion; scale: THREE.Vector3 }[] | null = null;
  let disposed = false;

  /** 关闭时把零件从当前姿态缓回初始姿态 */
  function beginClose() {
    closing = 1;
    fromPose = rest.poses.map((p) => ({
      position: p.obj.position.clone(),
      quaternion: p.obj.quaternion.clone(),
      scale: p.obj.scale.clone(),
    }));
  }

  function applyClose(dt: number) {
    if (!fromPose) return;
    closing = Math.max(0, closing - dt / 0.55);
    const k = easeOutCubic(1 - closing);
    rest.poses.forEach((p, i) => {
      const from = fromPose![i];
      if (!from) return;
      p.obj.position.lerpVectors(from.position, p.position, k);
      p.obj.quaternion.slerpQuaternions(from.quaternion, p.quaternion, k);
      p.obj.scale.lerpVectors(from.scale, p.scale, k);
    });
    for (const g of rest.glows) {
      g.material.emissiveIntensity = THREE.MathUtils.lerp(g.base * 2.2, g.base, k);
    }
    if (closing <= 0) fromPose = null;
  }

  return {
    trigger() {
      if (disposed) return;
      if (mode === 'info') {
        window.dispatchEvent(
          new CustomEvent('wenmai:asset-info', { detail: { assetId: payload?.infoId ?? assetId } }),
        );
        return;
      }
      active = !active;
      if (active) {
        closing = 0;
        fromPose = null;
      } else {
        beginClose();
      }
    },
    update(dt: number) {
      if (disposed) return;
      if (active) {
        clock += dt;
        if (mode === 'generic' && fn) {
          fn(clock * 1.35);
        } else if (mode === 'glow') {
          const k = Math.min(1, clock / 0.8);
          for (const g of rest.glows) {
            g.material.emissiveIntensity = THREE.MathUtils.lerp(g.base, g.base * 2.4, easeOutCubic(k));
          }
          // 莲花灯点亮的同潮流苏也要摆，否则「点亮」只剩一段静态发光
          if (payload?.glowMotion && fn) fn(clock * 1.35);
        } else if (mode === 'spin') {
          const target = pivot ?? root;
          target.rotation.y = clock * 0.9;
        }
      } else if (closing > 0) {
        applyClose(dt);
      }
    },
    isActive: () => active,
    serialize: () => ({ active }),
    restore(state) {
      if (!state?.active) return;
      active = true;
    },
    dispose() {
      disposed = true;
      fromPose = null;
    },
  };
}