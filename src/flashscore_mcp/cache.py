from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


# Marcadores de estado por los que decidimos el TTL estratificado.
_FINISHED_TOKENS = (
    "final",
    "finalizado",
    "ft",
    "after pen",
    "termin",
    "cancel",
    "aplaz",
    "post",
    "susp",
    "aban",
)
_LIVE_TOKENS = (
    "vivo",
    "live",
    "1er",
    "2do",
    "1st",
    "2nd",
    "ht",
    "descanso",
    "medio",
    "et",
    "prol",
    "pen",
)


def select_ttl(status: str | None, *, live: int, scheduled: int, finished: int) -> int:
    """Elige TTL en segundos segun el estado del partido.

    - finalizado/cancelado: TTL largo (datos inmutables).
    - en vivo: TTL corto (datos cambian segundo a segundo).
    - programado o desconocido: TTL intermedio.
    """
    if not status:
        return scheduled
    text = status.strip().lower()
    if not text:
        return scheduled
    if any(token in text for token in _FINISHED_TOKENS):
        return finished
    if any(token in text for token in _LIVE_TOKENS):
        return live
    # Estados puramente numericos (minuto en vivo, ej. "32'") son partidos en vivo
    if any(ch.isdigit() for ch in text) and "'" in text:
        return live
    return scheduled


def select_ttl_from_item(
    item: Any,
    *,
    live: int,
    scheduled: int,
    finished: int,
    default: int,
) -> int:
    """Helper que inspecciona el atributo `.status` del item si existe."""
    status: str | None = None
    if item is None:
        return default
    if hasattr(item, "status"):
        status = getattr(item, "status", None)
    elif isinstance(item, dict):
        status = item.get("status")
    if status is None:
        return default
    return select_ttl(status, live=live, scheduled=scheduled, finished=finished)


@dataclass
class CacheEntry(Generic[T]):
    value: T
    created_at: float
    ttl_seconds: int

    @property
    def age_seconds(self) -> float:
        return time.monotonic() - self.created_at

    @property
    def is_stale(self) -> bool:
        return self.age_seconds > self.ttl_seconds


class AsyncTTLCache(Generic[T]):
    def __init__(self) -> None:
        self._items: dict[str, CacheEntry[T]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> CacheEntry[T] | None:
        async with self._lock:
            return self._items.get(key)

    async def set(self, key: str, value: T, ttl_seconds: int) -> CacheEntry[T]:
        entry = CacheEntry(value=value, created_at=time.monotonic(), ttl_seconds=ttl_seconds)
        async with self._lock:
            self._items[key] = entry
        return entry

    async def status(self) -> dict[str, object]:
        async with self._lock:
            return {
                "keys": sorted(self._items),
                "size": len(self._items),
                "entries": {
                    key: {
                        "age_seconds": round(entry.age_seconds, 3),
                        "ttl_seconds": entry.ttl_seconds,
                        "stale": entry.is_stale,
                    }
                    for key, entry in self._items.items()
                },
            }
