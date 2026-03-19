"""1C/BAF Stock Polling & Sync to OneBox (HUB-012)."""

import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import UUID, uuid4
from sqlmodel import Session, select, SQLModel, Field, Column, JSON, text
from sqlalchemy.dialects.postgresql import JSONB

from src.core.database import engine
from src.core.logger import get_logger
from src.config.settings import settings
from src.core.models_db import DimProductVariant

logger = get_logger(__name__)

# --- Staging Table for Stock ---
class StgBafStockBalance(SQLModel, table=True):
    __tablename__ = "stg_baf_stock_balance"
    id: int | None = Field(default=None, primary_key=True)
    load_id: UUID = Field(index=True)
    loaded_at: datetime = Field(default_factory=datetime.utcnow)
    
    store_uuid: UUID = Field(index=True)
    product_uuid: UUID = Field(index=True)
    characteristic_uuid: UUID | None = Field(default=None, index=True)
    
    stock_qty: float = Field(default=0.0)
    source_system: str = Field(default="BAF")

# --- Stock Tracking Table ---
class FactStockBalance(SQLModel, table=True):
    __tablename__ = "fact_stock_balance"
    id: int | None = Field(default=None, primary_key=True)
    
    store_uuid: UUID = Field(index=True)
    product_uuid: UUID = Field(index=True)
    characteristic_uuid: UUID | None = Field(default=None, index=True)
    
    qty: float = Field(default=0.0)
    color: str | None = Field(default=None) # NEW FIELD
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    onebox_synced_at: datetime | None = None
    onebox_status: str = Field(default="pending", index=True)

class StockSyncWorker:
    """
    Handles polling stock from 1C and preparing data for reports/OneBox.
    """

    @staticmethod
    def poll_1c_stock():
        """Fetch current stock balances from 1C."""
        url = "http://91.202.6.56/SecretShopBAS/hs/reports/stock_balance_now"
        load_id = uuid4()
        
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.get(
                    url, 
                    auth=(settings.baf_user, settings.baf_password)
                )
                response.raise_for_status()
                data = response.json()
            
            rows = data if isinstance(data, list) else data.get("rows", [])
            logger.info("baf_stock_received", count=len(rows))
            
            with Session(engine) as session:
                # Pre-load store mappings
                stores = session.execute(text("SELECT store_name, store_uuid FROM dim_stores")).all()
                store_map = {s[0]: s[1] for s in stores}
                
                # Pre-load variant mappings
                # We need a robust way since there might be many. We can fetch them all.
                variants = session.execute(text("SELECT article, characteristic_name, product_uuid, characteristic_uuid FROM dim_product_variants")).all()
                variant_map = {(v[0] or "", v[1] or ""): (v[2], v[3]) for v in variants}
                
                stg_objects = []
                missing_variants = 0
                missing_stores = 0
                for row in rows:
                    w = row.get("warehouse", "")
                    a = row.get("artikul", "")
                    c = row.get("characteristic_name", "")
                    
                    store_uuid = store_map.get(w)
                    if not store_uuid:
                        missing_stores += 1
                        continue
                        
                    variant = variant_map.get((a, c))
                    if not variant:
                        # Try matching just the article if characteristic is empty, or vice versa
                        missing_variants += 1
                        continue
                        
                    p_uuid, c_uuid = variant
                        
                    stg = StgBafStockBalance(
                        load_id=load_id,
                        store_uuid=store_uuid,
                        product_uuid=p_uuid,
                        characteristic_uuid=c_uuid,
                        stock_qty=row.get("qty", 0.0)
                    )
                    stg_objects.append(stg)
                    
                    # Update color if needed
                    color = row.get("color")
                    if color and c_uuid:
                        session.execute(
                            text("UPDATE dim_product_variants SET color = :c WHERE characteristic_uuid = :id"),
                            {"c": color, "id": str(c_uuid)}
                        )
                
                if stg_objects:
                    session.add_all(stg_objects)
                session.commit()
                logger.info("baf_stock_mapped", mapped=len(stg_objects), missing_variants=missing_variants, missing_stores=missing_stores)
                
            StockSyncWorker.process_stock_to_fact(load_id, rows, variant_map, store_map)
            return load_id
            
        except Exception as e:
            logger.error("baf_stock_polling_failed", error=str(e))
            return None

    @staticmethod
    def process_stock_to_fact(load_id: UUID, raw_rows: List[dict], variant_map: dict, store_map: dict):
        """Update the fact table with the latest stock from staging."""
        # Create a lookup for colors from raw data
        color_lookup = {}
        for r in raw_rows:
            w = r.get("warehouse", "")
            a = r.get("artikul", "")
            c = r.get("characteristic_name", "")
            store_uuid = store_map.get(w)
            variant = variant_map.get((a, c))
            if store_uuid and variant:
                key = (str(store_uuid), str(variant[0]), str(variant[1]) if variant[1] else "None")
                color_lookup[key] = r.get("color")

        with Session(engine) as session:
            stg_items = session.exec(
                select(StgBafStockBalance).where(StgBafStockBalance.load_id == load_id)
            ).all()
            
            for s in stg_items:
                existing = session.exec(
                    select(FactStockBalance).where(
                        FactStockBalance.store_uuid == s.store_uuid,
                        FactStockBalance.product_uuid == s.product_uuid,
                        FactStockBalance.characteristic_uuid == s.characteristic_uuid
                    )
                ).first()
                
                c_uuid_str = str(s.characteristic_uuid) if s.characteristic_uuid else "None"
                color = color_lookup.get((str(s.store_uuid), str(s.product_uuid), c_uuid_str))

                if existing:
                    existing.qty = s.stock_qty
                    existing.color = color
                    existing.last_updated_at = datetime.utcnow()
                    existing.onebox_status = "pending"
                    session.add(existing)
                else:
                    fact = FactStockBalance(
                        store_uuid=s.store_uuid,
                        product_uuid=s.product_uuid,
                        characteristic_uuid=s.characteristic_uuid,
                        qty=s.stock_qty,
                        color=color,
                        onebox_status="pending"
                    )
                    session.add(fact)
            session.commit()
            logger.info("stock_fact_updated", load_id=str(load_id))

if __name__ == "__main__":
    # Create tables if not exist (only for this worker's tables)
    SQLModel.metadata.create_all(engine)
    StockSyncWorker.poll_1c_stock()
