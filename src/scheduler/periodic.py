"""Periodic job registration for RQ 2.x built-in scheduler.

Реєструє повторювані задачі через RQ native scheduler (rq >= 2.0).
Worker запускається з: rq worker --with-scheduler default

Запуск вручну (разова реєстрація):
  python -m src.scheduler.periodic
"""

from datetime import datetime, timezone, timedelta

from rq import Repeat
from src.core.queue import get_queue
from src.core.logger import get_logger

logger = get_logger(__name__)

CATALOG_STOCK_INTERVAL_SECONDS = 4 * 60 * 60   # кожні 4 години
BAF_POLLING_INTERVAL_SECONDS   = 20 * 60        # кожні 20 хвилин
DIGEST_INTERVAL_SECONDS        = 24 * 60 * 60  # щодня
REPEAT_TIMES                   = 99999          # практично нескінченно


def setup_periodic_jobs() -> None:
    """Реєструє всі periodic jobs в RQ scheduler. Безпечно викликати повторно."""
    queue = get_queue("default")
    now = datetime.now(tz=timezone.utc)

    _cancel_existing(queue, [
        "src.scheduler.catalog_then_stock_sync.run_catalog_then_stock",
        "src.scheduler.baf_polling.BafPollingWorker.run_polling",
        "src.bot.digest.send_daily_digest",
    ])

    # ── 1. BAF receipt polling — продажі (кожні 20 хв) ──────────────────
    queue.enqueue_at(
        now,
        "src.scheduler.baf_polling.BafPollingWorker.run_polling",
        job_timeout=600,
        repeat=Repeat(times=REPEAT_TIMES, interval=BAF_POLLING_INTERVAL_SECONDS),
    )
    logger.info("periodic_registered", func="baf_polling", interval_sec=BAF_POLLING_INTERVAL_SECONDS)

    # ── 2. Каталог → Залишки (кожні 4 год, старт через 2 хв) ────────────
    queue.enqueue_at(
        now + timedelta(minutes=2),
        "src.scheduler.catalog_then_stock_sync.run_catalog_then_stock",
        job_timeout=3600,
        repeat=Repeat(times=REPEAT_TIMES, interval=CATALOG_STOCK_INTERVAL_SECONDS),
    )
    logger.info("periodic_registered", func="catalog_then_stock", interval_sec=CATALOG_STOCK_INTERVAL_SECONDS)

    # ── 3. Щоденний Telegram digest (о 09:00 Kyiv = 06:00 UTC) ──────────
    next_digest = now.replace(hour=6, minute=0, second=0, microsecond=0)
    if next_digest <= now:
        next_digest += timedelta(days=1)
    queue.enqueue_at(
        next_digest,
        "src.bot.digest.send_daily_digest",
        job_timeout=120,
        repeat=Repeat(times=REPEAT_TIMES, interval=DIGEST_INTERVAL_SECONDS),
    )
    logger.info("periodic_registered", func="daily_digest", next_run=next_digest.isoformat())

    logger.info("periodic_jobs_setup_complete")


def _cancel_existing(queue, func_names: list[str]) -> None:
    """Скасовує раніше зареєстровані scheduled jobs за назвою функції."""
    try:
        registry = queue.scheduled_job_registry
        for job_id in registry.get_job_ids():
            try:
                from rq.job import Job
                job = Job.fetch(job_id, connection=queue.connection)
                if job.func_name in func_names:
                    registry.remove(job, delete_job=True)
                    logger.info("periodic_job_cancelled", job_id=job_id, func=job.func_name)
            except Exception:
                pass
    except Exception as exc:
        logger.warning("periodic_cancel_error", error=str(exc))


if __name__ == "__main__":
    setup_periodic_jobs()
