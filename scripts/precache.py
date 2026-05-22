"""Pre-cache para GitHub Actions: scrapea Flashscore y publica JSON estaticos.

Ejecutado por ``.github/workflows/precache.yml`` cada 5 min en ventana activa.
Escribe a ``./public/`` (luego pusheado a rama ``data`` y servido via Pages).

Estructura de salida:
    public/live/football-live.json       (partidos en vivo)
    public/live/football-all.json        (todos los del dia)
    public/by-date/football-YYYY-MM-DD.json
    public/detail/<match_id>.json        (top-N partidos)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from flashscore_mcp.config import Settings  # noqa: E402
from flashscore_mcp.models import LiveSnapshot, utc_now_iso  # noqa: E402
from flashscore_mcp.providers.flashscore import FlashscorePlaywrightProvider  # noqa: E402

OUTPUT_DIR = Path(os.getenv("PRECACHE_OUTPUT_DIR", "./public"))
TOP_N = int(os.getenv("PRECACHE_TOP_N", "20"))
DATE_WINDOW_DAYS = int(os.getenv("PRECACHE_DATE_DAYS", "1"))  # hoy +- 1


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  -> {path} ({len(json.dumps(payload))} bytes)")


def _snapshot_payload(items, source: str, ttl: int = 300) -> dict:
    snap = LiveSnapshot(
        source=source,
        fetched_at=utc_now_iso(),
        cache_ttl_seconds=ttl,
        stale=False,
        items=items,
    )
    return snap.to_dict()


async def main() -> None:
    # Forzar configuracion para Actions (sin cache estatico recursivo)
    os.environ.setdefault("SPORTS_PROVIDER", "flashscore")
    os.environ.setdefault("FLASHSCORE_HEADLESS", "1")
    os.environ.setdefault("FLASHSCORE_MAX_CONCURRENT_PAGES", "3")
    settings = Settings.from_env()

    # IMPORTANTE: usamos el provider BASELINE aqui (no fast) para evitar dependencia
    # circular con el cache L3 que este mismo script va a generar.
    provider = FlashscorePlaywrightProvider(settings)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"== precache empezando -> {OUTPUT_DIR.absolute()}")

    # 1) live (en vivo + todos)
    print("[1/3] live...")
    live = await provider.fetch_live_matches(sport="football", live_only=True)
    _write_json(
        OUTPUT_DIR / "live" / "football-live.json",
        _snapshot_payload(live, "precache_live", ttl=300),
    )
    all_today = await provider.fetch_live_matches(sport="football", live_only=False)
    _write_json(
        OUTPUT_DIR / "live" / "football-all.json",
        _snapshot_payload(all_today, "precache_all", ttl=300),
    )

    # 2) by-date (hoy +- DATE_WINDOW_DAYS)
    print(f"[2/3] by-date (+-{DATE_WINDOW_DAYS} dias)...")
    today = datetime.now(timezone.utc).date()
    for offset in range(-DATE_WINDOW_DAYS, DATE_WINDOW_DAYS + 1):
        day = today + timedelta(days=offset)
        iso = day.isoformat()
        try:
            day_matches = await provider.fetch_matches_by_date(date=iso, sport="football")
            _write_json(
                OUTPUT_DIR / "by-date" / f"football-{iso}.json",
                _snapshot_payload(day_matches, f"precache_date_{iso}", ttl=3600),
            )
        except Exception as exc:
            print(f"  ! by-date {iso} fallo: {exc}")

    # 3) detail top-N (heuristica: priorizar live, luego con TV, luego primeros del dia)
    print(f"[3/3] detail top-{TOP_N}...")
    candidates = list({m.match_id: m for m in (live + all_today)}.values())
    # Score simple: live > tv > resto
    def _score(m):
        s = 0
        if m.status and any(x in str(m.status).lower() for x in ("'", "live", "ht")):
            s += 100
        if m.tv_available:
            s += 10
        if m.betting_available:
            s += 5
        return s
    candidates.sort(key=_score, reverse=True)
    top = candidates[:TOP_N]
    print(f"  -> {len(top)} matches seleccionados")

    sem = asyncio.Semaphore(2)  # max 2 details en paralelo para no saturar runner

    async def _one_detail(match):
        async with sem:
            try:
                full = await provider.fetch_match_full_detail(match.match_id)
                if full is None:
                    return
                _write_json(
                    OUTPUT_DIR / "detail" / f"{match.match_id}.json",
                    full.to_dict(),
                )
            except Exception as exc:
                print(f"  ! detail {match.match_id} fallo: {exc}")

    await asyncio.gather(*(_one_detail(m) for m in top))

    print("== precache completado")


if __name__ == "__main__":
    asyncio.run(main())
