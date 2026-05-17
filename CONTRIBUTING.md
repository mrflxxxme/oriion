# Contributing — TEAMLY_RU

Этот проект использует disciplined AI-agent workflow per [ADR-023](.planning/decisions/ADR-023-ai-team-runtime.md) (11 persistent Opus AI-агентов + non-persistent specialized roles).

## Bootstrap (обязательно перед первым действием)

Прочитай ровно эти **4 файла** (~15 KB total):

1. [`.planning/README.md`](.planning/README.md) — что за проект + schema `.planning/`
2. [`.planning/STATUS.md`](.planning/STATUS.md) — текущее состояние, active blockers
3. [`.planning/HANDOFF.md`](.planning/HANDOFF.md) — снимок от прошлой сессии
4. [`.planning/agent-handbook/00-START-HERE.md`](.planning/agent-handbook/00-START-HERE.md) — workflow protocol

Полный workflow handbook — [`.planning/agent-handbook/`](.planning/agent-handbook/) (7 файлов: context-loading / delegation / escalation / handoff / PR-workflow / debugging / AI-team-pipeline).

## Code conventions

См. [`.planning/_meta/conventions.md`](.planning/_meta/conventions.md). Ключевое:

- **Commit format:** conventional commits с tier classification per ADR-027 tier-table в commit message
- **Atomic commits** — каждая логическая единица = один commit
- **Branch protection:** `--force-with-lease` only, no `--no-verify`, hook fail → fix
- **PR tier 3+** требует **founder explicit approve** per [P-INIT-3](.planning/decisions/ADR-028-policies-registry.md)
- **PR tier 4** требует founder approve + ADR-link
- **Exit ritual** обязателен перед merge: JOURNAL + HANDOFF дописываются (см. [`agent-handbook/04-HANDOFF.md`](.planning/agent-handbook/04-HANDOFF.md))

## Tier-table (per ADR-027)

| Tier | Founder action | Когда |
|---|---|---|
| 1 | auto-merge if CI green | docs, format, dep-patch |
| 2 | skim diff, ack | tests, refactors, copy |
| 3 | **explicit approve** | new endpoint, component, feature |
| 4 | **explicit approve + ADR-link** | architecture, security, billing, migrations |
| 5 | same-session approve | hotfix |

## Architecture Decision Records (ADR)

- Catalog: [`.planning/decisions/README.md`](.planning/decisions/README.md)
- Template: [`.planning/decisions/ADR-template.md`](.planning/decisions/ADR-template.md)
- Любое архитектурное отклонение от существующего ADR требует **новый ADR через template + escalation**

## Risks & TBD

- **Open questions:** [`.planning/OPEN-QUESTIONS.md`](.planning/OPEN-QUESTIONS.md)
- **TBD literals:** [`.planning/PLACEHOLDERS.md`](.planning/PLACEHOLDERS.md) — НЕ выдумывай значения, используй placeholder как literal
- **Risk register:** [`.planning/risks/REGISTER.md`](.planning/risks/REGISTER.md)

## Pull-request workflow

См. [`.planning/agent-handbook/05-PR-WORKFLOW.md`](.planning/agent-handbook/05-PR-WORKFLOW.md). Контрольный список:

- [ ] Atomic commits с tier classification в commit message
- [ ] Tests pass: `make test`
- [ ] Lint clean: `make lint`
- [ ] Typecheck clean: `make typecheck`
- [ ] Pre-commit hooks pass (или explicit reason для `--no-verify`)
- [ ] CI workflows зелёные (ci-backend / ci-frontend / ci-security)
- [ ] JOURNAL.md updated (append-only)
- [ ] HANDOFF.md rewritten (snapshot)
- [ ] STATUS.md reflects current state
- [ ] PR title: `<type>(<scope>): <subject>` (conventional commits)
- [ ] PR body: tier classification + ADR refs (если tier 4) + acceptance checklist

## Local dev

См. [README.md](README.md) Quickstart.

### Pre-commit hooks

```bash
uv run pre-commit install     # активировать (one-time per clone)
pre-commit run --all-files    # one-time full scan
```

Bypass только в emergency: `git commit --no-verify` (CI всё равно поймает).

### Tests

```bash
make test-backend             # pytest -m "not integration"
make test-backend-integration # требует `make dev` running
make test-frontend            # vitest + coverage
```

## Reporting issues

GitHub repo: см. `TBD_GITHUB_ORG/TBD_GITHUB_REPO` в [`.planning/PLACEHOLDERS.md`](.planning/PLACEHOLDERS.md).

## Founder

Kirill Uklonskiy <uklonskiy.k@gmail.com> — продукт + архитектура + sales + final approver per [ADR-027](.planning/decisions/ADR-027-solo-ai-git-pr-workflow.md).
