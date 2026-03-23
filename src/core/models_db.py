from datetime import datetime, date
from typing import Optional, Dict, Any
from uuid import UUID
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

class StgBafReceiptLine(SQLModel, table=True):
    __tablename__ = "stg_baf_receipt_lines"
    id: Optional[int] = Field(default=None, primary_key=True)
    load_id: UUID = Field(index=True)
    loaded_at: datetime = Field(default_factory=datetime.utcnow)
    
    receipt_uuid: UUID = Field(index=True)
    receipt_number: Optional[str] = None
    receipt_datetime: Optional[datetime] = None
    receipt_posted: bool = Field(default=True)
    receipt_deleted: bool = Field(default=False)
    receipt_total_amount: float = Field(default=0.0)
    
    store_uuid: Optional[UUID] = None
    customer_uuid: Optional[UUID] = None
    loyalty_card_uuid: Optional[UUID] = None
    
    line_no: int
    product_uuid: UUID
    characteristic_uuid: Optional[UUID] = None
    
    qty: float = Field(default=0.0)
    price: float = Field(default=0.0)
    line_amount: float = Field(default=0.0)
    
    raw_payload: Optional[Any] = Field(default={}, sa_column=Column(JSONB))
    
    source_system: str = Field(default="BAF")

class StgBafProductCatalog(SQLModel, table=True):
    __tablename__ = "stg_baf_product_catalog"
    id: Optional[int] = Field(default=None, primary_key=True)
    load_id: UUID = Field(index=True)
    loaded_at: datetime = Field(default_factory=datetime.utcnow)
    
    product_uuid: UUID
    product_name: str
    article: Optional[str] = None
    
    characteristic_uuid: Optional[UUID] = None
    characteristic_name: Optional[str] = None
    characteristic_article: Optional[str] = None
    
    group: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    material: Optional[str] = None
    napolnenie: Optional[str] = None
    brand: Optional[str] = None
    color: Optional[str] = None
    
    # Size/Attribute fields
    razmer_chashki: Optional[str] = None
    obxvat_grudi: Optional[str] = None
    obxvat_grudi_swim: Optional[str] = None
    razmer_trusikov: Optional[str] = None
    razmer_swim: Optional[str] = None
    razmer_plavok: Optional[str] = None
    razmer_sleep: Optional[str] = None
    
    osobennosti: Optional[Any] = Field(default=[], sa_column=Column(JSONB))
    
    source_system: str = Field(default="BAF")

class DimProductVariant(SQLModel, table=True):
    __tablename__ = "dim_product_variants"
    id: Optional[int] = Field(default=None, primary_key=True)
    product_uuid: UUID
    characteristic_uuid: Optional[UUID] = None
    
    article: Optional[str] = None # Base product article
    characteristic_article: Optional[str] = None # Full variant article (Anton: Source of Truth for OneBox)
    
    product_name: str
    characteristic_name: Optional[str] = None
    
    group: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    material: Optional[str] = None
    napolnenie: Optional[str] = None
    brand: Optional[str] = None
    color: Optional[str] = None
    
    # Size/Attribute fields
    razmer_chashki: Optional[str] = None
    obxvat_grudi: Optional[str] = None
    obxvat_grudi_swim: Optional[str] = None
    razmer_trusikov: Optional[str] = None
    razmer_swim: Optional[str] = None
    razmer_plavok: Optional[str] = None
    razmer_sleep: Optional[str] = None
    
    osobennosti: Optional[Any] = Field(default=[], sa_column=Column(JSONB))
    
    is_active: bool = Field(default=True)
    
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)
    loaded_at: datetime = Field(default_factory=datetime.utcnow)

class FactSalesReportItem(SQLModel, table=True):
    __tablename__ = "fact_sales_receipt_items"
    id: Optional[int] = Field(default=None, primary_key=True)
    
    receipt_uuid: UUID = Field(index=True)
    line_no: int
    
    receipt_number: Optional[str] = None
    receipt_datetime: datetime = Field(index=True)
    
    receipt_posted: bool = Field(default=True)
    receipt_deleted: bool = Field(default=False)
    receipt_total_amount: float = Field(default=0.0)
    
    store_uuid: Optional[UUID] = Field(default=None, index=True)
    customer_uuid: Optional[UUID] = Field(default=None, index=True)
    loyalty_card_uuid: Optional[UUID] = None
    
    product_uuid: UUID
    characteristic_uuid: Optional[UUID] = None
    
    qty: float
    price: float
    line_amount: float
    
    # OneBox Integration Fields
    onebox_status: str = Field(default="pending", index=True)
    onebox_order_id: Optional[str] = None
    sync_error: Optional[str] = None
    onebox_synced_at: Optional[datetime] = None
    
    # Gift Card & Payment Fields (HUB-015)
    is_gift_certificate_sale: bool = Field(default=False)
    gift_certificate_sale_amount: float = Field(default=0.0)
    has_certificate_payment: bool = Field(default=False)
    certificate_payment_amount: float = Field(default=0.0)
    
    # Metadata & Extensibility
    ext_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class DimStore(SQLModel, table=True):
    __tablename__ = "dim_stores"
    id: Optional[int] = Field(default=None, primary_key=True)
    store_uuid: UUID = Field(index=True)
    store_name: str
    loaded_at: datetime = Field(default_factory=datetime.utcnow)

class DimCustomer(SQLModel, table=True):
    __tablename__ = "dim_customers"
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_uuid: UUID = Field(index=True)

    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_phone_norm: Optional[str] = Field(default=None, index=True)

    birth_date: Optional[date] = None
    birth_month: Optional[int] = None
    birth_day: Optional[int] = None

    onebox_contact_id: Optional[str] = Field(default=None, index=True)
    onebox_synced_at: Optional[datetime] = None

    is_active: bool = Field(default=True)

    source_created_at: Optional[date] = None
    source_updated_at: Optional[datetime] = None

    ext_data: Optional[Any] = Field(default={}, sa_column=Column(JSONB))

    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class StgBafStore(SQLModel, table=True):
    __tablename__ = "stg_baf_stores"
    id: Optional[int] = Field(default=None, primary_key=True)
    load_id: UUID = Field(index=True)
    loaded_at: datetime = Field(default_factory=datetime.utcnow)
    
    store_uuid: UUID
    store_name: str
    
    source_system: str = Field(default="BAF")

class StgBafCustomer(SQLModel, table=True):
    __tablename__ = "stg_baf_customers"
    id: Optional[int] = Field(default=None, primary_key=True)
    load_id: UUID = Field(index=True)
    loaded_at: datetime = Field(default_factory=datetime.utcnow)

    customer_uuid: UUID
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    birth_date: Optional[date] = None
    source_created_at: Optional[date] = None
    source_updated_at: Optional[datetime] = None

    ext_data: Optional[Any] = Field(default={}, sa_column=Column(JSONB))

    source_system: str = Field(default="BAF")
