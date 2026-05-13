# Frontend implementer — workflows

---

## Playbook 1: Implement page from designer mock

**Entry:** inbound `tech.oriion.design.mock.v1` с mocks[] + validation_report.

**Шаги:**

1. **Validate input.** Проверить, что `validation_report.all_components_in_inventory=true`, `a11y_must_have_addressed=true`. Если нет — отбить handoff обратно к designer через `tech.oriion.handoff.error.v1`.
2. **Load codebase context (JIT).** Read `frontend/src/components/ui/` (shadcn primitives), relevant `frontend/src/routes/`, tsconfig + tailwind.config. Не загружать всё подряд — только покрывающие нужные components/routes файлы.
3. **Plan commits.** Декомпозировать deliverable в 3-7 atomic commits: route file → component skeleton → states (loading/empty/error) → data hooks → tests. План записать в `phase-state:<phase-id>` namespace.
4. **Execute (per commit).** Для каждого chunk: write/edit файлы → run `npm run lint` через Bash → `npm run typecheck` → `git add <files>` → `git commit -m` с форматом из [ADR-027 §4](../../../.planning/decisions/ADR-027-solo-ai-git-pr-workflow.md).
5. **Self-check checklist** `checklists/pr-prep.md` перед handoff к reviewers.
6. **Compose outbound handoff** `tech.oriion.code.commit.v1` — payload: commit SHAs, изменённые файлы, tokens-used map, components-used list, test-coverage report.

**Exit:** все commits в feature-branch, handoff отправлен к reviewer-frontend + reviewer-security параллельно.

---

## Playbook 2: Fix reviewer feedback

**Entry:** inbound `tech.oriion.review.report.v1` со status `revisions_requested` от reviewer-frontend или reviewer-security.

**Шаги:**

1. **Read `revisions/<phase>-<reviewer>.md`** в branch'е — там детали (file:line, expected, actual, severity).
2. **Plan fix** — НЕ `git --amend`, новый commit per [ADR-027 §6](../../../.planning/decisions/ADR-027-solo-ai-git-pr-workflow.md).
3. **Apply fix → lint → typecheck → commit → push (`--force-with-lease` allowed)**.
4. **Re-emit** `tech.oriion.code.commit.v1` с признаком `revision_iteration=N`.

**Exit:** новый commit, reviewer re-review. Max 3 цикла, потом эскалация founder.
