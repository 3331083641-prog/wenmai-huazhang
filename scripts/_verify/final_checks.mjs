import fs from 'node:fs';
import { connect, openDiyPanel } from './lib.mjs';

const cdp = await connect();
await cdp.reload(12000);
cdp.errors.length = 0;
await cdp.ev(`localStorage.removeItem('wenmai-gallery-diy-v1')`);
await cdp.reload(11000);
await cdp.ev(openDiyPanel);
await cdp.sleep(2600);

const heights = await cdp.ev(`(() => { const m={}; (window.__wenmaiAudit?window.__wenmaiAudit():[]).forEach(a=>{m[a.id]=a.size[1];}); return m; })()`);
const items = async () => cdp.ev(`(() => { const s=JSON.parse(localStorage.getItem('wenmai-gallery-diy-v1')||'{}').state||{};
  return (s.items||[]).map(i=>({key:i.key,p:i.propId,x:+i.x.toFixed(3),y:+i.y.toFixed(3),z:+i.z.toFixed(3),rot:+i.rotY.toFixed(3),
    parent:i.parentInstanceId||null,state:i.interactionState||null})); })()`);
const pick = async (text) => cdp.ev(`(() => { const p=document.querySelector('[aria-label="器物图库"]');
  const b=[...p.querySelectorAll('button')].find(x=>x.textContent.includes(${JSON.stringify(text)})); if(!b) return 'no-card'; b.click(); return 'ok'; })()`);
const hitFor = async (tag, cx, cy) => cdp.ev(`(() => {
  for (let r = 0; r <= 60; r += 4) for (let dy = -r; dy <= r; dy += 4) for (let dx = -r; dx <= r; dx += 4) {
    if (r > 0 && Math.max(Math.abs(dx), Math.abs(dy)) !== r) continue;
    const hits = window.__galleryPick(${cx} + dx, ${cy} + dy) || [];
    if (hits.some((h) => (h.names || []).some((n) => n.includes(${JSON.stringify(tag)})))) return { x: ${cx} + dx, y: ${cy} + dy };
  }
  return null;
})()`);

const out = {};

/* 1) surface：博古架顶面放梅瓶，截图与数据 */
await pick('胡桃木博古架');
await cdp.sleep(280);
await cdp.clickAt(600, 690, 850);
let list = await items();
const shelf = list.find((i) => i.p === 'DIY_A01');
if (shelf) {
  const top = await cdp.ev(`window.__galleryProject(${shelf.x}, ${shelf.y + (heights.DIY_A01 ?? 1.845)}, ${shelf.z})`);
  await pick('青花瓷梅瓶');
  await cdp.sleep(280);
  await cdp.clickAt(top.x, top.y - 30, 900);
  list = await items();
  const vase = list.find((i) => i.p === 'DIY_E01');
  out.surface = {
    shelf: { key: shelf.key, y: shelf.y },
    vase: vase && { y: vase.y, parent: vase.parent, expectedParent: shelf.key, parentOk: vase.parent === shelf.key },
    expectedY: Number((shelf.y + (heights.DIY_A01 ?? 1.845)).toFixed(3)),
  };
  await cdp.shot('asset-surface-vase');

  /* 2) 旋转承载物：子物件应绕承载物中心一起转 */
  if (vase) {
    const hit = await hitFor(shelf.key, Math.round((top.x + 600) / 2), Math.round((top.y + 690) / 2) + 30);
    if (hit) {
      await cdp.clickAt(hit.x, hit.y, 700);
      const rotated = await cdp.ev(`(() => { const b=document.querySelector('button[aria-label="右转 15°"]'); if(!b) return false; b.click(); return true; })()`);
      await cdp.sleep(500);
      const after = await items();
      const s2 = after.find((i) => i.p === 'DIY_A01');
      const v2 = after.find((i) => i.p === 'DIY_E01');
      const ox = vase.x - shelf.x;
      const oz = vase.z - shelf.z;
      const angle = (s2?.rot ?? 0) - (shelf.rot ?? 0);
      const expectedX = shelf.x + ox * Math.cos(angle) - oz * Math.sin(angle);
      const expectedZ = shelf.z + ox * Math.sin(angle) + oz * Math.cos(angle);
      out.rotationFollow = {
        rotated,
        angle,
        shelfRotBefore: shelf.rot,
        shelfRotAfter: s2?.rot,
        vaseBefore: { x: vase.x, z: vase.z },
        vaseAfter: v2 && { x: v2.x, z: v2.z },
        expected: { x: Number(expectedX.toFixed(3)), z: Number(expectedZ.toFixed(3)) },
        matches: Boolean(v2) && Math.abs(v2.x - expectedX) < 0.005 && Math.abs(v2.z - expectedZ) < 0.005,
        yPreserved: v2 ? Math.abs(v2.y - vase.y) < 1e-6 : null,
        parentPreserved: v2 ? v2.parent === shelf.key : null,
      };
      await cdp.shot('asset-surface-follow-rotate');
    }
  }
}

/* 3) 兼容旧布展：没有 surfaceId/parent 的旧存档也要能载入 */
const legacy = {
  state: {
    items: [
      { key: 'legacy-1', propId: 'DIY_A05', x: -1.2, y: 0.25, z: 0.4, rotY: 0, scale: 1, variant: 0, mount: 'ground' },
      { key: 'legacy-2', propId: 'DIY_A09', x: 1.2, y: 0.25, z: 0.4, rotY: 0, scale: 1, variant: 0, mount: 'ground' },
    ],
    roofTint: 'dai',
  },
  version: 1,
};
await cdp.ev(`localStorage.setItem('wenmai-gallery-diy-v1', ${JSON.stringify(JSON.stringify(legacy))})`);
await cdp.reload(11000);
cdp.errors.length = 0;
await cdp.sleep(2500);
out.legacy = {
  rendered: await cdp.ev(`(() => { const s=JSON.parse(localStorage.getItem('wenmai-gallery-diy-v1')||'{}').state||{}; return (s.items||[]).length; })()`),
  errors: cdp.errors.slice(0, 4),
  panelChip: await cdp.ev(`(() => { const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim().startsWith('器物')); return b?b.textContent.trim():null; })()`),
};
await cdp.shot('asset-legacy-save');

console.log(JSON.stringify({ out, errs: cdp.errors.slice(0, 6) }, null, 1));
fs.writeFileSync('D:\\wenmai-huazhang\\scripts\\_verify\\final_checks.json', JSON.stringify(out, null, 1));
cdp.close();