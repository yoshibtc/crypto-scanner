"""Pattern 1 — unlock pressure vs liquidity (data-only; suppressed on PARTIAL/UNKNOWN)."""

from __future__ import annotations

from typing import Any

from cgd.patterns.types import EvaluationContext, GapCandidate

PATTERN_ID = "P1"
SUPPLY_PCT = 0.05
DAYS = 7
VOL_MULT = 3.0


def _num(x: Any) -> float | None:
    try:
        if x is None:
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def detect(ctx: EvaluationContext) -> list[GapCandidate]:
    rows = [r for r in ctx.onchain_rows if r.get("fact_type") == "vesting_schedule"]
    if not rows:
        return []
    row = rows[-1]
    p = row.get("payload") or {}
    coverage = p.get("coverage", "UNKNOWN")
    if coverage in ("UNKNOWN", "PARTIAL"):
        return []

    unlock_pct_circ = _num(p.get("unlock_pct_circulating_within_7d"))
    unlock_fiat = _num(p.get("unlock_fiat_value"))
    adv = _num(p.get("adv_14d_quote"))
    if unlock_pct_circ is None or unlock_fiat is None or adv is None or adv <= 0:
        return []
    if unlock_pct_circ <= SUPPLY_PCT:
        return []
    if unlock_fiat <= VOL_MULT * adv:
        return []

    dedupe = f"{ctx.entity.id}:{PATTERN_ID}:{row['source_ts'].date().isoformat()}"
    return [
        GapCandidate(
            pattern_id=PATTERN_ID,
            entity_id=ctx.entity.id,
            dedupe_key=dedupe,
            payload={
                "unlock_pct_circ": unlock_pct_circ,
                "unlock_fiat": unlock_fiat,
                "adv_14d": adv,
            },
            refs={"vesting_adapter": p.get("adapter_id"), "source_ts": row["source_ts"].isoformat()},
            reason_codes=["P1_FIRED"],
        )
    ]
