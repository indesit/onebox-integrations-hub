import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HubEvent(BaseModel):
    """Normalized event entering the Hub from any source."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str                          # e.g. "onebox", "scheduler"
    event_type: str                      # e.g. "deal_created", "deal_updated"
    payload: dict[str, Any]
    received_at: datetime = Field(default_factory=datetime.utcnow)


class AdapterTask(BaseModel):
    """Unit of work dispatched to an adapter."""

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    adapter_name: str                    # e.g. "telegram", "onebox"
    action: str = ""                     # e.g. "send_message", "update_deal"
    data: dict[str, Any]
    attempt: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AdapterResult(BaseModel):
    """Result returned by an adapter after executing a task."""

    task_id: str
    success: bool
    error_message: str | None = None
    response_data: dict[str, Any] | None = None
    completed_at: datetime = Field(default_factory=datetime.utcnow)
