from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import ccxt
from sqlalchemy import select

from cgd.config.ccxt_matrix_loader import load_matrix
from cgd.db.engine import session_scope
from cgd.db.models import Entity, MarketFact
from cgd.db.repos.health_repo import touch_failure, touch_success


def _exchange(cid: str) -> ccxt.Exchange:
    cls = getattr(ccxt, cid)
    return cls({"enableRateLimit": True})


def ingest_ccxt_snapshot() -> int:
    now = datetime.now(timezone.utc)
    matrix = load_matrix()
    count = 0
    with session_scope() as session:
        entities = list(session.execute(select(Entity)).scalars().all())
        for vname, vcfg in (matrix.get("venues") or {}).items():
            if not isinstance(vcfg, dict) or not vcfg.get("enabled"):
                continue
            cid = vcfg.get("ccxt_id") or vname
            source_key = f"ccxt:{cid}"
            try:
                ex = _exchange(cid)
                ex.load_markets()
                for ent in entities:
                    cmap = ent.ccxt_symbol_map or {}
                    venue_map = cmap.get(cid) or cmap.get(vname) or {}
                    sym = venue_map.get("spot") or venue_map.get("perp") or venue_map.get("swap")
                    if not sym or sym not in ex.markets:
                        continue
                    ticker = ex.fetch_ticker(sym)
                    oi = None
                    funding = None
                    if venue_map.get("swap") and venue_map.get("swap") in ex.markets:
                        try:
                            if ex.has.get("fetchOpenInterest"):
                                oi = ex.fetch_open_interest(venue_map["swap"])
                        except Exception:
                            oi = None
                        try:
                            if ex.has.get("fetchFundingRate"):
                                fr = ex.fetch_funding_rate(venue_map["swap"])
                                funding = fr.get("fundingRate") if isinstance(fr, dict) else None
                        except Exception:
                            funding = None
                    payload: dict[str, Any] = {
                        "symbol": sym,
                        "last": ticker.get("last"),
                        "quoteVolume": ticker.get("quoteVolume"),
                        "percentage": ticker.get("percentage"),
                        "open_interest": oi,
                        "funding_rate": funding,
                    }
                    mf = MarketFact(
                        entity_id=ent.id,
                        fact_type="ccxt_ticker",
                        venue_id=cid,
                        pool_id=sym,
                        source_ts=now,
                        ingested_at=now,
                        payload=payload,
                    )
                    session.add(mf)
                    count += 1
                touch_success(source_key, None)
            except Exception as e:
                touch_failure(source_key, None, str(e))
    return count
