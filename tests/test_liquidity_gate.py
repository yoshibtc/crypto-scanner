"""Liquidity gate skips when no CCXT mapping exists."""

from __future__ import annotations

from types import SimpleNamespace

from cgd.config.pattern_config import PatternConfig
from cgd.engine.liquidity import apply_liquidity_gate
from cgd.patterns.types import GapCandidate


def test_liquidity_gate_skips_when_no_ccxt_map():
    cfg = PatternConfig(
        percentile_window_days=30,
        liquidity_quote_volume_floor_usd=500_000.0,
        gates={},
        regime_allowlist={},
    )
    ent = SimpleNamespace(id=1, ccxt_symbol_map={})
    cand = GapCandidate(
        pattern_id="P6",
        entity_id=1,
        dedupe_key="x",
        payload={},
        refs={},
        reason_codes=[],
        side="short",
        invalidation={},
        half_life_minutes=60,
        tradable=True,
    )
    apply_liquidity_gate(ent, cand, session=None, cfg=cfg)
    assert cand.tradable is True
    assert cand.payload.get("liquidity_note") == "NO_CEX_MAP_skipped"
