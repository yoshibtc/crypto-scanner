"""
Command handlers for the Telegram status bot.

Each function takes a SQLAlchemy Session and returns a plain-text string
ready to send back via sendMessage.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from cgd.db.models import Entity, EvaluationRun, Gap, GapStatus, SourceHealth
from cgd.settings import get_settings

_PATTERN_LABELS = {
    "p01_unlocks": "P01 Unlocks",
    "p02_tvl": "P02 TVL",
    "p06_revenue_fdv": "P06 Rev/FDV",
    "p07_derivs": "P07 Derivs",
    "p10_stable": "P10 Stable",
}


def _ago(dt: datetime | None) -> str:
    if dt is None:
        return "never"
    now = datetime.now(timezone.utc)
    secs = int((now - dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else now - dt).total_seconds())
    if secs < 60:
        return f"{secs}s ago"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    return f"{secs // 86400}d ago"


def cmd_help() -> str:
    return (
        "CGD Bot — available commands:\n\n"
        "/status    — system overview & last scan\n"
        "/watchlist — entities being tracked\n"
        "/gaps      — open / escalated gaps\n"
        "/alerts    — recently dispatched alerts\n"
        "/health    — data-source health\n"
        "/help      — this message"
    )


def cmd_status(session: Session) -> str:
    s = get_settings()

    # Last evaluation run (any entity)
    last_run: EvaluationRun | None = session.execute(
        select(EvaluationRun).order_by(desc(EvaluationRun.created_at)).limit(1)
    ).scalar_one_or_none()

    # Gap counts by status
    counts: dict[str, int] = {}
    for status in GapStatus:
        n = session.execute(
            select(func.count()).select_from(Gap).where(Gap.status == status.value)
        ).scalar_one()
        counts[status.value] = n

    # Source health summary
    total_sources = session.execute(select(func.count()).select_from(SourceHealth)).scalar_one()
    degraded = session.execute(
        select(func.count()).select_from(SourceHealth).where(SourceHealth.degraded.is_(True))
    ).scalar_one()

    mode = "SHADOW (dry-run)" if s.shadow_mode else "LIVE"
    lines = [
        "📊 System Status",
        f"Mode: {mode}",
        "",
        "Last evaluation run:",
    ]
    if last_run:
        lines += [
            f"  {_ago(last_run.created_at)}  (as_of {last_run.as_of.strftime('%H:%M UTC')})",
            f"  Summary: {last_run.summary}",
        ]
    else:
        lines.append("  No evaluation runs recorded yet.")

    lines += [
        "",
        "Gaps:",
        f"  Detected:    {counts.get('DETECTED', 0)}",
        f"  Escalated:   {counts.get('ESCALATED', 0)}",
        f"  Resolved:    {counts.get('RESOLVED', 0)}",
        f"  Invalidated: {counts.get('INVALIDATED', 0)}",
        "",
        f"Sources: {total_sources} tracked, {degraded} degraded",
    ]
    return "\n".join(lines)


def cmd_watchlist(session: Session) -> str:
    entities = list(session.execute(select(Entity).order_by(Entity.slug)).scalars())
    if not entities:
        return "No entities are currently being tracked."

    lines = [f"👁 Watchlist ({len(entities)} entities)\n"]
    for e in entities:
        patterns = ", ".join(
            _PATTERN_LABELS.get(p, p) for p in (e.enabled_patterns or [])
        ) or "none"
        conf = f"{e.mapping_confidence:.0%}"
        lines.append(f"• {e.display_name} ({e.slug})")
        lines.append(f"  Patterns: {patterns}  |  Confidence: {conf}")
    return "\n".join(lines)


def cmd_gaps(session: Session) -> str:
    active_statuses = [GapStatus.DETECTED.value, GapStatus.ESCALATED.value]
    gaps = list(
        session.execute(
            select(Gap)
            .where(Gap.status.in_(active_statuses))
            .order_by(desc(Gap.opened_at))
            .limit(20)
        ).scalars()
    )

    if not gaps:
        return "No open gaps right now."

    lines = [f"🚨 Open Gaps ({len(gaps)} shown, max 20)\n"]
    for g in gaps:
        ent = session.get(Entity, g.entity_id)
        name = ent.display_name if ent else f"entity#{g.entity_id}"
        pat = _PATTERN_LABELS.get(g.pattern_id, g.pattern_id)
        dispatched = "✅ alerted" if g.alert_dispatched_at else "⏳ pending"
        lines.append(
            f"[{g.status}] {name} — {pat}\n"
            f"  Opened {_ago(g.opened_at)} | {dispatched}"
        )
    return "\n".join(lines)


def cmd_alerts(session: Session) -> str:
    recent = list(
        session.execute(
            select(Gap)
            .where(Gap.alert_dispatched_at.is_not(None))
            .order_by(desc(Gap.alert_dispatched_at))
            .limit(10)
        ).scalars()
    )

    if not recent:
        return "No alerts have been dispatched yet."

    lines = [f"📬 Recent Alerts (last {len(recent)})\n"]
    for g in recent:
        ent = session.get(Entity, g.entity_id)
        name = ent.display_name if ent else f"entity#{g.entity_id}"
        pat = _PATTERN_LABELS.get(g.pattern_id, g.pattern_id)
        lines.append(
            f"• {name} — {pat}\n"
            f"  Alerted {_ago(g.alert_dispatched_at)}  |  Status: {g.status}"
        )
    return "\n".join(lines)


def cmd_health(session: Session) -> str:
    sources = list(
        session.execute(select(SourceHealth).order_by(SourceHealth.source_key)).scalars()
    )

    if not sources:
        return "No source-health records found yet."

    lines = ["🩺 Source Health\n"]
    for sh in sources:
        label = sh.source_key
        if sh.venue_id:
            label += f"/{sh.venue_id}"
        status = "🔴 DEGRADED" if sh.degraded else "🟢 OK"
        streak = (
            f"✓{sh.success_streak}" if not sh.degraded else f"✗{sh.fail_streak}"
        )
        last_ok = _ago(sh.last_ok_at)
        lines.append(f"{status}  {label}  streak:{streak}  last_ok:{last_ok}")
        if sh.degraded and sh.last_error:
            short_err = sh.last_error[:80] + ("…" if len(sh.last_error) > 80 else "")
            lines.append(f"  ↳ {short_err}")
    return "\n".join(lines)
