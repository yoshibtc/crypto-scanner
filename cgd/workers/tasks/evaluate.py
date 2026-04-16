from cgd.engine.runner import run_tier1_evaluation
from cgd.workers.celery_app import app


@app.task(name="cgd.evaluate_tier1", bind=True, max_retries=3)
def evaluate_tier1(self) -> dict:
    try:
        return run_tier1_evaluation()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120) from exc
