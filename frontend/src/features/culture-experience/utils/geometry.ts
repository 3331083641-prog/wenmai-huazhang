/**
 * 几何工具：把归一化的热点坐标换算成任意容器里的像素框。
 *
 * 关键点：`object-fit: contain` 会让图片的实际绘制区域小于容器区域。
 * 热点必须挂在「真实绘制区域」上，否则一旦容器宽高比变化就会漂移。
 * 本文件的所有函数都是纯函数，便于单元测试（见 tests/geometry.test.mjs）。
 */

import type { CircleGeometry, HotspotGeometry, PolygonGeometry, RectGeometry } from '../types';

export interface Size {
  width: number;
  height: number;
}

export interface Box {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * 计算 object-fit: contain 下图片的真实绘制区域。
 * 容器或图片尺寸为 0 时返回全零框，调用方应据此跳过渲染。
 */
export function computeContainBox(container: Size, image: Size): Box {
  const cw = Math.max(0, container.width);
  const ch = Math.max(0, container.height);
  const iw = Math.max(0, image.width);
  const ih = Math.max(0, image.height);
  if (cw === 0 || ch === 0 || iw === 0 || ih === 0) {
    return { x: 0, y: 0, width: 0, height: 0 };
  }
  const scale = Math.min(cw / iw, ch / ih);
  const width = iw * scale;
  const height = ih * scale;
  return {
    x: (cw - width) / 2,
    y: (ch - height) / 2,
    width,
    height,
  };
}

/** 归一化矩形 → 绘制区域内的像素框。 */
export function rectToBox(geometry: RectGeometry, imageBox: Box): Box {
  return {
    x: imageBox.x + clamp01(geometry.x) * imageBox.width,
    y: imageBox.y + clamp01(geometry.y) * imageBox.height,
    width: clamp01(geometry.width) * imageBox.width,
    height: clamp01(geometry.height) * imageBox.height,
  };
}

/** 归一化圆 → 外接像素框（r 以画面短边为基准）。 */
export function circleToBox(geometry: CircleGeometry, imageBox: Box): Box {
  const base = Math.min(imageBox.width, imageBox.height);
  const radius = Math.max(0, geometry.r) * base;
  const cx = imageBox.x + clamp01(geometry.cx) * imageBox.width;
  const cy = imageBox.y + clamp01(geometry.cy) * imageBox.height;
  return {
    x: cx - radius,
    y: cy - radius,
    width: radius * 2,
    height: radius * 2,
  };
}

export function polygonBox(geometry: PolygonGeometry, imageBox: Box): Box {
  const xs = geometry.points.map((p) => imageBox.x + clamp01(p[0]) * imageBox.width);
  const ys = geometry.points.map((p) => imageBox.y + clamp01(p[1]) * imageBox.height);
  if (xs.length === 0) return { x: imageBox.x, y: imageBox.y, width: 0, height: 0 };
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const maxX = Math.max(...xs);
  const maxY = Math.max(...ys);
  return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
}

export function hotspotBox(geometry: HotspotGeometry, imageBox: Box): Box {
  if ('points' in geometry) return polygonBox(geometry, imageBox);
  if ('r' in geometry) return circleToBox(geometry, imageBox);
  return rectToBox(geometry, imageBox);
}

/** 多边形 → 绘制区域内的绝对像素点串，供 SVG overlay 使用。 */
export function polygonPoints(geometry: PolygonGeometry, imageBox: Box): string {
  return geometry.points
    .map((p) => `${imageBox.x + clamp01(p[0]) * imageBox.width},${imageBox.y + clamp01(p[1]) * imageBox.height}`)
    .join(' ');
}

/**
 * 判断归一化点是否落在热点内（键盘/触控命中与单元测试都用它）。
 * aspect = 图像宽/高。圆的 r 以短边为基准，因此短边方向按 r 比较，
 * 长边方向按 r 乘以短边/长边比较。
 */
export function hotspotContainsPoint(
  geometry: HotspotGeometry,
  nx: number,
  ny: number,
  aspect = 1
): boolean {
  if ('points' in geometry) {
    const pts = geometry.points;
    let inside = false;
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      const [xi, yi] = pts[i];
      const [xj, yj] = pts[j];
      const intersect = yi > ny !== yj > ny && nx < ((xj - xi) * (ny - yi)) / (yj - yi + Number.EPSILON) + xi;
      if (intersect) inside = !inside;
    }
    return inside;
  }
  if ('r' in geometry) {
    const rx = aspect >= 1 ? geometry.r / aspect : geometry.r;
    const ry = aspect >= 1 ? geometry.r : geometry.r * aspect;
    const dx = (nx - geometry.cx) / (rx || Number.EPSILON);
    const dy = (ny - geometry.cy) / (ry || Number.EPSILON);
    return dx * dx + dy * dy <= 1;
  }
  return (
    nx >= geometry.x &&
    nx <= geometry.x + geometry.width &&
    ny >= geometry.y &&
    ny <= geometry.y + geometry.height
  );
}

/**
 * 缩放后的位移：让归一化焦点 (focusX, focusY) 落在容器中心。
 * 与 CSS `translate(...) scale(s)` 的顺序一致。
 */
export function focusTranslate(focusX: number, focusY: number, scale: number): { x: number; y: number } {
  return {
    x: (0.5 - clamp01(focusX)) * scale * 100,
    y: (0.5 - clamp01(focusY)) * scale * 100,
  };
}

export function clamp01(value: number): number {
  if (Number.isNaN(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

export function clamp(value: number, min: number, max: number): number {
  if (Number.isNaN(value)) return min;
  return Math.min(max, Math.max(min, value));
}

/** 把像素框转换成 CSS 百分比样式，供热点层内部定位。 */
export function boxToPercent(box: Box, imageBox: Box): { left: string; top: string; width: string; height: string } {
  const w = imageBox.width || 1;
  const h = imageBox.height || 1;
  return {
    left: `${((box.x - imageBox.x) / w) * 100}%`,
    top: `${((box.y - imageBox.y) / h) * 100}%`,
    width: `${(box.width / w) * 100}%`,
    height: `${(box.height / h) * 100}%`,
  };
}