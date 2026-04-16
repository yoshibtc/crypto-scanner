from __future__ import annotations

from typing import Any

from sqlalchemy import select

from cgd.db.models import MarketFact, OnchainFact


def load_market_fact_rows(session, entity_id: int, limit: int = 500) -> list[dict[str, Any]]:
    stmt = (
        select(MarketFact)
        .where(MarketFact.entity_id == entity_id)
        .order_by(MarketFact.source_ts.desc())
        .limit(limit)
    )
    rows = list(session.execute(stmt).scalars().all())
    out: list[dict[str, Any]] = []
    for r in reversed(rows):
        out.append(
            {
                "fact_type": r.fact_type,
                "venue_id": r.venue_id,
                "pool_id": r.pool_id,
                "source_ts": r.source_ts,
                "ingested_at": r.ingested_at,
                "payload": r.payload,
            }
        )
    return out


def load_onchain_fact_rows(session, entity_id: int, limit: int = 200) -> list[dict[str, Any]]:
    stmt = (
        select(OnchainFact)
        .where(OnchainFact.entity_id == entity_id)
        .order_by(OnchainFact.source_ts.desc())
        .limit(limit)
    )
    rows = list(session.execute(stmt).scalars().all())
    out: list[dict[str, Any]] = []
    for r in reversed(rows):
        out.append(
            {
                "fact_type": r.fact_type,
                "chain": r.chain,
                "contract_address": r.contract_address,
                "source_ts": r.source_ts,
                "payload": r.payload,
            }
        )
    return out
