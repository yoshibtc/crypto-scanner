from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cgd.db.models import Entity


@dataclass
class GapCandidate:
    pattern_id: str
    entity_id: int
    dedupe_key: str
    payload: dict[str, Any]
    refs: dict[str, Any]
    reason_codes: list[str] = field(default_factory=list)


@dataclass
class EvaluationContext:
    entity: Entity
    as_of: datetime
    semantics_version: int
    matrix_version: int
    market_rows: list[dict[str, Any]]
    onchain_rows: list[dict[str, Any]]
    # Set by engine from source_health; patterns stay free of DB imports.
    ccxt_degraded: bool = False
