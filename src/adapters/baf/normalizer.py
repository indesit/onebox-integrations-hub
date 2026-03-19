"""1C/BAF normalizer implementation (BAF-003)."""

from typing import Any, List, Dict
from datetime import datetime
from src.core.models import HubEvent
from src.core.models_db import Receipt, ReceiptItem

class BafNormalizer:
    @staticmethod
    def to_hub_event(payload: dict[str, Any]) -> HubEvent:
        """Transforms 1C receipt JSON into normalized HubEvent."""
        return HubEvent(
            source="1c",
            event_type="receipt_created",
            payload=payload
        )

    @staticmethod
    def to_db_objects_v2(lines: List[dict[str, Any]]) -> List[tuple[Receipt, List[ReceiptItem]]]:
        """Maps 1C flat list (lines) to DB models (grouped Receipts + Items)."""
        receipts_map: Dict[str, tuple[Receipt, List[ReceiptItem]]] = {}
        
        for line in lines:
            rid = line.get("receipt_uuid")
            if rid not in receipts_map:
                receipt = Receipt(
                    external_id=line.get("receipt_number"),
                    cdate=datetime.fromisoformat(line.get("receipt_datetime")) if line.get("receipt_datetime") else datetime.utcnow(),
                    shop_id=line.get("store_uuid"),
                    total_sum=float(line.get("receipt_total_amount", 0.0)),
                    synced_to_onebox=False
                )
                receipts_map[rid] = (receipt, [])
            
            # Map Item
            item = ReceiptItem(
                price=float(line.get("price", 0.0)),
                count=float(line.get("qty", 1.0)),
                variant_characteristics={
                    "product_uuid": line.get("product_uuid"),
                    "characteristic_uuid": line.get("characteristic_uuid"),
                    "line_no": line.get("line_no"),
                    "line_amount": line.get("line_amount")
                }
            )
            receipts_map[rid][1].append(item)
            
        return list(receipts_map.values())
