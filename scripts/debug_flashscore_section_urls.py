from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright

URLS = {
    "summary": "https://www.flashscore.pe/partido/futbol/paderborn-G2Op923t/wolfsburgo-nwkTahLL/",
    "lineups": "https://www.flashscore.pe/partido/futbol/paderborn-G2Op923t/wolfsburgo-nwkTahLL/resumen/alineaciones/?mid=K8bh3OkJ",
    "odds_1x2": "https://www.flashscore.pe/partido/futbol/paderborn-G2Op923t/wolfsburgo-nwkTahLL/cuotas/cuotas-1x2/partido/?mid=K8bh3OkJ",
    "h2h": "https://www.flashscore.pe/partido/futbol/paderborn-G2Op923t/wolfsburgo-nwkTahLL/h2h/general/?mid=K8bh3OkJ",
    "over_under": "https://www.flashscore.pe/partido/futbol/paderborn-G2Op923t/wolfsburgo-nwkTahLL/cuotas/mas-de-menos-de/partido/?mid=K8bh3OkJ",
}


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(locale="es-PE", timezone_id="America/Lima")
        for name, url in URLS.items():
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(2500)
            try:
                more = page.get_by_text("Mostrar previa íntegra", exact=False)
                if await more.count():
                    await more.first.click(timeout=2000)
                    await page.wait_for_timeout(1000)
            except Exception:
                pass
            body = (await page.locator("body").inner_text(timeout=8000)).replace("\n", " | ")
            print(f"\n===== {name} =====")
            print("url=", page.url)
            print("title=", await page.title())
            print("chars=", len(body))
            print(body[:3500])
            for selector in [
                "[class*='odds']",
                "[class*='ui-table']",
                "[class*='lf__']",
                "[class*='lineup']",
                "[class*='missing']",
                "[class*='h2h']",
                "[class*='section']",
            ]:
                try:
                    print(selector, await page.locator(selector).count())
                except Exception as exc:
                    print(selector, exc)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
