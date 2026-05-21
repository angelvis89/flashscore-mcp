from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(locale="es-PE", timezone_id="America/Lima")
        await page.goto("https://www.flashscore.pe/", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(3000)
        date_button = page.locator("[data-testid='wcl-dayPickerButton']")
        print("before", await date_button.first.inner_text())
        print("rows before", await page.locator(".event__match").count())
        previous = page.get_by_label("Día anterior")
        print("previous count", await previous.count())
        await previous.first.click(timeout=3000)
        await page.wait_for_timeout(3000)
        print("after prev", await date_button.first.inner_text())
        print("rows prev", await page.locator(".event__match").count())
        next_button = page.get_by_label("Día siguiente")
        print("next count", await next_button.count())
        await next_button.first.click(timeout=3000)
        await page.wait_for_timeout(3000)
        print("after next", await date_button.first.inner_text())
        print("rows next", await page.locator(".event__match").count())
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
