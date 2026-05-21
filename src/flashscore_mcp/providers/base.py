from __future__ import annotations

from typing import Protocol

from flashscore_mcp.models import LiveMatch, MatchDetail


class SportsDataProvider(Protocol):
    async def fetch_live_matches(
        self,
        *,
        sport: str = "football",
        league: str | None = None,
        live_only: bool = True,
    ) -> list[LiveMatch]:
        """Obtiene partidos en vivo o del dia desde la fuente configurada."""

    async def fetch_match_detail(self, match_id: str) -> LiveMatch | None:
        """Obtiene detalle de un partido por ID."""

    async def fetch_matches_by_date(
        self,
        *,
        date: str,
        sport: str = "football",
        league: str | None = None,
    ) -> list[LiveMatch]:
        """Obtiene partidos de una fecha ISO YYYY-MM-DD."""

    async def search_matches(
        self,
        *,
        query: str,
        date_from: str | None = None,
        date_to: str | None = None,
        sport: str = "football",
        league: str | None = None,
    ) -> list[LiveMatch]:
        """Busca partidos por texto en una o varias fechas."""

    async def fetch_match_full_detail(
        self,
        match_id: str,
        *,
        sections: list[str] | None = None,
    ) -> MatchDetail | None:
        """Obtiene detalle enriquecido de un partido por ID."""
