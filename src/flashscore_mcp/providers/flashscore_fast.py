"""Provider Flashscore optimizado.

Diferencias clave vs ``FlashscorePlaywrightProvider`` (baseline):

1. **Reusa BrowserPool**: NO lanza ``chromium.launch()`` por request (ahorra 5-10s/req).
2. **Cache L3 estatico**: antes de Playwright intenta GET a GitHub Pages (publicado
   por el workflow ``precache.yml``). Si hay hit fresco (<10min) responde en <300ms.
3. **Paralelizacion de secciones**: ``fetch_match_full_detail`` abre N paginas en
   paralelo con ``asyncio.gather`` (90s -> ~15s con N=6).
4. **fetch_match_detail directo**: va a la URL canonica ``/match/<mid>/`` en vez de
   iterar 7 dias pasados con browsers nuevos.
5. **storage_state reusado**: cookies aceptadas se cachean a disco; saltamos
   ``_try_accept_cookies`` cuando ya estan presentes.

Hereda del provider baseline para reusar todo el parsing (``_row_to_match``,
``_extract_detail_section``, ``_try_accept_cookies``, etc.). Solo overridea
los puntos de entrada que pagan el costo de Playwright.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from flashscore_mcp.browser_pool import BrowserPool
from flashscore_mcp.config import Settings
from flashscore_mcp.models import (
    LiveMatch,
    MatchDetail,
    MatchScore,
    MatchSection,
    utc_now_iso,
)
from flashscore_mcp.providers.flashscore import FlashscorePlaywrightProvider

logger = logging.getLogger(__name__)


class FlashscoreFastProvider(FlashscorePlaywrightProvider):
    """Provider Flashscore con pool reusado + paralelizacion + cache L3."""

    source_name = "flashscore_fast"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._pool = BrowserPool.get_instance(settings)
        self._http: httpx.AsyncClient | None = None

    # ---------------------------------------------------------------- helpers HTTP
    def _get_http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                timeout=self.settings.static_cache_timeout_seconds,
                headers={"Accept": "application/json", "User-Agent": "flashscore-mcp-fast/1.0"},
            )
        return self._http

    async def _try_static_cache(self, path: str) -> dict[str, Any] | None:
        """Intenta leer un JSON del CDN (GitHub Pages). Devuelve None si no hay hit."""
        base = (self.settings.static_cache_base_url or "").rstrip("/")
        if not base:
            return None
        url = f"{base}/{path.lstrip('/')}"
        try:
            client = self._get_http()
            response = await client.get(url)
            if response.status_code != 200:
                return None
            data = response.json()
        except Exception as exc:  # pragma: no cover - red puede fallar
            logger.debug("static cache miss para %s: %s", url, exc)
            return None

        # Verificar frescura: campo "fetched_at" del snapshot
        fetched_at = data.get("fetched_at")
        if fetched_at:
            try:
                ts = datetime.fromisoformat(str(fetched_at).replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - ts).total_seconds()
                if age > self.settings.static_cache_max_age_seconds:
                    logger.debug("static cache stale (%.0fs) para %s", age, url)
                    return None
            except Exception:
                pass
        logger.info("static cache HIT: %s", url)
        return data

    @staticmethod
    def _live_cache_path(sport: str, league: str | None, live_only: bool) -> str:
        suffix = "live" if live_only else "all"
        if league:
            league_slug = league.lower().replace(" ", "-")
            return f"live/{sport}-{league_slug}-{suffix}.json"
        return f"live/{sport}-{suffix}.json"

    @staticmethod
    def _date_cache_path(sport: str, date_iso: str, league: str | None) -> str:
        if league:
            league_slug = league.lower().replace(" ", "-")
            return f"by-date/{sport}-{date_iso}-{league_slug}.json"
        return f"by-date/{sport}-{date_iso}.json"

    @staticmethod
    def _detail_cache_path(match_id: str) -> str:
        return f"detail/{match_id}.json"

    def _items_from_payload(self, payload: dict[str, Any]) -> list[LiveMatch]:
        items = payload.get("items") or []
        result: list[LiveMatch] = []
        for raw in items:
            try:
                score_raw = raw.get("score") or {}
                result.append(
                    LiveMatch(
                        match_id=raw["match_id"],
                        home=raw.get("home", ""),
                        away=raw.get("away", ""),
                        score=MatchScore(
                            home=score_raw.get("home"), away=score_raw.get("away")
                        ),
                        status=raw.get("status"),
                        minute=raw.get("minute"),
                        league=raw.get("league"),
                        country=raw.get("country"),
                        url=raw.get("url"),
                        scheduled_at=raw.get("scheduled_at"),
                        favorite_available=bool(raw.get("favorite_available")),
                        betting_available=bool(raw.get("betting_available")),
                        tv_available=bool(raw.get("tv_available")),
                        raw_text=raw.get("raw_text"),
                    )
                )
            except Exception:
                continue
        return result

    # ---------------------------------------------------------------- API publica
    async def fetch_live_matches(
        self,
        *,
        sport: str = "football",
        league: str | None = None,
        live_only: bool = True,
    ) -> list[LiveMatch]:
        # 1) intentar cache L3
        payload = await self._try_static_cache(
            self._live_cache_path(sport, league, live_only)
        )
        if payload:
            return self._items_from_payload(payload)
        # 2) fallback Playwright via pool
        url = self._sport_url(sport)
        rows = await self._extract_rows_pooled(
            url=url, live_only=live_only, target_date=None
        )
        matches = [self._row_to_match(row) for row in rows]
        matches = [m for m in matches if m is not None]
        if league:
            needle = league.lower()
            matches = [
                m for m in matches
                if needle in " ".join(
                    value or "" for value in (m.league, m.country, m.raw_text)
                ).lower()
            ]
        return matches

    async def fetch_matches_by_date(
        self,
        *,
        date: str,
        sport: str = "football",
        league: str | None = None,
    ) -> list[LiveMatch]:
        payload = await self._try_static_cache(
            self._date_cache_path(sport, date, league)
        )
        if payload:
            return self._items_from_payload(payload)
        url = self._sport_url(sport)
        rows = await self._extract_rows_pooled(
            url=url, live_only=False, target_date=date
        )
        matches = [self._row_to_match(row) for row in rows]
        matches = [m for m in matches if m is not None]
        if league:
            needle = league.lower()
            matches = [
                m for m in matches if needle in f"{m.league} {m.raw_text}".lower()
            ]
        return matches

    async def fetch_match_detail(self, match_id: str) -> LiveMatch | None:
        """Optimizado: va directo a URL canonica, NO itera 7 dias pasados."""
        # 1) intentar cache L3
        payload = await self._try_static_cache(self._detail_cache_path(match_id))
        if payload and isinstance(payload.get("match"), dict):
            items = self._items_from_payload({"items": [payload["match"]]})
            if items:
                return items[0]
        # 2) intentar resolver desde live (suele cubrir partidos actuales rapido)
        try:
            current = await self.fetch_live_matches(live_only=False)
            for match in current:
                if match.match_id == match_id:
                    return match
        except Exception:
            pass
        # 3) ir directo a la URL canonica /match/<mid>/
        direct_url = f"{self.settings.base_url.rstrip('/')}/match/{match_id}/"
        try:
            async with self._pool.page() as (_ctx, page):
                await page.goto(direct_url, wait_until="domcontentloaded")
                await self._try_accept_cookies_fast(page)
                header = await self._extract_detail_header(page)
                if not header:
                    return None
                stub = LiveMatch(match_id=match_id, home="", away="", url=direct_url)
                return self._merge_match_header(stub, header)
        except Exception as exc:
            logger.warning("fetch_match_detail directo fallo para %s: %s", match_id, exc)
            return None

    async def fetch_match_full_detail(
        self,
        match_id: str,
        *,
        sections: list[str] | None = None,
    ) -> MatchDetail | None:
        # 1) cache L3 (lo mas rapido)
        payload = await self._try_static_cache(self._detail_cache_path(match_id))
        if payload and isinstance(payload.get("sections"), dict):
            requested = sections or list(payload["sections"].keys())
            if all(sec in payload["sections"] for sec in requested):
                match_data = payload.get("match") or {}
                items = self._items_from_payload({"items": [match_data]})
                if items:
                    sec_objs = {
                        name: MatchSection(
                            name=name,
                            available=bool(payload["sections"][name].get("available")),
                            raw_text=payload["sections"][name].get("raw_text"),
                            data=payload["sections"][name].get("data"),
                            warnings=payload["sections"][name].get("warnings") or [],
                        )
                        for name in requested
                    }
                    return MatchDetail(
                        match=items[0],
                        fetched_at=payload.get("fetched_at", utc_now_iso()),
                        source=f"{self.source_name}_l3cache",
                        sections=sec_objs,
                    )

        # 2) Resolver header con una pagina; luego paralelizar secciones
        match = await self.fetch_match_detail(match_id)
        if match is None:
            match = LiveMatch(
                match_id=match_id,
                home="",
                away="",
                url=f"{self.settings.base_url.rstrip('/')}/match/{match_id}/",
            )
        detail_url = match.url or f"{self.settings.base_url.rstrip('/')}/match/{match_id}/"
        base_url = self._base_match_url(detail_url)
        mid = self._match_mid(detail_url, match_id)
        requested = sections or ["summary", "statistics", "lineups", "odds", "h2h", "preview"]

        # Limitar paralelismo segun config. Default conservador (2) para evitar
        # saturar el BrowserPool cuando varios clientes piden detalle a la vez.
        # Si fast_parallel_sections=6 + clientes en paralelo => >20 paginas
        # simultaneas => Chromium se asfixia en HF Space free.
        sem = asyncio.Semaphore(
            min(self.settings.fast_parallel_sections, max(1, len(requested)))
        )
        # Timeout global por seccion: si Playwright se cuelga (cookies bloqueantes,
        # JS infinito, recurso lento), abortamos y devolvemos seccion vacia con
        # warning en vez de bloquear todo el detalle del partido.
        section_timeout = max(20.0, self.settings.timeout_ms / 1000.0 * 1.5)

        async def _run_section(name: str) -> tuple[str, MatchSection]:
            async with sem:
                async def _do() -> MatchSection:
                    async with self._pool.page() as (_ctx, page):
                        await page.goto(base_url, wait_until="domcontentloaded")
                        await self._try_accept_cookies_fast(page)
                        return await self._extract_detail_section(
                            page, section=name, base_url=base_url, mid=mid
                        )
                try:
                    section = await asyncio.wait_for(_do(), timeout=section_timeout)
                    return name, section
                except asyncio.TimeoutError:
                    logger.warning(
                        "Seccion %s del partido %s excedio timeout %.1fs",
                        name, mid, section_timeout,
                    )
                    return name, MatchSection(
                        name=name,
                        available=False,
                        warnings=[f"Timeout {section_timeout:.0f}s"],
                    )
                except Exception as exc:
                    return name, MatchSection(
                        name=name,
                        available=False,
                        warnings=[f"Error paralelo: {exc}"],
                    )

        results = await asyncio.gather(*(_run_section(s) for s in requested))
        result_sections: dict[str, MatchSection] = {name: sec for name, sec in results}

        return MatchDetail(
            match=match,
            fetched_at=utc_now_iso(),
            source=self.source_name,
            sections=result_sections,
        )

    # ---------------------------------------------------------------- internos
    async def _try_accept_cookies_fast(self, page: Any) -> None:
        """Skip cookies si ya hay cookie de Onetrust (storage_state reusado)."""
        try:
            cookies = await page.context.cookies()
            for cookie in cookies:
                name = cookie.get("name", "").lower()
                if "onetrust" in name or "cookieconsent" in name:
                    return  # ya aceptado, ahorrar tiempo
        except Exception:
            pass
        await self._try_accept_cookies(page)

    async def _extract_rows_pooled(
        self,
        *,
        url: str,
        live_only: bool,
        target_date: str | None,
    ) -> list[dict[str, Any]]:
        """Mismo extract que baseline pero usando el pool (sin launch por request)."""
        async with self._pool.page() as (_ctx, page):
            await page.goto(url, wait_until="domcontentloaded")
            await self._try_accept_cookies_fast(page)
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
                    const text = (q) => el.querySelector(q)?.textContent?.trim() || null;
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
                      home: text(".event__homeParticipant") || text(".event__participant--home"),
                      away: text(".event__awayParticipant") || text(".event__participant--away"),
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
            if not rows:
                logger.warning(
                    "Fast: 0 filas en %s (live_only=%s, date=%s)",
                    url,
                    live_only,
                    target_date,
                )
            return rows

    async def warmup(self) -> None:
        """Pre-calienta el browser + acepta cookies + guarda storage_state.

        Llamado por el server en lifespan. Hace que el primer request real
        encuentre browser ya iniciado + cookies preaceptadas (~5s ahorrados).
        """
        try:
            url = self.settings.base_url.rstrip("/") + "/"
            async with self._pool.page() as (ctx, page):
                await page.goto(url, wait_until="domcontentloaded")
                await self._try_accept_cookies(page)
                await page.wait_for_timeout(500)
                await self._pool.save_storage_state(ctx)
                logger.info("Warmup completado para %s", url)
        except Exception as exc:
            logger.warning("Warmup fallo (no critico): %s", exc)

    async def close(self) -> None:
        if self._http is not None:
            try:
                await self._http.aclose()
            except Exception:
                pass
            self._http = None


def _dumps_snapshot(items: list[LiveMatch], source: str) -> str:
    """Helper para serializar snapshots a JSON compatible con _items_from_payload."""
    return json.dumps(
        {
            "source": source,
            "fetched_at": utc_now_iso(),
            "items": [item.to_dict() for item in items],
        },
        ensure_ascii=False,
    )
