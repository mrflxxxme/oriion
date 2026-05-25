"""tests/tasks/ — unit tests for src/tasks/ bounded context.

Phase 00.6 Commit 10 (AC13 strict honor). Per-module coverage gate ≥85%
wired into ci-backend.yml в Commit 12.

Test files:
* test_schemas.py — Pydantic schema validation (TaskCreateRequest,
  TaskOut, TaskStepOut, TaskArtifactOut)
* test_events.py — CloudEvents emit_* shape assertions
* test_cost_rollup_service.py — atomic rollup walker (parent + ancestors)
* test_task_service.py — TaskService CRUD + delegation depth + TaskNotFound
* test_cancel_cascade.py — RELOCATED from tests/agents/ (Phase 00.5b
  Commit 7); BFS descendant collection + cancel-event emission
* test_routers.py — FastAPI router smoke (POST/GET/cancel + SSE stream)
"""
