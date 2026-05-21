"""Benchmark de las tools principales del MCP.

Mide tiempo en frio y en caliente (cache hit). Exporta JSON a stdout.

Uso:
    python scripts/bench.py
    python scripts/bench.py --match-id <id>
    python scripts/bench.py --json bench-result.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flashscore_mcp.browser_pool import BrowserPool  # noqa: E402
from flashscore_mcp.config import Settings  # noqa: E402
from flashscore_mcp.providers.flashscore import FlashscorePlaywrightProvider  # noqa: E402


async def _timed(coro):
    t0 = time.perf_counter()
    result = await coro
    return result, time.perf_counter() - t0


async def main(match_id: str | None, out_path: str | None) -> None:
    settings = Settings.from_env()
    provider = FlashscorePlaywrightProvider(settings)
    report: dict[str, object] = {"target_ms": {"live": 3000, "full": 10000, "search": 15000}}

    print("== live_scores (frio + 2 calientes) ==")
    cold_matches, dt_cold = await _timed(provider.fetch_live_matches(live_only=False))
    hot1, dt_hot1 = await _timed(provider.fetch_live_matches(live_only=False))
    hot2, dt_hot2 = await _timed(provider.fetch_live_matches(live_only=False))
    report["live_scores"] = {
        "cold_s": round(dt_cold, 3),
        "hot_p50_s": round(statistics.median([dt_hot1, dt_hot2]), 3),
        "items": len(cold_matches),
    }
    print(f"  frio={dt_cold:.2f}s  caliente1={dt_hot1:.2f}s  caliente2={dt_hot2:.2f}s  N={len(cold_matches)}")

    if not match_id and cold_matches:
        match_id = cold_matches[0].match_id

    if match_id:
        print(f"== match_full_detail ({match_id}) ==")
        _, dt_full = await _timed(
            provider.fetch_match_full_detail(match_id=match_id, sections=["summary", "statistics", "lineups"])
        )
        report["match_full_detail_3sec"] = {"s": round(dt_full, 3), "match_id": match_id}
        print(f"  3 secciones paralelas: {dt_full:.2f}s")

    print("== search_matches (3 dias) ==")
    from datetime import date, timedelta

    today = date.today()
    df = (today - timedelta(days=1)).isoformat()
    dt = (today + timedelta(days=1)).isoformat()
    items, dt_search = await _timed(
        provider.search_matches(query="real", date_from=df, date_to=dt)
    )
    report["search_matches_3d"] = {"s": round(dt_search, 3), "items": len(items)}
    print(f"  busqueda 3 dias: {dt_search:.2f}s  N={len(items)}")

    await BrowserPool.get_instance(settings).close()

    payload = json.dumps(report, indent=2, ensure_ascii=False)
    print("\n== resumen JSON ==")
    print(payload)
    if out_path:
        Path(out_path).write_text(payload, encoding="utf-8")
        print(f"\nGuardado en {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--match-id", default=None)
    parser.add_argument("--json", default=None, help="Ruta para guardar el reporte")
    args = parser.parse_args()
    asyncio.run(main(args.match_id, args.json))
