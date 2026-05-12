# RECONSTRUCTION NOTES — Gap Analysis vs наш Roadmap

> Финальный документ. Содержит actionable insights для пересмотра нашего roadmap'а и ADR'ов.

## Резюме (3 главных вывода)

1. **Pixel Department можно сделать намного проще, чем мы планировали.** Teamly использует native HTML `<canvas>` 2D + PNG sprite-sheets, никаких PixiJS/Phaser/Three.js. Это снимает требование к найму senior PixiJS-разработчика (вопрос 13 интервью, R-09). Главный bottleneck — pixel-art artist, не engineer.

2. **«Cell» концепция teamly — сильнейший маркетинговый и операционный wedge.** Каждая «AI team» = dedicated infra cell с фиксированным регионом. Это даёт честное обещание «dedicated infrastructure» и снимает security objections. Мы планируем то же самое (ADR-009 Level C на Wave 4), но **запускаем shared B на старте** — этим теряем маркетинговое преимущество. Стоит рассмотреть «dedicated cell с дня 1» для Pro-тарифа.

3. **Composio + BYOK дают огромное ускорение и доверие.** Teamly не строит свои коннекторы — берёт Composio (1000+ apps) и фокусируется на product. Это снижает effort интеграций в 10×. И BYOK с «no markup» — прозрачность, которая build trust моментально. Нам стоит:
   - Серьёзно рассмотреть Composio (или РФ-аналог) вместо собственного MCP-каталога для GUI-юзеров.
   - Поднять BYOK с Wave 4 до Wave 3.

## Per-ADR delta (что обновить)

### ADR-001: Модульный монолит (Python+FastAPI)
**Стабильно.** Teamly использует Next.js full-stack (likely API routes + backend services), мы используем Python — это разный путь, оба валидны. Никаких изменений.

### ADR-002: LLM Multi-provider Gateway
**Усиливать.** Teamly поддерживает 9 BYOK-провайдеров (anthropic, openai, google, openrouter, minimax, zai + 2 search + composio). Наш ADR-002 покрывает 2 + RU-стек. Нужно расширить:
- Добавить Google Gemini, OpenRouter в roadmap (Wave 3+)
- Опционально: MiniMax + Z.AI для Chinese LLM-доступа (для клиентов, которые работают с КНР-сегментом)

### ADR-003: Pydantic-AI runtime
**Стабильно.** Teamly's runtime скрыт, но workflow-step pattern совпадает с CrewAI-style decomposition. Pydantic-AI остаётся хорошим выбором.

### ADR-004: Pixel Department на PixiJS
**ПЕРЕСМОТР НЕОБХОДИМ.** Teamly не использует PixiJS — native canvas 2D + PNG sprites + CSS keyframes. Это:
- Упрощает frontend stack (no PixiJS dependency, ~500KB bundle сохранён)
- Снижает hiring requirements (любой React+Canvas разработчик справится)
- Производительность: 41 canvas на странице работает плавно

**Action:** обновить ADR-004 на «Native canvas 2D с PNG sprite-sheets». PixiJS — резервный вариант для Wave 4+ если потребуется heavy animation (drag-and-drop layouts, физика).

### ADR-005: pgvector then Qdrant
**Стабильно.** Teamly не раскрыл storage. Наш план — норм.

### ADR-006: gVisor then Firecracker
**Стабильно.** Teamly does не show sandbox approach (нет execution в free tier).

### ADR-007: Authentik then Keycloak
**Альтернатива: Clerk.** Teamly использует Clerk и явно happy with it. Clerk — это **managed identity-as-a-service**, заметно проще, чем self-hosted Authentik:
- Clerk: managed SaaS, easy SSO/social, $25-100/mo plans
- Authentik: self-hosted, free, but maintenance overhead

**Action:** для нашего РФ-проекта Clerk недоступен напрямую (US-only, рекомендации санкций). Authentik остаётся правильным выбором, но **знаем, что глобальные конкуренты экономят инженерное время через managed-identity**. Для международной экспансии (Wave 5+) — рассмотреть Clerk или аналог.

