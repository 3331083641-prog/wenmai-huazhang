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
  return (s.items||[]).map(i=>({key:i.key,p:i.propId,x:+i.x.toFixed(3),y:+i.y.toFixed(3),z:+i.z.toFixed(3),
    parent:i.parentInstanceId||null,state:i.interactionState||null})); })()`);
const pick = async (text) => cdp.ev(`(() => { const p=document.querySelector('[aria-label="器物图库"]');
  const b=[...p.querySelectorAll('button')].find(x=>x.textContent.includes(${JSON.stringify(text)})); if(!b) return 'no-card'; b.click(); return 'ok'; })()`);
const clearItems = async () => {
  await cdp.ev(`(() => { const p=document.querySelector('[aria-label="器物图库"]');
    const b=p && [...p.querySelectorAll('button')].find(x=>x.textContent.includes('清空器物')); b && b.click(); return !!b; })()`);
  await cdp.sleep(320);
};
const hitFor = async (tag, cx, cy) => cdp.ev(`(() => {
  for (let r = 0; r <= 60; r += 4) for (let dy = -r; dy <= r; dy += 4) for (let dx = -r; dx <= r; dx += 4) {
    if (r > 0 && Math.max(Math.abs(dx), Math.abs(dy)) !== r) continue;
    const hits = window.__galleryPick(${cx} + dx, ${cy} + dy) || [];
    if (hits.some((h) => (h.names || []).some((n) => n.includes(${JSON.stringify(tag)})))) return { x: ${cx} + dx, y: ${cy} + dy };
  }
  return null;
})()`);
const clickItem = async (tag, x, y, z, h) => {
  const p = await cdp.ev(`window.__galleryProject(${x}, ${y + h * 0.45}, ${z})`);
  if (!p?.inView) return null;
  const hit = await hitFor(tag, p.x, p.y);
  if (!hit) return null;
  await cdp.clickAt(hit.x, hit.y, 900);
  return hit;
};

const out = {};

/* ---------- 多实例：同款莲花灯两件 ---------- */
await pick('莲花暖光立灯');
await cdp.sleep(280);
await cdp.clickAt(420, 700, 800);
await pick('莲花暖光立灯');
await cdp.sleep(280);
await cdp.clickAt(900, 700, 800);
let list = await items();
const lamps = list.filter((i) => i.p === 'DIY_A05');
out.lampsPlaced = lamps.map((l) => ({ key: l.key, x: l.x, z: l.z, y: l.y }));
if (lamps.length >= 2) {
  await clickItem(lamps[0].key, lamps[0].x, lamps[0].y, lamps[0].z, heights.DIY_A05 ?? 1.53);
  await cdp.sleep(600);
  list = await items();
  out.afterLamp1 = list.filter((i) => i.p === 'DIY_A05').map((l) => ({ key: l.key, state: l.state }));
  await cdp.shot('asset-multi-instance');
  const second = list.filter((i) => i.p === 'DIY_A05')[1];
  await clickItem(second.key, second.x, second.y, second.z, heights.DIY_A05 ?? 1.53);
  await cdp.sleep(600);
  list = await items();
  out.afterLamp2 = list.filter((i) => i.p === 'DIY_A05').map((l) => ({ key: l.key, state: l.state }));
  await cdp.shot('asset-multi-instance-both');
}

/* ---------- 编辑模式：只选中不互动 ---------- */
await clearItems();
await pick('莲花暖光立灯');
await cdp.sleep(280);
await cdp.clickAt(700, 690, 800);
list = await items();
const lamp = list.find((i) => i.p === 'DIY_A05');
if (lamp) {
  const toggled = await cdp.ev(`(() => { const b=document.querySelector('[data-testid="diy-edit-entry"]'); if(!b) return false; b.click(); return true; })()`);
  await cdp.sleep(450);
  out.editToggle = toggled;
  out.editButtonText = await cdp.ev(`(() => { const b=document.querySelector('[data-testid="diy-edit-entry"]'); return b?b.textContent.trim():null; })()`);
  const clickEdit = await clickItem(lamp.key, lamp.x, lamp.y, lamp.z, heights.DIY_A05 ?? 1.53);
  list = await items();
  out.stateInEdit = list.find((i) => i.key === lamp.key)?.state ?? null;
  out.selectedText = await cdp.ev(`(() => { const el=[...document.querySelectorAll('p')].find(p=>p.textContent.includes('已选中')); return el?el.textContent.trim():null; })()`);
  await cdp.shot('asset-edit-mode');
  // 退出编辑后再点，应正常互动
  await cdp.ev(`(() => { const b=document.querySelector('[data-testid="diy-edit-entry"]'); b && b.click(); })()`);
  await cdp.sleep(450);
  out.clickEditPoint = clickEdit;
  await clickItem(lamp.key, lamp.x, lamp.y, lamp.z, heights.DIY_A05 ?? 1.53);
  await cdp.sleep(400);
  list = await items();
  out.stateNormal = list.find((i) => i.key === lamp.key)?.state ?? null;
  await cdp.shot('asset-edit-mode-exit');
}

console.log(JSON.stringify({ out, errs: cdp.errors.slice(0, 6) }, null, 1));
fs.writeFileSync('D:\\wenmai-huazhang\\scripts\\_verify\\multi_edit.json', JSON.stringify(out, null, 1));
cdp.close();