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
    max_watch_seconds: int = 120
    transport: str = "stdio"

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
            max_watch_seconds=_as_int(
                os.getenv("FLASHSCORE_MAX_WATCH_SECONDS"), cls.max_watch_seconds, minimum=5
            ),
            transport=os.getenv("MCP_TRANSPORT", cls.transport),
        )
