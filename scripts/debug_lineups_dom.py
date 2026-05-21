from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright

URL = "https://www.flashscore.pe/partido/futbol/paderborn-G2Op923t/wolfsburgo-nwkTahLL/?mid=K8bh3OkJ"


async def main() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(locale="es-PE")
        page = await context.new_page()
        await page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2500)
        # Listar pestañas visibles del header del detalle
        tabs = await page.evaluate(
            """
            () => Array.from(document.querySelectorAll("a, button"))
                .map(el => (el.innerText || '').trim())
                .filter(t => t && t.length < 25 && /[A-Z]{4,}/.test(t))
                .slice(0, 40)
            """
        )
        print("TABS visibles:")
        for t in tabs:
            print(" -", t)

        # Click ALINEACIONES y verificar
        for label in ("ALINEACIONES", "Alineaciones", "ALINEACIONES INICIALES"):
            loc = page.get_by_text(label, exact=True)
            count = await loc.count()
            print(f"locator '{label}': count={count}")

        try:
            await page.get_by_text("ALINEACIONES", exact=True).first.click(timeout=3000)
            print("CLICK ALINEACIONES ok")
        except Exception as e:
            print("CLICK fallo:", e)
        await page.wait_for_timeout(3000)
        info = await page.evaluate(
            """
            () => ({
              url: location.href,
              hasLineUp: !!document.querySelector('.lf__lineUp'),
              lineUpClasses: Array.from(document.querySelectorAll("[class*='lineUp'], [class*='lineup'], [class*='Lineup'], [class*='LineUp']")).slice(0,15).map(e=>e.className),
              participants: document.querySelectorAll("[data-testid^='wcl-lineupsParticipantGeneral']").length,
              testIdsSample: Array.from(document.querySelectorAll('[data-testid]')).slice(0,30).map(e=>e.getAttribute('data-testid')),
            })
            """
        )
        print("INFO:", info)
        body_text = await page.locator("body").inner_text(timeout=5000)
        for keyword in ("ALINEACIONES INICIALES", "SUPLENTES", "JUGADORES AUSENTES", "SISTEMA DE JUEGO"):
            print(f"  '{keyword}' in body: {keyword in body_text.upper()}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
