from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select

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


def _extract_fdv(payload: dict[str, Any]) -> float | None:
    fdv = payload.get("fdv")
    try:
        if fdv is None:
            return None
        return float(fdv)
    except (TypeError, ValueError):
        return None


def _extract_oi_raw(payload: dict[str, Any]) -> float | None:
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


def _nearest_row_for_target(
    rows_chrono: list[MarketFact],
    target_ts: datetime,
    tolerance: timedelta,
) -> MarketFact | None:
    """Pick the row whose ``source_ts`` is closest to ``target_ts`` within ``±tolerance``."""
    lo = target_ts - tolerance
    hi = target_ts + tolerance
    best: MarketFact | None = None
    best_delta: float | None = None
    for r in rows_chrono:
        ts = r.source_ts
        if ts < lo or ts > hi:
            continue
        delta = abs((ts - target_ts).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best = r
    return best


def _fdv_wow_ratios_at_horizon(
    rows_chrono: list[MarketFact],
    *,
    horizon: timedelta,
    tolerance: timedelta,
    max_pairs: int,
) -> list[float]:
    """Empirical FDV week-on-week ratios matching P6 anchored windows (not consecutive ingest rows)."""
    wows: list[float] = []
    for new_r in rows_chrono:
        target_old = new_r.source_ts - horizon
        old_r = _nearest_row_for_target(rows_chrono, target_old, tolerance)
        if old_r is None or old_r.source_ts >= new_r.source_ts:
            continue
        fo = _extract_fdv(old_r.payload or {})
        fn = _extract_fdv(new_r.payload or {})
        if fo is None or fn is None or fo <= 0:
            continue
        wows.append((fn - fo) / fo)
    if len(wows) > max_pairs:
        wows = wows[-max_pairs:]
    return wows


def _oi_change_ratios_at_horizon(
    rows_chrono: list[MarketFact],
    *,
    horizon: timedelta,
    tolerance: timedelta,
    max_pairs: int,
) -> list[float]:
    """OI change ratios matching P7 old/new spacing (~``horizon`` apart), not consecutive snapshots."""
    changes: list[float] = []
    for new_r in rows_chrono:
        target_old = new_r.source_ts - horizon
        old_r = _nearest_row_for_target(rows_chrono, target_old, tolerance)
        if old_r is None or old_r.source_ts >= new_r.source_ts:
            continue
        o0 = _extract_oi_raw(old_r.payload or {})
        o1 = _extract_oi_raw(new_r.payload or {})
        if not o0 or o0 <= 0 or o1 is None:
            continue
        changes.append((o1 - o0) / o0)
    if len(changes) > max_pairs:
        changes = changes[-max_pairs:]
    return changes


def historical_fdv_wow_pcts(session, entity_id: int, max_pairs: int = 80) -> list[float]:
    """Past FDV WoW ratios at the same ~7d horizon as P6 (recent window of stored snapshots)."""
    stmt = (
        select(MarketFact)
        .where(
            MarketFact.entity_id == entity_id,
            MarketFact.fact_type == "defillama_protocol",
        )
        .order_by(desc(MarketFact.source_ts))
        .limit(5000)
    )
    rows = list(session.execute(stmt).scalars().all())
    rows_chrono = list(reversed(rows))
    return _fdv_wow_ratios_at_horizon(
        rows_chrono,
        horizon=timedelta(days=7),
        tolerance=timedelta(hours=6),
        max_pairs=max_pairs,
    )


def historical_venue_oi_change_pcts(
    session, entity_id: int, venue_id: str, max_pairs: int = 80
) -> list[float]:
    """Historical OI change ratios at the same ~20h spacing P7 uses (one venue)."""
    stmt = (
        select(MarketFact)
        .where(
            MarketFact.entity_id == entity_id,
            MarketFact.fact_type == "ccxt_ticker",
            MarketFact.venue_id == venue_id,
        )
        .order_by(desc(MarketFact.source_ts))
        .limit(5000)
    )
    rows = list(session.execute(stmt).scalars().all())
    rows_chrono = list(reversed(rows))
    return _oi_change_ratios_at_horizon(
        rows_chrono,
        horizon=timedelta(hours=20),
        tolerance=timedelta(hours=4),
        max_pairs=max_pairs,
    )
