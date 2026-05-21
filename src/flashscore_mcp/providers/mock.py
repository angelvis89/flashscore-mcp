from __future__ import annotations

from flashscore_mcp.models import LiveMatch, MatchDetail, MatchScore, MatchSection, utc_now_iso


class MockSportsProvider:
    """Proveedor deterministico para probar el MCP sin navegador ni red."""

    source_name = "mock_sports_provider"

    async def fetch_live_matches(
        self,
        *,
        sport: str = "football",
        league: str | None = None,
        live_only: bool = True,
    ) -> list[LiveMatch]:
        matches = [
            LiveMatch(
                match_id="mock-alianza-u",
                home="Alianza Lima",
                away="Universitario",
                score=MatchScore(home="1", away="1"),
                status="Segundo tiempo",
                minute="67'",
                league="Liga 1 Peru",
                country="Peru",
                scheduled_at="2026-05-21T20:00:00-05:00",
                favorite_available=True,
                betting_available=True,
                tv_available=True,
                url="mock://match/mock-alianza-u",
            ),
            LiveMatch(
                match_id="mock-cristal-melgar",
                home="Sporting Cristal",
                away="Melgar",
                score=MatchScore(home="2", away="0"),
                status="Primer tiempo",
                minute="38'",
                league="Liga 1 Peru",
                country="Peru",
                scheduled_at="2026-05-22T15:00:00-05:00",
                favorite_available=True,
                betting_available=True,
                url="mock://match/mock-cristal-melgar",
            ),
        ]
        if league:
            needle = league.lower()
            matches = [match for match in matches if needle in (match.league or "").lower()]
        return matches

    async def fetch_match_detail(self, match_id: str) -> LiveMatch | None:
        for match in await self.fetch_live_matches(live_only=False):
            if match.match_id == match_id:
                return match
        return None

    async def fetch_matches_by_date(
        self,
        *,
        date: str,
        sport: str = "football",
        league: str | None = None,
    ) -> list[LiveMatch]:
        matches = await self.fetch_live_matches(sport=sport, league=league, live_only=False)
        return [match for match in matches if (match.scheduled_at or "").startswith(date)]

    async def search_matches(
        self,
        *,
        query: str,
        date_from: str | None = None,
        date_to: str | None = None,
        sport: str = "football",
        league: str | None = None,
    ) -> list[LiveMatch]:
        needle = query.lower()
        matches = await self.fetch_live_matches(sport=sport, league=league, live_only=False)
        return [
            match
            for match in matches
            if needle in f"{match.home} {match.away} {match.league}".lower()
        ]

    async def fetch_match_full_detail(
        self,
        match_id: str,
        *,
        sections: list[str] | None = None,
    ) -> MatchDetail | None:
        match = await self.fetch_match_detail(match_id)
        if match is None:
            return None
        requested = sections or ["summary", "statistics", "lineups", "odds", "h2h"]
        section_data = {
            "summary": MatchSection(
                name="summary",
                available=True,
                data={"events": [{"minute": "67'", "type": "score", "raw_text": "Partido mock"}]},
            ),
            "statistics": MatchSection(
                name="statistics",
                available=True,
                data={
                    "stats": [
                        {"name": "Ataques", "home": "64", "away": "51"},
                        {"name": "Corners", "home": "5", "away": "3"},
                        {"name": "Tarjetas amarillas", "home": "2", "away": "1"},
                    ]
                },
            ),
            "lineups": MatchSection(name="lineups", available=False),
            "odds": MatchSection(
                name="odds",
                available=True,
                data={
                    "markets": [{"name": "1X2", "home": "2.10", "draw": "3.25", "away": "3.60"}],
                    "most_probable_pick": "home",
                },
            ),
            "h2h": MatchSection(name="h2h", available=True, raw_text="Historial mock"),
        }
        return MatchDetail(
            match=match,
            fetched_at=utc_now_iso(),
            source=self.source_name,
            sections={key: section_data[key] for key in requested if key in section_data},
        )
