import test from 'node:test';
import assert from 'node:assert/strict';
import { fitArtworkCamera, pickHotspotFromUv } from '../src/features/painting-world/geometry.ts';

test('入场取景：桌面与手机均容纳方形、横幅和竖幅的完整成图', () => {
  for (const [width,height] of [[1440,1000],[390,844]]) {
    for (const aspect of [.55,1,1.8]) {
      const fit=fitArtworkCamera({planeHeight:1,planeWidth:aspect,fov:34,amplitude:.18,width,height,entryScale:1.74});
      const visibleHeight=2*(fit.rest-.18)*Math.tan(34*Math.PI/360);
      assert.ok(visibleHeight>1);
      assert.ok(visibleHeight*width/height>aspect);
      assert.ok(fit.start>fit.rest && fit.near<fit.rest && fit.near>.18);
    }
  }
});

test('画境热点点击：Three.js 底部原点 UV 转为图片顶部原点', () => {
  const spots=[{id:'top',x:.25,y:.2},{id:'bottom',x:.25,y:.8}];
  assert.equal(pickHotspotFromUv(spots,.25,.8),'top');
  assert.equal(pickHotspotFromUv(spots,.25,.2),'bottom');
  assert.equal(pickHotspotFromUv(spots,.8,.5),null);
});

test('新作额外保留界面安全边距，旧作默认取景不变',()=>{
  const input={planeHeight:1,planeWidth:1,fov:34,amplitude:.24,width:1440,height:1000,entryScale:1.74};
  assert.ok(fitArtworkCamera({...input,margin:1.2}).rest>fitArtworkCamera(input).rest);
});
