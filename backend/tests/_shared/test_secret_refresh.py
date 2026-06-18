"""Unit: no-redeploy secret refresh — reload + rebuild + SIGHUP guard (AC-W1-9)."""

from __future__ import annotations

import signal
from types import SimpleNamespace
from typing import Any

import pytest
from src._shared import secret_refresh
from src._shared.config import Settings, get_settings, reload_settings


def _fake_app() -> Any:
    return SimpleNamespace(state=SimpleNamespace())


def test_reload_settings_rereads_lockbox(monkeypatch: pytest.MonkeyPatch) -> None:
    """reload_settings() drops the cache and re-runs the Lockbox source, so a
    rotated value is picked up without a restart."""
    monkeypatch.setenv("LOCKBOX_SECRET_ID", "sid")
    monkeypatch.delenv("WORKER_METRICS_PORT", raising=False)
    calls = {"n": 0}

    def _fetch(*_a: object, **_k: object) -> dict[str, str]:
        calls["n"] += 1
        return {"WORKER_METRICS_PORT": str(7000 + calls["n"])}

    monkeypatch.setattr("src._shared.config.fetch_lockbox_secrets", _fetch)
    get_settings.cache_clear()
    try:
        first = get_settings()
        second = reload_settings()
        assert first.worker_metrics_port == 7001
        assert second.worker_metrics_port == 7002  # re-read, not the cached value
        assert calls["n"] == 2
    finally:
        get_settings.cache_clear()


def test_apply_secret_state_swaps_app_state(monkeypatch: pytest.MonkeyPatch) -> None:
    providers = {"deepseek": object()}
    router = object()
    monkeypatch.setattr(secret_refresh, "build_llm_router", lambda _s: (providers, {}, router))
    app = _fake_app()
    settings = Settings(_env_file=None, app_env="test")  # type: ignore[call-arg]

    secret_refresh.apply_secret_state(app, settings)

    assert app.state.settings is settings
    assert app.state.llm_providers is providers
    assert app.state.llm_router is router
    assert app.state.kms_provider is not None  # LocalAESKMS (ephemeral dev key)


@pytest.mark.asyncio
async def test_refresh_app_secrets_rebuilds(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(_env_file=None, app_env="test")  # type: ignore[call-arg]
    router = object()
    monkeypatch.setattr(secret_refresh, "reload_settings", lambda: settings)
    monkeypatch.setattr(
        secret_refresh, "build_llm_router", lambda _s: ({"x": object()}, {}, router)
    )
    app = _fake_app()

    returned = await secret_refresh.refresh_app_secrets(app)

    assert returned is settings
    assert app.state.llm_router is router
    assert app.state.settings is settings


def test_register_sighup_refresh_false_without_sighup(monkeypatch: pytest.MonkeyPatch) -> None:
    """No SIGHUP (e.g. Windows) → returns False; rotation falls back to restart."""
    monkeypatch.delattr(secret_refresh.signal, "SIGHUP", raising=False)
    assert secret_refresh.register_sighup_refresh(_fake_app(), object()) is False  # type: ignore[arg-type]


@pytest.mark.skipif(not hasattr(signal, "SIGHUP"), reason="SIGHUP is Unix-only")
def test_register_sighup_refresh_registers_when_available() -> None:
    registered: list[Any] = []

    class _FakeLoop:
        def add_signal_handler(self, sig: int, cb: Any) -> None:
            registered.append((sig, cb))

    ok = secret_refresh.register_sighup_refresh(_fake_app(), _FakeLoop())  # type: ignore[arg-type]
    assert ok is True
    assert registered and registered[0][0] == signal.SIGHUP
