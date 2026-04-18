from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select

from cgd.db.engine import session_scope
from cgd.db.models import Entity, EvaluationRun, Gap, GapStatus, MarketFact
from cgd.db.repos.gaps_repo import (
    escalate_gap_session,
    upsert_gap_candidate_session,
)
from cgd.db.repos.health_repo import any_enabled_ccxt_venue_degraded
from cgd.config.pattern_config import PatternConfig, load_pattern_config
from cgd.engine.eval_health import skip_pattern_for_health
from cgd.engine.facts_loader import load_market_fact_rows, load_onchain_fact_rows
from cgd.engine.liquidity import apply_liquidity_gate
from cgd.engine.stats import passes_percentile_gate
from cgd.engine.pattern_registry import ALL_TIER1, PATTERN_BY_ID
from cgd.patterns.types import EvaluationContext, GapCandidate, P10Mode
from cgd.settings import get_settings


def _inputs_hash(entity_id: int, market: list, onchain: list) -> str:
    blob = json.dumps(
        {"e": entity_id, "m": len(market), "o": len(onchain)},
        sort_keys=True,
    ).encode()
    return hashlib.sha256(blob).hexdigest()[:32]


def _finalize_payload(cand: GapCandidate) -> dict[str, Any]:
    out = {k: v for k, v in cand.payload.items() if not str(k).startswith("_")}
    out.setdefault("side", cand.side)
    out.setdefault("invalidation", cand.invalidation)
    out.setdefault("half_life_minutes", cand.half_life_minutes)
    out.setdefault("tradable", cand.tradable)
    return out


def _confluence_count(
    session,
    entity_id: int,
    pattern_id: str,
    window_hours: int,
    as_of: datetime,
) -> int:
    window_start = as_of - timedelta(hours=window_hours)
    stmt = (
        select(Gap.pattern_id)
        .where(
            Gap.entity_id == entity_id,
            Gap.opened_at >= window_start,
            Gap.opened_at <= as_of,
            Gap.pattern_id != pattern_id,
        )
        .distinct()
    )
    rows = session.execute(stmt).scalars().all()
    return len(rows)


def _load_latest_regime() -> dict[str, Any] | None:
    with session_scope() as session:
        stmt = (
            select(MarketFact)
            .where(MarketFact.fact_type == "btc_regime")
            .order_by(desc(MarketFact.source_ts))
            .limit(1)
        )
        row = session.execute(stmt).scalars().first()
        if row is None:
            return None
        return dict(row.payload or {})


def _regime_allows_pattern(
    pattern_cfg: PatternConfig,
    pattern_id: str,
    regime: dict[str, Any] | None,
) -> bool:
    if regime is None:
        return True
    allow = pattern_cfg.regime_allowlist.get(pattern_id)
    if not allow:
        return True
    trends = allow.get("trends")
    if trends and regime.get("trend") not in trends:
        return False
    vols = allow.get("vol_buckets")
    if vols and regime.get("realized_vol_bucket") not in vols:
        return False
    return True


def run_tier1_evaluation(
    pattern_ids: list[str] | None = None,
    *,
    p10_mode: P10Mode = "full",
) -> dict[str, Any]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    summary: dict[str, Any] = {"candidates": 0, "gaps": 0, "escalated": 0}
    pattern_cfg = load_pattern_config()
    ccxt_degraded = any_enabled_ccxt_venue_degraded()
    regime = _load_latest_regime()

    with session_scope() as session:
        entities = list(session.execute(select(Entity)).scalars().all())
        for ent in entities:
            if ent.mapping_confidence < 0.3:
                continue
            enabled = list(ent.enabled_patterns or ALL_TIER1)
            if pattern_ids is not None:
                allowed = set(pattern_ids)
                enabled = [p for p in enabled if p in allowed]
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
                session=session,
                p10_mode=p10_mode,
                regime=regime,
            )
            ih = _inputs_hash(ent.id, market, onchain)
            entity_summary: dict[str, Any] = {"candidates": 0, "gaps": 0, "escalated": 0}

            for pid in enabled:
                mod = PATTERN_BY_ID.get(pid)
                if mod is None:
                    continue
                if skip_pattern_for_health(pid):
                    continue
                if not _regime_allows_pattern(pattern_cfg, pid, regime):
                    continue
                for cand in mod.detect(ctx):
                    gcfg = pattern_cfg.gates.get(pid)
                    metric_val = cand.payload.get("_gate_metric")
                    if gcfg is not None and metric_val is not None:
                        hist = cand.payload.get("_gate_history") or []
                        gate_filter = {k: v for k, v in gcfg.items() if k != "metric"}
                        if not passes_percentile_gate(
                            hist,
                            float(metric_val),
                            pattern_cfg.percentile_window_days,
                            gate_filter,
                        ):
                            continue

                    conf = _confluence_count(session, ent.id, pid, 24, now)
                    cand.payload.setdefault("confluence_peers", conf)
                    cand.payload.setdefault("confluence_label", f"{conf}/5 peers in 24h")

                    apply_liquidity_gate(ent, cand, session, pattern_cfg)

                    clean_payload = _finalize_payload(cand)

                    summary["candidates"] += 1
                    entity_summary["candidates"] += 1
                    g, _ = upsert_gap_candidate_session(
                        session,
                        pattern_id=cand.pattern_id,
                        entity_id=cand.entity_id,
                        dedupe_key=cand.dedupe_key,
                        payload=clean_payload,
                        refs=cand.refs,
                        reason_codes=cand.reason_codes,
                        shadow_mode=settings.shadow_mode,
                    )
                    summary["gaps"] += 1
                    entity_summary["gaps"] += 1
                    if not settings.shadow_mode and ent.mapping_confidence >= 0.5:
                        if g.status == GapStatus.DETECTED.value:
                            if escalate_gap_session(session, g.id, shadow_mode=False):
                                summary["escalated"] += 1
                                entity_summary["escalated"] += 1

            er = EvaluationRun(
                entity_id=ent.id,
                semantics_version=settings.semantics_version,
                matrix_version=settings.matrix_version,
                as_of=now,
                inputs_hash=ih,
                shadow_mode=settings.shadow_mode,
                summary=entity_summary,
                created_at=now,
            )
            session.add(er)

        session.flush()
    return summary
