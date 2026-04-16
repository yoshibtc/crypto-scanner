from __future__ import annotations

from cgd.alerts.renderers import render_gap_alert
from cgd.alerts.telegram import send_telegram_text
from cgd.db.engine import session_scope
from cgd.db.models import Entity
from cgd.db.repos.gaps_repo import list_escalated_undispatched, mark_alert_dispatched_session
from cgd.workers.celery_app import app


@app.task(name="cgd.dispatch_alerts", bind=True, max_retries=3)
def dispatch_alerts(self) -> dict:
    sent = 0
    pending = 0
    try:
        with session_scope() as session:
            gaps = list_escalated_undispatched(session)
            pending = len(gaps)
            for g in gaps:
                ent = session.get(Entity, g.entity_id)
                if ent is None:
                    continue
                text = render_gap_alert(ent, g)
                if send_telegram_text(text):
                    mark_alert_dispatched_session(session, g.id)
                    sent += 1
        return {"sent": sent, "pending": pending}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60) from exc
