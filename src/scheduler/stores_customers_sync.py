import httpx
import re
import uuid
from datetime import datetime, date
from sqlmodel import Session, delete
from src.core.database import engine
from src.core.logger import get_logger
from src.core.models_db import StgBafStore, DimStore, StgBafCustomer, DimCustomer
from src.config.settings import settings

logger = get_logger(__name__)


def normalize_phone_ua(phone: str | None) -> str | None:
    """Normalize phone to 380XXXXXXXXX (12 digits) or return None."""
    if not phone:
        return None

    digits = re.sub(r"\D", "", str(phone))
    if not digits:
        return None

    # 380XXXXXXXXX (already normalized)
    if len(digits) == 12 and digits.startswith("380"):
        return digits

    # 0XXXXXXXXX -> 380XXXXXXXXX
    if len(digits) == 10 and digits.startswith("0"):
        return f"38{digits}"

    # 80XXXXXXXXX -> 380XXXXXXXXX
    if len(digits) == 11 and digits.startswith("80"):
        return f"3{digits}"

    # Common typo: 9 digits local without leading 0 (e.g. 631234567)
    if len(digits) == 9:
        return f"380{digits}"

    return None


def get_baf_data(endpoint):
    url = f"http://91.202.6.56/SecretShopBAS/hs/reports/{endpoint}"
    with httpx.Client(timeout=30.0) as client:
        res = client.get(url, auth=(settings.baf_user, settings.baf_password))
        res.raise_for_status()
        return res.json()

def sync_stores():
    try:
        res = get_baf_data("stores")
        rows = res.get("rows", [])
        load_id = uuid.uuid4()
        
        with Session(engine) as session:
            session.exec(delete(StgBafStore))
            for r in rows:
                stg = StgBafStore(
                    load_id=load_id,
                    store_uuid=r["store_uuid"],
                    store_name=r["store_name"]
                )
                session.add(stg)
                
                dim = session.query(DimStore).filter_by(store_uuid=stg.store_uuid).first()
                if not dim:
                    dim = DimStore(store_uuid=stg.store_uuid, store_name=stg.store_name)
                    session.add(dim)
                else:
                    dim.store_name = stg.store_name
                    dim.loaded_at = datetime.utcnow()
            session.commit()
        logger.info("sync_stores_done", count=len(rows))
    except Exception as e:
        logger.error("sync_stores_failed", error=str(e))

def parse_date(val: str | None) -> date | None:
    """Parse DATE from BAF (YYYY-MM-DD or DD.MM.YYYY)."""
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def parse_datetime(val: str | None) -> datetime | None:
    """Parse DATETIME from BAF (YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS)."""
    if not val:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def sync_customers():
    try:
        res = get_baf_data("customers")
        rows = res.get("rows", [])
        load_id = uuid.uuid4()

        with Session(engine) as session:
            session.exec(delete(StgBafCustomer))

            for r in rows:
                phone_norm = normalize_phone_ua(r.get("customer_phone"))
                birth_date = parse_date(r.get("birth_date"))
                source_created_at = parse_date(r.get("source_created_at"))
                source_updated_at = parse_datetime(r.get("source_updated_at"))

                stg = StgBafCustomer(
                    load_id=load_id,
                    customer_uuid=r["customer_uuid"],
                    customer_name=r.get("customer_name"),
                    customer_phone=phone_norm,
                    birth_date=birth_date,
                    source_created_at=source_created_at,
                    source_updated_at=source_updated_at,
                    ext_data={}
                )
                session.add(stg)

                now = datetime.utcnow()
                dim = session.query(DimCustomer).filter_by(customer_uuid=stg.customer_uuid).first()
                if not dim:
                    dim = DimCustomer(
                        customer_uuid=stg.customer_uuid,
                        customer_name=stg.customer_name,
                        customer_phone=stg.customer_phone,
                        customer_phone_norm=phone_norm,
                        birth_date=birth_date,
                        birth_month=birth_date.month if birth_date else None,
                        birth_day=birth_date.day if birth_date else None,
                        source_created_at=source_created_at,
                        source_updated_at=source_updated_at,
                        first_seen_at=now,
                        last_seen_at=now,
                    )
                    session.add(dim)
                else:
                    dim.customer_name = stg.customer_name
                    dim.customer_phone = stg.customer_phone
                    dim.customer_phone_norm = phone_norm
                    # Update birth_date only if we get a value (don't overwrite with None)
                    if birth_date:
                        dim.birth_date = birth_date
                        dim.birth_month = birth_date.month
                        dim.birth_day = birth_date.day
                    dim.source_created_at = source_created_at
                    dim.source_updated_at = source_updated_at
                    dim.last_seen_at = now
                    dim.updated_at = now

            session.commit()

        logger.info("sync_customers_done", count=len(rows))
    except Exception as e:
        logger.error("sync_customers_failed", error=str(e))

if __name__ == "__main__":
    sync_stores()
    sync_customers()
