"""Pattern 6 — FDV up vs fees/revenue down (WoW proxy from stored snapshots)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from cgd.patterns.types import EvaluationContext, GapCandidate

PATTERN_ID = "P6"
FDV_UP = 0.20
FEE_DOWN = 0.10
MIN_GAP = timedelta(days=5)


def _num(x: Any) -> float | None:
    try:
        if x is None:
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def detect(ctx: EvaluationContext) -> list[GapCandidate]:
    rows = [r for r in ctx.market_rows if r.get("fact_type") == "defillama_protocol"]
    if len(rows) < 2:
        return []
    rows.sort(key=lambda r: r["source_ts"])
    old = rows[0]
    new = rows[-1]
    if new["source_ts"] - old["source_ts"] < MIN_GAP:
        return []

    po = old.get("payload") or {}
    pn = new.get("payload") or {}
    fdv_o = _num(po.get("fdv"))
    fdv_n = _num(pn.get("fdv"))
    fee_o = _num(po.get("fees")) or _num(po.get("revenue"))
    fee_n = _num(pn.get("fees")) or _num(pn.get("revenue"))
    if not fdv_o or not fdv_n or fdv_o <= 0:
        return []
    if fee_o is None or fee_n is None or fee_o <= 0:
        return []

    fdv_wow = (fdv_n - fdv_o) / fdv_o
    fee_wow = (fee_n - fee_o) / fee_o
    if fdv_wow <= FDV_UP:
        return []
    if fee_wow >= -FEE_DOWN:
        return []

    dedupe = f"{ctx.entity.id}:{PATTERN_ID}:{int(new['source_ts'].timestamp())}"
    return [
        GapCandidate(
            pattern_id=PATTERN_ID,
            entity_id=ctx.entity.id,
            dedupe_key=dedupe,
            payload={
                "fdv_wow_pct": round(fdv_wow * 100, 4),
                "fee_wow_pct": round(fee_wow * 100, 4),
            },
            refs={"old_ts": old["source_ts"].isoformat(), "new_ts": new["source_ts"].isoformat()},
            reason_codes=["P6_FIRED"],
        )
    ]
