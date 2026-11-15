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
        # Block external fonts to avoid hanging network, leveraging system Noto/Songti/Yahei
        page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
        page.route("https://fonts.gstatic.com/**", lambda route: route.abort())

        # 1. 首页 Home Overview
        print("Capturing home-overview.jpg...")
        page.goto(f"{BASE_URL}/", wait_until='domcontentloaded')
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT_DIR / 'home-overview.jpg'), quality=90, timeout=10000, animations='disabled')

        # 2. 首页展馆区域 home-gallery.jpg
        print("Capturing home-gallery.jpg...")
        page.evaluate('window.scrollTo(0, 1050)')
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT_DIR / 'home-gallery.jpg'), quality=90, timeout=10000, animations='disabled')

        # 3. 风格库 StyleLibrary
        print("Capturing culture-styles.jpg...")
        page.goto(f"{BASE_URL}/styles", wait_until='domcontentloaded')
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT_DIR / 'culture-styles.jpg'), quality=90, timeout=10000, animations='disabled')

        # 3b. 风格文化基因考据弹窗 style-inspect-modal.jpg
        print("Capturing style-inspect-modal.jpg...")
        try:
            inspect_btn = page.locator('button:has-text("考据")').first
            if inspect_btn.is_visible():
                inspect_btn.click(force=True)
                page.wait_for_timeout(600)
                page.screenshot(path=str(OUT_DIR / 'style-inspect-modal.jpg'), quality=90, timeout=10000, animations='disabled')
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
        except Exception as e:
            print(f"Warning capturing style modal: {e}")

        # 4. 智能生成工作台 AICreator
        print("Capturing creation-workspace.jpg...")
        page.goto(f"{BASE_URL}/creator", wait_until='domcontentloaded')
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT_DIR / 'creation-workspace.jpg'), quality=90, timeout=10000, animations='disabled')

        # 5. 作品展厅 Gallery
        print("Capturing gallery.jpg...")
        page.goto(f"{BASE_URL}/gallery", wait_until='domcontentloaded')
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT_DIR / 'gallery.jpg'), quality=90, timeout=10000, animations='disabled')

        # 5b. 作品展厅印匣展开弹窗 gallery-archive-modal.jpg
        print("Capturing gallery-archive-modal.jpg...")
        try:
            # Click the archive casket
            casket_el = page.locator('img[alt*="古籍卷轴式立体书香金石印匣"]').first
            if casket_el.is_visible():
                casket_el.click(force=True)
                page.wait_for_timeout(600)
                page.screenshot(path=str(OUT_DIR / 'gallery-archive-modal.jpg'), quality=90, timeout=10000, animations='disabled')
                # Close the modal
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
        except Exception as e:
            print(f"Warning capturing gallery modal: {e}")

        # 6. 文创转化工坊 ProductStudio
        print("Capturing creative-products.jpg...")
        page.goto(f"{BASE_URL}/products", wait_until='domcontentloaded')
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT_DIR / 'creative-products.jpg'), quality=90, timeout=10000, animations='disabled')

        # 6b. 文创转化青瓷贯耳尊展开说明弹窗 product-vessel-modal.jpg
        print("Capturing product-vessel-modal.jpg...")
        try:
            vessel_el = page.locator('img[alt*="天青贯耳尊"]').first
            if vessel_el.is_visible():
                vessel_el.click(force=True)
                page.wait_for_timeout(600)
                page.screenshot(path=str(OUT_DIR / 'product-vessel-modal.jpg'), quality=90, timeout=10000, animations='disabled')
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
        except Exception as e:
            print(f"Warning capturing vessel modal: {e}")

        # 7. 应用场景 Scenarios
        print("Capturing scenarios.jpg...")
        page.goto(f"{BASE_URL}/scenarios", wait_until='domcontentloaded')
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT_DIR / 'scenarios.jpg'), quality=90, timeout=10000, animations='disabled')

        # 8. 关于项目 About
        print("Capturing about.jpg...")
        page.goto(f"{BASE_URL}/about", wait_until='domcontentloaded')
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT_DIR / 'about.jpg'), quality=90, timeout=10000, animations='disabled')

        # 9. 移动端 390px 视口 mobile-home.jpg
        print("Capturing mobile-home.jpg (390px)...")
        mobile_context = browser.new_context(
            viewport={'width': 390, 'height': 844},
            device_scale_factor=2,
            is_mobile=True,
        )
        mobile_page = mobile_context.new_page()
        mobile_page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
        mobile_page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
        mobile_page.goto(f"{BASE_URL}/", wait_until='domcontentloaded')
        mobile_page.wait_for_timeout(1200)
        mobile_page.screenshot(path=str(OUT_DIR / 'mobile-home.jpg'), quality=90, timeout=10000, animations='disabled')

        browser.close()
        print("All authentic screenshots successfully captured and updated!")

if __name__ == '__main__':
    run()
