"""Rolling percentile / distribution helpers for pattern gates."""

from __future__ import annotations

from typing import Any


def percentile_rank(sorted_values: list[float], value: float) -> float:
    """Return empirical percentile rank of ``value`` in ``sorted_values`` (0–1)."""
    if not sorted_values:
        return 0.5
    xs = sorted(sorted_values)
    n = len(xs)
    below = sum(1 for x in xs if x < value)
    eq = sum(1 for x in xs if x == value)
    return (below + 0.5 * eq) / n if n else 0.5


def passes_percentile_gate(
    hist: list[float],
    value: float,
    _window_days: int,
    gate: dict[str, Any],
) -> bool:
    """Return True if value's percentile rank falls within [min_percentile, max_percentile]."""
    if not hist:
        return True
    pr = percentile_rank(hist, value)
    mn = float(gate.get("min_percentile", 0.0))
    mx = float(gate.get("max_percentile", 1.0))
    return mn <= pr <= mx