### ADR-008: Team-кредиты + ЮKassa
**Уточнить.** Teamly's model: 1 T$ = $1 (passthrough). Мы планируем двухставочный курс (1× RU / 3× международный). Это **более сложно**, но необходимо для нашей реальности.

**Action:** уточнить в ADR-008:
- «1 Team-кредит = X токенов RU / Y токенов международный, не фиксированный курс к рублю»
- Добавить BYOK option на Wave 3 (а не Wave 4) — это закрывает ту же боль для price-sensitive enterprise клиентов
- «Top up anytime» — мы уже имеем soft/hard-cap, но также рассмотреть **on-demand top-up в любое время** (наш hard-cap может быть soft-blocker с одобрением)

### ADR-009: Multitenancy 3 levels (B → C → D)
**Обсудить ускорение C.** Teamly's «cell per team» = это уровень C с дня 1. Это сильный wedge.

**Action:**
- Рассмотреть запуск Pro-тарифа с dedicated namespace (level C) уже на Wave 3 (а не Wave 4).
- Маркетинговое сообщение «dedicated infrastructure per team» с дня 1 — мощное.
- Trade-off: дороже в эксплуатации; нужен ROI-анализ.

### ADR-010: Role versioning + canary + golden
**Стабильно.** У teamly versioning не наблюдали — возможно у них один canonical version per role без явной policy.

### ADR-011: 2-уровневая память
**Дополнить PARA Workspace concept.** Teamly's autonomous mode включает **PARA Workspace** (Projects/Areas/Resources/Archive) — это elegant structure для long-term knowledge. Это вдохновение для нашего Wave 5+ episodic memory.

**Action:** в ADR-011 добавить ссылку: «При проектировании episodic memory в Wave 5+ рассмотреть PARA-подобную структуру (см. teamly_to_analysis/05-agent-system.md).»

### ADR-012: Artifacts (Yjs для документов)
**Стабильно.** Teamly's artifact UX не видна (требует cell).

### ADR-013: MCP-протокол
**ОБСУДИТЬ ВЫБОР.** Composio vs MCP — стратегический вопрос:
- MCP — open standard, developer-focused, gaining adoption
- Composio — managed product, GUI-friendly, fast time-to-value
- Teamly выбрал Composio + offering BYOK

**Action:** рассмотреть гибрид в нашем roadmap:
- **MCP** для tech-savvy custom integrations (developers/partners) — Wave 3 (уже планируется)
- **Composio-style managed catalog** для GUI users — добавить как Wave 3/4 фичу
- ИЛИ строить свой managed catalog с **РФ-toolkits** (Bitrix24, amoCRM, 1С, Эльба) как наш wedge

### ADR-014: Security (RBAC + DLP + isolation)
**Стабильно.** Teamly's security не виден в depth, но «cell» isolation совпадает с нашим level C/D.

### ADR-015: AI-dev process
**Стабильно.** Teamly's внутренняя dev practice не видна.

## Открытые архитектурные вопросы (нужно решить)

1. **Каналы как input — добавляем?** Teamly's Channels (Slack/Discord/Telegram inputs) превращают cell в multi-channel AI worker. Это **major value-add для agency clients**. У нас в roadmap нет explicitly. Рекомендация: добавить как Wave 3 фичу (под autonomous-mode-flag).

2. **Polar.sh vs ЮKassa архитектура билинга.** Polar — modern, dev-friendly. ЮKassa — РФ-standard. Они работают по-разному (Polar = subscription + webhook, ЮKassa = single-shot + recurring). Наш ADR-008 предполагает ЮKassa. Это правильно для РФ. **Не менять.**

3. **Sprite asset pipeline.** Кто рисует pixel-art? Это самый дорогой бюджет (заметно дороже, чем JS-code). Action: на Wave 2 (Pixel Department phase 02.1) подключить subcontract pixel artist или агентство как раз перед стартом.

