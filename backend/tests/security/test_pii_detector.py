"""Unit tests for the deterministic RU-PDN DLP detector (ADR-039, layer B).

No DB, no network. Validates checksum discrimination (valid INN/SNILS detected,
invalid checksums + random runs rejected), format detectors (passport/phone/
email), the (category, span)-only finding contract, and that the raw value is
never surfaced.
"""

from __future__ import annotations

import pytest
from src.security.detectors.pii import (
    RegexPiiDetector,
    _inn10_ok,
    _inn12_ok,
    _snils_ok,
    scan_pii,
)
from src.security.ports import PiiCategory

# Checksum-valid fixtures (hand-verified against the RU algorithms).
VALID_INN10 = "7830002293"
VALID_INN12 = "500100732259"
VALID_SNILS = "112-233-445 95"  # base sum 95 (<100 branch)
VALID_SNILS_101 = "11223345900"  # base sum 101 -> control 00
VALID_SNILS_MOD = "99999999800"  # base sum 404 -> mod-101 -> control 00


def _cats(text: str) -> set[str]:
    return set(scan_pii(text).categories)


class TestInnChecksum:
    def test_valid_inn10_detected(self) -> None:
        assert PiiCategory.INN.value in _cats(f"ИНН организации: {VALID_INN10}.")

    def test_valid_inn12_detected(self) -> None:
        assert PiiCategory.INN.value in _cats(f"мой ИНН {VALID_INN12}")

    def test_invalid_inn10_checksum_rejected(self) -> None:
        # Same length, wrong control digit -> not a finding.
        assert PiiCategory.INN.value not in _cats("номер 7830002294 в договоре")

    def test_invalid_inn12_checksum_rejected(self) -> None:
        assert PiiCategory.INN.value not in _cats("код 500100732258 тут")

    def test_random_10_digit_run_not_flagged(self) -> None:
        assert PiiCategory.INN.value not in _cats("заказ 1234567890 готов")

    def test_inn10_helper_true_false(self) -> None:
        assert _inn10_ok([int(c) for c in VALID_INN10]) is True
        assert _inn10_ok([int(c) for c in "7830002294"]) is False
        assert _inn10_ok([1, 2, 3]) is False  # wrong length

    def test_inn12_helper_true_false(self) -> None:
        assert _inn12_ok([int(c) for c in VALID_INN12]) is True
        assert _inn12_ok([int(c) for c in "500100732258"]) is False
        assert _inn12_ok([1, 2, 3]) is False


class TestSnilsChecksum:
    @pytest.mark.parametrize("value", [VALID_SNILS, VALID_SNILS_101, VALID_SNILS_MOD])
    def test_valid_snils_detected(self, value: str) -> None:
        assert PiiCategory.SNILS.value in _cats(f"СНИЛС {value}")

    def test_invalid_snils_checksum_rejected(self) -> None:
        assert PiiCategory.SNILS.value not in _cats("СНИЛС 112-233-445 94")

    def test_low_number_snils_rejected(self) -> None:
        # base <= 001-001-998 has no defined checksum -> never a match.
        assert _snils_ok([0] * 11) is False

    def test_snils_helper_wrong_length(self) -> None:
        assert _snils_ok([1, 2, 3]) is False


class TestFormatDetectors:
    def test_passport_spaced_series_detected(self) -> None:
        assert PiiCategory.PASSPORT.value in _cats("паспорт 4509 123456 выдан")

    def test_passport_split_series_detected(self) -> None:
        # Split series + adjacent number (whitespace-separated) is the detected form.
        assert PiiCategory.PASSPORT.value in _cats("серия 45 09 123456 выдан")

    def test_passport_requires_separator(self) -> None:
        # 10 consecutive digits with no space is not a passport finding.
        assert PiiCategory.PASSPORT.value not in _cats("код 4509123456")

    @pytest.mark.parametrize(
        "phone",
        ["+79161234567", "89161234567", "+7 916 123-45-67", "8 (916) 123 45 67"],
    )
    def test_phone_variants_detected(self, phone: str) -> None:
        assert PiiCategory.PHONE.value in _cats(f"звоните {phone} днём")

    def test_email_detected(self) -> None:
        assert PiiCategory.EMAIL.value in _cats("пишите ivan.petrov@example.com")

    def test_benign_text_no_findings(self) -> None:
        result = scan_pii("Маркетинговый бриф по продукту. Целевая аудитория — SMB.")
        assert not result.has_pii
        assert result.categories == ()


class TestFindingContract:
    def test_findings_carry_span_not_value(self) -> None:
        text = f"ИНН {VALID_INN10} конец"
        result = RegexPiiDetector().scan(text)
        assert result.has_pii
        finding = result.findings[0]
        # A finding is (category, start, end) — the substring lives only in the
        # caller's text, never on the finding.
        assert not hasattr(finding, "value")
        assert text[finding.start : finding.end] == VALID_INN10

    def test_multiple_categories_sorted_unique(self) -> None:
        text = f"ИНН {VALID_INN10}, тел {VALID_INN10 and '+79161234567'}, mail a@b.co"
        cats = scan_pii(text).categories
        assert list(cats) == sorted(cats)
        assert len(set(cats)) == len(cats)
