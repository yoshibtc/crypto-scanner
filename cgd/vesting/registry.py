from __future__ import annotations

from typing import Any

from cgd.vesting.adapters.unknown import UnknownVestingAdapter

_REGISTRY: dict[str, Any] = {
    "unknown": UnknownVestingAdapter(),
}


def get_adapter(name: str):
    return _REGISTRY.get(name) or _REGISTRY["unknown"]
