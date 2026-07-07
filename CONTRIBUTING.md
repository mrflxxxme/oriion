# Contributing — Oriion

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
- **Merge authority = gate-stack** per [ADR-037 D1](.planning/decisions/ADR-037-autonomous-multiphase-runner.md) (ревизует прежнее «tier 3+ = founder approve»): auto-merge при всех зелёных гейтах + fresh evidence + tripwire exit 0; совпадение с [tripwire-категорией](.claude/autonomy/tripwire.yaml) → founder 1-click `/ack`
- **Exit ritual** обязателен перед merge: JOURNAL + HANDOFF + doc-sync (README-фаза / runbook / статус фазного файла per [ADR-040 D9](.planning/decisions/ADR-040-execution-spec-contract.md)); см. [`agent-handbook/04-HANDOFF.md`](.planning/agent-handbook/04-HANDOFF.md)

## Tier-table (per ADR-027; merge-колонка ревизована ADR-037)

| Tier | Merge path (ADR-037/040) | Когда |
|---|---|---|
| 1–2 | auto-merge (гейты + evidence зелёные, tripwire clean) | docs, format, dep-patch, tests, refactors |
| 3–4 | auto-merge ИЛИ founder `/ack` при tripwire-совпадении (migrations / auth / billing / secrets / contracts) | endpoint, feature, architecture, security |
| 5 | same-session `/ack` | hotfix |

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
