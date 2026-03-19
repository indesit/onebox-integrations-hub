"""Telegram adapter implementation (Epic 4)."""

from src.adapters.base import BaseAdapter
from src.adapters.telegram.client import TelegramClient
from src.core.logger import get_logger
from src.core.models import AdapterResult, AdapterTask

logger = get_logger(__name__)


class TelegramAdapter(BaseAdapter):
    name = "telegram"

    def __init__(self) -> None:
        self.client = TelegramClient()

    async def execute(self, task: AdapterTask) -> AdapterResult:
        action = task.action or "send_message"
        if action != "send_message":
            return AdapterResult(
                task_id=task.task_id,
                success=False,
                error_message=f"Unknown action: {action}",
            )

        chat_id = task.data.get("chat_id")
        text = task.data.get("text")

        if chat_id is None or not text:
            return AdapterResult(
                task_id=task.task_id,
                success=False,
                error_message="Missing required fields: chat_id and text",
            )

        try:
            result_data = await self.client.send_message(
                chat_id=chat_id,
                text=str(text),
                parse_mode=task.data.get("parse_mode"),
                disable_web_page_preview=task.data.get("disable_web_page_preview"),
            )
            return AdapterResult(
                task_id=task.task_id,
                success=True,
                response_data=result_data,
            )
        except Exception as exc:
            logger.error(
                "telegram_adapter_execution_failed",
                task_id=task.task_id,
                error=str(exc),
            )
            return AdapterResult(
                task_id=task.task_id,
                success=False,
                error_message=str(exc),
            )
