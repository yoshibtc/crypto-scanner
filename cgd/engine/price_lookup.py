"""Nearest CCXT ticker `last` price around a timestamp (from market_facts)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select

from cgd.db.models import MarketFact


def nearest_ccxt_last_price(
    session: Any,
    entity_id: int,
    target: datetime,
    *,
    max_rows: int = 400,
) -> float | None:
    stmt = (
        select(MarketFact)
        .where(
            MarketFact.entity_id == entity_id,
            MarketFact.fact_type == "ccxt_ticker",
        )
        .order_by(MarketFact.source_ts.desc())
        .limit(max_rows)
    )
    rows = list(session.execute(stmt).scalars().all())
    best: float | None = None
    best_delta: float | None = None
    for r in rows:
        raw = (r.payload or {}).get("last")
        try:
            px = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            continue
        if px is None or px <= 0:
            continue
        delta = abs((r.source_ts - target).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best = px
    return best
