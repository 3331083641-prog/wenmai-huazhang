/**
 * 纹脉展馆 · DIY 器物库
 *
 * 全部由 three 基础几何程序化拼出，不依赖外部模型 / 贴图 / 字体文件。
 * 约定：Y 轴向上、单位米；底部在 y=0、水平中心在原点，摆放端只设置
 * position / rotationY / scale。variant 在同一 id 下切换 2~3 种样式。
 *
 * 造型取自江南祠庙与徽派民居的小件：石灯笼四段式、条案束腰马蹄腿、
 * 展柜木框玻璃罩、匾额朱底金字等，靠起线、束腰、莲瓣、冰裂这些层次撑细节。
 */

import { useMemo } from 'react';
import * as THREE from 'three';

export type PropCategory = 'greenery' | 'light' | 'stone' | 'exhibit' | 'furniture' | 'wall' | 'asset';

export interface PropDef {
  id: string;
  name: string;
  category: PropCategory;
  /** 占地 X/Z，米 */
  footprint: [number, number];
  height: number;
  mount: 'ground' | 'wall';
  /**
   * 摆放类型（缺省 floor）：
   *  floor   落地
   *  surface 可放台面/柜顶，射线取承载面高度
   *  hang    必须悬挂到梁架锚点，无锚点拒绝落位
   */
  placement?: 'floor' | 'surface' | 'hang';
  note?: string;
  Component: React.FC<{ variant?: number }>;
}

/** 古建色板（sRGB），低饱和暖调，和站内朱砂 / 宣纸体系一致 */
export const PROP_COLORS = {
  wood: '#A9713F',
  woodMid: '#8A5330',
  woodDark: '#5C3A22',
  woodRed: '#6E3324',
  vermilion: '#A8352A',
  stone: '#CFC6B4',
  stoneMid: '#A99C87',
  stoneDark: '#8C8172',
  bronze: '#8C7443',
  brass: '#B08A4A',
  paper: '#F2E7D2',
  silk: '#E8D9BE',
  bamboo: '#6F8B4A',
  pine: '#46603A',
  pineLight: '#5E7A46',
  chap: '#2F5D55',
  porcelain: '#EDF1F4',
  porcelainBlue: '#3D5C8A',
  water: '#7FA6A0',
  glass: '#CFE0E4',
} as const;

const materialCache = new Map<string, THREE.MeshStandardMaterial>();

function mat(color: string, rough = 0.82, metal = 0.0, emissive?: string): THREE.MeshStandardMaterial {
  const key = `${color}|${rough}|${metal}|${emissive ?? ''}`;
  const cached = materialCache.get(key);
  if (cached) return cached;
  const material = new THREE.MeshStandardMaterial({
    color: new THREE.Color(color),
    roughness: rough,
    metalness: metal,
  });
  if (emissive) {
    material.emissive = new THREE.Color(emissive);
    material.emissiveIntensity = 0.85;
  }
  materialCache.set(key, material);
  return material;
}

/** 灯笼纸：半透暖光，夜里才亮得起来 */
function litPaper(): THREE.MeshStandardMaterial {
  return mat('#F3D9A8', 0.9, 0, '#FFB35C');
}

/* ------------------------------------------------------------------ 零件 */

type V3 = [number, number, number];

function Slab({
  size,
  at,
  color,
  rough = 0.85,
  metal = 0,
  rot,
}: {
  size: V3;
  at: V3;
  color: string;
  rough?: number;
  metal?: number;
  rot?: V3;
}) {
  return (
    <mesh position={at} rotation={rot} castShadow receiveShadow material={mat(color, rough, metal)}>
      <boxGeometry args={size} />
    </mesh>
  );
}

function Rod({
  r,
  h,
  at,
  color,
  seg = 12,
  rot,
  rough = 0.8,
}: {
  r: number;
  h: number;
  at: V3;
  color: string;
  seg?: number;
  rot?: V3;
  rough?: number;
}) {
  return (
    <mesh position={at} rotation={rot} castShadow receiveShadow material={mat(color, rough)}>
      <cylinderGeometry args={[r, r, h, seg]} />
    </mesh>
  );
}

function Taper({
  r0,
  r1,
  h,
  at,
  color,
  seg = 12,
  rot,
}: {
  r0: number;
  r1: number;
  h: number;
  at: V3;
  color: string;
  seg?: number;
  rot?: V3;
}) {
  return (
    <mesh position={at} rotation={rot} castShadow receiveShadow material={mat(color, 0.82)}>
      <cylinderGeometry args={[r0, r1, h, seg]} />
    </mesh>
  );
}

