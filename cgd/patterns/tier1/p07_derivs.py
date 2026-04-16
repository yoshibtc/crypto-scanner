"""Pattern 7 — positioning / leverage stress (deterministic)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

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


def detect(ctx: EvaluationContext) -> list[GapCandidate]:
    rows = [
        r
        for r in ctx.market_rows
        if r.get("fact_type") == "ccxt_ticker" and r.get("venue_id")
    ]
    rows.sort(key=lambda r: r["source_ts"])
    if len(rows) < 2:
        return []

    old = rows[0]
    new = rows[-1]
    if new["source_ts"] - old["source_ts"] < timedelta(hours=20):
        return []

    p_old = old.get("payload") or {}
    p_new = new.get("payload") or {}
    try:
        chg = float(p_new["percentage"]) if p_new.get("percentage") is not None else None
    except (TypeError, ValueError):
        chg = None
    if chg is None:
        return []
    if chg > FLAT_OR_DOWN_PCT:
        return []

    oi_o = _extract_oi(p_old)
    oi_n = _extract_oi(p_new)
    if not oi_o or oi_o <= 0 or oi_n is None:
        return []
    oi_up = (oi_n - oi_o) / oi_o
    if oi_up <= OI_UP:
        return []

    fr = p_new.get("funding_rate")
    try:
        fr_f = float(fr) if fr is not None else None
    except (TypeError, ValueError):
        fr_f = None
    if fr_f is None or fr_f >= FUNDING_MAX:
        return []

    dedupe = f"{ctx.entity.id}:{new['venue_id']}:{PATTERN_ID}"
    return [
        GapCandidate(
            pattern_id=PATTERN_ID,
            entity_id=ctx.entity.id,
            dedupe_key=dedupe,
            payload={
                "oi_change_pct": round(oi_up * 100, 4),
                "funding_rate": fr_f,
                "price_change_pct_24h": chg,
                "venue": new["venue_id"],
                "framing": "positioning_leverage_stress",
            },
            refs={"old_fact_ts": old["source_ts"].isoformat(), "new_fact_ts": new["source_ts"].isoformat()},
            reason_codes=["P7_FIRED"],
        )
    ]
