from __future__ import annotations

from datetime import datetime, timedelta, timezone
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


def _mf_to_row(r: MarketFact) -> dict[str, Any]:
    return {
        "fact_type": r.fact_type,
        "venue_id": r.venue_id,
        "pool_id": r.pool_id,
        "source_ts": r.source_ts,
        "ingested_at": r.ingested_at,
        "payload": r.payload,
    }


def load_anchored_pair(
    session,
    entity_id: int,
    fact_type: str,
    as_of: datetime,
    *,
    horizon: timedelta = timedelta(days=7),
    tolerance: timedelta = timedelta(hours=6),
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Latest row at/before ``as_of`` and best row near ``as_of - horizon`` (within tolerance)."""
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)

    stmt_new = (
        select(MarketFact)
        .where(
            MarketFact.entity_id == entity_id,
            MarketFact.fact_type == fact_type,
            MarketFact.source_ts <= as_of,
        )
        .order_by(MarketFact.source_ts.desc())
        .limit(1)
    )
    new_r = session.execute(stmt_new).scalar_one_or_none()
    if new_r is None:
        return None, None

    target = as_of - horizon
    stmt_old = (
        select(MarketFact)
        .where(
            MarketFact.entity_id == entity_id,
            MarketFact.fact_type == fact_type,
            MarketFact.source_ts >= target - tolerance,
            MarketFact.source_ts <= target + tolerance,
        )
        .order_by(MarketFact.source_ts.desc())
        .limit(1)
    )
    old_r = session.execute(stmt_old).scalar_one_or_none()
    if old_r is None:
        return None, _mf_to_row(new_r)
    return _mf_to_row(old_r), _mf_to_row(new_r)


def historical_fdv_wow_pcts(session, entity_id: int, max_pairs: int = 80) -> list[float]:
    """Past FDV week-on-week ratios from stored defillama_protocol snapshots (chronological pairs)."""
    stmt = (
        select(MarketFact)
        .where(
            MarketFact.entity_id == entity_id,
            MarketFact.fact_type == "defillama_protocol",
        )
        .order_by(MarketFact.source_ts.asc())
        .limit(max_pairs)
    )
    rows = list(session.execute(stmt).scalars().all())
    vals: list[float] = []
    for r in rows:
        fdv = (r.payload or {}).get("fdv")
        try:
            vals.append(float(fdv) if fdv is not None else 0.0)
        except (TypeError, ValueError):
            vals.append(0.0)
    wows: list[float] = []
    for i in range(1, len(vals)):
        a, b = vals[i - 1], vals[i]
        if a and a > 0:
            wows.append((b - a) / a)
    return wows


def historical_venue_oi_change_pcts(
    session, entity_id: int, venue_id: str, max_pairs: int = 80
) -> list[float]:
    """Historical open-interest change ratios for one venue's ccxt_ticker snapshots."""
    stmt = (
        select(MarketFact)
        .where(
            MarketFact.entity_id == entity_id,
            MarketFact.fact_type == "ccxt_ticker",
            MarketFact.venue_id == venue_id,
        )
        .order_by(MarketFact.source_ts.asc())
        .limit(max_pairs)
    )
    rows = list(session.execute(stmt).scalars().all())

    def extract_oi(payload: dict[str, Any]) -> float | None:
        oi = payload.get("open_interest")
        if oi is None:
            return None
        if isinstance(oi, dict):
            for k in ("openInterestAmount", "openInterest", "amount", "value"):
                if k in oi and oi[k] is not None:
                    try:
                        return float(oi[k])
                    except (TypeError, ValueError):
                        continue
            return None
        try:
            return float(oi)
        except (TypeError, ValueError):
            return None

    ois: list[float | None] = []
    for r in rows:
        ois.append(extract_oi(r.payload or {}))
    changes: list[float] = []
    for i in range(1, len(ois)):
        o0, o1 = ois[i - 1], ois[i]
        if o0 and o0 > 0 and o1 is not None:
            changes.append((o1 - o0) / o0)
    return changes
