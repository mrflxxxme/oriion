"""Unit: TotpService — enroll / confirm / verify / disable + backup codes.

Mock-first (London school): repositories are AsyncMocks; the KMS is a REAL
LocalAESKMS so the secret-at-rest encrypt/decrypt round-trip is exercised for
real (never a plaintext secret in the persisted column).
"""

from __future__ import annotations

import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pyotp
import pytest
from src.iam.exceptions import (
    TotpAlreadyEnabled,
    TotpInvalidCode,
    TotpNotEnabled,
    TotpNotEnrolled,
)
from src.iam.services.totp_service import TotpService
from src.llm_gateway.services.kms_provider import LocalAESKMS


def _build_service(
    *,
    local_kms: LocalAESKMS,
    credential_repo: AsyncMock | None = None,
    backup_code_repo: AsyncMock | None = None,
) -> tuple[TotpService, dict[str, AsyncMock]]:
    credential_repo = credential_repo or AsyncMock()
    backup_code_repo = backup_code_repo or AsyncMock()
    user_repo = AsyncMock()
    svc = TotpService(
        credential_repo=credential_repo,
        backup_code_repo=backup_code_repo,
        user_repo=user_repo,
        kms=local_kms,
    )
    return svc, {"credential": credential_repo, "backup": backup_code_repo}


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# ── enroll ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enroll_persists_encrypted_secret_never_plaintext(local_kms: LocalAESKMS) -> None:
    cred_repo = AsyncMock()
    cred_repo.find_by_user.return_value = None
    svc, _ = _build_service(local_kms=local_kms, credential_repo=cred_repo)

    enrollment = await svc.enroll(user_id=uuid4(), account_label="user@x.dev")

    # Provisioning material is returned once.
    assert enrollment.secret
    assert enrollment.provisioning_uri.startswith("otpauth://totp/")
    assert "issuer=Profiki" in enrollment.provisioning_uri

    # The persisted secret is CIPHERTEXT, and it decrypts back to the base32 secret.
    _, kwargs = cred_repo.create.call_args
    stored = kwargs["secret_encrypted"]
    assert isinstance(stored, bytes)
    assert enrollment.secret.encode("utf-8") not in stored  # not plaintext at rest
    assert (await local_kms.decrypt(stored)).decode("utf-8") == enrollment.secret


@pytest.mark.asyncio
async def test_enroll_refuses_when_already_active(local_kms: LocalAESKMS) -> None:
    cred_repo = AsyncMock()
    cred_repo.find_by_user.return_value = SimpleNamespace(
        id=uuid4(), confirmed_at=object(), disabled_at=None
    )
    svc, _ = _build_service(local_kms=local_kms, credential_repo=cred_repo)

    with pytest.raises(TotpAlreadyEnabled):
        await svc.enroll(user_id=uuid4(), account_label="user@x.dev")


@pytest.mark.asyncio
async def test_enroll_replaces_pending_row(local_kms: LocalAESKMS) -> None:
    cred_repo = AsyncMock()
    cred_repo.find_by_user.return_value = SimpleNamespace(
        id=uuid4(), confirmed_at=None, disabled_at=None
    )
    svc, _ = _build_service(local_kms=local_kms, credential_repo=cred_repo)

    await svc.enroll(user_id=uuid4(), account_label="user@x.dev")
    cred_repo.delete_for_user.assert_awaited_once()
    cred_repo.create.assert_awaited_once()


# ── confirm ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_activates_and_returns_backup_codes(local_kms: LocalAESKMS) -> None:
    secret = pyotp.random_base32()
    secret_encrypted = await local_kms.encrypt(secret.encode("utf-8"))
    cred_id = uuid4()
    cred_repo = AsyncMock()
    cred_repo.find_by_user.return_value = SimpleNamespace(
        id=cred_id, secret_encrypted=secret_encrypted, confirmed_at=None, disabled_at=None
    )
    backup_repo = AsyncMock()
    svc, _ = _build_service(
        local_kms=local_kms, credential_repo=cred_repo, backup_code_repo=backup_repo
    )

    good_code = pyotp.TOTP(secret).now()
    codes = await svc.confirm(user_id=uuid4(), code=good_code)

    cred_repo.confirm.assert_awaited_once_with(cred_id)
    assert len(codes) == 10
    # Backup codes are stored HASHED, not plaintext.
    _, kwargs = backup_repo.add_batch.call_args
    stored_hashes = kwargs["code_hashes"]
    assert all(_sha256(c) in stored_hashes for c in codes)
    assert not any(c in stored_hashes for c in codes)


