"""Prometheus metrics registration — idempotent + 9 metrics present."""

from __future__ import annotations

from prometheus_client import REGISTRY
from src._shared.observability import (
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


def test_register_default_metrics_idempotent() -> None:
    """Calling twice без error — module-level constructors run once, sanity
    check just inspects REGISTRY for the 9 expected base names."""
    register_default_metrics()
    register_default_metrics()


def test_all_9_metrics_constants_exported() -> None:
    """The 9 Counter/Gauge/Histogram objects are importable via the
    bounded-context package."""
    assert LLM_REQUEST_TOTAL is not None
    assert LLM_TOKENS_INPUT is not None
    assert LLM_TOKENS_OUTPUT is not None
    assert LLM_COST_RUB is not None
    assert LLM_LATENCY is not None
    assert LLM_PROVIDER_HEALTH is not None
    assert TASK_DURATION is not None
    assert TASK_TOTAL is not None
    assert TASK_QUEUE_DEPTH is not None


def test_metrics_registered_in_global_registry() -> None:
    """REGISTRY.collect() yields all 9 base-name metrics."""
    register_default_metrics()
    names = {m.name for m in REGISTRY.collect()}
    # Counter base names (without _total suffix per prometheus_client v0.20+):
    assert "llm_request" in names
    assert "llm_tokens_input" in names
    assert "llm_tokens_output" in names
    assert "llm_cost_rub" in names
    assert "task" in names
    # Histogram + Gauge — verbatim:
    assert "llm_request_latency_seconds" in names
    assert "task_duration_seconds" in names
    assert "llm_provider_health" in names
    assert "task_queue_depth" in names


def test_counter_increments_emit_samples() -> None:
    """Inc'ing a Counter shows up в /metrics exposition."""
    LLM_REQUEST_TOTAL.labels(provider="deepseek", model="v3", status="success").inc()
    samples = []
    for metric in REGISTRY.collect():
        if metric.name == "llm_request":
            for s in metric.samples:
                samples.append((s.name, dict(s.labels), s.value))
    matched = [
        s
        for s in samples
        if s[0] == "llm_request_total"
        and s[1] == {"provider": "deepseek", "model": "v3", "status": "success"}
    ]
    assert len(matched) == 1
    assert matched[0][2] >= 1.0


def test_gauge_set_visible() -> None:
    """Setting a Gauge value shows up в collect()."""
    LLM_PROVIDER_HEALTH.labels(provider="yandexgpt").set(0.5)
    samples = []
    for metric in REGISTRY.collect():
        if metric.name == "llm_provider_health":
            for s in metric.samples:
                samples.append((dict(s.labels), s.value))
    matched = [s for s in samples if s[0] == {"provider": "yandexgpt"}]
    assert matched, "Gauge label not collected"
    assert matched[0][1] == 0.5
