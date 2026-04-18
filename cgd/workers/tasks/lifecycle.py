"""Gap lifecycle: auto-resolve when pattern stops firing."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from cgd.db.engine import session_scope
from cgd.db.models import Entity, Gap, GapStatus
from cgd.db.repos.gaps_repo import resolve_gap_session
from cgd.engine.eval_health import skip_pattern_for_health
from cgd.engine.facts_loader import load_market_fact_rows, load_onchain_fact_rows
from cgd.engine.pattern_registry import PATTERN_BY_ID
from cgd.db.repos.health_repo import any_enabled_ccxt_venue_degraded
from cgd.patterns.types import EvaluationContext
from cgd.settings import get_settings
from cgd.workers.celery_app import app


@app.task(name="cgd.auto_resolve_gaps", bind=True, max_retries=3)
def auto_resolve_gaps(self) -> dict:
    settings = get_settings()
    thresh = settings.auto_resolve_miss_threshold
    resolved = 0
    checked = 0
    try:
        with session_scope() as session:
            stmt = select(Gap).where(
                Gap.status.in_([GapStatus.DETECTED.value, GapStatus.ESCALATED.value])
            )
            gaps = list(session.execute(stmt).scalars().all())
            now = datetime.now(timezone.utc)

            ccxt_degraded = any_enabled_ccxt_venue_degraded()
            for gap in gaps:
                checked += 1
                ent = session.get(Entity, gap.entity_id)
                if ent is None or ent.mapping_confidence < 0.3:
                    continue
                mod = PATTERN_BY_ID.get(gap.pattern_id)
                if mod is None:
                    continue
                if skip_pattern_for_health(gap.pattern_id):
                    continue

                market = load_market_fact_rows(session, ent.id)
                onchain = load_onchain_fact_rows(session, ent.id)
                ctx = EvaluationContext(
                    entity=ent,
                    as_of=now,
                    semantics_version=settings.semantics_version,
                    matrix_version=settings.matrix_version,
                    market_rows=market,
                    onchain_rows=onchain,
                    ccxt_degraded=ccxt_degraded,
                    session=session,
                    p10_mode="full",
                    regime=None,
                )
                try:
                    candidates = mod.detect(ctx)
                except Exception:
                    continue
                keys = {c.dedupe_key for c in candidates}
                if gap.dedupe_key in keys:
                    gap.resolve_miss_streak = 0
                else:
                    gap.resolve_miss_streak += 1
                    if gap.resolve_miss_streak >= thresh:
                        if resolve_gap_session(session, gap.id, reason="AUTO_STALE"):
                            resolved += 1
        return {"checked": checked, "resolved": resolved}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120) from exc