4. **PARA для memory — Tiago Forte methodology.** Стоит ли brand'ить нашу memory как «PARA» или придумывать собственный термин? Это маркетинговый вопрос.

5. **Composio для глобальных коннекторов.** ROI: $0.10-0.30 per OAuth-flow saved vs $50K-100K инженерных часов. Если у Composio есть РФ-юридический контур (доступность из РФ) — это **massive shortcut**.

## Кражи: что взять (paterns, NOT кода / ассетов)

### UX patterns
- ✅ «Hire your AI team» фрейминг
- ✅ Pixel-art aesthetic (наш своими ассетами)
- ✅ Press Start 2P font для headings
- ✅ Pre-built teams каталог UX
- ✅ Coordinator wizard для unauth users
- ✅ «Most Popular» badge на middle tier
- ✅ Tier-naming convention («Team 5 / 15 / 30»)
- ✅ BYOK transparency

### Architecture patterns
- ✅ Cell-per-team isolation (для Pro-tariff с дня 3)
- ✅ Composio-style managed integrations
- ✅ BYOK для все LLM providers с дня 1
- ✅ Autonomous mode: heartbeat + cron + memory
- ✅ Workflow templates как DAG со step.passesTo
- ✅ Sprite reuse strategy (один archetype → разные роли)

### НЕ берём
- ❌ USD billing (мы рублёвая)
- ❌ Polar.sh (мы ЮKassa)
- ❌ Clerk (мы Authentik)
- ❌ Composio для РФ-toolkits (там пусто; делаем custom)
- ❌ English-only маркетинг
- ❌ Wizard-only Coordinator на free-tier (наш LLM-Coordinator может быть доступен freemium с лимитами)

## Новые риски, открытые анализом

Добавить в `risks/REGISTER.md`:

- **R-13: Зависимость от 3rd-party AI-инфра (если выберем Composio).** Vendor lock-in.
- **R-14: Pixel-art artist bottleneck.** Без качественных ассетов Pixel Department выглядит дешёво. Стартовый бюджет: 30-50 sprite chars × ~$200-500 per char = $6K-25K на ассетах.
- **R-15: РФ-санкции на Composio.** Если Composio EU/US-hosted, есть risk доступа из РФ-IP. Альтернатива: VPS-proxy или собственная Composio-альтернатива.

## Стратегические инсайты для нашего GTM

1. **Wedge для РФ-рынка:** Composio NOT интегрирован с Bitrix/amoCRM/1С/Эльбой → у нас уникальное value-prop «AI-команды + ваши российские tools».
2. **Wedge для price-sensitive:** BYOK + рублёвый бил + transparent pricing «1 кредит = N токенов» (мы можем быть честнее) → trust + СМБ-friendly.
3. **Wedge для compliance:** ФЗ-152 + ПДн в РФ + аудит-журналы + российские контуры → enterprise-РФ может выбрать нас vs teamly.
4. **Wedge для лояльности:** Vertical-templates под российские use-cases (СМБ-маркетинг агентство / WB-селлер / гос-юрист / 1С-бухгалтер) — niche, но defendable.

## Action items (для команды, после ревью этого документа)

1. Tech Lead: пересмотреть ADR-004 (canvas vs PixiJS) — потенциально снизить scope Wave 2 phase 02.1
2. Tech Lead: оценить Composio integration для Wave 3 (alternative to MCP-only)
3. Founder: решить ускорение BYOK на Wave 3
4. Founder + Designer: pixel-art бюджет + subcontract план
5. Tech Lead: рассмотреть Channels (Slack/Telegram input) как Wave 3 фича
6. Founder: оценить «cell-per-team» dedicated infra для Pro-tariff на Wave 3
7. Risk owner: добавить R-13/R-14/R-15 в risks/REGISTER.md
8. Founder: PARA Workspace — название для нашей memory architecture (Wave 5+)
