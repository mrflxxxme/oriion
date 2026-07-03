"""Heuristic prompt-injection scanner + B1 neutralize (ADR-039, layer B).

Wave-1 injection risk is low (the only external content is ``web_search`` /
``read_url`` results — no outward connectors until 01.9), so this is a curated
set of **high-confidence** patterns (instruction-override, jailbreak markers,
system-prompt exfiltration, chat-template delimiter smuggling) rather than an ML
classifier. Conservative by design: benign search results do not match, so the
scanner is a no-op on legitimate content.

B1 (grill 2026-07-03): a hit does NOT block the task — the flagged fragment is
replaced with a marker and the rest of the (legitimate) content flows on. One
injected line in a fetched web page must not kill the whole task.

SECURITY: findings carry ``(pattern_id, span)`` only — never the matched text.
ReDoS-safe: linear patterns, no nested/overlapping quantifiers.
"""

from __future__ import annotations

import re

from src.security.ports import InjectionFinding, InjectionScanner, InjectionScanResult

_MARKER = "[фильтр безопасности: подозрительный фрагмент удалён]"

# (pattern_id, compiled regex). IGNORECASE; every pattern is linear.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "instruction_override",
        re.compile(
            r"(?:ignore|disregard|forget)\s+(?:all\s+|any\s+|the\s+|your\s+|"
            r"everything\s+)*(?:previous|prior|above|earlier|preceding|foregoing)"
            r"\s+(?:instruction|prompt|direction|message|rule|command|context)s?",
            re.IGNORECASE,
        ),
    ),
    (
        "system_prompt_exfil",
        re.compile(
            r"(?:reveal|show|print|repeat|output|display|reproduce|tell\s+me)\s+"
            r"(?:me\s+)?(?:your|the)\s+(?:full\s+|original\s+|system\s+|initial\s+)*"
            r"(?:system\s+)?(?:prompt|instruction)s?",
            re.IGNORECASE,
        ),
    ),
    (
        "instructions_probe",
        re.compile(
            r"what\s+(?:are|were)\s+your\s+(?:original\s+|initial\s+|system\s+)*" r"instructions",
            re.IGNORECASE,
        ),
    ),
    (
        # High-confidence jailbreak *mode* markers only. Bare "developer mode"
        # (Chrome/Android) and bare "jailbreak" (iPhone how-tos) are dropped —
        # too common in legitimate content (audit 2026-07-03); role-switch into
        # developer/dan is still caught by ``role_override`` below.
        "jailbreak_marker",
        re.compile(r"\b(?:DAN\s+mode|jailbreak\s+mode)\b", re.IGNORECASE),
    ),
    (
        "role_override",
        re.compile(
            r"you\s+are\s+now\s+(?:in\s+)?(?:a\s+|an\s+|the\s+)?"
            r"(?:developer|dan|admin|root|unrestricted|god)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "chat_template_delimiter",
        re.compile(r"<\|im_(?:start|end)\|>|\[/?INST\]|<<SYS>>|<</SYS>>", re.IGNORECASE),
    ),
    (
        # Fenced ``` ```system ``` code block only. The markdown-heading branch
        # (## Instructions / ### System requirements) was dropped — ubiquitous in
        # legitimate docs/tutorials (audit 2026-07-03).
        "fenced_system_block",
        re.compile(r"(?:```|~~~)\s*system\b", re.IGNORECASE),
    ),
)


class HeuristicInjectionScanner:
    """Deterministic injection scanner (implements ``ports.InjectionScanner``)."""

    def scan(self, text: str) -> InjectionScanResult:
        findings: list[InjectionFinding] = []
        spans: list[tuple[int, int]] = []
        for pattern_id, rx in _PATTERNS:
            for m in rx.finditer(text):
                if m.end() == m.start():
                    continue
                findings.append(InjectionFinding(pattern_id, m.start(), m.end()))
                spans.append((m.start(), m.end()))

        if not spans:
            return InjectionScanResult(neutralized_text=text, findings=())

        findings.sort(key=lambda f: (f.start, f.end))
        return InjectionScanResult(
            neutralized_text=_neutralize(text, spans),
            findings=tuple(findings),
        )


def _neutralize(text: str, spans: list[tuple[int, int]]) -> str:
    """Replace each (merged) flagged span with the marker (B1)."""
    spans.sort()
    merged: list[tuple[int, int]] = []
    cur_start, cur_end = spans[0]
    for start, end in spans[1:]:
        if start <= cur_end:
            cur_end = max(cur_end, end)
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end
    merged.append((cur_start, cur_end))

    out: list[str] = []
    prev = 0
    for start, end in merged:
        out.append(text[prev:start])
        out.append(_MARKER)
        prev = end
    out.append(text[prev:])
    return "".join(out)


default_injection_scanner: InjectionScanner = HeuristicInjectionScanner()


def scan_injection(text: str) -> InjectionScanResult:
    """Scan + B1-neutralize ``text`` with the default heuristic scanner."""
    return default_injection_scanner.scan(text)
