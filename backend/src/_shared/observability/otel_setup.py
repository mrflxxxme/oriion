"""OpenTelemetry SDK initialization для Phase 00.6 staging stack.

Wired в `src/main.py::lifespan` once at startup. Auto-instruments FastAPI
(request spans), httpx (outbound LLM calls), and asyncpg (DB queries). The
collector at `OTEL_EXPORTER_OTLP_ENDPOINT` fans out to Tempo (traces) and
Prometheus (metrics).

The setup is idempotent and feature-gated: setting `OTEL_TRACES_ENABLED=false`
short-circuits to no-op, which is what unit tests want (they're invoked
without a running collector and shouldn't pay the SDK init cost).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

_logger = logging.getLogger(__name__)

_tracer_provider: TracerProvider | None = None
_instrumented = False


def setup_otel(
    *,
    service_name: str,
    otlp_endpoint: str,
    enabled: bool = True,
) -> None:
    """Initialize OpenTelemetry SDK + auto-instrumentation.

    Idempotent: subsequent calls (e.g. lifespan-re-entry в tests) are no-ops.
    Disabling via `enabled=False` skips ALL instrumentation — use in unit
    test contexts that don't need a collector.

    Args:
        service_name: Resource attribute `service.name`; surfaces in Tempo UI.
        otlp_endpoint: gRPC endpoint of the OTLP collector
            (e.g. `http://otel-collector:4317`). Empty string disables
            exporter while keeping in-process span recording — useful for
            integration tests that want to assert span shape without network.
        enabled: Master switch; False = full no-op.
    """
    global _tracer_provider, _instrumented

    if not enabled:
        _logger.info("otel.setup.skipped", extra={"reason": "OTEL_TRACES_ENABLED=false"})
        return

    if _instrumented:
        _logger.debug("otel.setup.already_done")
        return

    # Lazy imports — if opentelemetry packages aren't installed (e.g. minimal
    # CI image), import-time errors stay localized to this call site.
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # noqa: F401
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.namespace": "oriion",
            "deployment.environment": "staging",
        }
    )
    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        # `insecure=True` because the OTLP collector inside our compose
        # network has no TLS — caddy fronts external traffic, collector is
        # internal-only. Stage B will swap к secure if we expose the
        # collector externally (we don't plan to).
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    else:
        _logger.info("otel.setup.no_exporter", extra={"reason": "OTLP endpoint empty"})

    trace.set_tracer_provider(provider)
    _tracer_provider = provider

    # Auto-instrument outbound + DB layers. FastAPI instrumentation is
    # applied lazily by FastAPIInstrumentor when it sees the app object —
    # we don't have the app here, so `src/main.py` calls
    # `FastAPIInstrumentor.instrument_app(app)` itself right after
    # FastAPI() construction. We pre-arm the httpx and asyncpg sides here.
    HTTPXClientInstrumentor().instrument()
    # opentelemetry-instrumentation-asyncpg untyped в 0.60b1; HTTPX
    # instrumentor ships type info already.
    AsyncPGInstrumentor().instrument()  # type: ignore[no-untyped-call]

    _instrumented = True
    _logger.info(
        "otel.setup.complete",
        extra={
            "service_name": service_name,
            "otlp_endpoint": otlp_endpoint or "<disabled>",
        },
    )


def shutdown_otel() -> None:
    """Flush remaining spans + shut down the tracer provider.

    Called from `lifespan`'s finally block. Safe to call when setup_otel
    was disabled (no-op).
    """
    global _tracer_provider, _instrumented

    if _tracer_provider is None:
        return

    _tracer_provider.shutdown()
    _tracer_provider = None
    _instrumented = False
    _logger.info("otel.shutdown.complete")
