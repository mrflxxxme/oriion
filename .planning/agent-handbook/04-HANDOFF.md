# 04-HANDOFF — Передача context между сессиями / агентами

> **Цель:** работа не теряется при switch'е agent / session / phase. Каждое завершение задачи оставляет следы для следующего agent'а.

## Single-file rolling handoff (canonical pattern, 2026-05-14 reorg)

Проект использует **один rolling-файл `.planning/HANDOFF.md`**, перезаписываемый каждой завершённой сессией как часть Exit ritual (см. [`05-PR-WORKFLOW.md`](./05-PR-WORKFLOW.md)). История доступна через `git log HANDOFF.md`. Append-only журнал сессий — отдельно в [`../JOURNAL.md`](../JOURNAL.md).

Преимущества rolling-pattern перед старой `.planning/handoffs/YYYY-MM-DD-<slug>.md` директорией: один и тот же файл всегда читается next-агентом (no guessing what's latest), git-history даёт авто-archive, no orphan files.

## Когда нужен handoff

### Полный handoff (формальный) — обязательный Exit ritual

- Завершил phase
- Завершил sprint / day's work
- Передаёшь работу другому agent'у (или человеку)
- Эскалируешь и блокирован > 1 час

### Lightweight handoff (commit + STATUS update)

- Завершил task внутри phase
- Завершил sub-task / 1 PR
- Сохраняешь partial progress (mid-day)

## Полный handoff template

Перезаписывай `.planning/HANDOFF.md` (single rolling file) этим шаблоном:

```markdown
# Handoff: <тема> · YYYY-MM-DD · <agent_name>

## Status
- Phase: Wave N Phase N.M (<slug>)
- Completion: <N>% (по acceptance-criteria из phase-spec)
- Branch: feature/<phase-id>-<slug>
- PR(s): #123 (merged), #124 (review)

## Done
- ✅ <Concrete task 1 done>
- ✅ <Concrete task 2 done>
- ✅ Tests for X passing (coverage 87%)

## In Progress
- 🔄 <Task currently in progress>
  - Files touched: backend/src/llm_gateway/router.py
  - Status: implementation done, tests missing
  - Next step: write integration test for fallback

## Blocked
- 🛑 <Blocker name>
  - Reason: waiting for OQ-XX resolution / waiting for subagent / encountered bug
  - Workaround: <если есть>
  - Escalation: <link to message / issue>

## Next steps (in priority order)
1. <Concrete action with file refs>
2. <Concrete action>
3. <Concrete action>

## Context for next agent
- **Read first:** <ordered list of files, ~5KB total>
- **Already loaded (don't re-read):** <files в текущем session memory>
- **DON'T touch:** <files outside scope, чтобы избежать accidental changes>

## Decisions made (без ADR)
- Chose `httpx.AsyncClient` over `aiohttp` — reason: native async + better типизация
- Used `pgvector_ivfflat` index — reason: fast insert, acceptable recall на <1M vectors

## Decisions deferred (waiting answer)
- <Decision> — waiting on <user / Tech Lead>
  - Link: <escalation message>

## Files modified (по bounded contexts)
- `backend/src/llm_gateway/`: router.py, providers/deepseek.py, billing.py
- `backend/tests/llm_gateway/`: test_router.py, test_deepseek.py
- `.planning/decisions/`: ADR-018 updated (added benchmarks section)

## Risks / TBD-tokens used
- `TBD_DEEPSEEK_API_KEY` — in `.env.example`, replace before prod
- `TBD_YANDEX_GPT_CATALOG_ID` — in alembic migration 0023

## Performance / metrics
- LLM router p95 latency: 45ms (no calls)
- Test runtime: 12 секунд
- Coverage: 87% (target 70%)

## Recommended subagents for next steps
- `tester` — для написания missing integration tests
- `code-reviewer` — для review перед merge
```

## Lightweight handoff (между tasks внутри phase)

Просто:

1. **Commit с descriptive message** (conventional commit):
   ```
   feat(llm_gateway): add DeepSeek provider with fallback
   
   - Add DeepSeek client wrapper (OpenAI-compatible base_url)
   - Implement fallback chain: DeepSeek → YandexGPT → GigaChat
   - Unit tests for happy-path + 503 fallback
   - Coverage: 85% (target met)
   
   Refs: phase 00.4, ADR-002, ADR-018
   TBD: TBD_DEEPSEEK_API_KEY in .env.example
   ```

2. **Update STATUS.md** активной phase (если phase progress изменился).

3. **TodoWrite update** — mark current item done, next в `in_progress`.

## Handoff артефакты

### Куда сохранять

| Где | Что |
|---|---|
| Commit message | Что сделано, кому ссылки, TBD-tokens |
| `.planning/HANDOFF.md` | Полный handoff (session-end, single rolling file) |
| `.planning/STATUS.md` | Текущее состояние проекта (rolling) |
| `.planning/JOURNAL.md` | Append-only журнал сессий (post-merge entry per session) |
| `OPEN-QUESTIONS.md` | Если открыт новый OQ |
| `risks/REGISTER.md` | Если новый risk discovered |
| ADR (new или revised) | Если архитектурное решение |
| PR description | Что в PR (Tier-based template) |
| TodoWrite | Live progress в session |

### Что НЕ нужно в handoff

- Полный context файлов, которые next agent сам прочитает (только pointers)
- Tribal knowledge — переносить в _meta/conventions.md
- Reasoning по каждой строке кода — это в commit + comment

## Resume protocol (when starting a session)

Если ты — NEW session continuing existing work:

1. Read [`../README.md`](../README.md) (3KB) — ориентация
2. Read [`../STATUS.md`](../STATUS.md) (4KB) — где мы
3. Read [`../HANDOFF.md`](../HANDOFF.md) — последний snapshot (single rolling file)
4. Read **active** phase-spec из `roadmap/`
5. Continue от «Next steps» в HANDOFF.md

**Не пере-делай работу, которую предыдущий agent уже сделал.** Доверяй handoff, проверяй только pillar changes.

## Anti-patterns

### ❌ Handoff с одним словом «продолжай»

Don't:
```
Did some work. Continue.
```

Next agent must reverse-engineer что было сделано → потерян час.

### ❌ Handoff без блокеров explicit

Don't: «всё хорошо, продолжаем» когда на самом деле есть waiting on user.

Do: explicit Blocker section.

### ❌ Handoff в commit-message only

Long handoff в commit message убийствен для readability. Use `.planning/HANDOFF.md` (single rolling file).

### ❌ Handoff без файлов

Don't: «refactored auth».

Do: «refactored backend/src/iam/jwt.py + tests; touched files X, Y, Z».

## Memory & cache strategy

Если у тебя есть memory tools (e.g. `claude-mem`, `notepad`):

- **Session-scoped memory:** current TodoWrite items, file-read cache
- **Project-scoped memory:** ADR-decisions, conventions, ongoing patterns
- **Cross-session memory:** rolling `.planning/HANDOFF.md` + append-only `.planning/JOURNAL.md` (git-history-backed)

При завершении session — **persist** project-scoped insights в файлы (ADR, _meta/, conventions). Session-scoped — это самой sessии.

## Handoff между AI и человеком

Когда ты заканчиваешь и передаёшь Tech Lead'у на review:

```markdown
# PR Review Ready: <PR title>

## Что сделано
<short summary>

## Где смотреть
- PR: #XYZ
- Phase: <slug>
- Touched files (логически грunpированные):
  - Backend LLM gateway: router.py + providers/
  - Tests: test_router.py + test_deepseek.py

## Знай перед review
- Использовал TBD_DEEPSEEK_API_KEY — заменить перед prod
- Откложил X на следующий PR — reason: scope-creep prevention (R-12)

## Что специально проверить
- [ ] Fallback chain logic (DeepSeek → Yandex → GigaChat)
- [ ] Error handling for 503 cases
- [ ] Pricing/credit-charging integration

## CI status
- Tests passing: ✅
- Lint clean: ✅
- Coverage 87%: ✅
- Security scan: ✅
```

## Cheat sheet

| Сценарий | Action |
|---|---|
| Завершил task внутри phase | Commit + TodoWrite update + (опц.) STATUS update |
| Завершил phase | Commit + HANDOFF.md refresh + JOURNAL.md +1 + STATUS update + phase-spec ✅ Complete |
| Передаёшь другому agent | HANDOFF.md refresh с явным «Read first» list |
| Передаёшь Tech Lead на review | PR description с «Что специально проверить» section |
| Эскалируешь user'у | ESCALATION block (см. 03-ESCALATION.md) + STATUS update |
| Заблокирован > 1 час | HANDOFF.md refresh + escalation + остановка работы |
