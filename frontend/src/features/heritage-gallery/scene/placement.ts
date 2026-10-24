/**
 * 器物摆放的几何求解：顶面吸附（surface）与梁架悬挂（hang）。
 *
 * 只用射线打已有几何，不写死任何器物/梁架坐标：
 *  - surface：优先「直接点在已摆器物上」→ 取该实例的世界包围盒顶面；
 *    否则从落点正上方向下打一条射线，取最高的朝上平面（器物顶面 / 展柜顶 / 模型台面）。
 *  - hang：同样从落点上方往下打，取第一个朝下的面（梁底 / 屋面底），作为悬挂锚点；
 *    找不到就返回 null，由调用方拒绝落位并给出提示，绝不允许悬空。
 */

import * as THREE from 'three';

/** 顶面吸附结果 */
export interface SurfaceTarget {
  /** 器物底面应处的世界高度 */
  y: number;
  /** 落点（承载面之上的世界坐标） */
  point: THREE.Vector3;
  /** 承载物是已摆器物时记录其实例 key */
  parentKey?: string;
  /** 承载面来源描述，用于提示与验收 */
  carrier: string;
  source: 'prop' | 'model';
}

/** 悬挂锚点 */
export interface HangTarget {
  /** 悬挂点（器物顶端贴合此处）世界高度 */
  y: number;
  /** 锚点世界坐标（决定悬挂件的 x/z） */
  point: THREE.Vector3;
  carrier: string;
}

const DOWN = new THREE.Vector3(0, -1, 0);

/**
 * 悬挂/吸附的几何范围。
 *
 * 以前这些值是写死的，只对经典馆成立；新馆更高更宽，必须由建筑定义传入
 * （buildings/layout.ts 的 deriveSceneSpec 按 envelope 推导）。
 * 这里保留经典馆的数值作为默认，方便尚未接参数的调用点继续工作。
 */
export interface HangSpec {
  /** 扫描柱起点高度：高于整馆脊线 */
  columnTop: number;
  /** 悬挂锚点允许的最低高度：低于一层梁架会撞人 */
  minY: number;
  /** 悬挂锚点允许的最高高度：高于屋面则等于悬空 */
  maxY: number;
  /** 落点允许范围：建筑外轮廓 + 一圈檐口 */
  bounds: { x: number; z: number };
}

export const DEFAULT_HANG_SPEC: HangSpec = {
  columnTop: 13,
  minY: 2.35,
  maxY: 7.6,
  bounds: { x: 4.7, z: 4.5 },
};

/**
 * 可以挂东西的构件名称。
 *
 * 只认梁架（BEAM / JOIST / PURLIN / RAFTER）与屋面（ROOF_*）的朝下表面：
 * 二层楼板、墙面、栏杆、窗框下面挂灯，看着就像灯粘在天花板上，
 * 而且会让「没有梁就拒绝」这条规则形同虚设。
 */
function isHangCarrier(name: string): boolean {
  if (!name) return false;
  if (/BEAM|JOIST|PURLIN|RAFTER/i.test(name)) return true;
  return /^ROOF_/i.test(name);
}

function faceNormal(hit: THREE.Intersection): THREE.Vector3 | null {
  const face = hit.face;
  if (!face) return null;
  const normal = face.normal.clone();
  normal.applyNormalMatrix(new THREE.Matrix3().getNormalMatrix(hit.object.matrixWorld));
  return normal.normalize();
}

/** 从命中对象往上找带 diyKey 的实例分组 */
function itemNodeOf(object: THREE.Object3D, root: THREE.Object3D | null): THREE.Object3D | null {
  let node: THREE.Object3D | null = object;
  while (node) {
    if ((node.userData as { diyKey?: string }).diyKey) return node;
    if (node === root) break;
    node = node.parent;
  }
  return null;
}

const _probe = new THREE.Raycaster();
const _column = new THREE.Raycaster();

/**
 * 求顶面吸附点。
 *
 * @param ray        鼠标射线（摄像头方向）
 * @param floorPoint 该射线与落位面的交点，用来定位「正上方那一列」
 * @param placedRoot 已摆器物的父节点（每个实例分组带 userData.diyKey）
 * @param structural 建筑网格（墙、地面、展柜等）
 * @param roof       屋顶网格集合，不参与台面吸附（否则会把器物摆到瓦面上）
 * @param minY       允许的最低台面高度（通常等于落位面高度）
 * @param excludeKey 被拖动的器物 key，自身不能当承载物
 * @param footprint  被摆器物的占地，用于把落点夹在承载面之内
 */
