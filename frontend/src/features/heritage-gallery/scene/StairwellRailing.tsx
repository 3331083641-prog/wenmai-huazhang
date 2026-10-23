import { useMemo } from 'react';

/**
 * 二层楼梯井的护栏。
 *
 * 展馆 GLB 里原本用两段栏杆（INT_F2_RAIL_M / _E）围住楼梯上方的一条楼板，
 * 结果从二层看只是一个围栏、看不到楼梯，视觉上像上不来。
 * 把那条楼板收窄、旧栏杆删掉之后，井口变成一块完整的开口，
 * 这里按原来的木作样式补齐两段护栏：西侧（x≈0.56）与北侧（z≈3.79）。
 */

const WOOD = '#8a5330';
const RAIL_TOP = 0.95;
const RAIL_MID = 0.5;

interface Segment {
  from: [number, number];
  to: [number, number];
}

const SEGMENTS: Segment[] = [
  // 西侧：从 B 跑出口（z≈2.86）到后墙带（z≈3.79）
  { from: [0.58, 2.88], to: [0.58, 3.79] },
  // 北侧：沿后墙带的南沿
  { from: [0.58, 3.79], to: [1.99, 3.79] },
];

export function StairwellRailing({ floorY = 3.6 }: { floorY?: number }) {
  const parts = useMemo(() => {
    const posts: Array<[number, number, number]> = [];
    const rails: Array<{ pos: [number, number, number]; size: [number, number, number] }> = [];
    const postSize = 0.07;
    for (const seg of SEGMENTS) {
      const [x0, z0] = seg.from;
      const [x1, z1] = seg.to;
      const length = Math.hypot(x1 - x0, z1 - z0);
      const count = Math.max(2, Math.round(length / 0.6) + 1);
      for (let i = 0; i < count; i += 1) {
        const t = i / (count - 1);
        posts.push([x0 + (x1 - x0) * t, floorY + 0.52, z0 + (z1 - z0) * t]);
      }
      const horizontal = Math.abs(x1 - x0) > Math.abs(z1 - z0);
      const midX = (x0 + x1) / 2;
      const midZ = (z0 + z1) / 2;
      for (const height of [RAIL_TOP, RAIL_MID]) {
        rails.push({
          pos: [midX, floorY + height, midZ],
          size: horizontal ? [length, 0.06, 0.05] : [0.05, 0.06, length],
        });
      }
    }
    return { posts, rails, postSize };
  }, [floorY]);

  return (
    <group name="INT_F2_STAIRWELL_RAIL">
      {parts.posts.map((pos, index) => (
        <mesh key={`post-${index}`} position={pos} castShadow>
          <boxGeometry args={[parts.postSize, 1.0, parts.postSize]} />
          <meshStandardMaterial color={WOOD} roughness={0.75} />
        </mesh>
      ))}
      {parts.rails.map((rail, index) => (
        <mesh key={`rail-${index}`} position={rail.pos} castShadow>
          <boxGeometry args={rail.size} />
          <meshStandardMaterial color={WOOD} roughness={0.75} />
        </mesh>
      ))}
    </group>
  );
}

export default StairwellRailing;