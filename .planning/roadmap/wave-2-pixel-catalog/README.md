# Wave 2 — Pixel Department + WB-vertical + Telegram Mini App (9 недель)

> **Revision 2026-05-15:** Wave 2 scope reduced — ИП-Бухгалтерия + СМБ-Sales vertical-templates moved W2 → W3. Wave 2 теперь ships: +WB-Селлер vertical (graduated W0→W2) + Pixel + Pyodide + Telegram Mini App + первые **3 Master-Agent instances** (Marketing + Telegram + WB) + Master-Agent hardening pass. Timebox 8 → 9 weeks. See [Session-decision](../../JOURNAL.md).

## Цель волны

**Public beta релиз.** Pixel Department живёт (Native Canvas 2D), 4 templates в каталоге (1 horizontal + 3 vertical), Pyodide для Analyst-роли, MCP-каталог (vertical + community серверы), Telegram Mini App контейнер, полноценный onboarding с TTFV ≤3 мин.

## Метрика успеха

- 100 регистраций/нед из публичного трафика
- TTFV ≤3 мин (медиана)
- Trial → paid конверсия ≥5%
- **4 templates** в production (horizontal + Marketing-agency + Telegram-крейтор + WB-Селлер), у каждого vertical — golden dataset (30-50 задач) и hand-drawn vertical-герой
- Master-Agent layer hardened на 3 vertical-instances; vertical-tier pricing rationale validated через A/B-test
- Telegram Mini App live: ≥10 friends используют для approve/edit DM-replies
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
- Pixel Department: Native HTML5 Canvas 2D + AI-generated baseline (24 archetypes) + 3 vertical-героев hand-drawn для W2 verticals (Marketing-agency «SMM-Анастасия», Telegram-крейтор «Крейтор-Денис», WB-Селлер «Селлер-Маркус») — ADR-004, ADR-021. Остальные 2 hand-drawn героя (Бухгалтер-Анна + Sales-Дмитрий) — Wave 3.
- Расширение каталога: **+WB-Селлер vertical-template** (graduated W0→W2) — добавляется поверх 3 templates из Wave 1
- **Master-Agent hardening pass** на 3 vertical-instances + новый WB-Master с deep prompt в `contracts/role-prompts/masters/wb-seller-master.md`
- Pyodide WASM для Analyst-роли (ADR-020) — code execution в браузере; Analyst capability-gap из Wave 0 закрыт
- **Telegram Mini App контейнер** per [ADR-030](../../decisions/ADR-030-telegram-business-api.md): inline-approve/edit DM-replies, schedule preview, content-approve workflow
- MCP-серверы (Wave 2 set): **wb-partners-mcp** (наш, для WB vertical), bitrix24-mcp, amocrm-mcp (наши) + community github-mcp, notion-mcp, slack-mcp, gmail-mcp, google-drive-mcp, google-sheets-mcp
- Полный onboarding: wizard (3 шага) + auto-spawn trial-cell + live demo + Pixel office tour + horizontal-vs-vertical routing UI
- Admin + Viewer RBAC расширение
- Golden datasets для 3 vertical-templates W2 (Marketing + Telegram + WB)
- 2D-сцена офиса (минимум: карточки + pixelBob, полная сцена — Wave 3)

**Nice:**
- ИП-Бухгалтерия / СМБ-Sales preview/teaser (показываются в каталоге как «Скоро» с waitlist signup)
- Mobile-responsive (минимум обеспечиваем, fully — Wave 3)
- Telegram-бот для нотификаций (без команд)

## Длительность и команда

- **Срок:** 9 недель (revision 2026-05-15: +1 нед vs prior 8 weeks — поглощает +WB-vertical и Telegram Mini App)
- **Команда:** +Middle Backend, +Designer (UI/UX), +Senior Frontend (Vite+React+Canvas), Tech Lead, Senior Backend, DevOps 0.5

## Phases

См. [PHASES.md](./PHASES.md).

> **⚠️ Phase-файлы Wave 2 — placeholder под прежнюю архитектуру.** Каждая phase регенерируется в начале Wave 2 на базе актуальных ADR + результатов Wave 1 retro.

## Risks specific

- **R-14** (Pixel-art bottleneck): pixel-artist для **3 vertical-героев W2** — найм через FL.ru / Хабр / Кворк ДО старта Phase 02.1 (Бухгалтер-Анна + Sales-Дмитрий — Wave 3 hire)
- **R-11** (Pixel как secondary USP): NPS upticks от Pixel — мониторим; kill criteria: NPS <30 + 0 упоминаний за 4 мес
- **R-12**: соблазн добавить MCP power-features / workflow-шаблоны — это Wave 3
- **R-27, R-28** (Pyodide): version pinning + «desktop recommended» UX для heavy analysis
- **R-05** (data leak, Mini App): Mini App работает внутри Telegram client → дополнительный attack surface; security review Mini App до production
- **R-NEW (Master-Agent maturity):** 3 verticals shipping simultaneously means 3 vertical Masters need to be production-quality одновременно — risk concentration; mitigated через staggered rollout (Marketing first → Telegram → WB)

## Артефакты к концу волны

- Public-доступный продукт на основном домене
- 4 templates в production (horizontal + 3 vertical) с golden datasets для verticals
- 3 hand-drawn vertical-героев + 24 AI-generated archetypes (ещё 2 hand-drawn — Wave 3)
- 3 vertical Master-Agents (hardened после Wave 1 first-draft) + WB-Master (Wave 2 new)
- Pixel Department live
- Telegram Mini App live с inline-approve UX
- MCP-каталог (9+ серверов) в UI, включая wb-partners-mcp
- Pyodide-runner для Analyst во всех team-presets (Analyst capability-gap из Wave 0 закрыт)
- Полный onboarding wizard + live demo + horizontal-vs-vertical routing
- ~50 платящих, обратная связь обработана
- Marketing-лендинги для horizontal-сегмента + 3 vertical-сегмента (через Astro)
- Waitlist для ИП-Бух + СМБ-Sales (готовится к Wave 3)
