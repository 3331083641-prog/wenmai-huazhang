import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';

import {
  EXHIBIT_POINTS,
  HALL,
  CAMERA,
  EXHIBIT,
  FLOOR1_Y,
  FLOOR2_Y,
  MOTION,
  SPAWN,
  STAIR,
  canStandAt,
  clampToHall,
  groundHeightAt,
} from './mascotConfig';

export type MascotView = 'third' | 'first';
export type MascotPhase = 'spawning' | 'ready';

export interface MascotProbe {
  active: boolean;
  phase: MascotPhase;
  view: MascotView;
  position: [number, number, number];
  yaw: number;
  action: string;
  floor: 1 | 2;
  nearestFrame: string | null;
  hasModel: boolean;
  camera: [number, number, number];
}

export interface MascotCompanionProps {
  active: boolean;
  /** 馆体网格：第三人称相机用它做射线碰撞，避免穿墙 */
  collisionMeshes?: THREE.Object3D[];
  view: MascotView;
  onExit: () => void;
  onViewChange: (view: MascotView) => void;
  /** 靠近展品 / 按 E 时回调，页面据此打开已有文化卡。 */
  onExhibit: (frameId: string) => void;
}

const ONE_SHOT = new Set(['Spawn', 'Happy', 'Interact']);

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

function MascotModel({
  onReady,
}: {
  onReady: (mixer: THREE.AnimationMixer, actions: Record<string, THREE.AnimationAction>) => void;
}) {
  const { scene, animations } = useGLTF(`${import.meta.env.BASE_URL}models/wenmai_mascot_ww.glb`);
  const mixer = useMemo(() => new THREE.AnimationMixer(scene), [scene]);

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

  return <primitive object={scene} />;
}

/* ------------------------------------------------------------------ 楼梯 */

/* ------------------------------------------------------------------ 主组件 */

