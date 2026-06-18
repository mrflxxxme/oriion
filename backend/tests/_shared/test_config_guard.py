"""Unit: staging/prod dev-secret guard makes the Lockbox cutover fail-safe (AC-W1-9)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from src._shared.config import Settings


def _clear_secret_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOCKBOX_SECRET_ID", raising=False)
    monkeypatch.delenv("JWT_SECRET_ACCESS_V1", raising=False)
    monkeypatch.delenv("BYOK_MASTER_KEY_B64", raising=False)


def test_guard_rejects_dev_defaults_in_staging(monkeypatch: pytest.MonkeyPatch) -> None:
    """staging boot on the dev JWT default / empty BYOK fails fast — so a missing
    Lockbox secret surfaces as a failed deploy, not an insecure-but-healthy boot."""
    _clear_secret_env(monkeypatch)
    with pytest.raises(ValidationError, match="dev default|empty"):
        Settings(_env_file=None, app_env="staging")  # type: ignore[call-arg]


def test_guard_rejects_dev_defaults_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_secret_env(monkeypatch)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="prod")  # type: ignore[call-arg]


def test_guard_skipped_in_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    """dev/test intentionally run on the defaults — the guard must not fire."""
    _clear_secret_env(monkeypatch)
    settings = Settings(_env_file=None, app_env="dev")  # type: ignore[call-arg]
    assert settings.is_dev


def test_guard_passes_with_real_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_secret_env(monkeypatch)
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        app_env="staging",
        jwt_secret_access_v1="prod-jwt-signing-secret-min-32-characters!!",
        byok_master_key_b64="cmVhbC1ieW9rLW1hc3Rlci1rZXk=",
        database_url="postgresql+asyncpg://u:p@managed-pg.yandexcloud:5432/oriion",
    )
    assert settings.app_env == "staging"