/** 四坡小屋顶：4 段圆锥转 45°，比正圆锥更像瓦顶 */
function HipCap({ w, d, h, y, color }: { w: number; d: number; h: number; y: number; color: string }) {
  return (
    <mesh
      position={[0, y, 0]}
      scale={[w / 2, 1, d / 2]}
      rotation={[0, Math.PI / 4, 0]}
      castShadow
      material={mat(color, 0.7)}
    >
      <coneGeometry args={[Math.SQRT2, h, 4]} />
    </mesh>
  );
}

/* ------------------------------------------------------------------ 物件 */

/** 石灯笼：基座 - 束腰 - 竿 - 火袋 - 笠 - 宝珠 */
function StoneLantern({ variant = 0 }: { variant?: number }) {
  const round = variant % 2 === 1;
  return (
    <group>
      <Slab size={[0.52, 0.1, 0.52]} at={[0, 0.05, 0]} color={PROP_COLORS.stoneMid} />
      <Slab size={[0.44, 0.06, 0.44]} at={[0, 0.13, 0]} color={PROP_COLORS.stone} />
      <Slab size={[0.36, 0.07, 0.36]} at={[0, 0.195, 0]} color={PROP_COLORS.stoneDark} />
      {round ? (
        <Rod r={0.085} h={0.46} at={[0, 0.46, 0]} color={PROP_COLORS.stone} seg={16} />
      ) : (
        <Slab size={[0.15, 0.46, 0.15]} at={[0, 0.46, 0]} color={PROP_COLORS.stone} />
      )}
      <Slab size={[0.34, 0.07, 0.34]} at={[0, 0.72, 0]} color={PROP_COLORS.stoneMid} />
      {([[-1, -1], [-1, 1], [1, -1], [1, 1]] as const).map(([sx, sz], i) => (
        <Slab
          key={i}
          size={[0.055, 0.3, 0.055]}
          at={[sx * 0.13, 0.905, sz * 0.13]}
          color={PROP_COLORS.stone}
        />
      ))}
      <mesh position={[0, 0.905, 0]} material={litPaper()}>
        <boxGeometry args={[0.21, 0.25, 0.21]} />
      </mesh>
      <Slab size={[0.34, 0.05, 0.34]} at={[0, 1.055, 0]} color={PROP_COLORS.stone} />
      <HipCap w={0.42} d={0.42} h={0.18} y={1.15} color={PROP_COLORS.stoneDark} />
      <mesh position={[0, 1.29, 0]} castShadow material={mat(PROP_COLORS.stone, 0.7)}>
        <sphereGeometry args={[0.062, 12, 10]} />
      </mesh>
    </group>
  );
}

/** 宫灯柱：石座 + 木柱 + 挑臂 + 六角宫灯 */
function PalaceLantern() {
  return (
    <group>
      <Slab size={[0.46, 0.12, 0.46]} at={[0, 0.06, 0]} color={PROP_COLORS.stoneMid} />
      <Slab size={[0.36, 0.06, 0.36]} at={[0, 0.15, 0]} color={PROP_COLORS.stone} />
      <Rod r={0.062} h={2.16} at={[0, 1.2, 0]} color={PROP_COLORS.woodDark} />
      <Slab size={[0.5, 0.07, 0.1]} at={[0.2, 2.2, 0]} color={PROP_COLORS.woodMid} />
      <Slab size={[0.07, 0.16, 0.07]} at={[0.42, 2.11, 0]} color={PROP_COLORS.woodMid} />
      <mesh position={[0.42, 1.92, 0]} castShadow material={litPaper()}>
        <cylinderGeometry args={[0.15, 0.15, 0.26, 6]} />
      </mesh>
      {[0, 1].map((i) => (
        <mesh
          key={i}
          position={[0.42, 1.79 + i * 0.26, 0]}
          castShadow
          material={mat(PROP_COLORS.woodDark, 0.7)}
        >
          <cylinderGeometry args={[0.175, 0.175, 0.035, 6]} />
        </mesh>
      ))}
      <Taper r0={0.02} r1={0.15} h={0.1} at={[0.42, 2.1, 0]} color={PROP_COLORS.woodDark} seg={6} />
      <Rod r={0.012} h={0.12} at={[0.42, 1.7, 0]} color={PROP_COLORS.vermilion} seg={6} />
    </group>
  );
}

