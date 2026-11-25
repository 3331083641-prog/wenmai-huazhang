/**
 * 电影视角 / 第一人称视角。
 *
 * 电影视角：绕馆缓慢环游 + 轻微升降，类似建筑漫游片头，不接用户输入。
 * 第一人称：锁定指针后 WASD 行走，视高 1.62 m，限制在馆内与檐廊范围，
 *          抬头上看就是通高屋顶的木构（模型本身没有楼板与天花）。
 *
 * 两者都只在激活时接管相机；退出时把朝向还给 OrbitControls。
 */

import { useEffect, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

const EYE = 1.62;

export function CinemaRig({ active }: { active: boolean }) {
  const { camera } = useThree();
  const t = useRef(0);
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
    const radius = 25.5 + Math.sin(time * 0.13) * 2.2;
    const height = 8.6 + Math.sin(time * 0.09 + 0.7) * 2.4;
    camera.position.set(Math.sin(angle) * radius, height, Math.cos(angle) * radius);
    camera.lookAt(0, 4.35, 0.15);
  });

  return null;
}

interface FirstPersonProps {
  active: boolean;
  /** 站立的楼层标高（一层 0.25） */
  floorY: number;
  /** 指针锁定状态回调，用来显示准星提示 */
  onLockChange?: (locked: boolean) => void;
}

export function FirstPersonRig({ active, floorY, onLockChange }: FirstPersonProps) {
  const { camera, gl } = useThree();
  const yaw = useRef(Math.PI);
  const pitch = useRef(0.02);
  const keys = useRef(new Set<string>());
  const position = useRef(new THREE.Vector3(0, floorY + EYE, -2.7));
  const euler = useRef(new THREE.Euler(0, 0, 0, 'YXZ'));

  useEffect(() => {
    if (!active) return;
    const dom = gl.domElement;
    position.current.set(0, floorY + EYE, 2.9);
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
  }, [active, camera, gl, floorY, onLockChange]);

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
      // 馆内 + 檐廊范围：允许走到前檐台阶上，但不穿墙出界
      position.current.x = Math.max(-4.9, Math.min(4.9, position.current.x));
      position.current.z = Math.max(-4.4, Math.min(4.1, position.current.z));
    }
    position.current.y = floorY + EYE;
    camera.position.copy(position.current);
    euler.current.set(pitch.current, yaw.current, 0, 'YXZ');
    camera.quaternion.setFromEuler(euler.current);
  });

  return null;
}