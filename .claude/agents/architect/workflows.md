# architect — workflows

Три canonical playbook'а. Каждый workflow — input → steps → outputs → handoff. Если задача
не ложится ни в один — escalate к founder с описанием gap.

---

## Workflow 1 — ADR drafting from grill-session

**Trigger:** founder завершил grill-сессию и записал решения в
`.planning/_meta/GRILL-DECISIONS-ORIION.md` §1 (новая строка в session log) + §2
(session detail). Призван через CloudEvent `tech.oriion.grill.decision.v1` от founder.

**Inputs:**
- Полный текст новой session detail из §2.
- Текущий `decisions/README.md` catalog (для understanding cross-link surface).
- Существующие ADR, чьи темы пересекаются (через grep по keywords из decision titles).
- Активные риски из `risks/REGISTER.md`.

**Steps:**

1. **Parse decisions.** Из session detail извлеки discrete decisions (обычно 1-N штук per
   session). Каждое decision → отдельный candidate ADR. Если decision слишком мелкое
   (single-line policy) — рассмотри добавление как policy в §3 GRILL-DECISIONS вместо ADR.
2. **Check overlap.** Для каждого candidate ADR grep existing ADR на overlap. Если overlap
   найден — определи: (a) supersedes (старый ADR полностью заменяется), (b) informs
   (старый ADR частично revised), (c) independent (новый ADR живёт рядом).
3. **Draft ADR file.** Per ADR template (см. ADR-023/024/025 как образец):
   - `# ADR-NNN: <title>` — NNN inkrement от max в catalog
   - `- **Status:** Accepted` (если founder approved в session) или `Proposed`
   - `## Decision` с пронумерованными секциями (1, 2, 3, ...)
   - `## Consequences` — explicit list trade-offs (+ benefits, − costs/risks)
   - `## Links` — cross-ref к GRILL DECISION, related ADR, affected risks
4. **Cross-link updates.** Подготовь diff для:
   - `decisions/README.md` — добавь строку в catalog
   - Superseded/informed ADR — обнови их frontmatter `Status` и Links секцию
   - `risks/REGISTER.md` — если ADR закрывает/добавляет/изменяет severity риска
5. **Self-audit per checklist.** Прогони `checklists/adr-creation.md`.
6. **Submit к founder для review.**

**Outputs:**
- `.planning/decisions/ADR-NNN-<slug>.md` (новый файл)
- Diff для `decisions/README.md`
- Diff для superseded ADR (если есть)
- Diff для `risks/REGISTER.md` (если applicable)

**Handoff:** CloudEvent `tech.oriion.adr.draft.v1` к founder. После founder approve →
`tech.oriion.adr.merged.v1` к `memory-curator` для catalog persistence и AgentDB
embedding refresh.

---

## Workflow 2 — Cross-phase invariant audit (pre-wave-gate)

**Trigger:** wave-gate approaches per ADR-025. `memory-curator` завершил auto-fill 80%
frontmatter в `.planning/gates/wave-N-to-N+1.md` и emit CloudEvent
`tech.oriion.gate.metrics_ready.v1`. Audit запускается перед founder-narrative phase.

**Inputs:**
- `.planning/gates/wave-N-to-N+1.md` (partially filled frontmatter)
- All phase-spec'и Wave N
- `_meta/contracts/<context>/` × 10 (или подмножество, затронутое Wave N)
- Текущий `decisions/README.md` + recent ADR (added в Wave N)
- `risks/REGISTER.md`

**Steps:**

1. **Deprecated-term sweep (P-AUDIT-2).** Grep по deprecated terms из ADR-024 §2 во всех
   phase-spec'ах Wave N + `_meta/contracts/<context>/`. Любой match — finding (severity:
   critical), proposal: rename в той же PR что закрывает gate.
2. **Naming drift check.** Grep canonical terms (`agent_archetype_id`, `system_roles`,
   `agent_archetypes`) — должны быть consistent across all contracts. Mixed case
   (например `agent_archetypeId` vs `agent_archetype_id`) — finding.
