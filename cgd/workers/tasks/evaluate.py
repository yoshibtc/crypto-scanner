from __future__ import annotations

from cgd.engine.runner import run_tier1_evaluation
from cgd.workers.celery_app import app


@app.task(name="cgd.evaluate_tier1", bind=True, max_retries=3)
def evaluate_tier1(self) -> dict:
    """Full Tier-1 run (all patterns, P10 full). Use for local one-shots."""
    try:
        return run_tier1_evaluation()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120) from exc


@app.task(name="cgd.evaluate_tier1_fast", bind=True, max_retries=3)
def evaluate_tier1_fast(self) -> dict:
    """Fast cadence: P7 + P10 CEX leg only."""
    try:
        return run_tier1_evaluation(pattern_ids=["P7", "P10"], p10_mode="cex_only")
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120) from exc


@app.task(name="cgd.evaluate_tier1_slow", bind=True, max_retries=3)
def evaluate_tier1_slow(self) -> dict:
    """Slow cadence: P6 fundamentals + P10 DEX leg only."""
    try:
        return run_tier1_evaluation(pattern_ids=["P6", "P10"], p10_mode="dex_only")
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120) from exc
