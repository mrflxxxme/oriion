# ADR-004: Pixel Department — Native Canvas 2D + AI-generated assets + РФ-стилистика

- **Status:** Accepted

> **Revision 2026-06-11 (per [ADR-031](./ADR-031-design-direction-restyling.md)):** Pixel-герои и офис reframed как **опциональный «скин»/режим (opt-in, off by default)** поверх строго профессионального nordic base UI. Скоуп ассетов Wave 2 не меняется; marketing-positioning понижается с «defensible visual brand» до «memorable opt-in feature» — primary visual brand = professional nordic.

> **Revision 2026-07-11 (founder-grill Wave-2 planning, D-06/D-09/D-10/D-20..23):** (1) **Селлер-Маркус удалён** вместе с WB-вертикалью; W2 hand-drawn герои = 2 (SMM-Анастасия, Крейтор-Денис); Бухгалтер-Анна + Sales-Дмитрий — W3. (2) Скин = **полный режим UI** (ось `data-skin` поверх DS v0.3 из [ADR-042](./ADR-042-wave2-tier1-redesign.md): радиусы/шрифты/акценты), не только аватары. (3) Live-состояния спрайтов по SSE-прогрессу задач — уже в W2. (4) Офис-вью = секция страницы ячейки + виджет Dashboard (не отдельный роут). (5) Asset-pipeline: API-генерация вместо локального SDXL (см. amendment [ADR-021](./ADR-021-ai-generated-pixel-pipeline.md)). (6) Гейт волны: скин + 24 AI-архетипа; hand-drawn герои — asset-апдейт вне гейта. Фазы: 02.6 (скин) + 02.7 (ассеты).

## Decision

### Технический стек

- **Native HTML5 Canvas 2D API**
- **PNG sprite-sheets** per agent per state
- **CSS `@keyframes pixelBob`** для idle bounce, прочие state-transitions через redraw
- **Retina-rendering:** `canvas.width = 2× style.width`
- **React-component wrapper** `<AgentSprite agentId="..." state="idle" />`

### Asset pipeline

**24 generic archetypes (AI-generated):**
- SDXL + Pixel-Art-XL LoRA локально или на Yandex DataSphere GPU
- ComfyUI workflow: prompt → 512×512 pixel-art → post-process (Aseprite) → 4-frame idle-animation
- Naming: `<archetype><nn>` (e.g. `creative01`, `formal05`, `hoodie07`)
- Бюджет: $200-500 compute + 20 часов dev/artist на pipeline

**5 vertical-героев (hand-drawn):**
1. **Селлер-Маркус** — WB-Селлер / Ozon-Селлер team
2. **SMM-Анастасия** — Маркетинг-агентство РФ
3. **Крейтор-Денис** — Telegram-крейтор team
4. **Бухгалтер-Анна** — ИП-Бухгалтерия
5. **Sales-Дмитрий** — СМБ-Sales

Каждый × 4 анимации (idle / working / thinking / success-pose) = 20 sprite-sheets. Подрядчик: freelance artist через FL.ru / Хабр Карьера / Кворк. Бюджет: $400-1000 per герой = $2-5K total.

**Total Wave 2 Pixel-art бюджет:** $3-5K.

### РФ-стилистика

Каждый sprite, vertical-герой и сцена офиса содержит узнаваемые РФ-детали:
- Окна с видом на типовую московскую/петербургскую крышу
- На столах: кружки с лого «1С» / Тильда / Yandex, стакан с лого «Шоколадница»
- Календари (День маркетолога 21 сентября, 8 марта, …)
- Постеры «Селлер-2026», «Marketing meetup СПб», «Хабр-конференция»
- Иконки софта на мониторах: Bitrix24, amoCRM, 1С, ВКонтакте Workspace

### Animation states

- `profile` — статичный портрет (каталог, sidebar avatar)
- `idle` — base 4-frame loop (medium energy + pixelBob)
- `working` — typing/active animation
- `thinking` — pause + lightbulb pulse
- `success` — happy-pose при complete task
- `error` — confused-pose при failed task

В Wave 2: достаточно `profile` + `idle` + `working` для 24 archetypes; full 6-state — только для 5 vertical-героев.

### CSS animation: pixelBob

```css
@keyframes pixelBob {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-2px); }
}
.agent-sprite {
  animation: pixelBob 1.6s ease-in-out infinite;
}
```

### Office view по волнам

- **Wave 2 (MVP):** простая сетка карточек агентов с pixel-sprite + pixelBob.
- **Wave 3:** 2D-сцена офиса (агенты на местах, occasional state transitions, message bubbles).
- **Wave 4+:** full interactive office (drag-and-drop layout, scene events).

## Consequences

- Native Canvas — нет bundle-overhead, AI-agents знают наизусть
- 5 vertical-героев + РФ-стилистика = defensible visual brand
- Vertical-герои = signature brand assets для маркетинга

## Marketing positioning

- Primary marketing: «AI-команда для российского бизнеса»
- Pixel Department как secondary supporting фича: «Команда работает прямо на ваших глазах»
- Visual brand: vertical-герои — узнаваемые персонажи на материалах, Telegram-стикерах, лендингах

## Links

- Risks: [R-14](../risks/REGISTER.md), [R-23](../risks/REGISTER.md), [R-24](../risks/REGISTER.md)
- Phase: 02.1 (Pixel Department implementation)
- Related ADRs: ADR-017 (vertical-templates), ADR-021 (AI-asset pipeline detail)
