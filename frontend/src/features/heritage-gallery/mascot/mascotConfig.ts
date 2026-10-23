/**
 * 展馆吉祥物「纹纹」的运行参数。
 *
 * 角色本体由 Blender 产出（`public/models/wenmai_mascot_ww.glb`），
 * 这里只放「它在展馆里怎么走、走多快、撞到哪、在哪儿能上楼」这类场景数据，
 * 与角色美术解耦，换模型不用改这里。
 *
 * 坐标系与 `data/gallery_layout.json` 一致：米制，Y 向上，原点在台基中心。
 */

/** 角色身高 1.0 m；网页里按展馆门高放到 1.0（展馆一层层高 3.35 m，比例合适）。 */
export const MASCOT_HEIGHT = 1.0;

/** 三层楼面标高（与 gallery_layout.envelope 对齐）。 */
export const FLOOR1_Y = 0.25;
export const FLOOR2_Y = 3.6;

/** 大厅内可走范围（墙在 x=±4.04 / z=4.14，留出角色半径）。 */
export const HALL = {
  minX: -3.72,
  maxX: 3.72,
  minZ: -2.4,
  maxZ: 3.86,
};

/** 入口与出生点：从馆外台阶下跳进来。 */
export const SPAWN = {
  outside: [0, FLOOR1_Y, -5.35] as [number, number, number],
  inside: [-1.2, FLOOR1_Y, 1.2] as [number, number, number],
  lookYaw: Math.PI, // 面向馆内（-Z 是模型正面，转身朝里）
};

/**
 * 室内转折楼梯（模型自带，INT_ST_*）：一跑沿 +X 上行到后侧休息平台，折返再沿 −X
 * 上到二层。坐标取自 GLB 里真实踏步的位置：
 *   A 跑：z≈3.41，x 0.30→2.90，y 0.25→1.92
 *   平台：x 2.86→3.62，z 1.75→3.55，y≈1.98
 *   B 跑：z≈2.31，x 2.90→0.55，y 1.98→3.60（出口正好落在二层楼板洞口的西沿）
 * 之前网页自己补的那段楼梯是错的（位置压在展柜上，也上不去），已删除。
 */
export const STAIR = {
  /** A 跑：沿 +X 升 */
  a: { x0: 0.3, x1: 2.9, z0: 2.9, z1: 3.92, y0: FLOOR1_Y, y1: 1.92 },
  /** 休息平台（平） */
  landing: { x0: 2.86, x1: 3.62, z0: 1.75, z1: 3.55, y: 1.98 },
  /** B 跑：沿 −X 升（x 越小越高） */
  b: { x0: 0.55, x1: 2.9, z0: 1.78, z1: 2.85, yLow: 1.98, yHigh: 3.6 },
  /** 楼梯构件前缀：这些网格不参与「家具障碍」计算，否则踏步会把楼梯自己堵死 */
  meshPrefix: 'INT_ST_',
};

/** 角色运动参数（米/秒、弧度/秒）。 */
export const MOTION = {
  walkSpeed: 1.35,
  runSpeed: 2.7,
  backSpeed: 0.9,
  turnSpeed: 2.6,
  /** 单帧位移上限，防止切后台回来一步穿墙。 */
  maxStep: 0.35,
  /** 台阶容差：超出这个高度差就当作墙。 */
  stepHeight: 0.42,
  radius: 0.26,
};

/** 相机：第三人称跟随 / 第一人称。 */
export const CAMERA = {
  thirdDistance: 1.9,
  thirdHeight: 1.55,
  thirdLookHeight: 0.8,
  firstEyeHeight: 0.86,
  firstForward: 0.14,
  followLambda: 7.5,
  spawnBlendSeconds: 1.3,
};

/** 展品互动：靠近画框时触发 Curious + 打开文化卡。 */
export const EXHIBIT = {
  enterDistance: 1.65,
  leaveDistance: 2.15,
  /** 同层判定：高度差超过这个值不算「在同一层看展」。 */
  sameFloorDelta: 1.2,
  cooldownMs: 4200,
};

/** 画框楼层：位置来自 gallery_layout.frames（floor 1 / 2）。 */
export function frameFloor(y: number): 1 | 2 {
  return y > 2 ? 2 : 1;
}

/**
 * 二层楼梯井的洞口范围（世界坐标）。这些位置没有楼板：掉下去就是一层。
 * 与 GLB 里开的洞一致：x 0.56–4.04 / z 1.76–3.79，另加 x≥2 的后段。
 */
