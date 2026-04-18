"""Registered Tier-1 pattern modules (single source for runner + lifecycle)."""

from __future__ import annotations

from cgd.patterns.tier1 import TIER1

ALL_TIER1 = ["P7", "P6", "P10"]

PATTERN_BY_ID = {m.PATTERN_ID: m for m in TIER1}
