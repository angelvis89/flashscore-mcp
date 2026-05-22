"""Benchmark A/B: mide latencia real de los tools del MCP.

Uso:
    python scripts/bench_provider.py --provider flashscore --runs 5
    python scripts/bench_provider.py --provider flashscore_fast --runs 5

Reporta p50, p95, p99 por tool en CSV en stdout.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import sys
import time
from typing import Any

# Permitir ejecucion directa sin instalar
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from flashscore_mcp.config import Settings  # noqa: E402
from flashscore_mcp.providers.factory import build_provider  # noqa: E402


async def _time_call(coro_factory: Any) -> float:
    start = time.perf_counter()
    try:
        await coro_factory()
    except Exception as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
    return time.perf_counter() - start


def _stats(samples: list[float]) -> dict[str, float]:
    if not samples:
        return {"p50": 0, "p95": 0, "p99": 0, "n": 0}
    samples_sorted = sorted(samples)
    return {
        "p50": statistics.median(samples_sorted),
        "p95": samples_sorted[max(0, int(0.95 * len(samples_sorted)) - 1)],
        "p99": samples_sorted[max(0, int(0.99 * len(samples_sorted)) - 1)],
        "mean": statistics.mean(samples_sorted),
        "n": len(samples_sorted),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark del provider Flashscore")
    parser.add_argument(
        "--provider", required=True, choices=["flashscore", "flashscore_fast", "mock"]
    )
    parser.add_argument("--runs", type=int, default=5, help="Iteraciones por tool")
    parser.add_argument(
        "--match-id", default=None,
        help="match_id real para el bench de detalle (opcional)",
    )
    args = parser.parse_args()

    os.environ["SPORTS_PROVIDER"] = args.provider
    settings = Settings.from_env()
    provider = build_provider(settings)

    # Warmup explicito si existe
    warm = getattr(provider, "warmup", None)
    if callable(warm):
        print(f"# warmup {args.provider}...", file=sys.stderr)
        await warm()

    scenarios: dict[str, Any] = {
        "live_scores": lambda: provider.fetch_live_matches(sport="football", live_only=True),
        "live_all": lambda: provider.fetch_live_matches(sport="football", live_only=False),
    }
    if args.match_id:
        scenarios["match_detail"] = lambda: provider.fetch_match_detail(args.match_id)
        scenarios["full_detail"] = lambda: provider.fetch_match_full_detail(args.match_id)

    print("tool,p50,p95,p99,mean,n")
    for name, factory in scenarios.items():
        samples = []
        for i in range(args.runs):
            elapsed = await _time_call(factory)
            print(f"# {name} run {i+1}/{args.runs}: {elapsed:.2f}s", file=sys.stderr)
            samples.append(elapsed)
        s = _stats(samples)
        print(
            f"{name},{s['p50']:.2f},{s['p95']:.2f},{s['p99']:.2f},{s['mean']:.2f},{s['n']}"
        )

    close = getattr(provider, "close", None)
    if callable(close):
        await close()


if __name__ == "__main__":
    asyncio.run(main())
