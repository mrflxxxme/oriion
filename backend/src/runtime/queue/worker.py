"""Dramatiq worker entrypoint — ``dramatiq src.runtime.queue.worker``.

Run with ``--processes 1 --threads 1`` so a single task orchestration runs at a
time (preserves the workers=1 / single global-budget invariant F-ARC-H2). The
worker process must run SSE_BACKEND=redis so its events reach the web tier's
``/stream`` subscribers.

Importing this module (a) configures the Redis broker explicitly from Settings,
(b) starts a Prometheus /metrics exporter on ``WORKER_METRICS_PORT`` (AC-W1-13 —
the orchestration runs here under async dispatch, so the llm_*/task_* metrics
accrue in THIS process's registry, scraped separately from the web tier), and
(c) imports the actor so Dramatiq discovers + declares it on that broker.
"""

from __future__ import annotations

import os

import structlog

from src._shared.config import Settings, get_settings
from src._shared.logging import configure_structlog
from src._shared.observability import register_default_metrics
from src.runtime.queue.broker import configure_broker

_logger = structlog.get_logger(__name__)


def start_worker_metrics_exporter(settings: Settings) -> None:
    """Expose the worker's Prometheus registry on ``settings.worker_metrics_port``.

    No-op when the port is 0 (exporter disabled). ``start_http_server`` spins a
    daemon thread serving the global REGISTRY — the same one the orchestrator +
    router increment — so a scrape of ``worker:<port>`` returns non-zero
    ``llm_request_total`` / ``task_duration_seconds`` after a demo run. Failures
    (port already bound) are logged, not fatal: the worker must keep consuming
    even if its metrics endpoint can't bind.
    """
    if settings.worker_metrics_port <= 0:
        _logger.info("runtime.worker.metrics.disabled")
        return
    # register_default_metrics() force-imports the 9 metric families so the
    # exposition is populated even before the first task runs.
    register_default_metrics()
    from prometheus_client import start_http_server

    try:
        start_http_server(settings.worker_metrics_port)
        _logger.info("runtime.worker.metrics.started", port=settings.worker_metrics_port)
    except OSError as exc:
        _logger.warning(
            "runtime.worker.metrics.bind_failed",
            port=settings.worker_metrics_port,
            error=str(exc),
        )


configure_structlog()
_settings = get_settings()
# Under the StubBroker test path the broker is already installed (broker.py runs
# configure_broker at import, and the actor is bound to it). Re-running it here
# would swap in a SECOND stub broker and orphan the actor's queue declaration —
# the exact init-ordering hazard broker.py warns about. So the real-process setup
# (broker reconfigure + /metrics bind) only runs when NOT testing; both pieces are
# unit-tested directly (start_worker_metrics_exporter) without importing this
# entrypoint's side effects.
if os.environ.get("DRAMATIQ_TESTING") != "1":
    configure_broker(_settings)
    start_worker_metrics_exporter(_settings)

# Import AFTER the broker is configured so the actors declare on the Redis broker.
from src.runtime.queue.actor import dispatch_task_actor  # noqa: E402, F401
from src.runtime.queue.outbox_relay import relay_outbox_actor  # noqa: E402  (AC-W1-4)

# Kick off the self-rescheduling outbox drain — one chain per worker boot. The
# actor re-arms itself after each run (ADR-036), so tasks.outbox rows written by
# the web tier are published at-least-once on a fixed cadence. Guarded out of the
# StubBroker test path (no Redis; tests drive relay_outbox_batch directly).
if os.environ.get("DRAMATIQ_TESTING") != "1":
    relay_outbox_actor.send()
