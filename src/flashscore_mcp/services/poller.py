from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from flashscore_mcp.cache import AsyncTTLCache
from flashscore_mcp.config import Settings
from flashscore_mcp.models import LiveSnapshot, utc_now_iso
from flashscore_mcp.providers.base import SportsDataProvider


def live_cache_key(sport: str, league: str | None, live_only: bool) -> str:
    league_key = (league or "all").strip().lower()
    return f"live:{sport.strip().lower()}:{league_key}:{live_only}"


@dataclass
class PollerState:
    running: bool = False
    sport: str = "football"
    league: str | None = None
    live_only: bool = True
    interval_seconds: int = 5
    last_success_at: str | None = None
    last_error: str | None = None
    refresh_count: int = 0


class LivePoller:
    def __init__(
        self,
        *,
        cache: AsyncTTLCache[Any],
        provider: SportsDataProvider,
        settings: Settings,
    ) -> None:
        self.cache = cache
        self.provider = provider
        self.settings = settings
        self.state = PollerState(interval_seconds=settings.refresh_seconds)
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    def start(
        self,
        *,
        sport: str = "football",
        league: str | None = None,
        live_only: bool = True,
        interval_seconds: int | None = None,
    ) -> dict[str, Any]:
        if self._task and not self._task.done():
            return self.status()

        self._stop_event = asyncio.Event()
        self.state = PollerState(
            running=True,
            sport=sport,
            league=league,
            live_only=live_only,
            interval_seconds=max(1, interval_seconds or self.settings.refresh_seconds),
        )
        self._task = asyncio.create_task(self._run(), name="flashscore-live-poller")
        return self.status()

    async def stop(self) -> dict[str, Any]:
        if not self._task or self._task.done():
            self.state.running = False
            return self.status()

        self._stop_event.set()
        try:
            await asyncio.wait_for(self._task, timeout=5)
        except TimeoutError:
            self._task.cancel()
        self.state.running = False
        return self.status()

    def status(self) -> dict[str, Any]:
        return {
            "running": self.state.running and bool(self._task and not self._task.done()),
            "sport": self.state.sport,
            "league": self.state.league,
            "live_only": self.state.live_only,
            "interval_seconds": self.state.interval_seconds,
            "last_success_at": self.state.last_success_at,
            "last_error": self.state.last_error,
            "refresh_count": self.state.refresh_count,
        }

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self.refresh_once()
            except Exception:
                # El error queda en estado; el cache anterior se conserva.
                pass

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.state.interval_seconds,
                )
            except TimeoutError:
                continue
        self.state.running = False

    async def refresh_once(self) -> LiveSnapshot:
        try:
            matches = await self.provider.fetch_live_matches(
                sport=self.state.sport,
                league=self.state.league,
                live_only=self.state.live_only,
            )
            snapshot = LiveSnapshot(
                source=getattr(self.provider, "source_name", "sports_provider"),
                fetched_at=utc_now_iso(),
                cache_ttl_seconds=self.settings.cache_ttl_seconds,
                stale=False,
                items=matches,
            )
            await self.cache.set(
                live_cache_key(self.state.sport, self.state.league, self.state.live_only),
                snapshot,
                self.settings.cache_ttl_seconds,
            )
            self.state.last_success_at = snapshot.fetched_at
            self.state.last_error = None
            self.state.refresh_count += 1
            return snapshot
        except Exception as exc:
            self.state.last_error = str(exc)
            raise
