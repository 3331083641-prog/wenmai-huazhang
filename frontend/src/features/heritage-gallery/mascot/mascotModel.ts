/**
 * 灵宠「纹纹」的模型接入配置（可替换模块）
 *
 * 目的：把「模型从哪加载、动画怎么对名、缩放/朝向/贴地怎么算」全部收进这一个文件。
 * 换一只角色（猫 -> 兔、或新一版 Blender 导出）时，**只改这个文件**：
 *   1. url 换成新的 GLB；
 *   2. clips 把语义动作映射到新模型里真实的动画名（名字可以在 Blender 的
 *      NLA / glTF 导出面板里看到，也可以用下文 describeMascotModel 打出来）；
 *   3. targetHeight / yawOffset / groundOffset 按新模型的实际包围盒与朝向微调，
 *      或者干脆留 targetHeight 让它按比例自动缩放。
 *
 * 与 mascotConfig.ts 的分工：
 *   - mascotConfig.ts：场景数据（大厅范围、楼梯、楼层标高、速度、展品触发距离），
 *     是「展馆」的属性，不随角色模型变；
 *   - 本文件：角色资产本身的属性（文件、动画、比例、朝向），是「角色」的属性。
 *
 * 当前模型：public/models/WenWen_v003_gallery.glb
 *   v003 四足模型，GLB 原始正面 +Z；带展馆基础绑定，动画共 8 条：
 *   Curious / Happy / Idle / Interact / Run / Spawn / Turn / Walk。
 */

import * as THREE from 'three';

/** 语义动作：游戏逻辑只用这 8 个名字，不直接引用 GLB 里的动画名 */
export type MascotClip =
  | 'idle'
  | 'walk'
  | 'run'
  | 'turn'
  | 'spawn'
  | 'happy'
  | 'interact'
  | 'curious';

export interface MascotModelConfig {
  /** GLB 地址（带 BASE_URL，静态站部署到子路径也不会 404） */
  url: string;
  /** 目标身高（米）：按包围盒等比缩放，设 0 表示完全不缩放 */
  targetHeight: number;
  /** 模型正面与 -Z 的夹角（弧度）：GLB 的脸朝 -Z 时为 0 */
  yawOffset: number;
  /** 贴地微调（米）：正数往上抬，负数往下压 */
  groundOffset: number;
  /** 是否按包围盒把脚底对齐到角色原点 y=0 */
  fitToGround: boolean;
  /** 语义动作 -> GLB 动画名 */
  clips: Record<MascotClip, string>;
}

export const MASCOT_MODEL: MascotModelConfig = {
  url: `${import.meta.env.BASE_URL}models/WenWen_v003_gallery.glb`,
  targetHeight: 1.0,
  yawOffset: Math.PI,
  groundOffset: 0,
  fitToGround: true,
  clips: {
    idle: 'Idle',
    walk: 'Walk',
    run: 'Run',
    turn: 'Turn',
    spawn: 'Spawn',
    happy: 'Happy',
    interact: 'Interact',
    curious: 'Curious',
  },
};

/** 一次性动作：播完就回到移动状态机，不循环 */
const ONE_SHOT: ReadonlySet<MascotClip> = new Set<MascotClip>(['spawn', 'happy', 'interact']);

export function isOneShotClip(clip: MascotClip): boolean {
  return ONE_SHOT.has(clip);
}

/** GLB 动画名 -> 语义名（模型里多出来的动画会被忽略，不报错） */
export const CLIP_TO_SEMANTIC: Record<string, MascotClip> = Object.fromEntries(
  (Object.entries(MASCOT_MODEL.clips) as [MascotClip, string][]).map(([semantic, name]) => [name, semantic]),
);

/** 语义动作对应的 GLB 动画名；模型没这条动画时回落到 idle */
export function clipName(clip: MascotClip): string {
  return MASCOT_MODEL.clips[clip] ?? MASCOT_MODEL.clips.idle;
}

export interface MascotFit {
  /** 等比缩放系数 */
  scale: number;
  /** 贴地偏移（米），作用在包裹组上 */
  offsetY: number;
  /** 原始包围盒，便于调参/验收时打印 */
  box: THREE.Box3;
}

/**
 * 按配置算出缩放与贴地偏移。
 * 用包围盒而不是手写数字：换模型以后哪怕比例完全不同，脚也一定踩在地上，
 * 不会出现「悬空半米」或「陷进地板」。
 */
export function computeMascotFit(object: THREE.Object3D): MascotFit {
  const box = new THREE.Box3().setFromObject(object);
  if (box.isEmpty()) return { scale: 1, offsetY: 0, box };
  const height = box.max.y - box.min.y;
  const scale =
    MASCOT_MODEL.targetHeight > 0 && height > 1e-4 ? MASCOT_MODEL.targetHeight / height : 1;
  const offsetY = (MASCOT_MODEL.fitToGround ? -box.min.y * scale : 0) + MASCOT_MODEL.groundOffset;
  return { scale, offsetY, box };
}

/**
 * 模型可用性：dev server 对缺失文件会回落 index.html（HTTP 200），
 * 所以必须验 GLB 的 magic（前 4 字节 glTF），不能只看状态码。
 */
export async function isMascotModelAvailable(): Promise<boolean> {
  try {
    const res = await fetch(MASCOT_MODEL.url, {
      cache: 'no-store',
      headers: { Range: 'bytes=0-3' },
    });
    if (!res.ok) return false;
    const buf = await res.arrayBuffer();
    if (buf.byteLength < 4) return false;
    const magic = String.fromCharCode(...new Uint8Array(buf.slice(0, 4)));
    return magic === 'glTF';
  } catch {
    return false;
  }
}

/**
 * 调参/验收用：把当前模型的实际包围盒与动画名打到 console。
 * 换模型时先跑一次这个，再把结果填回 MASCOT_MODEL。
 */
export function describeMascotModel(scene: THREE.Object3D, animations: THREE.AnimationClip[]): void {
  const fit = computeMascotFit(scene);
  const size = fit.box.getSize(new THREE.Vector3());
  console.info('[mascot] bounds', {
    min: fit.box.min.toArray().map((v) => Number(v.toFixed(3))),
    max: fit.box.max.toArray().map((v) => Number(v.toFixed(3))),
    size: size.toArray().map((v) => Number(v.toFixed(3))),
    computedScale: Number(fit.scale.toFixed(3)),
    offsetY: Number(fit.offsetY.toFixed(3)),
  });
  console.info(
    '[mascot] clips',
    animations.map((clip) => clip.name),
  );
  if (import.meta.env.DEV) {
    (window as unknown as { __wenwenModel?: unknown }).__wenwenModel = {
      url: MASCOT_MODEL.url,
      clips: animations.map((clip) => clip.name),
      scale: fit.scale,
      offsetY: fit.offsetY,
      samplePose: () => {
        const bones: Record<string, number[]> = {};
        scene.traverse((object) => {
          if (object instanceof THREE.Bone) bones[object.name] = object.quaternion.toArray();
        });
        return bones;
      },
    };
  }
}
