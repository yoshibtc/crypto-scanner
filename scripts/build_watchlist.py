#!/usr/bin/env python3
"""Upsert entities from Binance USDT-M perpetuals ranked by 24h quote volume.

DeFi/protocol entities (P6, etc.) are seeded separately via scripts/seed_entities.py —
this script is **perp-only** for P7 (OI + funding).

Usage:
  python scripts/build_watchlist.py [--top N] [--floor-usd VOLUME]

Requires network (CCXT). Idempotent by slug.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ccxt  # noqa: E402

from cgd.db.engine import session_scope  # noqa: E402
from cgd.db.repos.entities_repo import upsert_entity  # noqa: E402


def _slug_for_perp(sym: str) -> str:
    base = sym.split("/")[0].lower()
    return f"{base}-usdt-perp"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=50, help="How many symbols to keep")
    ap.add_argument(
        "--floor-usd",
        type=float,
        default=5_000_000.0,
        help="Minimum 24h quote volume (USD proxy)",
    )
    args = ap.parse_args()

    ex = ccxt.binanceusdm({"enableRateLimit": True})
    ex.load_markets()
    tickers = ex.fetch_tickers()

    ranked: list[tuple[str, float]] = []
    for sym, t in tickers.items():
        m = ex.markets.get(sym)
        if not m or not m.get("swap"):
            continue
        if not sym.endswith(":USDT"):
            continue
        qv = t.get("quoteVolume")
        try:
            qvf = float(qv) if qv is not None else 0.0
        except (TypeError, ValueError):
            continue
        if qvf < args.floor_usd:
            continue
        ranked.append((sym, qvf))

    ranked.sort(key=lambda x: -x[1])
    picked = ranked[: args.top]

    with session_scope() as session:
        for sym, qv in picked:
            slug = _slug_for_perp(sym)
            upsert_entity(
                session,
                slug=slug,
                display_name=f"{sym} (Binance USDT-M)",
                llama_protocol_slugs=[],
                ccxt_symbol_map={"binance_perp": {"swap": sym, "perp": sym}},
                mapping_confidence=0.72,
                enabled_patterns=["P7"],
            )
            print(f"upsert {slug}  vol~{qv:,.0f}")

    print(f"Done. Upserted {len(picked)} entities (cap {args.top}).")


if __name__ == "__main__":
    main()
