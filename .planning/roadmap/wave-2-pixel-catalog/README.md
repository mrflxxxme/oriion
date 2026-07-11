# Wave 2 — Public beta: tier-1 редизайн + цикл ценности + Pixel-скин + монетизация

> **Revision 2026-07-11 (founder-grill, D-01..D-24):** волна пересобрана по итогам Wave 1. Удалено: WB-Селлер вертикаль (D-06; заготовка `.planning/verticals/wb-seller/` — retired-архив). Добавлено: **tier-1 редизайн** (02.2, D-24), **Approval-UI + human-approved send** (02.3 — незакрытый хвост W1), friend-validation (02.0, перенос из гейта W1→2 per ADR-040 D5), 01.3b ЮKassa (carry-over, RW-04). Прежние ревизии 2026-05-15 / 2026-06-11 поглощены этой.
>
> **Revision-доп 2026-07-11 (grill-доп, D-25..D-28, суперсид D-03/D-04):** на освободившееся после WB место **возвращены финальными фазами** Mini App (02.12 — мобильный approval-фронт, БЕЗ Business API; 01.11 остаётся parked RW-05) и реальный MCP-протокол (02.13 — клиент + каталог + github-mcp/google-sheets-mcp; замыкающая, 1-й кандидат на перенос при затягивании). Гейт: +2 порога (`mini_app_live`, `mcp_live`); ориентир → 2026-09-21.

## Цель волны

**Public beta.** Продукт на tier-1 дизайне (пересобранные IA/навигация + DS v0.3) открыт публичному трафику с профики.online; полный цикл ценности работает: агент готовит → человек подтверждает → уходит наружу (Telegram/email), в том числе **с телефона через Telegram Mini App**; обе вертикали сертифицированы полными golden-прогонами; Pixel Department живёт как opt-in скин с AI-generated архетипами; монетизация live (рекуррентная подписка + credit-паки через ЮKassa — по RW-04); Pyodide закрывает Analyst capability-gap; **каталог интеграций** с первыми community-MCP серверами (github, google-sheets) поверх реального MCP-протокола.

## Метрики

**Hard-пороги гейта (вычислимые, D-17 + D-28)** — см. [gates/wave-2-to-3.md](../../gates/wave-2-to-3.md): must-фазы merged · AC pass-rate · DV без открытых P1 · approval-flow live e2e · скин live с AI-бейзлайном · сертификация ≥75% × 2 вертикали · платёж протестирован (если RW-04 разблокирован; иначе перенос по протоколу RUNWAY №3) · **mini_app_live** (TMA: initData-auth + approve-флоу e2e) · **mcp_live** (1+ community-сервер, tool-call round-trip; при переносе 02.13 в W3 по D-27 — порог N/A).

**Замеры к гейту (решение founder, не блокеры):** регистрации/нед из публичного трафика (ориентир 100) · TTFV медиана (ориентир ≤3 мин) · Trial→paid конверсия (ориентир ≥5%) · платящие (ориентир 50) · NPS friend-когорты · Pixel-скин: доля включивших + упоминания в фидбеке (kill-criteria R-11 читается с поправкой на opt-in).

## Scope

**Must (очередь — [PHASES.md](./PHASES.md)):**
- 02.1-retro (DV-гашение + хвосты W1 + распил dispatch.py + var-индирекция)
- 02.0 friend-validation (телеметрия + NPS; друзья 2 волнами)
- 02.2 **tier-1 редизайн**: UX-research трендов → IA/навигация/лейауты → DS v0.3 (ADR-042; founder-touchpoints: бриф → IA → bake-off → утверждение)
- 02.3 **Approval-UI**: human-approved send TG-постов + email; autonomous send OFF до W3+
- 02.4 golden-сертификация (30-task ≥75% × agency_marketing_ru + telegram_creator) + Master hardening
- 02.5 onboarding-расширение (routing, live-demo, waitlist ИП-Бух/СМБ-Sales)
- 02.6 Pixel: полный opt-in скин-режим + офис-витрина + live-состояния по SSE
- 02.7 Pixel-ассеты: API-генерация 24 архетипов + founder-курация (+ пиксель-тур в онбординге); 2 hand-drawn героя (Анастасия, Денис) — asset-апдейт вне гейта (RW-10)
- 02.8 marketing-лендинги (Astro, профики.online / app.профики.online)
- 01.3b ЮKassa (рекуррент + паки; parked-until-RW-04)
- 02.9 RBAC Admin/Viewer + приватные артефакты (DV-07)
- 02.10 storage-quota enforcement (HARD-REJECT)
- 02.11 Pyodide-runner (код-артефакт + Run)
- 02.12 **Telegram Mini App**: мобильный approval-фронт + задачи/артефакты + нотификации (initData-auth; БЕЗ Business API — D-25)
- 02.13 **MCP-протокол**: клиент + каталог интеграций + github-mcp + google-sheets-mcp (замыкающая; 1-й кандидат на перенос — D-27)

**Вне волны (→ W3):** 01.11 Business API + DM-сценарии Mini App (RW-05) · community-MCP сверх github/google-sheets + user-supplied серверы · следующая вертикаль (по данным беты) · Bot/Service-роль · autonomous send + layer-A ML · co-editing (y-websocket) · полная 2D-сцена офиса · интерактивный ноутбук · Telegram Stars.

## Срок и бюджет

- **Ориентир:** ~10 недель → **2026-09-21** (D-18, ревизия D-28: +2 недели на возвращённые 02.12/02.13; ориентир, не жёсткий дедлайн — фактический темп зависит от ack/RW-разблокировок; редизайн 02.2 — крупнейшая фаза, риск сдвига учтён).
- **Бюджет:** dev-team капы v4 без изменений — $50 soft / $75 hard в день (D-19). Live-golden суммарно по фазам ≈ $7–12 + image-gen $20–50 (RW-11).

## Риски

- **R-12 (scope creep)** — редизайн 02.2 «глубокий» — границы зафиксированы seed-spec'ом (IA+DS+пересборка, БЕЗ ребрендинга имени/мобайла); соблазн MCP/power-фич — W3.
- **R-14 (artist bottleneck)** — снят с критического пути: герои не гейтят волну (D-10); тендер стартует в неделю 1 (RW-10).
- **R-11 (Pixel USP)** — kill-criteria с поправкой на opt-in долю; friend-фидбек 02.0 — ранний сигнал.
- **R-27/R-28 (Pyodide)** — version pinning + desktop-recommended UX (в seed-spec).
- **R-04/R-05** — активны как в W1 (caps, DLP ON, approval-flow adversarial-аудит).
- **Новый:** зависимость гейта от RW-04 (внешний процесс) — купирована протоколом RUNWAY №3 (перенос в W3 при неразблокировке).

## Артефакты к концу волны

- Public-доступный продукт: лендинги на профики.online + приложение app.профики.online на DS v0.3
- 3 темплейта в production (horizontal + 2 сертифицированные вертикали) + waitlist на следующие
- Approval-очередь: живые отправки в Telegram/email через подтверждение
- Pixel-скин live: 24 откурированных AI-архетипа, офис с live-состояниями; герои — по готовности художника
- Платёжный цикл ЮKassa (тест→live по RW-04)
- RBAC 4 роли + приватные артефакты; storage-квоты enforced
- Pyodide-runner у Analyst во всех пресетах
- Telegram Mini App live: approve/edit исходящих с телефона (метрика «≥N friends пользуются» — замер)
- Каталог интеграций: native-коннекторы + github-mcp + google-sheets-mcp через реальный MCP-протокол
- Friend-validation отчёт (воронка/TTFV/NPS) + gate-замеры для решения о W3
