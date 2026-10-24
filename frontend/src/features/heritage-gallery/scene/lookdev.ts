/**
 * 纹脉展馆 · 观感（look-dev）参数表
 *
 * 目的：不重建 GLB、不改 Blender，只在网页侧把已有 PBR 材质调到「新中式美术馆」的观感：
 *  - 暖木：颜色微抬、粗糙度落在半哑光，避免黑成一片死木；
 *  - 石材/灰泥：粗糙度高、颜色略压，避免天光一打就死白；
 *  - 铜金：金属度抬高、靠 PMREM 环境（见 GalleryEnvironment）给出反射，
 *    否则没有环境贴图的金属只会是一块脏灰；
 *  - 朱红漆：粗糙度压低一点，做出髹漆的柔光，不反成塑料；
 *  - 纸感：给纸面/裱板一点点 sheen（布料级柔光），近看才有纤维感。
 *
 * 规则按材质名匹配（GLB 里的材质名由 Blender 导出，形如 M_wood / M_wood_m / M_stone_l），
 * 换一版模型只要材质命名保持约定，就不用改这个文件的结构。
 *
 * 注意：这里只改「材质参数」，不改几何、不改贴图，也不新建材质，因此
 * 不影响 DiYLayer 里按材质名做屋顶换色的逻辑。
 */

import * as THREE from 'three';

export interface MaterialTweak {
  /** 基色整体明度缩放：>1 提亮，<1 压暗 */
  colorScale?: number;
  roughness?: number;
  metalness?: number;
  /** 环境反射强度；没有环境贴图时无意义，但在 GalleryEnvironment 下生效 */
  envMapIntensity?: number;
  /** 布料/纸面柔光（仅 MeshPhysicalMaterial 支持） */
  sheen?: number;
  sheenColor?: string;
  clearcoat?: number;
}

interface Rule {
  /** 材质名匹配（精确或前缀） */
  match: RegExp;
  tweak: MaterialTweak;
  note: string;
}

/**
 * 顺序敏感：先匹配到哪条就用哪条，所以把「木的深/中/浅」「石的亮/暗」放在通用规则之前。
 */
