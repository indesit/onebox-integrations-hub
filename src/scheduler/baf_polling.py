"""1C/BAF Polling Logic (HUB-011)."""

import httpx
from datetime import datetime, timedelta
from sqlmodel import Session, select
from src.core.database import engine
from src.core.logger import get_logger
from src.adapters.baf.adapter import BafAdapter
from src.config.settings import settings

logger = get_logger(__name__)

class BafPollingWorker:
    @staticmethod
    def run_polling():
        """Poll 1C for new receipt lines and group them into receipts."""
        # 1. Window: Last 24h to catch up, then move to 20-min window
        now = datetime.utcnow()
        date_from = (now - timedelta(hours=24)).strftime("%Y-%m-%d")
        date_to = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        logger.info("baf_polling_start", date_from=date_from, date_to=date_to)

        # 2. Call 1C HTTP Service
        url = "http://91.202.6.56/SecretShopBAS/hs/reports/receipt_lines"
        params = {
            "date_from": date_from,
            "date_to": date_to
        }
        
        try:
            with httpx.Client(timeout=60.0) as client:
                # Assuming Basic Auth credentials are set in .env
                response = client.get(
                    url, 
                    params=params, 
                    auth=(settings.baf_user, settings.baf_password)
                )
                response.raise_for_status()
                lines = response.json()

            if isinstance(lines, dict) and "rows" in lines:
                rows = lines["rows"]
                logger.info("baf_polling_received", line_count=len(rows))
                # 3. Process flat lines through BafAdapter (groups them internally)
                receipt_ids = BafAdapter.process_flat_lines(rows)
                logger.info("baf_polling_processed", receipt_count=len(receipt_ids))
            elif isinstance(lines, list):
                logger.info("baf_polling_received", line_count=len(lines))
                # 3. Process flat lines through BafAdapter (groups them internally)
                receipt_ids = BafAdapter.process_flat_lines(lines)
                logger.info("baf_polling_processed", receipt_count=len(receipt_ids))
            
        except Exception as e:
            logger.error("baf_polling_failed", error=str(e))

if __name__ == "__main__":
    # Run once for testing or loop with delay
    BafPollingWorker.run_polling()
