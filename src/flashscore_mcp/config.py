from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_int(value: str | None, default: int, *, minimum: int | None = None) -> int:
    if value is None:
        result = default
    else:
        try:
            result = int(value)
        except ValueError:
            result = default
    if minimum is not None:
        return max(minimum, result)
    return result


@dataclass(frozen=True)
class Settings:
    sports_provider: str = "mock"
    base_url: str = "https://www.flashscore.pe/"
    headless: bool = True
    timeout_ms: int = 15_000
    refresh_seconds: int = 5
    cache_ttl_seconds: int = 8
    # TTL estratificada por estado del partido (segundos)
    ttl_live_seconds: int = 8
    ttl_scheduled_seconds: int = 60
    ttl_finished_seconds: int = 86_400
    max_watch_seconds: int = 120
    transport: str = "stdio"
    # Limites internos de concurrencia y rate-limit al scrapear Flashscore
    max_concurrent_pages: int = 3
    min_request_delay_ms: int = 0
    # Endurecimiento HTTP (solo activos cuando transport=streamable-http)
    auth_token: str | None = None
    cors_origins: str = "*"
    bind_host: str = "0.0.0.0"
    bind_port: int = 8000
    # ---- Modo FAST (FlashscoreFastProvider) ----
    # Numero de paginas paralelas para extraer secciones de fetch_match_full_detail.
    # 6 = una pagina por seccion (max velocidad, ~600MB RAM).
    fast_parallel_sections: int = 6
    # Path local donde se persiste el storage_state (cookies aceptadas) entre runs.
    storage_state_path: str = "/tmp/flashscore_state.json"
    # Si True, el server hace warmup del browser + cookies al startup (lifespan).
    fast_warmup_on_startup: bool = True
    # ---- Cache L3 estatico via GitHub Pages (publicado por precache.yml) ----
    # Ejemplo: https://angelvis89.github.io/flashscore-mcp
    # Si esta vacio, el provider Fast NO intenta cache estatico (cae directo a Playwright).
    static_cache_base_url: str = ""
    # Edad maxima aceptable del cache estatico (segundos). Mayor = mas hits, menos frescura.
    static_cache_max_age_seconds: int = 600
    # Timeout HTTP corto: si Pages no responde rapido, fallback a Playwright sin esperar.
    static_cache_timeout_seconds: float = 2.0

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            sports_provider=os.getenv("SPORTS_PROVIDER", cls.sports_provider),
            base_url=os.getenv("FLASHSCORE_BASE_URL", cls.base_url),
            headless=_as_bool(os.getenv("FLASHSCORE_HEADLESS"), cls.headless),
            timeout_ms=_as_int(os.getenv("FLASHSCORE_TIMEOUT_MS"), cls.timeout_ms, minimum=3_000),
            refresh_seconds=_as_int(
                os.getenv("FLASHSCORE_REFRESH_SECONDS"), cls.refresh_seconds, minimum=1
            ),
            cache_ttl_seconds=_as_int(
                os.getenv("FLASHSCORE_CACHE_TTL_SECONDS"), cls.cache_ttl_seconds, minimum=1
            ),
            ttl_live_seconds=_as_int(
                os.getenv("FLASHSCORE_TTL_LIVE_SECONDS"), cls.ttl_live_seconds, minimum=1
            ),
            ttl_scheduled_seconds=_as_int(
                os.getenv("FLASHSCORE_TTL_SCHEDULED_SECONDS"),
                cls.ttl_scheduled_seconds,
                minimum=1,
            ),
            ttl_finished_seconds=_as_int(
                os.getenv("FLASHSCORE_TTL_FINISHED_SECONDS"),
                cls.ttl_finished_seconds,
                minimum=1,
            ),
            max_watch_seconds=_as_int(
                os.getenv("FLASHSCORE_MAX_WATCH_SECONDS"), cls.max_watch_seconds, minimum=5
            ),
            transport=os.getenv("MCP_TRANSPORT", cls.transport),
            max_concurrent_pages=_as_int(
                os.getenv("FLASHSCORE_MAX_CONCURRENT_PAGES"),
                cls.max_concurrent_pages,
                minimum=1,
            ),
            min_request_delay_ms=_as_int(
                os.getenv("FLASHSCORE_MIN_DELAY_MS"), cls.min_request_delay_ms, minimum=0
            ),
            auth_token=os.getenv("MCP_AUTH_TOKEN") or None,
            cors_origins=os.getenv("MCP_CORS_ORIGINS", cls.cors_origins),
            bind_host=os.getenv("MCP_BIND_HOST", cls.bind_host),
            bind_port=_as_int(os.getenv("MCP_BIND_PORT"), cls.bind_port, minimum=1),
            fast_parallel_sections=_as_int(
                os.getenv("FLASHSCORE_FAST_PARALLEL_SECTIONS"),
                cls.fast_parallel_sections,
                minimum=1,
            ),
            storage_state_path=os.getenv(
                "FLASHSCORE_STORAGE_STATE_PATH", cls.storage_state_path
            ),
            fast_warmup_on_startup=_as_bool(
                os.getenv("FLASHSCORE_FAST_WARMUP"), cls.fast_warmup_on_startup
            ),
            static_cache_base_url=os.getenv(
                "FLASHSCORE_STATIC_CACHE_URL", cls.static_cache_base_url
            ),
            static_cache_max_age_seconds=_as_int(
                os.getenv("FLASHSCORE_STATIC_CACHE_MAX_AGE"),
                cls.static_cache_max_age_seconds,
                minimum=10,
            ),
            static_cache_timeout_seconds=float(
                os.getenv(
                    "FLASHSCORE_STATIC_CACHE_TIMEOUT",
                    str(cls.static_cache_timeout_seconds),
                )
            ),
        )