/** 幡旗杆：杆 + 横木 + 布幡 */
function BannerPole({ variant = 0 }: { variant?: number }) {
  const cloth = variant % 2 === 1 ? PROP_COLORS.chap : PROP_COLORS.silk;
  return (
    <group>
      <Slab size={[0.5, 0.1, 0.5]} at={[0, 0.05, 0]} color={PROP_COLORS.stoneMid} />
      <Slab size={[0.34, 0.1, 0.34]} at={[0, 0.15, 0]} color={PROP_COLORS.stone} />
      <Rod r={0.07} h={3.0} at={[0, 1.65, 0]} color={PROP_COLORS.woodDark} />
      <Slab size={[0.9, 0.07, 0.07]} at={[0.34, 3.08, 0]} color={PROP_COLORS.woodMid} />
      <Slab size={[0.5, 0.03, 0.03]} at={[0.34, 3.14, 0]} color={PROP_COLORS.brass} />
      <Slab size={[0.46, 1.34, 0.018]} at={[0.34, 2.36, 0]} color={cloth} />
      <Slab size={[0.46, 0.05, 0.024]} at={[0.34, 1.685, 0]} color={PROP_COLORS.vermilion} />
      <Slab size={[0.46, 0.05, 0.024]} at={[0.34, 3.03, 0]} color={PROP_COLORS.vermilion} />
      <Rod r={0.016} h={0.16} at={[0.34, 1.58, 0]} color={PROP_COLORS.vermilion} seg={6} />
    </group>
  );
}

/** 铜香炉：三足 + 鼓腹 + 双耳 + 宝顶盖 */
function IncenseBurner() {
  return (
    <group>
      <mesh position={[0, 0.04, 0]} castShadow material={mat(PROP_COLORS.bronze, 0.55, 0.5)}>
        <cylinderGeometry args={[0.26, 0.28, 0.06, 20]} />
      </mesh>
      {[0, 120, 240].map((deg) => (
        <Rod
          key={deg}
          r={0.028}
          h={0.2}
          at={[
            Math.cos((deg * Math.PI) / 180) * 0.15,
            0.15,
            Math.sin((deg * Math.PI) / 180) * 0.15,
          ]}
          color={PROP_COLORS.bronze}
          seg={8}
        />
      ))}
      <mesh position={[0, 0.34, 0]} castShadow material={mat(PROP_COLORS.bronze, 0.5, 0.55)}>
        <sphereGeometry args={[0.24, 20, 14]} />
      </mesh>
      <Slab size={[0.5, 0.04, 0.06]} at={[0, 0.5, 0]} color={PROP_COLORS.bronze} />
      {[-1, 1].map((sx) => (
        <mesh
          key={sx}
          position={[sx * 0.24, 0.44, 0]}
          rotation={[0, 0, sx * 0.4]}
          castShadow
          material={mat(PROP_COLORS.bronze, 0.5, 0.55)}
        >
          <torusGeometry args={[0.08, 0.018, 8, 12, Math.PI]} />
        </mesh>
      ))}
      <Taper r0={0.05} r1={0.17} h={0.12} at={[0, 0.58, 0]} color={PROP_COLORS.bronze} seg={16} />
      <mesh position={[0, 0.68, 0]} castShadow material={mat(PROP_COLORS.brass, 0.45, 0.6)}>
        <sphereGeometry args={[0.055, 12, 10]} />
      </mesh>
    </group>
  );
}

/** 太湖石：瘦皱漏透，用错位渐缩的石头堆出孔洞感 */
function TaihuStone({ variant = 0 }: { variant?: number }) {
  const lean = variant % 2 === 1 ? -1 : 1;
  return (
    <group>
      <Slab size={[0.82, 0.1, 0.82]} at={[0, 0.05, 0]} color={PROP_COLORS.stoneMid} />
      <mesh
        position={[0, 0.34, 0]}
        rotation={[0, 0.4 * lean, 0.1 * lean]}
        castShadow
        material={mat(PROP_COLORS.stoneDark, 0.95)}
      >
        <dodecahedronGeometry args={[0.36, 0]} />
      </mesh>
      <mesh
        position={[0.1 * lean, 0.86, 0.06]}
        rotation={[0.2, 0.9, 0]}
        castShadow
        material={mat(PROP_COLORS.stoneMid, 0.95)}
      >
        <dodecahedronGeometry args={[0.3, 0]} />
      </mesh>
      <mesh
        position={[-0.06 * lean, 1.3, -0.04]}
        rotation={[0.1, 0.2, 0.3]}
        castShadow
        material={mat(PROP_COLORS.stone, 0.95)}
      >
        <dodecahedronGeometry args={[0.24, 0]} />
      </mesh>
      <mesh
        position={[0.12 * lean, 1.62, 0.02]}
        rotation={[0.3, 0.5, 0]}
        castShadow
        material={mat(PROP_COLORS.stoneDark, 0.95)}
      >
        <dodecahedronGeometry args={[0.14, 0]} />
      </mesh>
    </group>
  );
}

