from __future__ import annotations

import asyncio
from datetime import date, timedelta

from flashscore_mcp.config import Settings
from flashscore_mcp.providers.flashscore import FlashscorePlaywrightProvider


def print_match(label: str, matches: list) -> str | None:
    print(f"{label}: total={len(matches)}")
    if not matches:
        return None
    match = matches[0]
    print(f"{label}: first={match.match_id} {match.home} vs {match.away} {match.scheduled_at}")
    print(f"{label}: url={match.url}")
    return match.match_id


async def main() -> None:
    settings = Settings.from_env()
    provider = FlashscorePlaywrightProvider(settings)
    today = date.today()

    past = await provider.fetch_matches_by_date(date=(today - timedelta(days=1)).isoformat())
    today_matches = await provider.fetch_matches_by_date(date=today.isoformat())
    future = await provider.fetch_matches_by_date(date=(today + timedelta(days=1)).isoformat())

    print_match("past", past)
    match_id = print_match("today", today_matches)
    print_match("future", future)

    if match_id:
        detail = await provider.fetch_match_full_detail(
            match_id,
            sections=["summary", "statistics", "lineups", "odds", "h2h", "preview"],
        )
        if detail:
            payload = detail.to_dict()
            print(f"detail: match={payload['match']['home']} vs {payload['match']['away']}")
            for name, section in payload["sections"].items():
                raw_text = section.get("raw_text") or ""
                data = section.get("data") or {}
                print(
                    f"detail:{name}: available={section['available']} "
                    f"raw_chars={len(raw_text)} data_keys={list(data.keys())}"
                )


if __name__ == "__main__":
    asyncio.run(main())
