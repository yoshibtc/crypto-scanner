"""Compute forward returns for gaps (labeling / calibration)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from cgd.db.engine import session_scope
from cgd.db.models import Gap
from cgd.db.repos.gaps_repo import upsert_gap_outcome_returns
from cgd.engine.price_lookup import nearest_ccxt_last_price
from cgd.workers.celery_app import app


def _pct_ret(p0: float | None, p1: float | None) -> float | None:
    if p0 is None or p1 is None or p0 <= 0:
        return None
    return round((p1 - p0) / p0 * 100.0, 6)


@app.task(name="cgd.compute_gap_outcomes", bind=True, max_retries=3)
def compute_gap_outcomes(self) -> dict:
    """Fill gap_outcomes forward-return columns for recent gaps."""
    done = 0
    skipped = 0
    try:
        with session_scope() as session:
            cutoff = datetime.now(timezone.utc) - timedelta(days=14)
            stmt = (
                select(Gap)
                .where(Gap.opened_at >= cutoff)
                .order_by(Gap.opened_at.desc())
                .limit(500)
            )
            gaps = list(session.execute(stmt).scalars().all())
            now = datetime.now(timezone.utc)

            for g in gaps:
                p0 = nearest_ccxt_last_price(session, g.entity_id, g.opened_at)
                if p0 is None:
                    skipped += 1
                    continue

                o1 = g.opened_at + timedelta(hours=1)
                o4 = g.opened_at + timedelta(hours=4)
                o24 = g.opened_at + timedelta(hours=24)
                o7 = g.opened_at + timedelta(days=7)

                r1 = (
                    _pct_ret(p0, nearest_ccxt_last_price(session, g.entity_id, o1))
                    if o1 <= now
                    else None
                )
                r4 = (
                    _pct_ret(p0, nearest_ccxt_last_price(session, g.entity_id, o4))
                    if o4 <= now
                    else None
                )
                r24 = (
                    _pct_ret(p0, nearest_ccxt_last_price(session, g.entity_id, o24))
                    if o24 <= now
                    else None
                )
                r7 = (
                    _pct_ret(p0, nearest_ccxt_last_price(session, g.entity_id, o7))
                    if o7 <= now
                    else None
                )

                upsert_gap_outcome_returns(
                    session,
                    gap_id=g.id,
                    ret_1h_pct=r1,
                    ret_4h_pct=r4,
                    ret_24h_pct=r24,
                    ret_7d_pct=r7,
                    notes="auto_forward_returns",
                )
                done += 1
        return {"updated": done, "skipped_no_price": skipped}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300) from exc
