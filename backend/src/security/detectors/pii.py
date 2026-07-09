# ruff: noqa: RUF001, RUF002, RUF003 — RU-PDN detector docs the Cyrillic «ИНН» token by domain
"""Deterministic RU-PDN DLP detector — regex + checksum (ADR-039, layer B).

Detects the Wave-1 RU-PDN categories the founder scoped (grill 2026-07-03):
ИНН-10/ИНН-12 and СНИЛС with **control-digit validation** (a coincidental digit
run almost never satisfies the checksum, keeping false positives low), plus
паспорт / телефон / e-mail by format. Checksums make ИНН/СНИЛС explainable for a
security review — the strength of the regex approach over an ML black box.

INN-10 precision (01.9a, closes DV-04/DV-05): a single mod-10 control digit is
satisfied by ~1/10 of arbitrary 10-digit runs, so checksum alone gives ~10%
false positives on order/invoice/account numbers. A checksum-valid INN-10 is
therefore flagged **only when an INN-labelling token is present** near the run —
the Cyrillic «ИНН», the Latin key `inn`/`tax_id`/`taxpayer` (a Pydantic
``model_dump()`` serialises as ``{"inn": "NNN"}`` — the default artifact form),
or the spelled-out «налогоплательщик» / «налоговый номер». The label may sit
before or after the run, on its line or one line up (table header → cell). A
bare 10-digit number that no text identifies as a tax id is not, on its own,
identifiable personal data (this is both the FP fix and the correct PDn
semantics). INN-12 keeps its context-free rule: its double control digit already
makes a coincidental match a ~1% event, so it stays as-is to preserve recall.

SECURITY: findings carry a ``(category, span)`` only — the matched substring is
never stored, so it cannot leak. ReDoS-safe: all patterns are linear (bounded
quantifiers, no nested/overlapping repetition).
"""

from __future__ import annotations

import re

from src.security.ports import DlpScanResult, PiiCategory, PiiDetector, PiiFinding

# ── Candidate patterns (linear, ReDoS-safe) ─────────────────────────────────
# ИНН: exactly 10 or 12 standalone digits (checksum-validated below).
_INN10_RE = re.compile(r"(?<!\d)\d{10}(?!\d)")
_INN12_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")
# СНИЛС: 11 digits, optionally grouped ``XXX-XXX-XXX YY`` (checksum-validated).
_SNILS_RE = re.compile(r"(?<!\d)\d{3}[\s-]?\d{3}[\s-]?\d{3}[\s-]?\d{2}(?!\d)")
# Паспорт РФ: 4-digit series (optionally split ``12 34``) + space + 6-digit number.
_PASSPORT_RE = re.compile(r"(?<!\d)\d{2}\s?\d{2}\s\d{6}(?!\d)")
# Телефон РФ: +7 / 8 followed by 10 digits with optional separators.
_PHONE_RE = re.compile(
    r"(?<![\w+])(?:\+7|8)[\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)"
)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# ── ИНН-10 context gate (01.9a — DV-04/DV-05 precision-tune) ─────────────────
# A checksum-valid INN-10 is flagged only when an INN-labelling token sits near
# the run — a bare checksum-passing run (order / invoice / account id) is not, on
# its own, identifiable PII, so it is not flagged (the FP fix). The context is
# matched on the run's WHOLE physical line plus a bounded look-behind/ahead, so
# the label may sit before OR after the number, on the same line, or one line up
# (a table header → cell). This is deliberately more permissive than a fixed
# offset (SECURE audit 01.9a): the negatives carry no token, so widening the
# window cannot raise the false-positive rate, while it closes recall gaps.
_INN_PRE_WINDOW = 160  # look-behind: qualified label + a preceding table-header row
_INN_POST_WINDOW = 80  # look-ahead: «NNN — это ИНН поставщика»
# INN-labelling tokens. The Cyrillic abbreviation «ИНН» AND the Latin key `inn`
# / `INN` (a Pydantic ``model_dump()`` serialises as ``{"inn": "NNN"}`` — the
# DEFAULT artifact form, never Cyrillic), the structured `tax_id` / `tax id` /
# `taxpayer` keys, and the spelled-out RU label «налогоплательщик» / «налоговый
# номер». Each token is boundary-anchored so a substring inside a word never
# matches: «длинный»/«финны» (Cyrillic), «inner»/«winner»/«innovation» (Latin),
# «таксист» never trip it; a trailing digit / «:» / «№» / «"» still counts, so
# JSON keys and «ИНН:»/«ИНН7830…» are recognised.
_INN_CONTEXT_RE = re.compile(
    r"\b(?:инн|inn)(?![a-zа-яё])"  # «ИНН» / inn / INN  (incl. JSON key "inn")
    r"|\btax[\s_]?id\b"  # tax_id / tax id / taxid
    r"|\btaxpayer\b"  # taxpayer
    r"|налогоплательщик"  # spelled-out RU label (any declension)
    r"|налогов\w*\s+номер",  # «налоговый номер» synonym
    re.IGNORECASE,
)

