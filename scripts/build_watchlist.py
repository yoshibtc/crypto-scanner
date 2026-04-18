#!/usr/bin/env python3
"""Upsert entities from Binance spot markets ranked by 24h quote volume (USDT pairs).

Usage:
  python scripts/build_watchlist.py [--top N] [--floor-usd VOLUME]

Requires network (CCXT). Idempotent by slug.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ccxt  # noqa: E402

from cgd.db.engine import session_scope  # noqa: E402
from cgd.db.repos.entities_repo import upsert_entity  # noqa: E402


def _slugify(sym: str) -> str:
    base = sym.replace("/", "-").lower()
    base = re.sub(r"[^a-z0-9-]", "-", base)
    return f"{base}-spot"


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

    ex = ccxt.binance({"enableRateLimit": True})
    ex.load_markets()
    tickers = ex.fetch_tickers()

    ranked: list[tuple[str, float]] = []
    for sym, t in tickers.items():
        if not sym.endswith("/USDT"):
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
            slug = _slugify(sym)
            upsert_entity(
                session,
                slug=slug,
                display_name=f"{sym} (Binance watch)",
                llama_protocol_slugs=[],
                ccxt_symbol_map={"binance": {"spot": sym}},
                mapping_confidence=0.72,
                enabled_patterns=["P7", "P6"],
            )
            print(f"upsert {slug}  vol~{qv:,.0f}")

    print(f"Done. Upserted {len(picked)} entities (cap {args.top}).")


if __name__ == "__main__":
    main()
