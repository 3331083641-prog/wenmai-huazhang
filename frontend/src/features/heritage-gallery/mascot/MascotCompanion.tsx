import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';

import {
  CAMERA,
  EXHIBIT,
  MOTION,
  createMascotWorld,
} from './mascotConfig';
import type { BuildingDef } from '../buildings';
import {
  MASCOT_MODEL,
  clipName,
  computeMascotFit,
  describeMascotModel,
  isMascotModelAvailable,
  isOneShotClip,
  type MascotClip,
} from './mascotModel';

export type MascotView = 'third' | 'first';
export type MascotPhase = 'spawning' | 'ready';

/** 竖直轴：每帧构造 Vector3 会产生垃圾，这里共用一份 */
const UP_AXIS = new THREE.Vector3(0, 1, 0);

export interface MascotProbe {
  active: boolean;
  phase: MascotPhase;
  view: MascotView;
  position: [number, number, number];
  yaw: number;
  /** 当前语义动作（idle/walk/run/...），不是 GLB 里的动画名 */
  action: MascotClip;
  /** 当前速度（米/秒），验收用来看加减速是否生效 */
  speed: number;
  floor: 1 | 2;
  nearestFrame: string | null;
  hasModel: boolean;
  camera: [number, number, number];
}

export interface MascotCompanionProps {
  /** 当前建筑：灵宠的楼层、可行走范围、展品点都按它推导 */
  building: BuildingDef;
  active: boolean;
  /** 馆体网格：第三人称相机用它做射线碰撞，避免穿墙 */
  collisionMeshes?: THREE.Object3D[];
  view: MascotView;
  onExit: () => void;
  onViewChange: (view: MascotView) => void;
  /** 靠近展品 / 按 E 时回调，页面据此打开已有文化卡。 */
  onExhibit: (frameId: string) => void;
}

/* ------------------------------------------------------------------ 占位角色 */

/** 模型没到位时的占位：只验证走位、碰撞、镜头与展品触发，不代表正式形象。 */
function PlaceholderCat() {
  return (
    <group>
      <mesh position={[0, 0.34, 0]} castShadow>
        <capsuleGeometry args={[0.16, 0.22, 6, 12]} />
        <meshStandardMaterial color="#f3e7cf" roughness={0.7} />
      </mesh>
      <mesh position={[0, 0.72, 0]} castShadow>
        <sphereGeometry args={[0.23, 20, 16]} />
        <meshStandardMaterial color="#f3e7cf" roughness={0.7} />
      </mesh>
      {[-1, 1].map((side) => (
        <mesh key={side} position={[side * 0.15, 0.9, 0]} rotation={[0, 0, side * 0.25]} castShadow>
          <coneGeometry args={[0.075, 0.16, 10]} />
          <meshStandardMaterial color="#b5322c" roughness={0.6} />
        </mesh>
      ))}
      {[-1, 1].map((side) => (
        <mesh key={`eye-${side}`} position={[side * 0.09, 0.74, -0.2]}>
          <sphereGeometry args={[0.035, 12, 10]} />
          <meshStandardMaterial color="#3e7f72" roughness={0.25} />
        </mesh>
      ))}
      <mesh position={[0, 0.36, 0.22]} rotation={[0.9, 0, 0]} castShadow>
        <torusGeometry args={[0.13, 0.035, 8, 20, Math.PI * 1.4]} />
        <meshStandardMaterial color="#f3e7cf" roughness={0.7} />
      </mesh>
    </group>
  );
}

/* ------------------------------------------------------------------ 正式模型 */

/**
 * 正式模型：所有「怎么摆」的算术都在 mascotModel.ts 的配置与 computeMascotFit 里，
 * 这里只负责把结果套到一个包裹组上（不直接改 useGLTF 缓存里的 scene 变换，
 * 否则第二次挂载会把上一次的缩放带进来）。
 */
function MascotModel({
  onReady,
}: {
  onReady: (mixer: THREE.AnimationMixer, actions: Record<string, THREE.AnimationAction>) => void;
}) {
  const { scene, animations } = useGLTF(MASCOT_MODEL.url);
  const fit = useMemo(() => computeMascotFit(scene), [scene]);
  const mixer = useMemo(() => new THREE.AnimationMixer(scene), [scene]);

  useEffect(() => {
    if (import.meta.env.DEV) describeMascotModel(scene, animations);
  }, [scene, animations]);

  useEffect(() => {
    const actions: Record<string, THREE.AnimationAction> = {};
    animations.forEach((clip) => {
      actions[clip.name] = mixer.clipAction(clip);
    });
    onReady(mixer, actions);
    return () => {
      mixer.stopAllAction();
    };
  }, [animations, mixer, onReady]);

  return (
    <group
      name="MASCOT_MODEL_FIT"
      rotation={[0, MASCOT_MODEL.yawOffset, 0]}
      scale={fit.scale}
      position={[0, fit.offsetY, 0]}
    >
      <primitive object={scene} />
    </group>
  );
}

