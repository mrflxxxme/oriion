"""runtime — orchestrator + SSE publisher + budget guard.

Phase 00.5b Commit 6. Drives Pydantic-AI Agent.run() with task-step
persistence, cost rollup, and SSE event emission. Wave 0 uses an
in-process publisher; Wave 1 swaps to Redis pub/sub without call-site
changes (see sse_publisher.SSEPublisher Protocol).
"""
