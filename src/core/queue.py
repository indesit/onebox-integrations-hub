"""Redis Queue (rq) integration (HUB-007)."""

from typing import Any, Callable

import redis as redis_lib
from rq import Queue

from src.config.settings import settings
from src.core.logger import get_logger

logger = get_logger(__name__)

_redis_conn: redis_lib.Redis | None = None  # type: ignore[type-arg]


def get_redis() -> redis_lib.Redis:  # type: ignore[type-arg]
    global _redis_conn
    if _redis_conn is None:
        _redis_conn = redis_lib.from_url(settings.redis_url)
    return _redis_conn


def get_queue(name: str = "default") -> Queue:
    return Queue(name, connection=get_redis(), is_async=True)


def enqueue_task(
    func: Callable[..., Any],
    *args: Any,
    queue_name: str = "default",
    **kwargs: Any,
) -> str:
    """Enqueue a callable and return the rq job id."""
    q = get_queue(queue_name)
    # Используем полное имя функции для корректного импорта воркером
    job = q.enqueue(f"{func.__module__}.{func.__name__}", *args, **kwargs)
    logger.info("task_enqueued", job_id=job.id, func=f"{func.__module__}.{func.__name__}")
    return job.id
