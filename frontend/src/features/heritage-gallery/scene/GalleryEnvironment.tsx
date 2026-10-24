/**
 * 纹脉展馆 · 环境反射（IBL）
 *
 * 为什么需要它：
 *  模型里 M_gold 是金属度 0.72 的铜，M_lacquer / M_porcelain 是低粗糙度漆面与釉面。
 *  PBR 下金属没有环境贴图就是一块死灰——之前展厅的铜饰件、瓷器高光都发闷，
 *  原因不是灯不够亮，而是「没有东西可反射」。
 *
 * 做法（不引入 HDRI、不联网、不加依赖）：
 *  用一张循序渐进的小场景（天色球 + 暖地面 + 一块太阳/月亮亮片）
 *  交给 THREE.PMREMGenerator.fromScene 烘焙成环境贴图，
 *  每次切时段烘焙一次（约几毫秒，GPU 端 6 面 256²），
 *  之后所有 PBR 材质共享同一张环境贴图，逐帧零成本。
 *
 * 地面色与亮片取自 DayNightRig 的同一套预设，天色与真实穹顶完全一致。
 */

import { useEffect, useRef } from 'react';
import { useThree } from '@react-three/fiber';
import * as THREE from 'three';

import { TIME_PRESETS, createSkyTexture, type TimeOfDay } from './DayNightRig';

/** 环境球半径：PMREM 的 near/far 之内即可，尺寸不影响亮度 */
const ENV_RADIUS = 40;

function buildEnvScene(time: TimeOfDay): THREE.Scene {
  const preset = TIME_PRESETS[time];
  const scene = new THREE.Scene();

  // 天色：内翻球 + 与主场景同一张竖向渐变
  const sky = new THREE.Mesh(
    new THREE.SphereGeometry(ENV_RADIUS, 16, 10),
    new THREE.MeshBasicMaterial({
      map: createSkyTexture(time),
      side: THREE.BackSide,
      toneMapped: false,
    }),
  );
  scene.add(sky);

  // 地面反弹：木地板与石台基的暖反光，决定室内暗部是暖灰还是死黑
  const ground = new THREE.Mesh(
    new THREE.CircleGeometry(ENV_RADIUS * 0.95, 24),
    new THREE.MeshBasicMaterial({ color: new THREE.Color(preset.envGround), toneMapped: false }),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -ENV_RADIUS * 0.15;
  scene.add(ground);

  // 太阳/月亮：一块高亮矩形，让铜饰、漆面、瓷器有明确的高光形状
  const sunDir = new THREE.Vector3(...preset.sunPosition).normalize();
  const sun = new THREE.Mesh(
    new THREE.PlaneGeometry(ENV_RADIUS * 0.55, ENV_RADIUS * 0.55),
    // 基色可以大于 1：PMREM 目标是浮点纹理，直接当 HDR 亮片用
    new THREE.MeshBasicMaterial({
      color: new THREE.Color(preset.sunColor).multiplyScalar(time === 'night' ? 1.6 : 2.6),
      toneMapped: false,
    }),
  );
  sun.position.copy(sunDir.multiplyScalar(ENV_RADIUS * 0.9));
  sun.lookAt(0, 0, 0);
  scene.add(sun);

  return scene;
}

/** 释放一份环境场景里的几何与材质（贴图是缓存共享的，material.dispose 不会连带释放 map） */
function disposeScene(scene: THREE.Scene): void {
  scene.traverse((object) => {
    const mesh = object as THREE.Mesh;
    if (!mesh.isMesh) return;
    mesh.geometry.dispose();
    const raw = mesh.material as THREE.Material | THREE.Material[];
    for (const material of Array.isArray(raw) ? raw : [raw]) material?.dispose();
  });
}

export function GalleryEnvironment({ time }: { time: TimeOfDay }): null {
  const gl = useThree((state) => state.gl);
  const scene = useThree((state) => state.scene);
  const targetRef = useRef<THREE.WebGLRenderTarget | null>(null);

  useEffect(() => {
    const preset = TIME_PRESETS[time];
    const pmrem = new THREE.PMREMGenerator(gl);
    const envScene = buildEnvScene(time);
    let target: THREE.WebGLRenderTarget | null = null;
    try {
      target = pmrem.fromScene(envScene, 0.02, 0.1, ENV_RADIUS * 2.2);
    } catch {
      // 极少数驱动（老 SwiftShader）不支持半浮点渲染目标；失败时退回无 IBL，
      // 画面只是少了反射，不会白屏。
      target = null;
    }

    if (target) {
      scene.environment = target.texture;
      scene.environmentIntensity = preset.envIntensity;
      // 换时段时释放上一张，避免环境贴图在新旧之间泄漏
      targetRef.current?.dispose();
      targetRef.current = target;
    }

    disposeScene(envScene);
    pmrem.dispose();

    return () => {
      // 只清理本次烘焙失败/替换下来的目标；场景卸载时统一在下面的 effect 处理
    };
  }, [gl, scene, time]);

  useEffect(
    () => () => {
      scene.environment = null;
      targetRef.current?.dispose();
      targetRef.current = null;
    },
    [scene],
  );

  return null;
}

export default GalleryEnvironment;