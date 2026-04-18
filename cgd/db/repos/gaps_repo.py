from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from cgd.db.engine import session_scope
from cgd.db.models import Gap, GapEvent, GapOutcome, GapStatus


def upsert_gap_candidate_session(
    session: Session,
    *,
    pattern_id: str,
    entity_id: int,
    dedupe_key: str,
    payload: dict[str, Any],
    refs: dict[str, Any],
    reason_codes: list[str],
    shadow_mode: bool,
) -> tuple[Gap, str]:
    now = datetime.now(timezone.utc)
    existing = session.execute(
        select(Gap).where(Gap.pattern_id == pattern_id, Gap.dedupe_key == dedupe_key)
    ).scalar_one_or_none()

    if existing is None:
        g = Gap(
            pattern_id=pattern_id,
            entity_id=entity_id,
            status=GapStatus.DETECTED.value,
            dedupe_key=dedupe_key,
            opened_at=now,
            escalated_at=None,
            resolved_at=None,
            payload_json=payload,
            supporting_observation_refs=refs,
            resolve_miss_streak=0,
        )
        session.add(g)
        session.flush()
        session.add(
            GapEvent(
                gap_id=g.id,
                event_type="DETECTED",
                reason_codes=reason_codes,
                meta={"shadow_mode": shadow_mode},
                created_at=now,
            )
        )
        return g, "created"

    existing.payload_json = payload
    existing.supporting_observation_refs = refs
    existing.resolve_miss_streak = 0
    session.add(
        GapEvent(
            gap_id=existing.id,
            event_type="REFRESH",
            reason_codes=reason_codes,
            meta={"shadow_mode": shadow_mode},
            created_at=now,
        )
    )
    return existing, "updated"


def escalate_gap_session(session: Session, gap_id: int, *, shadow_mode: bool) -> bool:
    now = datetime.now(timezone.utc)
    g = session.get(Gap, gap_id)
    if g is None or g.status != GapStatus.DETECTED.value:
        return False
    g.status = GapStatus.ESCALATED.value
    g.escalated_at = now
    session.add(
        GapEvent(
            gap_id=g.id,
            event_type="ESCALATED",
            reason_codes=[],
            meta={"shadow_mode": shadow_mode},
            created_at=now,
        )
    )
    return True


def mark_alert_dispatched_session(session: Session, gap_id: int) -> None:
    now = datetime.now(timezone.utc)
    g = session.get(Gap, gap_id)
    if g is None:
        return
    g.alert_dispatched_at = now
    session.add(
        GapEvent(
            gap_id=g.id,
            event_type="ALERT_SENT",
            reason_codes=[],
            meta={},
            created_at=now,
        )
    )


def list_escalated_undispatched(session: Session) -> list[Gap]:
    stmt = select(Gap).where(
        Gap.status == GapStatus.ESCALATED.value,
        Gap.alert_dispatched_at.is_(None),
    )
    return list(session.execute(stmt).scalars().all())


def resolve_gap_session(session: Session, gap_id: int, *, reason: str = "MANUAL") -> bool:
    now = datetime.now(timezone.utc)
    g = session.get(Gap, gap_id)
    if g is None or g.status not in (
        GapStatus.DETECTED.value,
        GapStatus.ESCALATED.value,
    ):
        return False
    g.status = GapStatus.RESOLVED.value
    g.resolved_at = now
    session.add(
        GapEvent(
            gap_id=g.id,
            event_type="RESOLVED",
            reason_codes=[],
            meta={"reason": reason},
            created_at=now,
        )
    )
    return True


def invalidate_gap_session(session: Session, gap_id: int, *, reason: str = "MANUAL") -> bool:
    now = datetime.now(timezone.utc)
    g = session.get(Gap, gap_id)
    if g is None or g.status not in (
        GapStatus.DETECTED.value,
        GapStatus.ESCALATED.value,
    ):
        return False
    g.status = GapStatus.INVALIDATED.value
    g.resolved_at = now
    session.add(
        GapEvent(
            gap_id=g.id,
            event_type="INVALIDATED",
            reason_codes=[],
            meta={"reason": reason},
            created_at=now,
        )
    )
    return True


def upsert_gap_outcome_returns(
    session: Session,
    *,
    gap_id: int,
    ret_1h_pct: float | None,
    ret_4h_pct: float | None,
    ret_24h_pct: float | None,
    ret_7d_pct: float | None,
    notes: str | None = None,
) -> None:
    """Insert or update forward-return snapshot for labeling."""
    now = datetime.now(timezone.utc)
    stmt = select(GapOutcome).where(GapOutcome.gap_id == gap_id)
    row = session.execute(stmt).scalar_one_or_none()
    if row is None:
        session.add(
            GapOutcome(
                gap_id=gap_id,
                actionable=None,
                still_true_7d=None,
                notes=notes or "",
                labeled_at=now,
                ret_1h_pct=ret_1h_pct,
                ret_4h_pct=ret_4h_pct,
                ret_24h_pct=ret_24h_pct,
                ret_7d_pct=ret_7d_pct,
                computed_at=now,
            )
        )
    else:
        row.ret_1h_pct = ret_1h_pct
        row.ret_4h_pct = ret_4h_pct
        row.ret_24h_pct = ret_24h_pct
        row.ret_7d_pct = ret_7d_pct
        row.notes = notes if notes is not None else row.notes
        row.labeled_at = now
        row.computed_at = now


def upsert_gap_candidate(**kwargs) -> tuple[Gap, str]:
    with session_scope() as session:
        g, ev = upsert_gap_candidate_session(session, **kwargs)
        session.expunge(g)
        return g, ev
