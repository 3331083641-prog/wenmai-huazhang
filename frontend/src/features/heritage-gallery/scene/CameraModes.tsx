/**
 * 电影视角 / 第一人称视角。
 *
 * 电影视角：绕馆缓慢环游 + 轻微升降，类似建筑漫游片头，不接用户输入。
 * 第一人称：锁定指针后 WASD 行走，视高 1.62 m，限制在馆内与檐廊范围。
 *
 * 两座建筑体量不同（经典馆 16 m 台基、华章新馆 22 m 台基），
 * 所以环游半径、视点高度、可行走范围一律从当前建筑的 SceneSpec 取，
 * 不再写死一套只对经典馆成立的数字。
 */

import { useEffect, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

import type { SceneSpec } from '../buildings';

const EYE = 1.62;

export function CinemaRig({ active, spec }: { active: boolean; spec: SceneSpec }) {
  const { camera } = useThree();
  const t = useRef(0);

  // 由体量推导环游参数：经典馆得到 25.6 m 半径 / 8.6 m 高度，与改造前一致
  const radiusBase = spec.diy.planeSize * 1.42;
  const heightBase = spec.orbitTarget[1] + 5.0;

  useEffect(() => {
    if (!active) return;
    t.current = 0;
    const cam = camera as THREE.PerspectiveCamera;
    cam.fov = 44;
    cam.updateProjectionMatrix();
  }, [active, camera]);

  useFrame((_, delta) => {
    if (!active) return;
    t.current += delta;
    const time = t.current;
    const angle = 0.55 + time * 0.075;
    const radius = radiusBase + Math.sin(time * 0.13) * 2.2;
    const height = heightBase + Math.sin(time * 0.09 + 0.7) * 2.4;
    camera.position.set(Math.sin(angle) * radius, height, Math.cos(angle) * radius);
    camera.lookAt(0, spec.orbitTarget[1] + 0.75, 0.15);
  });

  return null;
}

interface FirstPersonProps {
  active: boolean;
  /** 当前建筑的可行走范围、楼层标高与入口起点 */
  spec: SceneSpec;
  /** 指针锁定状态回调，用来显示准星提示 */
  onLockChange?: (locked: boolean) => void;
}

export function FirstPersonRig({ active, spec, onLockChange }: FirstPersonProps) {
  const { camera, gl } = useThree();
  const yaw = useRef(Math.PI);
  const pitch = useRef(0.02);
  const keys = useRef(new Set<string>());
  const floorY = spec.diy.baseTop;
  const position = useRef(new THREE.Vector3(0, floorY + EYE, spec.firstPerson.startZ));
  const euler = useRef(new THREE.Euler(0, 0, 0, 'YXZ'));

  useEffect(() => {
    if (!active) return;
    const dom = gl.domElement;
    position.current.set(0, floorY + EYE, spec.firstPerson.startZ);
    camera.position.copy(position.current);
    euler.current.set(pitch.current, yaw.current, 0, 'YXZ');
    camera.quaternion.setFromEuler(euler.current);

    const requestLock = () => {
      const result = dom.requestPointerLock?.();
      if (result && typeof (result as Promise<void>).catch === 'function') {
        (result as Promise<void>).catch(() => undefined);
      }
    };
    const onLock = () => onLockChange?.(document.pointerLockElement === dom);
    const onKeyDown = (event: KeyboardEvent) => {
      keys.current.add(event.code);
      if (['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.code)) {
        event.preventDefault();
      }
    };
    const onKeyUp = (event: KeyboardEvent) => keys.current.delete(event.code);
    const onMove = (event: MouseEvent) => {
      if (document.pointerLockElement !== dom) return;
      yaw.current -= event.movementX * 0.0024;
      pitch.current = Math.max(-1.15, Math.min(1.15, pitch.current - event.movementY * 0.0024));
    };

    dom.addEventListener('click', requestLock);
    dom.addEventListener('pointerdown', requestLock);
    document.addEventListener('pointerlockchange', onLock);
    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);
    window.addEventListener('mousemove', onMove);
    return () => {
      dom.removeEventListener('click', requestLock);
      dom.removeEventListener('pointerdown', requestLock);
      document.removeEventListener('pointerlockchange', onLock);
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
      window.removeEventListener('mousemove', onMove);
      if (document.pointerLockElement === dom) document.exitPointerLock();
      keys.current.clear();
      onLockChange?.(false);
    };
  }, [active, camera, gl, floorY, spec, onLockChange]);

  useFrame((_, delta) => {
    if (!active) return;
    const step = Math.min(delta, 0.05) * (keys.current.has('ShiftLeft') ? 4.2 : 2.1);
    const forward = new THREE.Vector3(-Math.sin(yaw.current), 0, -Math.cos(yaw.current));
    const right = new THREE.Vector3(Math.cos(yaw.current), 0, -Math.sin(yaw.current));
    const move = new THREE.Vector3();
    if (keys.current.has('KeyW') || keys.current.has('ArrowUp')) move.add(forward);
    if (keys.current.has('KeyS') || keys.current.has('ArrowDown')) move.sub(forward);
    if (keys.current.has('KeyD') || keys.current.has('ArrowRight')) move.add(right);
    if (keys.current.has('KeyA') || keys.current.has('ArrowLeft')) move.sub(right);
    if (move.lengthSq() > 0) {
      move.normalize().multiplyScalar(step);
      position.current.add(move);
      // 馆内 + 檐廊范围：允许走到前檐台阶上，但不穿墙出界（按本馆尺寸夹取）
      position.current.x = Math.max(
        spec.firstPerson.xMin,
        Math.min(spec.firstPerson.xMax, position.current.x),
      );
      position.current.z = Math.max(
        spec.firstPerson.zMin,
        Math.min(spec.firstPerson.zMax, position.current.z),
      );
    }
    position.current.y = floorY + EYE;
    camera.position.copy(position.current);
    euler.current.set(pitch.current, yaw.current, 0, 'YXZ');
    camera.quaternion.setFromEuler(euler.current);
  });

  return null;
}