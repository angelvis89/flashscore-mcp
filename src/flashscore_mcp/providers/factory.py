from __future__ import annotations

from flashscore_mcp.config import Settings
from flashscore_mcp.providers import (
    FlashscorePlaywrightProvider,
    MockSportsProvider,
    SportsDataProvider,
)


def build_provider(settings: Settings) -> SportsDataProvider:
    provider_name = settings.sports_provider.strip().lower()
    if provider_name == "flashscore":
        return FlashscorePlaywrightProvider(settings)
    if provider_name == "mock":
        return MockSportsProvider()
    raise ValueError(
        "SPORTS_PROVIDER invalido. Usa 'mock' para pruebas o 'flashscore' para Playwright."
    )
