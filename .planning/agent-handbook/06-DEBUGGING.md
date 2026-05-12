# 06-DEBUGGING — Triage protocol для AI-агента

> **Цель:** при failure (тест не проходит, build broken, runtime error) — структурированно diagnose + fix, не паника. Лучше потратить 10 мин на правильную диагностику, чем 1 час на trial-and-error.

## Triage decision tree

```
Что-то не работает.
│
├─ Это failure CI / тест / build / lint?
│  │
│  ├─ CI lint fail
│  │  └─ Запусти локально: `ruff check && mypy --strict && eslint`
│  │     └─ Fix локально → push
│  │
│  ├─ Тест fail
│  │  ├─ Регрессия (раньше работало)? → bisect / blame последний change
│  │  ├─ Новый тест fail? → fix imple+test pair
│  │  └─ Flaky? → retry, если повторяется — fix flakiness
│  │
│  ├─ Build fail
│  │  └─ Dependency issue? Type issue? Config? → читай stack-trace
│  │
│  └─ Security scan fail
│     └─ Real vuln? → fix. False-positive? → suppress с ADR-обоснованием.
│
├─ Это runtime error в dev?
│  │
│  ├─ Stack-trace ясный → fix root cause
│  ├─ Не ясный → enable debug logging, reproduce
│  ├─ Race condition → analyze concurrency
│  └─ Memory leak → profile с tracemalloc / dotmemory
│
├─ Это runtime error в prod?
│  └─ Sentry / Grafana → читай context → если critical → ESCALATE
│
└─ Это "странное поведение" (нет error, но не как ожидается)?
   ├─ Add logging / breakpoints
   ├─ Repro в isolated test
   └─ Если непонятно → ESCALATE с reproduction steps
```

## Common failure patterns

### LLM-related

| Symptom | Likely cause | Fix |
|---|---|---|
| `RateLimitExceeded` на DeepSeek | API rate-limit (TPM/RPM) | Backoff + retry with `tenacity`; check rate-limit headers |
| `ConnectError` к provider | Provider down или network issue | Failover на следующий provider в chain (см. ADR-002) |
| Empty response от LLM | Bad prompt / context-overflow | Reduce prompt size; check token-count |
| Hallucinated tool-call | Бад structured output | Add JSON-mode / use Pydantic-AI structured output |
| Slow LLM response (>30s) | Provider degraded или сложный prompt | Cache check; provider-status check; simplify prompt |

### Database

| Symptom | Likely cause | Fix |
|---|---|---|
| `RowLevelSecurity violation` | Missing `SET LOCAL app.current_cell_id` | Set RLS context в session middleware |
| Slow query (p95 >500ms) | Missing index, sequential scan | `EXPLAIN ANALYZE` → add index |
| Connection pool exhausted | Pool size too small / leak | Increase pool, fix connection lifecycle |
| Migration timeout | Big table ALTER без CONCURRENTLY | Use `squawk` to check migration safety |

### Auth

| Symptom | Likely cause | Fix |
|---|---|---|
| `JWT expired` после refresh | Race condition или timezone bug | Check refresh-token rotation logic |
| `Invalid signature` JWT | Secret rotated, old tokens still active | Wait TTL or force refresh; check secret-rotation |
| User can't login после register | Email verification not done | Show clear UX hint |
| 2FA bypass | TOTP-secret leak | Investigate immediately; force 2FA reset |

### Frontend

| Symptom | Likely cause | Fix |
|---|---|---|
| Vite HMR broken | File-watch limit, OS specific | Increase `fs.inotify.max_user_watches` на Linux |
| Type error mismatch BE↔FE | OpenAPI codegen out of sync | Regenerate `orval`/`openapi-typescript` |
| Canvas frame drop в Pixel | Too many sprites или non-batched draws | Profile с Chrome DevTools Performance |
| Yjs sync issues | y-websocket disconnect | Check WebSocket connection, reconnect logic |

### Pyodide

| Symptom | Likely cause | Fix |
|---|---|---|
| Pyodide load timeout >30s | Slow CDN или большой Pyodide-bundle | Self-host Pyodide на нашем CDN |
| `ModuleNotFoundError` | Package not in Pyodide micropip | Check Pyodide-supported packages list |
| `MemoryError` в browser | Heavy dataset для Pyodide | Pre-aggregate на backend перед передачей |
| Слабый device | Slow analytical task | UX hint «desktop recommended» |

### MCP

