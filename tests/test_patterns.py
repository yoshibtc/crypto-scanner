from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from cgd.patterns.tier1 import p06_revenue_fdv, p07_derivs, p10_stable
from cgd.patterns.types import EvaluationContext


def _entity(**kwargs):
    defaults = dict(
        id=1,
        slug="test",
        display_name="Test",
        semantics_version=1,
        llama_protocol_slugs=[],
        token_addresses={},
        ccxt_symbol_map={},
        rpc_chain=None,
        supply_source="stub",
        mapping_confidence=1.0,
        enabled_patterns=[],
        tvl_contract_allowlist=[],
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_p07_fires():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=24)
    rows = [
        {
            "fact_type": "ccxt_ticker",
            "venue_id": "binance",
            "pool_id": "BTC/USDT:USDT",
            "source_ts": t0,
            "payload": {
                "percentage": -0.2,
                "open_interest": {"openInterestAmount": 100.0},
                "funding_rate": -0.0006,
            },
        },
        {
            "fact_type": "ccxt_ticker",
            "venue_id": "binance",
            "pool_id": "BTC/USDT:USDT",
            "source_ts": t1,
            "payload": {
                "percentage": 0.1,
                "open_interest": {"openInterestAmount": 150.0},
                "funding_rate": -0.0006,
            },
        },
    ]
    ctx = EvaluationContext(
        entity=_entity(),
        as_of=t1,
        semantics_version=1,
        matrix_version=1,
        market_rows=rows,
        onchain_rows=[],
    )
    out = p07_derivs.detect(ctx)
    assert len(out) == 1
    assert out[0].pattern_id == "P7"


def test_p06_fires():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t1 = t0 + timedelta(days=7)
    rows = [
        {
            "fact_type": "defillama_protocol",
            "venue_id": None,
            "source_ts": t0,
            "payload": {"fdv": 100.0, "fees": 100.0},
        },
        {
            "fact_type": "defillama_protocol",
            "venue_id": None,
            "source_ts": t1,
            "payload": {"fdv": 130.0, "fees": 80.0},
        },
    ]
    ctx = EvaluationContext(
        entity=_entity(),
        as_of=t1,
        semantics_version=1,
        matrix_version=1,
        market_rows=rows,
        onchain_rows=[],
    )
    out = p06_revenue_fdv.detect(ctx)
    assert len(out) == 1


def test_p10_cex_stable():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i in range(4):
        rows.append(
            {
                "fact_type": "ccxt_ticker",
                "venue_id": "binance",
                "source_ts": base + timedelta(hours=i),
                "payload": {"last": 0.992},
            }
        )
    ctx = EvaluationContext(
        entity=_entity(slug="stable-usdt"),
        as_of=rows[-1]["source_ts"],
        semantics_version=1,
        matrix_version=1,
        market_rows=rows,
        onchain_rows=[],
    )
    out = p10_stable.detect(ctx)
    assert any(c.dedupe_key.endswith("P10:CEX") for c in out)


def test_p10_cex_skipped_when_ccxt_degraded():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i in range(4):
        rows.append(
            {
                "fact_type": "ccxt_ticker",
                "venue_id": "binance",
                "source_ts": base + timedelta(hours=i),
                "payload": {"last": 0.992},
            }
        )
    ctx = EvaluationContext(
        entity=_entity(slug="stable-usdt"),
        as_of=rows[-1]["source_ts"],
        semantics_version=1,
        matrix_version=1,
        market_rows=rows,
        onchain_rows=[],
        ccxt_degraded=True,
    )
    out = p10_stable.detect(ctx)
    assert not any(c.dedupe_key.endswith("P10:CEX") for c in out)
