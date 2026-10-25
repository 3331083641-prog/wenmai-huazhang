import test from 'node:test';
import assert from 'node:assert/strict';
import { withBase, resolveWorldAsset, worldTuning, hotspotWorldZ } from '../src/features/painting-world/world.ts';

test('运行期画境从后端动态加载，资源地址保留来源与版本', () => {
  const manifest='http://127.0.0.1:8000/interactive/own-case/world/world.json?v=own-hash';
  assert.equal(withBase(manifest),manifest);
  assert.equal(resolveWorldAsset(manifest,'cutout-subject.webp'),
    'http://127.0.0.1:8000/interactive/own-case/world/cutout-subject.webp?v=own-hash');
  assert.equal(resolveWorldAsset('interactive/bundled/world/world.json','art.webp'),
    '/interactive/bundled/world/art.webp');
});

test('复审参数是可选项，旧精选保留默认值，新作按受限参数渲染',()=>{
  const legacy={camera:{depth_amplitude:.3}} as any;
  assert.equal(worldTuning(legacy).haze,.1);
  assert.equal(worldTuning(legacy).cutout_motion,1);
  assert.equal(worldTuning({...legacy,tuning:{haze:.03,subject_relief:.06}}).haze,.03);
  assert.equal(worldTuning({...legacy,tuning:{haze:NaN,mist:999}}).haze,.1);
  assert.equal(worldTuning({...legacy,tuning:{mist:999}}).mist,.35);
  assert.ok(Math.abs(hotspotWorldZ({depth:.5,relief_delta:.25} as any,
    {...legacy,tuning:{subject_relief:.08}})-.17)<1e-9);
});
