/**
 * 纹脉展馆 · 三维场景根节点（双建筑皮肤）
 *
 * 场景内容 = 当前建筑的一份 Blender GLB + 可换画的画框 + 器物 DIY 层。
 *
 * 双馆的关键约定：
 *  - 建筑的一切坐标（机位、展墙、画框、尺寸参数）都从 `BuildingDef` 取，
 *    组件里没有一处手写的建筑常量，所以换馆只是换一份定义；
 *  - 模型由 `modelCache` 预加载，切换发生在「新模型已就绪」之后，
 *    因此不会出现旧建筑已卸载、新建筑还没好的空场白屏；
 *  - 场景内部所有与体量有关的数字（室内盒、落位面、悬挂范围、阴影底座）
 *    都读当前建筑的 SceneSpec，两馆体量差一倍也不会错位。
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { ContactShadows, OrbitControls } from '@react-three/drei';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import * as THREE from 'three';

import type { BuildingDef } from '../buildings';
import type { GalleryConfig } from '../buildings/layout';
import { resolveArtworkId, useActivePlan, useCurationStore } from '../state/curationStore';
import { useBuildingStore } from '../state/buildingStore';
import { useDiyStore } from '../state/diyStore';
import { PALETTE } from './materials';
import { useBuildingAssets } from './GalleryModel';
import { GalleryFrame } from './GalleryFrame';
import { DayNightRig, useTimeExposure, type TimeOfDay } from './DayNightRig';
import { GalleryEnvironment } from './GalleryEnvironment';
import { CinemaRig, FirstPersonRig } from './CameraModes';
import { DiYLayer } from './DiYLayer';
import { findHangTarget } from './placement';
import { StairwellRailing } from './StairwellRailing';
import { DoorInteraction } from './DoorInteraction';
import { MascotCompanion, type MascotView } from '../mascot/MascotCompanion';
import type { ViewMode } from '../components/ViewModeSwitch';
import type { GalleryMode } from '../types';

/* ------------------------------------------------------------------ 渲染观感 */

/**
 * 色调映射：PBR Neutral（Khronos 提出的 NeutralToneMapping）。
 *
 * 之前用 ACESFilmic：它的高光肩部会把暖木的橙压成灰、把白灰泥顶到死白，
 * 室内顶棚与石台基大面积丢层次。Neutral 的肩部更窄、保留原色相，
 * 在「暖木 + 朱红 + 纸白」这种低饱和东方色板上更接近真实漆面/宣纸。
 */
const TONE_MAPPING = THREE.NeutralToneMapping;

/** 纹理各向异性上限：地板/瓦面在斜视角下不糊成一片 */
function applyAnisotropy(root: THREE.Object3D, maxAnisotropy: number): void {
  if (maxAnisotropy <= 1) return;
  const cap = Math.min(8, maxAnisotropy);
  root.traverse((object) => {
    const mesh = object as THREE.Mesh;
    if (!mesh.isMesh) return;
    const raw = mesh.material as THREE.Material | THREE.Material[];
    for (const material of Array.isArray(raw) ? raw : [raw]) {
      const standard = material as THREE.MeshStandardMaterial;
      if (!standard || !standard.map) continue;
      if (standard.map.anisotropy >= cap) continue;
      standard.map.anisotropy = cap;
      standard.map.needsUpdate = true;
    }
  });
}

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

/** 需要压低到仰视的机位（梁架/檐下要抬头看屋顶） */
const LOOK_UP_PRESETS = new Set(['floor1', 'floor2', 'ceiling', 'eave']);

