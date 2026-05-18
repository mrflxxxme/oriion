"""structlog configuration.

JSON renderer in prod/staging (consumed by Sentry / log-aggregator).
Console renderer in dev/test (human-readable colour output).

Call `configure_structlog()` once at process start (before any logger.bind).
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from src._shared.config import get_settings


def _drop_color_message_key(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """uvicorn adds a duplicate `color_message` key — drop it."""
    event_dict.pop("color_message", None)
    return event_dict


def configure_structlog() -> None:
    """Wire structlog + stdlib logging.

    Renderer choice:
      - dev / test  → ConsoleRenderer (colour, dev-friendly)
      - staging / prod → JSONRenderer (structured, machine-parseable)

    All stdlib `logging.getLogger(...)` calls are routed through structlog
    so FastAPI / uvicorn / SQLAlchemy logs share the same envelope.
    """
    settings = get_settings()
    use_json = not (settings.is_dev or settings.is_test)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _drop_color_message_key,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if use_json:
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Route stdlib → structlog so uvicorn/sqlalchemy logs share envelope.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
