/**
 * 纹脉展馆 · 三维场景根节点
 *
 * 场景内容 = 一个真实的 Blender 模型（GLB）+ 可换画的画框 + 三渲二材质。
 * 不再用程序化几何体拼建筑：`scene/Base.tsx`、`scene/Pavilion.tsx` 是旧版程序化实现，
 * 现在只保留作对照，页面不再引用。
 *
 * 机位、展墙、画框全部读 `data/heritageGalleryConfig`（由 Blender 导出），
 * 所以场景里没有一处手写的建筑坐标。
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { ContactShadows, OrbitControls } from '@react-three/drei';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import * as THREE from 'three';

import {
  HIDE_ROOF_PRESETS,
  cameraPresets,
  frameSlots,
  galleryWalls,
  presetById,
} from '../../../data/heritageGalleryConfig';
import { useCurationStore, resolveArtworkId } from '../state/curationStore';
import { useDiyStore } from '../state/diyStore';
import { PALETTE } from './materials';
import { useGalleryAssets } from './GalleryModel';
import { GalleryFrame } from './GalleryFrame';
import { DayNightRig, useTimeExposure, type TimeOfDay } from './DayNightRig';
import { CinemaRig, FirstPersonRig } from './CameraModes';
import { DiYLayer } from './DiYLayer';
import { findHangTarget } from './placement';
import { StairwellRailing } from './StairwellRailing';
import { DoorInteraction } from './DoorInteraction';
import { MascotCompanion, type MascotView } from '../mascot/MascotCompanion';
import type { ViewMode } from '../components/ViewModeSwitch';
import type { GalleryMode } from '../types';

/* ------------------------------------------------------------------ 曝光 */

/** 昼夜切换时同步 renderer 曝光；写在这里，Canvas 只建一次 */
function ExposureRig({ time }: { time: TimeOfDay }) {
  const { gl } = useThree();
  const exposure = useTimeExposure(time);
  useEffect(() => {
    gl.toneMappingExposure = exposure;
  }, [gl, exposure]);
  return null;
}

/* ------------------------------------------------------------------ 相机 */

const TRANSITION = 0.85;

/** 参考图统一为 4:3，垂直取景以它为基准 */
const REFERENCE_ASPECT = 4 / 3;

/** 机位切换：位置/朝向/视场角做平滑插值，避免瞬移 */
function CameraRig({
  presetId,
  controlsRef,
}: {
  presetId: string;
  controlsRef: React.RefObject<OrbitControlsImpl | null>;
}) {
  const { camera } = useThree();
  const preset = presetById.get(presetId) ?? cameraPresets[0];
  // Blender 的焦距按「水平」视场角定义，three 的 camera.fov 是「垂直」的。
  // 换算时固定用 4:3——十张参考图都是 4:3，固定垂直构图才能在任意窗口比例下
  // 保持与参考一致的上下取景（窗口更宽时只在左右多看到一些，而不是把建筑拉高）。
  const aspect = REFERENCE_ASPECT;
  const verticalFov = (horizontal: number) =>
    (2 * Math.atan(Math.tan((horizontal * Math.PI) / 360) / aspect) * 180) / Math.PI;

  const from = useRef(new THREE.Vector3());
  const to = useRef(new THREE.Vector3());
  const targetFrom = useRef(new THREE.Vector3());
  const targetTo = useRef(new THREE.Vector3());
  const fovFrom = useRef(42);
  const fovTo = useRef(42);
  const progress = useRef(1);

  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls) return;
    from.current.copy(camera.position);
    to.current.set(...preset.position);
    targetFrom.current.copy(controls.target);
    targetTo.current.set(...preset.target);
    fovFrom.current = (camera as THREE.PerspectiveCamera).fov;
    fovTo.current = verticalFov(preset.fov ?? 42);
    progress.current = 0;
  }, [presetId, preset, camera, controlsRef, aspect]);

  useFrame((_, delta) => {
    if (progress.current >= 1) return;
    progress.current = Math.min(1, progress.current + delta / TRANSITION);
    // easeInOutCubic：起止都不生硬
    const t = progress.current;
    const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

    camera.position.lerpVectors(from.current, to.current, e);
    const controls = controlsRef.current;
    if (controls) {
      controls.target.lerpVectors(targetFrom.current, targetTo.current, e);
      controls.update();
    }
    const fov = fovFrom.current + (fovTo.current - fovFrom.current) * e;
    if ((camera as THREE.PerspectiveCamera).isPerspectiveCamera) {
      (camera as THREE.PerspectiveCamera).fov = fov;
      (camera as THREE.PerspectiveCamera).updateProjectionMatrix();
    }
  });

  return null;
}

