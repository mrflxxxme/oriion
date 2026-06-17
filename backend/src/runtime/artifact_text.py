"""Artifact markdown normalization (founder session 2026-06-11).

Role-prompt contracts (v0.1.x §3) make leaf agents emit machine-oriented
wrappers around the human document: a YAML frontmatter block, sometimes a
whole-output ```-fence, and a trailing "structured summary" block. Those
wrappers must keep flowing BETWEEN agents (prior_context), but they must
never reach the user-facing artifact — react-markdown renders a wrapping
fence as a literal code block (raw ###/** symbols on screen).

Extracted from ``runtime.dispatch`` (file-size canon split) so dispatch.py
stays orchestration-only. The public symbols
(``strip_wrapping_fence`` / ``normalize_artifact_markdown``) are re-exported
from ``runtime.dispatch`` for backward compatibility.
"""

from __future__ import annotations

import re

_FENCE_OPEN_RE = re.compile(r"^```[a-zA-Z0-9_-]*\s*$")

# Keys that identify the trailing structured-summary block defined in the
# role-prompt output contracts (writer/analyst flat block, researcher JSON).
_SUMMARY_BLOCK_HINTS = (
    "artifact_path",
    '"summary"',
    "key_messages",
    "key_findings",
    "recommended_next",
    "critical_assumptions",
)


def strip_wrapping_fence(text: str) -> str:
    """Unwrap a single code fence enclosing the ENTIRE text, if present.

    Unwraps when the first and last lines are the sole fence lines, OR when
    the opening fence declares ``markdown``/``md`` — that info string is an
    unambiguous LLM wrap-the-whole-doc marker even when the document contains
    its own interior fenced blocks (e.g. the structured-summary block the
    role contracts mandate). Idempotent.
    """
    stripped = text.strip()
    lines = stripped.splitlines()
    if len(lines) < 2 or lines[-1].strip() != "```":
        return stripped
    opening = re.match(r"^```([a-zA-Z0-9_-]*)\s*$", lines[0])
    if opening is None:
        return stripped
    inner = lines[1:-1]
    has_inner_fence = any(line.lstrip().startswith("```") for line in inner)
    if has_inner_fence and opening.group(1).lower() not in ("markdown", "md"):
        return stripped
    return "\n".join(inner).strip()


def _strip_leading_frontmatter(text: str) -> str:
    """Drop a leading YAML frontmatter block (``---`` ... ``---``/``...``)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            return "\n".join(lines[i + 1 :]).lstrip("\n")
    return text  # unterminated frontmatter — leave untouched


def _strip_trailing_summary_block(text: str) -> str:
    """Drop a trailing fenced structured-summary block (+ its label line)."""
    lines = text.rstrip().splitlines()
    if not lines or lines[-1].strip() != "```":
        return text
    for i in range(len(lines) - 2, -1, -1):
        if _FENCE_OPEN_RE.match(lines[i].strip()):
            content = "\n".join(lines[i + 1 : -1])
            if not any(hint in content for hint in _SUMMARY_BLOCK_HINTS):
                return text
            head = lines[:i]
            while head and not head[-1].strip():
                head.pop()
            if head and re.search(r"structured\s+summary", head[-1], re.IGNORECASE):
                head.pop()
            return "\n".join(head).rstrip()
    return text


def normalize_artifact_markdown(text: str) -> str:
    """Full user-facing normalization: fence + frontmatter + summary block.

    Applied ONLY at artifact materialization (``ArtifactRef.path_or_inline``).
    The inter-agent ``prior_context`` keeps the meta (see ``_run_leaf``, which
    applies ``strip_wrapping_fence`` alone).
    """
    out = strip_wrapping_fence(text)
    out = _strip_leading_frontmatter(out)
    out = _strip_trailing_summary_block(out)
    return out.strip()


__all__ = [
    "normalize_artifact_markdown",
    "strip_wrapping_fence",
]
