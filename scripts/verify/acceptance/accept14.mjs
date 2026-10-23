import fs from 'node:fs';
import { connect, openDiyPanel, SCREENS } from './lib.mjs';

const cdp = await connect();
await cdp.reload(12000);
cdp.errors.length = 0;
cdp.consoleErrors.length = 0;
await cdp.ev(`localStorage.removeItem('wenmai-gallery-diy-v1')`);
await cdp.reload(11000);
await cdp.ev(openDiyPanel);
await cdp.sleep(2800); // 等机位过渡到一层，镜头稳定后再落位

const heights = await cdp.ev(`(() => { const m={}; (window.__wenmaiAudit?window.__wenmaiAudit():[]).forEach(a=>{m[a.id]=a.size[1];}); return m; })()`);

const items = async () =>
  cdp.ev(`(() => { const s=JSON.parse(localStorage.getItem('wenmai-gallery-diy-v1')||'{}').state||{};
    return (s.items||[]).map(i=>({key:i.key,p:i.propId,x:+i.x.toFixed(2),y:+i.y.toFixed(3),z:+i.z.toFixed(2),
      parent:i.parentInstanceId||null,surface:i.surfaceId||null,state:i.interactionState||null})); })()`);
const clearItems = async () => {
  const done = await cdp.ev(`(() => { const p=document.querySelector('[aria-label="器物图库"]');
    const b=p && [...p.querySelectorAll('button')].find(x=>x.textContent.includes('清空器物')); if(b){b.click(); return true;} return false; })()`);
  await cdp.sleep(350);
  return done;
};
const pick = async (text) =>
  cdp.ev(`(() => { const p=document.querySelector('[aria-label="器物图库"]'); if(!p) return 'no-panel';
    const b=[...p.querySelectorAll('button')].find(x=>x.textContent.includes(${JSON.stringify(text)}));
    if(!b) return 'no-card'; b.click(); return 'ok'; })()`);
const canvasOnly = async (x, y) =>
  cdp.ev(`document.elementFromPoint(${x},${y})?.tagName === 'CANVAS'`);
const hint = async () =>
  cdp.ev(`(() => { const el=[...document.querySelectorAll('div')].find(d=>d.children.length===0 && /^点击互动/.test(d.textContent.trim())); return el?el.textContent.trim():null; })()`);

const FLOOR_POINT = [640, 680];

// 一层托梁上的可挂点（每轮重新探测，镜头停稳后位置才准）
const findBeamSpot = async () =>
  cdp.ev(`(() => {
    for (let y = 140; y <= 620; y += 20) for (let x = 160; x <= 980; x += 20) {
      if (document.elementFromPoint(x,y)?.tagName !== 'CANVAS') continue;
      const r = window.__galleryHang(x,y);
      if (r && /JOIST|BEAM/.test(r.carrier)) return { x, y };
    }
    return null;
  })()`);

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
  await clearItems();
  let placePoint = FLOOR_POINT;
  let carrierKey = null;

  if (def.kind === 'surface') {
    // 先摆一个博古架当承载物，再往它顶面放小件
    await pick('胡桃木博古架');
    await cdp.sleep(300);
    await cdp.clickAt(600, 690, 800);
    const shelf = (await items()).find((i) => i.p === 'DIY_A01');
    if (shelf) {
      carrierKey = shelf.key;
      const top = shelf.y + (heights.DIY_A01 ?? 1.845);
      const p = await cdp.ev(`window.__galleryProject(${shelf.x}, ${top}, ${shelf.z})`);
      if (p?.inView) placePoint = [p.x, p.y - 26];
    }
  } else if (def.kind === 'hang') {
    const spot = await findBeamSpot();
    if (spot) placePoint = [spot.x, spot.y];
  }

  await pick(def.name);
  await cdp.sleep(350);
  await cdp.clickAt(placePoint[0], placePoint[1], 850);

  const list = await items();
  const placed = [...list].reverse().find((i) => i.p === def.id) ?? null;
  const record = { id: def.id, name: def.name, placed, placePoint, carrierKey };

  if (!placed) {
    record.activate = false;
    record.note = 'placement-failed';
    results.push(record);
    await cdp.shot(`asset-${def.id.replace('DIY_', '')}`);
    continue;
  }

  // 悬停提示
  const cy = placed.y + (heights[def.id] ?? 0.6) * 0.45;
  const proj = await cdp.ev(`window.__galleryProject(${placed.x}, ${cy}, ${placed.z})`);
  record.projected = proj;
  if (proj?.inView && (await canvasOnly(proj.x, proj.y))) {
    await cdp.moveTo(proj.x, proj.y);
    await cdp.sleep(400);
    record.hover = await hint();
    await cdp.shot(`${def.id.replace('DIY_', '')}-before`);
    await cdp.clickAt(proj.x, proj.y, 900);
    const after = (await items()).find((i) => i.key === placed.key);
    record.afterClick = after?.state ?? null;
    await cdp.sleep(600);
    await cdp.shot(`asset-${def.id.replace('DIY_', '')}`);

    if (def.kind === 'info') {
      record.card = await cdp.ev(`(() => { const el=[...document.querySelectorAll('h3')].find(h=>h.textContent.includes('展签架')); return el?el.textContent.trim():null; })()`);
      // 再次点击 / 关闭按钮收起
      const closed = await cdp.ev(`(() => { const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='关闭'); if(b){b.click(); return 'closed-by-button';} return null; })()`);
      record.closed = closed;
      await cdp.sleep(500);
      record.cardAfter = await cdp.ev(`(() => { const el=[...document.querySelectorAll('h3')].find(h=>h.textContent.includes('展签架')); return el?el.textContent.trim():null; })()`);
      await cdp.shot(`asset-${def.id.replace('DIY_', '')}-reset`);
    } else {
      // 再点一次复位
      if (await canvasOnly(proj.x, proj.y)) {
        await cdp.clickAt(proj.x, proj.y, 900);
        const reset = (await items()).find((i) => i.key === placed.key);
        record.afterReset = reset?.state ?? null;
        await cdp.shot(`asset-${def.id.replace('DIY_', '')}-reset`);
      }
    }
    record.activate = true;
  } else {
    record.activate = false;
    record.note = 'projection-not-clickable';
    await cdp.shot(`asset-${def.id.replace('DIY_', '')}`);
  }
  results.push(record);
}

fs.writeFileSync('D:\\Codex\\wenmai-verify\\accept14.json', JSON.stringify({ results, errs: cdp.errors.slice(0, 8) }, null, 1));
console.log(JSON.stringify(results.map((r) => ({
  id: r.id, placed: r.placed && { y: r.placed.y, surface: r.placed.surface, parent: !!r.placed.parent },
  hover: r.hover, afterClick: r.afterClick, afterReset: r.afterReset, card: r.card, cardAfter: r.cardAfter, note: r.note,
})), null, 1));
console.log('errors:', JSON.stringify(cdp.errors.slice(0, 8)));
console.log('screens dir size:', fs.readdirSync(SCREENS).filter((f) => /^asset-/.test(f)).length);
cdp.close();