/** 松树盆景：石盆 + 曲干 + 四层云片 */
function PineBonsai({ variant = 0 }: { variant?: number }) {
  const s = variant % 2 === 1 ? -1 : 1;
  return (
    <group>
      <Slab size={[0.86, 0.3, 0.62]} at={[0, 0.15, 0]} color={PROP_COLORS.stone} />
      <Slab size={[0.92, 0.06, 0.68]} at={[0, 0.31, 0]} color={PROP_COLORS.stoneMid} />
      <Slab size={[0.78, 0.04, 0.54]} at={[0, 0.33, 0]} color={PROP_COLORS.woodDark} />
      <mesh
        position={[0.04 * s, 0.66, 0]}
        rotation={[0, 0, 0.22 * s]}
        castShadow
        material={mat('#5A4030', 0.9)}
      >
        <cylinderGeometry args={[0.05, 0.09, 0.66, 9]} />
      </mesh>
      <mesh
        position={[0.16 * s, 0.92, 0.02]}
        rotation={[0, 0, -0.5 * s]}
        castShadow
        material={mat('#5A4030', 0.9)}
      >
        <cylinderGeometry args={[0.03, 0.05, 0.34, 8]} />
      </mesh>
      {[
        [0.3 * s, 1.02, 0.02, 0.3, 0.13],
        [-0.14 * s, 1.1, -0.06, 0.26, 0.12],
        [0.1 * s, 1.24, 0.1, 0.22, 0.11],
        [0.02 * s, 1.06, 0.24, 0.2, 0.1],
      ].map(([x, y, z, r, h], i) => (
        <mesh
          key={i}
          position={[x, y, z]}
          scale={[1, h / r, 1]}
          castShadow
          material={mat(i % 2 ? PROP_COLORS.pineLight : PROP_COLORS.pine, 0.92)}
        >
          <sphereGeometry args={[r, 12, 8]} />
        </mesh>
      ))}
    </group>
  );
}

/** 竹丛：七竿 + 竹叶簇 */
function BambooClump() {
  const canes = useMemo(
    () =>
      Array.from({ length: 7 }, (_, i) => {
        const a = (i / 7) * Math.PI * 2 + 0.4;
        const r = 0.12 + (i % 3) * 0.11;
        return {
          x: Math.cos(a) * r,
          z: Math.sin(a) * r,
          h: 2.1 + (i % 4) * 0.28,
          tilt: ((i % 3) - 1) * 0.05,
        };
      }),
    [],
  );
  return (
    <group>
      <Slab size={[1.02, 0.16, 1.02]} at={[0, 0.08, 0]} color={PROP_COLORS.stoneMid} />
      <Slab size={[0.94, 0.04, 0.94]} at={[0, 0.18, 0]} color={PROP_COLORS.woodDark} />
      {canes.map((cane, i) => (
        <group key={i}>
          <mesh
            position={[cane.x, cane.h / 2 + 0.18, cane.z]}
            rotation={[0, 0, cane.tilt]}
            castShadow
            material={mat(PROP_COLORS.bamboo, 0.75)}
          >
            <cylinderGeometry args={[0.028, 0.034, cane.h, 8]} />
          </mesh>
          {[0.55, 0.78, 0.95].map((f, k) => (
            <mesh
              key={k}
              position={[
                cane.x + 0.1 * Math.cos(i + k),
                0.18 + cane.h * f,
                cane.z + 0.1 * Math.sin(i + k),
              ]}
              rotation={[0.4, i + k, 0.3]}
              scale={[1.4, 0.42, 1]}
              castShadow
              material={mat(k % 2 ? PROP_COLORS.pineLight : PROP_COLORS.bamboo, 0.9)}
            >
              <sphereGeometry args={[0.17, 8, 6]} />
            </mesh>
          ))}
        </group>
      ))}
    </group>
  );
}

