from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from cgd.db.engine import session_scope
from cgd.db.models import Entity, MarketFact
from cgd.db.repos.health_repo import touch_failure, touch_success
from cgd.resilience.http import fetch_json
from cgd.settings import get_settings


def _protocol_url(slug: str) -> str:
    base = get_settings().defillama_base_url.rstrip("/")
    return f"{base}/protocol/{slug}"


def _coerce_num(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, dict) and "total24h" in val:
        return val.get("total24h")
    if isinstance(val, dict) and "total7d" in val:
        return val.get("total7d")
    return val


def extract_protocol_snapshot(data: dict[str, Any], slug: str) -> dict[str, Any]:
    """Normalize common DeFiLlama protocol shapes into flat metrics for patterns."""
    tvl = data.get("tvl")
    fdv = data.get("fdv") or data.get("mcap")
    fees = _coerce_num(data.get("fees"))
    revenue = _coerce_num(data.get("revenue"))
    metrics = data.get("metrics")
    if isinstance(metrics, dict):
        if fees is None:
            fees = _coerce_num(metrics.get("fees") or metrics.get("totalFees"))
        if revenue is None:
            revenue = _coerce_num(metrics.get("revenue") or metrics.get("totalRevenue"))
        if fdv is None:
            fdv = _coerce_num(metrics.get("fdv") or metrics.get("mcap"))
    return {
        "slug": slug,
        "tvl": tvl,
        "fdv": fdv,
        "fees": fees,
        "revenue": revenue,
        "raw_keys": list(data.keys())[:40],
    }


def ingest_defillama_snapshot() -> int:
    now = datetime.now(timezone.utc)
    count = 0
    source_key = "defillama"
    try:
        with session_scope() as session:
            entities = list(session.execute(select(Entity)).scalars().all())
            for ent in entities:
                for slug in ent.llama_protocol_slugs or []:
                    try:
                        data: dict[str, Any] = fetch_json(_protocol_url(slug))
                        payload = extract_protocol_snapshot(data, slug)
                        mf = MarketFact(
                            entity_id=ent.id,
                            fact_type="defillama_protocol",
                            venue_id=None,
                            pool_id=None,
                            source_ts=now,
                            ingested_at=now,
                            payload=payload,
                        )
                        session.add(mf)
                        count += 1
                    except Exception:
                        continue
        touch_success(source_key, None)
    except Exception as e:
        touch_failure(source_key, None, str(e))
        raise
    return count
