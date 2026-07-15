# Wave 2 — Phase Index

> **Регенерировано 2026-07-11** по итогам founder-grill (24 решения D-01..D-24 → [DECISIONS-LOG](../../_session-context/DECISIONS-LOG.md), запись `grill-2026-07-11`) + фонового аудита (backend/frontend/canon — все гейты W1 green, блокеров нет). Прежний placeholder упразднён. Каждая фаза имеет seed-spec в [phases/](./phases/) (DoR-формат per [ADR-040 D1](../../decisions/ADR-040-execution-spec-contract.md)); спека дорастает на discuss-шаге `/autonomy:run`.

## Ключевые решения состава (grill 2026-07-11)

- **WB-Селлер удалён целиком** (D-06): вертикаль, коннектор, герой, пресет — вне роадмапа; W0-заготовка переехала в retired-архив [`.planning/verticals/_retired/wb-seller/`](../../verticals/_retired/) (2026-07-15) — история, не план. **Новых вертикалей в W2 нет** (D-07) — углубляем horizontal + 2 reviewed-вертикали; выбор следующей — на гейте W2→3 по данным 02.0/беты.
- **Mini App возвращён в W2 финальной фазой 02.12** (grill-доп 2026-07-11, **D-25**, суперсид D-03): скоуп БЕЗ Business API (мобильный approval-фронт + задачи; initData-auth); 01.11 остаётся parked RW-05, DM-сценарии — апгрейдом.
- **Реальный MCP-протокол возвращён замыкающей фазой 02.13** (**D-26**, суперсид D-04): клиент + каталог интеграций + community-серверы **github-mcp + google-sheets-mcp**; наши коннекторы остаются native (ADR-041). 02.13 — первый кандидат на перенос в W3 при затягивании волны (D-27).
- **Новая фаза 02.2 tier-1 редизайн** (D-24): research-first пересборка IA/навигации/лейаутов + DS v0.3 — сразу после retro, всё последующее строится на ней.
- **Approval-UI** (D-08): human-approved send (TG-пост + email), autonomous send выключен до W3+.
- **Pixel** (D-09/D-10/D-20..23): полный opt-in скин-режим; ассеты — API-генерация + founder-курация; hand-drawn герои не гейтят волну.
- **Платежи** (D-02/D-11): 01.3b в треке (parked-until-RW-04, founder стартует RW-04 в неделю 1); рекуррентная подписка + credit-паки.

## Очередь исполнения (последовательный раннер, ADR-037 D6)