/* ------------------------------------------------------------------ 探针 */

/**
 * 把画框的屏幕坐标发布到 window.__galleryProbe。
 * 浏览器验收时用它证明「画框确实挂在墙上、且画面可见」，
 * 不依赖人眼截图判断。仅在开发环境启用。
 */
function FrameProbe() {
  const { camera, size } = useThree();
  const published = useRef(0);
  useFrame(({ clock }) => {
    if (import.meta.env.PROD) return;
    if (clock.elapsedTime - published.current < 0.5) return;
    published.current = clock.elapsedTime;
    const store = useCurationStore.getState();
    const list = frameSlots.map((frame) => {
      const position = new THREE.Vector3(...positionOf(frame.id, store.positions));
      const projected = position.clone().project(camera);
      return {
        id: frame.id,
        x: Math.round(((projected.x + 1) / 2) * size.width),
        y: Math.round(((1 - projected.y) / 2) * size.height),
        visible: Math.abs(projected.x) < 1 && Math.abs(projected.y) < 1 && projected.z < 1,
        artworkId: resolveArtworkId(store.assignments, frame.id),
      };
    });
    (window as unknown as { __galleryProbe?: unknown }).__galleryProbe = list;
    // 验收探针：当前相机位置，用来判断机位切换是否真的到位
    (window as unknown as { __galleryCamera?: unknown }).__galleryCamera =
      camera.position.toArray().map((value) => Number(value.toFixed(2)));
  });
  return null;
}

/** 画框当前位置（含用户拖拽偏移），与 GalleryFrame 内部算法保持一致 */
function positionOf(
  frameId: string,
  positions: Record<string, { u: number; v: number }>,
): [number, number, number] {
  const frame = frameSlots.find((item) => item.id === frameId);
  if (!frame) return [0, 0, 0];
  const position = positions[frameId] ?? { u: frame.u, v: frame.v };
  const wall = wallCache.get(frame.wallId);
  if (!wall) return [0, 0, 0];
  const localX = (position.u - 0.5) * wall.size[0];
  const localY = (position.v - 0.5) * wall.size[1];
  const cos = Math.cos(wall.rotationY);
  const sin = Math.sin(wall.rotationY);
  return [
    wall.center[0] + localX * cos + sin * 0.06,
    wall.center[1] + localY,
    wall.center[2] - localX * sin + cos * 0.06,
  ];
}

const wallCache = new Map(galleryWalls.map((wall) => [wall.id, wall]));

/* ------------------------------------------------------------------ 拾取调试 */

/**
 * 开发用拾取探针：`window.__galleryPick(x, y)` 返回该屏幕点命中的节点名链。
 * 自动化验收用它判断「点画框为什么没反应」——是没命中，还是被墙板挡住。
 * 生产构建下不挂载。
 */
