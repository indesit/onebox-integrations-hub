"""One-shot: push birth_date to existing OneBox contacts (HUB-016)."""

import time
from sqlmodel import Session, select, text
from src.core.database import engine
from src.core.logger import get_logger
from src.adapters.onebox.client import OneBoxClient
from src.config.settings import settings

logger = get_logger(__name__)

BATCH_SIZE = 20
SLEEP_BETWEEN_BATCHES = 2.0  # seconds, to avoid OneBox rate limits


def run_birthday_backfill():
    """
    For all customers that:
      - have a birth_date in dim_customers
      - have at least one synced order in OneBox (onebox_order_id is set)
    Find their OneBox contact by externalid or phone, then update birthday.
    """
    client = OneBoxClient(
        domain=settings.onebox_url,
        login=settings.onebox_login,
        token=settings.onebox_api_key
    )

    with Session(engine) as session:
        # Get unique customers with birth_date that have synced receipts
        rows = session.exec(text("""
            SELECT DISTINCT
                d.customer_uuid,
                d.customer_name,
                d.customer_phone_norm,
                d.birth_date
            FROM dim_customers d
            JOIN fact_sales_receipt_items f ON f.customer_uuid = d.customer_uuid
            WHERE d.birth_date IS NOT NULL
              AND f.onebox_status = 'synced'
              AND f.customer_uuid IS NOT NULL
            ORDER BY d.customer_uuid
        """)).all()

    logger.info("birthday_backfill_start", total=len(rows))

    updated = 0
    skipped = 0
    failed = 0

    for i, row in enumerate(rows):
        customer_uuid = str(row[0])
        customer_name = row[1] or ""
        phone = row[2] or ""
        birth_date = row[3]
        birthday_str = birth_date.strftime("%Y-%m-%d") if birth_date else None

        # Find contact in OneBox by phone (most reliable for existing contacts)
        onebox_id = None
        onebox_name = ""
        onebox_namelast = ""
        already_has_bdate = False

        if phone:
            phone_res = client.get_contacts({
                "filter": {"phones": [phone]},
                "fields": ["id", "name", "namelast", "bdate"]
            })
            if phone_res.get("status") == 1:
                for c in phone_res.get("dataArray") or []:
                    c_name = (c.get("name") or "").strip()
                    if c_name == "restapi" or str(c.get("id")) == "1":
                        continue
                    existing_bdate = (c.get("bdate") or "").strip()
                    if existing_bdate and existing_bdate != "0000-00-00":
                        logger.info("birthday_backfill_skip_has_bdate",
                                    customer_uuid=customer_uuid, id=c.get("id"),
                                    existing=existing_bdate)
                        skipped += 1
                        already_has_bdate = True
                        break
                    onebox_id = str(c.get("id"))
                    onebox_name = c_name
                    onebox_namelast = (c.get("namelast") or "").strip()
                    break

        if already_has_bdate:
            continue

        if not onebox_id:
            logger.warning("birthday_backfill_not_found", customer_uuid=customer_uuid, phone=phone)
            failed += 1
            continue

        # Build name parts from dim_customers if OneBox has empty name
        if not onebox_name and customer_name:
            parts = customer_name.strip().split()
            onebox_namelast = parts[0] if parts else ""
            onebox_name = " ".join(parts[1:]) if len(parts) > 1 else customer_name

        # Update bdate by userid — avoids creating duplicates when contact has no phone field set
        update_res = client._post_with_retry("contact/set/", [{"userid": int(onebox_id), "bdate": birthday_str}])

        if update_res.get("status") == 1:
            logger.info("birthday_backfill_updated",
                        onebox_id=onebox_id, customer_uuid=customer_uuid,
                        birthday=birthday_str, name=customer_name)
            updated += 1
        else:
            logger.error("birthday_backfill_failed",
                         onebox_id=onebox_id, customer_uuid=customer_uuid,
                         error=update_res.get("errorArray"))
            failed += 1

        # Rate limit pause every batch
        if (i + 1) % BATCH_SIZE == 0:
            logger.info("birthday_backfill_progress", done=i + 1, total=len(rows))
            time.sleep(SLEEP_BETWEEN_BATCHES)

    logger.info("birthday_backfill_done", updated=updated, skipped=skipped, failed=failed)


if __name__ == "__main__":
    run_birthday_backfill()