const RULES: Rule[] = [
  // ---------------------------------------------------------------- 暖木
  {
    match: /^M_wood_d$/,
    tweak: { colorScale: 1.34, roughness: 0.6, envMapIntensity: 0.22 },
    note: '深色木构最容易被压成死黑，提亮最多，只给很弱的环境反射',
  },
  {
    match: /^M_wood$/,
    tweak: { colorScale: 1.2, roughness: 0.62, envMapIntensity: 0.28 },
    note: '主体木构：半哑光暖木',
  },
  {
    match: /^M_wood_m$/,
    tweak: { colorScale: 1.14, roughness: 0.58, envMapIntensity: 0.3 },
    note: '中色木：栏杆、格栅',
  },
  {
    match: /^M_wood_l$/,
    tweak: { colorScale: 1.08, roughness: 0.55, envMapIntensity: 0.34 },
    note: '浅色木：台面与展柜木框，稍亮一点把体量分开',
  },
  {
    match: /^M_(roof_board|floor1|floor2)$/,
    tweak: { colorScale: 1.12, roughness: 0.62, envMapIntensity: 0.32 },
    note: '望板与楼地面：有一点柔光反射，室内才不像纸板',
  },
  // ---------------------------------------------------------------- 朱红漆
  {
    match: /^M_red$/,
    tweak: { colorScale: 1.06, roughness: 0.5, envMapIntensity: 0.35 },
    note: '朱红柱/门：略降粗糙度，克制的高光',
  },
  {
    match: /^M_lacquer$/,
    tweak: { roughness: 0.36, envMapIntensity: 0.55 },
    note: '髹漆面：更紧的高光，但不加清漆到塑料感',
  },
  // ---------------------------------------------------------------- 铜金
  {
    match: /^M_gold$/,
    tweak: { metalness: 0.86, roughness: 0.34, envMapIntensity: 1.05 },
    note: '铜饰件：抬高金属度，靠环境贴图给出反射',
  },
  // ---------------------------------------------------------------- 石材 / 灰泥
  {
    match: /^M_stone_l$/,
    tweak: { colorScale: 0.94, roughness: 0.9, envMapIntensity: 0.25 },
    note: '亮石材：压 6% 避免被主光打成死白',
  },
  {
    match: /^M_stone_d$/,
    tweak: { colorScale: 1.1, roughness: 0.9, envMapIntensity: 0.2 },
    note: '深石材：抬一点形体，别糊成一块',
  },
  {
    match: /^M_stone$/,
    tweak: { colorScale: 0.98, roughness: 0.88, envMapIntensity: 0.24 },
    note: '石材默认',
  },
  {
    match: /^M_plaster$/,
    tweak: { colorScale: 0.94, roughness: 0.92, envMapIntensity: 0.18 },
    note: '白灰泥墙：压暗 6%，室内顶棚不再死白',
  },
  {
    match: /^M_plaster_d$/,
    tweak: { colorScale: 0.92, roughness: 0.92, envMapIntensity: 0.18 },
    note: '白灰泥（暗档）',
  },
  // ---------------------------------------------------------------- 纸感
  {
    match: /^M_(paper|panel_face|canvas)$/,
    tweak: { colorScale: 0.97, roughness: 0.88, sheen: 0.35, sheenColor: '#FFF3DC', envMapIntensity: 0.2 },
    note: '纸/裱画面：加一点 sheen，近看有纸纤维的柔光',
  },
  // ---------------------------------------------------------------- 瓦面
  {
    match: /^M_tile(_d)?$/,
    tweak: { roughness: 0.86, envMapIntensity: 0.26 },
    note: '黛瓦：保持高粗糙，只接一点点天光',
  },
  // ---------------------------------------------------------------- 瓷器 / 珐琅
  {
    match: /^M_(porcelain|cobalt)$/,
    tweak: { roughness: 0.2, envMapIntensity: 0.85 },
    note: '展品瓷器：釉面高光靠环境贴图',
  },
  {
    match: /^M_case_glass$/,
    tweak: { roughness: 0.06, envMapIntensity: 1.2 },
    note: '玻璃罩',
  },
  // ---------------------------------------------------------------- 织物
  {
    match: /^M_carpet2$/,
    tweak: { roughness: 0.92, sheen: 0.55, sheenColor: '#FFD9C2', envMapIntensity: 0.15 },
    note: '红毯：布料柔光，避免像塑料地胶',
  },
  // ---------------------------------------------------------------- 植被
  {
    match: /^M_(leaf|leaf_l|bamboo|bark|chap)$/,
    tweak: { roughness: 0.82, envMapIntensity: 0.2 },
    note: '庭院植被：哑光，退到配景层',
  },
];

/** 兜底环境反射：没有匹配规则的材质也有微弱 IBL，室内暗部才不死黑 */
const DEFAULT_ENV_INTENSITY = 0.22;

/** 逐材质缓存「是否已经处理过」，避免切换时段/重建时重复累乘 */
const applied = new WeakSet<THREE.Material>();

export interface LookDevStats {
  /** 遍历到的材质份数（去重后） */
  materials: number;
  /** 命中规则的份数 */
  tweaked: number;
  /** 实际生效的规则说明（按材质名） */
  appliedRules: string[];
}

function materialsOf(mesh: THREE.Mesh): THREE.Material[] {
  const raw = mesh.material as THREE.Material | THREE.Material[];
  return Array.isArray(raw) ? raw : [raw];
}

