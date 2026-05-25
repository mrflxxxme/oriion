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

from src._shared.observability.metrics import (
    LLM_COST_RUB,
    LLM_LATENCY,
    LLM_PROVIDER_HEALTH,
    LLM_REQUEST_TOTAL,
    LLM_TOKENS_INPUT,
    LLM_TOKENS_OUTPUT,
    TASK_DURATION,
    TASK_QUEUE_DEPTH,
    TASK_TOTAL,
    register_default_metrics,
)
from src._shared.observability.otel_setup import setup_otel, shutdown_otel

__all__ = [
    "LLM_COST_RUB",
    "LLM_LATENCY",
    "LLM_PROVIDER_HEALTH",
    "LLM_REQUEST_TOTAL",
    "LLM_TOKENS_INPUT",
    "LLM_TOKENS_OUTPUT",
    "TASK_DURATION",
    "TASK_QUEUE_DEPTH",
    "TASK_TOTAL",
    "register_default_metrics",
    "setup_otel",
    "shutdown_otel",
]
