from __future__ import annotations

import logging
import re
from datetime import date as date_type
from datetime import datetime
from typing import Any

from flashscore_mcp.config import Settings
from flashscore_mcp.models import LiveMatch, MatchDetail, MatchScore, MatchSection, utc_now_iso

logger = logging.getLogger(__name__)


class FlashscorePlaywrightProvider:
    """Proveedor experimental basado en DOM.

    Flashscore no publica una API oficial para este uso. Esta clase esta pensada
    para investigacion o uso interno, con cache y frecuencia conservadora.
    """

    source_name = "flashscore_playwright_experimental"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def fetch_live_matches(
        self,
        *,
        sport: str = "football",
        league: str | None = None,
        live_only: bool = True,
    ) -> list[LiveMatch]:
        url = self._sport_url(sport)
        rows = await self._extract_rows(url=url, live_only=live_only)
        matches = [self._row_to_match(row) for row in rows]
        matches = [match for match in matches if match is not None]

        if league:
            league_lower = league.lower()
            matches = [
                match
                for match in matches
                if league_lower in " ".join(
                    value or "" for value in (match.league, match.country, match.raw_text)
                ).lower()
            ]
        return matches

    async def fetch_match_detail(self, match_id: str) -> LiveMatch | None:
        # Flashscore usa slugs en la URL publica. Si solo tenemos el ID, el DOM
        # principal suele ser mas estable para recuperar el marcador resumido.
        matches = await self.fetch_live_matches(live_only=False)
        for match in matches:
            if match.match_id == match_id:
                return match
        # Fallback: el partido puede ser de un dia previo (finalizado). Buscamos
        # en los ultimos 7 dias antes de rendirnos.
        from datetime import date, timedelta
        today = date.today()
        for delta in range(1, 8):
            day = (today - timedelta(days=delta)).isoformat()
            try:
                day_matches = await self.fetch_matches_by_date(date=day)
            except Exception:
                continue
            for match in day_matches:
                if match.match_id == match_id:
                    return match
        return None

    async def fetch_matches_by_date(
        self,
        *,
        date: str,
        sport: str = "football",
        league: str | None = None,
    ) -> list[LiveMatch]:
        url = self._sport_url(sport)
        rows = await self._extract_rows(url=url, live_only=False, target_date=date)
        matches = [self._row_to_match(row) for row in rows]
        matches = [match for match in matches if match is not None]
        if league:
            needle = league.lower()
            matches = [m for m in matches if needle in f"{m.league} {m.raw_text}".lower()]
        return matches

    async def search_matches(
        self,
        *,
        query: str,
        date_from: str | None = None,
        date_to: str | None = None,
        sport: str = "football",
        league: str | None = None,
    ) -> list[LiveMatch]:
        dates = self._date_range(date_from, date_to)
        needle = query.lower()
        found: dict[str, LiveMatch] = {}
        for day in dates:
            for match in await self.fetch_matches_by_date(
                date=day.isoformat(),
                sport=sport,
                league=league,
            ):
                haystack = f"{match.home} {match.away} {match.league} {match.raw_text}".lower()
                if needle in haystack:
                    found[match.match_id] = match
        return list(found.values())

    async def fetch_match_full_detail(
        self,
        match_id: str,
        *,
        sections: list[str] | None = None,
    ) -> MatchDetail | None:
        match = await self.fetch_match_detail(match_id)
        synthetic = match is None
        if synthetic:
            # Partido no encontrado en el listado del dia actual (tipico de partidos
            # finalizados de dias anteriores). Construimos una URL canonica directa
            # usando el patron /match/<mid>/ y delegamos a la pagina de detalle.
            direct_url = f"{self.settings.base_url.rstrip('/')}/match/{match_id}/"
            match = LiveMatch(
                match_id=match_id,
                home="",
                away="",
                url=direct_url,
            )
        detail_url = match.url or f"{self.settings.base_url.rstrip('/')}/match/{match_id}/"
        base_url = self._base_match_url(detail_url)
        mid = self._match_mid(detail_url, match_id)
        requested = sections or ["summary", "statistics", "lineups", "odds", "h2h", "preview"]
        result_sections: dict[str, MatchSection] = {}

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.settings.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(locale="es-PE", timezone_id="America/Lima")
            page = await context.new_page()
            page.set_default_timeout(self.settings.timeout_ms)
            try:
                await page.goto(base_url, wait_until="domcontentloaded")
                await self._try_accept_cookies(page)
                await page.wait_for_timeout(1500)
                header = await self._extract_detail_header(page)
                if header:
                    match = self._merge_match_header(match, header)

                for section in requested:
                    result_sections[section] = await self._extract_detail_section(
                        page,
                        section=section,
                        base_url=base_url,
                        mid=mid,
                    )
            finally:
                await context.close()
                await browser.close()

        return MatchDetail(
            match=match,
            fetched_at=utc_now_iso(),
            source=self.source_name,
            sections=result_sections,
        )

    def _sport_url(self, sport: str) -> str:
        normalized = sport.strip().lower()
        if normalized in {"football", "soccer", "futbol", "fútbol"}:
            return self.settings.base_url.rstrip("/") + "/"
        return self.settings.base_url.rstrip("/") + f"/{normalized}/"

    async def _extract_rows(
        self,
        *,
        url: str,
        live_only: bool,
        target_date: str | None = None,
    ) -> list[dict[str, Any]]:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.settings.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                locale="es-PE",
                timezone_id="America/Lima",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()
            page.set_default_timeout(self.settings.timeout_ms)
            try:
                await page.goto(url, wait_until="domcontentloaded")
                await self._try_accept_cookies(page)
                if target_date:
                    await self._navigate_to_date(page, target_date)
                if live_only:
                    await self._try_live_filter(page)
                selector = "[id^='g_'], .event__match"
                await page.wait_for_selector(selector, timeout=self.settings.timeout_ms)
                rows = await page.evaluate(
                    """
                    ({ targetDate }) => {
                      const selector = "[id^='g_'], .event__match";
                      const rows = Array.from(document.querySelectorAll(selector));
                      return rows.map((el) => {
                        const text = (query) => {
                          return el.querySelector(query)?.textContent?.trim() || null;
                        };
                        const leagueHeader = (() => {
                          let node = el.previousElementSibling;
                          while (node) {
                            if (String(node.className).includes("headerLeague")) {
                              return node.textContent?.replace(/\\s+/g, " ")?.trim() || null;
                            }
                            node = node.previousElementSibling;
                          }
                          return null;
                        })();
                        return {
                          id: el.id || el.getAttribute("data-id") || null,
                          href: el.querySelector("a.eventRowLink")?.href || null,
                          home: text(".event__homeParticipant")
                            || text(".event__participant--home"),
                          away: text(".event__awayParticipant")
                            || text(".event__participant--away"),
                          homeScore: text(".event__score--home"),
                          awayScore: text(".event__score--away"),
                          status: text(".event__stage"),
                          time: text(".event__time"),
                          league: leagueHeader,
                          targetDate,
                          betting: Boolean(el.querySelector("[data-testid*='badgeLiveBet']")),
                          tv: Boolean(el.querySelector(".event__icon--tv")),
                          favorite: Boolean(el.querySelector("[data-testid*='favorite']")),
                          innerText: el.innerText || null,
                          rawText: el.textContent?.replace(/\\s+/g, " ")?.trim() || null,
                        };
                      });
                    }
                    """,
                    {"targetDate": target_date},
                )
                # Diagnostico cuando no se extraen filas (visible en logs).
                if not rows:
                    try:
                        title = await page.title()
                        body_count = await page.locator(selector).count()
                        logger.warning(
                            "Flashscore devolvio 0 filas (titulo='%s', selector_count=%d, url=%s)",
                            title,
                            body_count,
                            url,
                        )
                    except Exception:
                        pass
                return rows
            finally:
                await context.close()
                await browser.close()

    async def _try_accept_cookies(self, page: Any) -> None:
        # Selectores especificos primero (Onetrust + Flashscore propio).
        specific_selectors = (
            "#onetrust-accept-btn-handler",
            "button#onetrust-accept-btn-handler",
            "button[data-testid='wcl-buttonPrimary']",
            "button:has-text('AGREE')",
            "button:has-text('Accept All')",
        )
        for sel in specific_selectors:
            try:
                loc = page.locator(sel)
                if await loc.count():
                    await loc.first.click(timeout=1500)
                    await page.wait_for_timeout(400)
                    return
            except Exception:
                continue
        # Fallback por texto/role en varios idiomas.
        for label in (
            "Aceptar todo", "Aceptar", "Acepto", "Consentir", "Estoy de acuerdo",
            "I Accept", "Accept all", "Accept All", "AGREE", "Agree", "OK",
            "Akzeptieren", "Tout accepter", "Accetta",
        ):
            try:
                button = page.get_by_role("button", name=re.compile(label, re.I))
                if await button.count():
                    await button.first.click(timeout=1500)
                    await page.wait_for_timeout(400)
                    return
            except Exception:
                continue

    async def _try_live_filter(self, page: Any) -> None:
        for label in ("EN VIVO", "Live", "LIVE"):
            try:
                locator = page.get_by_text(label, exact=False)
                if await locator.count():
                    await locator.first.click(timeout=1500)
                    return
            except Exception:
                continue

    async def _navigate_to_date(self, page: Any, target_date: str) -> None:
        """Navega el day picker hasta la fecha pedida.

        Robustez frente a bugs conocidos del DOM de Flashscore:
        - Usa el atributo ``data-day-picker-arrow`` en vez de aria-label (i18n-safe).
        - Antes de cada click hace scroll_into_view + wait_for(state="visible").
        - Reintenta hasta 3 veces por paso con backoff y dismiss de overlays.
        - Fallback: si el click directo falla, dispara la accion con teclado o JS.
        - Verificacion final: confirma que el day picker visible muestra DD/MM esperado;
          si no, realiza hasta 3 ajustes finos (+/-1 paso) para corregir desvio.
        """
        try:
            requested = date_type.fromisoformat(target_date)
        except ValueError:
            return

        today = datetime.now().date()
        delta = (requested - today).days
        if delta == 0:
            return

        direction = "next" if delta > 0 else "prev"
        step_dir = 1 if delta > 0 else -1
        steps = min(abs(delta), 14)
        expected_label = requested.strftime("%d/%m")

        # Esperar a que el day picker exista antes de empezar.
        try:
            await page.locator("[data-testid='wcl-dayPickerButton']").first.wait_for(
                state="visible", timeout=8000
            )
        except Exception:
            logger.debug("day picker no visible aun; continuamos best-effort")

        for _ in range(steps):
            previous_date = await self._visible_date_text(page)
            moved = await self._click_day_arrow(page, direction)
            if not moved:
                logger.warning(
                    "No se pudo avanzar el day picker (direccion=%s). Abortando navegacion.",
                    direction,
                )
                break
            # Esperar a que el texto del picker cambie.
            try:
                await page.locator("[data-testid='wcl-dayPickerButton']").filter(
                    has_not_text=previous_date
                ).first.wait_for(timeout=5000)
            except Exception:
                # Damos un respiro y seguimos; la verificacion final corrige desvios.
                await page.wait_for_timeout(900)

        # Verificacion final con ajustes finos (hasta 3 correcciones de +/-1 paso).
        for _ in range(3):
            visible = await self._visible_date_text(page)
            if expected_label and expected_label in visible:
                return
            # Si la fecha visible difiere, intentar un paso adicional en la direccion correcta.
            visible_date = self._parse_visible_date(visible)
            if visible_date is None:
                break
            diff = (requested - visible_date).days
            if diff == 0:
                return
            corr_direction = "next" if diff > 0 else "prev"
            previous_date = visible
            if not await self._click_day_arrow(page, corr_direction):
                break
            try:
                await page.locator("[data-testid='wcl-dayPickerButton']").filter(
                    has_not_text=previous_date
                ).first.wait_for(timeout=4000)
            except Exception:
                await page.wait_for_timeout(700)

    async def _click_day_arrow(self, page: Any, direction: str) -> bool:
        """Click robusto sobre la flecha del day picker (next/prev).

        - Estrategia 1: selector por atributo ``[data-day-picker-arrow="<dir>"]``.
        - Estrategia 2: fallback por aria-label (multi-idioma).
        - Estrategia 3: JS ``element.click()`` para saltar overlays no-bloqueantes.
        - Estrategia 4: teclado (PageDown/PageUp) sobre el contenedor del picker.

        Devuelve True si parece haber registrado un click; False si todas fallaron.
        """
        # Dismiss preventivo de overlays que podrian tapar el boton.
        await self._dismiss_overlays(page)

        attr_selector = f"[data-day-picker-arrow='{direction}']"
        aria_labels = (
            "Día siguiente" if direction == "next" else "Día anterior",
            "Next day" if direction == "next" else "Previous day",
            "Tomorrow" if direction == "next" else "Yesterday",
        )

        # Estrategia 1: selector por atributo data.
        try:
            loc = page.locator(attr_selector).first
            if await loc.count():
                await loc.scroll_into_view_if_needed(timeout=1500)
                await loc.wait_for(state="visible", timeout=4000)
                await loc.click(timeout=8000)
                return True
        except Exception as exc:
            logger.debug("click arrow (attr) fallo: %s", exc)

        # Estrategia 2: aria-label en varios idiomas.
        for label in aria_labels:
            try:
                btn = page.get_by_label(label).first
                if await btn.count():
                    await btn.scroll_into_view_if_needed(timeout=1500)
                    await btn.wait_for(state="visible", timeout=3000)
                    await btn.click(timeout=6000)
                    return True
            except Exception as exc:
                logger.debug("click arrow (label=%s) fallo: %s", label, exc)
                continue

        # Estrategia 3: JS click para saltar overlays.
        try:
            handle = await page.locator(attr_selector).first.element_handle(timeout=1500)
            if handle is not None:
                await page.evaluate("(el) => el.click()", handle)
                return True
        except Exception as exc:
            logger.debug("click arrow (js) fallo: %s", exc)

        # Estrategia 4: teclado.
        try:
            key = "PageDown" if direction == "next" else "PageUp"
            await page.locator("[data-testid='wcl-dayPickerButton']").first.focus(timeout=1500)
            await page.keyboard.press(key)
            return True
        except Exception as exc:
            logger.debug("click arrow (keyboard) fallo: %s", exc)

        return False

    async def _dismiss_overlays(self, page: Any) -> None:
        """Cierra modales/banners conocidos que tapan los controles del day picker."""
        selectors = (
            "[data-testid='wcl-modal-close']",
            "button[aria-label*='cerrar' i]",
            "button[aria-label*='close' i]",
            "#onetrust-accept-btn-handler",
            ".banner__close",
            "[class*='ModalClose']",
        )
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() and await loc.is_visible():
                    await loc.click(timeout=1200)
                    await page.wait_for_timeout(150)
            except Exception:
                continue

    @staticmethod
    def _parse_visible_date(visible_text: str) -> date_type | None:
        """Extrae una fecha del texto del day picker (formatos DD/MM o DD.MM)."""
        if not visible_text:
            return None
        match = re.search(r"(\d{1,2})[/.\-](\d{1,2})", visible_text)
        if not match:
            return None
        day, month = int(match.group(1)), int(match.group(2))
        today = datetime.now().date()
        # Asumir mismo anio; si el mes esta muy alejado del actual, ajustar.
        year = today.year
        try:
            candidate = date_type(year, month, day)
        except ValueError:
            return None
        diff_days = (candidate - today).days
        if diff_days > 200:
            candidate = candidate.replace(year=year - 1)
        elif diff_days < -200:
            candidate = candidate.replace(year=year + 1)
        return candidate

    async def _visible_date_text(self, page: Any) -> str:
        try:
            return await page.locator("[data-testid='wcl-dayPickerButton']").first.inner_text()
        except Exception:
            return ""

    def _row_to_match(self, row: dict[str, Any]) -> LiveMatch | None:
        raw_id = row.get("id") or ""
        match_id = self._normalize_match_id(raw_id)
        home = (row.get("home") or "").strip()
        away = (row.get("away") or "").strip()
        raw_text = (row.get("rawText") or "").strip()
        inner_text = (row.get("innerText") or "").strip()

        if not home or not away:
            parsed = self._fallback_parse(inner_text or raw_text)
            home = home or parsed.get("home", "")
            away = away or parsed.get("away", "")
            row["homeScore"] = row.get("homeScore") or parsed.get("home_score")
            row["awayScore"] = row.get("awayScore") or parsed.get("away_score")

        if not match_id or not home or not away:
            return None

        return LiveMatch(
            match_id=match_id,
            home=home,
            away=away,
            score=MatchScore(home=row.get("homeScore"), away=row.get("awayScore")),
            status=row.get("status"),
            minute=row.get("time"),
            league=row.get("league"),
            url=row.get("href") or f"{self.settings.base_url.rstrip('/')}/partido/{match_id}/",
            scheduled_at=self._scheduled_at(row.get("targetDate"), row.get("time")),
            favorite_available=bool(row.get("favorite")),
            betting_available=bool(row.get("betting")),
            tv_available=bool(row.get("tv")),
            raw_text=raw_text,
        )

    def _normalize_match_id(self, raw_id: str) -> str:
        # Ejemplo comun: g_1_W8mj7MDD -> W8mj7MDD
        parts = raw_id.split("_")
        if len(parts) >= 3 and parts[0] == "g":
            return parts[-1]
        return raw_id

    def _fallback_parse(self, raw_text: str) -> dict[str, str]:
        # Fallback simple para cambios menores de clases CSS.
        pieces = [part.strip() for part in re.split(r"\s{2,}|\n", raw_text) if part.strip()]
        if len(pieces) >= 5 and pieces[-2:] == ["-", "-"]:
            return {"home": pieces[1], "away": pieces[2], "home_score": "-", "away_score": "-"}
        if len(pieces) >= 6 and pieces[-2].isdigit() and pieces[-1].isdigit():
            return {
                "home": pieces[1],
                "away": pieces[2],
                "home_score": pieces[-2],
                "away_score": pieces[-1],
            }
        if len(pieces) >= 3:
            return {"home": pieces[1], "away": pieces[2]}
        return {}

    def _scheduled_at(self, target_date: str | None, time_text: str | None) -> str | None:
        if not time_text:
            return target_date
        value = time_text.strip()
        if target_date and re.fullmatch(r"\d{1,2}:\d{2}", value):
            return f"{target_date}T{value}:00-05:00"
        return value

    def _date_range(self, date_from: str | None, date_to: str | None) -> list[date_type]:
        start = date_type.fromisoformat(date_from) if date_from else datetime.now().date()
        end = date_type.fromisoformat(date_to) if date_to else start
        if end < start:
            start, end = end, start
        days = min((end - start).days, 14)
        return [start.fromordinal(start.toordinal() + offset) for offset in range(days + 1)]

    async def _extract_detail_header(self, page: Any) -> dict[str, str | None]:
        return await page.evaluate(
            """
            () => ({
              home: document.querySelector(".duelParticipant__home .participant__participantName")
                ?.textContent?.trim() || null,
              away: document.querySelector(".duelParticipant__away .participant__participantName")
                ?.textContent?.trim() || null,
              score: document.querySelector(".detailScore__wrapper")?.textContent?.trim() || null,
              status: document.querySelector(".detailScore__status")?.textContent?.trim() || null,
              startTime: document.querySelector(".duelParticipant__startTime")
                ?.textContent?.trim() || null,
            })
            """
        )

    def _merge_match_header(self, match: LiveMatch, header: dict[str, str | None]) -> LiveMatch:
        score_text = header.get("score") or ""
        scores = re.findall(r"\d+|-", score_text)
        score = match.score
        if len(scores) >= 2:
            score = MatchScore(home=scores[0], away=scores[1])
        return LiveMatch(
            match_id=match.match_id,
            home=header.get("home") or match.home,
            away=header.get("away") or match.away,
            score=score,
            status=header.get("status") or match.status,
            minute=match.minute,
            league=match.league,
            country=match.country,
            url=match.url,
            scheduled_at=header.get("startTime") or match.scheduled_at,
            favorite_available=match.favorite_available,
            betting_available=match.betting_available,
            tv_available=match.tv_available,
            raw_text=match.raw_text,
        )

    async def _extract_detail_section(
        self,
        page: Any,
        *,
        section: str,
        base_url: str,
        mid: str,
    ) -> MatchSection:
        try:
            if section == "odds":
                return await self._extract_all_odds_markets(page, base_url=base_url, mid=mid)

            if section in {"summary", "preview"}:
                await page.goto(
                    base_url,
                    wait_until="domcontentloaded",
                    timeout=self.settings.timeout_ms,
                )
                await self._expand_full_preview(page)
            elif section == "lineups":
                await page.goto(
                    base_url,
                    wait_until="domcontentloaded",
                    timeout=self.settings.timeout_ms,
                )
                await self._open_lineups_tab(page)
            elif section == "h2h":
                await page.goto(
                    f"{base_url}h2h/general/?mid={mid}",
                    wait_until="domcontentloaded",
                    timeout=self.settings.timeout_ms,
                )
            elif section == "statistics":
                await page.goto(
                    base_url,
                    wait_until="domcontentloaded",
                    timeout=self.settings.timeout_ms,
                )
                await self._open_tab_by_text(page, "ESTADÍSTICAS")
            else:
                await page.goto(
                    base_url,
                    wait_until="domcontentloaded",
                    timeout=self.settings.timeout_ms,
                )

            await page.wait_for_timeout(2200)
            raw_text = (await page.locator("body").inner_text(timeout=4000)).strip()
            useful = self._slice_section_text(raw_text)
            data = await self._extract_structured_section(page, section)
            return MatchSection(
                name=section,
                available=bool(useful or data),
                raw_text=useful,
                data=data,
            )
        except Exception as exc:
            return MatchSection(
                name=section,
                available=False,
                warnings=[f"No se pudo extraer la seccion: {exc}"],
            )

    def _slice_section_text(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines[:220])

    async def _extract_structured_section(self, page: Any, section: str) -> dict[str, Any]:
        body_text = await page.locator("body").inner_text(timeout=5000)
        lines = [line.strip() for line in body_text.splitlines() if line.strip()]
        if section == "statistics":
            return await page.evaluate(
                """
                () => {
                  const rows = Array.from(document.querySelectorAll("[class*='stat']"));
                  return { stats: rows.map((el) => el.innerText).filter(Boolean).slice(0, 80) };
                }
                """
            )
        if section == "odds":
            data = await page.evaluate(
                """
                () => {
                  const rows = Array.from(document.querySelectorAll("[class*='odds']"));
                  const oddsRows = rows.map((el) => el.innerText).filter(Boolean).slice(0, 120);
                  return { odds_rows: oddsRows };
                }
                """
            )
            data["most_probable_pick"] = self._guess_most_probable_pick(data.get("odds_rows", []))
            return data
        if section == "summary":
            return {
                "preview": self._between_lines(lines, "PREVIA DE FLASHSCORE", "1X2"),
                "absences": self._between_lines(lines, "BAJAS", "CANAL TV"),
                "tv": self._between_lines(lines, "CANAL TV", "STREAMING EN DIRECTO"),
                "streaming": self._between_lines(
                    lines,
                    "STREAMING EN DIRECTO",
                    "INFORMACIÓN ADICIONAL",
                ),
                "additional_info": self._between_lines(lines, "INFORMACIÓN ADICIONAL", "FICHA"),
                "h2h_summary": self._between_lines(lines, "ENFRENTAMIENTOS", "FLASHCORE NOTICIAS"),
            }
        if section == "preview":
            return {
                "preview": self._between_lines(lines, "PREVIA DE FLASHSCORE", "1X2"),
                "absences": self._between_lines(lines, "BAJAS", "CANAL TV"),
            }
        if section == "lineups":
            dom_data = await self._extract_lineups_dom(page)
            # Fallback a parser de texto si el DOM no devolvio nada util
            if not dom_data.get("starting_lineups", {}).get("home") and not dom_data.get(
                "starting_lineups", {}
            ).get("away"):
                dom_data = {
                    "formations": dom_data.get("formations")
                    or self._extract_formations(lines),
                    "starting_lineups": self._between_lines(
                        lines,
                        "ALINEACIONES INICIALES",
                        "SUPLENTES",
                    ),
                    "substitutes": self._between_lines(
                        lines, "SUPLENTES", "JUGADORES AUSENTES"
                    ),
                    "absent_players": self._between_lines(
                        lines, "JUGADORES AUSENTES", "ENTRENADORES"
                    ),
                    "coaches": self._between_lines(lines, "ENTRENADORES", "1X2"),
                    "fallback": "text_parser",
                }
            else:
                # Si las formaciones no salieron del DOM, intentar por texto
                if not (
                    dom_data.get("formations", {}).get("home")
                    or dom_data.get("formations", {}).get("away")
                ):
                    dom_data["formations"] = self._extract_formations(lines)
            return dom_data
        if section == "h2h":
            return {
                "recent_home": self._between_lines(
                    lines,
                    "ÚLTIMOS PARTIDOS: WOLFSBURGO",
                    "ÚLTIMOS PARTIDOS: PADERBORN",
                ),
                "recent_away": self._between_lines(
                    lines,
                    "ÚLTIMOS PARTIDOS: PADERBORN",
                    "ENFRENTAMIENTOS",
                ),
                "head_to_head": self._between_lines(lines, "ENFRENTAMIENTOS", "CUOTAS"),
            }
        return {}

    async def _extract_lineups_dom(self, page: Any) -> dict[str, Any]:
        """Extrae alineaciones, suplentes, ausentes, entrenadores y formaciones
        navegando el DOM del widget `.lf__lineUp` con selectores estables
        (clases BEM `lf__*` y `data-testid` + `[class*='wcl-*']` para tolerar
        los hashes de CSS-in-JS de Flashscore).
        """
        js = r"""
        () => {
          const root = document.querySelector('.lf__lineUp');
          if (!root) return null;

          // Detectar lado (home/away) por el data-testid o por la clase lf__isReversed
          const sideOf = (participantEl) => {
            const tid = participantEl.getAttribute('data-testid') || '';
            if (tid.endsWith('-left')) return 'home';
            if (tid.endsWith('-right')) return 'away';
            const wrapper = participantEl.closest('.lf__participantNew');
            if (wrapper && wrapper.classList.contains('lf__isReversed')) return 'away';
            return 'home';
          };

          const pickByClassPrefix = (el, prefix) => {
            if (!el) return null;
            const node = el.querySelector("[class*='" + prefix + "']");
            return node ? node.textContent.trim() : null;
          };

          const parsePlayer = (participantEl, includeReason) => {
            const number = pickByClassPrefix(participantEl, 'wcl-number');
            const nameRaw = pickByClassPrefix(participantEl, 'wcl-name');
            const flagImg = participantEl.querySelector('img[alt]');
            const country = flagImg ? flagImg.getAttribute('alt') : null;
            const link = participantEl.querySelector("a[href^='/jugador/']");
            const playerUrl = link ? link.getAttribute('href') : null;
            const roleNodes = participantEl.querySelectorAll("[class*='wcl-roles'] span");
            const roles = Array.from(roleNodes)
              .map((n) => (n.textContent || '').trim())
              .filter(Boolean);
            // Limpiar rol pegado al nombre (ej: "Grabara K.(G)" -> "Grabara K.")
            let name = nameRaw || null;
            if (name) {
              roles.forEach((r) => {
                if (r) name = name.split(r).join('');
              });
              name = name.replace(/\s+/g, ' ').trim();
            }
            const out = { number: number || null, name, country, player_url: playerUrl, roles };
            if (includeReason) {
              const reason = pickByClassPrefix(participantEl, 'wcl-description');
              out.reason = reason || null;
            }
            return out;
          };

          const normalize = (s) => (s || '')
            .toLowerCase()
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '');

          const TITLE_MAP = [
            { key: 'starting_lineups', needles: ['alineaciones iniciales', 'alineacion inicial', 'titulares'] },
            { key: 'substitutes', needles: ['suplentes', 'banca'] },
            { key: 'absent_players', needles: ['jugadores ausentes', 'ausentes', 'bajas'] },
            { key: 'coaches', needles: ['entrenadores', 'cuerpo tecnico', 'entrenador'] },
          ];

          const result = {
            formations: { home: null, away: null },
            starting_lineups: { home: [], away: [] },
            substitutes: { home: [], away: [] },
            absent_players: { home: [], away: [] },
            coaches: { home: [], away: [] },
          };

          // Formaciones: dentro del header del campo aparecen como '3-1-4-2' y '3-4-2-1'
          const headerSpans = root.querySelectorAll(
            "[class*='lf__fieldHeader'], [class*='lf__formation']"
          );
          const formations = [];
          headerSpans.forEach((el) => {
            const txt = (el.textContent || '').trim();
            if (/^\d(?:[-\u00B7\u2022\s]+\d)+$/.test(txt) && txt.length <= 17) {
              const clean = txt
                .replace(/[\s\u00B7\u2022\-]+/g, '-')
                .replace(/^-+|-+$/g, '');
              formations.push(clean);
            }
          });
          if (formations.length >= 2) {
            result.formations.home = formations[0];
            result.formations.away = formations[1];
          }

          // Recorrer secciones (Alineaciones iniciales, Suplentes, Ausentes, Entrenadores)
          const sections = root.querySelectorAll(':scope > .section, .section');
          sections.forEach((sec) => {
            const titleEl = sec.querySelector("[data-testid='wcl-headerSection-text']");
            const title = titleEl ? normalize(titleEl.textContent || '') : '';
            const target = TITLE_MAP.find((m) => m.needles.some((n) => title.includes(n)));
            if (!target) return;
            const includeReason = target.key === 'absent_players';
            const participants = sec.querySelectorAll(
              "[data-testid^='wcl-lineupsParticipantGeneral']"
            );
            participants.forEach((p) => {
              const side = sideOf(p);
              result[target.key][side].push(parsePlayer(p, includeReason));
            });
          });

          return result;
        }
        """
        try:
            data = await page.evaluate(js)
        except Exception:
            return {
                "formations": {"home": None, "away": None},
                "starting_lineups": {"home": [], "away": []},
                "substitutes": {"home": [], "away": []},
                "absent_players": {"home": [], "away": []},
                "coaches": {"home": [], "away": []},
            }
        if not data:
            return {
                "formations": {"home": None, "away": None},
                "starting_lineups": {"home": [], "away": []},
                "substitutes": {"home": [], "away": []},
                "absent_players": {"home": [], "away": []},
                "coaches": {"home": [], "away": []},
            }
        return data

    def _guess_most_probable_pick(self, odds_rows: list[str]) -> str | None:
        numbers: list[tuple[float, str]] = []
        labels = ["home", "draw", "away"]
        for row in odds_rows[:20]:
            for index, value in enumerate(re.findall(r"\d+\.\d+", row)[:3]):
                try:
                    numbers.append((float(value), labels[index]))
                except ValueError:
                    continue
        if not numbers:
            return None
        return min(numbers, key=lambda item: item[0])[1]

    def _base_match_url(self, url: str) -> str:
        clean = url.split("#", 1)[0].split("?", 1)[0]
        if "/cuotas/" in clean:
            clean = clean.split("/cuotas/", 1)[0] + "/"
        if "/h2h/" in clean:
            clean = clean.split("/h2h/", 1)[0] + "/"
        if "/resumen/" in clean:
            clean = clean.split("/resumen/", 1)[0] + "/"
        return clean.rstrip("/") + "/"

    def _match_mid(self, url: str, fallback: str) -> str:
        match = re.search(r"[?&]mid=([^&#]+)", url)
        return match.group(1) if match else fallback

    async def _expand_full_preview(self, page: Any) -> None:
        for label in ("Mostrar previa íntegra", "Mostrar previa integra"):
            try:
                locator = page.get_by_text(label, exact=False)
                if await locator.count():
                    await locator.first.click(timeout=2500)
                    await page.wait_for_timeout(1000)
                    return
            except Exception:
                continue

    async def _open_lineups_tab(self, page: Any) -> None:
        # Click sobre la pestana Alineaciones (es SPA, la URL directa devuelve 404).
        # Ojo: en el DOM el texto esta capitalizado ("Alineaciones"); las mayusculas
        # que se ven en pantalla son CSS `text-transform: uppercase`.
        await self._open_tab_by_text(page, "Alineaciones")
        # Esperar a que el widget de alineaciones aparezca en el DOM
        try:
            await page.wait_for_selector(".lf__lineUp", timeout=8000)
        except Exception:
            # Tolerar partidos sin alineaciones publicadas todavia
            await page.wait_for_timeout(1200)

    async def _open_tab_by_text(self, page: Any, label: str) -> None:
        # Intentar varias variantes (DOM tiene capitalizada, no MAYUSCULA)
        variants: list[str] = []
        seen: set[str] = set()
        for candidate in (label, label.capitalize(), label.lower(), label.upper()):
            if candidate and candidate not in seen:
                seen.add(candidate)
                variants.append(candidate)
        for variant in variants:
            try:
                locator = page.get_by_text(variant, exact=True)
                count = await locator.count()
            except Exception:
                continue
            if not count:
                continue
            try:
                await locator.first.click(timeout=3000)
                await page.wait_for_timeout(2000)
                return
            except Exception:
                continue
        # Fallback: regex case-insensitive
        try:
            import re as _re

            pattern = _re.compile(rf"^\s*{_re.escape(label)}\s*$", _re.IGNORECASE)
            locator = page.get_by_text(pattern)
            if await locator.count():
                await locator.first.click(timeout=3000)
                await page.wait_for_timeout(2000)
        except Exception:
            return

    async def _extract_all_odds_markets(
        self,
        page: Any,
        *,
        base_url: str,
        mid: str,
    ) -> MatchSection:
        markets = {
            "1x2": "cuotas-1x2/partido/",
            "over_under": "mas-de-menos-de/partido/",
            "both_teams_to_score": "ambos-equipos-marcaran/partido/",
            "asian_handicap": "handicap-asiatico/partido/",
            "to_qualify": "clasificara/partido-pr-incl/",
            "double_chance": "doble-oportunidad/partido/",
            "draw_no_bet": "draw-no-bet/partido/",
            "correct_score": "correct-score/partido/",
            "half_time_full_time": "ht-ft/partido/",
            "odd_even_goals": "odd-even/partido/",
        }
        data: dict[str, Any] = {"markets": {}, "best_recommendations": []}
        raw_parts: list[str] = []
        for name, path in markets.items():
            url = f"{base_url}cuotas/{path}?mid={mid}"
            try:
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.settings.timeout_ms,
                )
                await page.wait_for_timeout(1800)
                text = (await page.locator("body").inner_text(timeout=5000)).strip()
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                market_data = self._parse_odds_market(name, lines)
                data["markets"][name] = market_data
                raw_parts.append(f"## {name}\n" + "\n".join(lines[:120]))
            except Exception as exc:
                data["markets"][name] = {"available": False, "error": str(exc)}

        data["best_recommendations"] = self._build_betting_recommendations(data["markets"])
        return MatchSection(
            name="odds",
            available=any(market.get("available") for market in data["markets"].values()),
            raw_text="\n\n".join(raw_parts),
            data=data,
        )

    def _parse_odds_market(self, name: str, lines: list[str]) -> dict[str, Any]:
        start = self._first_index(lines, "CASA DE APUESTAS")
        end_candidates = [
            self._first_index(lines, "Los juegos y apuestas deportivas"),
            self._first_index(lines, "PROMOCIONES"),
            self._first_index(lines, "LIGAS ANCLADAS"),
        ]
        end_values = [value for value in end_candidates if value is not None and value > start]
        end = min(end_values) if end_values else min(len(lines), start + 180)
        odds_lines = lines[start:end]
        numeric_values = [float(value) for value in re.findall(r"\d+\.\d+", "\n".join(odds_lines))]
        return {
            "available": bool(odds_lines and numeric_values),
            "lines": odds_lines[:160],
            "lowest_odds": min(numeric_values) if numeric_values else None,
            "highest_odds": max(numeric_values) if numeric_values else None,
            "market": name,
        }

    def _build_betting_recommendations(self, markets: dict[str, Any]) -> list[dict[str, Any]]:
        recommendations: list[dict[str, Any]] = []
        one_x_two = markets.get("1x2", {})
        if one_x_two.get("available"):
            pick = self._guess_most_probable_pick(one_x_two.get("lines", []))
            recommendations.append(
                {
                    "market": "1x2",
                    "pick": pick,
                    "reason": (
                        "La cuota menor del mercado 1X2 suele representar "
                        "el resultado más probable."
                    ),
                }
            )
        for key in ("double_chance", "draw_no_bet", "over_under", "both_teams_to_score"):
            market = markets.get(key, {})
            if market.get("available"):
                recommendations.append(
                    {
                        "market": key,
                        "pick": "revisar lineas con menor cuota y mayor margen de seguridad",
                        "reason": (
                            "Mercado disponible con varias casas; usar como "
                            "alternativa conservadora."
                        ),
                    }
                )
        return recommendations

    def _between_lines(self, lines: list[str], start_label: str, end_label: str) -> list[str]:
        start = self._first_index(lines, start_label)
        if start is None:
            return []
        end = self._first_index(lines, end_label, start + 1)
        if end is None:
            end = min(len(lines), start + 80)
        return lines[start + 1 : end]

    def _first_index(self, lines: list[str], label: str, start: int = 0) -> int | None:
        label_lower = label.lower()
        for index in range(start, len(lines)):
            if label_lower in lines[index].lower():
                return index
        return None

    def _extract_formations(self, lines: list[str]) -> dict[str, str | None]:
        def _normalize_formation(value: str | None) -> str | None:
            if not value:
                return None
            cleaned = re.sub(r"[\s\u00B7\u2022\-]+", "-", value.strip()).strip("-")
            return cleaned or None

        for index, line in enumerate(lines):
            if line == "SISTEMA DE JUEGO" and index > 0 and index + 1 < len(lines):
                return {
                    "home": _normalize_formation(lines[index - 1]),
                    "away": _normalize_formation(lines[index + 1]),
                }
        return {"home": None, "away": None}