| Symptom | Likely cause | Fix |
|---|---|---|
| MCP-server timeout | Network / wrong endpoint | Health-check MCP, retry |
| Tool-call failed silently | Schema mismatch | Pydantic validation logs |
| Permission denied (DLP block) | Output contains PDN | Adjust prompt / use approval-mode |

## Tools для debugging

### Backend (Python)

```bash
# Logs (structured, JSON)
docker compose logs -f backend | jq

# Database queries
docker compose exec postgres psql -U teamly -c "EXPLAIN ANALYZE SELECT ..."

# Redis state
docker compose exec redis redis-cli

# Profile slow endpoint
python -m cProfile -o profile.out backend/main.py

# Memory profile
python -m tracemalloc

# OpenTelemetry traces (Wave 0.6+)
# Read in Tempo via Grafana UI
```

### Frontend (Vite + React)

```bash
# Dev server with verbose
pnpm dev --debug

# Production build analyze
pnpm build && pnpm preview
vite-bundle-visualizer

# React DevTools (browser extension)
# TanStack Query DevTools (in-app)

# Network capture
# Chrome DevTools → Network → Preserve log
```

### Pyodide

```javascript
// Console in browser worker
// Открыть Web Worker DevTools → Console

// Pyodide internal state
pyodide.runPython("import sys; print(sys.path)")
```

### Database introspection

```sql
-- Active queries
SELECT pid, query, state, query_start FROM pg_stat_activity WHERE state != 'idle';

-- Slow queries (с pg_stat_statements)
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC LIMIT 10;

-- RLS check
SHOW row_security;
SELECT current_setting('app.current_cell_id');
```

## Reproduction protocol

При нечётком bug'е:

1. **Capture steps:** что именно делал user / system перед error
2. **Capture state:** DB-state, env-vars, browser state
3. **Capture output:** stack-trace, logs, screenshots
4. **Isolate:** написать минимальный test, который reproducible reproduces bug
5. **Fix:** root cause не симптом
6. **Regression test:** добавить test чтобы не повторилось

## Failed task escalation

Если debugging > 1 час без прогресса:

1. **Stop digging deeper**
2. Сохрани **handoff** с: что пытался, что нашёл, где застрял ([`04-HANDOFF.md`](./04-HANDOFF.md))
3. **Escalate** ([`03-ESCALATION.md`](./03-ESCALATION.md)) — другому agent (свежий perspective) или Tech Lead'у

## Production debugging

Wave 0-3 (no real prod): debug в staging.

Wave 4+ (real prod):
- **Никогда не отлаживай live на prod** — read-only access only
- Reproducible в staging → fix → deploy hotfix
- Если incident → incident response runbook ([`docs/runbooks/incident-*.md`](../../docs/runbooks/))

## Common antipatterns

### ❌ Random try-and-pray fixes
Меняешь код наугад, надеешься что заработает. **Сначала diagnose, потом fix.**

### ❌ Игнорирование первого error в stack-trace
Часто FIRST error — root cause, subsequent — следствия. Не скипай первый.

### ❌ Disabling tests чтобы CI прошёл
Никогда. Тест fail = real signal. Если test broken — fix test, не skip.

### ❌ Comments вместо тестов после fix
`# fix bug XYZ` в коде. Должно быть **regression test** для повтора в CI.

### ❌ Loud logging без structured fields
`print("here")` в production-code. Используй structlog с structured fields для filter / query.

## Cheat sheet

| Симптом | Первый шаг |
|---|---|
| Test failing | `pytest -x -v` (stop on first fail, verbose) |
| Build failing | Read FIRST error in stack-trace |
| LLM 503 | Check provider health + fallback chain |
| DB slow | `EXPLAIN ANALYZE` |
| Auth bug | Check JWT TTL + Redis blacklist |
| Frontend rerender storm | TanStack Query DevTools + React Profiler |
| Pyodide hang | Browser Web Worker DevTools |
| RLS violation | Check `current_setting('app.current_cell_id')` |
| Memory leak | tracemalloc / heap-snapshot |
| Random flaky test | Add seed, isolate test |

## When to ask for human help

| Ситуация | Action |
|---|---|
| Spent >1 hour без прогресса | Handoff + escalation |
| Trying to disable security check | STOP, escalation 100% |
| Modifying ADR без discussion | STOP, escalation |
| Production-affecting issue | STOP, escalation (Tech Lead) |
| Bug в third-party library | Search issue tracker, file bug, workaround |
