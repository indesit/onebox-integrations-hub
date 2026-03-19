"""1C Product Catalog Sync Worker (HUB-012)."""

import httpx
from uuid import UUID
from sqlmodel import Session
from src.core.database import engine
from src.core.logger import get_logger
from src.core.etl import ETLLayer
from src.config.settings import settings

logger = get_logger(__name__)

class CatalogSyncWorker:
    @staticmethod
    def run_sync():
        """Fetch the full product catalog from 1C and update Hub dimensions."""
        url = "http://91.202.6.56/SecretShopBAS/hs/reports/product_catalog"
        
        logger.info("catalog_sync_start", url=url)
        
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.get(
                    url,
                    auth=(settings.baf_user, settings.baf_password)
                )
                response.raise_for_status()
                catalog_data = response.json()

            if isinstance(catalog_data, dict) and "rows" in catalog_data:
                rows = catalog_data["rows"]
                logger.info("catalog_received", count=len(rows))
                
                with Session(engine) as session:
                    etl = ETLLayer(session)
                    # 1. Stage the raw catalog data
                    load_id = etl.stage_catalog(rows)
                    # 2. Process into dim_product_variants
                    etl.process_dim_variants(load_id)
                
                logger.info("catalog_sync_complete", load_id=str(load_id))
            elif isinstance(catalog_data, list):
                logger.info("catalog_received", count=len(catalog_data))
                
                with Session(engine) as session:
                    etl = ETLLayer(session)
                    # 1. Stage the raw catalog data
                    load_id = etl.stage_catalog(catalog_data)
                    # 2. Process into dim_product_variants
                    etl.process_dim_variants(load_id)
                
                logger.info("catalog_sync_complete", load_id=str(load_id))
            else:
                logger.error("catalog_invalid_format", type=str(type(catalog_data)))

        except Exception as e:
            logger.error("catalog_sync_failed", error=str(e))

if __name__ == "__main__":
    CatalogSyncWorker.run_sync()
