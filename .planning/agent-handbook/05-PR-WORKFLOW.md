# 05-PR-WORKFLOW — Workflow для Pull Requests

> **Цель:** atomic PR, чёткий review-process, voiceless integration в main. Каждый PR — это понятная единица изменений с tests + docs.

## Жизненный цикл

```
1. Phase task → branch создан
2. Изменения commit'ы (atomic, conventional)
3. PR создан (используя template)
4. CI gates pass (lint/types/tests/security/SBOM)
5. Tier-based review (см. ниже)
6. **Exit ritual выполнен** (JOURNAL + HANDOFF — см. ниже)
7. Merge в main (squash или rebase per repo policy)
8. Phase-checkpoint updated в roadmap (mark done)
```

## Exit ritual (обязателен перед merge)

Перед merge каждой PR агент обязан выполнить три действия:

1. **Append запись в [`../JOURNAL.md`](../JOURNAL.md)** (append-only журнал сессий). Шаблон:
   ```
   ## YYYY-MM-DD · <branch-slug> · @<agent>
   - Scope: <одно предложение>
   - Done: <ключевые изменения>
   - Decisions: <ссылки на новые ADR, если есть>
   - Next: <что должен сделать следующий agent>
   - Refs: PR #NNN, phase ID
   ```
   При >300 строк журнал откатывается в `dev-log/archive/JOURNAL-YYYYQN.md` (директория создаётся при первой архивации; не нужна заранее).

2. **Перезаписать [`../HANDOFF.md`](../HANDOFF.md)** — снимок текущего state для следующей сессии (current phase, in-progress work, blockers, must-read files, рекомендации по next-action). История — через `git log HANDOFF.md`.

3. **Упомянуть оба обновления в описании PR** (в разделе «Linked artifacts» или отдельной строкой «Exit ritual: JOURNAL +1, HANDOFF refreshed»).

**Без выполнения Exit ritual review-gate блокирует merge.** Это hard rule — не soft-рекомендация. Reviewer проверяет наличие обновлений `JOURNAL.md` и `HANDOFF.md` в diff'е PR.

**Исключение:** trivial auto-merge Tier 1 (typo fix, format-only) — можно пропустить, но рекомендуется записать одну строку в JOURNAL для трейсабилити.

## Branching

| Тип | Naming |
|---|---|
| Phase task (AI-led session, default) | `claude/<adjective-noun-hash>` (e.g. `claude/heuristic-rhodes-f7a3ef`) — Claude-Code-generated short id |
| Phase task (human-led) | `feature/<phase-id>-<slug>` (e.g. `feature/00.4-llm-gateway`) |
| Bugfix | `fix/<slug>` (e.g. `fix/auth-token-expiry`) |
| Hotfix (prod) | `hotfix/<slug>` |
| Chore (config/docs) | `chore/<slug>` |
| Refactor | `refactor/<slug>` |

The `claude/<slug>` form is the documented practice for Claude-Code AI
sessions and is semantically equivalent to `feature/<phase-id>-<slug>` —
the PR title carries the phase-id (e.g. `[00.4] feat: ...`) so the phase
binding is in the PR, not the branch.

## Commit conventions (Conventional Commits)

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat` — new feature
- `fix` — bug fix
- `chore` — config, build, dependencies
- `docs` — documentation
- `refactor` — code restructure no functional change
- `test` — adding/changing tests
- `perf` — performance improvement
- `security` — security fix

**Scopes (our project):**
- `iam` — auth, users, workspaces
- `cells` — cell lifecycle
- `agents` — roles, runtime, prompts
- `runtime` — task execution, workflows
- `artifacts` — files, Yjs, S3
- `billing` — credits, ЮKassa
- `memory` — workspace + role + PARA
- `mcp` — MCP client + servers
- `audit` — logs, compliance
- `notifications` — email, Telegram
- `frontend` — UI components, routing
- `pixel` — Pixel Department
- `infra` — Terraform, Docker, k8s, CI
- `docs` — `.planning/` updates

**Examples:**
```
feat(llm_gateway): add DeepSeek provider with OpenAI-compatible client

- Implement DeepSeek client wrapper
- Add fallback chain DeepSeek → YandexGPT → GigaChat
- Unit tests + integration test
- Coverage 87%

Refs: phase 00.4, ADR-018
TBD: TBD_DEEPSEEK_API_KEY in .env.example

Co-Authored-By: Claude Code <noreply@anthropic.com>
```

```
fix(iam): refresh-token rotation race condition

When concurrent requests refreshed simultaneously, both got new tokens
but old token wasn't revoked atomically. Fixed via row-lock в transaction.

Refs: R-21, ADR-007

Co-Authored-By: Claude Code <noreply@anthropic.com>
```

## PR template

```markdown
## Goal

<one-sentence: что меняем и зачем>

## Changes

- <Concrete change 1>
- <Concrete change 2>
- <Tests added/updated>

## Phase / ADR / Risk references

- Phase: Wave N Phase N.M (<slug>)
- ADR: ADR-XXX, ADR-YYY
- Risk: R-NN (if security/compliance)

## TBD-tokens used

- `TBD_X` — in <file>:<line>, replace before <when>

## Testing

- [x] Unit tests added/updated
- [x] Integration tests pass
- [x] Manual smoke tests done
- Coverage: 87% (new code) — exceeds 70% target

## CI checks

