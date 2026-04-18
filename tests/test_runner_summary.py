"""EvaluationRun.summary suppression counters."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import sessionmaker

from cgd.db.models import Entity
from cgd.engine.runner import run_tier1_evaluation


def test_run_summary_has_suppression_counters(memory_engine, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    factory = sessionmaker(bind=memory_engine)
    session = factory()
    now = datetime.now(timezone.utc)
    session.add(
        Entity(
            slug="runner-sum",
            display_name="Runner Sum",
            semantics_version=1,
            llama_protocol_slugs=[],
            token_addresses={},
            ccxt_symbol_map={"binance": {"spot": "BTC/USDT"}},
            rpc_chain=None,
            supply_source="stub",
            mapping_confidence=1.0,
            enabled_patterns=["P7", "P6", "P10"],
            tvl_contract_allowlist=[],
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()
    session.close()

    monkeypatch.setattr("cgd.engine.runner.skip_pattern_for_health", lambda _pid: True)
    monkeypatch.setattr("cgd.engine.runner.any_enabled_ccxt_venue_degraded", lambda: False)
    monkeypatch.setattr("cgd.engine.runner.load_market_fact_rows", lambda _s, _eid: [])
    monkeypatch.setattr("cgd.engine.runner.load_onchain_fact_rows", lambda _s, _eid: [])
    monkeypatch.setattr("cgd.engine.runner._load_latest_regime", lambda: None)

    out = run_tier1_evaluation()
    assert out["suppressed_health"] == 3
    assert out["suppressed_regime"] == 0
