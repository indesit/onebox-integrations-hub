import httpx
import re
import uuid
from datetime import datetime
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

def sync_customers():
    try:
        res = get_baf_data("customers")
        rows = res.get("rows", [])
        load_id = uuid.uuid4()
        
        with Session(engine) as session:
            session.exec(delete(StgBafCustomer))
            for r in rows:
                phone_normalized = normalize_phone_ua(r.get("customer_phone"))

                stg = StgBafCustomer(
                    load_id=load_id,
                    customer_uuid=r["customer_uuid"],
                    customer_name=r["customer_name"],
                    customer_phone=phone_normalized
                )
                session.add(stg)
                
                dim = session.query(DimCustomer).filter_by(customer_uuid=stg.customer_uuid).first()
                if not dim:
                    dim = DimCustomer(
                        customer_uuid=stg.customer_uuid,
                        customer_name=stg.customer_name,
                        customer_phone=stg.customer_phone
                    )
                    session.add(dim)
                else:
                    dim.customer_name = stg.customer_name
                    dim.customer_phone = stg.customer_phone
                    dim.loaded_at = datetime.utcnow()
            session.commit()
        logger.info("sync_customers_done", count=len(rows))
    except Exception as e:
        logger.error("sync_customers_failed", error=str(e))

if __name__ == "__main__":
    sync_stores()
    sync_customers()
