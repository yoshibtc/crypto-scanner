from __future__ import annotations

from typing import Any

from cgd.vesting.types import VestingReadResult


class UnknownVestingAdapter:
    adapter_id = "unknown"

    def read(self, chain: str, contract: str, context: dict[str, Any] | None = None) -> VestingReadResult:
        return VestingReadResult(
            adapter_id=self.adapter_id,
            coverage="UNKNOWN",
            segments=[],
            normalized={},
        )
