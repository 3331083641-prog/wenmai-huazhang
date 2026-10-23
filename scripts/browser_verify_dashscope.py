from __future__ import annotations

import base64
import json
import subprocess
import time
from pathlib import Path

import requests
import websocket

ROOT = Path(r"D:\wenmai-huazhang")
SCREEN = ROOT / "outputs" / "screenshots"
LOG = ROOT / "logs" / "browser_dashscope_verify.log"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
PORT = 9223
BASE = "http://localhost:5173"


def write(line: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


class CDP:
    def __init__(self, ws_url: str) -> None:
        self.ws = websocket.create_connection(ws_url, timeout=30)
        self.next_id = 1
        self.events = []

    def call(self, method: str, params: dict | None = None) -> dict:
        msg = {"id": self.next_id, "method": method, "params": params or {}}
        self.next_id += 1
        self.ws.send(json.dumps(msg))
        while True:
            raw = self.ws.recv()
            data = json.loads(raw)
            if "method" in data:
                self.events.append(data)
            if data.get("id") == msg["id"]:
                if "error" in data:
                    raise RuntimeError(data["error"])
                return data.get("result", {})

    def eval(self, expression: str, await_promise: bool = False) -> object:
        result = self.call("Runtime.evaluate", {
            "expression": expression,
            "awaitPromise": await_promise,
            "returnByValue": True,
        })
        return result.get("result", {}).get("value")

    def screenshot(self, name: str, full: bool = True) -> None:
        SCREEN.mkdir(parents=True, exist_ok=True)
        if full:
            metrics = self.call("Page.getLayoutMetrics")
            content = metrics.get("contentSize", {})
            clip = {
                "x": 0,
                "y": 0,
                "width": max(1, content.get("width", 1440)),
                "height": max(1, content.get("height", 1000)),
                "scale": 1,
            }
            data = self.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True, "clip": clip})["data"]
        else:
            data = self.call("Page.captureScreenshot", {"format": "png"})["data"]
        (SCREEN / name).write_bytes(base64.b64decode(data))
        write(f"screenshot={SCREEN / name}")

    def close(self) -> None:
        self.ws.close()


def wait_for_page(cdp: CDP, timeout: int = 30) -> None:
    end = time.time() + timeout
    while time.time() < end:
        state = cdp.eval("document.readyState")
        if state == "complete":
            return
        time.sleep(0.5)


def wait_until(cdp: CDP, expr: str, timeout: int, interval: float = 1.0) -> object:
    end = time.time() + timeout
    last = None
    while time.time() < end:
        last = cdp.eval(expr)
        if last:
            return last
        time.sleep(interval)
    return last


def main() -> int:
    SCREEN.mkdir(parents=True, exist_ok=True)
    profile = ROOT / ".cache" / "edge-cdp-profile"
    profile.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen([
        str(EDGE),
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--remote-debugging-port=" + str(PORT),
        "--remote-allow-origins=*",
        "--window-size=1440,1000",
        "--user-data-dir=" + str(profile),
        BASE,
    ])
    try:
        for _ in range(30):
            try:
                requests.get(f"http://127.0.0.1:{PORT}/json/version", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        tab = requests.put(f"http://127.0.0.1:{PORT}/json/new?{BASE}", timeout=5).json()
        cdp = CDP(tab["webSocketDebuggerUrl"])
        try:
            cdp.call("Page.enable")
            cdp.call("Runtime.enable")
            cdp.call("Log.enable")
            cdp.call("Console.enable")
            wait_for_page(cdp)
            time.sleep(2)
            home_text = cdp.eval("document.body.innerText || ''") or ""
            home_root_len = cdp.eval("(document.getElementById('root')?.innerHTML || '').length")
            write(f"homeBodyTextLength={len(home_text)} homeRootHtmlLength={home_root_len}")
            cdp.screenshot("home.png", full=False)

            cdp.call("Page.navigate", {"url": BASE + "/creator"})
            wait_for_page(cdp)
            cdp.eval("localStorage.removeItem('wenmai_latest_result')")
            time.sleep(2)
            cdp.screenshot("ai_creator_before.png")

            fill_js = r'''
(() => {
  const setNative = (el, value) => {
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
    setter.call(el, value);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  };
  const textarea = document.querySelector('textarea');
  if (textarea) setNative(textarea, '开封古城墙与朱仙镇木版年画风格融合的非遗文旅海报');
  const selects = [...document.querySelectorAll('select')];
  if (selects[0]) { selects[0].value = 'portrait'; selects[0].dispatchEvent(new Event('change', { bubbles: true })); }
  if (selects[1]) { selects[1].value = 'poster'; selects[1].dispatchEvent(new Event('change', { bubbles: true })); }
  const range = document.querySelector('input[type="range"]');
  if (range) setNative(range, '65');
  const buttons = [...document.querySelectorAll('button')];
  const gen = buttons.find(b => /AI 开始渲染|开始渲染|生成/.test(b.textContent || ''));
  if (gen) { gen.click(); return true; }
  return false;
})()
'''
            clicked = cdp.eval(fill_js)
            write(f"generateClicked={clicked}")
            if not clicked:
                return 2
            result = wait_until(cdp, "(() => { const raw = localStorage.getItem('wenmai_latest_result'); if (!raw) return false; try { const r = JSON.parse(raw); return Boolean(r.createdAt && r.imageUrl && r.mode); } catch(e) { return false; } })()", 360, 2)
            write(f"localStorageResult={result}")
            time.sleep(3)
            cdp.eval("window.scrollTo(0, 0)")
            time.sleep(1)
            cdp.screenshot("ai_creator_after_dashscope.png", full=False)
            cdp.eval("window.scrollTo(0, Math.max(0, document.body.scrollHeight * 0.35))")
            time.sleep(1)
            cdp.screenshot("culture_card.png", full=False)
            cdp.eval("window.scrollTo(0, Math.max(0, document.body.scrollHeight * 0.55))")
            time.sleep(1)
            cdp.screenshot("image_analysis.png", full=False)
            body_text = cdp.eval("document.body.innerText || ''") or ""
            root_len = cdp.eval("(document.getElementById('root')?.innerHTML || '').length")
            write(f"creatorBodyTextLength={len(body_text)} creatorRootHtmlLength={root_len}")
            write("runtimeEvents=" + json.dumps(cdp.events[-12:], ensure_ascii=False)[:3000])
            summary = cdp.eval("JSON.parse(localStorage.getItem('wenmai_latest_result') || '{}')")
            write("resultSummary=" + json.dumps({
                "mode": summary.get("mode"),
                "provider": summary.get("provider"),
                "imageUrl": summary.get("imageUrl"),
                "hasCultureCard": bool(summary.get("cultureCard")),
                "hasImageAnalysis": bool(summary.get("imageAnalysis")),
                "hasEnhancedPrompt": bool(summary.get("enhancedPrompt")),
                "hasRealProviderError": bool(summary.get("realProviderError")),
            }, ensure_ascii=False))

            cdp.call("Page.navigate", {"url": BASE + "/products"})
            wait_for_page(cdp)
            time.sleep(2)
            cdp.screenshot("product_studio.png")
            prod_text = cdp.eval("document.body.innerText") or ""
            write("productStudioHasRecent=" + str("当前图像来源" in prod_text or "最近一次生成" in prod_text))
            return 0
        finally:
            cdp.close()
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())