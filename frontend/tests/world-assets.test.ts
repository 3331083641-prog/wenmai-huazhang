import test from 'node:test';
import assert from 'node:assert/strict';
import { withBase, resolveWorldAsset } from '../src/features/painting-world/world.ts';

test('运行期画境从后端动态加载，资源地址保留来源与版本', () => {
  const manifest='http://127.0.0.1:8000/interactive/own-case/world/world.json?v=own-hash';
  assert.equal(withBase(manifest),manifest);
  assert.equal(resolveWorldAsset(manifest,'cutout-subject.webp'),
    'http://127.0.0.1:8000/interactive/own-case/world/cutout-subject.webp?v=own-hash');
  assert.equal(resolveWorldAsset('interactive/bundled/world/world.json','art.webp'),
    '/interactive/bundled/world/art.webp');
});
