"""Pattern 7 — positioning / leverage stress (deterministic)."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any

from cgd.engine.facts_loader import historical_venue_oi_change_pcts
from cgd.patterns.types import EvaluationContext, GapCandidate

PATTERN_ID = "P7"

OI_UP = 0.25
FUNDING_MAX = -0.0005  # -0.05% as decimal (ccxt fundingRate)
FLAT_OR_DOWN_PCT = 0.5  # ccxt ticker `percentage` is usually % points


def _extract_oi(payload: dict[str, Any]) -> float | None:
    oi = payload.get("open_interest")
    if oi is None:
        return None
    if isinstance(oi, dict):
        for k in ("openInterestAmount", "openInterest", "amount", "value"):
            if k in oi and oi[k] is not None:
                try:
                    return float(oi[k])
                except (TypeError, ValueError):
                    continue
        return None
    try:
        return float(oi)
    except (TypeError, ValueError):
        return None


def _detect_one_venue(
    ctx: EvaluationContext,
    vid: str,
    rows: list[dict[str, Any]],
) -> GapCandidate | None:
    rows.sort(key=lambda r: r["source_ts"])
    if len(rows) < 2:
        return None

    old = rows[0]
    new = rows[-1]
    if new["source_ts"] - old["source_ts"] < timedelta(hours=20):
        return None

    p_old = old.get("payload") or {}
    p_new = new.get("payload") or {}
    try:
        chg = float(p_new["percentage"]) if p_new.get("percentage") is not None else None
    except (TypeError, ValueError):
        chg = None
    if chg is None:
        return None
    if chg > FLAT_OR_DOWN_PCT:
        return None

    oi_o = _extract_oi(p_old)
    oi_n = _extract_oi(p_new)
    if not oi_o or oi_o <= 0 or oi_n is None:
        return None
    oi_up = (oi_n - oi_o) / oi_o
    if oi_up <= OI_UP:
        return None

    fr = p_new.get("funding_rate")
    try:
        fr_f = float(fr) if fr is not None else None
    except (TypeError, ValueError):
        fr_f = None
    if fr_f is None or fr_f >= FUNDING_MAX:
        return None

    oi_change_pct = round(oi_up * 100, 4)
    hist_pct: list[float] = []
    if ctx.session is not None:
        hist = historical_venue_oi_change_pcts(ctx.session, ctx.entity.id, vid)
        hist_pct = [h * 100.0 for h in hist]

    dedupe = f"{ctx.entity.id}:{vid}:{PATTERN_ID}"
    payload: dict[str, Any] = {
        "oi_change_pct": oi_change_pct,
        "funding_rate": fr_f,
        "price_change_pct_24h": chg,
        "venue": vid,
        "framing": "positioning_leverage_stress",
        "_gate_metric": float(oi_change_pct),
        "_gate_history": hist_pct,
    }
    return GapCandidate(
        pattern_id=PATTERN_ID,
        entity_id=ctx.entity.id,
        dedupe_key=dedupe,
        payload=payload,
        refs={"old_fact_ts": old["source_ts"].isoformat(), "new_fact_ts": new["source_ts"].isoformat()},
        reason_codes=["P7_FIRED"],
        side="watch",
        invalidation={"type": "funding_above", "level": FUNDING_MAX},
        half_life_minutes=240,
        tradable=True,
    )


def detect(ctx: EvaluationContext) -> list[GapCandidate]:
    venue_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in ctx.market_rows:
        if r.get("fact_type") == "ccxt_ticker" and r.get("venue_id"):
            venue_rows[str(r["venue_id"])].append(r)

    out: list[GapCandidate] = []
    for vid, rows in venue_rows.items():
        cand = _detect_one_venue(ctx, vid, rows)
        if cand is not None:
            out.append(cand)
    return out
