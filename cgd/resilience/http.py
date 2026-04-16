from __future__ import annotations

import random
import time
from typing import Any

import httpx

from cgd.settings import get_settings


def fetch_json(
    url: str,
    *,
    method: str = "GET",
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    settings = get_settings()
    max_retries = settings.http_max_retries
    timeout = settings.http_timeout_s
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                r = client.request(method, url, headers=headers, json=json_body)
                r.raise_for_status()
                return r.json()
        except (httpx.HTTPError, ValueError) as e:
            last_exc = e
            if attempt >= max_retries:
                break
            base = min(60.0, 0.5 * (2**attempt))
            jitter = random.uniform(0, base * 0.2)
            time.sleep(base + jitter)
    assert last_exc is not None
    raise last_exc
