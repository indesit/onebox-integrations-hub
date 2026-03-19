import sys
import os
import httpx
import time
from datetime import datetime, timedelta
from sqlmodel import Session, select, func
from src.core.database import engine
from src.core.etl import ETLLayer
from src.config.settings import settings
from src.core.logger import get_logger

# Add project path to sys.path
sys.path.append('/root/.openclaw/workspace/projects/onebox-integrations-hub')

logger = get_logger(__name__)

class SalesBackfillWorker:
    """
    Handles historical data loading from 1C to Integrations Hub.
    """
    
    def __init__(self, start_date="2021-04-30", step_days=14):
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.step_days = step_days
        self.url = "http://91.202.6.56/SecretShopBAS/hs/reports/receipt_lines"
        self.auth = (settings.baf_user, settings.baf_password)

    def run(self):
        current_start = self.start_date
        end_limit = datetime.utcnow()
        
        logger.info("backfill_started", start_date=str(current_start), step=self.step_days)
        
        while current_start < end_limit:
            current_end = current_start + timedelta(days=self.step_days)
            
            # Format dates for API
            d_from = current_start.strftime("%Y-%m-%d")
            d_to = current_end.strftime("%Y-%m-%d")
            
            logger.info("backfill_batch_request", date_from=d_from, date_to=d_to)
            
            try:
                with httpx.Client(timeout=180.0) as client:
                    response = client.get(
                        self.url, 
                        params={"date_from": d_from, "date_to": d_to}, 
                        auth=self.auth
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        rows = data if isinstance(data, list) else data.get("rows", [])
                        
                        if rows:
                            with Session(engine) as session:
                                etl = ETLLayer(session)
                                load_id = etl.stage_receipt_lines(rows)
                                etl.process_fact_sales(load_id)
                                # Optional: session.execute(text("DELETE FROM stg_baf_receipt_lines WHERE load_id = :id"), {"id": load_id})
                                logger.info("backfill_batch_success", count=len(rows), load_id=str(load_id))
                        else:
                            logger.info("backfill_batch_empty", date_from=d_from)
                    else:
                        logger.error("backfill_batch_api_error", status=response.status_code, text=response.text)
                        # Stop or retry logic here
                        break
                        
            except Exception as e:
                logger.error("backfill_batch_failed", error=str(e))
                break # Pause on fatal error
            
            # Move to next period
            current_start = current_end
            time.sleep(2) # Gentle delay between batches
            
        logger.info("backfill_finished")

if __name__ == "__main__":
    # This is a plan/template. Execution should be triggered after index creation.
    print("Backfill Worker initialized for start date 2021-04-30.")
