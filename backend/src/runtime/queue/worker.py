"""Dramatiq worker entrypoint — ``dramatiq src.runtime.queue.worker``.

Run with ``--processes 1 --threads 1`` so a single task orchestration runs at a
time (preserves the workers=1 / single global-budget invariant F-ARC-H2). The
worker process must run SSE_BACKEND=redis so its events reach the web tier's
``/stream`` subscribers.

Importing this module (a) configures the Redis broker explicitly from Settings
and (b) imports the actor so Dramatiq discovers + declares it on that broker.
"""

from __future__ import annotations

from src._shared.config import get_settings
from src._shared.logging import configure_structlog
from src.runtime.queue.broker import configure_broker

configure_structlog()
configure_broker(get_settings())

# Import AFTER the broker is configured so the actor declares on the Redis broker.
from src.runtime.queue.actor import dispatch_task_actor  # noqa: E402, F401
