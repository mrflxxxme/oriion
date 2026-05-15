# Development Journal

Append-only журнал AI-агентских сессий. Одна запись на каждую завершённую сессию. Не редактировать прошлые записи — фиксируют состояние на момент завершения.

**Шаблон записи:**

```
## YYYY-MM-DD · <branch-slug> · @<agent>
- Scope: <одно предложение>
- Done: <ключевые изменения>
- Decisions: <ссылки на новые ADR, если есть>
- Next: <что должен сделать следующий agent>
- Refs: PR #NNN, phase ID
```

**Архивирование:** при >300 строк журнал откатывается в `dev-log/archive/JOURNAL-YYYYQN.md` (создаётся при необходимости).

---

## 2026-05-14 · epic-almeida-152bad · @claude-opus
- Scope: финальный аудит репозитория перед Wave 0; cleanup + реорганизация + Path C разведение entry-points.
- Done:
  - Git-гигиена: удалены 11 merged feature/milestone-c-* и feature/milestone-d-* веток (локально + origin), 3 стале claude/* веток, 3 неактивных worktree (peaceful/optimistic/zen) сняты с git-реестра.
  - Удалены устаревшие артефакты: `research/teamly_to_analysis/` (4+ файла), 36 phase-stub'ов wave-1..4, `_meta/agent-protocol.md`.
  - Реорганизация: `_meta/{contracts,verticals,ui,tools}` → top-level `.planning/`; `_meta/open-questions.md` → `.planning/OPEN-QUESTIONS.md`. _meta теперь = 4 файла (README, stack, glossary, conventions; GRILL-DECISIONS подлежит дистилляции в Stage 7).
  - Стандартизация: `_meta/INDEX.md` → `_meta/README.md`; `roadmap/INDEX.md` → `roadmap/README.md`. Созданы тонкие `README.md` для risks/, contracts/, verticals/, ui/, tools/.
  - Path C: `.planning/README.md` сокращён до «what is this project» (~2 KB); `agent-handbook/00-START-HERE.md` переписан как полный workflow protocol с жёстким bootstrap-чек-листом (4 файла).
  - JOURNAL + HANDOFF созданы как обязательные exit-артефакты; Exit ritual добавлен в `agent-handbook/05-PR-WORKFLOW.md` как hard rule.
- Decisions: см. plan `C:\Users\KUklonskiy\.claude\plans\fluffy-napping-sunrise.md` (branches A–E, 10 решений).
- Next: закрытие OQ-17 (фандинг) + OQ-18 (burn-budget) — founder decision → старт Phase 00.1 (Repo & CI/CD).
- Follow-up в той же PR: зачищены pre-existing broken-ссылки в `verticals/wb-seller/*` (ADR-026 filename, ADR-015 filename, `roadmap.md`, depth-3 `tools/`, `_shared/cost-budget.yaml` пути).
- Refs: PR [oriion#22](https://github.com/mrflxxxme/oriion/pull/22); план fluffy-napping-sunrise.md.

## 2026-05-15 · frosty-raman-c9aaee · @claude-opus
- Scope: Pre-Wave-0 roadmap reorganization — horizontal team-preset как Wave 0 anchor вместо WB-Селлер vertical; introduction of Master-Agent layer для vertical-templates; Telegram Business API integration в Wave 1.
- Done (11 strategic decisions через grill-me interview):
  1. **Wave 0 anchor changed:** WB-Селлер vertical team → horizontal `productivity-core` («Твои личные ассистенты») с 4 ролями: Coordinator + Researcher + Writer + Analyst.
  2. **Demo Wave 0:** «Market & content brief для нового продукта» — 3 artifacts (brief.md ≥1500w + competitive-matrix.md ≥5×4 + content-plan.md 10 posts), latency ≤120s, cost ≤30¢.
  3. **Vertical wave-distribution re-ordered:** WB-Селлер W0→W2 (теперь vertical-anchor для public beta); ИП-Бух + СМБ-Sales W2→W3.
  4. **Wave 1 ships:** horizontal + 2 vertical (Marketing-agency + Telegram-крейтор) с первой инстанциацией Master-Agent layer; WB defer.
  5. **Dual messaging:** universal entry («Твои личные ассистенты») + vertical depth (Master-Agent layer).
  6. **NEW ADR-029 (Master-Agent layer):** двухслойная оркестрация для vertical-templates — Master (CEO domain-knowledge keeper) → Coordinator (operational COO) → specialists. Wave 1+ only; horizontal остаётся однослойным.
  7. **NEW ADR-030 (Telegram Business API):** telegram-mcp v0.2 в Wave 1 (Read + post + Business API + consent flow + 152-ФЗ disclosure); Mini App defer W2; Stars billing defer W4+.
  8. **Wave 2 timebox:** 8 → 9 нед (+WB + Mini App + Master-Agent first instances + 3 hand-drawn vertical-героев).
  9. **Wave 3 timebox:** 8 → 10 нед (+ИП-Бух + СМБ-Sales verticals + Master-Agents).
  10. **Downstream dates:** Wave 4 → 2027-02-22 (+3 нед vs prior).
  11. **Role-prompts contract pattern:** `contracts/role-prompts/` — 9-секционная глубокая структура (~2500–3200 слов / роль), YAML-frontmatter; coordinator/researcher/writer/analyst materialized в Wave 0; vertical Masters — в Wave 1+.
- Decisions: новые [ADR-029](.planning/decisions/ADR-029-master-agent-vertical-templates.md), [ADR-030](.planning/decisions/ADR-030-telegram-business-api.md). Revised: ADR-013 (MCP wave-table), ADR-017 (horizontal anchor + wave-reorder), ADR-022 (Coordinator hierarchy bifurcation horizontal vs vertical).
- Commits: `760991f` (main reorg, 22 files), follow-up commit (consistency fixes — gates/wave-0-to-1, phase 00.6 AC2, verticals/README, glossary, risks/REGISTER, PLACEHOLDERS, ADR cross-refs, verticals/wb-seller deferred-status).
- Next: founder подтверждает все decisions через `git push` + PR review → старт Phase 00.1 (Repo & CI/CD) per [STATUS.md](.planning/STATUS.md). Phase 01.1 retro spec'ается с включением role-prompts hardening pass (per AC14 phase 00.5).
- Refs: branch `claude/frosty-raman-c9aaee`; session-prompts/role-prompts в `.planning/contracts/role-prompts/`.
