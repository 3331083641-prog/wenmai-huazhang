import fs from 'node:fs';
import { connect, openDiyPanel } from './lib.mjs';

const OUT = 'D:\\Codex\\wenmai-verify\\accept14.json';
let cdp = await connect();
const errors = [];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const revive = async (why) => {
  try { cdp.ws.close(); } catch { /* ignore */ }
  errors.push(`revive: ${why}`);
  cdp = await connect();
  await sleep(1500);
};

const ev = async (expr) => {
  try {
    return await cdp.ev(expr);
  } catch (error) {
    await revive(String(error.message).slice(0, 80));
    return await cdp.ev(expr);
  }
};
const clickAt = async (x, y, settle = 800) => {
  try {
    await cdp.clickAt(x, y, settle);
  } catch (error) {
    await revive(`click:${String(error.message).slice(0, 60)}`);
    await cdp.clickAt(x, y, settle);
  }
};
const shot = async (name) => {
  try { return await cdp.shot(name); } catch (error) { await revive('shot'); return null; }
};
const reload = async (ms) => { await cdp.reload(ms); };

const items = async () =>
  ev(`(() => { const s=JSON.parse(localStorage.getItem('wenmai-gallery-diy-v1')||'{}').state||{};
    return (s.items||[]).map(i=>({key:i.key,p:i.propId,x:+i.x.toFixed(3),y:+i.y.toFixed(3),z:+i.z.toFixed(3),
      parent:i.parentInstanceId||null,surface:i.surfaceId||null,state:i.interactionState||null})); })()`);
const clearItems = async () => {
  await ev(`(() => { const p=document.querySelector('[aria-label="器物图库"]');
    const b=p && [...p.querySelectorAll('button')].find(x=>x.textContent.includes('清空器物')); if(b){b.click(); return true;} return false; })()`);
  await sleep(320);
};
const pick = async (text) =>
  ev(`(() => { const p=document.querySelector('[aria-label="器物图库"]'); if(!p) return 'no-panel';
    const b=[...p.querySelectorAll('button')].find(x=>x.textContent.includes(${JSON.stringify(text)}));
    if(!b) return 'no-card'; b.click(); return 'ok'; })()`);
const canvasOnly = async (x, y) => ev(`document.elementFromPoint(${x},${y})?.tagName === 'CANVAS'`);
const hoverHint = async () =>
  ev(`(() => { const el=[...document.querySelectorAll('div')].find(d=>d.children.length===0 && /^点击互动/.test(d.textContent.trim())); return el?el.textContent.trim():null; })()`);
// 在投影点附近用拾取探针找「真的能点中这件器物」的屏幕点（小件很必要）
const findHit = async (id, cx, cy, maxR = 70) =>
  ev(`(() => {
    const root = document.querySelector('canvas');
    const W = root.clientWidth, H = root.clientHeight;
    for (let r = 0; r <= ${maxR}; r += 5) {
      for (let dy = -r; dy <= r; dy += 5) {
        for (let dx = -r; dx <= r; dx += 5) {
          if (r > 0 && Math.max(Math.abs(dx), Math.abs(dy)) !== r) continue;
          const x = Math.round(${cx} + dx), y = Math.round(${cy} + dy);
          if (x < 2 || y < 2 || x > W - 2 || y > H - 2) continue;
          const hits = window.__galleryPick(x, y) || [];
          for (const hit of hits) {
            if ((hit.names || []).some((n) => n.startsWith(${JSON.stringify(id)}))) return { x, y };
          }
        }
      }
    }
    return null;
  })()`);

const FLOOR_POINT = [640, 680];
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

const results = [];

