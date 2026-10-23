import fs from "node:fs";
const PORT = process.env.CDP_PORT || "50315";
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
const clickAt = async (x, y) => { await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y, button: "none" }); await sleep(100);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 }); await sleep(500); };
await send("Page.enable"); await send("Runtime.enable");
await send("Page.navigate", { url: "http://localhost:5173/heritage-gallery" });
await sleep(14000);
await ev(`(() => { const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim().startsWith('器物')); b && b.click(); return 1; })()`);
await sleep(1200);
const picked = await ev(`(() => { const p=document.querySelector('[aria-label="器物图库"]'); const b=[...p.querySelectorAll('button')].find(x=>x.textContent.includes('宋式铜座文化展签架')); b && b.click(); return !!b; })()`);
await sleep(600);
await clickAt(560, 700);
await sleep(1000);
await shot("v16-01-a09-placed");
let hit = null;
outer:
for (let y = 500; y <= 780; y += 12) for (let x = 480; x <= 720; x += 12) {
  const names = await ev(`(window.__galleryPick(${x},${y})||[]).map(h=>h.names[0]).join('|')`);
  if (names && names.includes("DIY_A09")) { hit = [x, y]; break outer; }
}
if (hit) { await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: hit[0], y: hit[1], button: "none" }); await sleep(500); await shot("v16-02-a09-hover"); await clickAt(hit[0], hit[1]); await sleep(900); await shot("v16-03-a09-card"); }
const card = await ev(`(() => { const el=[...document.querySelectorAll('h3')].find(h=>h.textContent.includes('展签架')); return el ? el.textContent : null; })()`);
console.log(JSON.stringify({ picked, hit, card, hint: await ev(`(() => { const el=[...document.querySelectorAll('div')].find(d=>d.textContent.trim().startsWith('点击互动')); return el ? el.textContent.trim().slice(0,24) : null; })()`), errs: errs.slice(0,3) }));
ws.close();
