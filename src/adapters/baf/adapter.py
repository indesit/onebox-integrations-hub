"""1C/BAF Adapter Implementation (HUB-007)."""

from typing import Any, List
from sqlmodel import Session, select
from src.core.database import engine
from src.core.logger import get_logger
from src.core.models_db import StgBafReceiptLine
from src.core.etl import ETLLayer

logger = get_logger(__name__)

class BafAdapter:
    @staticmethod
    def process_flat_lines(lines: List[dict[str, Any]]) -> List[str]:
        """Entry point for 1C flat lines: Group, Validate, and Store."""
        
        # 1. Primary Logic: Stage raw lines and run ETL
        with Session(engine) as session:
            try:
                etl = ETLLayer(session)
                load_id = etl.stage_receipt_lines(lines)
                # Transform to Fact Sales immediately
                etl.process_fact_sales(load_id)
                logger.info("baf_adapter_etl_success", load_id=str(load_id), lines=len(lines))
                return [str(load_id)]
            except Exception as e:
                logger.error("baf_adapter_etl_failed", error=str(e))
                return []
