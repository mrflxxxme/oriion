"""tests/runtime/ — unit tests for src/runtime/ bounded context.

Phase 00.6 Commit 11 (AC13 strict honor). Per-module coverage gate ≥85%
wired into ci-backend.yml в Commit 12.

Test files:
* test_budget_guard.py — check_budget cap enforcement + reserve + refund_unused
* test_sse_events.py — TaskStreamEvent Pydantic shape
* test_sse_publisher.py — InProcessSSEPublisher publish/subscribe + drain-replay
* test_orchestrator.py — orchestrator state machine + task.failed emit
"""
