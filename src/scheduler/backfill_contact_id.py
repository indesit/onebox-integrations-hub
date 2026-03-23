"""One-shot: backfill onebox_contact_id in dim_customers by phone lookup."""

import time
from datetime import datetime
from sqlmodel import Session, select, text
from src.core.database import engine
from src.core.models_db import DimCustomer
from src.adapters.onebox.client import OneBoxClient
from src.config.settings import settings
from src.core.logger import get_logger

logger = get_logger(__name__)

BATCH_SIZE = 20
SLEEP_BETWEEN_BATCHES = 1.5


def run_backfill():
    client = OneBoxClient(
        domain=settings.onebox_url,
        login=settings.onebox_login,
        token=settings.onebox_api_key
    )

    with Session(engine) as session:
        # All customers that have synced receipts but no onebox_contact_id yet
        rows = session.exec(text("""
            SELECT DISTINCT d.customer_uuid, d.customer_phone_norm
            FROM dim_customers d
            JOIN fact_sales_receipt_items f ON f.customer_uuid = d.customer_uuid
            WHERE f.onebox_status = 'synced'
              AND d.onebox_contact_id IS NULL
              AND d.customer_phone_norm IS NOT NULL
            ORDER BY d.customer_uuid
        """)).all()

    logger.info("backfill_contact_id_start", total=len(rows))

    found = 0
    not_found = 0

    for i, row in enumerate(rows):
        customer_uuid = str(row[0])
        phone = row[1]

        res = client.get_contacts({
            "filter": {"phones": [phone]},
            "fields": ["id", "name"]
        })

        onebox_id = None
        if res.get("status") == 1:
            for c in res.get("dataArray") or []:
                c_name = (c.get("name") or "").strip()
                if c_name == "restapi" or str(c.get("id")) == "1":
                    continue
                onebox_id = str(c.get("id"))
                break

        if onebox_id:
            with Session(engine) as session:
                dim = session.query(DimCustomer).filter_by(
                    customer_uuid=customer_uuid
                ).first()
                if dim:
                    dim.onebox_contact_id = onebox_id
                    dim.onebox_synced_at = datetime.utcnow()
                    dim.updated_at = datetime.utcnow()
                    session.commit()
            logger.info("backfill_contact_id_found",
                        customer_uuid=customer_uuid, onebox_id=onebox_id, phone=phone)
            found += 1
        else:
            logger.warning("backfill_contact_id_not_found",
                           customer_uuid=customer_uuid, phone=phone)
            not_found += 1

        if (i + 1) % BATCH_SIZE == 0:
            logger.info("backfill_contact_id_progress", done=i + 1, total=len(rows))
            time.sleep(SLEEP_BETWEEN_BATCHES)

    logger.info("backfill_contact_id_done", found=found, not_found=not_found)


if __name__ == "__main__":
    run_backfill()
