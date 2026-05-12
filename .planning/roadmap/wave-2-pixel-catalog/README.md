# Wave 2 — Pixel Department + полный каталог vertical-templates (8 недель)

## Цель волны

**Public beta релиз.** Pixel Department живёт (Native Canvas 2D), 5 vertical-templates в каталоге, Pyodide для Analyst-роли, MCP-каталог (vertical + community серверы), полноценный onboarding с TTFV ≤3 мин.

## Метрика успеха

- 100 регистраций/нед из публичного трафика
- TTFV ≤3 мин (медиана)
- Trial → paid конверсия ≥5%
- 5 vertical-templates в production, у каждого golden dataset (30-50 задач)
- 50+ платящих клиентов
- Pixel Department NPS: первые отзывы упоминают как secondary USP

## Критерий перехода к Wave 3

- Все phase'ы Wave 2 — Done
- 50+ платящих
- Метрики достигнуты
- Marketing-канал отдаёт стабильно (Telegram-канал founder + 1 публикация на vc.ru / Хабре)
- Retro + risks register update

## Scope

**Must:**
- Pixel Department: Native HTML5 Canvas 2D + AI-generated baseline (24 archetypes) + 5 vertical-героев hand-drawn (ADR-004, ADR-021)
- Расширение каталога до 5 vertical-templates: +ИП-Бухгалтерия + СМБ-Sales (помимо 3 из Wave 1) — ADR-017
- Pyodide WASM для Analyst-роли (ADR-020) — code execution в браузере
- MCP-серверы (Wave 2 set): bitrix24-mcp, amocrm-mcp, wb-partners-mcp, ozon-seller-mcp (наши) + community github-mcp, notion-mcp, slack-mcp, gmail-mcp, google-drive-mcp, google-sheets-mcp
- Полный onboarding: wizard (3 шага) + auto-spawn trial-cell + live demo + Pixel office tour
- Admin + Viewer RBAC расширение
- Golden datasets для всех 5 vertical-templates
- 2D-сцена офиса (минимум: карточки + pixelBob, полная сцена — Wave 3)

**Nice:**
- 6-я vertical-template (если ресурс позволяет)
- Mobile-responsive (минимум обеспечиваем, fully — Wave 3)
- Telegram-бот для нотификаций

## Длительность и команда

- **Срок:** 8 недель
- **Команда:** +Middle Backend, +Designer (UI/UX), +Senior Frontend (Vite+React+Canvas), Tech Lead, Senior Backend, DevOps 0.5

## Phases

См. [PHASES.md](./PHASES.md).

> **⚠️ Phase-файлы Wave 2 — placeholder под прежнюю архитектуру.** Каждая phase регенерируется в начале Wave 2 на базе актуальных ADR + результатов Wave 1 retro.

## Risks specific

- **R-14** (Pixel-art bottleneck): pixel-artist для 5 vertical-героев — найм через FL.ru / Хабр / Кворк ДО старта Phase 02.1
- **R-11** (Pixel как secondary USP): NPS upticks от Pixel — мониторим; kill criteria: NPS <30 + 0 упоминаний за 4 мес
- **R-12**: соблазн добавить MCP power-features / workflow-шаблоны — это Wave 3
- **R-27, R-28** (Pyodide): version pinning + «desktop recommended» UX для heavy analysis

## Артефакты к концу волны

- Public-доступный продукт на основном домене
- 5 vertical-templates в production с golden datasets
- 5 hand-drawn vertical-героев + 24 AI-generated archetypes
- MCP-каталог (10+ серверов) в UI
- Pyodide-runner для Analyst во всех vertical-team
- Полный onboarding wizard + live demo
- ~50 платящих, обратная связь обработана
- Marketing-лендинги для 3-5 vertical-сегментов (через Astro)
