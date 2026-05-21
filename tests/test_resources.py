from __future__ import annotations

import asyncio
import importlib.util
import json


def test_football_live_resource_returns_json() -> None:
    if importlib.util.find_spec("mcp") is None:
        return

    from flashscore_mcp.server import football_live_resource

    async def scenario() -> dict[str, object]:
        raw = await football_live_resource()
        return json.loads(raw)

    data = asyncio.run(scenario())
    assert data["source"] == "mock_sports_provider"
    assert isinstance(data["items"], list)