/** 梅枝瓶：青花瓶 + 折枝 + 花点 */
function PlumVase({ variant = 0 }: { variant?: number }) {
  const sign = variant % 2 === 1 ? -1 : 1;
  return (
    <group>
      <mesh position={[0, 0.34, 0]} castShadow material={mat(PROP_COLORS.porcelain, 0.35)}>
        <latheGeometry
          args={[
            [
              new THREE.Vector2(0.001, 0),
              new THREE.Vector2(0.16, 0),
              new THREE.Vector2(0.2, 0.1),
              new THREE.Vector2(0.22, 0.34),
              new THREE.Vector2(0.16, 0.52),
              new THREE.Vector2(0.1, 0.58),
              new THREE.Vector2(0.12, 0.64),
              new THREE.Vector2(0.09, 0.66),
            ],
            24,
          ]}
        />
      </mesh>
      <mesh position={[0, 0.44, 0]} castShadow material={mat(PROP_COLORS.porcelainBlue, 0.4)}>
        <torusGeometry args={[0.205, 0.012, 6, 24]} />
      </mesh>
      <mesh
        position={[0.02, 0.86, 0]}
        rotation={[0, 0, 0.28 * sign]}
        castShadow
        material={mat('#5A4030', 0.9)}
      >
        <cylinderGeometry args={[0.012, 0.022, 0.46, 6]} />
      </mesh>
      <mesh
        position={[0.14 * sign, 1.06, 0.04]}
        rotation={[0.2, 0, -0.7 * sign]}
        castShadow
        material={mat('#5A4030', 0.9)}
      >
        <cylinderGeometry args={[0.008, 0.014, 0.26, 6]} />
      </mesh>
      {[
        [0.02, 1.1, 0],
        [0.18 * sign, 1.16, 0.04],
        [-0.04 * sign, 1.02, 0.06],
        [0.1 * sign, 0.96, -0.05],
      ].map(([x, y, z], i) => (
        <mesh key={i} position={[x, y, z]} material={mat(i % 2 ? '#C9506A' : '#E7B6C2', 0.8)}>
          <sphereGeometry args={[0.035, 8, 6]} />
        </mesh>
      ))}
    </group>
  );
}

/** 荷花缸：石缸 + 水面 + 荷叶 + 花苞 */
function LotusVat() {
  return (
    <group>
      <mesh position={[0, 0.3, 0]} castShadow receiveShadow material={mat(PROP_COLORS.stoneMid, 0.9)}>
        <cylinderGeometry args={[0.42, 0.34, 0.6, 24]} />
      </mesh>
      <mesh position={[0, 0.58, 0]} material={mat(PROP_COLORS.stone, 0.9)}>
        <torusGeometry args={[0.42, 0.04, 8, 24]} />
      </mesh>
      <mesh position={[0, 0.56, 0]} material={mat(PROP_COLORS.water, 0.25, 0.2)}>
        <cylinderGeometry args={[0.39, 0.39, 0.02, 24]} />
      </mesh>
      {[
        [0.16, 0.6, 0.1, 0.19],
        [-0.14, 0.6, -0.12, 0.15],
        [0.02, 0.6, -0.2, 0.12],
      ].map(([x, y, z, r], i) => (
        <mesh key={i} position={[x, y, z]} material={mat(PROP_COLORS.pine, 0.8)}>
          <cylinderGeometry args={[r, r, 0.012, 14]} />
        </mesh>
      ))}
      <Rod r={0.012} h={0.34} at={[0.12, 0.76, 0.08]} color={PROP_COLORS.pine} seg={6} />
      <mesh position={[0.12, 0.94, 0.08]} scale={[1, 1.3, 1]} material={mat('#E7A6B4', 0.7)}>
        <sphereGeometry args={[0.06, 10, 8]} />
      </mesh>
    </group>
  );
}

/** 鼓凳：鼓形 + 六开光 + 托泥 */
function DrumStool() {
  return (
    <group>
      <mesh position={[0, 0.25, 0]} castShadow receiveShadow material={mat(PROP_COLORS.woodMid, 0.7)}>
        <cylinderGeometry args={[0.21, 0.21, 0.44, 16]} />
      </mesh>
      <mesh position={[0, 0.47, 0]} material={mat(PROP_COLORS.woodDark, 0.7)}>
        <torusGeometry args={[0.21, 0.022, 6, 16]} />
      </mesh>
      <mesh position={[0, 0.03, 0]} material={mat(PROP_COLORS.woodDark, 0.7)}>
        <torusGeometry args={[0.21, 0.022, 6, 16]} />
      </mesh>
      {[0, 60, 120, 180, 240, 300].map((deg) => (
        <Slab
          key={deg}
          size={[0.12, 0.16, 0.012]}
          at={[
            Math.cos((deg * Math.PI) / 180) * 0.205,
            0.25,
            Math.sin((deg * Math.PI) / 180) * 0.205,
          ]}
          rot={[0, -(deg * Math.PI) / 180, 0]}
          color={PROP_COLORS.silk}
        />
      ))}
    </group>
  );
}

