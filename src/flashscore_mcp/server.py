from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from flashscore_mcp.cache import AsyncTTLCache, select_ttl_from_item
from flashscore_mcp.config import Settings
from flashscore_mcp.models import LiveMatch, LiveSnapshot, MatchDetail, utc_now_iso
from flashscore_mcp.providers.factory import build_provider
from flashscore_mcp.services import LivePoller
from flashscore_mcp.services.poller import live_cache_key

logger = logging.getLogger(__name__)

settings = Settings.from_env()
mcp = FastMCP(
    "flashscore-live-mcp",
    stateless_http=True,
    json_response=True,
    host=settings.bind_host,
    port=settings.bind_port,
)
provider = build_provider(settings)
cache: AsyncTTLCache[Any] = AsyncTTLCache()
poller = LivePoller(cache=cache, provider=provider, settings=settings)


def _ttl_for_items(items: list[LiveMatch]) -> int:
    """Devuelve el TTL apropiado segun la mayoria de estados de los partidos."""
    if not items:
        return settings.ttl_scheduled_seconds
    counts = {"live": 0, "scheduled": 0, "finished": 0}
    for match in items:
        ttl = select_ttl_from_item(
            match,
            live=settings.ttl_live_seconds,
            scheduled=settings.ttl_scheduled_seconds,
            finished=settings.ttl_finished_seconds,
            default=settings.ttl_scheduled_seconds,
        )
        if ttl == settings.ttl_live_seconds:
            counts["live"] += 1
        elif ttl == settings.ttl_finished_seconds:
            counts["finished"] += 1
        else:
            counts["scheduled"] += 1
    # Si hay AL MENOS un partido en vivo, refrescamos rapido todo el snapshot.
    if counts["live"] > 0:
        return settings.ttl_live_seconds
    if counts["scheduled"] > 0:
        return settings.ttl_scheduled_seconds
    return settings.ttl_finished_seconds


async def _live_snapshot(
    *,
    sport: str,
    league: str | None,
    live_only: bool,
    force_refresh: bool,
) -> dict[str, Any]:
    key = live_cache_key(sport, league, live_only)
    entry = await cache.get(key)
    if entry and not force_refresh and not entry.is_stale:
        snapshot: LiveSnapshot = entry.value
        return snapshot.to_dict()

    warnings: list[str] = []
    try:
        matches = await provider.fetch_live_matches(
            sport=sport,
            league=league,
            live_only=live_only,
        )
        snapshot = LiveSnapshot(
            source=provider.source_name,
            fetched_at=utc_now_iso(),
            cache_ttl_seconds=settings.cache_ttl_seconds,
            stale=False,
            items=matches,
            warnings=warnings,
        )
        ttl = _ttl_for_items(matches)
        await cache.set(key, snapshot, ttl)
        return snapshot.to_dict()
    except Exception as exc:
        if entry:
            snapshot = entry.value
            fallback = LiveSnapshot(
                source=snapshot.source,
                fetched_at=snapshot.fetched_at,
                cache_ttl_seconds=snapshot.cache_ttl_seconds,
                stale=True,
                items=snapshot.items,
                warnings=[f"Fuente no disponible; se devuelve cache anterior: {exc}"],
            )
            return fallback.to_dict()
        raise


