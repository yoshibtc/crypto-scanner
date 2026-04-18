"""Gap lifecycle repo behaviour."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import sessionmaker

from cgd.db.models import Entity, Gap, GapStatus
from cgd.db.repos.gaps_repo import upsert_gap_candidate_session


def test_reopen_resolved_gap(memory_engine, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    factory = sessionmaker(bind=memory_engine)
    session = factory()
    now = datetime.now(timezone.utc)
    ent = Entity(
        slug="lifecycle-test",
        display_name="Lifecycle Test",
        semantics_version=1,
        llama_protocol_slugs=[],
        token_addresses={},
        ccxt_symbol_map={},
        rpc_chain=None,
        supply_source="stub",
        mapping_confidence=1.0,
        enabled_patterns=["P7"],
        tvl_contract_allowlist=[],
        created_at=now,
        updated_at=now,
    )
    session.add(ent)
    session.flush()
    g = Gap(
        pattern_id="P7",
        entity_id=ent.id,
        status=GapStatus.RESOLVED.value,
        dedupe_key="test-dedupe",
        opened_at=now,
        payload_json={},
        supporting_observation_refs={},
        resolve_miss_streak=0,
        resolved_at=now,
        alert_dispatched_at=now,
    )
    session.add(g)
    session.commit()

    _, ev = upsert_gap_candidate_session(
        session,
        pattern_id="P7",
        entity_id=ent.id,
        dedupe_key="test-dedupe",
        payload={"oi_change_pct": 99.0},
        refs={},
        reason_codes=["TEST"],
        shadow_mode=False,
    )
    session.commit()

    assert ev == "reopened"
    session.refresh(g)
    assert g.status == GapStatus.DETECTED.value
    assert g.alert_dispatched_at is None
    assert g.resolved_at is None
    session.close()
