import test from 'node:test';
import assert from 'node:assert/strict';
import { validateExperienceDraft, parseExperienceDraft } from '../src/features/culture-experience/schema.ts';
import type { CultureExperienceDraft } from '../src/features/culture-experience/types.ts';
import zhuxianzhen from '../src/data/experiences/zhuxianzhen.ts';
import bianxiu from '../src/data/experiences/bianxiu.ts';
import songhua from '../src/data/experiences/songhua.ts';
import qinghua from '../src/data/experiences/qinghua.ts';
import jianzhi from '../src/data/experiences/jianzhi.ts';

const drafts: CultureExperienceDraft[] = [zhuxianzhen, bianxiu, songhua, qinghua, jianzhi];

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

test('五件作品全部通过 schema 校验', () => {
  for (const draft of drafts) {
    const result = validateExperienceDraft(draft);
    assert.deepEqual(result.issues, [], `${draft.styleId} 校验失败：${JSON.stringify(result.issues)}`);
    assert.equal(result.ok, true);
  }
});

test('parseExperienceDraft 返回同一份内容（不静默改写）', () => {
  for (const draft of drafts) {
    const parsed = parseExperienceDraft(draft, draft.styleId);
    assert.equal(parsed.id, draft.id);
    assert.equal(parsed.hotspots.length, draft.hotspots.length);
    assert.equal(parsed.chapters.length, draft.chapters.length);
  }
});

test('styleId 与 id 全局唯一', () => {
  const ids = drafts.map((draft) => draft.id);
  const styleIds = drafts.map((draft) => draft.styleId);
  assert.equal(new Set(ids).size, ids.length);
  assert.equal(new Set(styleIds).size, styleIds.length);
});

test('shape 与 geometry 不一致时必须报错', () => {
  const broken = clone(zhuxianzhen);
  broken.hotspots[0].shape = 'circle';
  broken.hotspots[0].geometry = { x: 0.1, y: 0.1, width: 0.2, height: 0.2 };
  const result = validateExperienceDraft(broken);
  assert.equal(result.ok, false);
  assert.ok(result.issues.some((issue) => issue.message.includes('circle') || issue.message.includes('几何')));
});

test('confirmed 但没有来源时必须报错（不允许无出处断言）', () => {
  const broken = clone(zhuxianzhen);
  broken.hotspots[0].sourceIds = [];
  const result = validateExperienceDraft(broken);
  assert.equal(result.ok, false);
});

test('confirmed 不能同时标记为 unverified', () => {
  const broken = clone(zhuxianzhen);
  broken.hotspots[0].locationStatus = 'unverified';
  const result = validateExperienceDraft(broken);
  assert.equal(result.ok, false);
});

test('章节 index 必须从 1 开始连续', () => {
  const broken = clone(zhuxianzhen);
  broken.chapters[2].index = 7;
  const result = validateExperienceDraft(broken);
  assert.equal(result.ok, false);
});

test('章节引用了不存在的热点必须报错', () => {
  const broken = clone(zhuxianzhen);
  broken.chapters[0].focusHotspotIds = ['not-exist'];
  const result = validateExperienceDraft(broken);
  assert.equal(result.ok, false);
  assert.ok(result.issues.some((issue) => issue.message.includes('not-exist')));
});

test('layered 模式必须提供至少两层素材', () => {
  const broken = clone(songhua);
  broken.animation.mode = 'layered'; // 显式测 layered 规则，不依赖某件作品当前用的是哪个模式
  broken.animation.layers = [];
  const result = validateExperienceDraft(broken);
  assert.equal(result.ok, false);
});

test('world 模式必须提供世界资产地址', () => {
  const broken = clone(songhua);
  broken.animation.world = undefined;
  const result = validateExperienceDraft(broken);
  assert.equal(result.ok, false);
});

test('normalize：坐标越界必须被拒绝', () => {
  const broken = clone(zhuxianzhen);
  broken.hotspots[0].geometry = { x: 1.2, y: 0.1, width: 0.2, height: 0.2 };
  const result = validateExperienceDraft(broken);
  assert.equal(result.ok, false);
});