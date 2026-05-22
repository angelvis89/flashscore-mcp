"""Tests del FlashscoreFastProvider sin tocar Playwright real.

Cubre:
- _items_from_payload deserializa correctamente.
- _try_static_cache: HIT fresco, MISS por edad, MISS por 404.
- factory.build_provider("flashscore_fast") devuelve la clase correcta.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from flashscore_mcp.config import Settings
from flashscore_mcp.models import LiveMatch
from flashscore_mcp.providers.factory import build_provider
from flashscore_mcp.providers.flashscore_fast import FlashscoreFastProvider


def _settings(**overrides) -> Settings:
    base = dict(
        sports_provider="flashscore_fast",
        static_cache_base_url="https://example.github.io/flashscore-mcp",
        static_cache_max_age_seconds=600,
        static_cache_timeout_seconds=1.0,
        storage_state_path="",
        fast_warmup_on_startup=False,
        fast_parallel_sections=2,
    )
    base.update(overrides)
    return Settings(**base)


def test_factory_returns_fast_provider():
    provider = build_provider(_settings())
    assert isinstance(provider, FlashscoreFastProvider)
    assert provider.source_name == "flashscore_fast"


def test_items_from_payload_round_trip():
    provider = FlashscoreFastProvider(_settings())
    payload = {
        "items": [
            {
                "match_id": "ABC123",
                "home": "Boca",
                "away": "River",
                "score": {"home": "1", "away": "0"},
                "status": "LIVE",
                "minute": "45'",
                "league": "Liga",
                "country": "Argentina",
                "url": "https://x/match/ABC123/",
                "scheduled_at": "2026-05-22T20:00:00-05:00",
                "favorite_available": True,
                "betting_available": False,
                "tv_available": True,
                "raw_text": "raw",
            }
        ]
    }
    items = provider._items_from_payload(payload)
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, LiveMatch)
    assert item.match_id == "ABC123"
    assert item.score.home == "1"
    assert item.tv_available is True


def test_items_from_payload_ignora_items_invalidos():
    provider = FlashscoreFastProvider(_settings())
    payload = {"items": [{}, {"match_id": "X", "home": "A", "away": "B"}]}
    items = provider._items_from_payload(payload)
    assert len(items) == 1
    assert items[0].match_id == "X"


def test_cache_paths():
    live = FlashscoreFastProvider._live_cache_path
    by_date = FlashscoreFastProvider._date_cache_path
    detail = FlashscoreFastProvider._detail_cache_path
    assert live("football", None, True) == "live/football-live.json"
    assert live("football", None, False) == "live/football-all.json"
    assert live("football", "La Liga", True) == "live/football-la-liga-live.json"
    assert by_date("football", "2026-05-22", None) == "by-date/football-2026-05-22.json"
    assert detail("ABC123") == "detail/ABC123.json"


@pytest.mark.asyncio
async def test_try_static_cache_hit_fresco():
    provider = FlashscoreFastProvider(_settings())
    fresh_iso = datetime.now(timezone.utc).isoformat()
    fake_payload = {"fetched_at": fresh_iso, "items": []}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value=fake_payload)

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    provider._http = mock_client

    result = await provider._try_static_cache("live/football-live.json")
    assert result == fake_payload
    mock_client.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_try_static_cache_miss_por_edad():
    provider = FlashscoreFastProvider(_settings(static_cache_max_age_seconds=60))
    stale_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    fake_payload = {"fetched_at": stale_iso, "items": []}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value=fake_payload)

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    provider._http = mock_client

    result = await provider._try_static_cache("live/football-live.json")
    assert result is None


@pytest.mark.asyncio
async def test_try_static_cache_miss_por_404():
    provider = FlashscoreFastProvider(_settings())
    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    provider._http = mock_client

    result = await provider._try_static_cache("detail/inexistente.json")
    assert result is None


@pytest.mark.asyncio
async def test_try_static_cache_sin_base_url_no_llama():
    provider = FlashscoreFastProvider(_settings(static_cache_base_url=""))
    mock_client = AsyncMock()
    provider._http = mock_client
    result = await provider._try_static_cache("anything.json")
    assert result is None
    mock_client.get.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_live_matches_usa_cache_primero():
    provider = FlashscoreFastProvider(_settings())
    fresh_iso = datetime.now(timezone.utc).isoformat()
    fake_payload = {
        "fetched_at": fresh_iso,
        "items": [{"match_id": "X1", "home": "A", "away": "B"}],
    }
    with patch.object(provider, "_try_static_cache", new=AsyncMock(return_value=fake_payload)):
        # No debe llamar a Playwright porque hay cache hit
        with patch.object(provider, "_extract_rows_pooled", new=AsyncMock()) as mock_extract:
            result = await provider.fetch_live_matches(sport="football", live_only=True)
            mock_extract.assert_not_called()
    assert len(result) == 1
    assert result[0].match_id == "X1"
