"""Periodic job registration for RQ built-in scheduler (rq >= 1.16).

Реєструє повторювані задачі через RQ native scheduler.
Worker запускається з: rq worker --with-scheduler default

Як підключити:
  Викличте setup_periodic_jobs() один раз при старті — наприклад
  через окремий скрипт або з docker entrypoint перед запуском worker-а.

Запуск вручну (разова реєстрація):
  python -m src.scheduler.periodic
"""

from datetime import datetime, timezone, timedelta

from src.core.queue import get_queue, get_redis
from src.core.logger import get_logger

logger = get_logger(__name__)

# ── Інтервали ─────────────────────────────────────────────────────────────────

CATALOG_STOCK_INTERVAL_SECONDS = 4 * 60 * 60   # кожні 4 години
BAF_POLLING_INTERVAL_SECONDS   = 20 * 60        # кожні 20 хвилин


def setup_periodic_jobs() -> None:
    """Реєструє всі periodic jobs в RQ scheduler. Безпечно викликати повторно."""
    from rq.job import Retry
    from rq import Scheduler

    redis = get_redis()
    queue = get_queue("default")
    scheduler = Scheduler(queue=queue, connection=redis)

    # Очищаємо старі periodic jobs щоб уникнути дублікатів при рестарті
    _cancel_existing(scheduler, [
        "src.scheduler.catalog_then_stock_sync.run_catalog_then_stock",
        "src.scheduler.baf_polling.BafPollingWorker.run_polling",
    ])

    # ── 1. Каталог → Залишки (кожні 4 год) ──────────────────────────────
    scheduler.schedule(
        scheduled_time=datetime.now(tz=timezone.utc),
        func="src.scheduler.catalog_then_stock_sync.run_catalog_then_stock",
        interval=CATALOG_STOCK_INTERVAL_SECONDS,
        repeat=None,
        queue_name="default",
        meta={"description": "Catalog → Stock sequential sync"},
    )
    logger.info("periodic_registered", func="catalog_then_stock", interval_sec=CATALOG_STOCK_INTERVAL_SECONDS)

    # ── 2. BAF receipt polling — продажі (кожні 20 хв) ──────────────────
    scheduler.schedule(
        scheduled_time=datetime.now(tz=timezone.utc) + timedelta(minutes=1),
        func="src.scheduler.baf_polling.BafPollingWorker.run_polling",
        interval=BAF_POLLING_INTERVAL_SECONDS,
        repeat=None,
        queue_name="default",
        meta={"description": "BAF receipt lines polling"},
    )
    logger.info("periodic_registered", func="baf_polling", interval_sec=BAF_POLLING_INTERVAL_SECONDS)

    logger.info("periodic_jobs_setup_complete")


def _cancel_existing(scheduler, func_names: list[str]) -> None:
    """Скасовує раніше зареєстровані periodic jobs за назвою функції."""
    try:
        for job in scheduler.get_jobs():
            func_name = getattr(job, 'func_name', '') or ''
            if func_name in func_names:
                scheduler.cancel(job)
                logger.info("periodic_job_cancelled", job_id=job.id, func=func_name)
    except Exception as exc:
        logger.warning("periodic_cancel_error", error=str(exc))


if __name__ == "__main__":
    setup_periodic_jobs()
