"""Seed pilot entities (run after migrations)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# project root on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from cgd.db.engine import session_scope
from cgd.db.models import Entity


def main() -> None:
    now = datetime.now(timezone.utc)
    samples = [
        Entity(
            slug="llama-aave",
            display_name="Aave (Llama pilot)",
            semantics_version=1,
            llama_protocol_slugs=["aave"],
            token_addresses={"ethereum": "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9"},
            ccxt_symbol_map={},
            rpc_chain="ethereum",
            supply_source="stub",
            mapping_confidence=0.85,
            enabled_patterns=["P6", "P2"],
            tvl_contract_allowlist=[],
            created_at=now,
            updated_at=now,
        ),
        Entity(
            slug="btc-binance-perp",
            display_name="BTC perp (Binance pilot)",
            semantics_version=1,
            llama_protocol_slugs=[],
            token_addresses={},
            ccxt_symbol_map={
                "binance": {
                    "spot": "BTC/USDT",
                    "swap": "BTC/USDT:USDT",
                }
            },
            rpc_chain=None,
            supply_source="stub",
            mapping_confidence=0.8,
            enabled_patterns=["P7"],
            tvl_contract_allowlist=[],
            created_at=now,
            updated_at=now,
        ),
        Entity(
            slug="stable-usdt",
            display_name="USDT peg watch",
            semantics_version=1,
            llama_protocol_slugs=[],
            token_addresses={},
            ccxt_symbol_map={"binance": {"spot": "USDT/USDC"}},
            rpc_chain=None,
            supply_source="stub",
            mapping_confidence=0.75,
            enabled_patterns=["P10"],
            tvl_contract_allowlist=[],
            created_at=now,
            updated_at=now,
        ),
    ]

    with session_scope() as session:
        for ent in samples:
            existing = session.execute(select(Entity).where(Entity.slug == ent.slug)).scalar_one_or_none()
            if existing:
                continue
            session.add(ent)
    print("Seed complete (skipped existing slugs).")


if __name__ == "__main__":
    main()
