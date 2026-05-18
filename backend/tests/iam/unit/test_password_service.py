"""Unit: PasswordService — hash/verify roundtrip + needs_rehash + tamper detection."""

from __future__ import annotations

from argon2 import PasswordHasher
from src.iam.services.password_service import PasswordService


def test_hash_returns_argon2id_phc_string(password_service: PasswordService) -> None:
    h = password_service.hash("correct-horse-battery-staple")
    assert h.startswith("$argon2id$")
    assert "$" in h[10:]  # PHC delimiters


def test_verify_happy_path(password_service: PasswordService) -> None:
    h = password_service.hash("S3cret-pass!")
    assert password_service.verify(h, "S3cret-pass!") is True


def test_verify_returns_false_on_mismatch(password_service: PasswordService) -> None:
    h = password_service.hash("right-password")
    assert password_service.verify(h, "wrong-password") is False


def test_verify_returns_false_on_malformed_hash(password_service: PasswordService) -> None:
    assert password_service.verify("not-a-valid-hash", "anything") is False


def test_needs_rehash_false_with_current_hasher(password_service: PasswordService) -> None:
    h = password_service.hash("x")
    assert password_service.needs_rehash(h) is False


def test_needs_rehash_true_after_params_change() -> None:
    """When the production hasher is upgraded, old hashes should be flagged."""
    weak = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)
    strong = PasswordHasher(time_cost=3, memory_cost=4096, parallelism=2)
    old_hash = weak.hash("pw")
    ps = PasswordService(hasher=strong)
    assert ps.needs_rehash(old_hash) is True
