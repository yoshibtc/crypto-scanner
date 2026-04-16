from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from cgd.db.engine import session_scope
from cgd.db.models import Entity, EvaluationRun, GapStatus
from cgd.db.repos.gaps_repo import (
    escalate_gap_session,
    upsert_gap_candidate_session,
)
from cgd.db.repos.health_repo import any_enabled_ccxt_venue_degraded, is_source_degraded
from cgd.engine.facts_loader import load_market_fact_rows, load_onchain_fact_rows
from cgd.patterns.tier1 import TIER1
from cgd.patterns.types import EvaluationContext
from cgd.settings import get_settings

ALL_TIER1 = ["P7", "P6", "P10", "P2", "P1"]

PATTERN_BY_ID = {m.PATTERN_ID: m for m in TIER1}


def _inputs_hash(entity_id: int, market: list, onchain: list) -> str:
    blob = json.dumps(
        {"e": entity_id, "m": len(market), "o": len(onchain)},
        sort_keys=True,
    ).encode()
    return hashlib.sha256(blob).hexdigest()[:32]


def _skip_pattern_for_health(pattern_id: str) -> bool:
    if pattern_id == "P7" and any_enabled_ccxt_venue_degraded():
        return True
    if pattern_id in ("P6", "P2") and is_source_degraded("defillama", None):
        return True
    return False


def run_tier1_evaluation() -> dict[str, Any]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    summary: dict[str, Any] = {"candidates": 0, "gaps": 0, "escalated": 0}
    ccxt_degraded = any_enabled_ccxt_venue_degraded()

    with session_scope() as session:
        entities = list(session.execute(select(Entity)).scalars().all())
        for ent in entities:
            if ent.mapping_confidence < 0.3:
                continue
            enabled = ent.enabled_patterns or ALL_TIER1
            market = load_market_fact_rows(session, ent.id)
            onchain = load_onchain_fact_rows(session, ent.id)
            ctx = EvaluationContext(
                entity=ent,
                as_of=now,
                semantics_version=settings.semantics_version,
                matrix_version=settings.matrix_version,
                market_rows=market,
                onchain_rows=onchain,
                ccxt_degraded=ccxt_degraded,
            )
            ih = _inputs_hash(ent.id, market, onchain)
            er = EvaluationRun(
                entity_id=ent.id,
                semantics_version=settings.semantics_version,
                matrix_version=settings.matrix_version,
                as_of=now,
                inputs_hash=ih,
                shadow_mode=settings.shadow_mode,
                summary={},
                created_at=now,
            )
            session.add(er)

            for pid in enabled:
                mod = PATTERN_BY_ID.get(pid)
                if mod is None:
                    continue
                if _skip_pattern_for_health(pid):
                    continue
                for cand in mod.detect(ctx):
                    summary["candidates"] += 1
                    g, _ = upsert_gap_candidate_session(
                        session,
                        pattern_id=cand.pattern_id,
                        entity_id=cand.entity_id,
                        dedupe_key=cand.dedupe_key,
                        payload=cand.payload,
                        refs=cand.refs,
                        reason_codes=cand.reason_codes,
                        shadow_mode=settings.shadow_mode,
                    )
                    summary["gaps"] += 1
                    if not settings.shadow_mode and ent.mapping_confidence >= 0.5:
                        if g.status == GapStatus.DETECTED.value:
                            if escalate_gap_session(session, g.id, shadow_mode=False):
                                summary["escalated"] += 1

        session.flush()
    return summary