/** 机位切换：位置/朝向/视场角做平滑插值，避免瞬移 */
function CameraRig({
  config,
  presetId,
  buildingId,
  controlsRef,
}: {
  config: GalleryConfig;
  presetId: string;
  buildingId: string;
  controlsRef: React.RefObject<OrbitControlsImpl | null>;
}) {
  const { camera } = useThree();
  const preset = config.cameras.find((item) => item.id === presetId) ?? config.cameras[0];
  // Blender 的焦距按「水平」视场角定义，three 的 camera.fov 是「垂直」的。
  // 换算时固定用 4:3——参考图都是 4:3，固定垂直构图才能在任意窗口比例下
  // 保持上下取景一致（窗口更宽时只在左右多看到一些，而不是把建筑拉高）。
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
  const previousBuilding = useRef(buildingId);

  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls) return;
    // 换馆不走插值：旧馆的机位对新馆没有意义，插值过去会有一秒「镜头在半空乱飞」
    if (previousBuilding.current !== buildingId) {
      previousBuilding.current = buildingId;
      camera.position.set(...preset.position);
      controls.target.set(...preset.target);
      const nextFov = verticalFov(preset.fov ?? 42);
      if ((camera as THREE.PerspectiveCamera).isPerspectiveCamera) {
        (camera as THREE.PerspectiveCamera).fov = nextFov;
        (camera as THREE.PerspectiveCamera).updateProjectionMatrix();
      }
      controls.update();
      progress.current = 1;
      return;
    }
    from.current.copy(camera.position);
    to.current.set(...preset.position);
    targetFrom.current.copy(controls.target);
    targetTo.current.set(...preset.target);
    fovFrom.current = (camera as THREE.PerspectiveCamera).fov;
    fovTo.current = verticalFov(preset.fov ?? 42);
    progress.current = 0;
    // buildingId 进依赖：换馆时即使机位 id 没变，也要重新定位到新馆机位
  }, [presetId, preset, camera, controlsRef, aspect, buildingId]);

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
function FrameProbe({ config }: { config: GalleryConfig }) {
  const { camera, size } = useThree();
  const published = useRef(0);
  const positions = useActivePlan().positions;
  useFrame(({ clock }) => {
    if (import.meta.env.PROD) return;
    if (clock.elapsedTime - published.current < 0.5) return;
    published.current = clock.elapsedTime;
    const list = config.frames.map((frame) => {
      const position = new THREE.Vector3(...positionOf(config, frame.id, positions));
      const projected = position.clone().project(camera);
      return {
        id: frame.id,
        x: Math.round(((projected.x + 1) / 2) * size.width),
        y: Math.round(((1 - projected.y) / 2) * size.height),
        visible: Math.abs(projected.x) < 1 && Math.abs(projected.y) < 1 && projected.z < 1,
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
  config: GalleryConfig,
  frameId: string,
  positions: Record<string, { u: number; v: number }>,
): [number, number, number] {
  const frame = config.frameById.get(frameId);
  if (!frame) return [0, 0, 0];
  const position = positions[frameId] ?? { u: frame.u, v: frame.v };
  const wall = config.wallById.get(frame.wallId);
  if (!wall) return [0, 0, 0];
  return config.wallPointToWorld(wall, position.u, position.v, 0.06);
}

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
        rotation: [found.rotation.x, found.rotation.y, found.rotation.z].map((value) =>
          Number(value.toFixed(4)),
        ),
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
function HangProbe({ structural, spec }: { structural: THREE.Object3D[]; spec: BuildingDef['scene'] }) {
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
        new THREE.Plane(new THREE.Vector3(0, 1, 0), -spec.diy.baseTop),
        floor,
      );
      const target = findHangTarget({
        structural,
        ray: raycaster.ray,
        floorPoint: hasFloor ? floor : null,
        spec: spec.hang,
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
  }, [structural, camera, size, spec]);
  return null;
}

/* ------------------------------------------------------------------ 性能探针 */

/**
 * 帧率探针：把「实测帧率 / 单帧耗时 / draw call / 三角形数 / 当前 pixelRatio」
 * 发布到 window.__galleryPerf，每 500 ms 更新一次。仅开发构建启用。
 */
function PerfProbe() {
  const { gl, scene, setDpr, viewport } = useThree();
  const stat = useRef({ frames: 0, elapsed: 0, last: 0, low: 0, high: 0 });
  useFrame((_, delta) => {
    const t = stat.current;
    t.frames += 1;
    t.elapsed += delta;
    if (t.elapsed - t.last < 0.5) return;
    const span = t.elapsed - t.last;
    t.last = t.elapsed;
    const fps = t.frames / span;
    let lights = 0;
    scene.traverse((object) => {
      if ((object as THREE.Light).isLight) lights += 1;
    });

    // ---- 动态分辨率：真正会生效的那一档优化 ----
    // 连续两次 < 46 fps 就退 0.25 档（最低 1.0）；连续 8 次 > 57 fps 再升回去。
    const current = viewport.dpr;
    if (fps < 46) {
      t.low += 1;
      t.high = 0;
    } else if (fps > 57) {
      t.high += 1;
      t.low = 0;
    } else {
      t.low = 0;
      t.high = 0;
    }
    if (t.low >= 2 && current > 1.0) {
      setDpr(Math.max(1, Number((current - 0.25).toFixed(2))));
      t.low = 0;
    } else if (t.high >= 8 && current < 1.75) {
      setDpr(Math.min(1.75, Number((current + 0.25).toFixed(2))));
      t.high = 0;
    }

    if (import.meta.env.PROD) return;
    (window as unknown as { __galleryPerf?: unknown }).__galleryPerf = {
      fps: Number(fps.toFixed(1)),
      frameMs: Number(((span / t.frames) * 1000).toFixed(2)),
      drawCalls: gl.info.render.calls,
      triangles: gl.info.render.triangles,
      programs: gl.info.programs?.length ?? 0,
      dpr: Number(current.toFixed(2)),
      lights,
      textures: gl.info.memory.textures,
      geometries: gl.info.memory.geometries,
    };
    t.frames = 0;
  });
  return null;
}

/* ------------------------------------------------------------------ 场景 */

function SceneContent({
  building,
  presetId,
  time,
  viewMode,
  diy,
  level,
  onFrameSelect,
  onReady,
  dragging,
  setDragging,
  mascot,
}: {
  building: BuildingDef;
  presetId: string;
  time: TimeOfDay;
  viewMode: ViewMode;
  diy: boolean;
  level: number;
  onFrameSelect: (frameId: string) => void;
  onReady?: (buildingId: string) => void;
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
  const assets = useBuildingAssets(building);
  const config = building.config;
  const spec = building.scene;
  const { gl } = useThree();

  const plan = useActivePlan();
  const selectedFrameId = useCurationStoreSelectedFrame();
  const activeBuildingId = useBuildingStore((state) => state.active);

  // onReady 用 ref 兜住：页面若传了未 memo 的回调，直接进依赖会触发无限重渲染
  const onReadyRef = useRef(onReady);
  useEffect(() => {
    onReadyRef.current = onReady;
  }, [onReady]);
  useEffect(() => {
    if (!assets) return;
    onReadyRef.current?.(building.id);
  }, [assets, building.id]);

  // 斜视角下地板/瓦面的贴图 anisotropy 拉到硬件的 8 倍以内，避免糊成一条灰带
  useEffect(() => {
    if (!assets) return;
    applyAnisotropy(assets.root, gl.capabilities.getMaxAnisotropy());
  }, [assets, gl]);

  // 只有「看房间」的两个机位需要收屋顶；梁架/檐下要看的就是屋顶本身
  const interior = config.hideRoofPresets.has(presetId);

  // 内部机位隐藏屋顶，否则整层被瓦顶盖住，什么也看不见
  useEffect(() => {
    if (!assets) return;
    for (const object of assets.layers.roof) object.visible = !interior;
  }, [interior, assets]);

  /* 描边是「背面外推」的壳：相机站到壳里面（进梁架/檐下/室内机位）时，
     看到的其实是壳的内表面——一整片不受光的平色，会把顶棚压成黑板。
     所以只要相机在室内包围盒里，就把屋顶那几张网的轮廓收起来。 */
  const roofHullHidden = useRef<boolean | null>(null);
  useFrame(({ camera }) => {
    if (!assets) return;
    const { x, y, z } = camera.position;
    const box = spec.interiorBox;
    const inside =
      Math.abs(x) < box.x && Math.abs(z) < box.z && y > box.yMin && y < box.yMax;
    if (roofHullHidden.current === inside) return;
    roofHullHidden.current = inside;
    for (const outline of assets.layers.roofOutlines) outline.visible = !inside;
    (window as unknown as { __galleryOutlineCulled?: boolean }).__galleryOutlineCulled = inside;
  });

  useEffect(() => {
    if (!assets) return;
    (window as unknown as { __galleryStats?: unknown }).__galleryStats = {
      ...assets.stats,
      buildingId: building.id,
      interior,
      frames: config.frames.length,
      walls: config.walls.length,
    };
  }, [assets, interior, config, building.id]);

  return (
    <>
      <DayNightRig time={time} />
      <ExposureRig time={time} />
      <GalleryEnvironment time={time} />

      {assets ? (
        <>
          <primitive object={assets.root} />
          <DoorInteraction root={assets.root} />

          {config.frames.map((frame) => (
            <GalleryFrame
              key={`${building.id}-${frame.id}`}
              config={config}
              frameId={frame.id}
              artworkId={resolveArtworkId(plan.assignments, frame.id, building.id)}
              u={plan.positions[frame.id]?.u ?? frame.u}
              v={plan.positions[frame.id]?.v ?? frame.v}
              selected={selectedFrameId === frame.id}
              onSelect={onFrameSelect}
            />
          ))}

          {/* 经典馆的二层楼梯井护栏是模型里缺失的，前端补齐；新馆自带 */}
          {spec.stairwellRailing ? <StairwellRailing floorY={spec.diy.floor2} /> : null}

          {mascot ? (
            <MascotCompanion
              key={`mascot-${building.id}`}
              building={building}
              collisionMeshes={assets.layers.meshes}
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
            spec={spec}
            wallMeshes={assets.layers.meshes}
            roofMeshes={assets.layers.roof}
            onDragStateChange={setDragging}
          />

          <ContactShadows
            position={[0, spec.contactShadow.y, 0]}
            // 只有一层「贴地暗部」：不透明度略提高，弥补分辨率下调后的边界变软
            opacity={0.38}
            scale={spec.contactShadow.scale}
            blur={2.6}
            far={spec.contactShadow.far}
            // 768² 而不是 1024²：一次性烘焙（frames=1）下省 44% 显存/填充率
            resolution={768}
            color="#2a1d16"
            // 建筑与展品都是静态的，接触阴影烘一次就够；
            // 每帧重算会让低端 GPU 直接掉到个位数帧率。
            frames={1}
          />
        </>
      ) : null}

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
            maxPolarAngle={LOOK_UP_PRESETS.has(presetId) ? Math.PI * 0.95 : Math.PI / 2 - 0.04}
            target={spec.orbitTarget}
            makeDefault
          />
          <CameraRig
            config={config}
            presetId={presetId}
            buildingId={building.id}
            controlsRef={controlsRef}
          />
        </>
      )}
      {viewMode === 'cinema' && <CinemaRig active spec={spec} />}
      {viewMode === 'first' && <FirstPersonRig active spec={spec} />}
      <FrameProbe config={config} />
      <PickingProbe />
      {assets ? <HangProbe structural={assets.layers.meshes} spec={spec} /> : null}
      <PerfProbe />
    </>
  );
}

/** 只订阅选中画框 id，避免场景整体依赖布展 store 的其它字段 */
function useCurationStoreSelectedFrame(): string | null {
  return useCurationStore((state) => state.selectedFrameId);
}

export interface HeritageSceneProps {
  /** 当前建筑皮肤 */
  building: BuildingDef;
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
  /** 模型就绪回调：页面据此关闭切换遮罩 */
  onReady?: (buildingId: string) => void;
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
  building,
  presetId,
  mode = 'exterior',
  time = 'day',
  viewMode = 'third',
  diy = false,
  level = 1,
  onFrameSelect,
  onReady,
  mascot,
}: HeritageSceneProps) {
  const [dragging, setDragging] = useState(false);
  // 页面切到后台/别的标签页时把渲染循环停下（frameloop="never"）：
  // 这是最实在的一条省电/省 GPU 措施，回来时自动续上，交互无感。
  const [pageVisible, setPageVisible] = useState<boolean>(() =>
    typeof document === 'undefined' ? true : !document.hidden,
  );
  useEffect(() => {
    const onVisibility = () => setPageVisible(!document.hidden);
    document.addEventListener('visibilitychange', onVisibility);
    return () => document.removeEventListener('visibilitychange', onVisibility);
  }, []);
  const initial = building.config.cameras.find((item) => item.id === presetId) ?? building.config.cameras[0];
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
        // 换馆时重建 WebGL 上下文没有意义（会丢纹理与阴影缓存），
        // 这里靠 SceneContent 内部替换 root 完成切换。
        shadows
        // dpr 上限 1.75：4K/Retina 上把像素量压到 1/1.9，观感几乎无差；
        // PerfProbe 里的动态分辨率还会在掉帧时继续往 1.0 退。
        dpr={[1, 1.75]}
        frameloop={pageVisible ? 'always' : 'never'}
        camera={{
          position: initial.position,
          fov: initialFov,
          near: 0.1,
          far: 320,
        }}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: 'high-performance',
          // 场景里没有任何地方用模板缓冲，关掉省一份带宽
          stencil: false,
        }}
        style={{ background: PALETTE.sky, cursor: dragging ? 'grabbing' : 'grab' }}
        onCreated={({ gl }) => {
          gl.toneMapping = TONE_MAPPING;
          gl.toneMappingExposure = useTimeExposure(time);
          gl.shadowMap.type = THREE.PCFSoftShadowMap;
          gl.shadowMap.enabled = true;
        }}
      >
        <SceneContent
          building={building}
          presetId={presetId}
          time={time}
          viewMode={viewMode}
          diy={diy}
          level={level}
          onFrameSelect={onFrameSelect}
          onReady={onReady}
          dragging={dragging}
          setDragging={handleDragState}
          mascot={mascot}
        />
      </Canvas>
    </div>
  );
}