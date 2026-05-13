# Checklist — ADR creation

Прогоняется перед emit `tech.oriion.adr.draft.v1` к founder. Все пункты должны быть
checked или явно отмечены N/A с rationale.

## Frontmatter & status

- [ ] `# ADR-NNN: <title>` — NNN корректно incremented vs `decisions/README.md` catalog
- [ ] `- **Status:** Accepted` ИЛИ `Proposed` (не пусто, не `Draft`)
- [ ] Title — короткий, descriptive, без implementation details (e.g. "Vertical-prompt
      SemVer auto-bump policy", не "Implement auto-bump in CI workflow")
- [ ] Файл назван `ADR-NNN-<slug>.md` где `<slug>` совпадает с title (kebab-case)

## Decision section

- [ ] `## Decision` — первый параграф открывается ссылкой на source: `Покрывает
      [GRILL-DECISIONS-ORIION](../_meta/GRILL-DECISIONS-ORIION.md) DECISION-N` ИЛИ
      `Cross-cutting ADR без single grill-source` (с rationale)
- [ ] Decision декомпозирован на пронумерованные секции (`### 1.`, `### 2.`, ...) — не
      walls of text
- [ ] Каждая секция имеет concrete deliverable (table, code block, file path) — не только
      narrative
- [ ] Если ADR содержит DDL/OpenAPI fragments — fragments представлены как example, а
      authoritative spec ссылается на `_meta/contracts/<context>/`
- [ ] Альтернативы рассмотрены: либо явно (table «Alternatives considered») либо упомянуты
      inline с rationale почему отвергнуты

## Consequences section

- [ ] `## Consequences` — explicit list: benefits + costs/risks + trade-offs
- [ ] Каждый consequence — actionable (можно проверить через 6 месяцев, что он реализовался
      или нет)
- [ ] Если ADR влияет на team capacity / cost — упомянуто наличие механизма
      (`cost-budget.yaml`), но не конкретные числа (per P-AUDIT-1)
- [ ] Если ADR закрывает риск — указано «Closes R-NN»; если добавляет — «Adds R-MM (owner=...)»

## Links section

- [ ] `## Links` — присутствует
- [ ] Cross-ref на GRILL DECISION ID + section
- [ ] Cross-ref на superseded ADR (если есть) + supersede direction
- [ ] Cross-ref на informed/revised ADR (если есть)
- [ ] Cross-ref на affected risks (R-NN)
- [ ] External standards (если cited): URL + accessed-date

## Naming & invariants

- [ ] Используются канонические термины: `agent_archetype_id`, `system_roles`,
      `agent_archetypes` — NO `roles_rbac` / `roles_agent` / `sprite-ID` / `ui_sprite_archetype`
- [ ] Bounded-context references — точные имена из ADR-024 §1 (10 contexts)
- [ ] Никаких $-чисел / RUB / MRR thresholds в ADR (per P-AUDIT-1)
- [ ] CloudEvents — упоминается только spec 1.0, не custom форматы

## Cross-link maintenance diffs

- [ ] Diff для `decisions/README.md` подготовлен (новая строка в catalog с правильной
      категорией)
- [ ] Если ADR supersedes: diff для старого ADR с `Status: Superseded by ADR-NNN` +
      Links update
- [ ] Если ADR informs: diff для старого ADR с new informs-link
- [ ] Если ADR закрывает/добавляет/изменяет риск: diff для `risks/REGISTER.md`

## Per-PR-bundle (P-AUDIT-2)

- [ ] Если ADR объявляет термин/column/API deprecated — выявлены ВСЕ existing phase-spec'и
      / contracts / handbook-файлы с этим термином (через Grep)
- [ ] Patch-diff'ы для cleanup deprecated terms подготовлены и будут в той же PR
- [ ] НЕ deferred в follow-up milestone — иначе AI-агент материализует deprecated artifact

## Final

- [ ] Self-review: прочитан вслух (mental playback) — звучит coherently, без contradictions
- [ ] Founder action явно указан: `approve` / `revise <section>` / `discuss`
- [ ] CloudEvent payload `tech.oriion.adr.draft.v1` собран и validated против
      `_shared/handoff-schema.json`