function PickingProbe() {
  const { camera, scene, size } = useThree();
  useEffect(() => {
    if (import.meta.env.PROD) return;
    const raycaster = new THREE.Raycaster();
    const view = window as unknown as {
      __galleryPick?: (x: number, y: number) => unknown;
      __galleryProject?: (x: number, y: number, z: number) => unknown;
      __gallerySnapshot?: (prefix: string) => unknown;
      __galleryPart?: (name: string) => unknown;
    };
    view.__galleryPick = (x: number, y: number) => {
      raycaster.setFromCamera(
        new THREE.Vector2((x / size.width) * 2 - 1, -(y / size.height) * 2 + 1),
        camera,
      );
      const hits = raycaster.intersectObjects(scene.children, true);
      return hits.slice(0, 6).map((hit) => {
        const names: string[] = [];
        let node: THREE.Object3D | null = hit.object;
        while (node && names.length < 4) {
          if (node.name) names.push(node.name);
          node = node.parent;
        }
        return { names, distance: Number(hit.distance.toFixed(2)) };
      });
    };
    // 世界坐标 -> 屏幕像素：验收脚本用它在真实渲染里定位器物，
    // 不再靠盲扫屏幕猜位置（也用于确认器物确实在视口内）。
    view.__galleryProject = (x: number, y: number, z: number) => {
      const point = new THREE.Vector3(x, y, z).project(camera);
      return {
        x: Math.round(((point.x + 1) / 2) * size.width),
        y: Math.round(((1 - point.y) / 2) * size.height),
        z: Number(point.z.toFixed(3)),
        inView: Math.abs(point.x) < 1 && Math.abs(point.y) < 1 && point.z < 1,
      };
    };
    // 器物内部零件姿态快照：比较点击前后「哪些零件真的动了」
    view.__gallerySnapshot = (prefix: string) => {
      let root: THREE.Object3D | null = null;
      scene.traverse((object) => {
        if (!root && object.name.startsWith(prefix)) root = object;
      });
      if (!root) return null;
      const out: Record<string, number[]> = {};
      (root as THREE.Object3D).traverse((object) => {
        if (!object.name) return;
        out[object.name] = [
          Number(object.position.x.toFixed(4)),
          Number(object.position.y.toFixed(4)),
          Number(object.position.z.toFixed(4)),
          Number(object.rotation.x.toFixed(4)),
          Number(object.rotation.y.toFixed(4)),
          Number(object.rotation.z.toFixed(4)),
        ];
      });
      return out;
    };
    // 单个零件的材质/几何状态：纸被揭起（顶点变形）与灯芯点亮（自发光）
    // 都不体现在 position 上，需要直接读几何与材质。
    view.__galleryPart = (name: string) => {
      let found: THREE.Object3D | null = null;
      scene.traverse((object) => {
        if (!found && object.name === name) found = object;
      });
      if (!found) return null;
      const mesh = found as THREE.Mesh;
      let emissive: number | null = null;
      let geometryZ = null;
      if (mesh.isMesh) {
        const raw = mesh.material as THREE.Material | THREE.Material[];
        const material = (Array.isArray(raw) ? raw[0] : raw) as THREE.MeshStandardMaterial;
        if (material && typeof material.emissiveIntensity === 'number') {
          emissive = Number(material.emissiveIntensity.toFixed(3));
        }
        const position = mesh.geometry.getAttribute('position');
        if (position) {
          let sum = 0;
          for (let i = 0; i < position.count; i += 1) sum += Math.abs(position.getZ(i));
          geometryZ = Number(sum.toFixed(4));
        }
      }
      return {
        emissive,
        geometryZ,
        position: found.position.toArray().map((value) => Number(value.toFixed(4))),
        rotation: [found.rotation.x, found.rotation.y, found.rotation.z].map((value) => Number(value.toFixed(4))),
      };
    };
    return () => {
      delete view.__galleryPick;
      delete view.__galleryProject;
      delete view.__gallerySnapshot;
      delete view.__galleryPart;
    };
  }, [camera, scene, size]);
  return null;
}

/**
 * 悬挂锚点探针：`window.__galleryHang(x, y)` 返回该屏幕点能不能挂、挂在哪。
 * 浏览器验收用它确认「宫灯必须吸到梁架，不允许悬空」，也用来标出梁下可挂区域。
 */
function HangProbe({ structural }: { structural: THREE.Object3D[] }) {
  const { camera, size } = useThree();
  useEffect(() => {
    if (import.meta.env.PROD) return;
    const raycaster = new THREE.Raycaster();
    const view = window as unknown as {
      __galleryHang?: (x: number, y: number) => unknown;
    };
    view.__galleryHang = (x: number, y: number) => {
      raycaster.setFromCamera(
        new THREE.Vector2((x / size.width) * 2 - 1, -(y / size.height) * 2 + 1),
        camera,
      );
      const floor = new THREE.Vector3();
      const hasFloor = raycaster.ray.intersectPlane(
        new THREE.Plane(new THREE.Vector3(0, 1, 0), -0.25),
        floor,
      );
      const target = findHangTarget({
        structural,
        ray: raycaster.ray,
        floorPoint: hasFloor ? floor : null,
      });
      return target
        ? {
            x: Number(target.point.x.toFixed(2)),
            y: Number(target.point.y.toFixed(2)),
            z: Number(target.point.z.toFixed(2)),
            carrier: target.carrier,
          }
        : null;
    };
    return () => {
      delete view.__galleryHang;
    };
  }, [structural, camera, size]);
  return null;
}

