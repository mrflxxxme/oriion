# ruff: noqa: RUF001, RUF002, RUF003 — RU-PDN detector tests mix Cyrillic + Latin by domain
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


class TestInnContext:
    """01.9a context-gate (DV-04/DV-05): a checksum-valid INN-10 is a finding
    only with an INN-labelling token near it (Cyrillic «ИНН», Latin `inn`/
    `tax_id`, spelled-out label); INN-12 stays context-free (double checksum)."""

    def test_bare_checksum_valid_inn10_not_flagged(self) -> None:
        # The core FP fix: a valid-checksum 10-digit run with no label nearby is
        # not identifiable PII, so it is NOT flagged (unlike pre-01.9a).
        assert PiiCategory.INN.value not in _cats(f"номер {VALID_INN10} в реестре")

    def test_contextual_inn10_flagged(self) -> None:
        assert PiiCategory.INN.value in _cats(f"ИНН {VALID_INN10}")

    def test_structural_inn10_no_space_flagged(self) -> None:
        assert PiiCategory.INN.value in _cats(f"ИНН:{VALID_INN10}")

    def test_lowercase_keyword_flagged(self) -> None:
        assert PiiCategory.INN.value in _cats(f"инн {VALID_INN10} проверьте")

    def test_latin_json_key_flagged(self) -> None:
        # model_dump() serialises artifacts as {"inn": "NNN"} — the default form.
        assert PiiCategory.INN.value in _cats('{"inn": "' + VALID_INN10 + '"}')

    def test_latin_tax_id_key_flagged(self) -> None:
        assert PiiCategory.INN.value in _cats('{"tax_id": "' + VALID_INN10 + '"}')

    def test_spelled_out_label_flagged(self) -> None:
        assert PiiCategory.INN.value in _cats(f"Налогоплательщик {VALID_INN10} на учёте")

    def test_keyword_after_number_flagged(self) -> None:
        # RU word order can place the label AFTER the run (same line).
        assert PiiCategory.INN.value in _cats(f"{VALID_INN10} — это ИНН поставщика")

    def test_table_header_one_line_up_flagged(self) -> None:
        text = "| Орг | ИНН | Город |\n| ООО | " + VALID_INN10 + " | Москва |"
        assert PiiCategory.INN.value in _cats(text)

    def test_word_containing_inn_is_not_context(self) -> None:
        # «длинный» contains и-н-н but is not the «ИНН» token; Latin «winner»/
        # «inner» likewise must not manufacture context for a nearby run.
        assert PiiCategory.INN.value not in _cats(f"длинный список {VALID_INN10} позиций")
        assert PiiCategory.INN.value not in _cats(f"winner number {VALID_INN10} announced")

    def test_keyword_on_distant_line_not_context(self) -> None:
        # New semantics: context is the run's line + a bounded look-behind/ahead.
        # An «ИНН» in a far earlier paragraph (beyond the window, not on the run's
        # line) does not attach to an unrelated order number.
        text = (
            "ИНН компании указан в шапке документа.\n"
            + "заполнитель " * 20
            + "\nЗаказ "
            + VALID_INN10
            + " отгружен со склада"
        )
        assert PiiCategory.INN.value not in _cats(text)

    def test_bare_inn12_still_flagged(self) -> None:
        # INN-12 keeps its context-free rule (double control digit ~1% FP).
        assert PiiCategory.INN.value in _cats(f"код {VALID_INN12} присвоен")


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
