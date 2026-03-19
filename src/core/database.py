import os
from sqlmodel import create_engine, SQLModel, Session
from src.config.settings import settings
from src.core.logger import get_logger

logger = get_logger(__name__)

# Fallback for local dev if DATABASE_URL is not set
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://hub_user:hub_pass@localhost:5432/hub_db")

engine = create_engine(DATABASE_URL, echo=False)

def init_db():
    """Create all tables defined in models_db.py."""
    from src.core.models_db import StgBafReceiptLine, StgBafProductCatalog, DimProductVariant, FactSalesReportItem
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("database_initialized", url=DATABASE_URL)
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
        raise

def get_session():
    """Generator for database sessions."""
    with Session(engine) as session:
        yield session
