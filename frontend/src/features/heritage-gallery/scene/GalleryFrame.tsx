/**
 * 画框：固定在墙面上，可点击换画、悬停提示。
 *
 * 关键设计：
 *  - 尺寸完全来自布局数据（frame.size，横竖不一），不再写死正方形，
 *    长卷、立轴、斗方都能按真实比例落位。
 *  - 画框位置用「墙面局部归一化坐标」，渲染时换算成世界坐标，
 *    因此墙面一改，画框自动跟随，也不会因为相机旋转而漂移。
 *  - 画框位置只读布局数据：用户要求「只保留固定画框」，所以这里不再
 *    提供拖拽移动（旧的 u/v 拖拽逻辑已删除），点击只负责打开图库换画；
 *  - 悬停时把画框 id 与光标位置写进 frameHoverStore，页面据此弹出
 *    「点击更换图画」的提示。
 */

import { useMemo, useState } from 'react';
import * as THREE from 'three';
import { useTexture } from '@react-three/drei';
import type { GalleryConfig } from '../buildings/layout';
import { useFrameHoverStore } from '../state/frameHoverStore';
import { findArtwork } from '../../../data/artworkRegistry';
import { PALETTE } from './materials';
import { ToonBox } from './primitives';

interface FrameProps {
  /** 当前建筑的配置（画框/展墙都在里面，换馆时随 props 变化） */
  config: GalleryConfig;
  frameId: string;
  artworkId: string;
  /** 墙面局部归一化位置 */
  u: number;
  v: number;
  selected: boolean;
  /** 点击画框（打开图库） */
  onSelect: (frameId: string) => void;
}

/** 由外框尺寸推导框条 / 卡纸 / 画面尺寸，保证任何比例都不塌陷 */
function frameMetrics(w: number, h: number) {
  const short = Math.min(w, h);
  const moulding = Math.min(0.055, short * 0.09);
  const mat = Math.min(0.075, short * 0.11);
  const inner = Math.max(0.12, short - 2 * (moulding + mat));
  return { moulding, mat, inner };
}

/**
 * 单张作品的贴图组件。
 * 用 drei 的 useTexture 自动处理加载与卸载；suspense 由外层统一包裹。
 */
function ArtworkPlane({ url, accent, w, h }: { url: string; accent: string; w: number; h: number }) {
  const texture = useTexture(url);
  const memoTexture = useMemo(() => {
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.anisotropy = 8;
    return texture;
  }, [texture]);

  // 按图片真实比例「contain」进画心，绝不拉伸：横图左右留卡纸，竖图上下留卡纸。
  const fitted = useMemo<[number, number]>(() => {
    const image = texture.image as { width?: number; height?: number } | undefined;
    const iw = Number(image?.width) || 1;
    const ih = Number(image?.height) || 1;
    const imageAspect = iw / ih;
    const frameAspect = w / h;
    if (imageAspect >= frameAspect) return [w, w / imageAspect];
    return [h * imageAspect, h];
  }, [texture, w, h]);

  return (
    <mesh position={[0, 0, 0.031]}>
      <planeGeometry args={[fitted[0], fitted[1]]} />
      <meshBasicMaterial map={memoTexture} toneMapped={false} />
      {/* 选中时的细描边，用作品主题色，不涂红圈 */}
      <mesh position={[0, 0, 0.001]} scale={1.03}>
        <planeGeometry args={[fitted[0], fitted[1]]} />
        <meshBasicMaterial color={accent} transparent opacity={0.9} side={THREE.BackSide} />
      </mesh>
    </mesh>
  );
}

/** 空画框：只显示卡纸与一层淡纹，提示「这里可以挂画」 */
function EmptyPlane({ w, h }: { w: number; h: number }) {
  return (
    <mesh position={[0, 0, 0.031]}>
      <planeGeometry args={[w, h]} />
      <meshBasicMaterial color="#EFE4CF" />
    </mesh>
  );
}

