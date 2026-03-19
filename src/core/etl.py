from datetime import datetime
from uuid import UUID, uuid4
from typing import List, Optional
from sqlmodel import Session, select, func
from src.core.models_db import StgBafReceiptLine, StgBafProductCatalog, DimProductVariant, FactSalesReportItem
from src.core.logger import get_logger

logger = get_logger(__name__)

class ETLLayer:
    """
    Refined ETL Layer based on the approved PostgreSQL schema.
    Handles high-performance upserts and data linking.
    """

    def __init__(self, session: Session):
        self.session = session

    def stage_receipt_lines(self, raw_lines: List[dict]) -> UUID:
        """Load raw data into staging with a unique load_id."""
        load_id = uuid4()
        try:
            for line in raw_lines:
                # Handle empty UUID strings from 1C
                c_uuid = line.get("characteristic_uuid")
                if not c_uuid or str(c_uuid).startswith("00000000"):
                    c_uuid = None
                
                # Fix for line_amount: if 0, calculate from qty * price
                amount = line.get("line_amount") or line.get("amount") or 0.0
                if not amount and line.get("qty") and line.get("price"):
                    amount = float(line.get("qty")) * float(line.get("price"))

                stg = StgBafReceiptLine(
                    load_id=load_id,
                    receipt_uuid=line.get("receipt_uuid"),
                    receipt_number=line.get("receipt_number"),
                    receipt_datetime=line.get("receipt_datetime"),
                    receipt_posted=line.get("receipt_posted", True),
                    receipt_deleted=line.get("receipt_deleted", False),
                    receipt_total_amount=line.get("receipt_total_amount", 0.0),
                    store_uuid=line.get("store_uuid"),
                    customer_uuid=line.get("customer_uuid"),
                    loyalty_card_uuid=line.get("loyalty_card_uuid"),
                    line_no=line.get("line_no", 1),
                    product_uuid=line.get("product_uuid"),
                    characteristic_uuid=c_uuid,
                    qty=line.get("qty", 0.0),
                    price=line.get("price", 0.0),
                    line_amount=amount,
                    source_system="BAF"
                )
                # Keep raw payload for extensibility
                stg.raw_payload = line 
                self.session.add(stg)
            self.session.commit()
            logger.info("etl_staged_receipts", load_id=str(load_id), count=len(raw_lines))
            return load_id
        except Exception as e:
            self.session.rollback()
            logger.error("etl_staging_failed", error=str(e))
            raise

    def process_fact_sales(self, load_id: UUID):
        """
        Upsert staged lines into FactSalesReportItem.
        Note: In production, we'd use raw SQL for performance 'ON CONFLICT DO UPDATE'.
        """
        stg_lines = self.session.exec(
            select(StgBafReceiptLine).where(StgBafReceiptLine.load_id == load_id)
        ).all()
        
        for s in stg_lines:
            existing = self.session.exec(
                select(FactSalesReportItem).where(
                    FactSalesReportItem.receipt_uuid == s.receipt_uuid,
                    FactSalesReportItem.line_no == s.line_no
                )
            ).first()
            
            if existing:
                # Update logic
                existing.receipt_number = s.receipt_number
                existing.receipt_datetime = s.receipt_datetime
                existing.receipt_posted = s.receipt_posted
                existing.receipt_deleted = s.receipt_deleted
                existing.receipt_total_amount = s.receipt_total_amount
                existing.qty = s.qty
                existing.price = s.price
                existing.line_amount = s.line_amount
                
                # Anton: Gift Card Updates
                if s.raw_payload:
                    existing.is_gift_certificate_sale = s.raw_payload.get("is_gift_certificate_sale", False)
                    existing.gift_certificate_sale_amount = s.raw_payload.get("gift_certificate_sale_amount", 0.0)
                    existing.has_certificate_payment = s.raw_payload.get("has_certificate_payment", False)
                    existing.certificate_payment_amount = s.raw_payload.get("certificate_payment_amount", 0.0)
                
                existing.updated_at = datetime.utcnow()
                self.session.add(existing)
            else:
                # Insert logic
                fact = FactSalesReportItem(
                    receipt_uuid=s.receipt_uuid,
                    line_no=s.line_no,
                    receipt_number=s.receipt_number,
                    receipt_datetime=s.receipt_datetime,
                    receipt_posted=s.receipt_posted,
                    receipt_deleted=s.receipt_deleted,
                    receipt_total_amount=s.receipt_total_amount,
                    store_uuid=s.store_uuid,
                    customer_uuid=s.customer_uuid,
                    loyalty_card_uuid=s.loyalty_card_uuid,
                    product_uuid=s.product_uuid,
                    characteristic_uuid=s.characteristic_uuid,
                    qty=s.qty,
                    price=s.price,
                    line_amount=s.line_amount,
                    is_gift_certificate_sale=s.raw_payload.get("is_gift_certificate_sale", False) if s.raw_payload else False,
                    gift_certificate_sale_amount=s.raw_payload.get("gift_certificate_sale_amount", 0.0) if s.raw_payload else 0.0,
                    has_certificate_payment=s.raw_payload.get("has_certificate_payment", False) if s.raw_payload else False,
                    certificate_payment_amount=s.raw_payload.get("certificate_payment_amount", 0.0) if s.raw_payload else 0.0,
                    onebox_status="pending",
                    ext_data=s.raw_payload if s.raw_payload else {}
                )
                self.session.add(fact)
        
        self.session.commit()
        logger.info("etl_fact_sales_synced", load_id=str(load_id))

    def stage_catalog(self, raw_catalog: List[dict]) -> UUID:
        """Load catalog data into staging."""
        load_id = uuid4()
        chunk_size = 500
        for i in range(0, len(raw_catalog), chunk_size):
            chunk = raw_catalog[i:i+chunk_size]
            for item in chunk:
                # Handle empty strings for UUIDs from 1C
                c_uuid = item.get("characteristic_uuid")
                if not c_uuid:
                    c_uuid = None
                
                p_uuid = item.get("product_uuid")
                if not p_uuid:
                    continue # Skip items without product_uuid

                stg = StgBafProductCatalog(
                    load_id=load_id,
                    product_uuid=p_uuid,
                    product_name=item.get("product_name"),
                    article=item.get("article"),
                    characteristic_uuid=c_uuid,
                    characteristic_name=item.get("characteristic_name"),
                    characteristic_article=item.get("characteristic_article"),
                    group=item.get("group"),
                    category=item.get("category"),
                    type=item.get("type"),
                    material=item.get("material"),
                    napolnenie=item.get("napolnenie"),
                    brand=item.get("brand"),
                    color=item.get("color"),
                    razmer_chashki=item.get("razmer_chashki"),
                    obxvat_grudi=item.get("obxvat_grudi"),
                    obxvat_grudi_swim=item.get("obxvat_grudi_swim"),
                    razmer_trusikov=item.get("razmer_trusikov"),
                    razmer_swim=item.get("razmer_swim"),
                    razmer_plavok=item.get("razmer_plavok"),
                    razmer_sleep=item.get("razmer_sleep"),
                    osobennosti=item.get("osobennosti", [])
                )
                self.session.add(stg)
            self.session.commit()
        return load_id

    def process_dim_variants(self, load_id: UUID):
        """Upsert catalog staging to dimensions."""
        stg_items = self.session.exec(
            select(StgBafProductCatalog).where(StgBafProductCatalog.load_id == load_id)
        ).all()
        
        for s in stg_items:
            existing = self.session.exec(
                select(DimProductVariant).where(
                    DimProductVariant.product_uuid == s.product_uuid,
                    DimProductVariant.characteristic_uuid == s.characteristic_uuid
                )
            ).first()
            
            if existing:
                existing.product_name = s.product_name
                existing.article = s.article
                existing.characteristic_name = s.characteristic_name
                existing.characteristic_article = s.characteristic_article
                existing.group = s.group
                existing.category = s.category
                existing.type = s.type
                existing.material = s.material
                existing.napolnenie = s.napolnenie
                existing.brand = s.brand
                existing.color = s.color
                existing.razmer_chashki = s.razmer_chashki
                existing.obxvat_grudi = s.obxvat_grudi
                existing.obxvat_grudi_swim = s.obxvat_grudi_swim
                existing.razmer_trusikov = s.razmer_trusikov
                existing.razmer_swim = s.razmer_swim
                existing.razmer_plavok = s.razmer_plavok
                existing.razmer_sleep = s.razmer_sleep
                existing.osobennosti = s.osobennosti
                existing.last_seen_at = datetime.utcnow()
                existing.loaded_at = datetime.utcnow()
                self.session.add(existing)
            else:
                variant = DimProductVariant(
                    product_uuid=s.product_uuid,
                    characteristic_uuid=s.characteristic_uuid,
                    product_name=s.product_name,
                    article=s.article,
                    characteristic_name=s.characteristic_name,
                    characteristic_article=s.characteristic_article,
                    group=s.group,
                    category=s.category,
                    type=s.type,
                    material=s.material,
                    napolnenie=s.napolnenie,
                    brand=s.brand,
                    color=s.color,
                    razmer_chashki=s.razmer_chashki,
                    obxvat_grudi=s.obxvat_grudi,
                    obxvat_grudi_swim=s.obxvat_grudi_swim,
                    razmer_trusikov=s.razmer_trusikov,
                    razmer_swim=s.razmer_swim,
                    razmer_plavok=s.razmer_plavok,
                    razmer_sleep=s.razmer_sleep,
                    osobennosti=s.osobennosti
                )
                self.session.add(variant)
        self.session.commit()
        logger.info("etl_dim_variants_synced", load_id=str(load_id))
