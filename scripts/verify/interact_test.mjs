import fs from "node:fs";
const PORT = process.env.CDP_PORT || "64366";
const t = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = t.find(x => x.type === "page");
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0; const pend = new Map(); const errors = [];
ws.addEventListener("message", e => { const m = JSON.parse(e.data); if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
  if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails?.exception?.description?.split("\n")[0]); });
await new Promise((r, j) => { ws.addEventListener("open", r, { once: true }); ws.addEventListener("error", j, { once: true }); });
const send = (method, params = {}) => new Promise(res => { id += 1; pend.set(id, res); ws.send(JSON.stringify({ id, method, params })); });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ev = async e => (await send("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true })).result?.result?.value;
const shot = async name => { const r = await send("Page.captureScreenshot", { format: "png" }); fs.writeFileSync(`D:\\wenmai-huazhang\\docs\\heritage_gallery\\screens\\${name}.png`, Buffer.from(r.result.data, "base64")); };
await send("Page.enable"); await send("Runtime.enable");
await send("Page.navigate", { url: "http://localhost:5173/heritage-gallery" });
await sleep(14000);
// 找到已摆放的莲花灯在屏幕上的位置
let hit = null;
outer:
for (let y = 420; y <= 760 && !hit; y += 14) {
  for (let x = 620; x <= 1000; x += 14) {
    const names = await ev(`(window.__galleryPick(${x},${y})||[]).map(h=>h.names[0]).join('|')`);
    if (names && names.includes("DIY_A05")) { hit = [x, y]; break outer; }
  }
}
if (!hit) { console.log(JSON.stringify({ error: "lamp not found on screen", errors: errors.slice(0,3) })); ws.close(); process.exit(0); }
await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: hit[0], y: hit[1], button: "none" });
await sleep(400);
await shot("v15-05-lamp-hover");
await send("Input.dispatchMouseEvent", { type: "mousePressed", x: hit[0], y: hit[1], button: "left", clickCount: 1 });
await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: hit[0], y: hit[1], button: "left", clickCount: 1 });
await sleep(1500);
await shot("v15-06-lamp-lit");
const state = await ev(`(() => { const s=JSON.parse(localStorage.getItem('wenmai-gallery-diy-v1')||'{}').state||{}; return (s.items||[]).map(i=>({p:i.propId, st:i.interactionState})); })()`);
console.log(JSON.stringify({ hit, state, errors: errors.slice(0,3) }));
ws.close();