export function findSurfaceTarget(options: {
  ray: THREE.Ray;
  floorPoint?: THREE.Vector3 | null;
  placedRoot: THREE.Object3D | null;
  structural: THREE.Object3D[];
  roof: Set<THREE.Object3D>;
  minY: number;
  /** 承载面允许的最高点（防止一层布展吸到二层楼板） */
  maxY: number;
  excludeKey?: string;
  footprint?: [number, number];
  /** 扫描柱起点（默认经典馆脊高），新馆更高要传自己的 */
  columnTop?: number;
}): SurfaceTarget | null {
  const { ray, floorPoint, placedRoot, structural, roof, minY, maxY, excludeKey, footprint } = options;
  const columnTop = options.columnTop ?? DEFAULT_HANG_SPEC.columnTop;
  _probe.set(ray.origin, ray.direction);
  _probe.near = 0.02;
  _probe.far = 120;

  // A. 直接点在已摆器物上：取该实例世界包围盒的顶面（器身侧面被点中也算）
  if (placedRoot) {
    const hits = _probe.intersectObject(placedRoot, true);
    for (const hit of hits) {
      const node = itemNodeOf(hit.object, placedRoot);
      if (!node) continue;
      const key = (node.userData as { diyKey?: string }).diyKey;
      if (!key || key === excludeKey) continue;
      const box = new THREE.Box3().setFromObject(node);
      if (!Number.isFinite(box.max.y)) continue;
      // 落点取「点中的位置」夹到承载面之内（给被摆器物留出半个体量），
      // 这样点博古架哪一格就摆在哪一格的顶上，而不是永远堆在正中间。
      const halfX = (footprint?.[0] ?? 0) / 2;
      const halfZ = (footprint?.[1] ?? 0) / 2;
      const px = clampAxis(hit.point.x, box.min.x + halfX, box.max.x - halfX);
      const pz = clampAxis(hit.point.z, box.min.z + halfZ, box.max.z - halfZ);
      return {
        y: box.max.y,
        point: new THREE.Vector3(px, box.max.y, pz),
        parentKey: key,
        carrier: (node.userData as { diyName?: string }).diyName ?? '已摆器物',
        source: 'prop',
      };
    }
  }

  // B. 落点正上方向下扫描：取「可达高度以内」最高的朝上平面。
  //    必须有 maxY：否则一层布展会把器物吸到二层楼板（floor2）顶上。
  if (!floorPoint) return null;
  _column.set(new THREE.Vector3(floorPoint.x, columnTop, floorPoint.z), DOWN);
  _column.near = 0.02;
  _column.far = 60;
  const columnHits: THREE.Intersection[] = [];
  if (placedRoot) columnHits.push(..._column.intersectObject(placedRoot, true));
  if (structural.length) columnHits.push(..._column.intersectObjects(structural, true));
  columnHits.sort((a, b) => a.distance - b.distance);

  for (const hit of columnHits) {
    if (roof.has(hit.object)) continue;
    const normal = faceNormal(hit);
    if (!normal || normal.y < 0.5) continue;
    // 地面本身不算「台面」：贴着落位面的命中要跳过，
    // 否则点空地会把小件判成「吸到了模型台面」，还挡住屏幕近邻吸附。
    if (hit.point.y < minY + 0.03) continue;
    if (hit.point.y > maxY) continue;
    const node = placedRoot ? itemNodeOf(hit.object, placedRoot) : null;
    return {
      y: hit.point.y,
      point: hit.point.clone(),
      parentKey: node ? (node.userData as { diyKey?: string }).diyKey : undefined,
      carrier: node
        ? ((node.userData as { diyName?: string }).diyName ?? '已摆器物')
        : hit.object.name || '模型台面',
      source: node ? 'prop' : 'model',
    };
  }

  return null;
}

function clampAxis(value: number, min: number, max: number): number {
  if (min > max) return (min + max) / 2;
  return Math.min(Math.max(value, min), max);
}

/**
 * 屏幕近邻吸附：点在器物「上方一点点」也算放在它顶上。
 *
 * 只做兜底——几何射线没命中任何承载面时，找离光标最近的已摆器物，
 * 把落点吸到它的顶面中心。距离阈值按像素给，避免点空地也乱吸。
 */
