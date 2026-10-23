import fs from 'node:fs';
import { connect, openDiyPanel } from './lib.mjs';

const cdp = await connect();
await cdp.reload(11000);
await cdp.ev(`localStorage.removeItem('wenmai-gallery-diy-v1')`);
await cdp.reload(10000);
await cdp.ev(openDiyPanel);
await cdp.sleep(2500);

const heights = await cdp.ev(`(() => { const m={}; (window.__wenmaiAudit?window.__wenmaiAudit():[]).forEach(a=>{m[a.id]=a.size[1];}); return m; })()`);
const items = async () => cdp.ev(`(() => { const s=JSON.parse(localStorage.getItem('wenmai-gallery-diy-v1')||'{}').state||{};
  return (s.items||[]).map(i=>({key:i.key,p:i.propId,x:+i.x.toFixed(3),y:+i.y.toFixed(3),z:+i.z.toFixed(3),rot:+i.rotY.toFixed(3),
    parent:i.parentInstanceId||null})); })()`);
const pick = async (t) => cdp.ev(`(() => { const p=document.querySelector('[aria-label="器物图库"]');
  const b=[...p.querySelectorAll('button')].find(x=>x.textContent.includes(${JSON.stringify(t)})); if(!b) return 'no-card'; b.click(); return 'ok'; })()`);
const hitFor = async (tag, cx, cy) => cdp.ev(`(() => {
  for (let r = 0; r <= 90; r += 4) for (let dy = -r; dy <= r; dy += 4) for (let dx = -r; dx <= r; dx += 4) {
    if (r > 0 && Math.max(Math.abs(dx), Math.abs(dy)) !== r) continue;
    const hits = window.__galleryPick(${cx} + dx, ${cy} + dy) || [];
    if (hits.some((h) => (h.names || []).some((n) => n.includes(${JSON.stringify(tag)})))) return { x: ${cx} + dx, y: ${cy} + dy };
  }
  return null;
})()`);

await pick('胡桃木博古架');
await cdp.sleep(280);
await cdp.clickAt(600, 690, 850);
let list = await items();
const shelf = list.find((i) => i.p === 'DIY_A01');
await pick('青花瓷梅瓶');
await cdp.sleep(280);
const top = await cdp.ev(`window.__galleryProject(${shelf.x}, ${shelf.y + (heights.DIY_A01 ?? 1.845)}, ${shelf.z})`);
await cdp.clickAt(top.x - 34, top.y - 18, 900);
list = await items();
const vase = list.find((i) => i.p === 'DIY_E01');
console.log('before', JSON.stringify({ shelf, vase }));

// 选博古架：投影器身中下部（避开顶部梅瓶）
const mid = await cdp.ev(`window.__galleryProject(${shelf.x}, ${shelf.y + (heights.DIY_A01 ?? 1.845) * 0.35}, ${shelf.z})`);
console.log('shelf mid proj', JSON.stringify(mid));
const hit = await hitFor(shelf.key, mid.x, mid.y);
console.log('shelf hit', JSON.stringify(hit));
if (hit) {
  // 选中承载物要走「调整位置」模式：平时点击是互动，只选中不互动
  await cdp.ev(`(() => { const b=document.querySelector('[data-testid="diy-edit-entry"]'); if(!b) return false; b.click(); return true; })()`);
  await cdp.sleep(400);
  await cdp.clickAt(hit.x, hit.y, 700);
  console.log('selected:', await cdp.ev(`(() => { const el=[...document.querySelectorAll('p')].find(p=>p.textContent.includes('已选中')); return el?el.textContent.trim():null; })()`));
  const rotated = await cdp.ev(`(() => { const b=document.querySelector('button[aria-label="右转 15°"]'); if(!b) return false; b.click(); return true; })()`);
  await cdp.sleep(600);
  const after = await items();
  const s2 = after.find((i) => i.p === 'DIY_A01');
  const v2 = after.find((i) => i.p === 'DIY_E01');
  const ox = vase.x - shelf.x;
  const oz = vase.z - shelf.z;
  const angle = (s2.rot ?? 0) - (shelf.rot ?? 0);
  const expectedX = shelf.x + ox * Math.cos(angle) - oz * Math.sin(angle);
  const expectedZ = shelf.z + ox * Math.sin(angle) + oz * Math.cos(angle);
  const result = {
    rotated,
    angle,
    shelfRot: [shelf.rot, s2.rot],
    vaseBefore: { x: vase.x, z: vase.z, y: vase.y },
    vaseAfter: { x: v2.x, z: v2.z, y: v2.y },
    expected: { x: Number(expectedX.toFixed(3)), z: Number(expectedZ.toFixed(3)) },
    orbitMatches: Math.abs(v2.x - expectedX) < 0.005 && Math.abs(v2.z - expectedZ) < 0.005,
    yPreserved: Math.abs(v2.y - vase.y) < 1e-6,
    parentPreserved: v2.parent === shelf.key,
  };
  console.log('rotate-follow', JSON.stringify(result));
  fs.writeFileSync('D:\\wenmai-huazhang\\scripts\\_verify\\rotate_follow.json', JSON.stringify(result, null, 1));
  await cdp.shot('asset-surface-follow-rotate');
}
console.log('errs', JSON.stringify(cdp.errors.slice(0, 4)));
cdp.close();