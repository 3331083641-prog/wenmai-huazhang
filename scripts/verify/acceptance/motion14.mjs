import fs from 'node:fs';
import { connect, openDiyPanel } from './lib.mjs';

let cdp = await connect();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const revive = async (why) => {
  try { cdp.ws.close(); } catch { /* ignore */ }
  cdp = await connect();
  await sleep(1200);
};
const ev = async (expr) => {
  try { return await cdp.ev(expr); } catch { await revive('ev'); return cdp.ev(expr); }
};
const clickAt = async (x, y, settle = 800) => {
  try { await cdp.clickAt(x, y, settle); } catch { await revive('click'); await cdp.clickAt(x, y, settle); }
};

await cdp.reload(12000);
await ev(`localStorage.removeItem('wenmai-gallery-diy-v1')`);
await cdp.reload(11000);
await ev(openDiyPanel);
await sleep(2600);

const heights = await ev(`(() => { const m={}; (window.__wenmaiAudit?window.__wenmaiAudit():[]).forEach(a=>{m[a.id]=a.size[1];}); return m; })()`);
const items = async () => ev(`(() => { const s=JSON.parse(localStorage.getItem('wenmai-gallery-diy-v1')||'{}').state||{};
  return (s.items||[]).map(i=>({key:i.key,p:i.propId,x:+i.x.toFixed(3),y:+i.y.toFixed(3),z:+i.z.toFixed(3),surface:i.surfaceId||null})); })()`);
const clearItems = async () => {
  await ev(`(() => { const p=document.querySelector('[aria-label="器物图库"]');
    const b=p && [...p.querySelectorAll('button')].find(x=>x.textContent.includes('清空器物')); b && b.click(); return !!b; })()`);
  await sleep(300);
};
const pick = async (text) => ev(`(() => { const p=document.querySelector('[aria-label="器物图库"]'); if(!p) return 'no-panel';
  const b=[...p.querySelectorAll('button')].find(x=>x.textContent.includes(${JSON.stringify(text)}));
  if(!b) return 'no-card'; b.click(); return 'ok'; })()`);
const findHit = async (id, cx, cy, maxR = 70) => ev(`(() => {
  for (let r = 0; r <= ${maxR}; r += 5) for (let dy = -r; dy <= r; dy += 5) for (let dx = -r; dx <= r; dx += 5) {
    if (r > 0 && Math.max(Math.abs(dx), Math.abs(dy)) !== r) continue;
    const hits = window.__galleryPick(${cx} + dx, ${cy} + dy) || [];
    for (const hit of hits) if ((hit.names || []).some((n) => n.startsWith(${JSON.stringify(id)}))) return { x: ${cx} + dx, y: ${cy} + dy };
  }
  return null;
})()`);
const snapshot = async (id) => ev(`window.__gallerySnapshot(${JSON.stringify(id + '_')})`);

const DEFS = [
  { id: 'DIY_A01', name: '胡桃木博古架' },
  { id: 'DIY_A02', name: '云纹玻璃展柜' },
  { id: 'DIY_A04', name: '宋式折叠屏风' },
  { id: 'DIY_A05', name: '莲花暖光立灯' },
  { id: 'DIY_A07', name: '六方悬挂宫灯', kind: 'hang' },
  { id: 'DIY_A09', name: '宋式铜座文化展签架', kind: 'info' },
  { id: 'DIY_B02', name: '木版套印工作台' },
  { id: 'DIY_C02', name: '彩色丝线陈列架', kind: 'surface' },
  { id: 'DIY_D01', name: '宋式画案与矿物颜料' },
  { id: 'DIY_D04', name: '青绿山水微缩摆件', kind: 'surface' },
  { id: 'DIY_E01', name: '青花瓷梅瓶', kind: 'surface' },
  { id: 'DIY_E02', name: '青花瓷茶具套组', kind: 'surface' },
  { id: 'DIY_E05', name: '青花瓷文创花灯', kind: 'surface' },
  { id: 'DIY_F05', name: '可旋转剪纸走马灯', kind: 'surface' },
];

