# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-05-15
- Session: `frosty-raman-c9aaee` (Wave 0 roadmap reorganization + OQ-17/18 out-of-scope closure + consistency cleanup)
- Agent: @claude-opus

## Project status

- **Wave:** Pre-Wave-0 (preparation complete — ready to start)
- **Active phase:** none (Phase 00.1 не стартовал — следующая сессия)
- **Next phase:** [`roadmap/wave-0-foundation/phases/00.1-repo-cicd.md`](./roadmap/wave-0-foundation/phases/00.1-repo-cicd.md) (Owner: DevOps; Duration: 3 дня)

## Active blockers

**None within project scope.** Phase 00.1 ready to start.

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление | Founder + юрист | Required до Phase 00.2 (НЕ блокирует 00.1) |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку, нужно до открытия ЮKassa (Wave 1) |

> **Closed `N/A` per [P-INIT-5](./decisions/ADR-028-policies-registry.md):** OQ-13, OQ-14, OQ-15, OQ-16 (hiring; solo + 11 AI model).
> **Closed `out-of-scope` per Session-2026-05-15:** OQ-17 (funding), OQ-18 (burn-budget) — founder-personal financial decisions не tracked в project docs; AI dev cost caps живут в `.claude/agents/_shared/cost-budget.yaml`.

Полный реестр — [`OPEN-QUESTIONS.md`](./OPEN-QUESTIONS.md).

## What just happened (this session — 3 commits)

### Commit `760991f` — Roadmap reorg
**11 strategic decisions через grill-me interview** трансформировали roadmap:

1. **Wave 0 anchor changed:** WB-Селлер vertical → horizontal `productivity-core` team-preset («Твои личные ассистенты»). Состав: Coordinator + Researcher + Writer + Analyst.
2. **Demo Wave 0:** «Market & content brief для нового продукта» — 3 артефакта (brief.md ≥1500w + competitive-matrix.md ≥5×4 + content-plan.md 10 posts), latency ≤120s, cost ≤30¢.
3. **Vertical wave-distribution re-ordered:** WB-Селлер W0→W2 (теперь vertical-anchor для public beta); ИП-Бух + СМБ-Sales W2→W3.
4. **Wave 1 ships:** horizontal + 2 vertical (Marketing-agency + Telegram-крейтор) с первой инстанциацией Master-Agent layer; WB defer.
5. **Dual messaging positioning:** universal entry («Твои личные ассистенты») + vertical depth (Master-Agent layer).
6. **NEW [ADR-029](./decisions/ADR-029-master-agent-vertical-templates.md) — Master-Agent layer:** двухслойная оркестрация для vertical-templates — Master (CEO domain-knowledge keeper) → Coordinator (operational COO) → specialists. Wave 1+ only; horizontal остаётся однослойным.
7. **NEW [ADR-030](./decisions/ADR-030-telegram-business-api.md) — Telegram Business API:** telegram-mcp v0.2 в Wave 1 (Read + post + Business API + consent flow + 152-ФЗ disclosure); Mini App defer W2; Stars billing defer W4+.
8. **Wave 2 timebox:** 8 → 9 нед (+WB + Mini App + Master-Agent first instances + 3 hand-drawn vertical-героев).
9. **Wave 3 timebox:** 8 → 10 нед (+ИП-Бух + СМБ-Sales verticals + Master-Agents).
10. **Downstream dates:** Wave 4 complete → 2027-02-22 (+3 нед vs prior).
11. **Role-prompts contract pattern:** [`contracts/role-prompts/`](./contracts/role-prompts/) — 9-секционная глубокая структура (~2500–3200 слов / роль), YAML-frontmatter; 4 horizontal roles materialized как first-draft. Hardening pass — в Phase 01.1 retro.

### Commit `4bea037` — Consistency fixes
Закрытие 9 audit findings:
- `gates/wave-0-to-1.md` hard threshold под productivity-core demo
- Phase 00.6 AC2 fix
- `JOURNAL.md` Session-2026-05-15 entry
- `verticals/README.md` wave-distribution table updated
- `verticals/wb-seller/README.md` deferred-status frontmatter (preserves W2 prep-work)
- `PLACEHOLDERS.md` wave-targets adjusted
- `_meta/glossary.md` +3 терминов (Master-Agent, horizontal preset, productivity-core)
- `risks/REGISTER.md` +3 риска (R-32, R-33, R-34) + strategic-bets revised
- ADR-029 ↔ ADR-030 mutual cross-refs

### Commit `8902ed9` — OQ-17/18 out-of-scope
Founder directive: financial decisions outside project docs.
- OQ-17 + OQ-18 closed `out-of-scope`
- PLACEHOLDERS.md финансовая секция scrubbed
- STATUS.md blockers updated
- risks/REGISTER.md R-12 runway-language убран
- ADR-028 P-AUDIT-1 уточнён

## Next agent — read first

Bootstrap (4 файла):
1. [`README.md`](./README.md) — что за проект
2. [`STATUS.md`](./STATUS.md) — текущее состояние, no blockers
3. этот HANDOFF.md
4. [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md) — workflow protocol

После bootstrap → Phase 00.1 spec.

## Next steps (priority order)

### Founder action — pre-launch

1. **Push branch + open PR** (or merge directly если confident):
   - `git push -u origin claude/frosty-raman-c9aaee`
   - `gh pr create` или merge через GitHub UI
   - Review-gate: 27 файлов + 4 deep role-prompts + 2 новых ADR

