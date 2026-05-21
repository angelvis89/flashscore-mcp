from __future__ import annotations

from flashscore_mcp.config import Settings
from flashscore_mcp.providers.flashscore import FlashscorePlaywrightProvider
from flashscore_mcp.services.poller import live_cache_key


def test_settings_from_env_parses_values(monkeypatch) -> None:
    monkeypatch.setenv("SPORTS_PROVIDER", "mock")
    monkeypatch.setenv("FLASHSCORE_HEADLESS", "false")
    monkeypatch.setenv("FLASHSCORE_REFRESH_SECONDS", "2")
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")

    settings = Settings.from_env()

    assert settings.sports_provider == "mock"
    assert settings.headless is False
    assert settings.refresh_seconds == 2
    assert settings.transport == "stdio"


def test_live_cache_key_normalizes_values() -> None:
    assert live_cache_key(" Football ", " Liga 1 ", True) == "live:football:liga 1:True"


def test_flashscore_match_id_normalization() -> None:
    provider = FlashscorePlaywrightProvider(Settings())
    assert provider._normalize_match_id("g_1_W8mj7MDD") == "W8mj7MDD"