function applyTweak(material: THREE.Material, tweak: MaterialTweak): void {
  const standard = material as THREE.MeshStandardMaterial;
  if (typeof standard.roughness === 'number' && typeof tweak.roughness === 'number') {
    standard.roughness = tweak.roughness;
  }
  if (typeof standard.metalness === 'number' && typeof tweak.metalness === 'number') {
    standard.metalness = tweak.metalness;
  }
  if (typeof tweak.envMapIntensity === 'number') {
    standard.envMapIntensity = tweak.envMapIntensity;
  }
  if (typeof tweak.colorScale === 'number' && standard.color) {
    // 线性空间下等比缩放，避免只抬红通道把暖木调成橘色
    standard.color.multiplyScalar(tweak.colorScale);
  }
  // sheen / clearcoat 只有 MeshPhysicalMaterial 有；GLB 带 KHR_materials_specular 时
  // GLTFLoader 会生成 MeshPhysicalMaterial，所以这里用存在性判断而不是类型断言。
  const physical = material as THREE.MeshPhysicalMaterial;
  if (typeof physical.sheen === 'number') {
    if (typeof tweak.sheen === 'number') physical.sheen = tweak.sheen;
    if (tweak.sheenColor && physical.sheenColor) physical.sheenColor.set(tweak.sheenColor);
  }
  if (typeof physical.clearcoat === 'number' && typeof tweak.clearcoat === 'number') {
    physical.clearcoat = tweak.clearcoat;
  }
  if ('emissiveIntensity' in material) {
    // 保留 GLB 作者设定的自发光（窗纸、灯笼），只确保它不被写坏
    const emissive = material as THREE.MeshStandardMaterial;
    if (emissive.emissive && emissive.emissive.getHex() === 0x000000) {
      emissive.emissiveIntensity = 0;
    }
  }
  material.needsUpdate = true;
}

/**
 * 把观感表作用到整棵模型树上。
 * 幂等：同一个材质实例只处理一次（WeakSet），重复调用不会把 colorScale 累乘。
 */
export function applyLookDev(root: THREE.Object3D): LookDevStats {
  const stats: LookDevStats = { materials: 0, tweaked: 0, appliedRules: [] };
  const seen = new Set<string>();
  root.traverse((object) => {
    const mesh = object as THREE.Mesh;
    if (!mesh.isMesh) return;
    for (const material of materialsOf(mesh)) {
      if (!material || seen.has(material.uuid) || applied.has(material)) continue;
      seen.add(material.uuid);
      applied.add(material);
      stats.materials += 1;
      const name = material.name ?? '';
      const rule = RULES.find((entry) => entry.match.test(name));
      if (rule) {
        applyTweak(material, rule.tweak);
        stats.tweaked += 1;
        stats.appliedRules.push(`${name}: ${rule.note}`);
      } else if (typeof (material as THREE.MeshStandardMaterial).envMapIntensity === 'number') {
        (material as THREE.MeshStandardMaterial).envMapIntensity = DEFAULT_ENV_INTENSITY;
      }
    }
  });
  return stats;
}

/**
 * 夜间的展品重点照明参数。
 *
 * 不用 15 盏逐画框射灯（前向渲染下每个光源都会摊到所有像素上），
 * 只给「作品最密的三面主墙」各一盏无阴影的洗墙 spot：
 *  - 有 penumbra=0.9 的软边，不会在墙上留生硬光斑；
 *  - castShadow=false，阴影仍然只由主光那一盏负责。
 */
export const EXHIBIT_WASHERS: {
  key: string;
  position: [number, number, number];
  target: [number, number, number];
  color: string;
  /** 白天几乎不要，夜里需要它把画框周围照亮 */
  intensity: [number, number, number];
  distance: number;
  angle: number;
}[] = [
  {
    key: 'f1-back',
    position: [0.2, 2.75, 0.6],
    target: [-0.5, 1.9, 4.1],
    color: '#FFE7C6',
    intensity: [3.6, 6.2, 9.4],
    distance: 11,
    angle: 0.85,
  },
  {
    key: 'f2-back',
    position: [0.1, 6.2, 0.9],
    target: [0, 5.0, 4.1],
    color: '#FFE9CC',
    intensity: [3.2, 5.6, 8.6],
    distance: 11,
    angle: 0.9,
  },
  {
    key: 'f1-vitrine',
    position: [0, 3.1, -0.5],
    target: [0, 0.9, 0.1],
    color: '#FFF0D6',
    intensity: [2.4, 3.4, 4.6],
    distance: 6.5,
    angle: 0.7,
  },
];