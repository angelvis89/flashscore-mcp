from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright


async def count_for(url: str) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(locale="es-PE", timezone_id="America/Lima")
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(4000)
        rows = await page.locator(".event__match").count()
        title = await page.title()
        body = (await page.locator("body").inner_text(timeout=5000)).replace("\n", " | ")
        print(f"url={url}")
        print(f"title={title}")
        print(f"rows={rows}")
        print(f"sample={body[:500]}")
        await browser.close()


async def main() -> None:
    for url in [
        "https://www.flashscore.pe/",
        "https://www.flashscore.pe/?d=2026-05-20",
        "https://www.flashscore.pe/?d=2026-05-21",
        "https://www.flashscore.pe/?d=2026-05-22",
    ]:
        await count_for(url)


if __name__ == "__main__":
    asyncio.run(main())