/** 条案：翘头 + 束腰 + 马蹄腿 + 牙板 */
function AltarTable({ variant = 0 }: { variant?: number }) {
  const apron = variant % 2 === 1 ? PROP_COLORS.chap : PROP_COLORS.vermilion;
  return (
    <group>
      <Slab size={[1.6, 0.07, 0.42]} at={[0, 0.8, 0]} color={PROP_COLORS.wood} />
      <Slab size={[1.62, 0.03, 0.44]} at={[0, 0.845, 0]} color={PROP_COLORS.woodMid} />
      {[-1, 1].map((sx) => (
        <Slab
          key={sx}
          size={[0.1, 0.09, 0.04]}
          at={[sx * 0.8, 0.87, 0]}
          rot={[0, 0, sx * 0.35]}
          color={PROP_COLORS.woodMid}
        />
      ))}
      <Slab size={[1.5, 0.07, 0.34]} at={[0, 0.735, 0]} color={PROP_COLORS.woodRed} />
      <Slab size={[1.54, 0.05, 0.3]} at={[0, 0.685, 0]} color={PROP_COLORS.woodDark} />
      {[-1, 1].map((sx) => (
        <group key={sx}>
          <Slab size={[0.07, 0.62, 0.07]} at={[sx * 0.7, 0.36, 0.14]} color={PROP_COLORS.wood} />
          <Slab size={[0.07, 0.62, 0.07]} at={[sx * 0.7, 0.36, -0.14]} color={PROP_COLORS.wood} />
          <Slab size={[0.1, 0.05, 0.1]} at={[sx * 0.7, 0.03, 0.14]} color={PROP_COLORS.woodDark} />
          <Slab size={[0.1, 0.05, 0.1]} at={[sx * 0.7, 0.03, -0.14]} color={PROP_COLORS.woodDark} />
          <Slab size={[0.06, 0.06, 0.34]} at={[sx * 0.7, 0.62, 0]} color={PROP_COLORS.wood} />
        </group>
      ))}
      <Slab size={[1.3, 0.13, 0.03]} at={[0, 0.63, 0.3]} color={PROP_COLORS.woodMid} />
      <Slab size={[1.3, 0.13, 0.03]} at={[0, 0.63, -0.3]} color={PROP_COLORS.woodMid} />
      <Slab size={[1.0, 0.28, 0.02]} at={[0, 0.5, 0.31]} color={apron} />
    </group>
  );
}

/** 展柜：木座 + 铜包角 + 玻璃罩 + 内展台 */
function DisplayCase({ variant = 0 }: { variant?: number }) {
  const w = variant % 2 === 1 ? 1.3 : 1.05;
  return (
    <group>
      <Slab size={[w, 0.62, 0.66]} at={[0, 0.31, 0]} color={PROP_COLORS.woodMid} />
      <Slab size={[w + 0.06, 0.05, 0.72]} at={[0, 0.645, 0]} color={PROP_COLORS.wood} />
      <Slab size={[w - 0.14, 0.3, 0.5]} at={[0, 0.32, 0]} color={PROP_COLORS.vermilion} />
      {[-1, 1].map((sx) =>
        [-1, 1].map((sz) => (
          <Slab
            key={`${sx}${sz}`}
            size={[0.05, 0.62, 0.05]}
            at={[sx * (w / 2 - 0.03), 0.31, sz * 0.3]}
            color={PROP_COLORS.brass}
            metal={0.6}
            rough={0.4}
          />
        )),
      )}
      <Slab size={[w - 0.16, 0.02, 0.52]} at={[0, 0.68, 0]} color={PROP_COLORS.paper} />
      {[0.33, -0.33].map((z) => (
        <mesh key={z} position={[0, 1.02, z]} material={mat(PROP_COLORS.glass, 0.08)}>
          <boxGeometry args={[w - 0.1, 0.68, 0.012]} />
        </mesh>
      ))}
      {[-1, 1].map((sx) => (
        <mesh key={sx} position={[sx * (w / 2 - 0.06), 1.02, 0]} material={mat(PROP_COLORS.glass, 0.08)}>
          <boxGeometry args={[0.012, 0.68, 0.64]} />
        </mesh>
      ))}
      <Slab size={[w - 0.08, 0.03, 0.62]} at={[0, 1.37, 0]} color={PROP_COLORS.woodDark} />
      <mesh position={[0, 0.88, 0]} castShadow material={mat(PROP_COLORS.porcelain, 0.35)}>
        <latheGeometry
          args={[
            [
              new THREE.Vector2(0.001, 0),
              new THREE.Vector2(0.09, 0),
              new THREE.Vector2(0.12, 0.08),
              new THREE.Vector2(0.1, 0.22),
              new THREE.Vector2(0.05, 0.26),
              new THREE.Vector2(0.06, 0.29),
            ],
            18,
          ]}
        />
      </mesh>
      <mesh position={[0, 0.83, 0]} material={mat(PROP_COLORS.porcelainBlue, 0.4)}>
        <torusGeometry args={[0.115, 0.008, 6, 18]} />
      </mesh>
    </group>
  );
}

