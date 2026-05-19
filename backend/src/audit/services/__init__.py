"""audit.services — orchestration.

Public surface:
  * AuditService — class wrapping the repository for DI use
  * emit_audit_event(...) — module-level coroutine. Optional
    ``session`` / ``workspace_id`` / ``cell_id`` kwargs let callers in
    iam / multitenancy / llm_gateway that already own a transactional
    session INSERT into audit.audit_log inside the same TX as their
    domain write.
"""
