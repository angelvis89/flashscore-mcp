from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(locale="es-PE", timezone_id="America/Lima")
        page = await context.new_page()
        await page.goto("https://www.flashscore.pe/", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(5000)
        print("title=", await page.title())
        for selector in [
            "[id^='g_']",
            ".event__match",
            "[class*='event']",
            "[class*='participant']",
            "[class*='score']",
            "[class*='match']",
            "main",
            "body",
        ]:
            try:
                count = await page.locator(selector).count()
                print(f"{selector}={count}")
            except Exception as exc:
                print(f"{selector}=ERROR {exc}")
        body = await page.locator("body").inner_text(timeout=5000)
        print("body_sample=", body[:2000].replace("\n", " | "))
        first = page.locator(".event__match").first
        print("first_class=", await first.get_attribute("class"))
        print("first_text=", (await first.inner_text()).replace("\n", " | "))
        print("first_html=", (await first.evaluate("el => el.outerHTML"))[:1500])
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