/* ------------------------------------------------------------------ 场景 */

function SceneContent({
  presetId,
  mode,
  time,
  viewMode,
  diy,
  level,
  onFrameSelect,
  dragging,
  setDragging,
  mascot,
}: {
  presetId: string;
  mode: GalleryMode;
  time: TimeOfDay;
  viewMode: ViewMode;
  diy: boolean;
  level: number;
  onFrameSelect: (frameId: string) => void;
  dragging: boolean;
  setDragging: (value: boolean) => void;
  mascot?: {
    active: boolean;
    view: MascotView;
    onExit: () => void;
    onViewChange: (view: MascotView) => void;
    onExhibit: (frameId: string) => void;
  };
}) {
  const controlsRef = useRef<OrbitControlsImpl | null>(null);
  const { root, layers, stats } = useGalleryAssets();
  // 只有「看房间」的两个机位需要收屋顶；梁架/檐下要看的就是屋顶本身，
  // 收掉它们会直接看到天。
  const interior = HIDE_ROOF_PRESETS.has(presetId);

  const assignments = useCurationStore((state) => state.assignments);
  const positions = useCurationStore((state) => state.positions);
  const selectedFrameId = useCurationStore((state) => state.selectedFrameId);
  const moveFrame = useCurationStore((state) => state.moveFrame);

  // 内部机位隐藏屋顶，否则整层被瓦顶盖住，什么也看不见
  useEffect(() => {
    for (const object of layers.roof) object.visible = !interior;
  }, [interior, layers.roof]);

  /* 描边是「背面外推」的壳：相机站到壳里面（进梁架/檐下/室内机位）时，
     看到的其实是壳的内表面——一整片不受光的平色，会把顶棚压成黑板。
     所以只要相机在室内包围盒里，就把屋顶那几张网的轮廓收起来。 */
  const roofHullHidden = useRef<boolean | null>(null);
  useFrame(({ camera }) => {
    const { x, y, z } = camera.position;
    const inside = Math.abs(x) < 4.35 && Math.abs(z) < 4.05 && y > 0.15 && y < 7.0;
    if (roofHullHidden.current === inside) return;
    roofHullHidden.current = inside;
    for (const outline of layers.roofOutlines) outline.visible = !inside;
    (window as unknown as { __galleryOutlineCulled?: boolean }).__galleryOutlineCulled = inside;
  });

  useEffect(() => {
    (window as unknown as { __galleryStats?: unknown }).__galleryStats = {
      ...stats,
      interior,
      frames: frameSlots.length,
    };
  }, [stats, interior]);

  return (
    <>
      <DayNightRig time={time} />
      <ExposureRig time={time} />
      <primitive object={root} />
      <DoorInteraction root={root} />

      {frameSlots.map((frame) => (
        <GalleryFrame
          key={frame.id}
          frameId={frame.id}
          artworkId={resolveArtworkId(assignments, frame.id)}
          u={positions[frame.id]?.u ?? frame.u}
          v={positions[frame.id]?.v ?? frame.v}
          selected={selectedFrameId === frame.id}
          onSelect={onFrameSelect}
        />
      ))}

      {/* 二层楼梯井护栏：模型里原有的两段栏杆已删除，井口按原木作样式补齐 */}
      <StairwellRailing floorY={3.6} />

      {mascot ? (
        <MascotCompanion
          collisionMeshes={layers.meshes}
          active={mascot.active}
          view={mascot.view}
          onExit={mascot.onExit}
          onViewChange={mascot.onViewChange}
          onExhibit={mascot.onExhibit}
        />
      ) : null}

      <DiYLayer
        enabled={diy && viewMode !== 'first' && !mascot?.active}
        level={level}
        wallMeshes={layers.meshes}
        roofMeshes={layers.roof}
        onDragStateChange={setDragging}
      />

      <ContactShadows
        position={[0, -0.67, 0]}
        opacity={0.34}
        // 底座 14 m：阴影面收到 17 m 就够托住模型，再大就摊成一片灰地
        scale={17}
        blur={2.2}
        far={6}
        resolution={1024}
        color="#2a1d16"
        // 建筑与展品都是静态的，接触阴影烘一次就够；
        // 每帧重算会让低端 GPU 直接掉到个位数帧率。
        frames={1}
      />

      {!mascot?.active && viewMode === 'third' && (
        <>
          <OrbitControls
            ref={controlsRef}
            enabled={!dragging}
            enableDamping
            dampingFactor={0.06}
            rotateSpeed={0.62}
            panSpeed={0.7}
            zoomSpeed={0.85}
            minDistance={2.4}
            maxDistance={52}
            // 室内机位（尤其「梁架」）要求相机低于视点仰头看，旧的
            // maxPolarAngle = 90° 会把相机强行抬到目标点上方，
            // 结果梁架机位被顶到屋顶外面，只拍到瓦面。
            maxPolarAngle={
              ['floor1', 'floor2', 'ceiling', 'eave'].includes(presetId)
                ? Math.PI * 0.95
                : Math.PI / 2 - 0.04
            }
            target={[0, 3.6, 0]}
            makeDefault
          />
          <CameraRig presetId={presetId} controlsRef={controlsRef} />
        </>
      )}
      {viewMode === 'cinema' && <CinemaRig active />}
      {viewMode === 'first' && <FirstPersonRig active floorY={0.25} />}
      <FrameProbe />
      <PickingProbe />
      <HangProbe structural={layers.meshes} />
    </>
  );
}