@mcp.tool()
async def get_live_scores(
    sport: str = "football",
    league: str | None = None,
    live_only: bool = True,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Obtiene marcadores deportivos desde cache con refresco controlado."""
    return await _live_snapshot(
        sport=sport,
        league=league,
        live_only=live_only,
        force_refresh=force_refresh,
    )


@mcp.tool()
async def get_match_detail(match_id: str, force_refresh: bool = False) -> dict[str, Any]:
    """Obtiene el detalle resumido de un partido por ID."""
    key = f"match:{match_id}"
    entry = await cache.get(key)
    if entry and not force_refresh and not entry.is_stale:
        match: LiveMatch = entry.value
        return {"source": provider.source_name, "stale": False, "item": match.to_dict()}

    try:
        match = await provider.fetch_match_detail(match_id)
        if match is None:
            return {
                "source": provider.source_name,
                "stale": False,
                "item": None,
                "warnings": ["No se encontro el partido en la fuente actual."],
            }
        ttl = select_ttl_from_item(
            match,
            live=settings.ttl_live_seconds,
            scheduled=settings.ttl_scheduled_seconds,
            finished=settings.ttl_finished_seconds,
            default=settings.cache_ttl_seconds,
        )
        await cache.set(key, match, ttl)
        return {"source": provider.source_name, "stale": False, "item": match.to_dict()}
    except Exception as exc:
        if entry:
            match = entry.value
            return {
                "source": provider.source_name,
                "stale": True,
                "item": match.to_dict(),
                "warnings": [f"Fuente no disponible; se devuelve cache anterior: {exc}"],
            }
        raise


@mcp.tool()
async def get_matches_by_date(
    date: str,
    sport: str = "football",
    league: str | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Obtiene partidos de una fecha ISO YYYY-MM-DD desde Flashscore."""
    key = f"date:{sport}:{date}:{league or 'all'}"
    entry = await cache.get(key)
    if entry and not force_refresh and not entry.is_stale:
        snapshot: LiveSnapshot = entry.value
        return snapshot.to_dict()

    matches = await provider.fetch_matches_by_date(date=date, sport=sport, league=league)
    snapshot = LiveSnapshot(
        source=provider.source_name,
        fetched_at=utc_now_iso(),
        cache_ttl_seconds=settings.cache_ttl_seconds,
        stale=False,
        items=matches,
    )
    ttl = _ttl_for_items(matches)
    await cache.set(key, snapshot, ttl)
    return snapshot.to_dict()


@mcp.tool()
async def search_matches(
    query: str,
    date_from: str | None = None,
    date_to: str | None = None,
    sport: str = "football",
    league: str | None = None,
) -> dict[str, Any]:
    """Busca partidos por equipo, liga o texto entre fechas."""
    matches = await provider.search_matches(
        query=query,
        date_from=date_from,
        date_to=date_to,
        sport=sport,
        league=league,
    )
    return {
        "source": provider.source_name,
        "fetched_at": utc_now_iso(),
        "query": query,
        "items": [match.to_dict() for match in matches],
    }


@mcp.tool()
async def get_match_full_detail(
    match_id: str,
    sections: list[str] | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Obtiene resumen, estadisticas, alineaciones, H2H y previa del partido.

    Nota: en HF Space free tier (2 vCPU) las cuotas (`odds`) NO se incluyen por
    defecto porque su scrapeo paraleliza 3 mercados y satura CPU al combinarse
    con las otras 4 secciones. Para cuotas usar `get_match_odds` que las pide
    aparte (un solo request HTTP, ~10s) y se cachea independientemente.
    """
    requested = sections or ["summary", "statistics", "lineups", "h2h", "preview"]
    key = f"full:{match_id}:{','.join(sorted(requested))}"
    entry = await cache.get(key)
    if entry and not force_refresh and not entry.is_stale:
        detail: MatchDetail = entry.value
        return detail.to_dict()

    # Timeout global: GARANTIZA que nunca tardamos mas que el cliente
    # (default cliente warm=45s, cold=90s). Si excedemos, devolvemos cache
    # stale (si existe) o un error explicito para que el cliente no se
    # bloquee. Configurable via FLASHSCORE_FULL_DETAIL_TIMEOUT_S (default 24s).
    full_timeout = float(os.getenv("FLASHSCORE_FULL_DETAIL_TIMEOUT_S", "24"))
    try:
        detail = await asyncio.wait_for(
            provider.fetch_match_full_detail(match_id=match_id, sections=requested),
            timeout=full_timeout,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "get_match_full_detail timeout global %.1fs para %s, fallback a cache stale",
            full_timeout, match_id,
        )
        if entry is not None:
            stale_detail: MatchDetail = entry.value
            payload = stale_detail.to_dict()
            payload["warnings"] = (payload.get("warnings") or []) + [
                f"Timeout global {full_timeout:.0f}s: sirviendo cache stale",
            ]
            return payload
        return {
            "source": provider.source_name,
            "fetched_at": utc_now_iso(),
            "item": None,
            "warnings": [
                f"Timeout global {full_timeout:.0f}s y sin cache previo.",
            ],
        }
    if detail is None:
        return {
            "source": provider.source_name,
            "fetched_at": utc_now_iso(),
            "item": None,
            "warnings": ["No se encontro el partido para extraer detalle completo."],
        }
    ttl = select_ttl_from_item(
        detail.match,
        live=settings.ttl_live_seconds,
        scheduled=settings.ttl_scheduled_seconds,
        finished=settings.ttl_finished_seconds,
        default=settings.cache_ttl_seconds,
    )
    await cache.set(key, detail, ttl)
    return detail.to_dict()


@mcp.tool()
async def get_match_statistics(match_id: str, force_refresh: bool = False) -> dict[str, Any]:
    """Obtiene estadisticas visibles: ataques, posesion, corners, tarjetas, tiros, etc."""
    return await get_match_full_detail(
        match_id=match_id,
        sections=["statistics"],
        force_refresh=force_refresh,
    )


@mcp.tool()
async def get_match_odds(match_id: str, force_refresh: bool = False) -> dict[str, Any]:
    """Obtiene cuotas visibles y una estimacion simple del pick mas probable."""
    return await get_match_full_detail(
        match_id=match_id,
        sections=["odds"],
        force_refresh=force_refresh,
    )


@mcp.tool()
async def get_match_events(match_id: str, force_refresh: bool = False) -> dict[str, Any]:
    """Obtiene resumen/timeline visible de eventos del partido."""
    return await get_match_full_detail(
        match_id=match_id,
        sections=["summary"],
        force_refresh=force_refresh,
    )


@mcp.tool()
async def watch_match(
    match_id: str,
    duration_seconds: int = 30,
    interval_seconds: int = 5,
) -> dict[str, Any]:
    """Observa un partido por polling cacheado y devuelve una serie de muestras."""
    duration = min(max(duration_seconds, 5), settings.max_watch_seconds)
    interval = min(max(interval_seconds, 1), duration)
    samples: list[dict[str, Any]] = []
    deadline = asyncio.get_running_loop().time() + duration

    while True:
        samples.append(await get_match_detail(match_id=match_id, force_refresh=True))
        if asyncio.get_running_loop().time() + interval > deadline:
            break
        await asyncio.sleep(interval)

    return {
        "source": provider.source_name,
        "match_id": match_id,
        "duration_seconds": duration,
        "interval_seconds": interval,
        "samples": samples,
    }


@mcp.tool()
async def get_cache_status() -> dict[str, object]:
    """Muestra estado interno del cache en memoria."""
    return await cache.status()


@mcp.tool()
async def refresh_live_cache(
    sport: str = "football",
    league: str | None = None,
    live_only: bool = True,
) -> dict[str, Any]:
    """Fuerza un refresco unico del snapshot en vivo."""
    poller.state.sport = sport
    poller.state.league = league
    poller.state.live_only = live_only
    snapshot = await poller.refresh_once()
    return snapshot.to_dict()


@mcp.tool()
async def start_live_poller(
    sport: str = "football",
    league: str | None = None,
    live_only: bool = True,
    interval_seconds: int | None = None,
) -> dict[str, Any]:
    """Inicia refresco automatico en background para snapshots vivos."""
    return poller.start(
        sport=sport,
        league=league,
        live_only=live_only,
        interval_seconds=interval_seconds,
    )


@mcp.tool()
async def stop_live_poller() -> dict[str, Any]:
    """Detiene el refresco automatico en background."""
    return await poller.stop()


@mcp.tool()
async def get_poller_status() -> dict[str, Any]:
    """Muestra estado del poller interno."""
    return poller.status()


@mcp.resource("sports://football/live")
async def football_live_resource() -> str:
    """Snapshot actual de futbol en vivo."""
    data = await get_live_scores(sport="football", live_only=True)
    return json.dumps(data, ensure_ascii=False)


@mcp.resource("sports://match/{match_id}")
async def match_resource(match_id: str) -> str:
    """Detalle resumido de partido por ID."""
    data = await get_match_full_detail(match_id=match_id)
    return json.dumps(data, ensure_ascii=False)


def main() -> None:
    transport = settings.transport
    if transport == "streamable-http":
        _run_http_with_middleware()
        return
    try:
        mcp.run(transport=transport)
    finally:
        try:
            from flashscore_mcp.browser_pool import BrowserPool

            pool = BrowserPool.get_instance(settings)
            asyncio.run(pool.close())
        except Exception:
            pass


def _run_http_with_middleware() -> None:
    """Lanza uvicorn directamente con auth Bearer + /healthz montados.

    ``mcp.run(transport='streamable-http')`` construye una app Starlette
    nueva en cada llamada, asi que no podemos pre-modificarla. En su lugar
    construimos la app aqui, le anadimos middleware + ruta de salud,
    y la servimos con uvicorn manualmente.
    """
    import uvicorn
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    app = mcp.streamable_http_app()

    # ---- Warmup del browser en startup (solo modo fast) ----
    if (
        settings.sports_provider.strip().lower() in {"flashscore_fast", "fast"}
        and getattr(settings, "fast_warmup_on_startup", False)
    ):
        @app.on_event("startup")
        async def _warmup() -> None:  # pragma: no cover - integracion startup
            warm = getattr(provider, "warmup", None)
            if callable(warm):
                logger.info("Iniciando warmup del browser (modo fast)...")
                try:
                    await warm()
                except Exception as exc:
                    logger.warning("Warmup fallo: %s", exc)

    async def _healthz(_request: Any) -> Any:
        return JSONResponse({"status": "ok", "service": "flashscore-mcp"})

    expected_token = (settings.auth_token or "").strip()

    class _BearerAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Any, call_next: Any) -> Any:  # type: ignore[override]
            path = request.url.path or ""
            if path.startswith("/healthz") or not expected_token:
                return await call_next(request)
            header = request.headers.get("authorization", "")
            if not header.lower().startswith("bearer "):
                return JSONResponse({"error": "missing bearer token"}, status_code=401)
            received = header.split(" ", 1)[1].strip()
            if received != expected_token:
                return JSONResponse({"error": "invalid token"}, status_code=403)
            return await call_next(request)

    app.router.routes.insert(0, Route("/healthz", endpoint=_healthz, methods=["GET"]))
    app.add_middleware(_BearerAuthMiddleware)
    logger.info(
        "HTTP listo en %s:%s (auth=%s, healthz=ON)",
        settings.bind_host,
        settings.bind_port,
        "ON" if expected_token else "OFF",
    )

    try:
        uvicorn.run(
            app,
            host=settings.bind_host,
            port=settings.bind_port,
            log_level="info",
        )
    finally:
        try:
            from flashscore_mcp.browser_pool import BrowserPool

            pool = BrowserPool.get_instance(settings)
            asyncio.run(pool.close())
        except Exception:
            pass


if __name__ == "__main__":
    main()
