# ruff: noqa: RUF001, RUF002, RUF003 — RU-PDN corpus mixes Cyrillic + Latin by domain
"""INN-10 precision gate on the golden corpus (01.9a — closes DV-04/DV-05).

Compares the pre-01.9a checksum-only baseline against the context-aware detector
on the labelled negatives, and asserts the tuned false-positive rate is ≤1%.

Measured baseline vs tuned (documented for the security-review trail; recomputed
deterministically each run from the seeded corpus):

    hard negatives (360, all checksum-passing): baseline FP = 100.0%  → tuned 0.0%
    random negatives (360, arbitrary 10-digit): baseline FP ≈  10%    → tuned 0.0%
    ALL negatives (720):                        baseline FP ≈  55%    → tuned 0.0%

The hard set isolates the exact failure DV-05 describes (a coincidental
checksum-passing run flagged with zero context); the random set reproduces the
~10% real-world FP figure DV-05 quotes.
"""

from __future__ import annotations

from collections.abc import Sequence

from src.security.detectors.pii import scan_pii
from src.security.ports import PiiCategory

from tests.security.corpus import (
    INN_HARD_NEGATIVES,
    INN_NEGATIVES,
    INN_RANDOM_NEGATIVES,
    CorpusRow,
    baseline_inn10_flag,
)


def _tuned_flags_inn(text: str) -> bool:
    return PiiCategory.INN.value in scan_pii(text).categories


def _fp_rate(rows: Sequence[CorpusRow], *, tuned: bool) -> float:
    hits = sum((_tuned_flags_inn(r.text) if tuned else baseline_inn10_flag(r.text)) for r in rows)
    return hits / len(rows)


def test_corpus_negatives_are_sized_and_labelled() -> None:
    assert len(INN_HARD_NEGATIVES) >= 300  # AC-01.9a.1 — enough to measure FP
    assert len(INN_RANDOM_NEGATIVES) >= 300
    assert all(r.should_flag_inn is False for r in INN_NEGATIVES)


def test_hard_negatives_baseline_is_high() -> None:
    # DV-05 root cause: the checksum-only detector flags (almost) every
    # checksum-passing run — here 100%, since the hard set is valid by design.
    assert _fp_rate(INN_HARD_NEGATIVES, tuned=False) >= 0.99


def test_random_negatives_baseline_near_ten_percent() -> None:
    # DV-05's ~10% figure: ~1/10 of arbitrary 10-digit runs pass the single
    # control digit. Loose bounds keep the deterministic corpus non-flaky.
    baseline = _fp_rate(INN_RANDOM_NEGATIVES, tuned=False)
    assert 0.05 <= baseline <= 0.20


def test_inn_precision_fp_at_most_one_percent() -> None:
    # AC-01.9a.2 — the gate. Context-aware detection flags none of the no-context
    # negatives, so tuned FP = 0 ≤ 0.01.
    tuned = _fp_rate(INN_NEGATIVES, tuned=True)
    baseline = _fp_rate(INN_NEGATIVES, tuned=False)
    assert tuned <= 0.01, f"tuned_fp={tuned:.4f} baseline_fp={baseline:.4f}"


def test_hard_negatives_tuned_fp_is_zero() -> None:
    assert _fp_rate(INN_HARD_NEGATIVES, tuned=True) == 0.0
