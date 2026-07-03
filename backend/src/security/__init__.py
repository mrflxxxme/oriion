"""Security guardrails bounded context (Phase 01.6, ADR-039).

Deterministic layer-B guardrails with detector PORTS (upgrade seam B->A ML):

* ``detectors.pii`` — RU-PDN DLP (INN/SNILS checksum, passport, phone, email).
* ``detectors.injection`` — heuristic prompt-injection scanner + B1 neutralize.
* ``capability`` — static tool-risk registry + ``requires_approval`` seam
  (no runtime gate in 01.6 — activates in 01.9).
* ``services.dlp`` — A3 output hard-block (audit row via the ``AuditSink`` port
  + raise ``DlpViolation``).

No tables / migrations: detectors are stateless and the DLP block writes the
existing ``audit.audit_log`` (via the runtime ``AuditSink`` adapter). SECURITY
invariant: findings carry a ``(category, span)`` only — never the raw matched
value in any log, audit payload, SSE frame, or exception message.
"""
