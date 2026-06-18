"""Dramatiq broker selection — one source of truth for web + worker + tests.

The hazard with Dramatiq + FastAPI is init ordering: ``@dramatiq.actor`` binds to
whatever broker is global at *decoration* time, and a later ``set_broker`` does not
move already-declared actors. So the broker must be chosen ONCE, at import, before
``actor.py`` is imported:

* Tests set ``DRAMATIQ_TESTING=1`` (the root ``tests/conftest.py`` does this at the
  very top, before the app — and therefore the actor module — is imported) → a
  ``StubBroker`` with no network. The StubBroker test pattern then drives the actor
  synchronously via ``dramatiq.Worker``.
* Real processes (web + worker) get a ``RedisBroker`` (lazy connection — importing
  is safe even when Redis is down; it connects on the first ``send``/consume).

``configure_broker(settings)`` is also exposed so the worker entrypoint can rebuild
the broker explicitly from a known Settings object.
"""

from __future__ import annotations

import os

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.stub import StubBroker

from src._shared.config import Settings, get_settings


def _testing() -> bool:
    settings = get_settings()
    return os.environ.get("DRAMATIQ_TESTING") == "1" or settings.app_env == "test"


def _build_broker(settings: Settings) -> dramatiq.Broker:
    # dramatiq.* is ignore_missing_imports → the broker classes are Any, so the
    # constructor calls read as untyped in this typed module.
    if _testing():
        return StubBroker()  # type: ignore[no-untyped-call]
    return RedisBroker(url=settings.redis_url.get_secret_value())  # type: ignore[no-untyped-call]


def configure_broker(settings: Settings) -> dramatiq.Broker:
    """Build + install the broker for the current process. Called at import below
    and again (explicitly) by the worker entrypoint."""
    broker = _build_broker(settings)
    dramatiq.set_broker(broker)
    return broker


# Install at import so ``@dramatiq.actor`` (in actor.py) binds to the right broker.
configure_broker(get_settings())
