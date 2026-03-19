"""Webhook normalizer for OneBox (OB-002)."""

from typing import Any
from src.core.models import HubEvent

class OneBoxNormalizer:
    @staticmethod
    def to_hub_event(raw_payload: dict[str, Any]) -> HubEvent:
        """Translates OneBox webhook payload to a standard HubEvent."""
        
        # OneBox usually sends the event type in 'event' or 'action' field
        # Добавляем fallback на 'event_type' из нашего тестового запроса
        event_type = raw_payload.get("event", raw_payload.get("action", raw_payload.get("event_type", "unknown")))
        
        return HubEvent(
            source="onebox",
            event_type=event_type,
            payload=raw_payload
        )