### AI-agent action — после merge в main

2. **Start Phase 00.1 (Repo & CI/CD)** — DevOps owner, 3 дня:
   - Owner per ADR-023: `devops-implementer` (non-persistent spawned role) с support от `architect` + `planner` + `backend-implementer` для skeleton
   - Phase spec: [`roadmap/wave-0-foundation/phases/00.1-repo-cicd.md`](./roadmap/wave-0-foundation/phases/00.1-repo-cicd.md)
   - Acceptance: cold-start dev env ≤10 мин, CI ≤8 мин, coverage ≥70%
   - Deliverables: monorepo (backend/+frontend/+infra/+docs/+scripts/) + docker-compose + 4 CI workflows + pre-commit + Makefile + .env.example + GitLab mirror setup

3. **Parallel-ready phases после 00.1:**
   - 00.2 (Custom JWT auth) — depends 00.1, OQ-04 (РКН required)
   - 00.3 (DB + RLS + Cell schema) — depends 00.1
   - 00.4 (LLM gateway + MCP) — depends 00.1

4. **Sequential after 00.3 + 00.4:**
   - 00.5 (Pydantic-AI + `productivity-core` team) — uses `contracts/role-prompts/{coordinator,researcher,writer,analyst}.md` first-draft
   - 00.6 (Deploy + observability) ∥ 00.7 (Frontend skeleton)

5. **Wave 0 → Wave 1 gate:** Internal demo «Market & content brief» passes per [`gates/wave-0-to-1.md`](./gates/wave-0-to-1.md) revised hard threshold.

## Ready-to-build checklist (Session-2026-05-15 audit)

- ✅ **Bootstrap-4 ready:** README + STATUS + HANDOFF (rewritten) + 00-START-HERE — all current
- ✅ **Phase 00.1 spec executable:** 13+ acceptance criteria + full file-tree + inline Makefile/CI/scripts/tests
- ✅ **No project-scope blockers:** OQ-17/18 closed, Phase 00.1 not gated by OQ-04
- ✅ **11 .claude/agents/ runtime ready:** architect, planner, memory-curator, designer, frontend-impl, backend-impl, reviewer-{frontend,backend,security}, verifier, evaluator
- ✅ **10 contracts/ subdomains with README:** agents, artifacts, billing, iam, llm-gateway, mcp, memory, multitenancy, rbac, tasks
- ✅ **NEW contracts/role-prompts/:** coordinator + researcher + writer + analyst (4 deep prompts, ~11K слов суммарно)
- ✅ **30 ADRs + ADR-template:** all linked from decisions/README.md
- ✅ **34 risks + strategic bets:** REGISTER updated с R-32/R-33/R-34
- ✅ **Gates ready:** wave-0-to-1 hard threshold обновлён под productivity-core
- ✅ **UI assets:** component-inventory, design-tokens, UI-DESIGN-PLAYBOOK ready для Phase 00.7
- ✅ **AI cost-budget:** `.claude/agents/_shared/cost-budget.yaml` — dev_team $500/mo kill-switch + Sonnet fallback rules

## Files modified this session

- **NEW (5):** ADR-029, ADR-030, contracts/role-prompts/coordinator.md + researcher.md + writer.md + analyst.md
- **MODIFIED:** STATUS, PROJECT, README (.planning), JOURNAL, HANDOFF (this file), OPEN-QUESTIONS, PLACEHOLDERS, _meta/glossary, decisions/README, ADR-013/-017/-022/-028, roadmap/README, wave-0/README + PHASES, wave-1/README + PHASES, wave-2/README, wave-3/README, gates/wave-0-to-1, phase 00.6 AC2, risks/REGISTER, verticals/README, verticals/wb-seller/README
- **RENAMED:** phase 00.5 spec (was `00.5-pydantic-ai-wb-team.md` → `00.5-pydantic-ai-productivity-team.md`, fully rewritten)
- **3 commits:** 760991f (reorg, 22 files) + 4bea037 (consistency, 10 files) + 8902ed9 (OQ scope, 6 files)

## Known caveats

- 3 worktree-директории (peaceful-hermann, optimistic-raman, zen-murdock) сняты с git worktree list ещё в Session-2026-05-14, но папки на диске остались (Windows file-lock от watcher-процессов). Не git-state issue; можно удалить вручную позже.
- Role-prompts (`contracts/role-prompts/`) — first-draft quality. Hardening pass запланирован в Phase 01.1 retro per AC14 phase 00.5 spec. NOT production-final.
- `verticals/wb-seller/` сохранён as-is (deferred to Wave 2). Existing prompts/coordinator.md, prompts/listing_writer.md, prompts/researcher.md, 30 golden-dataset tasks valid как Wave 2 prep, но архитектурно не align'нуты с ADR-029 (Master-Agent). Alignment scheduled в Wave 2 Phase 02.X.

## Build / test state

- Этот repo — документационный. Build/test не запускаются до Phase 00.1.
- CI gates по коду активируются с Phase 00.1.

## Exit ritual completed

- [x] JOURNAL.md updated (Session-2026-05-15 entry added in commit 4bea037)
- [x] HANDOFF.md rewritten (this file)
- [x] STATUS.md reflects current state
- [x] OPEN-QUESTIONS.md reflects closed blockers
- [ ] PR opened — founder action (next step)
