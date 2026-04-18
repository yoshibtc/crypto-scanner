"""Historical FDV WoW uses ~7d anchors (not consecutive ingest jitter)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from cgd.engine.facts_loader import _fdv_wow_ratios_at_horizon
from cgd.engine.stats import percentile_rank


def test_fdv_wow_percentile_high_for_step_change():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i in range(25):
        rows.append(
            SimpleNamespace(
                source_ts=base + timedelta(days=i),
                payload={"fdv": 100.0},
            )
        )
    for i in range(25, 31):
        rows.append(
            SimpleNamespace(
                source_ts=base + timedelta(days=i),
                payload={"fdv": 100.0 + (i - 25) * 20.0},
            )
        )

    wows = _fdv_wow_ratios_at_horizon(
        rows,
        horizon=timedelta(days=7),
        tolerance=timedelta(hours=6),
        max_pairs=200,
    )
    assert wows
    last = wows[-1]
    hist = wows[:-1]
    pr = percentile_rank(hist, last)
    assert pr > 0.85
