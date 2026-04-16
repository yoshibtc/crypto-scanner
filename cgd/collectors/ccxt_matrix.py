from __future__ import annotations

from typing import Any

from cgd.config.ccxt_matrix_loader import load_matrix
from cgd.db.repos.health_repo import touch_failure, touch_success


def verify_matrix_against_exchanges() -> dict[str, Any]:
    import ccxt

    data = load_matrix()
    results: dict[str, Any] = {"matrix_version": data.get("matrix_version"), "venues": {}}
    for name, cfg in (data.get("venues") or {}).items():
        if not isinstance(cfg, dict) or not cfg.get("enabled"):
            results["venues"][name] = {"skipped": True}
            continue
        cid = cfg.get("ccxt_id") or name
        source_key = f"ccxt:{cid}"
        try:
            cls = getattr(ccxt, cid)
            ex = cls({"enableRateLimit": True})
            ex.load_markets()
            ok = bool(ex.markets)
            results["venues"][name] = {"ok": ok, "markets": len(ex.markets)}
            if ok:
                touch_success(source_key, None)
            else:
                touch_failure(source_key, None, "load_markets_empty")
        except Exception as e:
            results["venues"][name] = {"ok": False, "error": str(e)[:500]}
            touch_failure(source_key, None, str(e)[:500])
    return results
