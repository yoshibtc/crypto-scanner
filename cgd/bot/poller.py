"""
Telegram long-poll bot for CGD status commands.

Run with:  cgd-bot
or:        python -m cgd.bot.poller

The bot only responds to the configured TELEGRAM_CHAT_ID.
It uses the raw Bot API with long-polling so no extra dependencies are needed.
"""
from __future__ import annotations

import logging
import time

import httpx

from cgd.bot.commands import (
    cmd_alerts,
    cmd_gaps,
    cmd_health,
    cmd_help,
    cmd_invalidate,
    cmd_regime,
    cmd_resolve,
    cmd_status,
    cmd_watchlist,
    cmd_watchlist_add,
    cmd_watchlist_remove,
)
from cgd.db.engine import session_scope
from cgd.settings import get_settings

log = logging.getLogger(__name__)

POLL_TIMEOUT = 30  # seconds for long-poll


def _api(token: str, method: str, **kwargs) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    with httpx.Client(timeout=POLL_TIMEOUT + 5) as client:
        r = client.post(url, json=kwargs)
        r.raise_for_status()
        return r.json()


def _reply(token: str, chat_id: str | int, text: str) -> None:
    try:
        _api(
            token,
            "sendMessage",
            chat_id=chat_id,
            text=text,
            disable_web_page_preview=True,
        )
    except Exception as exc:
        log.error("Failed to send reply: %s", exc)


def _handle(token: str, allowed_chat: str, message: dict) -> None:
    chat_id = str(message.get("chat", {}).get("id", ""))
    if chat_id != str(allowed_chat):
        log.warning("Ignored message from unknown chat %s", chat_id)
        return

    text: str = message.get("text", "").strip()
    if not text.startswith("/"):
        return

    parts = text.split()
    command = parts[0].split("@")[0].lower()
    args = parts[1:]
    log.info("Command received: %s args=%s", command, args)

    try:
        if command == "/help":
            reply = cmd_help()
        elif command == "/status":
            with session_scope() as session:
                reply = cmd_status(session)
        elif command == "/watchlist":
            with session_scope() as session:
                reply = cmd_watchlist(session)
        elif command == "/watchlist_add":
            if len(args) < 1:
                reply = "Usage: /watchlist_add slug [display_name...]"
            else:
                slug = args[0]
                rest = " ".join(args[1:]).strip()
                with session_scope() as session:
                    reply = cmd_watchlist_add(session, slug, rest or None)
        elif command == "/watchlist_remove":
            if len(args) < 1:
                reply = "Usage: /watchlist_remove slug"
            else:
                with session_scope() as session:
                    reply = cmd_watchlist_remove(session, args[0])
        elif command == "/gaps":
            with session_scope() as session:
                reply = cmd_gaps(session)
        elif command == "/resolve":
            if len(args) < 1:
                reply = "Usage: /resolve <gap_id>"
            else:
                with session_scope() as session:
                    reply = cmd_resolve(session, int(args[0]))
        elif command == "/invalidate":
            if len(args) < 1:
                reply = "Usage: /invalidate <gap_id>"
            else:
                with session_scope() as session:
                    reply = cmd_invalidate(session, int(args[0]))
        elif command == "/regime":
            with session_scope() as session:
                reply = cmd_regime(session)
        elif command == "/alerts":
            with session_scope() as session:
                reply = cmd_alerts(session)
        elif command == "/health":
            with session_scope() as session:
                reply = cmd_health(session)
        else:
            reply = f"Unknown command: {command}\n\nType /help for a list of commands."
    except Exception as exc:
        log.exception("Error handling command %s", command)
        reply = f"Error running {command}: {exc}"

    _reply(token, chat_id, reply)


def run_poll_loop() -> None:
    s = get_settings()
    if not s.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set.")
    if not s.telegram_chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID is not set.")

    token = s.telegram_bot_token
    allowed_chat = s.telegram_chat_id

    log.info("CGD bot starting — polling for updates (allowed chat: %s)", allowed_chat)

    offset: int | None = None
    backoff = 1

    while True:
        try:
            params: dict = {"timeout": POLL_TIMEOUT, "allowed_updates": ["message"]}
            if offset is not None:
                params["offset"] = offset

            data = _api(token, "getUpdates", **params)
            updates = data.get("result", [])

            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message") or update.get("edited_message")
                if message:
                    _handle(token, allowed_chat, message)

            backoff = 1  # reset on success

        except httpx.HTTPStatusError as exc:
            log.error("HTTP error from Telegram API: %s", exc)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except httpx.RequestError as exc:
            log.warning("Network error, retrying in %ss: %s", backoff, exc)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except KeyboardInterrupt:
            log.info("Bot stopped by user.")
            break
        except Exception as exc:
            log.exception("Unexpected error: %s", exc)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_poll_loop()


if __name__ == "__main__":
    main()
