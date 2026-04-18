"""Load deterministic pattern thresholds from YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PatternConfig:
    percentile_window_days: int = 30
    liquidity_quote_volume_floor_usd: float = 500_000.0
    gates: dict[str, dict[str, Any]] = field(default_factory=dict)
    regime_allowlist: dict[str, dict[str, Any]] = field(default_factory=dict)


def patterns_yaml_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "config" / "patterns.yaml"


def load_pattern_config() -> PatternConfig:
    p = patterns_yaml_path()
    if not p.exists():
        return PatternConfig()
    with p.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        return PatternConfig()
    return PatternConfig(
        percentile_window_days=int(raw.get("percentile_window_days", 30)),
        liquidity_quote_volume_floor_usd=float(
            raw.get("liquidity_quote_volume_floor_usd", 500_000)
        ),
        gates=dict(raw.get("gates") or {}),
        regime_allowlist=dict(raw.get("regime_allowlist") or {}),
    )
