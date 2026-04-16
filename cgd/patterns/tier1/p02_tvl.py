"""Pattern 2 — Llama TVL WoW up vs on-chain native share of inflows (partial)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from cgd.patterns.types import EvaluationContext, GapCandidate

PATTERN_ID = "P2"
TVL_UP = 0.15
NATIVE_SHARE = 0.80
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

    tvl_o = _num((old.get("payload") or {}).get("tvl"))
    tvl_n = _num((new.get("payload") or {}).get("tvl"))
    if not tvl_o or not tvl_n or tvl_o <= 0:
        return []
    tvl_wow = (tvl_n - tvl_o) / tvl_o
    if tvl_wow <= TVL_UP:
        return []

    oc_rows = [r for r in ctx.onchain_rows if r.get("fact_type") == "tvl_composition"]
    if not oc_rows:
        return []
    comp = (oc_rows[-1].get("payload") or {})
    native_share = _num(comp.get("native_share_of_inflow"))
    if native_share is None or native_share < NATIVE_SHARE:
        return []

    dedupe = f"{ctx.entity.id}:{PATTERN_ID}"
    return [
        GapCandidate(
            pattern_id=PATTERN_ID,
            entity_id=ctx.entity.id,
            dedupe_key=dedupe,
            payload={"tvl_wow_pct": round(tvl_wow * 100, 4), "native_share": native_share},
            refs={"composition_ts": oc_rows[-1]["source_ts"].isoformat()},
            reason_codes=["P2_FIRED"],
        )
    ]