3. **Bounded-context coupling audit.** Для каждого `_meta/contracts/<context>/README.md`
   прочитай «External dependencies» секцию (если есть). Cross-reference с фактическими
   импортами в `backend/src/<context>/` (если код существует). Mismatches — finding.
4. **DDL conformance.** Diff `_meta/contracts/<context>/schema.sql` против
   `backend/alembic/versions/<context>/*.py` — все таблицы из schema.sql должны иметь
   migration. Drift — finding.
5. **Economic-numbers sweep (P-AUDIT-1).** Grep `$[0-9]`, `RUB`, `₽`, `MRR`, `budget` во
   всех новых артефактах Wave N (ADR/risks/phase-spec). Любой match — finding,
   proposal: extract в `cost-budget.yaml`.
6. **ADR cross-ref integrity.** Для каждого ADR added в Wave N — verify, что Links секция
   указывает: GRILL DECISION + related ADR + affected risks. Missing — finding.
7. **Compile audit report.** Findings table + recommendations + severity.

**Outputs:**
- `.planning/_meta/audits/audit-<YYYY-MM-DD>-wave-N-gate.md` с findings table

**Handoff:** CloudEvent `tech.oriion.audit.report.v1` к `memory-curator`. Если есть
critical findings — также `tech.oriion.conflict.escalation.v1` к founder с recommendation
закрыть findings в той же PR (per P-AUDIT-2).

---

## Workflow 3 — Escalation arbitration

**Trigger:** один из (a) `reviewer-backend` + `reviewer-security` дали conflicting
verdicts (один approve, другой revision-request на тот же diff); (b) 3 цикла
reviewer ↔ implementer исчерпаны (per ADR-027 §6); (c) founder призвал явно для second
opinion на tier-4 decision.

**Inputs:**
- PR diff (через git read-only access)
- Все reviewer artifacts: `revisions/<phase>-<reviewer>.md` × N
- PLAN.md этой phase
- Affected ADR + contracts
- Risks linked в commit message

**Steps:**

1. **Read reviewers' positions full.** Не делай assumptions — каждый revision-report
   прочитан полностью, including file:line references.
2. **Identify root conflict.** Чаще всего конфликт = trade-off (security vs performance,
   simplicity vs flexibility, ADR-A vs ADR-B). Сформулируй trade-off в одно предложение.
3. **Apply invariants priority.** Используй приоритеты из system-prompt §Invariants:
   - Inviolable: bounded-context boundaries, founder-approve tier 3+, no economic numbers
     in ADR, naming conventions
   - Negotiable per case: performance trade-offs, code style, testing depth
   Если конфликт inviolable vs negotiable — inviolable wins.
4. **Check existing policy.** Может быть policy в §3 GRILL-DECISIONS уже разрешает этот
   класс конфликтов. Если да — cite + close. Если нет — это policy-gap, escalate.
5. **Draft decision.** Markdown с (a) Trade-off statement, (b) Recommendation, (c)
   Rationale через ADR/policy cross-ref, (d) Risks of chosen path, (e) Mitigation.
6. **Decide: self-arbitrate or escalate.**
   - **Self-arbitrate:** если decision лежит в рамках existing ADR/policy. Decision
     возвращается reviewers + implementer как ground truth.
   - **Escalate к founder:** если decision требует policy override (новая ADR, изменение
     gate-threshold, экономическое решение, наклон конкретного бизнес-приоритета).
     Готовь escalation packet.

**Outputs:**
- Если self-arbitrate: `revisions/<phase>-architect-arbitration.md` с decision
- Если escalate: escalation packet к founder

**Handoff:**
- Self-arbitrate: CloudEvent `tech.oriion.arbitration.decision.v1` к reviewers и
  implementer одновременно (parallel).
- Escalate: CloudEvent `tech.oriion.conflict.escalation.v1` к founder. После founder
  decision — emit `tech.oriion.arbitration.decision.v1` с founder-rationale.
