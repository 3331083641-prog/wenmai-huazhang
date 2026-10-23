/**
 * 立面大门的交互：鼠标悬停高亮 + 点击开合。
 *
 * 模型里两扇门各自挂在一个空物体 `DOOR_HingeL / DOOR_HingeR` 下，空物体的
 * 原点就在门轴线上。这里只做三件事：
 *   1. 每帧用当前指针射线测一遍门扇，更新 doorStore 的 hover；
 *   2. 悬停时把门的材质稍微提亮（自发光），提示「可以点」；
 *   3. 点击切换开合，铰链绕局部 Y 轴缓动到 0 或 ±78°。
 */

import { useEffect, useMemo, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

import { useDoorStore } from '../state/doorStore';

const OPEN_ANGLE = THREE.MathUtils.degToRad(40);

export function DoorInteraction({ root }: { root: THREE.Object3D }) {
  const { camera, raycaster, pointer, size, gl } = useThree();
  const hinges = useRef<{ left: THREE.Object3D | null; right: THREE.Object3D | null }>({
    left: null,
    right: null,
  });
  const doorMeshes = useRef<THREE.Object3D[]>([]);
  const highlight = useRef<THREE.MeshStandardMaterial[]>([]);
  const progress = useRef(0);
  const hoverRef = useRef(false);

  const open = useDoorStore((state) => state.open);
  const toggle = useDoorStore((state) => state.toggle);
  const setHover = useDoorStore((state) => state.setHover);

  useEffect(() => {
    const left = root.getObjectByName('DOOR_HingeL') ?? null;
    const right = root.getObjectByName('DOOR_HingeR') ?? null;
    hinges.current = { left, right };
    const meshes: THREE.Object3D[] = [];
    const mats: THREE.MeshStandardMaterial[] = [];
    for (const hinge of [left, right]) {
      if (!hinge) continue;
      hinge.traverse((child) => {
        const mesh = child as THREE.Mesh;
        if (!mesh.isMesh) return;
        meshes.push(mesh);
        // 材质是全场共享的（M_wood / M_gold ...），要高亮门就必须先克隆一份，
        // 否则点门会把整栋建筑的木作一起点亮。
        const raw = mesh.material as THREE.Material | THREE.Material[];
        const list = (Array.isArray(raw) ? raw : [raw]).map((material) => {
          const clone = material.clone() as THREE.MeshStandardMaterial;
          if ('emissive' in clone) mats.push(clone);
          return clone;
        });
        mesh.material = Array.isArray(raw) ? list : list[0];
      });
    }
    doorMeshes.current = meshes;
    highlight.current = mats;
    return () => {
      useDoorStore.getState().reset();
    };
  }, [root]);

  // 点击：只有指针真的在门上时才开合，避免点场景任何位置都开门
  useEffect(() => {
    const dom = gl.domElement;
    const onClick = () => {
      if (hoverRef.current) useDoorStore.getState().toggle();
    };
    dom.addEventListener('click', onClick);
    return () => dom.removeEventListener('click', onClick);
  }, [gl]);

  useFrame((state, delta) => {
    // 1) 悬停检测（每帧一次，门只有十几个三角面，开销可以忽略）
    raycaster.setFromCamera(pointer, camera);
    const hit = doorMeshes.current.length
      ? raycaster.intersectObjects(doorMeshes.current, true)[0]
      : undefined;
    const isHover = Boolean(hit);
    if (isHover !== hoverRef.current) {
      hoverRef.current = isHover;
      setHover(isHover);
      gl.domElement.style.cursor = isHover ? 'pointer' : '';
      for (const material of highlight.current) {
        material.emissive = new THREE.Color(isHover ? '#7a4a1c' : '#000000');
        material.emissiveIntensity = isHover ? 0.55 : 0;
      }
    }
    if (isHover) {
      // 提示跟着鼠标走（画布坐标，页面负责定位）
      setHover(true, (pointer.x * 0.5 + 0.5) * size.width, (-pointer.y * 0.5 + 0.5) * size.height);
    }

    // 2) 开合缓动
    const target = useDoorStore.getState().open ? 1 : 0;
    if (Math.abs(progress.current - target) > 0.001) {
      progress.current += (target - progress.current) * Math.min(1, delta * 7.5);
      const angle = OPEN_ANGLE * progress.current;
      // 向廊内开 40°：门廊净深 1.10 m、门扇 1.48 m，40° 时门扇末端到 y≈2.15，刚好不撞廊后墙；开门后看到的是格心正面，不是白纸背板
      if (hinges.current.left) hinges.current.left.rotation.y = angle;
      if (hinges.current.right) hinges.current.right.rotation.y = -angle;
    }
    void state;
  });

  return null;
}