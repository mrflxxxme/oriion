"""multitenancy — Workspaces & Cells bounded context.

Per ADR-024 / contracts/multitenancy/. Owns:
  * workspaces      (billing / legal tenant — was `organizations` pre-2026-05-19)
  * cells           (workspace boundary = AI team per ADR-009)
  * cell_members    (user ↔ cell membership with system role)

Public service contract:
  * provision_initial_workspace(session, user_id, email_localpart)
    → WorkspaceProvisionResult  — called by iam.auth_service.register()
  * CellService.provision_cell(...) — per-cell schema + audit + owner-member.

Per-cell schemas (cell_<uuid>.memory_entries with pgvector HNSW index) are
materialized eagerly via the SQL function
``multitenancy.provision_cell_schema(uuid)`` (ADR-009 amendment 2026-05-19).
"""
