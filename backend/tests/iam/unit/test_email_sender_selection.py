"""Unit: get_email_sender selection logic (Phase 01.8).

Covers the credential-driven switch in ``src.iam.deps.get_email_sender``:

  * dev / test               → ConsoleEmailSender
  * prod + SMTP creds present → YandexSmtpEmailSender
  * prod + SMTP creds absent  → NoOpEmailSender (deferred-live-send fallback)

Settings is constructed directly (not via env) so the test is hermetic and
never depends on a real .env — pydantic ``model_construct``-free path uses the
public constructor with explicit kwargs.
"""

from __future__ import annotations

from pydantic import SecretStr
from src._shared.config import Settings
from src.iam.deps import get_email_sender
from src.iam.services.email_service import (
    ConsoleEmailSender,
    NoOpEmailSender,
    YandexSmtpEmailSender,
)


def _settings(**overrides: object) -> Settings:
    # The prod/staging guard (_guard_no_dev_secrets) rejects dev-default
    # secrets, so a prod Settings must supply real-looking non-dev values.
    base: dict[str, object] = {
        "app_env": "prod",
        "database_url": SecretStr("postgresql+asyncpg://u:p@db.internal:5432/prod"),
        "jwt_secret_access_v1": SecretStr("prod-jwt-secret-please-32-chars-minimum-xx"),
        "byok_master_key_b64": SecretStr("dGVzdC1tYXN0ZXIta2V5LTMyLWJ5dGVzLXBhZGRpbmc="),
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_dev_selects_console() -> None:
    sender = get_email_sender(_settings(app_env="dev"))
    assert isinstance(sender, ConsoleEmailSender)


def test_test_env_selects_console() -> None:
    sender = get_email_sender(_settings(app_env="test"))
    assert isinstance(sender, ConsoleEmailSender)


def test_prod_without_creds_falls_back_to_noop() -> None:
    # No smtp_user / smtp_password → deferred-live-send fallback, no crash.
    sender = get_email_sender(_settings(app_env="prod"))
    assert isinstance(sender, NoOpEmailSender)


def test_prod_with_only_user_still_noop() -> None:
    sender = get_email_sender(_settings(app_env="prod", smtp_user="no-reply@profiki.online"))
    assert isinstance(sender, NoOpEmailSender)


def test_prod_with_only_password_still_noop() -> None:
    sender = get_email_sender(_settings(app_env="prod", smtp_password=SecretStr("pw")))
    assert isinstance(sender, NoOpEmailSender)


def test_prod_with_creds_selects_yandex_smtp() -> None:
    sender = get_email_sender(
        _settings(
            app_env="prod",
            smtp_user="no-reply@profiki.online",
            smtp_password=SecretStr("app-pass"),
        )
    )
    assert isinstance(sender, YandexSmtpEmailSender)


def test_is_smtp_configured_helper() -> None:
    assert _settings(app_env="prod").is_smtp_configured is False
    assert (
        _settings(
            app_env="prod", smtp_user="u@x.ru", smtp_password=SecretStr("pw")
        ).is_smtp_configured
        is True
    )


def test_smtp_sender_address_defaults_to_user() -> None:
    s = _settings(smtp_user="user@profiki.online")
    assert s.smtp_sender_address == "user@profiki.online"
    s2 = _settings(smtp_user="user@profiki.online", smtp_from="brand@profiki.online")
    assert s2.smtp_sender_address == "brand@profiki.online"
