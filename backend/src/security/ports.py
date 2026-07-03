"""Ports + value types for the security guardrails context (ADR-039).

The service layer + runtime seams depend on these Protocols only; the Wave-1
deterministic adapters live in ``detectors/``. Swapping in an ML detector
(Prompt Guard / bge, layer A) later is a new Protocol impl with zero call-site
change.

SECURITY: every finding is a ``(category, span)`` — the raw matched substring is
NEVER carried on a finding, so it cannot leak through a log, audit payload, SSE
frame, or exception. Callers that need to act (neutralize) use the span into the
*caller's own* text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol
from uuid import UUID


class PiiCategory(str, Enum):
    """RU-PDN categories the Wave-1 deterministic DLP detects."""

    INN = "inn"
    SNILS = "snils"
    PASSPORT = "passport"
    PHONE = "phone"
    EMAIL = "email"


class RiskLevel(str, Enum):
    """Capability risk tier for an agent tool (ADR-039 §5)."""

    READ_ONLY = "read_only"  # web_search / read_url — external read, no side-effect
    INTERNAL = "internal"  # delegate_task — in-team fan-out, no outward action
    DANGEROUS = "dangerous"  # outward action (send_email/…); gate activates 01.9


@dataclass(frozen=True, slots=True)
class PiiFinding:
    """One DLP hit — category + half-open span into the scanned text (no value)."""

    category: PiiCategory
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class DlpScanResult:
    """Outcome of a DLP scan."""

    findings: tuple[PiiFinding, ...] = ()

    @property
    def has_pii(self) -> bool:
        return bool(self.findings)

    @property
    def categories(self) -> tuple[str, ...]:
        """Sorted unique category labels — safe to log / audit (no raw values)."""
        return tuple(sorted({f.category.value for f in self.findings}))


@dataclass(frozen=True, slots=True)
class InjectionFinding:
    """One injection hit — the matched heuristic id + span (no value)."""

    pattern_id: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class InjectionScanResult:
    """Outcome of an injection scan (B1): findings + neutralized text."""

    neutralized_text: str
    findings: tuple[InjectionFinding, ...] = field(default=())

    @property
    def has_injection(self) -> bool:
        return bool(self.findings)


class PiiDetector(Protocol):
    """Detect RU-PDN in text. Layer-B impl = regex+checksum; layer-A = ML."""

    def scan(self, text: str) -> DlpScanResult: ...


class InjectionScanner(Protocol):
    """Detect + B1-neutralize prompt-injection in external content."""

    def scan(self, text: str) -> InjectionScanResult: ...


class AuditSink(Protocol):
    """Sink for a DLP hard-block audit row (real impl wraps ``emit_audit_event``).

    SECURITY: the impl MUST NOT receive or persist raw PII — only category
    labels + a count.
    """

    async def record_dlp_block(
        self,
        *,
        task_id: UUID,
        cell_id: UUID | None,
        workspace_id: UUID | None,
        categories: tuple[str, ...],
        finding_count: int,
    ) -> None: ...
