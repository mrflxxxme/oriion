"""audit.services — orchestration.

Public surface:
  * AuditService — class wrapping the repository for DI use
  * emit_audit_event(...) — module-level coroutine, contract-locked to
    src/_stubs/audit.py::emit_audit_event (Phase 00.2.5 swap is a pure
    import-replacement). Strict superset signature: adds optional
    ``session`` / ``workspace_id`` / ``cell_id`` kwargs that callers in
    00.3 / 00.4 already-in-tx code paths use.
"""
