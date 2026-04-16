from celery import Celery

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
        "evaluate-tier1-every-10m": {
            "task": "cgd.evaluate_tier1",
            "schedule": 600.0,
            "options": {"queue": "evaluate"},
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
    },
)
