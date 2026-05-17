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

## 2026-05-17 · amazing-hamilton-8b9d2c · @claude-opus
- Scope: Phase 00.1 (Repo & CI/CD) — monorepo skeleton + dev stack + CI workflows + pre-commit + bootstrap docs. Goal: cold-start dev env ≤ 600s, любой агент/разработчик стартует за <10 минут.
- Done (18 atomic commits (16 spec + impl + lock-files/format-fixes + test_health + exit-ritual + post-ritual gitignore tweak + audit-fix pass), ~1700 lines added):
  1. **Spec trim** (commit #1): drop `infra/terraform/`, MkDocs, GitLab mirror doc, standalone `ci-license.yml`, `docker-compose.staging.yml` placeholder. License-check merged как step в backend/frontend CI workflows. AC8→AC7 renumber (7 AC total). Rationale: maximum MVP velocity, infra-as-code returns Phase 00.6 as YC manual runbook.
  2. **Monorepo skeleton** (commits #2-#8): `.gitignore` extended (coverage/vite cache); `backend/` (pyproject.toml + uv + ruff + mypy strict + pytest + src/__init__.py + tests with 100% coverage); `frontend/` (Vite 6 + React 19 + TS strict + Tailwind v4 + shadcn/ui + ESLint 9 flat config + Prettier + vitest + utils.ts with 100% coverage); `infra/` (docker-compose.dev.yml с 6 services и healthchecks, Caddyfile.dev, postgres init-pgvector.sh — image pgvector/pgvector:pg16); backend + frontend Dockerfiles (multi-stage dev+prod); backend/src/main.py FastAPI app с /health endpoint (drives AC6); `scripts/` (wait_for_db.py + seed_dev_data.py async); `Makefile` (POSIX, 18 targets, TAB-indented) + `.gitattributes` для LF enforcement; `backend/alembic.ini` multi-version-directory per ADR-024 + env.py async runner + script.py.mako template.
  3. **CI workflows** (commits #9-#11, all tier 4): `ci-backend.yml` (ruff + mypy strict + pytest --cov-fail-under=70 + bandit + pip-audit + pip-licenses GPL/AGPL/LGPL forbid + Codecov upload, postgres+redis service containers с pgvector); `ci-frontend.yml` (eslint + prettier + tsc + vitest + Vite build smoke + npm audit + license-checker GPL/AGPL/LGPL forbid + Codecov); `ci-security.yml` (3 parallel jobs: gitleaks+trufflehog / Trivy filesystem SARIF / Syft SBOM + Grype SARIF). All workflows: timeout-minutes 8, concurrency cancel-in-progress, permissions: contents:read + security-events:write.
  4. **Pre-commit** (commit #12): `.pre-commit-config.yaml` (ruff + ruff-format + gitleaks + markdownlint + 4 local hooks: mypy-backend, eslint-frontend, prettier-frontend, typecheck-frontend) + `.markdownlint.json` lenient (MD013/MD033/MD034/MD041 off для ru-RU prose).
  5. **Bootstrap docs** (commit #13): `.env.example` (20 vars — dev defaults + TBD_ literals per PLACEHOLDERS.md), root `README.md` (Quickstart + Stack + docs cross-refs + project structure tree), `CONTRIBUTING.md` (bootstrap-4 + tier-table + ADR workflow + PR checklist).
  6. **Lock files + format fixes** (commits #14-15): committed `backend/uv.lock` + `frontend/package-lock.json` для reproducible CI; ruff/prettier auto-format pass; eslint test ruleset relaxed (no-unnecessary-condition/no-confusing-void-expression off в тестах); `.gitignore` extended с `.omc/` + `.claude-flow/` + `.swarm/` + `.hive-mind/`.
  7. **Backend coverage fix** (commit #16): added `backend/tests/test_health.py` (5 tests covering FastAPI app + /health endpoint + Swagger UI + ReDoc disabled + HealthResponse model). Result: 8 tests, 100% backend coverage (16/16 stmts, 100% branch). AC2 ✓.
- Local verification (30-min timebox):
  - **AC2** ✓ (coverage ≥70%): backend 100% (8 tests), frontend 100% on utils.ts (5 tests).
  - **AC7** ✓ (lint + typecheck): backend ruff + ruff-format + mypy --strict pass; frontend eslint --max-warnings=0 + prettier --check + tsc -b pass.
  - **AC1** DEFERRED (dev-bootstrap ≤600s): `docker compose up --build` failed на pull этапе с "short read: expected N bytes but got M: unexpected EOF" — network/registry connectivity issue в dev environment, не related к spec. Founder верифицирует post-merge или в окружении с stable Docker Hub access.
  - **AC6** DEFERRED (compose healthchecks ≤180s): same root cause — containers не стартовали без images.
  - **AC3 / AC4 / AC5** plan-deferred — CI workflows self-verify когда PR откроется (gated by branch protection per ADR-027).
- Decisions: no new ADR. Phase 00.1 strictly executes existing ADR-001/015/024/027/028. Reaffirmed: остаёмся на Yandex Cloud (рассмотрены альтернативы: VK Cloud, Selectel, Timeweb — отклонены на MVP scale из-за marginal cost savings vs архитектурный refactor); cloud provisioning отложен Phase 00.6 как manual YC runbook (no Terraform Wave 0).
- Next: (a) Final consistency audit (4 parallel subagents: Code Reviewer + security-reviewer + memory-curator + architect). (b) Founder push + PR open (tier 4 per ADR-027 — security workflows + CI infra). (c) Founder local-verify AC1/AC6 на своей машине OR в CI runner; revision-commits если нужно. (d) После merge → старт Phase 00.2 (Custom JWT auth) — required OQ-04 РКН close, parallel-ready с Phase 00.3 (DB + RLS + Cell schema) и Phase 00.4 (LLM gateway + MCP).
- Refs: branch `claude/amazing-hamilton-8b9d2c`; plan `C:\Users\KUklonskiy\.claude\plans\start-phase-00-1-of-dazzling-moore.md`; phase spec [`roadmap/wave-0-foundation/phases/00.1-repo-cicd.md`](./roadmap/wave-0-foundation/phases/00.1-repo-cicd.md).

## 2026-05-17 (post-merge) · post-00.1-memory-curator · @claude-opus
- Scope: post-merge memory-curator pass для Phase 00.1 completion. STATUS / HANDOFF / JOURNAL / PROJECT обновлены чтобы next session мог seamlessly start Phase 00.2 / 00.3 / 00.4 без re-discovery.
- Done:
  - **PR #25 merged** 2026-05-17T16:28:03Z → merge-commit `b192c6b` на main. 21 atomic commits всего (18 Phase 00.1 impl + 1 audit-fix + 2 CI fix passes).
  - **CI verdict:** all 6 status checks PASS на финальном run (ci-backend lint+typecheck+test+security+license / ci-frontend / 3 ci-security jobs / gitleaks). AC3/AC4/AC5 CI-verified inline.
  - **Security debt уже закрыт в Phase 00.1 PR** (не deferred Phase 00.2): python-jose → PyJWT[crypto], passlib → argon2-cffi (per ADR-014); FastAPI 0.115 → 0.129, starlette 0.46 → 0.52 (fixes CVE-2025-54121, CVE-2025-62727); pytest 8.3 → 9.0 (fixes CVE-2025-71176).
  - **CI infra fixes (in-PR):** pip-audit `--skip-editable` (was failing на local editable package not on PyPI); trivy-action `@0.28.0` → `@master` (version 0.28.0 не существует).
  - **STATUS.md:** Phase 00.1 → ✅ Complete; final AC scoreboard; OQ-04 explicitly tagged как 00.2 blocker; 00.3/00.4 parallel-ready listed; target-dates table: 00.1 finished 2 дня раньше plan (-2 нед buffer).
  - **PROJECT.md:** Current phase pointer updated to "Phase 00.1 Complete; Next: 00.2 (gated OQ-04), parallel 00.3/00.4".
  - **HANDOFF.md:** rewritten для next session — bootstrap-4 read list, Phase 00.2/00.3/00.4 starter pointers, prerequisites checklist, no remaining audit findings active.
- Decisions: no new ADR. Phase 00.1 security debt resolved without ADR-014 amendment (PyJWT + argon2-cffi already в ADR-014's preference list).
- Next: founder verifies AC1 + AC6 локально (выйдет за рамки этой curator-сессии). Затем next AI-agent session открывает либо Phase 00.2 (если OQ-04 closed) либо Phase 00.3/00.4 в parallel.
- Refs: PR [oriion#25](https://github.com/mrflxxxme/oriion/pull/25); merge-commit `b192c6b`; branch `claude/post-00.1-memory-curator`.
