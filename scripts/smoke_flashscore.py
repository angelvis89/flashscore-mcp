from __future__ import annotations

import asyncio
import os

from flashscore_mcp.config import Settings
from flashscore_mcp.providers.flashscore import FlashscorePlaywrightProvider


async def main() -> None:
    os.environ.setdefault("SPORTS_PROVIDER", "flashscore")
    os.environ.setdefault("FLASHSCORE_TIMEOUT_MS", "10000")
    provider = FlashscorePlaywrightProvider(Settings.from_env())
    matches = await provider.fetch_live_matches(live_only=False)
    print(f"matches={len(matches)}")
    if matches:
        print(matches[0].to_dict())


if __name__ == "__main__":
    asyncio.run(main())