- [x] Lint (ruff / eslint)
- [x] Type-check (mypy strict / tsc strict)
- [x] Security scan (Semgrep / Bandit / gitleaks)
- [x] License scan (no GPL/AGPL)
- [x] Dependency vulnerability scan
- [x] SBOM generated
- [x] Container scan (if Docker)
- [x] Migration safety (if DB changes)
- [x] Golden dataset regression (if role prompt changed)

## Reviewers

Per tier-based ruleset (см. conventions.md):
- Tier: <1-5>
- AI-reviewers: <subagent IDs>
- Human-reviewers: <@usernames>

## Risk assessment

- Breaking changes: <yes/no>
- DB migrations: <none / safe / requires downtime>
- Rollback plan: <how>

## Linked artifacts

- Issue: #NNN
- Handoff: HANDOFF.md refresh + JOURNAL.md +1 (per Exit ritual)
- Updated docs: <list>
```

## Tier-based review

**Source of truth:** [ADR-027 §tier-table](../decisions/ADR-027-solo-ai-git-pr-workflow.md) — 5 tiers с AI reviewers (per ADR-023 11-role catalog) + Founder approval per [P-INIT-3](../decisions/ADR-028-policies-registry.md#policies-canonical-home) (Founder = always final approver tier 3+).

Не дублируем tier-table инлайн. При изменении tier-policy → обновляется ADR-027.

## CI gates (mandatory)

Из conventions.md:

```
1. Lint (ruff, eslint)
2. Type-check (mypy strict, tsc strict)
3. Unit tests + coverage gate (≥70% для нового кода, ≥85% security-critical)
4. Integration tests
5. Security: Semgrep, Bandit, gitleaks, pip-audit, npm audit
6. SBOM (Syft) + vuln scan (Grype)
7. License scan (forbid GPL/AGPL)
8. Container scan (Trivy)
9. Migration safety (squawk)
10. Golden dataset regression (if role prompt changed)
11. Performance benchmark (для critical endpoints)
```

**Любой fail = блок merge.** Bypass только через explicit override + human approval + ADR-обоснование.

## PR size guidelines

- **Target:** < 500 строк изменений
- **Acceptable:** до 800 строк (с обоснованием)
- **Block:** > 1000 строк (требуется split)

**Исключения:**
- Generated кода (миграции, OpenAPI clients) — отдельный commit с явным labeling
- Pixel-art ассеты (binary files) — отдельный PR

## Atomicity

Один PR = один logical change.

✅ Good:
- «Add DeepSeek provider» (provider + tests + config + docs)
- «Fix auth token race condition» (bug + test + rollback)

❌ Bad:
- «Add 3 providers + refactor billing + new UI screen» — split на 3 PR.

## Auto-merge для Tier 1

Patch security updates, doc fixes, format-only changes:

- Auto-merge if CI green
- Auto-cleanup ветки

## Hotfix workflow

При prod incident:

1. Branch from `main` → `hotfix/<slug>`
2. Минимальный fix (не fix-everything, только нужное)
3. PR → tier 5 → 1 senior expedited review
4. Merge → cherry-pick в develop (если есть)
5. **Post-mortem** в `docs/incidents/YYYY-MM-DD-slug.md`

## Deploy gates

После merge в main:
- **Staging deploy** — auto (через ArgoCD / GitHub Actions)
- **Smoke tests** — auto post-deploy
- **Prod deploy** — manual approval (Tech Lead trigger) после staging-soak >1 час

## Issue linking

В PR description:
- `Closes #123` — auto-close issue после merge
- `Refs #124` — связь без closing
- `See ADR-XXX` — pointer на architecture decision
- `Mitigates R-NN` — pointer на risk

## When PR is stuck

| Reason | Action |
|---|---|
| CI failing | Fix locally, push update |
| Conflict with main | Rebase against main, force-push к feature-ветке |
| Reviewer unavailable >24h | Поставить async-комментарий, escalate в Tech Lead |
| Архитектурное disagreement | Escalation (см. 03-ESCALATION.md) → создать ADR |
| Scope creep | Split PR, переоткрыть с smaller scope |

## Anti-patterns

### ❌ PR без tests
Не merge'им. Tier 2+ требует tests.

### ❌ PR с TBD-tokens в production-code без явного marking
- Use ENV vars для secrets
- Mark TBD в код-комментарии: `# TODO: TBD_BRAND_NAME — replace after OQ-09`

### ❌ Big-bang refactor PR
Split на mechanical refactor + functional changes.

### ❌ Merge без CI green
Никогда. Bypass = ADR + Tech Lead override.

### ❌ Commit message «Updated stuff»
Conventional commits, please.

## Branch protection (для main)

Settings в GitHub:
- ✅ Require pull request reviews before merging
- ✅ Require status checks to pass (все CI gates)
- ✅ Require branches to be up to date
- ✅ Include administrators
- ✅ Restrict who can push to matching branches
- ✅ Require signed commits (Wave 2+)

## Cheat sheet

| Сценарий | Branch | Tier | Approval |
|---|---|---|---|
| Fix typo in doc | `chore/...` | 1 | Auto-merge |
| Add unit test | `test/...` | 2 | 1 AI |
| Add new endpoint | `claude/...` or `feature/...` | 3 | 1 AI + 1 human |
| Change auth flow | `claude/...` or `feature/...` | 4 | 2 AI + 2 human |
| Prod bug fix | `hotfix/...` | 5 | 1 AI + 1 senior expedited |
