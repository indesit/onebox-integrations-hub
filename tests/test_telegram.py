import asyncio
import pytest
from unittest.mock import MagicMock, patch
from src.adapters.telegram.adapter import TelegramAdapter
from src.core.models import AdapterTask

@pytest.mark.asyncio
async def test_telegram_adapter_send_message_success():
    # Mock TelegramClient to avoid actual API calls
    with patch("src.adapters.telegram.adapter.TelegramClient") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.send_message = asyncio.Coroutine()
        mock_instance.send_message.return_value = {"ok": True, "result": {"message_id": 123}}

        adapter = TelegramAdapter()
        task = AdapterTask(
            task_id="test-123",
            adapter_name="telegram",
            action="send_message",
            data={
                "chat_id": 168847015,
                "text": "Hello from Epic 4 test!"
            }
        )

        result = await adapter.execute(task)

        assert result.success is True
        assert result.response_data["ok"] is True
        mock_instance.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_telegram_adapter_missing_fields():
    adapter = TelegramAdapter()
    task = AdapterTask(
        task_id="test-456",
        adapter_name="telegram",
        action="send_message",
        data={"chat_id": 168847015} # Missing text
    )

    result = await adapter.execute(task)
    assert result.success is False
    assert "Missing required fields" in result.error_message
