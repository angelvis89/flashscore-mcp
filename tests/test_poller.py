from __future__ import annotations

import asyncio

from flashscore_mcp.cache import AsyncTTLCache
from flashscore_mcp.config import Settings
from flashscore_mcp.providers.mock import MockSportsProvider
from flashscore_mcp.services.poller import LivePoller, live_cache_key


def test_refresh_once_populates_live_cache() -> None:
    async def scenario() -> int:
        cache = AsyncTTLCache()
        provider = MockSportsProvider()
        poller = LivePoller(cache=cache, provider=provider, settings=Settings())
        snapshot = await poller.refresh_once()
        entry = await cache.get(live_cache_key("football", None, True))
        assert entry is not None
        assert snapshot.source == "mock_sports_provider"
        return len(snapshot.items)

    assert asyncio.run(scenario()) == 2
