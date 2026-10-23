import fs from "node:fs";
const PORT = process.env.CDP_PORT;
const t = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = t.find(x => x.type === "page");
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0; const pend = new Map(); const errs = [];
ws.addEventListener("message", e => { const m = JSON.parse(e.data); if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
  if (m.method === "Runtime.exceptionThrown") errs.push(m.params.exceptionDetails?.exception?.description?.split("\n")[0]); });
await new Promise((r, j) => { ws.addEventListener("open", r, { once: true }); ws.addEventListener("error", j, { once: true }); });
const send = (method, params = {}) => new Promise(res => { id += 1; pend.set(id, res); ws.send(JSON.stringify({ id, method, params })); });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ev = async e => (await send("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true })).result?.result?.value;
const shot = async name => { const r = await send("Page.captureScreenshot", { format: "png" }); fs.writeFileSync(`D:\\wenmai-huazhang\\docs\\heritage_gallery\\screens\\${name}.png`, Buffer.from(r.result.data, "base64")); };
const clickAt = async (x, y) => { await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y, button: "none" }); await sleep(120);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 }); await sleep(600); };
const pickCard = async (text) => ev(`(() => { const p=document.querySelector('[aria-label="器物图库"]'); if(!p) return false; const b=[...p.querySelectorAll('button')].find(x=>x.textContent.includes(${JSON.stringify(text)})); if(b){b.click(); return true;} return false; })()`);
await send("Page.enable"); await send("Runtime.enable");
await send("Page.navigate", { url: "http://localhost:5173/heritage-gallery" });
await sleep(14000);
await ev(`(() => { localStorage.removeItem('wenmai-gallery-diy-v1'); return 1; })()`);
await send("Page.navigate", { url: "http://localhost:5173/heritage-gallery" });
await sleep(13000);
await ev(`(() => { const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim().startsWith('器物')); b && b.click(); return 1; })()`);
await sleep(1200);
// 1) 摆博古架
await pickCard('胡桃木博古架'); await sleep(500);
await clickAt(600, 690); await sleep(900);
await shot("v17-01-bogujia");
// 找博古架的屏幕位置
let hit = null;
outer:
for (let y = 500; y <= 780; y += 12) for (let x = 470; x <= 760; x += 12) {
  const names = await ev(`(window.__galleryPick(${x},${y})||[]).map(h=>h.names[0]).join('|')`);
  if (names && names.includes("DIY_A01")) { hit = [x, y]; break outer; }
}
// 2) 往博古架顶面放梅瓶
if (hit) { await pickCard('青花瓷梅瓶'); await sleep(500); await clickAt(hit[0], hit[1] - 30); await sleep(900); }
await shot("v17-02-surface-vase");
const items = await ev(`(() => { const s=JSON.parse(localStorage.getItem('wenmai-gallery-diy-v1')||'{}').state||{}; return (s.items||[]).map(i=>({p:i.propId,y:+i.y.toFixed(3),parent:i.parentInstanceId||null,surface:i.surfaceId||null})); })()`);
console.log(JSON.stringify({ hit, items, errs: errs.slice(0,3) }));
ws.close();
