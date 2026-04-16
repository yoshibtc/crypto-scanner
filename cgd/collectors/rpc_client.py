from __future__ import annotations

import os
import random
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from cgd.db.repos.health_repo import touch_failure, touch_success


def _rpc_urls_for_chain(chain: str) -> list[str]:
    key = f"RPC_URLS_{chain.upper()}"
    raw = os.environ.get(key, "")
    if not raw:
        return []
    return [u.strip() for u in raw.split(",") if u.strip()]


def eth_block_number(url: str) -> int:
    body = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
    with httpx.Client(timeout=20.0) as client:
        r = client.post(url, json=body)
        r.raise_for_status()
        j = r.json()
        return int(j["result"], 16)


def check_rpc_health() -> dict[str, Any]:
    """Primary + fallback: compare block heights; mark degraded if lag > threshold."""
    now = datetime.now(timezone.utc)
    out: dict[str, Any] = {"checked_at": now.isoformat(), "chains": {}}
    for chain in ("ethereum",):
        urls = _rpc_urls_for_chain(chain)
        if len(urls) < 1:
            out["chains"][chain] = {"skipped": True, "reason": "no RPC_URLS_* env"}
            continue
        heights: list[tuple[str, int]] = []
        for url in urls:
            try:
                h = eth_block_number(url)
                heights.append((urlparse(url).netloc or url, h))
                touch_success(f"rpc:{chain}", url)
            except Exception as e:
                touch_failure(f"rpc:{chain}", url, str(e))
        if not heights:
            out["chains"][chain] = {"ok": False, "error": "all endpoints failed"}
            continue
        max_h = max(h for _, h in heights)
        degraded = any(max_h - h > 8 for _, h in heights)
        out["chains"][chain] = {
            "heights": [{"host": n, "block": h} for n, h in heights],
            "degraded": degraded,
        }
        if degraded:
            out["chains"][chain]["note"] = "peer_lag_threshold_exceeded"
    return out
