"""Telegram bot long-polling loop."""

import time
import httpx
from src.config.settings import settings
from src.core.logger import get_logger
from src.bot.handlers import handle_message

logger = get_logger(__name__)

BASE_URL = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
ADMIN_CHAT_ID = settings.telegram_admin_chat_id


def send_message(chat_id: str | int, text: str) -> None:
    try:
        httpx.post(f"{BASE_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }, timeout=10)
    except Exception as e:
        logger.error("tg_send_failed", chat_id=chat_id, error=str(e))


def get_updates(offset: int) -> list:
    try:
        res = httpx.get(f"{BASE_URL}/getUpdates", params={
            "offset": offset,
            "timeout": 30,
            "allowed_updates": ["message"],
        }, timeout=40)
        return res.json().get("result", [])
    except Exception as e:
        logger.error("tg_get_updates_failed", error=str(e))
        return []


def run_bot() -> None:
    if not settings.telegram_bot_token:
        logger.error("bot_no_token")
        return

    logger.info("bot_started")
    offset = 0

    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            text = msg.get("text", "")

            if not chat_id or not text:
                continue

            # Only respond to admin chat
            if ADMIN_CHAT_ID and str(chat_id) != str(ADMIN_CHAT_ID):
                logger.warning("bot_unauthorized_chat", chat_id=chat_id)
                continue

            logger.info("bot_command", chat_id=chat_id, text=text[:50])
            reply = handle_message(text)
            send_message(chat_id, reply)

        if not updates:
            time.sleep(1)


if __name__ == "__main__":
    run_bot()
