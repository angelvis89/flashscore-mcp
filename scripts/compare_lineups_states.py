"""Compara la extraccion de alineaciones entre un partido programado
(que aun no comienza) y otro en vivo, para Elvis verifique que el flujo
funciona en ambos estados y como varian los datos disponibles.

Estrategia:
1. Obtener los partidos del dia con FlashscoreProvider.fetch_live_scores().
2. Categorizar por status (programado vs en vivo vs finalizado).
3. Tomar el primero programado cuya hora sea < 90 minutos en el futuro
   (las alineaciones suelen aparecer ~60 min antes).
4. Tomar el primero en vivo.
5. Para ambos ejecutar fetch_match_full_detail y resumir.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from typing import Any

from flashscore_mcp.config import Settings
from flashscore_mcp.providers.flashscore import FlashscorePlaywrightProvider


SCHEDULED_PATTERN = re.compile(r"^\d{1,2}:\d{2}$")  # ej "20:30"


def categorize(status: str | None) -> str:
    text = (status or "").strip().lower()
    if not text:
        return "unknown"
    if SCHEDULED_PATTERN.match(text):
        return "scheduled"
    keywords_live = ["1er tiempo", "2do tiempo", "descanso", "min", "'", "en vivo"]
    if any(k in text for k in keywords_live):
        return "live"
    if any(k in text for k in ["finalizado", "ft", "terminado", "after pen", "ap"]):
        return "finished"
    if any(k in text for k in ["pospuesto", "cancelado", "aplazado", "suspendido"]):
        return "other"
    return "unknown"


def _side(value: object, side: str) -> list:
    if isinstance(value, dict):
        items = value.get(side, [])
        return list(items) if isinstance(items, list) else []
    if isinstance(value, list) and side == "home":
        return list(value)
    return []


def summarize_detail(detail: Any) -> dict[str, Any]:
    sections = detail.sections
    summary = sections.get("summary")
    lineups = sections.get("lineups")
    odds = sections.get("odds")
    h2h = sections.get("h2h")
    summary_data = summary.data if summary else {}
    lineups_data = lineups.data if lineups else {}
    odds_data = odds.data if odds else {}
    h2h_data = h2h.data if h2h else {}
    return {
        "match": {
            "home": detail.match.home,
            "away": detail.match.away,
            "status": detail.match.status,
            "scheduled_at": detail.match.scheduled_at,
            "league": detail.match.league,
            "country": detail.match.country,
            "url": detail.match.url,
        },
        "sections_available": {
            "summary": bool(summary and summary.available),
            "lineups": bool(lineups and lineups.available),
            "odds": bool(odds and odds.available),
            "h2h": bool(h2h and h2h.available),
        },
        "summary_keys_with_data": [
            k
            for k, v in (summary_data or {}).items()
            if isinstance(v, list) and v
        ],
        "summary_preview_lines": len((summary_data or {}).get("preview", []) or []),
        "summary_absences_lines": len((summary_data or {}).get("absences", []) or []),
        "lineups": {
            "formations": lineups_data.get("formations") if isinstance(lineups_data, dict) else None,
            "starting_home": len(_side(lineups_data.get("starting_lineups") if isinstance(lineups_data, dict) else None, "home")),
            "starting_away": len(_side(lineups_data.get("starting_lineups") if isinstance(lineups_data, dict) else None, "away")),
            "subs_home": len(_side(lineups_data.get("substitutes") if isinstance(lineups_data, dict) else None, "home")),
            "subs_away": len(_side(lineups_data.get("substitutes") if isinstance(lineups_data, dict) else None, "away")),
            "absent_home": len(_side(lineups_data.get("absent_players") if isinstance(lineups_data, dict) else None, "home")),
            "absent_away": len(_side(lineups_data.get("absent_players") if isinstance(lineups_data, dict) else None, "away")),
            "coaches_home": [c.get("name") for c in _side(lineups_data.get("coaches") if isinstance(lineups_data, dict) else None, "home") if isinstance(c, dict)],
            "coaches_away": [c.get("name") for c in _side(lineups_data.get("coaches") if isinstance(lineups_data, dict) else None, "away") if isinstance(c, dict)],
            "fallback": lineups_data.get("fallback") if isinstance(lineups_data, dict) else None,
            "starting_home_sample_names": [
                p.get("name") for p in _side(lineups_data.get("starting_lineups") if isinstance(lineups_data, dict) else None, "home")[:5]
                if isinstance(p, dict)
            ],
            "absent_home_sample": [
                {"name": p.get("name"), "reason": p.get("reason")}
                for p in _side(lineups_data.get("absent_players") if isinstance(lineups_data, dict) else None, "home")[:3]
                if isinstance(p, dict)
            ],
        },
        "odds_markets_available": [
            k for k, v in (odds_data.get("markets", {}) or {}).items()
            if isinstance(v, dict) and v.get("available")
        ],
        "h2h_lines": len((h2h_data or {}).get("head_to_head", []) or []),
    }


async def main() -> None:
    settings = Settings.from_env()
    provider = FlashscorePlaywrightProvider(settings)

    print("Descargando partidos del dia...")
    matches = await provider.fetch_live_matches()
    print(f"Total partidos: {len(matches)}")

    buckets: dict[str, list] = {"scheduled": [], "live": [], "finished": [], "unknown": [], "other": []}
    for m in matches:
        buckets[categorize(m.status)].append(m)

    print(
        "Por estado: "
        + ", ".join(f"{k}={len(v)}" for k, v in buckets.items() if v)
    )

    # Mostrar muestra de unknown para entender formato
    print("\nMuestra status 'unknown' (top 10):")
    for m in buckets["unknown"][:10]:
        print(f"  - status={m.status!r:<20} | {m.home} vs {m.away} | mid={m.match_id}")

    # Imprimir muestra para que Elvis vea opciones
    print("\nProgramados (top 10, en orden recibido):")
    for m in buckets["scheduled"][:10]:
        print(f"  - {m.status:>5} | {m.country or '?':<15} | {m.league or '?':<25} | {m.home} vs {m.away} | mid={m.match_id}")
    print("\nEn vivo (top 5):")
    for m in buckets["live"][:5]:
        print(f"  - {m.status:>10} | {m.country or '?':<15} | {m.league or '?':<25} | {m.home} vs {m.away} | mid={m.match_id}")

    # Elegir candidatos
    now = datetime.now()

    def hours_until(m) -> float | None:
        # status formato "HH:MM"
        if not m.status or not SCHEDULED_PATTERN.match(m.status.strip()):
            return None
        try:
            hh, mm = map(int, m.status.strip().split(":"))
        except ValueError:
            return None
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        delta = (target - now).total_seconds() / 3600.0
        return delta

    # Programado: que falte entre 0 y 2h (alineaciones suelen estar 1h antes)
    scheduled_candidates = []
    for m in buckets["scheduled"]:
        h = hours_until(m)
        if h is not None and 0 <= h <= 2:
            scheduled_candidates.append((h, m))
    scheduled_candidates.sort(key=lambda x: x[0])
    scheduled_pick = scheduled_candidates[0][1] if scheduled_candidates else (buckets["scheduled"][0] if buckets["scheduled"] else None)
    live_pick = buckets["live"][0] if buckets["live"] else None

    print("\n=== SELECCION ===")
    if scheduled_pick:
        print(f"PROGRAMADO: {scheduled_pick.home} vs {scheduled_pick.away} ({scheduled_pick.status}) mid={scheduled_pick.match_id}")
    else:
        print("PROGRAMADO: ninguno disponible")
    if live_pick:
        print(f"EN VIVO:    {live_pick.home} vs {live_pick.away} ({live_pick.status}) mid={live_pick.match_id}")
    else:
        print("EN VIVO: ninguno disponible")

    out: dict[str, Any] = {}

    for label, pick in (("scheduled", scheduled_pick), ("live", live_pick)):
        if not pick:
            out[label] = None
            continue
        print(f"\nObteniendo detalle ({label}) de {pick.match_id}...")
        try:
            detail = await provider.fetch_match_full_detail(
                pick.match_id,
                sections=["summary", "lineups", "odds", "h2h"],
            )
        except Exception as exc:
            out[label] = {"error": str(exc), "match_id": pick.match_id}
            continue
        if detail is None:
            out[label] = {"error": "detail none", "match_id": pick.match_id}
            continue
        out[label] = summarize_detail(detail)

    print("\n=== RESUMEN COMPARATIVO ===")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
