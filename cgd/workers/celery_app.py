from celery import Celery
from celery.schedules import crontab

from cgd.settings import get_settings

settings = get_settings()

app = Celery(
    "cgd",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "cgd.workers.tasks.ingest",
        "cgd.workers.tasks.evaluate",
        "cgd.workers.tasks.alerts",
        "cgd.workers.tasks.health",
        "cgd.workers.tasks.lifecycle",
        "cgd.workers.tasks.labels",
        "cgd.workers.tasks.regime",
        "cgd.workers.tasks.reports",
        "cgd.workers.tasks.watchlist",
    ],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
    task_queues={
        "ingest_rest": {},
        "ingest_ccxt": {},
        "ingest_rpc": {},
        "evaluate": {},
        "alerts": {},
        "default": {},
    },
    beat_schedule={
        "ingest-defillama-every-15m": {
            "task": "cgd.ingest_defillama",
            "schedule": 900.0,
            "options": {"queue": "ingest_rest"},
        },
        "ingest-ccxt-every-5m": {
            "task": "cgd.ingest_ccxt",
            "schedule": 300.0,
            "options": {"queue": "ingest_ccxt"},
        },
        "ingest-rpc-health-every-5m": {
            "task": "cgd.ingest_rpc_health",
            "schedule": 300.0,
            "options": {"queue": "ingest_rpc"},
        },
        "evaluate-tier1-fast-every-2m": {
            "task": "cgd.evaluate_tier1_fast",
            "schedule": 120.0,
            "options": {"queue": "evaluate"},
        },
        "evaluate-tier1-slow-every-20m": {
            "task": "cgd.evaluate_tier1_slow",
            "schedule": 1200.0,
            "options": {"queue": "evaluate"},
        },
        "auto-resolve-gaps-every-20m": {
            "task": "cgd.auto_resolve_gaps",
            "schedule": 1200.0,
            "options": {"queue": "evaluate"},
        },
        "compute-gap-outcomes-hourly": {
            "task": "cgd.compute_gap_outcomes",
            "schedule": 3600.0,
            "options": {"queue": "default"},
        },
        "record-btc-regime-daily": {
            "task": "cgd.record_btc_regime",
            "schedule": 86400.0,
            "options": {"queue": "default"},
        },
        "dispatch-alerts-every-2m": {
            "task": "cgd.dispatch_alerts",
            "schedule": 120.0,
            "options": {"queue": "alerts"},
        },
        "ccxt-matrix-verify-daily": {
            "task": "cgd.verify_ccxt_matrix",
            "schedule": 86400.0,
            "options": {"queue": "ingest_ccxt"},
        },
        "refresh-perp-watchlist-daily": {
            "task": "cgd.refresh_perp_watchlist",
            "schedule": crontab(hour=1, minute=0),
            "options": {"queue": "ingest_ccxt"},
        },
        "daily-summary-report-midnight": {
            "task": "cgd.daily_summary_report",
            "schedule": crontab(hour=0, minute=0),
            "options": {"queue": "alerts"},
        },
    },
)
