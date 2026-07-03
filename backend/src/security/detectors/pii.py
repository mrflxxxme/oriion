"""Deterministic RU-PDN DLP detector — regex + checksum (ADR-039, layer B).

Detects the Wave-1 RU-PDN categories the founder scoped (grill 2026-07-03):
ИНН-10/ИНН-12 and СНИЛС with **control-digit validation** (a coincidental digit
run almost never satisfies the checksum, keeping false positives low), plus
паспорт / телефон / e-mail by format. Checksums make ИНН/СНИЛС explainable for a
security review — the strength of the regex approach over an ML black box.

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

# ── Checksum weight tables ──────────────────────────────────────────────────
_INN10_WEIGHTS = (2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN12_WEIGHTS_11 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN12_WEIGHTS_12 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)


def _digits(text: str) -> list[int]:
    return [int(c) for c in text if c.isdigit()]


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
            if _inn12_ok(_digits(m.group())):
                findings.append(PiiFinding(PiiCategory.INN, m.start(), m.end()))
        for m in _INN10_RE.finditer(text):
            if _inn10_ok(_digits(m.group())):
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
