# ruff: noqa: RUF001, RUF002, RUF003 — RU-PDN corpus mixes Cyrillic + Latin by domain
"""INN recall gate on the golden corpus (01.9a — closes DV-04/DV-05).

The context-aware tuning fixes false positives; this proves it did NOT tank
recall: every realistic, labelled INN context (the «ИНН» keyword present) is
still caught, and the non-INN detectors (SNILS/passport/phone/email) are
unaffected. Baseline recall on these positives was 1.0 (the checksum-only
detector caught every valid INN); tuned recall must also be 1.0.
"""

from __future__ import annotations

import pytest
from src.security.detectors.pii import scan_pii
from src.security.ports import PiiCategory

from tests.security.corpus import INN_POSITIVES, OTHER_POSITIVES


def test_all_inn_positives_still_flagged() -> None:
    # AC-01.9a.3 — recall not degraded below the (1.0) baseline.
    missed = [
        r.note for r in INN_POSITIVES if PiiCategory.INN.value not in scan_pii(r.text).categories
    ]
    recall = 1 - len(missed) / len(INN_POSITIVES)
    assert recall == 1.0, f"recall={recall:.3f} missed={missed}"


@pytest.mark.parametrize(("text", "expected"), OTHER_POSITIVES)
def test_other_category_positives_unaffected(text: str, expected: str) -> None:
    # The tuning touches only INN-10 context; SNILS/passport/phone/email must
    # still be detected exactly as before.
    assert expected in scan_pii(text).categories
