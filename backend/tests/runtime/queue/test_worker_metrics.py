"""AC-W1-13: the Dramatiq worker exposes a Prometheus /metrics endpoint.

Under async dispatch (ADR-034) the orchestration runs in the worker process, so
its registry must be scraped independently of the web tier. We test the exporter
wiring without binding a real socket in CI by stubbing start_http_server.
"""

from __future__ import annotations

from typing import Any

import src.runtime.queue.worker as worker_mod
from src._shared.config import Settings, get_settings


def _settings_with_port(port: int) -> Settings:
    return get_settings().model_copy(update={"worker_metrics_port": port})


def test_exporter_noop_when_port_disabled(monkeypatch: Any) -> None:
    calls: list[int] = []
    monkeypatch.setattr(
        "prometheus_client.start_http_server", lambda port: calls.append(port)
    )
    worker_mod.start_worker_metrics_exporter(_settings_with_port(0))
    assert calls == []


def test_exporter_binds_configured_port(monkeypatch: Any) -> None:
    calls: list[int] = []
    monkeypatch.setattr(
        "prometheus_client.start_http_server", lambda port: calls.append(port)
    )
    worker_mod.start_worker_metrics_exporter(_settings_with_port(9191))
    assert calls == [9191]


def test_exporter_survives_bind_failure(monkeypatch: Any) -> None:
    def _boom(port: int) -> None:
        raise OSError("address already in use")

    monkeypatch.setattr("prometheus_client.start_http_server", _boom)
    # Must NOT raise — the worker keeps consuming even if the port is taken.
    worker_mod.start_worker_metrics_exporter(_settings_with_port(9191))
