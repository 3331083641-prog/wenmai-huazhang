"""
Capture authentic, high-definition screenshots of Wenmai Huazhang VNext UI
using Playwright against the live local development server at http://127.0.0.1:5173.
"""
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'docs' / 'screenshots' / 'current'
OUT_DIR.mkdir(parents=True, exist_ok=True)

EDGE_PATH = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
BASE_URL = 'http://127.0.0.1:5173'

def run():
    print(f"Connecting to live server at {BASE_URL}...")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=EDGE_PATH,
            headless=True,
            args=[
                '--no-proxy-server',
                '--disable-gpu',
                '--no-first-run',
                '--disable-sync',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
            ]
        )
        context = browser.new_context(
            viewport={'width': 1440, 'height': 1000},
            device_scale_factor=1,
        )
        page = context.new_page()
        page.set_default_timeout(30000)

        # 1. 首页 Home
        print("Capturing home-overview.jpg...")
        page.goto(f"{BASE_URL}/", wait_until='domcontentloaded')
        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUT_DIR / 'home-overview.jpg'), quality=90)

        # 2. 首页展馆区域 home-gallery.jpg
        print("Capturing home-gallery.jpg...")
        page.evaluate('window.scrollTo(0, 1150)')
        page.wait_for_timeout(1000)
        page.screenshot(path=str(OUT_DIR / 'home-gallery.jpg'), quality=90)

        # 3. 风格库 StyleLibrary
        print("Capturing culture-styles.jpg...")
        page.goto(f"{BASE_URL}/styles", wait_until='domcontentloaded')
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT_DIR / 'culture-styles.jpg'), quality=90)

        # 4. 智能生成工作台 AICreator
        print("Capturing creation-workspace.jpg...")
        page.goto(f"{BASE_URL}/creator", wait_until='domcontentloaded')
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT_DIR / 'creation-workspace.jpg'), quality=90)

        # 5. 作品展厅 Gallery
        print("Capturing gallery.jpg...")
        page.goto(f"{BASE_URL}/gallery", wait_until='domcontentloaded')
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT_DIR / 'gallery.jpg'), quality=90)

        # 6. 文创衍生效果工坊 ProductStudio
        print("Capturing creative-products.jpg...")
        page.goto(f"{BASE_URL}/products", wait_until='domcontentloaded')
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT_DIR / 'creative-products.jpg'), quality=90)

        # 7. 多维应用场景 Scenarios
        print("Capturing scenarios.jpg...")
        page.goto(f"{BASE_URL}/scenarios", wait_until='domcontentloaded')
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT_DIR / 'scenarios.jpg'), quality=90)

        # 8. 关于项目 About
        print("Capturing about.jpg...")
        page.goto(f"{BASE_URL}/about", wait_until='domcontentloaded')
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT_DIR / 'about.jpg'), quality=90)

        browser.close()
        print("All target screenshots captured successfully!")

if __name__ == '__main__':
    run()
