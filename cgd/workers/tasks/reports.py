from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from cgd.alerts.telegram import send_telegram_text
from cgd.db.engine import session_scope
from cgd.db.models import EvaluationRun, Gap, GapStatus, SourceHealth, Entity
from cgd.settings import get_settings
from cgd.workers.celery_app import app


@app.task(name="cgd.daily_summary_report", bind=True, max_retries=3)
def daily_summary_report(self) -> dict:
    try:
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=24)

        with session_scope() as session:
            # Gaps opened in last 24h
            new_gaps = session.execute(
                select(func.count()).select_from(Gap).where(Gap.opened_at >= since)
            ).scalar_one()

            escalated_24h = session.execute(
                select(func.count()).select_from(Gap).where(Gap.escalated_at >= since)
            ).scalar_one()

            resolved_24h = session.execute(
                select(func.count()).select_from(Gap).where(
                    Gap.resolved_at >= since, Gap.status == GapStatus.RESOLVED.value
                )
            ).scalar_one()

            invalidated_24h = session.execute(
                select(func.count()).select_from(Gap).where(
                    Gap.resolved_at >= since, Gap.status == GapStatus.INVALIDATED.value
                )
            ).scalar_one()

            # All-time gap counts by status
            status_counts: dict[str, int] = {}
            for status in GapStatus:
                status_counts[status.value] = session.execute(
                    select(func.count()).select_from(Gap).where(Gap.status == status.value)
                ).scalar_one()

            # Evaluation runs and candidate totals in last 24h
            runs = list(
                session.execute(
                    select(EvaluationRun).where(EvaluationRun.created_at >= since)
                ).scalars()
            )
            run_count = len(runs)
            total_candidates = sum(r.summary.get("candidates", 0) for r in runs)

            # Source health
            total_sources = session.execute(
                select(func.count()).select_from(SourceHealth)
            ).scalar_one()
            degraded_sources = session.execute(
                select(func.count())
                .select_from(SourceHealth)
                .where(SourceHealth.degraded.is_(True))
            ).scalar_one()

            # Watchlist size
            entity_count = session.execute(
                select(func.count()).select_from(Entity)
            ).scalar_one()

        s = get_settings()
        mode = "SHADOW (dry-run)" if s.shadow_mode else "LIVE"
        date_str = now.strftime("%Y-%m-%d")

        lines = [
            f"📋 Daily Report — {date_str} UTC",
            f"Mode: {mode}",
            "",
            "Last 24h:",
            f"  Eval runs:   {run_count}",
            f"  Candidates:  {total_candidates}",
            f"  New gaps:    {new_gaps}",
            f"  Escalated:   {escalated_24h}",
            f"  Resolved:    {resolved_24h}",
            f"  Invalidated: {invalidated_24h}",
            "",
            "All-time gaps:",
            f"  Detected:    {status_counts.get('DETECTED', 0)}",
            f"  Escalated:   {status_counts.get('ESCALATED', 0)}",
            f"  Resolved:    {status_counts.get('RESOLVED', 0)}",
            f"  Invalidated: {status_counts.get('INVALIDATED', 0)}",
            "",
            f"Watchlist: {entity_count} entities",
            f"Sources: {total_sources} tracked, {degraded_sources} degraded",
        ]

        text = "\n".join(lines)
        send_telegram_text(text)
        return {"ok": True, "run_count": run_count, "candidates": total_candidates}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300) from exc
