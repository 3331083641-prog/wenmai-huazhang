import os
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = r"D:\wenmai-huazhang\docs\screenshots\vnext"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def verify_about():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        print("Navigating to http://127.0.0.1:5173/about ...")
        page.goto("http://127.0.0.1:5173/about", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # 检查控制台报错
        if console_errors:
            print("Console Errors Detected:")
            for err in console_errors:
                print("  ", err)
        else:
            print("No console errors detected on initial load.")

        # 检查主焦点卡片是否存在
        hero_title = page.locator("h3:has-text('Qwen Image 3.0 可控智能生成')")
        if hero_title.is_visible():
            print("Verified: Card 01 (Qwen Image 3.0) is visible and expanded as default Hero.")
        else:
            print("Warning: Card 01 hero title not found.")

        # 截图 1: 默认 Card 01 展开态 (主展示区)
        matrix_sec = page.locator("#capabilities")
        matrix_sec.scroll_into_view_if_needed()
        page.wait_for_timeout(600)
        card1_path = os.path.join(SCREENSHOT_DIR, "about-card-01.jpg")
        matrix_sec.screenshot(path=card1_path, quality=90)
        print(f"Captured: {card1_path}")

        # 互动测试 1: 点击 Card 04 (画中有话 · 一图一境 · 画境漫游)
        print("Clicking Card 04 (画中有话 · 一图一境 · 画境漫游)...")
        card4_btn = page.locator("div[role='button']:has-text('04 · 互动赏析')")
        card4_btn.click()
        page.wait_for_timeout(800)

        hero_card4 = page.locator("h3:has-text('画中有话 · 一图一境 · 画境漫游')")
        if hero_card4.is_visible():
            print("Verified: Card 04 successfully expanded to Hero showcase!")
        card4_path = os.path.join(SCREENSHOT_DIR, "about-card-04.jpg")
        matrix_sec.screenshot(path=card4_path, quality=90)
        print(f"Captured: {card4_path}")

        # 互动测试 2: 点击 Card 05 (纹脉展馆与 DIY 沉浸式布展)
        print("Clicking Card 05 (纹脉展馆与 DIY 沉浸式布展)...")
        card5_btn = page.locator("div[role='button']:has-text('05 · 空间展陈')")
        card5_btn.click()
        page.wait_for_timeout(800)

        hero_card5 = page.locator("h3:has-text('纹脉展馆与 DIY 沉浸式布展')")
        if hero_card5.is_visible():
            print("Verified: Card 05 successfully expanded to Hero showcase!")
        card5_path = os.path.join(SCREENSHOT_DIR, "about-card-05.jpg")
        matrix_sec.screenshot(path=card5_path, quality=90)
        print(f"Captured: {card5_path}")

        # 互动测试 3: 点击 Card 02 (Qwen3-VL 视觉理解与文化卡)
        print("Clicking Card 02 (Qwen3-VL 视觉理解与文化卡)...")
        card2_btn = page.locator("div[role='button']:has-text('02 · 视觉理解')")
        card2_btn.click()
        page.wait_for_timeout(800)

        hero_card2 = page.locator("h3:has-text('Qwen3-VL 视觉理解与文化卡')")
        if hero_card2.is_visible():
            print("Verified: Card 02 successfully expanded to Hero showcase!")
        card2_path = os.path.join(SCREENSHOT_DIR, "about-card-02.jpg")
        matrix_sec.screenshot(path=card2_path, quality=90)
        print(f"Captured: {card2_path}")

        # 切换回 Card 01
        print("Switching back to Card 01 via top pill...")
        pill1 = page.locator("button:has-text('智能视觉生成')")
        pill1.click()
        page.wait_for_timeout(800)

        # 检查五大风格切换
        print("Testing Cultural Styles switcher...")
        page.locator("button:has-text('宋画青绿山水')").click()
        page.wait_for_timeout(500)
        songhua_title = page.locator("h3:has-text('宋画青绿山水')")
        if songhua_title.is_visible():
            print("Verified: Style switched to 宋画青绿山水.")

        # 检查技术架构 Tab 切换
        print("Testing Architecture layer switcher...")
        page.locator("button:has-text('后端服务与任务流水线')").click()
        page.wait_for_timeout(500)
        backend_title = page.locator("h3:has-text('后端服务与任务流水线')")
        if backend_title.is_visible():
            print("Verified: Architecture switched to 后端服务与任务流水线.")

        # 全页截图
        full_path = os.path.join(SCREENSHOT_DIR, "about.jpg")
        page.screenshot(path=full_path, full_page=True, quality=85)
        print(f"Captured Full Page: {full_path}")

        # 移动端适配验证
        print("Verifying mobile layout (390x844)...")
        mobile_context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        mobile_page = mobile_context.new_page()
        mobile_page.goto("http://127.0.0.1:5173/about", wait_until="networkidle")
        mobile_page.wait_for_timeout(1000)
        mobile_path = os.path.join(SCREENSHOT_DIR, "about-mobile.jpg")
        mobile_page.screenshot(path=mobile_path, full_page=True, quality=85)
        print(f"Captured Mobile Full Page: {mobile_path}")

        browser.close()
        print("All verification steps completed successfully!")

if __name__ == "__main__":
    verify_about()
