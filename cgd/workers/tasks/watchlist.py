from __future__ import annotations

import ccxt

from cgd.db.engine import session_scope
from cgd.db.models import Entity
from cgd.db.repos.entities_repo import disable_entity, upsert_entity
from cgd.workers.celery_app import app
from sqlalchemy import select

TOP_N = 50
FLOOR_USD = 5_000_000.0


def _slug(sym: str) -> str:
    return f"{sym.split('/')[0].lower()}-usdt-perp"


@app.task(name="cgd.refresh_perp_watchlist", bind=True, max_retries=3)
def refresh_perp_watchlist(self) -> dict:
    try:
        ex = ccxt.binanceusdm({"enableRateLimit": True})
        ex.load_markets()
        tickers = ex.fetch_tickers()

        ranked: list[tuple[str, float]] = []
        for sym, t in tickers.items():
            m = ex.markets.get(sym)
            if not m or not m.get("swap"):
                continue
            if not sym.endswith(":USDT"):
                continue
            try:
                qv = float(t.get("quoteVolume") or 0)
            except (TypeError, ValueError):
                continue
            if qv < FLOOR_USD:
                continue
            ranked.append((sym, qv))

        ranked.sort(key=lambda x: -x[1])
        picked = ranked[:TOP_N]
        active_slugs = {_slug(sym) for sym, _ in picked}

        with session_scope() as session:
            for sym, _ in picked:
                upsert_entity(
                    session,
                    slug=_slug(sym),
                    display_name=f"{sym} (Binance USDT-M)",
                    llama_protocol_slugs=[],
                    ccxt_symbol_map={"binance_perp": {"swap": sym, "perp": sym}},
                    mapping_confidence=0.72,
                    enabled_patterns=["P7"],
                )

            # Disable perp entities that dropped out of the top N
            all_perps = list(
                session.execute(
                    select(Entity).where(Entity.slug.like("%-usdt-perp"))
                ).scalars()
            )
            disabled = 0
            for ent in all_perps:
                if ent.slug not in active_slugs and ent.mapping_confidence > 0:
                    disable_entity(session, ent.slug)
                    disabled += 1

        return {"upserted": len(picked), "disabled": disabled}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=600) from exc
