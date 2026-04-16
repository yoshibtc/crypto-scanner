from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def matrix_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "config" / "ccxt_matrix.yaml"


def load_matrix() -> dict[str, Any]:
    p = matrix_path()
    with p.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def iter_enabled_ccxt_source_keys() -> list[str]:
    """`source_health.source_key` values for enabled matrix venues only."""
    data = load_matrix()
    keys: list[str] = []
    for _name, cfg in (data.get("venues") or {}).items():
        if not isinstance(cfg, dict) or not cfg.get("enabled"):
            continue
        cid = cfg.get("ccxt_id") or _name
        if isinstance(cid, str) and cid:
            keys.append(f"ccxt:{cid}")
    # Same ccxt_id can appear under multiple YAML keys; health rows are per exchange id.
    return list(dict.fromkeys(keys))
