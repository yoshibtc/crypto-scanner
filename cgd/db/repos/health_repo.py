from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_, select

from cgd.db.engine import session_scope
from cgd.db.models import SourceHealth


def _norm_venue(venue_id: str | None) -> str:
    return venue_id if venue_id is not None else ""


def _get_or_create(session, source_key: str, venue_id: str | None) -> SourceHealth:
    vid = _norm_venue(venue_id)
    stmt = select(SourceHealth).where(
        SourceHealth.source_key == source_key,
        SourceHealth.venue_id == vid,
    )
    row = session.execute(stmt).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row is None:
        row = SourceHealth(
            source_key=source_key,
            venue_id=vid,
            success_streak=0,
            fail_streak=0,
            degraded=False,
            last_error=None,
            last_ok_at=None,
            updated_at=now,
        )
        session.add(row)
    return row


def touch_success(source_key: str, venue_id: str | None) -> None:
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        row = _get_or_create(session, source_key, venue_id)
        row.success_streak += 1
        row.fail_streak = 0
        row.degraded = False
        row.last_ok_at = now
        row.last_error = None
        row.updated_at = now


def touch_failure(source_key: str, venue_id: str | None, err: str) -> None:
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        row = _get_or_create(session, source_key, venue_id)
        row.fail_streak += 1
        row.success_streak = 0
        row.last_error = err[:2000]
        row.updated_at = now
        if row.fail_streak >= 3:
            row.degraded = True


def any_ccxt_venue_degraded() -> bool:
    """True if any `ccxt:%` row is degraded (includes stale keys from removed venues)."""
    with session_scope() as session:
        stmt = select(SourceHealth).where(
            SourceHealth.source_key.like("ccxt:%"),
            SourceHealth.degraded.is_(True),
        )
        return session.execute(stmt).first() is not None


def any_enabled_ccxt_venue_degraded() -> bool:
    """True only when a **matrix-enabled** venue's `ccxt:{id}` health row is degraded.

    If no venues are `enabled: true`, returns False (fail-open: patterns still run on facts).
    """
    from cgd.config.ccxt_matrix_loader import iter_enabled_ccxt_source_keys

    keys = iter_enabled_ccxt_source_keys()
    if not keys:
        return False
    with session_scope() as session:
        stmt = select(SourceHealth).where(
            SourceHealth.source_key.in_(keys),
            or_(
                SourceHealth.venue_id == _norm_venue(None),
                SourceHealth.venue_id.is_(None),
            ),
            SourceHealth.degraded.is_(True),
        )
        return session.execute(stmt).first() is not None


def is_source_degraded(source_key: str, venue_id: str | None = None) -> bool:
    vid = _norm_venue(venue_id)
    with session_scope() as session:
        stmt = select(SourceHealth).where(
            SourceHealth.source_key == source_key,
            SourceHealth.venue_id == vid,
        )
        row = session.execute(stmt).scalar_one_or_none()
        return bool(row and row.degraded)
