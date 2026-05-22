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
    if provider_name in {"flashscore_fast", "fast"}:
        # Import perezoso: solo carga httpx/BrowserPool si se pide el modo fast.
        from flashscore_mcp.providers.flashscore_fast import FlashscoreFastProvider

        return FlashscoreFastProvider(settings)
    if provider_name == "mock":
        return MockSportsProvider()
    raise ValueError(
        "SPORTS_PROVIDER invalido. Usa 'mock', 'flashscore' o 'flashscore_fast'."
    )
