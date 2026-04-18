"""Shared health checks for skipping patterns during evaluation."""

from __future__ import annotations

from cgd.db.repos.health_repo import any_enabled_ccxt_venue_degraded, is_source_degraded


def skip_pattern_for_health(pattern_id: str) -> bool:
    """Return True if this pattern should not run due to degraded upstream sources."""
    if pattern_id == "P7" and any_enabled_ccxt_venue_degraded():
        return True
    if pattern_id in ("P6", "P2") and is_source_degraded("defillama", None):
        return True
    return False
