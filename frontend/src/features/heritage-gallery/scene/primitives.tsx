/**
 * 通用三渲二构件。
 *
 * 每个 ToonBox / ToonCylinder 都自动附带一层轮廓，
 * 这样建筑、台阶、灯笼的风格能保持一致。
 */

import { useMemo } from 'react';
import * as THREE from 'three';
import { toonMaterial, outlineMaterial } from './materials';

interface ToonMeshProps {
  geometry: THREE.BufferGeometry;
  color: string;
  emissive?: string;
  emissiveIntensity?: number;
  /** 轮廓外扩系数，1 表示不画轮廓 */
  outlineScale?: number;
  position?: [number, number, number];
  rotation?: [number, number, number];
  scale?: [number, number, number];
  castShadow?: boolean;
  receiveShadow?: boolean;
  opacity?: number;
}

/**
 * 形状类构件的公共属性：不含 geometry（由各构件自己创建）。
 * 不直接复用 ToonMeshProps，否则 size 版组件会被要求传 geometry。
 */
type ToonShapeProps = Omit<ToonMeshProps, 'geometry'>;

/** 带墨线轮廓的基础网格 */
export function ToonMesh({
  geometry,
  color,
  emissive,
  emissiveIntensity,
  outlineScale = 1.012,
  position = [0, 0, 0],
  rotation = [0, 0, 0],
  scale,
  castShadow = true,
  receiveShadow = true,
  opacity = 1,
}: ToonMeshProps) {
  const material = useMemo(
    () => toonMaterial(color, { emissive, emissiveIntensity, transparent: opacity < 1, opacity }),
    [color, emissive, emissiveIntensity, opacity],
  );

  return (
    <group position={position} rotation={rotation} scale={scale}>
      <mesh geometry={geometry} material={material} castShadow={castShadow} receiveShadow={receiveShadow} />
      {outlineScale > 1 && (
        <mesh geometry={geometry} material={outlineMaterial} scale={outlineScale} castShadow={false} receiveShadow={false} />
      )}
    </group>
  );
}

/** 立方体 */
export function ToonBox({
  size,
  ...rest
}: ToonShapeProps & { size: [number, number, number] }) {
  const geometry = useMemo(() => new THREE.BoxGeometry(size[0], size[1], size[2]), [size[0], size[1], size[2]]);
  return <ToonMesh geometry={geometry} {...rest} />;
}

/** 圆柱（柱子、灯笼主体、树干） */
export function ToonCylinder({
  radiusTop,
  radiusBottom,
  height,
  segments = 16,
  ...rest
}: ToonShapeProps & { radiusTop: number; radiusBottom: number; height: number; segments?: number }) {
  const geometry = useMemo(
    () => new THREE.CylinderGeometry(radiusTop, radiusBottom, height, segments),
    [radiusTop, radiusBottom, height, segments],
  );
  return <ToonMesh geometry={geometry} {...rest} />;
}

/** 球体（树冠、灯笼） */
export function ToonSphere({
  radius,
  segments = 16,
  ...rest
}: ToonShapeProps & { radius: number; segments?: number }) {
  const geometry = useMemo(() => new THREE.SphereGeometry(radius, segments, Math.max(8, segments / 2)), [radius, segments]);
  return <ToonMesh geometry={geometry} {...rest} />;
}