const floors = {};
const compare = (a, b) => {
  if (!a || !b) return { changed: [], maxDelta: null };
  const changed = [];
  let maxDelta = 0;
  for (const [name, values] of Object.entries(a)) {
    const other = b[name];
    if (!other) continue;
    let delta = 0;
    for (let i = 0; i < 6; i += 1) delta = Math.max(delta, Math.abs(values[i] - other[i]));
    if (delta > 0.002) { changed.push({ name, delta: Number(delta.toFixed(4)) }); maxDelta = Math.max(maxDelta, delta); }
  }
  changed.sort((x, y) => y.delta - x.delta);
  return { changed, maxDelta: Number(maxDelta.toFixed(4)) };
};

const rows = [];
for (const def of DEFS) {
  const row = { id: def.id, name: def.name };
  try {
    await clearItems();
    let point = [640, 680];
    if (def.kind === 'surface') {
      await pick('胡桃木博古架');
      await sleep(280);
      await clickAt(600, 690, 800);
      const shelf = (await items()).find((i) => i.p === 'DIY_A01');
      if (shelf) {
        const p = await ev(`window.__galleryProject(${shelf.x}, ${shelf.y + (heights.DIY_A01 ?? 1.845)}, ${shelf.z})`);
        if (p?.inView) point = [p.x, p.y - 26];
      }
    } else if (def.kind === 'hang') {
      const spot = await ev(`(() => {
        for (let y = 140; y <= 620; y += 20) for (let x = 160; x <= 980; x += 20) {
          if (document.elementFromPoint(x,y)?.tagName !== 'CANVAS') continue;
          const r = window.__galleryHang(x,y);
          if (r && /JOIST|BEAM/.test(r.carrier)) return { x, y };
        }
        return null;
      })()`);
      if (spot) point = [spot.x, spot.y];
    }
    await pick(def.name);
    await sleep(300);
    await clickAt(point[0], point[1], 850);
    const placed = (await items()).reverse().find((i) => i.p === def.id);
    if (!placed) { row.note = 'not-placed'; rows.push(row); continue; }
    row.placed = placed;
    const cy = placed.y + (heights[def.id] ?? 0.6) * 0.45;
    const proj = await ev(`window.__galleryProject(${placed.x}, ${cy}, ${placed.z})`);
    const hit = proj?.inView ? await findHit(def.id, proj.x, proj.y) : null;
    if (!hit) { row.note = 'no-hit'; rows.push(row); continue; }
    await sleep(500);
    const before = await snapshot(def.id);
    await clickAt(hit.x, hit.y, 240);
    await sleep(900);
    const during = await snapshot(def.id);
    const step1 = compare(before, during);
    row.parts = Object.keys(before ?? {}).length;
    row.changedAtActivation = step1.changed.slice(0, 6);
    row.changedCount = step1.changed.length;
    if (def.kind !== 'info') {
      await clickAt(hit.x, hit.y, 240);
      await sleep(1100);
      const after = await snapshot(def.id);
      const step2 = compare(before, after);
      row.changedAfterReset = step2.changed.slice(0, 4);
      row.resetDelta = step2.maxDelta;
    } else {
      await ev(`(() => { const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='关闭'); b && b.click(); })()`);
    }
  } catch (error) {
    row.note = `error:${String(error.message).slice(0, 80)}`;
    await revive('row');
  }
  rows.push(row);
  console.log(JSON.stringify(rows[rows.length - 1]));
  fs.writeFileSync('D:\\Codex\\wenmai-verify\\motion14.json', JSON.stringify(rows, null, 1));
}
console.log('SUMMARY', JSON.stringify(rows.map((r) => ({ id: r.id, parts: r.parts, changed: r.changedCount, top: r.changedAtActivation?.[0], note: r.note }))));
cdp.close();