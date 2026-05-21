from __future__ import annotations

import asyncio

from flashscore_mcp.cache import AsyncTTLCache


def test_cache_entry_becomes_stale() -> None:
    async def scenario() -> bool:
        cache: AsyncTTLCache[str] = AsyncTTLCache()
        entry = await cache.set("a", "valor", ttl_seconds=1)
        assert not entry.is_stale
        await asyncio.sleep(1.05)
        return entry.is_stale

    assert asyncio.run(scenario())


def test_cache_status_lists_keys() -> None:
    async def scenario() -> dict[str, object]:
        cache: AsyncTTLCache[str] = AsyncTTLCache()
        await cache.set("live:football", "ok", ttl_seconds=10)
        return await cache.status()

    status = asyncio.run(scenario())
    assert status["size"] == 1
    assert status["keys"] == ["live:football"]
