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
        jwt_secret_access_v1="prod-jwt-signing-secret-min-32-characters!!",  # gitleaks:allow
        byok_master_key_b64="dGVzdA==",  # gitleaks:allow — dummy base64; guard only checks non-empty
        database_url="postgresql+asyncpg://u:p@managed-pg.yandexcloud:5432/oriion",
    )
    assert settings.app_env == "staging"


def test_dsn_password_not_leaked_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    """database_url/redis_url are SecretStr so the embedded password can't leak via
    repr/str — e.g. a logged Settings object or a connection-error traceback that
    references the field (audit P2). .get_secret_value() recovers it at the call site."""
    from pydantic import SecretStr

    _clear_secret_env(monkeypatch)
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        app_env="staging",
        jwt_secret_access_v1="prod-jwt-signing-secret-min-32-characters!!",  # gitleaks:allow
        byok_master_key_b64="dGVzdA==",  # gitleaks:allow
        database_url="postgresql+asyncpg://dbuser:sup3rsecret@pg.host:5432/oriion",  # gitleaks:allow
        redis_url="redis://:r3dispass@redis.host:6379/0",  # gitleaks:allow
    )
    assert isinstance(settings.database_url, SecretStr)
    assert isinstance(settings.redis_url, SecretStr)
    for projection in (
        repr(settings),
        str(settings.database_url),
        repr(settings.database_url),
        str(settings.redis_url),
    ):
        assert "sup3rsecret" not in projection
        assert "r3dispass" not in projection
    # The real DSN is still recoverable where it's actually needed.
    assert settings.database_url.get_secret_value().endswith("@pg.host:5432/oriion")
    assert "r3dispass" in settings.redis_url.get_secret_value()