| # | Фаза | Направление | Seed-spec | Ключевые ADR | Статус |
|---|---|---|---|---|---|
| 1 | **02.1-retro** | Wave-opening retro: DV-01/03/10 (+DV-11 по кредам), хвосты W1, распил dispatch.py, frontend var-индирекция, docs-sync | [02.1-retro](./phases/02.1-retro.md) | ADR-040 D6 | ⏳ next |
| 2 | **02.0** | Friend-validation: воронка-телеметрия + NPS-виджет; друзья 2 волнами (2–3 сразу → 10–15 после 02.2) | [02.0](./phases/02.0-friend-validation.md) | ADR-040 D5 | ⏳ |
| 3 | **02.2** | **Tier-1 редизайн**: UX-research → IA/навигация → DS v0.3 (+bake-off, founder-touchpoints) | [02.2](./phases/02.2-redesign-tier1.md) | **ADR-042** (new), ADR-031 | ⏳ |
| 4 | **02.3** | **Approval-UI + send unlock** (TG+email, human-approved; fail-closed scoping) | [02.3](./phases/02.3-approval-ui-send.md) | ADR-041, ADR-014 | ⏳ |
| 5 | **02.4** | Golden-сертификация 30-task ≥75% × 2 вертикали + Master hardening (гасит DV-13) | [02.4](./phases/02.4-golden-certification.md) | ADR-026, ADR-029 | ⏳ |
| 6 | **02.5** | Onboarding-расширение: routing horizontal-vs-vertical, live-demo, waitlist «Скоро» | [02.5](./phases/02.5-onboarding-extension.md) | ADR-016, ADR-022 | ⏳ |
| 7 | **02.6** | Pixel: полный скин-режим (`data-skin` поверх DS v0.3) + офис в cell/Dashboard + live-состояния по SSE | [02.6](./phases/02.6-pixel-skin.md) | ADR-004, ADR-031 | ⏳ |
| 8 | **02.7** | Pixel-ассеты: API-ген 24 архетипов + founder-курация + пиксель-тур; герои — asset-апдейтом (RW-10) | [02.7](./phases/02.7-pixel-assets.md) | ADR-021 (amended) | ⏳ |
| 9 | **02.8** | Marketing-лендинги (Astro) на профики.online: главная + 2 вертикали + прайсинг + waitlist | [02.8](./phases/02.8-marketing-landings.md) | ADR-017, ADR-042 | ⏳ |
| ⇄ | **01.3b** | ЮKassa: рекуррентная подписка + credit-паки — **вливается в очередь по RW-04** (ожидаемо середина волны) | [01.3b](./phases/01.3b-yookassa.md) | ADR-008 | ⏸ parked (RW-04) |
| 10 | **02.9** | RBAC: Admin + Viewer + приватные артефакты (гасит DV-07); Bot/Service → W3 | [02.9](./phases/02.9-rbac-extension.md) | ADR-014, ADR-038 | ⏳ |
| 11 | **02.10** | Storage-quota enforcement: HARD-REJECT + алерт 90% (субстрат 01.5) | [02.10](./phases/02.10-storage-quotas.md) | ADR-012, ADR-008 | ⏳ |
| 12 | **02.11** | Pyodide-runner для Analyst: код-артефакт + Run-кнопка (web worker) | [02.11](./phases/02.11-pyodide-runner.md) | ADR-020 | ⏳ |
| 13 | **02.12** | **Telegram Mini App**: мобильный approval-фронт (reuse API 02.3) + задачи/артефакты + нотификации; initData-auth; БЕЗ Business API (01.11 parked RW-05) | [02.12](./phases/02.12-telegram-mini-app.md) | ADR-030 (revised) | ⏳ |
| 14 | **02.13** | **MCP-протокол**: реальный клиент (stdio/streamable-http) + каталог интеграций + github-mcp + google-sheets-mcp; unknown-tool fail-closed; замыкающая, 1-й кандидат на перенос | [02.13](./phases/02.13-mcp-protocol.md) | ADR-013/041 (revised) | ⏳ |

## Founder-треки (параллельно, старт — неделя 1)

| Трек | RW | Гейтит |
|---|---|---|
| OQ-02 (юр.форма) + заявка ЮKassa (5–10 раб. дней) | [RW-04](../../FOUNDER-RUNWAY.md) | 01.3b целиком |
| Наём pixel-художника: тендер FL.ru/Кворк, 2 героя (SMM-Анастасия, Крейтор-Денис), $400–1000/герой | RW-10 (new) | ничего (герои — asset-апдейт, D-10) |
| API-ключ image-gen сервиса (~$20–50) | RW-11 (new) | 02.7 |
| Telegram bot-token + тест-канал (~5 мин) | RW-03 | live-proof 02.3 + остаток DV-11 |
| Рекрутинг друзей (2–3 сразу, 10–15 после 02.2) | — | метрики 02.0 |

## Перенесено в Wave 3 (решения 2026-07-11, ревизия grill-доп D-25/D-26)

01.11 Business API + DM-сценарии Mini App (RW-05, юрист) · community-MCP сверх github/google-sheets (notion/slack/gmail/gdrive — по спросу беты) + user-supplied MCP-серверы · следующая вертикаль (D-07, выбор по данным беты) · Bot/Service-роль (D-15) · autonomous send + layer-A ML DLP (D-08) · co-editing 02.9-old (RQ-20260701-001, триггер не наступил) · интерактивный ноутбук (D-14) · Telegram Stars (ADR-030).

## Acceptance gate to Wave 3

[gates/wave-2-to-3.md](../../gates/wave-2-to-3.md) — **переписан 2026-07-11 (D-17)**: hard-пороги = вычислимые технические; регистрации/TTFV/конверсия — замеры к гейту (решение founder), не блокеры.