# ── Checksum weight tables ──────────────────────────────────────────────────
_INN10_WEIGHTS = (2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN12_WEIGHTS_11 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN12_WEIGHTS_12 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)


def _digits(text: str) -> list[int]:
    return [int(c) for c in text if c.isdigit()]


def _has_inn_context(text: str, start: int, end: int) -> bool:
    """True if an INN-labelling token sits on the run's line or in the window.

    The region searched is the union of (a) the run's whole physical line — so a
    label placed before OR after the number on the same line counts — and (b) a
    bounded look-behind/ahead that may cross one newline (a table header on the
    line above the cell, or a trailing label below).
    """
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)
    region_start = min(line_start, max(0, start - _INN_PRE_WINDOW))
    region_end = max(line_end, min(len(text), end + _INN_POST_WINDOW))
    return _INN_CONTEXT_RE.search(text[region_start:region_end]) is not None


def _inn10_ok(d: list[int]) -> bool:
    if len(d) != 10:
        return False
    control = sum(x * w for x, w in zip(d[:9], _INN10_WEIGHTS, strict=True)) % 11 % 10
    return control == d[9]


def _inn12_ok(d: list[int]) -> bool:
    if len(d) != 12:
        return False
    c11 = sum(x * w for x, w in zip(d[:10], _INN12_WEIGHTS_11, strict=True)) % 11 % 10
    c12 = sum(x * w for x, w in zip(d[:11], _INN12_WEIGHTS_12, strict=True)) % 11 % 10
    return c11 == d[10] and c12 == d[11]


def _snils_ok(d: list[int]) -> bool:
    """СНИЛС control sum (mod-101), defined for base numbers > 001-001-998."""
    if len(d) != 11:
        return False
    base = d[:9]
    if int("".join(str(x) for x in base)) <= 1001998:
        return False  # checksum undefined for low numbers — treat as non-match
    control = d[9] * 10 + d[10]
    total = sum(x * (9 - i) for i, x in enumerate(base))
    if total < 100:
        expected = total
    elif total in (100, 101):
        expected = 0
    else:
        expected = total % 101
        if expected == 100:
            expected = 0
    return expected == control


class RegexPiiDetector:
    """Deterministic RU-PDN detector (implements ``ports.PiiDetector``)."""

    def scan(self, text: str) -> DlpScanResult:
        findings: list[PiiFinding] = []

        for m in _INN12_RE.finditer(text):
            # INN-12: double control digit — coincidental match is ~1%, so it is
            # flagged context-free (preserves recall on bare valid INN-12).
            if _inn12_ok(_digits(m.group())):
                findings.append(PiiFinding(PiiCategory.INN, m.start(), m.end()))
        for m in _INN10_RE.finditer(text):
            # INN-10: single control digit passes ~1/10 of random runs, so require
            # an INN-labelling token near the run (01.9a — the DV-04/DV-05 FP fix).
            if _inn10_ok(_digits(m.group())) and _has_inn_context(text, m.start(), m.end()):
                findings.append(PiiFinding(PiiCategory.INN, m.start(), m.end()))
        for m in _SNILS_RE.finditer(text):
            if _snils_ok(_digits(m.group())):
                findings.append(PiiFinding(PiiCategory.SNILS, m.start(), m.end()))
        for m in _PASSPORT_RE.finditer(text):
            findings.append(PiiFinding(PiiCategory.PASSPORT, m.start(), m.end()))
        for m in _PHONE_RE.finditer(text):
            findings.append(PiiFinding(PiiCategory.PHONE, m.start(), m.end()))
        for m in _EMAIL_RE.finditer(text):
            findings.append(PiiFinding(PiiCategory.EMAIL, m.start(), m.end()))

        findings.sort(key=lambda f: (f.start, f.end))
        return DlpScanResult(findings=tuple(findings))


default_pii_detector: PiiDetector = RegexPiiDetector()


def scan_pii(text: str) -> DlpScanResult:
    """Scan ``text`` for RU-PDN with the default deterministic detector."""
    return default_pii_detector.scan(text)
