"""Pattern 10 — sub-signals: CEX peg drift (hourly) and DEX pool skew (on-chain)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from cgd.patterns.types import EvaluationContext, GapCandidate

PATTERN_ID = "P10"
PEG_DRIFT = 0.005  # 0.5%
CONSEC_HOURS = 4
POOL_SKEW = 0.70  # worse than 70/30 => major leg > 70%


def _is_stable_entity(ctx: EvaluationContext) -> bool:
    s = ctx.entity.slug.lower()
    return s.startswith("stable-") or "usdt" in s or "usdc" in s or "dai" in s


def _cex_leg(ctx: EvaluationContext) -> list[GapCandidate]:
    if ctx.ccxt_degraded:
        return []
    rows = [r for r in ctx.market_rows if r.get("fact_type") == "ccxt_ticker"]
    rows.sort(key=lambda r: r["source_ts"])
    if len(rows) < CONSEC_HOURS:
        return []
    last_n = rows[-CONSEC_HOURS:]
    drift_count = 0
    for r in last_n:
        last = (r.get("payload") or {}).get("last")
        try:
            px = float(last) if last is not None else None
        except (TypeError, ValueError):
            px = None
        if px is None:
            return []
        if abs(px - 1.0) > PEG_DRIFT:
            drift_count += 1
        else:
            return []
    if drift_count < CONSEC_HOURS:
        return []
    for i in range(len(last_n) - 1):
        if last_n[i + 1]["source_ts"] - last_n[i]["source_ts"] > timedelta(minutes=90):
            return []
    dedupe = f"{ctx.entity.id}:P10:CEX"
    return [
        GapCandidate(
            pattern_id=PATTERN_ID,
            entity_id=ctx.entity.id,
            dedupe_key=dedupe,
            payload={"leg": "CEX", "hours": CONSEC_HOURS, "peg_drift": PEG_DRIFT},
            refs={"last_ts": last_n[-1]["source_ts"].isoformat()},
            reason_codes=["P10_CEX_FIRED"],
        )
    ]


def _dex_leg(ctx: EvaluationContext) -> list[GapCandidate]:
    rows = [r for r in ctx.onchain_rows if r.get("fact_type") == "dex_pool_ratio"]
    if not rows:
        return []
    row = rows[-1]
    p = row.get("payload") or {}
    major = p.get("major_share")
    try:
        mj = float(major) if major is not None else None
    except (TypeError, ValueError):
        mj = None
    if mj is None or mj <= POOL_SKEW:
        return []
    dedupe = f"{ctx.entity.id}:P10:DEX"
    return [
        GapCandidate(
            pattern_id=PATTERN_ID,
            entity_id=ctx.entity.id,
            dedupe_key=dedupe,
            payload={"leg": "DEX", "major_share": mj},
            refs={"source_ts": row["source_ts"].isoformat()},
            reason_codes=["P10_DEX_FIRED"],
        )
    ]


def detect(ctx: EvaluationContext) -> list[GapCandidate]:
    if not _is_stable_entity(ctx):
        return []
    out: list[GapCandidate] = []
    out.extend(_cex_leg(ctx))
    out.extend(_dex_leg(ctx))
    return out
