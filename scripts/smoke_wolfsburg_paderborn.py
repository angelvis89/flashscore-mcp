from __future__ import annotations

import asyncio
import json

from flashscore_mcp.config import Settings
from flashscore_mcp.providers.flashscore import FlashscorePlaywrightProvider

MATCH_ID = "K8bh3OkJ"


def _side(value: object, side: str) -> list:
    """Devuelve la lista de jugadores para `side` ('home' o 'away').

    Tolera tanto el nuevo formato (dict con claves home/away) como el viejo
    (lista plana de strings caida del parser de texto).
    """
    if isinstance(value, dict):
        items = value.get(side, [])
        return list(items) if isinstance(items, list) else []
    if isinstance(value, list):
        return list(value) if side == "home" else []
    return []


async def main() -> None:
    settings = Settings.from_env()
    provider = FlashscorePlaywrightProvider(settings)
    detail = await provider.fetch_match_full_detail(
        MATCH_ID,
        sections=["summary", "lineups", "odds", "h2h", "preview"],
    )
    if detail is None:
        raise SystemExit("No se encontro el partido K8bh3OkJ")

    sections = detail.sections
    summary = sections["summary"].data
    lineups = sections["lineups"].data
    odds = sections["odds"].data
    h2h = sections["h2h"].data

    result = {
        "match": {
            "home": detail.match.home,
            "away": detail.match.away,
            "status": detail.match.status,
            "scheduled_at": detail.match.scheduled_at,
            "url": detail.match.url,
        },
        "summary": {
            "available": sections["summary"].available,
            "preview_lines": len(summary.get("preview", [])),
            "absences_lines": len(summary.get("absences", [])),
            "additional_info_lines": len(summary.get("additional_info", [])),
            "first_preview": summary.get("preview", [])[:5],
        },
        "lineups": {
            "available": sections["lineups"].available,
            "formations": lineups.get("formations"),
            "starting_home_count": len(_side(lineups.get("starting_lineups"), "home")),
            "starting_away_count": len(_side(lineups.get("starting_lineups"), "away")),
            "substitutes_home_count": len(_side(lineups.get("substitutes"), "home")),
            "substitutes_away_count": len(_side(lineups.get("substitutes"), "away")),
            "absent_home_count": len(_side(lineups.get("absent_players"), "home")),
            "absent_away_count": len(_side(lineups.get("absent_players"), "away")),
            "coaches_home": _side(lineups.get("coaches"), "home"),
            "coaches_away": _side(lineups.get("coaches"), "away"),
            "starting_home_sample": _side(lineups.get("starting_lineups"), "home")[:3],
            "absent_home_sample": _side(lineups.get("absent_players"), "home")[:3],
            "fallback": lineups.get("fallback"),
        },
        "odds": {
            "available": sections["odds"].available,
            "markets_available": [
                key for key, value in odds.get("markets", {}).items() if value.get("available")
            ],
            "one_x_two_sample": odds.get("markets", {}).get("1x2", {}).get("lines", [])[:24],
            "recommendations": odds.get("best_recommendations", []),
        },
        "h2h": {
            "available": sections["h2h"].available,
            "head_to_head_lines": len(h2h.get("head_to_head", [])),
            "head_to_head_sample": h2h.get("head_to_head", [])[:20],
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
