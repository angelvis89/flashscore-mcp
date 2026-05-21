from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


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
