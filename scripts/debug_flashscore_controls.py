from __future__ import annotations

import asyncio
import json

from playwright.async_api import async_playwright


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(locale="es-PE", timezone_id="America/Lima")
        await page.goto("https://www.flashscore.pe/", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(4000)
        data = await page.evaluate(
            """
            () => Array.from(document.querySelectorAll("button, [role=button], a"))
              .map((e) => ({
                tag: e.tagName,
                text: e.innerText,
                aria: e.getAttribute("aria-label"),
                cls: String(e.className),
                test: e.getAttribute("data-testid")
              }))
              .filter((x) => (x.text || x.aria || x.test || "").match(
                /ayer|mañana|anterior|siguiente|calendar|fecha|21\\/05|directo|finalizados|próximos/i
              ))
              .slice(0, 80)
            """
        )
        print(json.dumps(data, ensure_ascii=False, indent=2))
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