export interface HeritageSceneProps {
  presetId: string;
  /** 浏览模式；缺省按外观处理 */
  mode?: GalleryMode;
  /** 时段：白天 / 黄昏 / 夜晚 */
  time?: TimeOfDay;
  /** 视角：第三人称 / 电影 / 第一人称 */
  viewMode?: ViewMode;
  /** 是否启用 DIY 器物层 */
  diy?: boolean;
  /** DIY 落位标高：1 = 台面与一层，2 = 二层回廊 */
  level?: number;
  onFrameSelect: (frameId: string) => void;
  /** 展馆萌宠「纹纹」的探索模式；不传即普通看展 */
  mascot?: {
    active: boolean;
    view: MascotView;
    onExit: () => void;
    onViewChange: (view: MascotView) => void;
    onExhibit: (frameId: string) => void;
  };
}

export function HeritageScene({
  presetId,
  mode = 'exterior',
  time = 'day',
  viewMode = 'third',
  diy = false,
  level = 1,
  onFrameSelect,
  mascot,
}: HeritageSceneProps) {
  const [dragging, setDragging] = useState(false);
  const initial = presetById.get(presetId) ?? cameraPresets[0];
  // 初始视场角按参考图的 4:3 换算，与 CameraRig 的取景口径保持一致
  const initialFov =
    (2 * Math.atan(Math.tan(((initial.fov ?? 42) * Math.PI) / 360) / (4 / 3)) * 180) / Math.PI;
  const handleDragState = useCallback((value: boolean) => setDragging(value), []);
  const setDropRequest = useDiyStore((state) => state.setDropRequest);

  return (
    <div
      className="h-full w-full"
      onDragOver={(event) => {
        if (diy) {
          event.preventDefault();
          event.dataTransfer.dropEffect = 'copy';
        }
      }}
      onDrop={(event) => {
        if (!diy) return;
        const propId = event.dataTransfer.getData('text/x-wenmai-prop');
        if (!propId) return;
        event.preventDefault();
        setDropRequest({ propId, clientX: event.clientX, clientY: event.clientY });
      }}
    >
      <Canvas
        shadows
        dpr={[1, 1.8]}
        camera={{
          position: initial.position,
          fov: initialFov,
          near: 0.1,
          far: 320,
        }}
        gl={{ antialias: true, alpha: false, powerPreference: 'high-performance' }}
        style={{ background: PALETTE.sky, cursor: dragging ? 'grabbing' : 'grab' }}
        onCreated={({ gl }) => {
          gl.toneMapping = THREE.ACESFilmicToneMapping;
          gl.toneMappingExposure = useTimeExposure(time);
          gl.shadowMap.type = THREE.PCFSoftShadowMap;
          gl.shadowMap.enabled = true;
        }}
      >
        <SceneContent
          presetId={presetId}
          mode={mode}
          time={time}
          viewMode={viewMode}
          diy={diy}
          level={level}
          onFrameSelect={onFrameSelect}
          dragging={dragging}
          setDragging={handleDragState}
          mascot={mascot}
      />
      </Canvas>
    </div>
  );
}