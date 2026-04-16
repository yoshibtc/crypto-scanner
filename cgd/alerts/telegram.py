from __future__ import annotations

import httpx

from cgd.settings import get_settings


def send_telegram_text(text: str) -> bool:
    s = get_settings()
    if not s.telegram_bot_token or not s.telegram_chat_id:
        return False
    url = f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage"
    body = {
        "chat_id": s.telegram_chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    with httpx.Client(timeout=30.0) as client:
        r = client.post(url, json=body)
        r.raise_for_status()
    return True
