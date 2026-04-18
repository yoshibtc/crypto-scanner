"""Pattern 6 — FDV up vs fees/revenue down (WoW proxy from stored snapshots)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from cgd.engine.facts_loader import (
    historical_fdv_wow_pcts,
    load_anchored_pair,
)
from cgd.patterns.types import EvaluationContext, GapCandidate

PATTERN_ID = "P6"
FDV_UP = 0.20
FEE_DOWN = 0.10
ANCHOR_HORIZON = timedelta(days=7)
ANCHOR_TOL = timedelta(hours=6)


def _num(x: Any) -> float | None:
    try:
        if x is None:
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def detect(ctx: EvaluationContext) -> list[GapCandidate]:
    old: dict[str, Any] | None = None
    new: dict[str, Any] | None = None

    if ctx.session is not None:
        old, new = load_anchored_pair(
            ctx.session,
            ctx.entity.id,
            "defillama_protocol",
            ctx.as_of,
            horizon=ANCHOR_HORIZON,
            tolerance=ANCHOR_TOL,
        )
    if old is None or new is None:
        rows = [r for r in ctx.market_rows if r.get("fact_type") == "defillama_protocol"]
        if len(rows) < 2:
            return []
        rows.sort(key=lambda r: r["source_ts"])
        old, new = rows[0], rows[-1]
        if new["source_ts"] - old["source_ts"] < timedelta(days=5):
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

    hist_pct: list[float] = []
    if ctx.session is not None:
        hist = historical_fdv_wow_pcts(ctx.session, ctx.entity.id)
        hist_pct = [h * 100.0 for h in hist]

    payload: dict[str, Any] = {
        "fdv_wow_pct": round(fdv_wow * 100, 4),
        "fee_wow_pct": round(fee_wow * 100, 4),
        "_gate_metric": round(fdv_wow * 100, 6),
        "_gate_history": hist_pct,
    }

    return [
        GapCandidate(
            pattern_id=PATTERN_ID,
            entity_id=ctx.entity.id,
            dedupe_key=dedupe,
            payload=payload,
            refs={"old_ts": old["source_ts"].isoformat(), "new_ts": new["source_ts"].isoformat()},
            reason_codes=["P6_FIRED"],
            side="short",
            invalidation={"type": "fee_wow_pct_above", "level": round(-FEE_DOWN * 100, 4)},
            half_life_minutes=24 * 60,
            tradable=True,
        )
    ]
