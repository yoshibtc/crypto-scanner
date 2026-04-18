"""Record BTC regime (trend vs MA20 + realized-vol bucket) into market_facts."""

from __future__ import annotations

import statistics
from datetime import datetime, timezone

import ccxt

from cgd.db.engine import session_scope
from cgd.db.models import MarketFact
from cgd.workers.celery_app import app


@app.task(name="cgd.record_btc_regime", bind=True, max_retries=3)
def record_btc_regime(self) -> dict:
    now = datetime.now(timezone.utc)
    try:
        ex = ccxt.binance({"enableRateLimit": True})
        ohlcv = ex.fetch_ohlcv("BTC/USDT", "1d", limit=40)
        if len(ohlcv) < 21:
            return {"ok": False, "reason": "insufficient_ohlcv"}

        closes = [float(x[4]) for x in ohlcv]
        ma20 = sum(closes[-20:]) / 20.0
        last = closes[-1]
        trend = "up" if last >= ma20 else "down"

        rets: list[float] = []
        for i in range(1, len(closes)):
            if closes[i - 1]:
                rets.append(closes[i] / closes[i - 1] - 1.0)
        recent = rets[-30:] if len(rets) >= 30 else rets
        sd = statistics.stdev(recent) if len(recent) > 1 else 0.0
        ann_pct = sd * (365**0.5) * 100.0
        if ann_pct < 35:
            bucket = "low"
        elif ann_pct < 70:
            bucket = "mid"
        else:
            bucket = "high"

        payload = {
            "trend": trend,
            "realized_vol_bucket": bucket,
            "realized_vol_ann_pct": round(ann_pct, 4),
            "last_close": last,
            "ma20": ma20,
        }

        with session_scope() as session:
            mf = MarketFact(
                entity_id=None,
                fact_type="btc_regime",
                venue_id=None,
                pool_id=None,
                source_ts=now,
                ingested_at=now,
                payload=payload,
            )
            session.add(mf)

        return {"ok": True, "payload": payload}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=600) from exc
