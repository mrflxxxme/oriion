"""Unit: the broker drops Dramatiq's built-in Prometheus middleware.

Live golden (2026-06-19) found that the worker's custom metrics exporter
(``start_worker_metrics_exporter``, AC-W1-13) AND Dramatiq's built-in Prometheus
middleware both bind the metrics port at worker boot → ``OSError: [Errno 98]
Address already in use`` crashes Dramatiq's exposition fork. ``configure_broker``
now drops the built-in (the custom exporter already exposes the global registry).
"""

from __future__ import annotations


def test_drop_prometheus_middleware_removes_it() -> None:
    from dramatiq.brokers.stub import StubBroker
    from dramatiq.middleware.prometheus import Prometheus
    from src.runtime.queue.broker import _drop_prometheus_middleware

    broker = StubBroker()
    # Ensure one is present (StubBroker may or may not add it by default), so the
    # removal is exercised deterministically.
    if not any(type(m).__name__ == "Prometheus" for m in broker.middleware):
        broker.add_middleware(Prometheus())
    assert any(type(m).__name__ == "Prometheus" for m in broker.middleware)

    _drop_prometheus_middleware(broker)

    assert not any(type(m).__name__ == "Prometheus" for m in broker.middleware)


def test_configure_broker_has_no_prometheus() -> None:
    from src._shared.config import get_settings
    from src.runtime.queue.broker import configure_broker

    broker = configure_broker(get_settings())  # StubBroker under DRAMATIQ_TESTING

    assert not any(type(m).__name__ == "Prometheus" for m in broker.middleware)
