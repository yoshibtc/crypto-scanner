"""Optional housekeeping / health probes."""

from cgd.workers.celery_app import app


@app.task(name="cgd.ping_health")
def ping_health() -> dict:
    return {"ok": True}
