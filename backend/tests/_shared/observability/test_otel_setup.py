"""OpenTelemetry SDK setup — feature gate + idempotency."""

from __future__ import annotations

import src._shared.observability.otel_setup as otel_mod
from src._shared.observability import setup_otel, shutdown_otel


def test_setup_skipped_when_disabled() -> None:
    """enabled=False short-circuits — _instrumented stays False."""
    otel_mod._instrumented = False
    otel_mod._tracer_provider = None
    setup_otel(service_name="test", otlp_endpoint="", enabled=False)
    assert otel_mod._instrumented is False
    assert otel_mod._tracer_provider is None


def test_setup_with_empty_endpoint_still_initializes() -> None:
    """otlp_endpoint='' is the in-memory-test path: SDK init runs (so
    span context is real в logs), but no OTLP exporter attached."""
    # Reset module state so test is isolated.
    import contextlib

    if otel_mod._tracer_provider is not None:
        with contextlib.suppress(Exception):
            otel_mod._tracer_provider.shutdown()
    otel_mod._instrumented = False
    otel_mod._tracer_provider = None

    setup_otel(service_name="test-empty-endpoint", otlp_endpoint="", enabled=True)
    assert otel_mod._instrumented is True
    assert otel_mod._tracer_provider is not None


def test_setup_idempotent_double_call() -> None:
    """Second setup_otel call returns without re-instrumenting."""
    setup_otel(service_name="test", otlp_endpoint="", enabled=True)
    first_provider = otel_mod._tracer_provider
    setup_otel(service_name="other", otlp_endpoint="", enabled=True)
    # Same provider instance (module-state guarded).
    assert otel_mod._tracer_provider is first_provider


def test_shutdown_clears_module_state() -> None:
    """shutdown_otel resets the module flags so a fresh setup_otel can run."""
    setup_otel(service_name="test", otlp_endpoint="", enabled=True)
    assert otel_mod._tracer_provider is not None
    shutdown_otel()
    assert otel_mod._tracer_provider is None
    assert otel_mod._instrumented is False  # type: ignore[unreachable]


def test_shutdown_safe_when_never_setup() -> None:
    """shutdown_otel is a no-op when setup was skipped."""
    otel_mod._tracer_provider = None
    otel_mod._instrumented = False
    shutdown_otel()  # Should not raise
