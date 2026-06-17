"""structlog configuration with OpenTelemetry trace correlation.

JSON renderer in staging/prod (consumed by Loki via container stdout tail).
Console renderer in dev/test (human-readable colour output).
Override via `Settings.log_format = json | console | auto` so docker-compose
local-staging stack can force JSON while pytest stays human-readable.

Every emitted log event auto-injects the active OpenTelemetry trace_id +
span_id (when present) — this lets Grafana surface trace<->log jumps
between Loki and Tempo. Without the OTel processor traces are stitched
по timestamp + service.name only, which is brittle at high ingestion rate.

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


def _inject_otel_context(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """Pull active OTel span context into the log event.

    No-op if OpenTelemetry isn't initialized (setup_otel skipped) — the
    SDK returns INVALID_SPAN as current span and we don't pollute the
    event_dict with zero-valued trace_id keys. Loki + Tempo correlation
    only fires when a real request span is active.
    """
    try:
        from opentelemetry import trace as _otel_trace

        span = _otel_trace.get_current_span()
        ctx = span.get_span_context()
        if ctx.is_valid:
            event_dict["trace_id"] = f"{ctx.trace_id:032x}"
            event_dict["span_id"] = f"{ctx.span_id:016x}"
    except ImportError:
        # opentelemetry not installed — skip silently. setup_otel raises
        # ImportError before we ever get here, so this branch is defensive.
        pass
    return event_dict


def configure_structlog() -> None:
    """Wire structlog + stdlib logging.

    Renderer choice (`Settings.log_format`):
      - "auto" (default) → JSON в staging/prod, ConsoleRenderer dev/test
      - "json"            → force JSON regardless of app_env
      - "console"         → force ConsoleRenderer regardless of app_env

    Phase 00.6: OTel-aware processor injects `trace_id` + `span_id` into
    every event when a request span is active. Loki LogQL `{service="oriion-
    backend"} | json | trace_id != ""` becomes a clean filter to feed
    Grafana «View related trace» action linking to Tempo.

    All stdlib `logging.getLogger(...)` calls are routed through structlog
    so FastAPI / uvicorn / SQLAlchemy logs share the same envelope.
    """
    settings = get_settings()

    if settings.log_format == "json":
        use_json = True
    elif settings.log_format == "console":
        use_json = False
    else:  # auto
        use_json = not (settings.is_dev or settings.is_test)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _inject_otel_context,
        _drop_color_message_key,
        structlog.processors.StackInfoRenderer(),
    ]

    if use_json:
        # format_exc_info renders exc_info into a string field for the JSON log.
        # ConsoleRenderer does its OWN (prettier) exception formatting, and having
        # format_exc_info ahead of it makes structlog warn ("Remove format_exc_info
        # from your processor chain…") the moment an exception is rendered — which
        # under pytest's filterwarnings=error is a hard failure. So it belongs in
        # the JSON branch only.
        processors: list[Processor] = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = [*shared_processors, structlog.dev.ConsoleRenderer(colors=True)]

    structlog.configure(
        processors=processors,
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
