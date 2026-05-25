"""Observability bounded context — Phase 00.6.

Three responsibilities, three modules:

* `otel_setup` — OpenTelemetry SDK initialization + auto-instrumentation of
  FastAPI, httpx, and asyncpg. Traces flow backend → otel-collector → Tempo.
* `metrics` — Prometheus custom metrics (llm_*, task_*, billing_*) +
  `register_default_metrics()` idempotent registration. ASGI `/metrics`
  endpoint mounted in `src/main.py`.
* `logging_setup` — structlog JSON renderer для Loki tail-from-stdout.

Per ADR-024 §3, all observability code lives in `_shared/` since every
bounded context emits metrics/spans/logs through it. No new sanctioned
cross-context import — observability uses only `_shared/config.py` to read
Settings.
"""

from src._shared.observability.otel_setup import setup_otel, shutdown_otel

# Prometheus metrics module lands в Commit C5; until then this package
# exposes only OpenTelemetry surface.

__all__ = [
    "setup_otel",
    "shutdown_otel",
]
