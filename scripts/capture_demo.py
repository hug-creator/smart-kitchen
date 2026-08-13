"""智能餐厅演示 GIF 截图脚本。

用 Playwright（系统 Edge 浏览器）自动操作页面，截取关键步骤。
"""

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT_DIR = Path(r"D:\219\smart-kitchen\docs\demo_shots")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # 1. 首页（实时下单）
        page.goto("http://127.0.0.1:5000")
        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUT_DIR / "01_home.png"))

        # 2. 点餐
        page.fill("#order-input", "来一份番茄炒蛋")
        page.screenshot(path=str(OUT_DIR / "02_input.png"))
        page.click("#order-btn")
        # 等 LLM 处理完成（接单+库存+烹饪+质检约 5-8 秒）
        page.wait_for_timeout(9000)
        page.screenshot(path=str(OUT_DIR / "03_result.png"))

        # 3. 库存管理
        page.click('li[data-tab="inventory"]')
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT_DIR / "04_inventory.png"))

        # 4. 订单历史
        page.click('li[data-tab="history"]')
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT_DIR / "05_history.png"))

        # 5. 系统监控
        page.click('li[data-tab="monitor"]')
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT_DIR / "06_monitor.png"))

        browser.close()

    print("截图完成：", [f.name for f in sorted(OUT_DIR.glob("*.png"))])


if __name__ == "__main__":
    main()
