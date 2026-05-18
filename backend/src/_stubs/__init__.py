"""_stubs — cross-context stubs replaced in Phase 00.2.5 integration.

Owner of each stub matches the worktree producing it (see
.planning/_session-context/2026-05-17-architect-pr-3-way-parallel.md
"Stub interfaces" section):

    multitenancy.provision_initial_workspace  — owned by 00.2 worktree
    audit.emit_audit_event                    — owned by 00.2 + 00.4 worktrees

Integration phase 00.2.5 deletes this directory and rewires imports to
the real impls landed by Phase 00.3.
"""
