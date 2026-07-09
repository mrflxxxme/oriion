"""AC-W1-25 — role-prompt hardening: parse integrity + example diversification.

Asserts every canonical role-prompt (1) still parses (9-section structure +
required frontmatter), (2) is bumped to the v1.0.0 / stable hardening contract,
and (3) carries ≥2 §6 few-shot examples beyond the single market-brief demo.
The clean-artifact conformance half of AC-W1-25 is exercised by the
normalize_artifact_markdown tests (tests/runtime/test_dispatch.py) + the live
golden run; here we lock the prompt-content invariants.
"""

from __future__ import annotations

import pytest
from src.agents.services.role_prompt_loader import load_role_prompt

# (slug, minimum total §6 examples after diversification, pinned SemVer)
# writer bumped to 1.1.0 by the 2026-07-10 anti-fabrication hardening (zero-fabrication
# output-discipline constraint added to §3 after TG-008 fabricated case-study metrics).
_ROLE_MIN_EXAMPLES = [
    ("coordinator", 3, "1.0.1"),
    ("researcher", 4, "1.0.1"),
    ("analyst", 5, "1.0.1"),
    ("writer", 4, "1.1.1"),
]


@pytest.mark.parametrize(("slug", "min_examples", "version"), _ROLE_MIN_EXAMPLES)
def test_role_prompt_parses_and_is_hardened(slug: str, min_examples: int, version: str) -> None:
    """load_role_prompt enforces the 9-section structure; we add the stable
    hardening contract + the §6 diversification floor on top."""
    rp = load_role_prompt(slug)

    # Stable hardening contract (ADR-010 hardening pass at Phase 01.1); writer carries
    # the 1.1.0 anti-fabrication bump on top.
    assert rp.version == version, f"{slug}: version not pinned to {version}"
    assert rp.frontmatter.get("quality_bar") == "stable", f"{slug}: quality_bar not stable"

    # §6 few-shot diversification (AC-W1-25): ≥2 examples beyond the brief demo.
    # Heading convention is inconsistent across roles: coordinator/researcher use
    # "## Example N", analyst/writer use "## Пример N" — count both.
    section_6 = rp.sections[6]
    example_count = section_6.count("## Example") + section_6.count("## Пример")
    assert example_count >= min_examples, (
        f"{slug}: §6 has {example_count} examples, expected ≥{min_examples} "
        "(AC-W1-25 wants ≥2 non-brief examples per role)"
    )
