"""audit — Append-only audit-log bounded context.

Per ADR-014 (Wave 0 amendment 2026-05-19) the audit context owns:
  * audit.audit_log — partitioned by RANGE (ts), one partition per month
  * audit.deny_update_delete() trigger function enforcing append-only invariant
  * Retention: 3 years (purge by partition DROP, not DELETE)

The public emit_audit_event(...) coroutine accepts an optional
AsyncSession (plus workspace_id / cell_id) so callers in iam / multitenancy
/ llm_gateway that already own a transactional session can INSERT into
audit.audit_log inside the same TX as their domain write.
"""
