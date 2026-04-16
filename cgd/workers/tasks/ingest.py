from __future__ import annotations

from cgd.collectors.ccxt_collector import ingest_ccxt_snapshot
from cgd.collectors.defillama import ingest_defillama_snapshot
from cgd.collectors.rpc_client import check_rpc_health
from cgd.workers.celery_app import app


@app.task(name="cgd.ingest_defillama", bind=True, max_retries=5)
def ingest_defillama(self) -> dict:
    try:
        n = ingest_defillama_snapshot()
        return {"ok": True, "rows": n}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@app.task(name="cgd.ingest_ccxt", bind=True, max_retries=5)
def ingest_ccxt(self) -> dict:
    try:
        n = ingest_ccxt_snapshot()
        return {"ok": True, "rows": n}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@app.task(name="cgd.ingest_rpc_health", bind=True, max_retries=3)
def ingest_rpc_health(self) -> dict:
    try:
        return check_rpc_health()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)


@app.task(name="cgd.verify_ccxt_matrix", bind=True, max_retries=2)
def verify_ccxt_matrix(self) -> dict:
    from cgd.collectors.ccxt_matrix import verify_matrix_against_exchanges

    return verify_matrix_against_exchanges()
