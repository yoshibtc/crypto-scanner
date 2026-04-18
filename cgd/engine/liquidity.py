"""Liquidity / tradability gate from latest CCXT ticker facts."""

from __future__ import annotations

from typing import Any

from sqlalchemy import desc, select

from cgd.db.models import MarketFact
from cgd.config.pattern_config import PatternConfig
from cgd.patterns.types import GapCandidate


def _latest_quote_volume_usd(session, entity_id: int) -> float | None:
    stmt = (
        select(MarketFact)
        .where(MarketFact.entity_id == entity_id, MarketFact.fact_type == "ccxt_ticker")
        .order_by(desc(MarketFact.source_ts))
        .limit(5)
    )
    rows = list(session.execute(stmt).scalars().all())
    for r in rows:
        qv = (r.payload or {}).get("quoteVolume")
        try:
            if qv is not None:
                return float(qv)
        except (TypeError, ValueError):
            continue
    return None


def apply_liquidity_gate(entity: Any, cand: GapCandidate, session: Any, cfg: PatternConfig) -> None:
    cmap = getattr(entity, "ccxt_symbol_map", None) or {}
    if not cmap:
        cand.payload.setdefault("liquidity_note", "NO_CEX_MAP_skipped")
        return

    floor = cfg.liquidity_quote_volume_floor_usd
    qv = _latest_quote_volume_usd(session, entity.id)
    cand.payload.setdefault("quote_volume_usd", qv)
    if qv is None or qv < floor:
        cand.tradable = False
        cand.payload.setdefault("liquidity_note", "NOT_TRADABLE_below_volume_floor")
