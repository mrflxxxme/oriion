"""rbac — Role-Based Access Control (system level) bounded context.

Per ADR-024 / contracts/rbac/. Owns:
  * system_roles      (built-in role catalogue — owner/admin/editor/...)
  * permissions       (granular `<resource>.<action>` capability tokens)
  * role_permissions  (many-to-many bridge)
  * role_assignments  (user ↔ scope_type ↔ scope_id ↔ role binding)

Crucial disambiguation: `system_roles` here are for PEOPLE doing system
operations. `agent_archetypes` (in the `agents` context) are AI personas
declared by a vertical template. The two catalogues are unrelated.
"""
