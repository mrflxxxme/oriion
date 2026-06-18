"""Unit: YC Lockbox direct-read + the pydantic-settings source (AC-W1-9)."""

from __future__ import annotations

import base64

import httpx
import pytest
from src._shared.lockbox import (
    LockboxError,
    fetch_iam_token_from_metadata,
    fetch_lockbox_secrets,
)


def _install_transport(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    original = httpx.Client

    def patched(*args: object, **kwargs: object) -> httpx.Client:
        kwargs["transport"] = transport
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("src._shared.lockbox.httpx.Client", patched)


def test_fetch_lockbox_secrets_parses_text_and_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization", "")
        seen["path"] = request.url.path
        return httpx.Response(
            200,
            json={
                "versionId": "v-1",
                "entries": [
                    {"key": "DATABASE_URL", "textValue": "postgresql+asyncpg://x/db"},
                    {
                        "key": "BYOK_MASTER_KEY_B64",
                        "binaryValue": base64.b64encode(b"raw-secret").decode(),
                    },
                ],
            },
        )

    _install_transport(monkeypatch, httpx.MockTransport(handler))

    secrets = fetch_lockbox_secrets("sid-123", iam_token="explicit-token")

    assert secrets == {
        "DATABASE_URL": "postgresql+asyncpg://x/db",
        "BYOK_MASTER_KEY_B64": "raw-secret",
    }
    assert seen["auth"] == "Bearer explicit-token"  # explicit token used, no metadata hop
    assert seen["path"].endswith("/lockbox/v1/secrets/sid-123/payload")


def test_fetch_iam_token_from_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("metadata-flavor") == "Google"
        return httpx.Response(200, json={"access_token": "meta-token"})

    _install_transport(monkeypatch, httpx.MockTransport(handler))
    assert fetch_iam_token_from_metadata() == "meta-token"


def test_fetch_lockbox_secrets_http_error_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "denied"})

    _install_transport(monkeypatch, httpx.MockTransport(handler))
    with pytest.raises(LockboxError, match="lockbox payload fetch failed"):
        fetch_lockbox_secrets("sid", iam_token="t")


# ── pydantic-settings source integration ────────────────────────────────


def test_settings_source_noop_without_secret_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """No LOCKBOX_SECRET_ID → Settings constructs with zero network calls."""
    monkeypatch.delenv("LOCKBOX_SECRET_ID", raising=False)

    def _boom(*_a: object, **_k: object) -> dict[str, str]:
        raise AssertionError("Lockbox must not be queried without LOCKBOX_SECRET_ID")

    monkeypatch.setattr("src._shared.config.fetch_lockbox_secrets", _boom)
    from src._shared.config import Settings

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.lockbox_secret_id == ""


def test_settings_source_populates_from_lockbox(monkeypatch: pytest.MonkeyPatch) -> None:
    """With LOCKBOX_SECRET_ID set, payload keys populate Settings fields."""
    monkeypatch.setenv("LOCKBOX_SECRET_ID", "sid")
    monkeypatch.delenv("GIGACHAT_AUTH_KEY", raising=False)

    monkeypatch.setattr(
        "src._shared.config.fetch_lockbox_secrets",
        lambda *_a, **_k: {"GIGACHAT_AUTH_KEY": "from-lockbox"},
    )
    from src._shared.config import Settings

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.gigachat_auth_key.get_secret_value() == "from-lockbox"


def test_settings_env_overrides_lockbox(monkeypatch: pytest.MonkeyPatch) -> None:
    """An explicit env-var wins over Lockbox (break-glass override)."""
    monkeypatch.setenv("LOCKBOX_SECRET_ID", "sid")
    monkeypatch.setenv("GIGACHAT_AUTH_KEY", "from-env")
    monkeypatch.setattr(
        "src._shared.config.fetch_lockbox_secrets",
        lambda *_a, **_k: {"GIGACHAT_AUTH_KEY": "from-lockbox"},
    )
    from src._shared.config import Settings

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.gigachat_auth_key.get_secret_value() == "from-env"
