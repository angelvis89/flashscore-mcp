from __future__ import annotations

import asyncio
import sys

from playwright.async_api import async_playwright


async def main() -> None:
    match_id = sys.argv[1] if len(sys.argv) > 1 else "K8bh3OkJ"
    url = f"https://www.flashscore.pe/partido/{match_id}/#/resumen-del-partido"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(locale="es-PE", timezone_id="America/Lima")
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(5000)
        print("url=", page.url)
        print("title=", await page.title())
        for selector in [
            ".duelParticipant",
            ".detailScore__wrapper",
            ".smv__verticalSections",
            ".tabs__tab",
            "[class*='stat']",
            "[class*='odds']",
            "[class*='lineup']",
            "[class*='h2h']",
            "[class*='incident']",
        ]:
            try:
                print(selector, await page.locator(selector).count())
            except Exception as exc:
                print(selector, "ERROR", exc)
        body = (await page.locator("body").inner_text(timeout=5000)).replace("\n", " | ")
        print("body=", body[:3000])
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
