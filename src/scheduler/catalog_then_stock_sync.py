"""Catalog → Stock sequential sync worker.

Runs in two phases:
  1. CatalogSyncWorker  — завантажує довідник товарів з 1С → dim_product_variants
  2. StockSyncWorker    — завантажує поточні залишки → fact_stock_balance

Stock sync залежить від актуального довідника (characteristic_uuid),
тому завжди виконується після каталогу.
"""

from src.core.logger import get_logger
from src.scheduler.catalog_sync import CatalogSyncWorker
from src.scheduler.stock_sync import StockSyncWorker

logger = get_logger(__name__)


def run_catalog_then_stock() -> None:
    """Entry point для RQ job: каталог → залишки."""
    logger.info("catalog_stock_sync_start")

    # ── Phase 1: Catalog ──────────────────────────────────────────────────
    try:
        logger.info("phase_1_catalog_start")
        CatalogSyncWorker.run_sync()
        logger.info("phase_1_catalog_done")
    except Exception as exc:
        logger.error("phase_1_catalog_failed", error=str(exc))
        # Продовжуємо до залишків навіть якщо каталог не оновився —
        # dim_product_variants може бути вже актуальним з попереднього запуску.

    # ── Phase 2: Stock ────────────────────────────────────────────────────
    try:
        logger.info("phase_2_stock_start")
        load_id = StockSyncWorker.poll_1c_stock()
        if load_id:
            logger.info("phase_2_stock_done", load_id=str(load_id))
        else:
            logger.warning("phase_2_stock_no_data")
    except Exception as exc:
        logger.error("phase_2_stock_failed", error=str(exc))

    logger.info("catalog_stock_sync_complete")


if __name__ == "__main__":
    run_catalog_then_stock()
