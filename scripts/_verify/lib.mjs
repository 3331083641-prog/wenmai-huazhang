// Minimal CDP harness for the wenmai gallery acceptance runs.
// Kept inside the project so D:\Codex cleanups can't remove it.
import fs from 'node:fs';

export const SCREENS = 'D:\\wenmai-huazhang\\docs\\heritage_gallery\\screens';

export async function connect(port = process.env.CDP_PORT || '58831') {
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const page = targets.find((t) => t.type === 'page' && /heritage-gallery/.test(t.url)) || targets.find((t) => t.type === 'page');
  if (!page) throw new Error('no page target');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0;
  const pend = new Map();
  const errors = [];
  const consoleErrors = [];
  ws.addEventListener('message', (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
    if (m.method === 'Runtime.exceptionThrown') {
      const d = m.params.exceptionDetails;
      errors.push(`${d.text || ''} ${d.exception?.description?.split('\n')[0] || ''}`.trim());
    }
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
      consoleErrors.push(m.params.args.map((a) => a.value ?? a.description ?? '').join(' ').slice(0, 300));
    }
  });
  await new Promise((res, rej) => {
    ws.addEventListener('open', res, { once: true });
    ws.addEventListener('error', rej, { once: true });
  });
  const send = (method, params = {}) => new Promise((res) => { id += 1; pend.set(id, res); ws.send(JSON.stringify({ id, method, params })); });
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const ev = async (expression) => {
    const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    if (r.result?.exceptionDetails) {
      const d = r.result.exceptionDetails;
      throw new Error(`eval: ${d.text} ${d.exception?.description?.split('\n')[0] || ''}`);
    }
    return r.result?.result?.value;
  };
  const shot = async (name, dir = SCREENS) => {
    fs.mkdirSync(dir, { recursive: true });
    const r = await send('Page.captureScreenshot', { format: 'png' });
    const p = `${dir}\\${name}.png`;
    fs.writeFileSync(p, Buffer.from(r.result.data, 'base64'));
    return p;
  };
  const moveTo = async (x, y) => {
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y, button: 'none' });
    await sleep(220);
  };
  const clickAt = async (x, y, settle = 420) => {
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y, button: 'none' });
    await sleep(90);
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', buttons: 1, clickCount: 1 });
    await sleep(40);
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', buttons: 0, clickCount: 1 });
    await sleep(settle);
  };
  const reload = async (waitMs = 9000) => {
    await send('Page.enable');
    await send('Page.navigate', { url: 'http://localhost:5173/heritage-gallery' });
    await sleep(waitMs);
  };
  await send('Page.enable');
  await send('Runtime.enable');
  return { ws, send, ev, shot, moveTo, clickAt, reload, sleep, errors, consoleErrors, close: () => ws.close() };
}

export const openDiyPanel = `(() => {
  const b = [...document.querySelectorAll('button')].find((x) => (x.textContent || '').trim().startsWith('器物'));
  if (!b) return 'no-panel-button';
  b.click();
  return 'ok';
})()`;