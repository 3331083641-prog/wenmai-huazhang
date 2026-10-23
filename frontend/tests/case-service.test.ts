import test from 'node:test';
import assert from 'node:assert/strict';

import { mergeCases, normalizeAnalysis, normalizeCase, type GalleryCase } from '../src/services/caseService.ts';

const base = {
  caseId: 'zhuxianzhen',
  caseOrigin: 'curated' as const,
  styleId: 'zhuxianzhen',
  styleName: '朱仙镇木版年画',
  artworkTitle: '瑞猫迎春',
  theme: '瑞猫迎春',
  generatedAt: '2026-10-08T10:34:33+08:00',
  styleStrength: 0.65,
  analysisSource: 'qwen3_vl',
  imageUrl: '/examples/zhuxianzhen/generated.png',
};

test('normalizeCase：缺少图片地址的条目会被丢弃', () => {
  assert.equal(normalizeCase({ ...base, imageUrl: '' }), null);
  assert.equal(normalizeCase({ ...base, imageUrl: undefined }), null);
});

test('normalizeCase：后端案例标记为 runtime，缺省时按 curated 处理', () => {
  const runtime = normalizeCase({ ...base, caseId: 'qinghua-20261020-191500-abcd', caseOrigin: 'runtime', imageUrl: 'http://x/g.png' });
  assert.equal(runtime?.caseOrigin, 'runtime');
  const legacy = normalizeCase({ ...base, caseOrigin: undefined, imageUrl: 'http://x/g.png' });
  assert.equal(legacy?.caseOrigin, 'curated');
});

test('normalizeCase：空的 experienceId 视为没有互动解读', () => {
  const item = normalizeCase({ ...base, experienceId: '', imageUrl: 'http://x/g.png' });
  assert.equal(item?.experienceId, undefined);
  const linked = normalizeCase({ ...base, experienceId: 'zhuxianzhen-ruimao', imageUrl: 'http://x/g.png' });
  assert.equal(linked?.experienceId, 'zhuxianzhen-ruimao');
});

test('normalizeCase：缺字段时给出可用兜底，不抛错', () => {
  // 没有 caseId / styleId 的条目无法去重与定位，直接丢弃
  assert.equal(normalizeCase({ imageUrl: 'http://x/g.png' }), null);
  const item = normalizeCase({ caseId: 'qinghua-20261020-191500-abcd', imageUrl: 'http://x/g.png' });
  assert.ok(item);
  assert.equal(item?.artworkTitle, '未命名作品');
  assert.equal(item?.styleName, '传统风格');
  assert.deepEqual(item?.visionAnalysis.visual_features, []);
  assert.equal(item?.visionAnalysis.theme_alignment, '中');
});

test('normalizeAnalysis：非法枚举值回落到安全值，数组字段保持数组', () => {
  const analysis = normalizeAnalysis({
    theme_alignment: '很高',
    style_alignment: '有点像',
    visual_features: '不是数组',
    dominant_colors: ['朱红', '', null, '墨黑'],
  });
  assert.equal(analysis.theme_alignment, '中');
  assert.equal(analysis.style_alignment, '基本');
  assert.deepEqual(analysis.visual_features, []);
  assert.deepEqual(analysis.dominant_colors, ['朱红', '墨黑']);
});

test('mergeCases：运行期案例排在最前，同 caseId 时不重复且内置优先', () => {
  const curated = [{ ...base } as GalleryCase];
  const runtime = [
    { ...base, caseId: 'qinghua-20261020-191500-abcd', caseOrigin: 'runtime' as const, imageUrl: 'http://x/new.png', visionAnalysis: normalizeAnalysis({}) },
    { ...base, caseId: 'zhuxianzhen', caseOrigin: 'runtime' as const, imageUrl: 'http://x/dup.png', visionAnalysis: normalizeAnalysis({}) },
  ];
  const merged = mergeCases(curated, runtime);
  assert.equal(merged.length, 2);
  assert.equal(merged[0].caseId, 'qinghua-20261020-191500-abcd');
  assert.equal(merged[1].caseId, 'zhuxianzhen');
  // 同 caseId 时保留内置那件（它的图片是打包进前端的，离线可用）
  assert.equal(merged[1].imageUrl, '/examples/zhuxianzhen/generated.png');
});

test('mergeCases：没有运行期案例时原样返回内置列表', () => {
  const curated = [{ ...base } as GalleryCase];
  assert.deepEqual(mergeCases(curated, []), curated);
});