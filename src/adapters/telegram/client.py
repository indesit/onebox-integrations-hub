"""Async HTTP client for Telegram Bot API (Epic 4)."""

from typing import Any

import httpx

from src.config.settings import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


class TelegramClient:
    def __init__(self) -> None:
        if not settings.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not configured")

        self.base_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
        self.timeout = httpx.Timeout(10.0, connect=5.0)

    async def _request(self, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "telegram_api_error",
                    status_code=exc.response.status_code,
                    detail=exc.response.text,
                    url=url,
                )
                raise
            except Exception as exc:
                logger.error("telegram_client_exception", error=str(exc), url=url)
                raise

    async def send_message(
        self,
        chat_id: str | int,
        text: str,
        parse_mode: str | None = None,
        disable_web_page_preview: bool | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }

        if parse_mode:
            payload["parse_mode"] = parse_mode
        if disable_web_page_preview is not None:
            payload["disable_web_page_preview"] = disable_web_page_preview

        return await self._request("POST", "/sendMessage", json=payload)