const VOID_RECTS = [
  { x0: 0.56, x1: 4.04, z0: 1.76, z1: 3.79 },
  { x0: 2.0, x1: 4.04, z0: 3.79, z1: 4.14 },
];

/** 该点是否落在楼梯井洞口上方（脚下没有楼板）。 */
export function isOverVoid(x: number, z: number): boolean {
  return VOID_RECTS.some((r) => x > r.x0 && x < r.x1 && z > r.z0 && z < r.z1);
}
/** 楼梯上所有可能的地面高度（同一位置在 A 跑、平台、B 跑、二层楼板里取最合适的那个）。 */
function stairCandidates(x: number, z: number): number[] {
  const out: number[] = [];
  const a = STAIR.a;
  if (x >= a.x0 && x <= a.x1 && z >= a.z0 && z <= a.z1) {
    out.push(a.y0 + ((x - a.x0) / (a.x1 - a.x0)) * (a.y1 - a.y0));
  }
  const l = STAIR.landing;
  if (x >= l.x0 && x <= l.x1 && z >= l.z0 && z <= l.z1) out.push(l.y);
  const b = STAIR.b;
  if (x >= b.x0 && x <= b.x1 && z >= b.z0 && z <= b.z1) {
    out.push(b.yLow + ((b.x1 - x) / (b.x1 - b.x0)) * (b.yHigh - b.yLow));
  }
  return out;
}

/**
 * 当前脚下的地面标高。
 * 转折楼梯有 A 跑 / 平台 / B 跑三段，同一点可能落在两段的重叠区里，
 * 取「离当前高度最近、且不超过一级台阶」的那个，才不会在折返处把人卡住或瞬移。
 */
export function groundHeightAt(x: number, z: number, currentY: number): number {
  const floor = currentY > (FLOOR1_Y + FLOOR2_Y) / 2 ? FLOOR2_Y : FLOOR1_Y;
  const stair = stairCandidates(x, z);
  if (stair.length) {
    // 站在楼梯投影里就以楼梯为准：否则「楼层地面」永远和当前高度相等，
    // 角色会一直贴着地面走，上不去。
    let best = stair[0];
    let bestDelta = Math.abs(best - currentY);
    for (const value of stair) {
      const delta = Math.abs(value - currentY);
      if (delta < bestDelta) {
        bestDelta = delta;
        best = value;
      }
    }
    if (bestDelta <= MOTION.stepHeight + 0.05) return best;
  }
  if (isOverVoid(x, z)) return Number.NEGATIVE_INFINITY; // 井口没有地板
  return floor;
}

/** 走到墙外就贴回大厅内沿（简单可靠，不会穿墙也不会掉出场景）。 */
export function clampToHall(x: number, z: number): [number, number] {
  return [
    Math.min(HALL.maxX, Math.max(HALL.minX, x)),
    Math.min(HALL.maxZ, Math.max(HALL.minZ, z)),
  ];
}

/** 角色能否站到目标点：地面高度差超过台阶容差就不能过。 */
export function canStandAt(x: number, z: number, currentY: number): boolean {
  const target = groundHeightAt(x, z, currentY);
  if (!Number.isFinite(target)) return false; // 洞口不可站立
  return Math.abs(target - currentY) <= MOTION.stepHeight + 0.02;
}
/**
 * 展品（画框）的世界坐标：画框数据只有墙上的归一化 u/v，
 * 这里按「墙中心 + 墙面局部偏移」换算成世界坐标，供角色靠近判定使用。
 */
import { frameSlots, galleryWalls } from '../../../data/heritageGalleryConfig';

const wallMap = new Map(galleryWalls.map((wall) => [wall.id, wall]));

export interface ExhibitPoint {
  id: string;
  floor: 1 | 2;
  x: number;
  z: number;
  y: number;
}

export const EXHIBIT_POINTS: ExhibitPoint[] = frameSlots
  .map((frame) => {
    const wall = wallMap.get(frame.wallId);
    if (!wall) return null;
    const localX = (frame.u - 0.5) * wall.size[0];
    const localY = (frame.v - 0.5) * wall.size[1];
    const cos = Math.cos(wall.rotationY);
    const sin = Math.sin(wall.rotationY);
    return {
      id: frame.id,
      floor: wall.floor,
      x: wall.center[0] + localX * cos,
      y: wall.center[1] + localY,
      z: wall.center[2] - localX * sin,
    };
  })
  .filter((point): point is ExhibitPoint => point !== null);