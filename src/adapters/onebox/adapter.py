"""OneBox Adapter implementation (OB-003, OB-004, OB-005)."""

from typing import Any
from src.adapters.base import BaseAdapter
from src.adapters.onebox.client import OneBoxClient
from src.core.models import AdapterTask, AdapterResult
from src.core.logger import get_logger

logger = get_logger(__name__)

class OneBoxAdapter(BaseAdapter):
    name = "onebox"

    def __init__(self):
        self.client = OneBoxClient()

    async def execute(self, task: AdapterTask) -> AdapterResult:
        """Executes outbound actions in OneBox."""
        action = task.action
        data = task.data
        
        try:
            result_data = {}
            if action == "upsert_contact":
                result_data = await self.client.upsert_contact(data)
            elif action == "create_order":
                result_data = await self.client.create_order(data)
            else:
                # Actions requiring order_id
                order_id = data.get("order_id", data.get("deal_id"))
                if not order_id:
                    return AdapterResult(
                        task_id=task.task_id,
                        success=False,
                        error_message="Missing order_id or deal_id in task data"
                    )

                if action == "update_order" or action == "update_deal":
                    result_data = await self.client.update_order(order_id, data.get("fields", {}))
                elif action == "add_comment":
                    result_data = await self.client.add_comment(order_id, data.get("comment", ""))
                elif action == "get_order":
                    result_data = await self.client.get_order(order_id)
                else:
                    return AdapterResult(
                        task_id=task.task_id,
                        success=False,
                        error_message=f"Unknown action: {action}"
                    )

            return AdapterResult(
                task_id=task.task_id,
                success=True,
                response_data=result_data
            )

        except Exception as e:
            logger.error("onebox_adapter_execution_failed", task_id=task.task_id, error=str(e))
            return AdapterResult(
                task_id=task.task_id,
                success=False,
                error_message=str(e)
            )
