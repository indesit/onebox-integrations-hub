"""Daily digest sender — runs as RQ job.

Sends the digest to all authorized users with role owner or admin.
Falls back to TELEGRAM_ADMIN_CHAT_ID env var if no users are persisted yet.
"""

import httpx
from src.config.settings import settings
from src.bot.handlers import cmd_digest
from src.bot.roles import list_users
from src.core.logger import get_logger

logger = get_logger(__name__)

_SEND_URL = "https://api.telegram.org/bot{token}/sendMessage"


def _send(chat_id: str | int, text: str) -> None:
    try:
        httpx.post(
            _SEND_URL.format(token=settings.telegram_bot_token),
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
    except Exception as e:
        logger.error("digest_send_failed", chat_id=chat_id, error=str(e))


def send_daily_digest() -> None:
    if not settings.telegram_bot_token:
        logger.warning("digest_skipped_no_token")
        return

    text = cmd_digest("")

    # Send to all owner/admin users
    recipients = [u["user_id"] for u in list_users() if u["role"] in ("owner", "admin")]

    # Fallback: legacy env var
    if not recipients and settings.telegram_admin_chat_id:
        recipients = [settings.telegram_admin_chat_id]

    if not recipients:
        logger.warning("digest_skipped_no_recipients")
        return

    for chat_id in recipients:
        _send(chat_id, text)
        logger.info("digest_sent", chat_id=chat_id)