export function GalleryFrame({
  config,
  frameId,
  artworkId,
  u,
  v,
  selected,
  onSelect,
}: FrameProps) {
  const frame = config.frameById.get(frameId);
  const wall = frame ? config.wallById.get(frame.wallId) : undefined;
  const artwork = findArtwork(artworkId);

  const [hovered, setHovered] = useState(false);

  const outerW = frame?.size?.[0] ?? 1.0;
  const outerH = frame?.size?.[1] ?? 0.85;
  const { moulding, mat, inner } = frameMetrics(outerW, outerH);
  const imgW = outerW - 2 * (moulding + mat);
  const imgH = outerH - 2 * (moulding + mat);

  const worldPosition = useMemo<[number, number, number]>(() => {
    if (!wall) return [0, 0, 0];
    return config.wallPointToWorld(wall, u, v, 0.06);
  }, [config, wall, u, v]);

  const rotationY = wall?.rotationY ?? 0;

  if (!wall || !frame) return null;

  const edgeColor = selected ? PALETTE.vermilion : PALETTE.wood;

  return (
    <group
      position={worldPosition}
      rotation={[0, rotationY, 0]}
      userData={{ frameId }}
      onClick={(event) => {
        event.stopPropagation();
        onSelect(frameId);
      }}
      onPointerOver={(event) => {
        event.stopPropagation();
        setHovered(true);
        document.body.style.cursor = 'pointer';
        const native = event.nativeEvent as PointerEvent;
        useFrameHoverStore
          .getState()
          .setHover(frameId, native.clientX, native.clientY, artwork?.title ?? '空画框');
      }}
      onPointerMove={(event) => {
        const native = event.nativeEvent as PointerEvent;
        useFrameHoverStore
          .getState()
          .setHover(frameId, native.clientX, native.clientY, artwork?.title ?? '空画框');
      }}
      onPointerOut={() => {
        setHovered(false);
        document.body.style.cursor = '';
        useFrameHoverStore.getState().clear();
      }}
    >
      {/* 外框：四条边按真实长宽比装配 */}
      <ToonBox size={[outerW, moulding, 0.06]} color={edgeColor} position={[0, outerH / 2 - moulding / 2, 0]} outlineScale={1.02} />
      <ToonBox size={[outerW, moulding, 0.06]} color={edgeColor} position={[0, -outerH / 2 + moulding / 2, 0]} outlineScale={1.02} />
      <ToonBox size={[moulding, outerH - moulding * 2, 0.06]} color={edgeColor} position={[-outerW / 2 + moulding / 2, 0, 0]} outlineScale={1.02} />
      <ToonBox size={[moulding, outerH - moulding * 2, 0.06]} color={edgeColor} position={[outerW / 2 - moulding / 2, 0, 0]} outlineScale={1.02} />

      {/* 卡纸底板 */}
      <mesh position={[0, 0, 0.02]}>
        <planeGeometry args={[imgW + mat * 2, imgH + mat * 2]} />
        <meshBasicMaterial color="#FBF5E9" />
      </mesh>

      {/* 画面 */}
      {artwork ? (
        <ArtworkPlane url={artwork.imageUrl} accent={artwork.accent} w={imgW} h={imgH} />
      ) : (
        <EmptyPlane w={imgW} h={imgH} />
      )}

      {/* 悬停/选中时的柔和外发光，代替厚重描边 */}
      {(hovered || selected) && (
        <mesh position={[0, 0, 0.005]}>
          <planeGeometry args={[outerW + 0.1, outerH + 0.1]} />
          <meshBasicMaterial color={artwork?.accent ?? PALETTE.vermilion} transparent opacity={0.16} />
        </mesh>
      )}
      {/* 标注线：让 15 个画框有排布逻辑（小尺寸画心的薄边） */}
      {inner > 0.2 && (
        <mesh position={[0, 0, 0.023]}>
          <planeGeometry args={[imgW + mat * 1.1, imgH + mat * 1.1]} />
          <meshBasicMaterial color="#E4D6BC" transparent opacity={0.55} />
        </mesh>
      )}
    </group>
  );
}