@pytest.mark.asyncio
async def test_confirm_wrong_code_rejected(local_kms: LocalAESKMS) -> None:
    secret = pyotp.random_base32()
    secret_encrypted = await local_kms.encrypt(secret.encode("utf-8"))
    cred_repo = AsyncMock()
    cred_repo.find_by_user.return_value = SimpleNamespace(
        id=uuid4(), secret_encrypted=secret_encrypted, confirmed_at=None, disabled_at=None
    )
    svc, _ = _build_service(local_kms=local_kms, credential_repo=cred_repo)

    with pytest.raises(TotpInvalidCode):
        await svc.confirm(user_id=uuid4(), code="000000")
    cred_repo.confirm.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirm_without_enrollment_raises(local_kms: LocalAESKMS) -> None:
    cred_repo = AsyncMock()
    cred_repo.find_by_user.return_value = None
    svc, _ = _build_service(local_kms=local_kms, credential_repo=cred_repo)

    with pytest.raises(TotpNotEnrolled):
        await svc.confirm(user_id=uuid4(), code="123456")


# ── verify_for_login ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_verify_for_login_accepts_current_code(local_kms: LocalAESKMS) -> None:
    secret = pyotp.random_base32()
    secret_encrypted = await local_kms.encrypt(secret.encode("utf-8"))
    cred_repo = AsyncMock()
    cred_repo.find_active_by_user.return_value = SimpleNamespace(
        id=uuid4(), secret_encrypted=secret_encrypted
    )
    backup_repo = AsyncMock()
    svc, _ = _build_service(
        local_kms=local_kms, credential_repo=cred_repo, backup_code_repo=backup_repo
    )

    ok = await svc.verify_for_login(user_id=uuid4(), code=pyotp.TOTP(secret).now())
    assert ok is True
    backup_repo.find_unused_by_hash.assert_not_called()


@pytest.mark.asyncio
async def test_verify_for_login_wrong_code_returns_false(local_kms: LocalAESKMS) -> None:
    secret = pyotp.random_base32()
    secret_encrypted = await local_kms.encrypt(secret.encode("utf-8"))
    cred_repo = AsyncMock()
    cred_repo.find_active_by_user.return_value = SimpleNamespace(
        id=uuid4(), secret_encrypted=secret_encrypted
    )
    backup_repo = AsyncMock()
    backup_repo.find_unused_by_hash.return_value = None
    svc, _ = _build_service(
        local_kms=local_kms, credential_repo=cred_repo, backup_code_repo=backup_repo
    )

    assert await svc.verify_for_login(user_id=uuid4(), code="000000") is False


@pytest.mark.asyncio
async def test_verify_for_login_no_active_credential_returns_false(
    local_kms: LocalAESKMS,
) -> None:
    cred_repo = AsyncMock()
    cred_repo.find_active_by_user.return_value = None
    svc, _ = _build_service(local_kms=local_kms, credential_repo=cred_repo)

    assert await svc.verify_for_login(user_id=uuid4(), code="123456") is False


@pytest.mark.asyncio
async def test_verify_for_login_consumes_backup_code_once(local_kms: LocalAESKMS) -> None:
    secret = pyotp.random_base32()
    secret_encrypted = await local_kms.encrypt(secret.encode("utf-8"))
    cred_repo = AsyncMock()
    cred_repo.find_active_by_user.return_value = SimpleNamespace(
        id=uuid4(), secret_encrypted=secret_encrypted
    )
    backup_id = uuid4()
    backup_repo = AsyncMock()
    backup_repo.find_unused_by_hash.return_value = SimpleNamespace(id=backup_id)
    svc, _ = _build_service(
        local_kms=local_kms, credential_repo=cred_repo, backup_code_repo=backup_repo
    )

    # A non-TOTP string that matches an (unused) backup code → accepted + consumed.
    ok = await svc.verify_for_login(user_id=uuid4(), code="abcde-12345")
    assert ok is True
    backup_repo.mark_used.assert_awaited_once_with(backup_id)


# ── disable ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_disable_requires_valid_code(local_kms: LocalAESKMS) -> None:
    secret = pyotp.random_base32()
    secret_encrypted = await local_kms.encrypt(secret.encode("utf-8"))
    cred_id = uuid4()
    cred_repo = AsyncMock()
    cred_repo.find_active_by_user.return_value = SimpleNamespace(
        id=cred_id, secret_encrypted=secret_encrypted
    )
    backup_repo = AsyncMock()
    backup_repo.find_unused_by_hash.return_value = None
    svc, _ = _build_service(
        local_kms=local_kms, credential_repo=cred_repo, backup_code_repo=backup_repo
    )

    with pytest.raises(TotpInvalidCode):
        await svc.disable(user_id=uuid4(), code="000000")
    cred_repo.disable.assert_not_awaited()

    # Correct code → disabled + unused backup codes cleared.
    await svc.disable(user_id=uuid4(), code=pyotp.TOTP(secret).now())
    cred_repo.disable.assert_awaited_once_with(cred_id)
    backup_repo.delete_unused_for_credential.assert_awaited_once_with(cred_id)


@pytest.mark.asyncio
async def test_disable_when_not_enabled_raises(local_kms: LocalAESKMS) -> None:
    cred_repo = AsyncMock()
    cred_repo.find_active_by_user.return_value = None
    svc, _ = _build_service(local_kms=local_kms, credential_repo=cred_repo)

    with pytest.raises(TotpNotEnabled):
        await svc.disable(user_id=uuid4(), code="123456")