export function MascotCompanion({ active, view, collisionMeshes, onExit, onViewChange, onExhibit }: MascotCompanionProps) {
  const { camera } = useThree();
  const rootRef = useRef<THREE.Group>(null);
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const actionsRef = useRef<Record<string, THREE.AnimationAction>>({});
  const currentClip = useRef('Idle');

  const [hasModel, setHasModel] = useState(false);
  const [phase, setPhase] = useState<MascotPhase>('spawning');

  const state = useRef({
    position: new THREE.Vector3(...SPAWN.outside),
    yaw: SPAWN.lookYaw,
    spawnT: 0,
    nearest: null as string | null,
    lastExhibitAt: 0,
    moved: 0,
    oneShotUntil: 0,
    camBlend: 0,
  });
  const keys = useRef<Set<string>>(new Set());
  const s0 = state;
  const camRay = useMemo(() => new THREE.Raycaster(), []);
  const collisionMeshesRef = useRef<THREE.Object3D[]>([]);
  const obstaclesRef = useRef<Array<{ floor: 1 | 2; minX: number; maxX: number; minZ: number; maxZ: number }>>([]);
  const spawnTarget = useRef(new THREE.Vector3(...SPAWN.inside));
  collisionMeshesRef.current = collisionMeshes ?? [];

  /* 模型可用性：dev server 对缺失文件会回落 index.html，必须先验 magic */
  useEffect(() => {
    let cancelled = false;
    fetch(`${import.meta.env.BASE_URL}models/wenmai_mascot_ww.glb`, { cache: 'no-store' })
      .then((res) => res.arrayBuffer())
      .then((buf) => {
        if (cancelled) return;
        setHasModel(String.fromCharCode(...new Uint8Array(buf.slice(0, 4))) === 'glTF');
      })
      .catch(() => {
        if (!cancelled) setHasModel(false);
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
        return [x, FLOOR1_Y, z];
      }
    }
    (window as unknown as { __mascotSpawnDebug?: unknown }).__mascotSpawnDebug = debug;
    return SPAWN.inside;
  }, []);

  /** 把馆体网格里「挡住走路的家具/展柜」抽成二维矩形，按楼层分组。 */
  const buildObstacles = useCallback(() => {
    const meshes = collisionMeshesRef.current;
    const boxes: Array<{ floor: 1 | 2; minX: number; maxX: number; minZ: number; maxZ: number }> = [];
    const box = new THREE.Box3();
    const inStair = (object: THREE.Object3D) => {
      let node: THREE.Object3D | null = object;
      while (node) {
        if (node.name && node.name.startsWith(STAIR.meshPrefix)) return true;
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
      const floor: 1 | 2 = centerY > (FLOOR1_Y + FLOOR2_Y) / 2 ? 2 : 1;
      const floorY = floor === 1 ? FLOOR1_Y : FLOOR2_Y;
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
    const floor: 1 | 2 = y > (FLOOR1_Y + FLOOR2_Y) / 2 ? 2 : 1;
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
    state.current.yaw = SPAWN.lookYaw;
    state.current.spawnT = 0;
    state.current.camBlend = 0;
    state.current.nearest = null;
    setPhase('spawning');
  }, [active, pickSpawn]);

  const fadeTo = useCallback((name: string, duration = 0.25) => {
    if (currentClip.current === name) return;
    const prev = actionsRef.current[currentClip.current];
    const next = actionsRef.current[name];
    if (next) {
      next.reset();
      next.setLoop(ONE_SHOT.has(name) ? THREE.LoopOnce : THREE.LoopRepeat, ONE_SHOT.has(name) ? 1 : Infinity);
      next.clampWhenFinished = name !== 'Spawn';
      next.fadeIn(duration).play();
    }
    if (prev && prev !== next) prev.fadeOut(duration);
    currentClip.current = name;
  }, []);

  const playOneShot = useCallback(
    (name: string) => {
      fadeTo(name, 0.16);
      const duration = actionsRef.current[name]?.getClip().duration ?? 0.9;
      state.current.oneShotUntil = performance.now() + duration * 1000;
    },
    [fadeTo]
  );

  const onModelReady = useCallback(
    (mixer: THREE.AnimationMixer, actions: Record<string, THREE.AnimationAction>) => {
      mixerRef.current = mixer;
      actionsRef.current = actions;
      if (actions.Idle) {
        actions.Idle.play();
        currentClip.current = 'Idle';
      }
      if (actions.Spawn) {
        const spawn = actions.Spawn;
        spawn.reset();
        spawn.setLoop(THREE.LoopOnce, 1);
        spawn.clampWhenFinished = false;
        spawn.play();
        currentClip.current = 'Spawn';
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
          playOneShot('Interact');
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
        s0.current.position.set(x, y ?? groundHeightAt(x, z, s0.current.position.y), z);
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
      s.position.lerpVectors(new THREE.Vector3(...SPAWN.outside), spawnTarget.current, ease);
      s.position.y = FLOOR1_Y + Math.sin(Math.PI * Math.min(1, s.spawnT / 0.85)) * 0.3;
      if (s.spawnT >= 1) {
        s.position.copy(spawnTarget.current);
        setPhase('ready');
        fadeTo('Idle', 0.2);
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
      s.yaw += turnKey * MOTION.turnSpeed * dt;

      const speed = forwardKey > 0 ? (running ? MOTION.runSpeed : MOTION.walkSpeed) : forwardKey < 0 ? -MOTION.backSpeed : 0;
      if (speed !== 0) {
        s.moved += Math.abs(speed * dt);
        const forward = new THREE.Vector3(0, 0, -1).applyAxisAngle(new THREE.Vector3(0, 1, 0), s.yaw);
        const step = THREE.MathUtils.clamp(speed * dt, -MOTION.maxStep, MOTION.maxStep);
        const [cx, cz] = clampToHall(s.position.x + forward.x * step, s.position.z + forward.z * step);
        // 只按障碍盒判碰撞：楼梯踏步/栏杆本身就是通道，用射线打会把自己挡住
        const blocked = blockedAt(cx, cz, s.position.y);
        if (!blocked && canStandAt(cx, cz, s.position.y)) {
          s.position.x = cx;
          s.position.z = cz;
          s.position.y = groundHeightAt(cx, cz, s.position.y);
        }
      }

      const now = performance.now();
      const oneShot = now < s.oneShotUntil;
      if (!oneShot) {
        if (Math.abs(turnKey) > 0 && speed === 0) fadeTo('Turn');
        else if (speed > 1.9) fadeTo('Run');
        else if (speed !== 0) fadeTo('Walk');
        else fadeTo('Idle');
      }
      if (keys.current.has('Space') && !oneShot) {
        keys.current.delete('Space');
        playOneShot('Happy');
      }
    }

    // 展品接近：同层 + 距离阈值（带迟滞），靠近就好奇地看一眼并打开文化卡
    const now = performance.now();
    let nearest: string | null = null;
    let nearestDist = Infinity;
    for (const frame of EXHIBIT_POINTS) {
      const floorY = frame.floor === 1 ? FLOOR1_Y : FLOOR2_Y;
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
      playOneShot('Curious');
    }
    s.nearest = inRange ? nearest : null;

    root.position.copy(s.position);
    root.rotation.y = s.yaw;

    // 相机：第三人称跟随 / 第一人称（第一人称时隐藏头部网格）
    s.camBlend = Math.min(1, s.camBlend + dt / CAMERA.spawnBlendSeconds);
    const forward = new THREE.Vector3(0, 0, -1).applyAxisAngle(new THREE.Vector3(0, 1, 0), s.yaw);
    if (view === 'third') {
      const desired = new THREE.Vector3()
        .copy(s.position)
        .addScaledVector(forward, -CAMERA.thirdDistance)
        .add(new THREE.Vector3(0, CAMERA.thirdHeight, 0));
      // 室内家具多，第三人称改用「高位后上方」的引导机位：
      // 越过展柜看角色，比贴着地面做射线碰撞稳，也不会把相机挤进家具里。
      desired.x = THREE.MathUtils.clamp(desired.x, HALL.minX + 0.35, HALL.maxX - 0.35);
      desired.z = THREE.MathUtils.clamp(desired.z, HALL.minZ + 0.35, HALL.maxZ - 0.35);
      desired.y = THREE.MathUtils.clamp(desired.y, FLOOR1_Y + 1.6, FLOOR2_Y + 2.6);
      camera.position.lerp(desired, 1 - Math.exp(-CAMERA.followLambda * s.camBlend * dt));
      camera.lookAt(new THREE.Vector3().copy(s.position).add(new THREE.Vector3(0, CAMERA.thirdLookHeight, 0)));
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
      action: currentClip.current,
      floor: s.position.y > (FLOOR1_Y + FLOOR2_Y) / 2 ? 2 : 1,
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