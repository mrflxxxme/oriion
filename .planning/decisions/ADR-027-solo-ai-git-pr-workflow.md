# ADR-027: Solo + AI Git/PR workflow — phase-branch + atomic AI commits + selective rebase + tier-based review

- **Status:** Accepted (§5 tier-table **ревизован [ADR-037](./ADR-037-autonomous-multiphase-runner.md)** — под автономным раннером founder выходит из merge-петли на всех тирах; approver-prerogative заменён на узкую растяжку D2 + продукт-эскалацию D4)

## Decision

Покрывает [ADR-028 policies registry](./ADR-028-policies-registry.md) DECISION-10. Описывает, КАК код, сгенерированный AI-агентами (см. ADR-023), попадает в `main`. Заменяет tier-based review секцию из ADR-015 (revised → operational hygiene).

### 1. Branching

- **Per-phase branch:** `feature/wave-N-phase-NN.M-<slug>` (например `feature/wave-0-phase-00.2-custom-jwt-auth`).
- AI-агенты делают **atomic commits** внутри branch'а — каждый logical step (одна табличка, один endpoint, один компонент) → один commit.
- `main` защищена branch-protection (no direct push, require PR + status checks).
- **No merge-commits в main** — линейная история (rebase или squash, см. §3).

### 2. Pre-merge rebase

Перед merge founder делает `git rebase -i` для consolidation atomic AI-commits в 3-5 logical chunks (если PR большой). Trivial PR (≤3 commits) — без rebase.

Цель: PR history читаемый человеку через год, AI-trail сохраняется в `Pipeline-role` поле commit message (см. §4).

### 3. Merge policy

| Tier | Strategy |
|---|---|
| Tier 1 (docs, format, dep-patch) | Squash merge |
| Tier 2 (tests, refactors, copy) | Squash merge |
| Tier 3 (new endpoint, component) | Rebase merge (сохраняем pipeline-trail) |
| Tier 4 (architecture, security, billing, migrations) | Rebase merge + ADR-link обязателен |
| Tier 5 (hotfix) | Fast-forward после verifier full-acceptance |

### 3a. Post-merge branch teardown

- **Head-ветки удаляются автоматически при merge** (repo-setting `deleteBranchOnMerge=true`). После merge PR'а ветка-источник на `origin` исчезает — это норма, не аномалия.
- **Prune-audit gate ОБЯЗАН использовать `gh pr` state==MERGED, а НЕ `git branch -r --merged origin/main`.** Squash/rebase merge переписывают SHA → tip merged-ветки **не является ancestor** `main`, поэтому эвристика `--merged` возвращает пустоту и даёт ложный «nothing to prune». Канонический источник «что уже влито» — состояние PR через `gh`, не git-ancestry.
- **Периодическая гигиена:** прогонять `git fetch --prune` + удалять worktree'ы/ветки, чей upstream показывает `: gone]` (в `git branch -vv`). Это снимает локально-висящие ветки, чей remote-tracking уже удалён auto-teardown'ом.

### 4. AI commit format

Каждый commit от AI-агента:

```
<type>(<bounded-context>): <description>

Phase: <phase-id>
Pipeline-role: <role-name>
Reviewers: <list with approval status>
ADR-refs: <list>

Co-Authored-By: <role-name> (Opus) <role@teamly-ai>
```

Пример:

```
feat(iam): add JWT refresh-token rotation

Phase: 00.2
Pipeline-role: backend-implementer
Reviewers: reviewer-backend (approved), reviewer-security (approved)
ADR-refs: ADR-007, ADR-014

Co-Authored-By: backend-implementer (Opus) <backend-implementer@teamly-ai>
```

`<type>` следует Conventional Commits (`feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`).

### 5. Tier-table (re-thought для solo + AI)

> **⚠️ Ревизия [ADR-037](./ADR-037-autonomous-multiphase-runner.md) (2026-07-01):** под автономным раннером «Founder = всегда финальный approver для tier 3+» **больше не действует**. Founder выходит из merge-петли на всех тирах; авто-мёрж всё зелёное, кроме узкой растяжки категорий (миграции/auth/billing/секреты/контракты → 1-клик ack) + продукт-эскалаций. Таблица ниже описывает legacy manual-режим — сохранена для контекста и как fallback, когда раннер не используется.

| Tier | Примеры | AI reviewers | Founder action |
|---|---|---|---|
| **1** | Docs, format, dep-patch | — | Auto-merge if CI green |
| **2** | Tests, refactors, copy | 1 (relevant reviewer) | Skim diff, ack |
| **3** | New endpoint, новый компонент | 2 (code + security) | Approve |
| **4** | Architecture, security, billing, migrations | 3 (code + security + architect) + ADR-link **required** | Explicit approve |
| **5** | Hotfix | 1 expedited + verifier full-acceptance | Same-session approve |

**Founder = всегда финальный approver для tier 3+.** AI-агенты не имеют merge prerogative. CI green + reviewer-approved не достаточно — нужен явный founder-approve.

### 6. Failure handling

Если reviewer находит блокирующее замечание:

1. Reviewer создаёт `revisions/<phase>-<reviewer>.md` в branch'е с failure detail (file:line, expected, actual, severity).
2. **planner** (см. ADR-023) перепланирует subtask, добавляет в PLAN.md.
3. **implementer** фиксит, делает новый commit (НЕ `--amend`).
4. **reviewer** делает re-review.

Max **3 цикла** reviewer ↔ implementer. После 3-го цикла — эскалация к founder (architect agent prepares context summary).

### 7. Force-push

- AI-агенты имеют `--force-with-lease` **только на feature-branch**. `main` защищена branch-protection.
- `--force` (без `-with-lease`) запрещён всем.
- Pre-merge rebase делает founder, не AI.

### 8. Commit signing

GPG-sign отложен до **Wave 3** (GA-release). До Wave 3 коммиты подписываются только по author email convention (`<role>@teamly-ai` для AI-агентов, founder personal email для ручных правок). Wave 3 включит GPG signing для:
- Founder commits.
- AI-агентов через managed signing key (стoroage TBD, Wave 3 phase-spec).

## Consequences

- **ADR-015 (revised)** теряет секцию «Tier-based ревью» — заменяется cross-ref сюда.
- **Founder approver-prerogative** сохраняется на всех значимых tier'ах. CI и AI reviewers — necessary but not sufficient.
- **Atomic AI-commits** дают reviewer'у мелкозернистый diff per commit (каждый = одно logical change). Pre-merge rebase консолидирует под человекочитаемую структуру при mergе.
- **Max 3 цикла reviewer ↔ implementer** предотвращает бесконечные loops (например, реviewer-frontend и implementer спорят о styling) — после 3-го раза founder решает.
- **Audit trail** через `Pipeline-role` поле в commit message — через год понятно, какая роль написала каждый кусок кода.
- **No GPG до Wave 3** — операционная гигиена не страдает (audit log в audit context + GitHub commit history), но supply-chain attack surface остаётся выше до Wave 3.

## Links

- [ADR-028 policies registry](./ADR-028-policies-registry.md) — DECISION-10
- [ADR-015](./ADR-015-ai-dev-process.md) — operational hygiene (CI-gates, isolation, observability)
- [ADR-023](./ADR-023-ai-team-runtime.md) — 11 ролей + pipeline-шаблон + handoff
- [ADR-014](./ADR-014-security.md) — RBAC + DLP (применяется к code review)
- Conventional Commits spec: https://www.conventionalcommits.org/
