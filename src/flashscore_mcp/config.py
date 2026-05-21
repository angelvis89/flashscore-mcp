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
        )