/** 屏风：三扇，冰裂格心 + 裙板 */
function Screen() {
  return (
    <group>
      {[-1, 0, 1].map((p, i) => (
        <group key={i} position={[p * 0.56, 0, Math.abs(p) * 0.16]} rotation={[0, p * -0.32, 0]}>
          <Slab size={[0.56, 1.76, 0.05]} at={[0, 0.96, 0]} color={PROP_COLORS.woodDark} />
          <Slab size={[0.48, 1.66, 0.06]} at={[0, 0.96, 0]} color={PROP_COLORS.silk} />
          {[-0.33, 0.33].map((dx) => (
            <Slab key={dx} size={[0.035, 1.7, 0.075]} at={[dx, 0.96, 0]} color={PROP_COLORS.woodMid} />
          ))}
          <Slab size={[0.56, 0.045, 0.075]} at={[0, 1.8, 0]} color={PROP_COLORS.woodMid} />
          <Slab size={[0.56, 0.045, 0.075]} at={[0, 0.16, 0]} color={PROP_COLORS.woodMid} />
          {[-1, 1].map((s) => (
            <Slab
              key={s}
              size={[0.62, 0.012, 0.07]}
              at={[0, 1.02, 0]}
              rot={[0, 0, s * 0.42]}
              color={PROP_COLORS.woodMid}
            />
          ))}
          <Slab size={[0.44, 0.34, 0.06]} at={[0, 0.36, 0]} color={PROP_COLORS.woodRed} />
        </group>
      ))}
    </group>
  );
}

/** 匾额文字纹理：canvas 绘制，不引外部字体文件 */
function plaqueTexture(text: string): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 320;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    const grad = ctx.createLinearGradient(0, 0, 0, canvas.height);
    grad.addColorStop(0, '#4A2A1C');
    grad.addColorStop(0.5, '#3A1E13');
    grad.addColorStop(1, '#2A150D');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = '#C9A15A';
    ctx.lineWidth = 10;
    ctx.strokeRect(16, 16, canvas.width - 32, canvas.height - 32);
    ctx.fillStyle = '#E8C67A';
    ctx.font = '600 178px "Songti SC", "STSong", "SimSun", serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, canvas.width / 2, canvas.height / 2 + 8);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  return texture;
}

function PlaqueBoard({ variant = 0 }: { variant?: number }) {
  const texture = useMemo(
    () => plaqueTexture(variant % 2 === 1 ? '匠心传韵' : '非遗艺术馆'),
    [variant],
  );
  return (
    <group>
      <Slab size={[1.72, 0.56, 0.07]} at={[0, 0, 0]} color={PROP_COLORS.woodDark} />
      <Slab
        size={[1.8, 0.06, 0.1]}
        at={[0, 0.32, 0]}
        color={PROP_COLORS.brass}
        metal={0.55}
        rough={0.45}
      />
      <Slab
        size={[1.8, 0.06, 0.1]}
        at={[0, -0.32, 0]}
        color={PROP_COLORS.brass}
        metal={0.55}
        rough={0.45}
      />
      <mesh position={[0, 0, 0.045]}>
        <planeGeometry args={[1.62, 0.48]} />
        <meshStandardMaterial map={texture} roughness={0.62} />
      </mesh>
    </group>
  );
}

/** 砖雕花窗（挂墙）：外框 + 冰裂棂条 */
function LatticeWindow({ variant = 0 }: { variant?: number }) {
  const bars = useMemo(() => {
    const list: { x: number; y: number; rot: number; len: number }[] = [];
    for (let i = 0; i < 7; i += 1) list.push({ x: -0.36 + i * 0.12, y: 0, rot: Math.PI / 2, len: 0.9 });
    for (let i = 0; i < 5; i += 1) list.push({ x: 0, y: -0.36 + i * 0.18, rot: 0, len: 0.9 });
    if (variant % 2 === 1) {
      list.push({ x: -0.18, y: 0, rot: 0.5, len: 0.92 });
      list.push({ x: 0.18, y: 0, rot: -0.5, len: 0.92 });
    }
    return list;
  }, [variant]);
  return (
    <group>
      <Slab size={[1.16, 1.16, 0.08]} at={[0, 0, 0]} color={PROP_COLORS.stoneMid} />
      <Slab size={[1.02, 1.02, 0.06]} at={[0, 0, 0.02]} color={PROP_COLORS.paper} />
      <Slab size={[0.94, 0.94, 0.1]} at={[0, 0, 0.05]} color={PROP_COLORS.stoneDark} />
      <Slab size={[0.88, 0.88, 0.05]} at={[0, 0, 0.09]} color="#2A1A12" />
      {bars.map((bar, i) => (
        <mesh
          key={i}
          position={[bar.x, bar.y, 0.11]}
          rotation={[0, 0, bar.rot]}
          material={mat(PROP_COLORS.stone, 0.9)}
        >
          <boxGeometry args={[0.05, bar.len, 0.05]} />
        </mesh>
      ))}
      <Slab size={[1.24, 0.07, 0.12]} at={[0, 0.58, 0.02]} color={PROP_COLORS.stone} />
      <Slab size={[1.24, 0.07, 0.12]} at={[0, -0.58, 0.02]} color={PROP_COLORS.stone} />
      <Slab size={[0.07, 1.24, 0.12]} at={[0.58, 0, 0.02]} color={PROP_COLORS.stone} />
      <Slab size={[0.07, 1.24, 0.12]} at={[-0.58, 0, 0.02]} color={PROP_COLORS.stone} />
    </group>
  );
}

