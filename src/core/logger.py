"""Structured JSON Lines logger (ADR-007).

Usage:
    from src.core.logger import get_logger
    log = get_logger(__name__)
    log.info("event_name", key="value")
"""

import logging
import sys

import structlog

from src.config.settings import settings


def setup_logging() -> None:
    """Configure structlog for JSON Lines output. Call once at startup."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            # structlog.stdlib.add_logger_name,  <-- Убираем это, вызывает ошибку с PrintLogger
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.ExceptionRenderer(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Suppress noisy access logs — we log per-request in middleware
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