/* ------------------------------------------------------------------ 楼梯 */

/* ------------------------------------------------------------------ 主组件 */

export function MascotCompanion({ building, active, view, collisionMeshes, onExit, onViewChange, onExhibit }: MascotCompanionProps) {
  const { camera } = useThree();
  // 每座展馆一套行走参数：经典馆沿用调好的楼梯世界，新馆按体量推导
  const world = useMemo(() => createMascotWorld(building), [building]);
  const rootRef = useRef<THREE.Group>(null);
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const actionsRef = useRef<Record<string, THREE.AnimationAction>>({});
  /** 当前语义动作（idle/walk/...），GLB 里的动画名只在 fadeTo 内部出现 */
  const currentAction = useRef<MascotClip>('idle');

  const [hasModel, setHasModel] = useState(false);
  const [phase, setPhase] = useState<MascotPhase>('spawning');

  const state = useRef({
    position: new THREE.Vector3(...world.spawn.outside),
    yaw: world.spawn.lookYaw,
    spawnT: 0,
    nearest: null as string | null,
    lastExhibitAt: 0,
    moved: 0,
    oneShotUntil: 0,
    camBlend: 0,
    /** 平滑后的速度（米/秒）：按键目标速度 -> 加速度 -> 实际位移 */
    speed: 0,
    /** 平滑后的角速度（弧度/秒） */
    yawVel: 0,
    /** 相机遮挡检测的降频计数 */
    camTick: 0,
    /** 遮挡检测允许的相机距离（缓存上一次采样结果，避免每帧 raycast） */
    camClear: CAMERA.thirdDistance,
  });
  const keys = useRef<Set<string>>(new Set());
  const s0 = state;
  const camRay = useMemo(() => new THREE.Raycaster(), []);
  const collisionMeshesRef = useRef<THREE.Object3D[]>([]);
  const obstaclesRef = useRef<Array<{ floor: 1 | 2; minX: number; maxX: number; minZ: number; maxZ: number }>>([]);
  const spawnTarget = useRef(new THREE.Vector3(...world.spawn.inside));
  collisionMeshesRef.current = collisionMeshes ?? [];

  /* 模型可用性：地址与 magic 校验都在 mascotModel.ts，换模型不用改这里 */
  useEffect(() => {
    let cancelled = false;
    isMascotModelAvailable().then((ok) => {
      if (!cancelled) setHasModel(ok);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  /** 候选出生点：从门口往里排，挑第一块四周没有家具/展柜的空地。 */
  const pickSpawn = useCallback((): [number, number, number] => {
    if (!obstaclesRef.current.length) buildObstacles();
    const meshes = collisionMeshesRef.current;
    const probe = new THREE.Raycaster();
    const dirs: Array<[number, number]> = [];
    for (let i = 0; i < 8; i += 1) dirs.push([Math.cos((i / 8) * Math.PI * 2), Math.sin((i / 8) * Math.PI * 2)]);
    const clearAt = (x: number, z: number) => {
      const blockedByBox = obstaclesRef.current.some(
        (box) =>
          box.floor === 1 &&
          x > box.minX - MOTION.radius &&
          x < box.maxX + MOTION.radius &&
          z > box.minZ - MOTION.radius &&
          z < box.maxZ + MOTION.radius
      );
      if (blockedByBox) return false;
      if (!meshes.length) return true;
      for (const y of [0.45, 0.95]) {
        for (const [dx, dz] of dirs) {
          probe.set(new THREE.Vector3(x, y, z), new THREE.Vector3(dx, 0, dz));
          probe.far = 0.55;
          if (probe.intersectObjects(meshes, true).length) return false;
        }
      }
      probe.set(new THREE.Vector3(x, 2.2, z), new THREE.Vector3(0, -1, 0));
      probe.far = 2.4;
      return probe.intersectObjects(meshes, true).length > 0;
    };
    const candidates: Array<[number, number]> = [
      [-1.2, 1.2], [-1.2, 1.6], [0.4, 1.2], [-2.4, 2.4], [1.6, 1.2], [0, 1.2], [-2, 0], [2, 0], [0, 3.2],
    ];
    const debug: Array<{ x: number; z: number; ok: boolean }> = [];
    for (const [x, z] of candidates) {
      const ok = clearAt(x, z);
      debug.push({ x, z, ok });
      if (ok) {
        (window as unknown as { __mascotSpawnDebug?: unknown }).__mascotSpawnDebug = debug;
        return [x, world.floor1Y, z];
      }
    }
    (window as unknown as { __mascotSpawnDebug?: unknown }).__mascotSpawnDebug = debug;
    return world.spawn.inside;
  }, []);

  /** 把馆体网格里「挡住走路的家具/展柜」抽成二维矩形，按楼层分组。 */
  const buildObstacles = useCallback(() => {
    const meshes = collisionMeshesRef.current;
    const boxes: Array<{ floor: 1 | 2; minX: number; maxX: number; minZ: number; maxZ: number }> = [];
    const box = new THREE.Box3();
    const inStair = (object: THREE.Object3D) => {
      let node: THREE.Object3D | null = object;
      while (node) {
        if (node.name && node.name.startsWith(world.stairMeshPrefix)) return true;
        node = node.parent;
      }
      return false;
    };
    for (const mesh of meshes) {
      if (!(mesh as THREE.Mesh).isMesh) continue;
      if (inStair(mesh)) continue; // 楼梯踏步/栏杆自己就是通道，不能算障碍
      box.setFromObject(mesh);
      if (!Number.isFinite(box.min.x) || !Number.isFinite(box.max.x)) continue;
      const height = box.max.y - box.min.y;
      const sizeX = box.max.x - box.min.x;
      const sizeZ = box.max.z - box.min.z;
      // 天花板/地面/墙体这类薄而大的面不算家具
      if (height < 0.25 || height > 2.6) continue;
      if (sizeX > 6 || sizeZ > 6) continue;
      const centerY = (box.min.y + box.max.y) / 2;
      const floor: 1 | 2 = centerY > (world.floor1Y + world.floor2Y) / 2 ? 2 : 1;
      const floorY = floor === 1 ? world.floor1Y : world.floor2Y;
      // 只保留站在楼面上、能挡到角色腰部的物件
      if (box.min.y > floorY + 1.3 || box.max.y < floorY + 0.12) continue;
      boxes.push({ floor, minX: box.min.x, maxX: box.max.x, minZ: box.min.z, maxZ: box.max.z });
    }
    obstaclesRef.current = boxes;
    (window as unknown as { __mascotObstacleStats?: unknown }).__mascotObstacleStats = {
      meshes: meshes.length,
      boxes: boxes.length,
    };
    (window as unknown as { __mascotObstacles?: unknown }).__mascotObstacles = boxes;
  }, []);

  /** 角色能否站在 (x,z)：不在任何同层障碍盒（外扩角色半径）里。 */
  const blockedAt = useCallback((x: number, z: number, y: number) => {
    const floor: 1 | 2 = y > (world.floor1Y + world.floor2Y) / 2 ? 2 : 1;
    return obstaclesRef.current.some(
      (box) =>
        box.floor === floor &&
        x > box.minX - MOTION.radius &&
        x < box.maxX + MOTION.radius &&
        z > box.minZ - MOTION.radius &&
        z < box.maxZ + MOTION.radius
    );
  }, [buildObstacles]);

  /* 进入模式：回位、播 Spawn、镜头开始混合 */
  useEffect(() => {
    if (!active) return;
    const spawn = pickSpawn();
    spawnTarget.current.set(spawn[0], spawn[1], spawn[2]);
    state.current.position.set(spawn[0], spawn[1], spawn[2]);
    state.current.yaw = world.spawn.lookYaw;
    state.current.spawnT = 0;
    state.current.camBlend = 0;
    state.current.nearest = null;
    setPhase('spawning');
  }, [active, pickSpawn]);

  /**
 * 切动作：入口与出口都用语义名（'walk'），GLB 的真实动画名只在 clipName() 里出现，
 * 换模型时改 mascotModel.ts 的 clips 表即可。
 */
  const fadeTo = useCallback((action: MascotClip, duration = 0.25) => {
    if (currentAction.current === action) return;
    const prev = actionsRef.current[clipName(currentAction.current)];
    const next = actionsRef.current[clipName(action)];
    const oneShot = isOneShotClip(action);
    if (next) {
      next.reset();
      next.setLoop(oneShot ? THREE.LoopOnce : THREE.LoopRepeat, oneShot ? 1 : Infinity);
      next.clampWhenFinished = action !== 'spawn';
      next.fadeIn(duration).play();
    }
    if (prev && prev !== next) prev.fadeOut(duration);
    currentAction.current = action;
  }, []);

  const playOneShot = useCallback(
    (action: MascotClip) => {
      fadeTo(action, 0.16);
      const duration = actionsRef.current[clipName(action)]?.getClip().duration ?? 0.9;
      state.current.oneShotUntil = performance.now() + duration * 1000;
    },
    [fadeTo]
  );

  const onModelReady = useCallback(
    (mixer: THREE.AnimationMixer, actions: Record<string, THREE.AnimationAction>) => {
      mixerRef.current = mixer;
      actionsRef.current = actions;
      const idle = actions[clipName('idle')];
      if (idle) {
        idle.play();
        currentAction.current = 'idle';
      }
      const spawn = actions[clipName('spawn')];
      if (spawn) {
        spawn.reset();
        spawn.setLoop(THREE.LoopOnce, 1);
        spawn.clampWhenFinished = false;
        spawn.play();
        currentAction.current = 'spawn';
      }
    },
    []
  );

  /* 键盘 */
  useEffect(() => {
    if (!active) return;
    const onDown = (event: KeyboardEvent) => {
      const code = event.code;
      if (
        ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'].includes(code) ||
        ['KeyW', 'KeyA', 'KeyS', 'KeyD', 'KeyE', 'KeyV', 'Escape'].includes(code)
      ) {
        event.preventDefault();
      }
      if (code === 'Escape') return onExit();
      if (code === 'KeyV') return onViewChange(view === 'third' ? 'first' : 'third');
      if (code === 'KeyE') {
        if (state.current.nearest) {
          onExhibit(state.current.nearest);
          playOneShot('interact');
        }
        return;
      }
      keys.current.add(code);
    };
    const onUp = (event: KeyboardEvent) => keys.current.delete(event.code);
    window.addEventListener('keydown', onDown);
    window.addEventListener('keyup', onUp);
    return () => {
      window.removeEventListener('keydown', onDown);
      window.removeEventListener('keyup', onUp);
      keys.current.clear();
    };
  }, [active, onExit, onViewChange, onExhibit, playOneShot, view]);

  /* 开发用传送：仅 dev 构建暴露，便于自动化验收楼梯/展品联动 */
  useEffect(() => {
    if (!import.meta.env.DEV) return;
    (window as unknown as { __mascotDebug?: unknown }).__mascotDebug = {
      teleport: (x: number, z: number, yaw = s0.current.yaw, y?: number) => {
        s0.current.position.set(x, y ?? world.groundHeightAt(x, z, s0.current.position.y), z);
        s0.current.yaw = yaw;
        s0.current.spawnT = 1;
        setPhase('ready');
      },
    };
    return () => {
      (window as unknown as { __mascotDebug?: unknown }).__mascotDebug = undefined;
    };
  }, []);

  /* 每帧 */
  useFrame((_, delta) => {
    if (!active) return;
    const dt = Math.min(0.05, delta);
    const s = state.current;
    const root = rootRef.current;
    if (!root) return;

    if (phase === 'spawning') {
      s.spawnT = Math.min(1, s.spawnT + dt / 1.15);
      const ease = s.spawnT * s.spawnT * (3 - 2 * s.spawnT);
      s.position.lerpVectors(new THREE.Vector3(...world.spawn.outside), spawnTarget.current, ease);
      s.position.y = world.floor1Y + Math.sin(Math.PI * Math.min(1, s.spawnT / 0.85)) * 0.3;
      if (s.spawnT >= 1) {
        s.position.copy(spawnTarget.current);
        setPhase('ready');
        fadeTo('idle', 0.2);
      }
    } else {
      const forwardKey =
        keys.current.has('KeyW') || keys.current.has('ArrowUp')
          ? 1
          : keys.current.has('KeyS') || keys.current.has('ArrowDown')
            ? -1
            : 0;
      const turnKey =
        keys.current.has('KeyA') || keys.current.has('ArrowLeft')
          ? 1
          : keys.current.has('KeyD') || keys.current.has('ArrowRight')
            ? -1
            : 0;
      const running = keys.current.has('ShiftLeft') || keys.current.has('ShiftRight');

      // 转向：目标角速度 -> 平滑逼近。旧版是「按键瞬间给满转速」，
      // 松手立刻停，看起来像贴图在转；现在有角加速度，起转/收转都有过渡。
      s.yawVel = THREE.MathUtils.damp(s.yawVel, turnKey * MOTION.turnSpeed, MOTION.turnAccel, dt);
      s.yaw += s.yawVel * dt;

      // 速度同样走加速/减速，不再按帧硬切；低于 2 cm/s 归零，避免残余漂移。
      const targetSpeed =
        forwardKey > 0 ? (running ? MOTION.runSpeed : MOTION.walkSpeed) : forwardKey < 0 ? -MOTION.backSpeed : 0;
      s.speed = THREE.MathUtils.damp(s.speed, targetSpeed, MOTION.accel, dt);
      if (Math.abs(s.speed) < 0.02) s.speed = 0;

      if (s.speed !== 0) {
        const forward = new THREE.Vector3(0, 0, -1).applyAxisAngle(UP_AXIS, s.yaw);
        const distance = THREE.MathUtils.clamp(s.speed * dt, -MOTION.maxStep, MOTION.maxStep);
        s.moved += Math.abs(distance);
        // 子步推进：一帧最多 0.35 m，但薄墙/栏杆只有 0.1 m 厚，
        // 按 0.1 m 切成子步逐段判定，一步跨穿墙的情况基本消失。
        const steps = Math.max(1, Math.ceil(Math.abs(distance) / MOTION.subStep));
        const stepLength = distance / steps;
        for (let i = 0; i < steps; i += 1) {
          const [cx, cz] = world.clampToHall(
            s.position.x + forward.x * stepLength,
            s.position.z + forward.z * stepLength,
          );
          // 只按障碍盒判碰撞：楼梯踏步/栏杆本身就是通道，用射线打会把自己挡住
          if (blockedAt(cx, cz, s.position.y) || !world.canStandAt(cx, cz, s.position.y)) {
            s.speed = 0;
            break;
          }
          s.position.x = cx;
          s.position.z = cz;
          const nextY = world.groundHeightAt(cx, cz, s.position.y);
          if (Number.isFinite(nextY)) s.position.y = nextY;
        }

        // 坠落保护：脚下滑出楼板（数值异常或踩到洞）时回到最近的合法落点，
        // 而不是继续往下掉、最后飘在场景外。
        if (!Number.isFinite(s.position.y) || s.position.y < world.floor1Y - MOTION.fallGuard) {
          const [sx, sz] = world.clampToHall(s.position.x, s.position.z);
          const fallbackY = world.groundHeightAt(sx, sz, world.floor1Y);
          s.position.set(sx, Number.isFinite(fallbackY) ? fallbackY : world.floor1Y, sz);
          s.speed = 0;
          s.yawVel = 0;
        }
      }

      const now = performance.now();
      const oneShot = now < s.oneShotUntil;
      if (!oneShot) {
        if (Math.abs(turnKey) > 0 && Math.abs(s.speed) < 0.05) fadeTo('turn');
        else if (s.speed > 1.9) fadeTo('run');
        else if (Math.abs(s.speed) > 0.12) fadeTo('walk');
        else fadeTo('idle');
      }
      if (keys.current.has('Space') && !oneShot) {
        keys.current.delete('Space');
        playOneShot('happy');
      }
    }

    // 展品接近：同层 + 距离阈值（带迟滞），靠近就好奇地看一眼并打开文化卡
    const now = performance.now();
    let nearest: string | null = null;
    let nearestDist = Infinity;
    for (const frame of world.exhibits) {
      const floorY = frame.floor === 1 ? world.floor1Y : world.floor2Y;
      if (Math.abs(floorY - s.position.y) > EXHIBIT.sameFloorDelta) continue;
      const distance = Math.hypot(frame.x - s.position.x, frame.z - s.position.z);
      if (distance < nearestDist) {
        nearestDist = distance;
        nearest = frame.id;
      }
    }
    const inRange = Boolean(nearest) && nearestDist <= (s.nearest === nearest ? EXHIBIT.leaveDistance : EXHIBIT.enterDistance);
    if (inRange && nearest && nearest !== s.nearest && s.moved > 0.6 && now - s.lastExhibitAt > EXHIBIT.cooldownMs) {
      s.lastExhibitAt = now;
      onExhibit(nearest);
      playOneShot('curious');
    }
    s.nearest = inRange ? nearest : null;

    root.position.copy(s.position);
    root.rotation.y = s.yaw;

    // 相机：第三人称跟随 / 第一人称（第一人称时隐藏头部网格）
    s.camBlend = Math.min(1, s.camBlend + dt / CAMERA.spawnBlendSeconds);
    const forward = new THREE.Vector3(0, 0, -1).applyAxisAngle(UP_AXIS, s.yaw);
    if (view === 'third') {
      // 室内家具多，第三人称用「高位后上方」的引导机位：越过展柜看角色。
      const pivot = new THREE.Vector3()
        .copy(s.position)
        .add(new THREE.Vector3(0, CAMERA.thirdLookHeight, 0));
      const offset = new THREE.Vector3()
        .addScaledVector(forward, -CAMERA.thirdDistance)
        .add(new THREE.Vector3(0, CAMERA.thirdHeight, 0));
      const wantDistance = offset.length();

      // 相机遮挡：从角色头顶朝机位打一条射线，撞到墙/梁就把相机拉近到撞点前。
      // 每 2 帧采样一次并缓存结果——角色移动慢，肉眼无差，但省掉一半 raycast。
      s.camTick += 1;
      if (s.camTick % CAMERA.occlusionEvery === 0 && collisionMeshesRef.current.length) {
        const dir = offset.clone().normalize();
        camRay.set(pivot, dir);
        camRay.far = wantDistance;
        const hits = camRay.intersectObjects(collisionMeshesRef.current, true);
        s.camClear = hits.length
          ? Math.max(CAMERA.thirdMinDistance, hits[0].distance - CAMERA.occlusionMargin)
          : wantDistance;
      }
      const allowed = THREE.MathUtils.clamp(s.camClear, CAMERA.thirdMinDistance, wantDistance);
      const desired = pivot.clone().addScaledVector(offset.clone().normalize(), allowed);
      desired.x = THREE.MathUtils.clamp(desired.x, world.hall.minX + 0.35, world.hall.maxX - 0.35);
      desired.z = THREE.MathUtils.clamp(desired.z, world.hall.minZ + 0.35, world.hall.maxZ - 0.35);
      desired.y = THREE.MathUtils.clamp(desired.y, world.floor1Y + 1.6, world.floor2Y + 2.6);
      camera.position.lerp(desired, 1 - Math.exp(-CAMERA.followLambda * s.camBlend * dt));
      camera.lookAt(pivot);
    } else {
      const desired = new THREE.Vector3()
        .copy(s.position)
        .add(new THREE.Vector3(0, CAMERA.firstEyeHeight, 0))
        .addScaledVector(forward, CAMERA.firstForward);
      camera.position.lerp(desired, 1 - Math.exp(-18 * dt));
      camera.lookAt(new THREE.Vector3().copy(desired).add(forward));
    }
    // 第一人称：整只角色隐藏，避免相机卡在头里；楼梯不进这个开关，仍要看得见。
    const body = root.getObjectByName('MASCOT_BODY');
    if (body) body.visible = view !== 'first';

    if (mixerRef.current) mixerRef.current.update(dt);

    (window as unknown as { __mascot?: MascotProbe }).__mascot = {
      active,
      phase,
      view,
      position: [Number(s.position.x.toFixed(2)), Number(s.position.y.toFixed(2)), Number(s.position.z.toFixed(2))],
      yaw: Number(s.yaw.toFixed(2)),
      action: currentAction.current,
      speed: Number(s.speed.toFixed(2)),
      floor: s.position.y > (world.floor1Y + world.floor2Y) / 2 ? 2 : 1,
      nearestFrame: s.nearest,
      hasModel,
      camera: [Number(camera.position.x.toFixed(2)), Number(camera.position.y.toFixed(2)), Number(camera.position.z.toFixed(2))],
    };
  });

  if (!active) return null;

  return (
    <>
      <group ref={rootRef} name="MASCOT_ROOT">
        <group name="MASCOT_BODY">
          {hasModel ? (
            <Suspense fallback={<PlaceholderCat />}>
              <MascotModel onReady={onModelReady} />
            </Suspense>
          ) : (
            <PlaceholderCat />
          )}
        </group>
      </group>
    </>
  );
}

export default MascotCompanion;