/* ------------------------------------------------------------------ 目录 */

export const PROP_CATALOG: PropDef[] = [
  { id: 'stone-lantern', name: '石灯笼', category: 'stone', footprint: [0.55, 0.55], height: 1.35, mount: 'ground', note: '四段石作，火袋透光', Component: StoneLantern },
  { id: 'palace-lantern', name: '宫灯柱', category: 'light', footprint: [0.6, 0.6], height: 2.34, mount: 'ground', note: '六角宫灯，夜里自发光', Component: PalaceLantern },
  { id: 'banner-pole', name: '幡旗杆', category: 'light', footprint: [1.0, 0.5], height: 3.2, mount: 'ground', note: '布幡朱边，可换青绿', Component: BannerPole },
  { id: 'incense-burner', name: '铜香炉', category: 'exhibit', footprint: [0.56, 0.56], height: 0.74, mount: 'ground', note: '三足双耳，宝顶盖', Component: IncenseBurner },
  { id: 'taihu-stone', name: '太湖石', category: 'stone', footprint: [0.86, 0.86], height: 1.78, mount: 'ground', note: '瘦皱漏透，庭院立石', Component: TaihuStone },
  { id: 'pine-bonsai', name: '松树盆景', category: 'greenery', footprint: [0.95, 0.7], height: 1.34, mount: 'ground', note: '曲干四层云片', Component: PineBonsai },
  { id: 'bamboo-clump', name: '竹丛', category: 'greenery', footprint: [1.05, 1.05], height: 2.9, mount: 'ground', note: '七竿带叶，石盆', Component: BambooClump },
  { id: 'plum-vase', name: '梅枝瓶', category: 'exhibit', footprint: [0.5, 0.5], height: 1.2, mount: 'ground', note: '青花瓶配折枝', Component: PlumVase },
  { id: 'lotus-vat', name: '荷花缸', category: 'stone', footprint: [0.9, 0.9], height: 1.0, mount: 'ground', note: '石缸水面荷叶', Component: LotusVat },
  { id: 'drum-stool', name: '鼓凳', category: 'furniture', footprint: [0.46, 0.46], height: 0.5, mount: 'ground', note: '六开光，可坐可陈', Component: DrumStool },
  { id: 'altar-table', name: '条案', category: 'furniture', footprint: [1.65, 0.46], height: 0.9, mount: 'ground', note: '翘头束腰马蹄腿', Component: AltarTable },
  { id: 'display-case', name: '展柜', category: 'exhibit', footprint: [1.35, 0.72], height: 1.4, mount: 'ground', note: '木座玻璃罩，内置瓷瓶', Component: DisplayCase },
  { id: 'screen', name: '屏风', category: 'furniture', footprint: [1.7, 0.5], height: 1.85, mount: 'ground', note: '三扇冰裂格心', Component: Screen },
  { id: 'plaque', name: '匾额', category: 'wall', footprint: [1.8, 0.12], height: 0.7, mount: 'wall', note: '朱底金字，挂墙', Component: PlaqueBoard },
  { id: 'lattice-window', name: '花窗', category: 'wall', footprint: [1.24, 0.12], height: 1.24, mount: 'wall', note: '砖雕冰裂纹，挂墙', Component: LatticeWindow },
];

export const PROP_BY_ID: Map<string, PropDef> = new Map(PROP_CATALOG.map((def) => [def.id, def]));

export const PROP_CATEGORY_LABEL: Record<PropCategory, string> = {
  greenery: '绿植',
  light: '灯幡',
  stone: '石作',
  exhibit: '陈设',
  furniture: '家具',
  wall: '墙面',
  asset: '非遗器物',
};