import fs from "node:fs";
const PORT = process.env.CDP_PORT || "64366";
const t = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = t.find(x => x.type === "page");
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0; const pend = new Map(); const errors = [];
ws.addEventListener("message", e => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
  if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails?.exception?.description?.split("\n")[0]);
});
await new Promise((r, j) => { ws.addEventListener("open", r, { once: true }); ws.addEventListener("error", j, { once: true }); });
const send = (method, params = {}) => new Promise(res => { id += 1; pend.set(id, res); ws.send(JSON.stringify({ id, method, params })); });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ev = async e => (await send("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true })).result?.result?.value;
const shot = async name => { const r = await send("Page.captureScreenshot", { format: "png" }); fs.writeFileSync(`D:\\wenmai-huazhang\\docs\\heritage_gallery\\screens\\${name}.png`, Buffer.from(r.result.data, "base64")); };
const clickAt = async (x, y) => {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y, button: "none" });
  await sleep(120);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
  await sleep(400);
};
await send("Page.enable"); await send("Runtime.enable");
// 选“莲花暖光立灯”卡片
const picked = await ev(`(() => { const p=document.querySelector('[aria-label="器物图库"]'); if(!p) return false; const b=[...p.querySelectorAll('button')].find(x=>x.textContent.includes('莲花暖光立灯')); if(b){ b.click(); return true; } return false; })()`);
await sleep(800);
await shot("v15-02-pending-lamp");
// 在门前空地落位
await clickAt(640, 700);
await sleep(700);
await shot("v15-03-lamp-placed");
const after = await ev(`(() => JSON.parse(localStorage.getItem('wenmai-gallery-diy-v1')||'{}').state || {})()`);
// 再点一次落位的器物（应该在原地触发互动）
await clickAt(640, 700);
await sleep(1200);
await shot("v15-04-lamp-on");
console.log(JSON.stringify({ picked, items: (after.items||[]).length, last: (after.items||[]).slice(-1), errors: errors.slice(0,5) }));
ws.close();
