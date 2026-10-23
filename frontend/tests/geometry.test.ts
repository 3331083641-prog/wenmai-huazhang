import test from 'node:test';
import assert from 'node:assert/strict';
import {
  computeContainBox,
  hotspotBox,
  hotspotContainsPoint,
  focusTranslate,
  rectToBox,
  circleToBox,
  boxToPercent,
  clamp,
  clamp01,
} from '../src/features/culture-experience/utils/geometry.ts';
import type { HotspotGeometry } from '../src/features/culture-experience/types.ts';

test('contain box：正方形图放进宽容器，左右留黑边、垂直占满', () => {
  const box = computeContainBox({ width: 1000, height: 500 }, { width: 1024, height: 1024 });
  assert.equal(box.height, 500);
  assert.equal(box.width, 500);
  assert.equal(box.x, 250);
  assert.equal(box.y, 0);
});

test('contain box：正方形图放进高容器，上下留黑边', () => {
  const box = computeContainBox({ width: 400, height: 900 }, { width: 1024, height: 1024 });
  assert.equal(box.width, 400);
  assert.equal(box.height, 400);
  assert.equal(box.x, 0);
  assert.equal(box.y, 250);
});

test('contain box：尺寸为 0 时返回空框，调用方应跳过渲染', () => {
  assert.deepEqual(computeContainBox({ width: 0, height: 0 }, { width: 1024, height: 1024 }), {
    x: 0,
    y: 0,
    width: 0,
    height: 0,
  });
  assert.deepEqual(computeContainBox({ width: 800, height: 600 }, { width: 0, height: 0 }), {
    x: 0,
    y: 0,
    width: 0,
    height: 0,
  });
});

test('矩形换算：叠加绘制区域偏移后位置正确', () => {
  const imageBox = { x: 100, y: 50, width: 400, height: 400 };
  const box = rectToBox({ x: 0.25, y: 0.5, width: 0.1, height: 0.2 }, imageBox);
  assert.deepEqual(box, { x: 200, y: 250, width: 40, height: 80 });
});

test('圆形换算：r 以短边为基准，外接框边长 = 2r * 短边', () => {
  const imageBox = { x: 0, y: 0, width: 600, height: 600 };
  const box = circleToBox({ cx: 0.5, cy: 0.5, r: 0.1 }, imageBox);
  assert.equal(box.width, 120);
  assert.equal(box.height, 120);
  assert.equal(box.x, 240);
  assert.equal(box.y, 240);
});

test('多边形与外接框：hotspotBox 对三种形状都返回正尺寸', () => {
  const imageBox = { x: 0, y: 0, width: 100, height: 100 };
  const polygons: HotspotGeometry = {
    points: [
      [0.2, 0.2],
      [0.8, 0.2],
      [0.5, 0.9],
    ],
  };
  const box = hotspotBox(polygons, imageBox);
  assert.equal(box.x, 20);
  assert.equal(box.y, 20);
  assert.equal(box.width, 60);
  assert.equal(box.height, 70);
});

test('命中测试：矩形四角与外部', () => {
  const geometry: HotspotGeometry = { x: 0.2, y: 0.2, width: 0.2, height: 0.2 };
  assert.equal(hotspotContainsPoint(geometry, 0.2, 0.2), true);
  assert.equal(hotspotContainsPoint(geometry, 0.4, 0.4), true);
  assert.equal(hotspotContainsPoint(geometry, 0.41, 0.3), false);
  assert.equal(hotspotContainsPoint(geometry, 0.1, 0.3), false);
});

test('命中测试：圆在 1:1 图上等价于正圆', () => {
  const geometry: HotspotGeometry = { cx: 0.5, cy: 0.5, r: 0.1 };
  assert.equal(hotspotContainsPoint(geometry, 0.5, 0.5, 1), true);
  assert.equal(hotspotContainsPoint(geometry, 0.59, 0.5, 1), true);
  assert.equal(hotspotContainsPoint(geometry, 0.61, 0.5, 1), false);
});

test('命中测试：多边形用射线法，凹多边形的凹口不算命中', () => {
  // 一个「V」形凹多边形
  const geometry: HotspotGeometry = {
    points: [
      [0.1, 0.1],
      [0.9, 0.1],
      [0.9, 0.9],
      [0.5, 0.4],
      [0.1, 0.9],
    ],
  };
  assert.equal(hotspotContainsPoint(geometry, 0.5, 0.2), true);
  assert.equal(hotspotContainsPoint(geometry, 0.2, 0.3), true);
  // 凹口内部（V 的开口处）不应命中
  assert.equal(hotspotContainsPoint(geometry, 0.5, 0.75), false);
});

test('缩放位移：焦点在中心时不动，偏离时按倍数反推', () => {
  assert.deepEqual(focusTranslate(0.5, 0.5, 2), { x: 0, y: 0 });
  const moved = focusTranslate(0.35, 0.2, 2);
  assert.ok(Math.abs(moved.x - 30) < 1e-9, `x 应为 30，实际 ${moved.x}`);
  assert.ok(Math.abs(moved.y - 60) < 1e-9, `y 应为 60，实际 ${moved.y}`);
});

test('边界：clamp / clamp01 处理越界与 NaN', () => {
  assert.equal(clamp(5, 0, 3), 3);
  assert.equal(clamp(-5, 0, 3), 0);
  assert.equal(clamp(Number.NaN, 1, 3), 1);
  assert.equal(clamp01(1.4), 1);
  assert.equal(clamp01(-0.2), 0);
  assert.equal(clamp01(Number.NaN), 0);
});

test('百分比样式：框与绘制区域一致时为 0%–100%', () => {
  const imageBox = { x: 10, y: 20, width: 200, height: 100 };
  const style = boxToPercent({ ...imageBox }, imageBox);
  assert.equal(style.left, '0%');
  assert.equal(style.top, '0%');
  assert.equal(style.width, '100%');
  assert.equal(style.height, '100%');
});