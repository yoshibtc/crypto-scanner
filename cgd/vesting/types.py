from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Coverage = Literal["FULL", "PARTIAL", "UNKNOWN"]


@dataclass
class VestingReadResult:
    adapter_id: str
    coverage: Coverage
    segments: list[dict[str, Any]] = field(default_factory=list)
    normalized: dict[str, Any] = field(default_factory=dict)