for (const def of DEFS) {
  const record = { id: def.id, name: def.name };
  try {
    if (!(await ev(`!!document.querySelector('[aria-label="器物图库"]')`))) {
      await reload(10000);
      await ev(openDiyPanel);
      await sleep(2400);
    }
    const heights = await ev(`(() => { const m={}; (window.__wenmaiAudit?window.__wenmaiAudit():[]).forEach(a=>{m[a.id]=a.size[1];}); return m; })()`);
    await clearItems();

    let placePoint = FLOOR_POINT;
    if (def.kind === 'surface') {
      await pick('胡桃木博古架');
      await sleep(300);
      await clickAt(600, 690, 800);
      const shelf = (await items()).find((i) => i.p === 'DIY_A01');
      if (shelf) {
        const top = shelf.y + (heights.DIY_A01 ?? 1.845);
        const p = await ev(`window.__galleryProject(${shelf.x}, ${top}, ${shelf.z})`);
        if (p?.inView) placePoint = [p.x, p.y - 26];
        record.carrierKey = shelf.key;
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
      if (spot) placePoint = [spot.x, spot.y];
    }

    await pick(def.name);
    await sleep(320);
    await clickAt(placePoint[0], placePoint[1], 850);
    record.placePoint = placePoint;

    const list = await items();
    const placed = [...list].reverse().find((i) => i.p === def.id) ?? null;
    record.placed = placed;
    if (!placed) {
      record.activate = false;
      record.note = 'placement-failed';
      await shot(`asset-${def.id.replace('DIY_', '')}`);
      results.push(record);
      fs.writeFileSync(OUT, JSON.stringify({ results, errors }, null, 1));
      continue;
    }

    const cy = placed.y + (heights[def.id] ?? 0.6) * 0.45;
    const proj = await ev(`window.__galleryProject(${placed.x}, ${cy}, ${placed.z})`);
    record.projected = proj;
    // 投影点只作起点：再用拾取探针在附近找出真正命中器物的像素点
    const hitPoint = proj?.inView ? await findHit(def.id, proj.x, proj.y) : null;
    record.hitPoint = hitPoint;
    if (!proj?.inView || !hitPoint || !(await canvasOnly(hitPoint.x, hitPoint.y))) {
      record.activate = false;
      record.note = 'projection-not-clickable';
      await shot(`asset-${def.id.replace('DIY_', '')}`);
      results.push(record);
      fs.writeFileSync(OUT, JSON.stringify({ results, errors }, null, 1));
      continue;
    }

    // 先把鼠标挪到空白处清掉上一件的悬停残影
    await cdp.moveTo(970, 130);
    await sleep(220);
    await cdp.moveTo(hitPoint.x, hitPoint.y);
    await sleep(420);
    record.hover = await hoverHint();
    await shot(`${def.id.replace('DIY_', '')}-before`);
    await clickAt(hitPoint.x, hitPoint.y, 950);
    record.afterClick = (await items()).find((i) => i.key === placed.key)?.state ?? null;
    await sleep(650);
    await shot(`asset-${def.id.replace('DIY_', '')}`);

    if (def.kind === 'info') {
      record.card = await ev(`(() => { const el=[...document.querySelectorAll('h3')].find(h=>h.textContent.includes('展签架')); return el?el.textContent.trim():null; })()`);
      record.closed = await ev(`(() => { const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='关闭'); if(b){b.click(); return 'closed-by-button';} return null; })()`);
      await sleep(500);
      record.cardAfter = await ev(`(() => { const el=[...document.querySelectorAll('h3')].find(h=>h.textContent.includes('展签架')); return el?el.textContent.trim():null; })()`);
      await shot(`asset-${def.id.replace('DIY_', '')}-reset`);
    } else {
      if (await canvasOnly(hitPoint.x, hitPoint.y)) {
        await clickAt(hitPoint.x, hitPoint.y, 950);
        record.afterReset = (await items()).find((i) => i.key === placed.key)?.state ?? null;
        await shot(`asset-${def.id.replace('DIY_', '')}-reset`);
      }
    }
    record.activate = true;
  } catch (error) {
    record.activate = false;
    record.note = `error: ${String(error.message).slice(0, 120)}`;
    await revive('item-error');
  }
  results.push(record);
  fs.writeFileSync(OUT, JSON.stringify({ results, errors }, null, 1));
  console.log(JSON.stringify({ id: record.id, placed: !!record.placed, hover: record.hover, afterClick: record.afterClick, afterReset: record.afterReset, card: record.card, note: record.note }));
}

console.log('DONE', JSON.stringify(results.map((r) => ({
  id: r.id,
  y: r.placed?.y,
  surface: r.placed?.surface,
  parent: !!r.placed?.parent,
  hover: r.hover,
  click: r.afterClick,
  reset: r.afterReset,
  card: r.card,
  cardAfter: r.cardAfter,
  note: r.note,
}))));
fs.writeFileSync(OUT, JSON.stringify({ results, errors }, null, 1));
cdp.close();