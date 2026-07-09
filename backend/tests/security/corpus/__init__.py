# ruff: noqa: RUF001, RUF002, RUF003 — RU-PDN corpus mixes Cyrillic + Latin by domain
"""Golden PII corpus for the RU-PDN INN detector precision/recall gate (01.9a).

Closes DV-04 / DV-05: it measures the INN-10 false-positive rate and lets the
precision test prove the context-aware detector drives it ≤1% while the recall
test proves realistic, labelled INN contexts are still caught.

Rows are LABELLED so the tests can score them:

* ``INN_POSITIVES``        — text that IS an ИНН in realistic RU context (the
                             «ИНН» keyword is present). MUST be flagged as INN.
* ``INN_HARD_NEGATIVES``   — checksum-PASSING 10-digit numbers with NO «ИНН»
                             context (order / invoice / account / tracking /
                             timestamp ids). MUST NOT be flagged. This is the
                             adversarial set: the pre-01.9a checksum-only
                             detector flags ~100 % of them; the context-aware
                             detector flags none.
* ``INN_RANDOM_NEGATIVES`` — arbitrary 10-digit runs with no context (models the
                             wild): ~10 % happen to pass the single control
                             digit, so the checksum-only baseline FP is ~10 %
                             here — the ~10 % figure DV-05 records.
* ``OTHER_POSITIVES``      — SNILS / passport / phone / e-mail positives, to
                             guard the non-INN detectors against a tuning
                             regression.

The checksum-valid INNs are GENERATED with an INDEPENDENT implementation of the
official RU control-digit algorithm (deterministic; a fixed PRNG seed), NOT the
detector's own code — so the corpus cross-checks the detector instead of
mirroring a shared bug.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# ── Independent RU INN control-digit algorithm (generation side) ─────────────
_INN10_W = (2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN12_W11 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN12_W12 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)


def _control(digits: list[int], weights: tuple[int, ...]) -> int:
    return sum(x * w for x, w in zip(digits, weights, strict=True)) % 11 % 10


def make_inn10(prefix9: int) -> str:
    """Build a checksum-valid INN-10 from a 9-digit integer prefix."""
    body = f"{prefix9 % 1_000_000_000:09d}"
    return body + str(_control([int(c) for c in body], _INN10_W))


def make_inn12(prefix10: int) -> str:
    """Build a checksum-valid INN-12 from a 10-digit integer prefix."""
    body = f"{prefix10 % 10_000_000_000:010d}"
    d = [int(c) for c in body]
    c11 = _control(d, _INN12_W11)
    c12 = _control([*d, c11], _INN12_W12)
    return f"{body}{c11}{c12}"


def _inn10_checksum_ok(run: str) -> bool:
    """Independent checksum check — the pre-01.9a (context-free) detection rule."""
    if len(run) != 10 or not run.isdigit():
        return False
    d = [int(c) for c in run]
    return _control(d[:9], _INN10_W) == d[9]


@dataclass(frozen=True)
class CorpusRow:
    """One labelled corpus row."""

    text: str
    should_flag_inn: bool
    note: str


# ── Positives: realistic RU contexts that DO contain an ИНН (must be flagged) ─
# Generated valid INNs embedded in the label forms a real deliverable uses.
_P10 = [make_inn10(p) for p in (783000229, 770401001, 502100123, 616400777, 246600555)]
_P10B = [make_inn10(p) for p in (784001234, 771002345, 502003456, 616004567, 246005678, 390006789)]
_P12 = [make_inn12(p) for p in (5001007322, 7701123456, 3123004567)]

INN_POSITIVES: list[CorpusRow] = [
    CorpusRow(f"ИНН организации: {_P10[0]}.", True, "inn10 label+colon"),
    CorpusRow(f"мой ИНН {_P10[1]}", True, "inn10 keyword+space"),
    CorpusRow(f"Реквизиты компании — ИНН {_P10[2]}, КПП 780101001.", True, "inn10 in sentence"),
    CorpusRow(f"ИНН:{_P10[3]}", True, "inn10 structural no-space"),
    CorpusRow(f"ИНН № {_P10[4]} присвоен ФНС.", True, "inn10 with №"),
    CorpusRow(f"инн {_P10[0]} проверьте в ЕГРЮЛ", True, "inn10 lowercase keyword"),
    CorpusRow(f"Плательщик, ИНН {_P10[1]}, оплатил счёт.", True, "inn10 mid-clause"),
    CorpusRow(f"ИНН поставщика {_P10[2]} внесён в договор.", True, "inn10 qualified label"),
    CorpusRow(f"ИНН ИП: {_P12[0]}", True, "inn12 label"),
    CorpusRow(f"мой ИНН {_P12[1]} как физлица", True, "inn12 sentence"),
    CorpusRow(f"{_P12[2]}", True, "inn12 bare (context-free double-checksum)"),
    # 01.9a SECURE-audit: real-deliverable diversity the fixed-40ch window missed.
    CorpusRow(
        '{"company": "ООО Ромашка", "inn": "' + _P10B[0] + '"}',
        True,
        "inn10 Latin JSON key (model_dump — the default artifact form)",
    ),
    CorpusRow(
        "| Организация | ИНН | Город |\n| ООО Ромашка | " + _P10B[1] + " | Москва |",
        True,
        "inn10 wide table row (header->cell, label one line up)",
    ),
    CorpusRow(
        f"Налогоплательщик {_P10B[2]} состоит на учёте в ФНС.", True, "inn10 spelled-out label"
    ),
    CorpusRow(
        f"Налоговый номер {_P10B[3]} внесён в реестр.", True, "inn10 «налоговый номер» synonym"
    ),
    CorpusRow(f"{_P10B[4]} — это ИНН поставщика.", True, "inn10 keyword AFTER the number"),
    CorpusRow(
        f"ИНН головной организации-поставщика по государственному договору: {_P10B[5]}",
        True,
        "inn10 qualified label >40 chars from run",
    ),
    CorpusRow(f"INN: {_P10B[0]} (registration record)", True, "inn10 Latin INN: label"),
]

# ── Other-category positives (non-INN detectors must not regress) ────────────
OTHER_POSITIVES: list[tuple[str, str]] = [
    ("СНИЛС 112-233-445 95 в анкете", "snils"),
    ("паспорт 4509 123456 выдан ОВД", "passport"),
    ("звоните +7 916 123-45-67 днём", "phone"),
    ("пишите ivan.petrov@example.com", "email"),
]

# ── Negatives: non-INN 10-digit numbers with NO «ИНН» context ────────────────
# NB: none of these templates contain the «ИНН» token, so the context-aware
# detector must flag zero of them.
_NEG_TEMPLATES = (
    "Заказ №{n} отгружен со склада.",
    "Счёт-фактура {n} оплачена полностью.",
    "Номер лицевого счёта: {n}.",
    "Трек-номер отправления {n}.",
    "Артикул товара {n} снят с продажи.",
    "Транзакция {n} подтверждена банком.",
    "Договор {n} продлён на год.",
    "Табельный номер сотрудника {n}.",
    "Код бронирования {n} действителен.",
    "{n}",  # bare number — zero context
)

_HARD_N = 360
_RANDOM_N = 360


def _build_hard_negatives() -> list[CorpusRow]:
    """≥300 checksum-PASSING 10-digit numbers in non-INN contexts.

    A deterministic 9-digit prefix walk → every number is a valid INN-10 by
    construction, so the checksum-only baseline flags all of them; the
    context-aware detector must flag none (no «ИНН» token in any template).
    """
    rng = random.Random(20260709)  # corpus generation, not crypto
    rows: list[CorpusRow] = []
    for i in range(_HARD_N):
        prefix9 = rng.randrange(100_000_000, 1_000_000_000)
        number = make_inn10(prefix9)
        assert _inn10_checksum_ok(number)  # invariant: this set is 100% checksum-valid
        template = _NEG_TEMPLATES[i % len(_NEG_TEMPLATES)]
        rows.append(CorpusRow(template.format(n=number), False, "hard: checksum-passing non-INN"))
    return rows


def _build_random_negatives() -> list[CorpusRow]:
    """Arbitrary 10-digit runs with no context — models the wild (~10% pass)."""
    rng = random.Random(4242)  # corpus generation, not crypto
    rows: list[CorpusRow] = []
    for i in range(_RANDOM_N):
        number = "".join(str(rng.randrange(10)) for _ in range(10))
        template = _NEG_TEMPLATES[i % len(_NEG_TEMPLATES)]
        rows.append(CorpusRow(template.format(n=number), False, "random: arbitrary 10-digit"))
    return rows


INN_HARD_NEGATIVES: list[CorpusRow] = _build_hard_negatives()
INN_RANDOM_NEGATIVES: list[CorpusRow] = _build_random_negatives()
INN_NEGATIVES: list[CorpusRow] = INN_HARD_NEGATIVES + INN_RANDOM_NEGATIVES


def baseline_inn10_flag(text: str) -> bool:
    """Pre-01.9a (checksum-only) INN-10 decision — the baseline the tuning replaces.

    Extracts standalone 10-digit runs and returns True if any passes the control
    digit, ignoring context — exactly what ``pii.py`` did before 01.9a.
    """
    return any(_inn10_checksum_ok(token) for token in _iter_10digit_runs(text))


def _iter_10digit_runs(text: str) -> list[str]:
    runs: list[str] = []
    current: list[str] = []
    for ch in [*text, " "]:  # sentinel flush
        if ch.isdigit():
            current.append(ch)
        else:
            if len(current) == 10:
                runs.append("".join(current))
            current = []
    return runs


__all__ = [
    "INN_HARD_NEGATIVES",
    "INN_NEGATIVES",
    "INN_POSITIVES",
    "INN_RANDOM_NEGATIVES",
    "OTHER_POSITIVES",
    "CorpusRow",
    "baseline_inn10_flag",
    "make_inn10",
    "make_inn12",
]
