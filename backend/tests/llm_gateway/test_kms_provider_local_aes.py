"""Unit tests for LocalAESKMS — roundtrip + tamper detection."""

from __future__ import annotations

import base64
import os

import pytest
from src.llm_gateway.exceptions import KMSError
from src.llm_gateway.services.kms_provider import (
    LocalAESKMS,
    YandexKMS,
    get_kms_provider,
)


@pytest.mark.asyncio
async def test_encrypt_then_decrypt_roundtrips(master_key_bytes: bytes) -> None:
    kms = LocalAESKMS(master_key=master_key_bytes)
    plaintext = b"sk-test-very-long-fake-api-key-1234567890"  # gitleaks:allow
    ciphertext = await kms.encrypt(plaintext)
    assert ciphertext != plaintext
    assert len(ciphertext) >= 12 + 16  # nonce + GCM tag
    out = await kms.decrypt(ciphertext)
    assert out == plaintext


@pytest.mark.asyncio
async def test_encrypt_uses_fresh_nonce_each_call(master_key_bytes: bytes) -> None:
    """Two encryptions of identical plaintext must produce distinct ciphertexts."""
    kms = LocalAESKMS(master_key=master_key_bytes)
    pt = b"identical input"
    a = await kms.encrypt(pt)
    b = await kms.encrypt(pt)
    assert a != b  # nonce randomness ensures distinct ciphertexts


@pytest.mark.asyncio
async def test_tampered_ciphertext_raises_kms_error(master_key_bytes: bytes) -> None:
    kms = LocalAESKMS(master_key=master_key_bytes)
    ct = bytearray(await kms.encrypt(b"secret"))
    # Flip the last byte of the GCM auth tag.
    ct[-1] ^= 0x01
    with pytest.raises(KMSError):
        await kms.decrypt(bytes(ct))


@pytest.mark.asyncio
async def test_truncated_ciphertext_raises_kms_error(master_key_bytes: bytes) -> None:
    kms = LocalAESKMS(master_key=master_key_bytes)
    with pytest.raises(KMSError):
        await kms.decrypt(b"too-short")


def test_init_rejects_wrong_key_length() -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        LocalAESKMS(master_key=b"only-16-bytes-key")


def test_init_uses_env_when_no_master_key(monkeypatch: pytest.MonkeyPatch) -> None:
    # autouse fixture already sets BYOK_MASTER_KEY_B64 — re-set explicitly.
    raw = os.urandom(32)
    monkeypatch.setenv("BYOK_MASTER_KEY_B64", base64.b64encode(raw).decode("ascii"))
    kms = LocalAESKMS()
    assert kms is not None


def test_init_rejects_missing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BYOK_MASTER_KEY_B64", raising=False)
    with pytest.raises(ValueError, match="BYOK_MASTER_KEY_B64"):
        LocalAESKMS()


@pytest.mark.asyncio
async def test_yandex_kms_stub_raises_not_implemented() -> None:
    kms = YandexKMS()
    with pytest.raises(NotImplementedError):
        await kms.encrypt(b"x")
    with pytest.raises(NotImplementedError):
        await kms.decrypt(b"x")


def test_get_kms_provider_default_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KMS_BACKEND", raising=False)
    provider = get_kms_provider()
    assert isinstance(provider, LocalAESKMS)


def test_get_kms_provider_yandex(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KMS_BACKEND", "yandex")
    provider = get_kms_provider()
    assert isinstance(provider, YandexKMS)


def test_get_kms_provider_unknown_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KMS_BACKEND", "exotic")
    with pytest.raises(ValueError, match="Unknown KMS_BACKEND"):
        get_kms_provider()
