"""Compara la extraccion de alineaciones entre dos partidos especificos
(uno programado y uno en vivo) pasados como argumentos.

Uso:
    python scripts\\compare_two_matches.py SCHEDULED_MID LIVE_MID

Por ejemplo, con la cartelera del 21/05/2026:
    SCHEDULED_MID candidatos (Libertadores noche):
        8AfJcokS  Atletico-MG vs Cienciano
        U3mgFzcl  Racing Club vs Caracas
        KC8HhsYr  Penarol vs Corinthians
    LIVE_MID candidatos (en vivo):
        K8bh3OkJ  Wolfsburgo vs Paderborn (Bundesliga)
        6150EZrn  Al Fayha vs Al-Hilal (Saudi)
"""
from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from flashscore_mcp.config import Settings
from flashscore_mcp.providers.flashscore import FlashscorePlaywrightProvider


def _side(value: object, side: str) -> list:
    if isinstance(value, dict):
        items = value.get(side, [])
        return list(items) if isinstance(items, list) else []
    if isinstance(value, list) and side == "home":
        return list(value)
    return []


def summarize(detail: Any) -> dict[str, Any]:
    sections = detail.sections
    s = sections.get("summary")
    l = sections.get("lineups")
    o = sections.get("odds")
    h = sections.get("h2h")
    sdata = s.data if s else {}
    ldata = l.data if l else {}
    odata = o.data if o else {}
    hdata = h.data if h else {}
    return {
        "match": {
            "home": detail.match.home,
            "away": detail.match.away,
            "status": detail.match.status,
            "scheduled_at": detail.match.scheduled_at,
            "league": detail.match.league,
            "url": detail.match.url,
        },
        "sections_available": {
            "summary": bool(s and s.available),
            "lineups": bool(l and l.available),
            "odds": bool(o and o.available),
            "h2h": bool(h and h.available),
        },
        "summary": {
            "preview_lines": len((sdata or {}).get("preview", []) or []),
            "absences_lines": len((sdata or {}).get("absences", []) or []),
            "tv_lines": len((sdata or {}).get("tv", []) or []),
            "additional_info_lines": len((sdata or {}).get("additional_info", []) or []),
            "first_preview_lines": (sdata or {}).get("preview", [])[:3],
            "first_absences": (sdata or {}).get("absences", [])[:5],
        },
        "lineups": {
            "formations": ldata.get("formations") if isinstance(ldata, dict) else None,
            "starting_home": len(_side(ldata.get("starting_lineups") if isinstance(ldata, dict) else None, "home")),
            "starting_away": len(_side(ldata.get("starting_lineups") if isinstance(ldata, dict) else None, "away")),
            "subs_home": len(_side(ldata.get("substitutes") if isinstance(ldata, dict) else None, "home")),
            "subs_away": len(_side(ldata.get("substitutes") if isinstance(ldata, dict) else None, "away")),
            "absent_home": len(_side(ldata.get("absent_players") if isinstance(ldata, dict) else None, "home")),
            "absent_away": len(_side(ldata.get("absent_players") if isinstance(ldata, dict) else None, "away")),
            "coaches": {
                "home": [c.get("name") for c in _side(ldata.get("coaches") if isinstance(ldata, dict) else None, "home") if isinstance(c, dict)],
                "away": [c.get("name") for c in _side(ldata.get("coaches") if isinstance(ldata, dict) else None, "away") if isinstance(c, dict)],
            },
            "fallback": ldata.get("fallback") if isinstance(ldata, dict) else None,
            "starting_home_sample": [
                {"n": p.get("number"), "name": p.get("name"), "roles": p.get("roles"), "country": p.get("country")}
                for p in _side(ldata.get("starting_lineups") if isinstance(ldata, dict) else None, "home")[:4]
                if isinstance(p, dict)
            ],
            "absent_sample": [
                {"name": p.get("name"), "reason": p.get("reason"), "country": p.get("country")}
                for p in _side(ldata.get("absent_players") if isinstance(ldata, dict) else None, "home")[:3]
                if isinstance(p, dict)
            ],
        },
        "odds_markets_available": [
            k for k, v in (odata.get("markets", {}) or {}).items()
            if isinstance(v, dict) and v.get("available")
        ],
        "h2h_lines": len((hdata or {}).get("head_to_head", []) or []),
    }


async def main() -> None:
    if len(sys.argv) >= 3:
        scheduled_mid, live_mid = sys.argv[1], sys.argv[2]
    else:
        # defaults para hoy 21/05/2026
        scheduled_mid = "8AfJcokS"  # Atletico-MG vs Cienciano (Libertadores)
        live_mid = "K8bh3OkJ"  # Wolfsburgo vs Paderborn (Bundesliga, en vivo)

    settings = Settings.from_env()
    provider = FlashscorePlaywrightProvider(settings)

    out: dict[str, Any] = {}
    for label, mid in (("scheduled", scheduled_mid), ("live", live_mid)):
        print(f"\n[{label}] obteniendo detalle de mid={mid} ...")
        try:
            detail = await provider.fetch_match_full_detail(
                mid, sections=["summary", "lineups", "odds", "h2h"]
            )
        except Exception as exc:
            out[label] = {"error": str(exc), "mid": mid}
            continue
        if detail is None:
            out[label] = {"error": "not found", "mid": mid}
            continue
        out[label] = summarize(detail)

    print("\n=== COMPARATIVA ===")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
