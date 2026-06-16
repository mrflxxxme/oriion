"""AC-W1-11 (span header redaction) + AC-W1-12 (thread-safe setup_otel)."""

from __future__ import annotations

import threading

from src._shared.observability.otel_setup import (
    _SecretRedactingSpanProcessor,
    redact_sensitive_attributes,
    setup_otel,
)


def test_redacts_authorization_and_subscription_token() -> None:
    attrs = {
        "http.request.header.authorization": "Bearer sk-secret-123",
        "http.request.header.x-subscription-token": "brave-key",
        "http.request.header.api-key": "Api-Key yandex",
        "http.url": "https://api.deepseek.com/v1/chat/completions",
    }
    out = redact_sensitive_attributes(attrs)
    assert out["http.request.header.authorization"] == "[REDACTED]"
    assert out["http.request.header.x-subscription-token"] == "[REDACTED]"
    assert out["http.request.header.api-key"] == "[REDACTED]"
    # Non-secret attributes pass through untouched.
    assert out["http.url"] == "https://api.deepseek.com/v1/chat/completions"


def test_does_not_redact_token_count_attributes() -> None:
    """`tokens_input` ends in 'tokens_input', not a sensitive header name —
    must NOT be redacted (guards against over-matching 'token')."""
    attrs = {"llm.tokens_input": 1234, "llm.tokens_output": 5678}
    out = redact_sensitive_attributes(attrs)
    assert out["llm.tokens_input"] == 1234
    assert out["llm.tokens_output"] == 5678


def test_processor_on_end_mutates_span_attributes() -> None:
    class _FakeSpan:
        def __init__(self) -> None:
            self._attributes = {
                "http.request.header.authorization": "Bearer leak",
                "http.method": "POST",
            }

    span = _FakeSpan()
    _SecretRedactingSpanProcessor().on_end(span)  # type: ignore[arg-type]
    assert span._attributes["http.request.header.authorization"] == "[REDACTED]"
    assert span._attributes["http.method"] == "POST"


def test_setup_otel_concurrent_init_is_safe() -> None:
    """AC-W1-12: concurrent setup_otel(enabled=False) calls don't race. With
    enabled=False it's a no-op, but the call must be thread-safe and not raise
    when hit from many threads (the multi-worker lifespan-reentry shape)."""
    errors: list[BaseException] = []

    def _init() -> None:
        try:
            setup_otel(service_name="t", otlp_endpoint="", enabled=False)
        except BaseException as exc:  # record any race fallout
            errors.append(exc)

    threads = [threading.Thread(target=_init) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