export function findNearbyItemTop(options: {
  camera: THREE.Camera;
  size: { width: number; height: number };
  screen: { x: number; y: number };
  placedRoot: THREE.Object3D | null;
  maxPx: number;
  excludeKey?: string;
}): SurfaceTarget | null {
  const { camera, size, screen, placedRoot, maxPx, excludeKey } = options;
  if (!placedRoot) return null;
  const corners = [
    new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3(),
    new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3(),
  ];
  let best: { node: THREE.Object3D; box: THREE.Box3; distance: number } | null = null;

  for (const node of placedRoot.children) {
    const key = (node.userData as { diyKey?: string }).diyKey;
    if (!key || key === excludeKey) continue;
    const box = new THREE.Box3().setFromObject(node);
    if (!Number.isFinite(box.max.y)) continue;
    const { min, max } = box;
    const coords: [number, number, number][] = [
      [min.x, min.y, min.z], [max.x, min.y, min.z], [min.x, max.y, min.z], [max.x, max.y, min.z],
      [min.x, min.y, max.z], [max.x, min.y, max.z], [min.x, max.y, max.z], [max.x, max.y, max.z],
    ];
    let left = Infinity; let right = -Infinity; let top = Infinity; let bottom = -Infinity;
    let behind = 0;
    coords.forEach((coord, index) => {
      const point = corners[index].set(coord[0], coord[1], coord[2]).project(camera);
      if (point.z > 1) behind += 1;
      const px = ((point.x + 1) / 2) * size.width;
      const py = ((1 - point.y) / 2) * size.height;
      left = Math.min(left, px); right = Math.max(right, px);
      top = Math.min(top, py); bottom = Math.max(bottom, py);
    });
    if (behind > 0 && behind < 8) continue; // 部分在相机后面，投影不可信
    const dx = Math.max(left - screen.x, 0, screen.x - right);
    const dy = Math.max(top - screen.y, 0, screen.y - bottom);
    const distance = Math.hypot(dx, dy);
    if (distance > maxPx) continue;
    if (!best || distance < best.distance) best = { node, box, distance };
  }

  if (!best) return null;
  const key = (best.node.userData as { diyKey?: string }).diyKey as string;
  const center = best.box.getCenter(new THREE.Vector3());
  return {
    y: best.box.max.y,
    point: new THREE.Vector3(center.x, best.box.max.y, center.z),
    parentKey: key,
    carrier: (best.node.userData as { diyName?: string }).diyName ?? '已摆器物',
    source: 'prop',
  };
}

/**
 * 求悬挂锚点。
 *
 * 两种取法，优先「直接点中梁底」：
 *  A. 鼠标射线打到朝下的结构面（梁底/屋面底）——点在梁上就能挂；
 *  B. 落点正上方向下扫描，取第一个朝下的面——点在梁下空地上也能挂。
 * 两种都找不到、或锚点不在建筑范围内时返回 null，调用方必须拒绝落位。
 */
export function findHangTarget(options: {
  structural: THREE.Object3D[];
  ray?: THREE.Ray;
  floorPoint?: THREE.Vector3 | null;
  /** 当前建筑的悬挂几何范围；不传则按经典馆 */
  spec?: HangSpec;
}): HangTarget | null {
  const { structural, ray, floorPoint } = options;
  const spec = options.spec ?? DEFAULT_HANG_SPEC;
  if (!structural.length) return null;

  const accept = (hit: THREE.Intersection): boolean => {
    if (!isHangCarrier(hit.object.name)) return false;
    const point = hit.point;
    return (
      Math.abs(point.x) <= spec.bounds.x &&
      Math.abs(point.z) <= spec.bounds.z &&
      point.y >= spec.minY &&
      point.y <= spec.maxY
    );
  };

  // A. 直接点中梁底 / 屋面底
  if (ray) {
    _probe.set(ray.origin, ray.direction);
    _probe.near = 0.02;
    _probe.far = 80;
    const hits = _probe.intersectObjects(structural, true).sort((a, b) => a.distance - b.distance);
    for (const hit of hits) {
      const normal = faceNormal(hit);
      if (!normal || normal.y > -0.5) continue;
      if (!accept(hit)) continue;
      return { y: hit.point.y, point: hit.point.clone(), carrier: hit.object.name };
    }
  }

  // B. 落点正上方向下扫描
  if (!floorPoint) return null;
  if (Math.abs(floorPoint.x) > spec.bounds.x || Math.abs(floorPoint.z) > spec.bounds.z) return null;
  _column.set(new THREE.Vector3(floorPoint.x, spec.columnTop, floorPoint.z), DOWN);
  _column.near = 0.02;
  _column.far = 60;
  const hits = _column.intersectObjects(structural, true).sort((a, b) => a.distance - b.distance);
  for (const hit of hits) {
    const normal = faceNormal(hit);
    if (!normal || normal.y > -0.5) continue;
    if (!accept(hit)) continue;
    return {
      y: hit.point.y,
      point: new THREE.Vector3(floorPoint.x, hit.point.y, floorPoint.z),
      carrier: hit.object.name,
    };
  }
  return null;
}

export const HANG_HINT = '此处没有梁架锚点，请点在梁下或廊下';
export const SURFACE_HINT = '此处没有可放台面，已落到地面';