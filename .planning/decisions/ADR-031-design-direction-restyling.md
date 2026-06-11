# ADR-031: Design direction — professional nordic base, pixel as optional skin

- **Status:** Proposed (акцентный цвет выбирается внутри Phase 00.8; flip → Accepted при exit фазы)
- **Date:** 2026-06-11
- **Deciders:** Founder (grill-session 2026-06-11), architect, designer

## Context

Phase 00.7 поставила Wave-0 UI на токенах Nordic Warm v0.1.0 (slate + amber-500, dark-first). Founder-ревизия 2026-06-11 после живого прогона зафиксировала два запроса:

1. Базовый внешний вид должен сместиться к **более профессиональной, приглушённой эстетике в духе Claude Code**: глубже тёмный фон, спокойный тёплый акцент вместо яркого «предупреждающего» amber-500, плотность/иерархия экранов по образцу teamly.to (просторный SaaS-layout, явные секции, числовая иерархия).
2. **Pixel Department (ADR-004) переосмысляется**: пиксельные герои и офис остаются фичей Wave 2, но как **опциональный «скин»/режим офиса (opt-in)** — базовый UI и брендинг строго профессиональные. Пиксели не определяют identity бренда.

Constraints: OQ-09 (финальный бренд/имя/домен) остаётся открытым до Wave 2 — это интерим-направление v0.2, не финальный ребрендинг. CI-гейты Phase 00.7 (no-inline-hex grep, no-arbitrary-values grep, 18-export barrel audit) должны остаться зелёными.

## Decision

Принять направление **«professional nordic»** как базовую визуальную идентичность продукта на W0–W2:

1. **Phase 00.8 (Design restyling)** вставляется в Wave 0 после 00.7: рестайлинг значений токенов (палитра/акцент) + полировка 6 существующих экранов по layout-паттернам teamly.to. Архитектура токенов, 18 компонентов, светлая тема и dark-default **не меняются**.
2. **Акцентный цвет выбирается внутри Phase 00.8** сравнением 2–3 вариантов на макетах: терракота ≈`#d97757` (Claude-эстетика) vs приглушённый amber vs один дополнительный кандидат. Выбор фиксируется flip-ом этого ADR → Accepted + design-tokens v0.2.0.
3. **Pixel-герои = опциональный скин** (поправка к ADR-004): off by default; пользователь включает «пиксельный офис» сознательно. Маркетинговое позиционирование пикселей понижается с «defensible visual brand» до «memorable opt-in feature». Скоуп ассетов Wave 2 не меняется.

## Consequences

- ✅ Positive: продукт выглядит профессионально для B2B-СМБ ICP до публичной беты; демо для friends (Wave 1) идёт на «взрослом» UI; дешевле менять токены сейчас, чем после 01.5 Dashboard UI.
- ⚠️ Negative / trade-off: +2–3 дня frontend-работы до старта Wave 1; повторная WCAG AA-проверка контраста всей палитры; ADR-004 marketing-positioning ослабляется.
- 🔮 Future: Wave 2 brand refresh (OQ-09) наследует направление вместо выбора с нуля; pixel-скин становится темизацией поверх стабильных структурных токенов.

## Alternatives Considered

| Альтернатива | Pro | Contra | Почему отклонили |
|---|---|---|---|
| Оставить Nordic Warm v0.1.0 как есть до W2 | 0 работы | Яркий amber «предупреждающий», founder недоволен видом перед friends-демо | Внешний вид важен ДО Wave 1 demo |
| Полный ребрендинг сейчас (закрыть OQ-09) | Один проход вместо двух | Имя/домен/финальный бренд не готовы; большой blast radius | OQ-09 осознанно W2 |
| Убрать Pixel Department целиком | Меньше скоупа W2 | Теряем дифференциатор и узнаваемых персонажей для маркетинга | Founder: оставить как opt-in фичу |
| Рестайлинг внутри 01.5 Dashboard UI | Одна UI-фаза | Новый вид появился бы через недели (после 01.1–01.4) | Демо-вид нужен раньше; токены дешевле менять до 01.5 |

## Links

- Phase: [00.8-design-restyling](../roadmap/wave-0-foundation/phases/00.8-design-restyling.md)
- Amends: [ADR-004](./ADR-004-pixel-department.md) (pixel positioning), [ADR-028 DECISION-4 / P-DESIGN-1](./ADR-028-policies-registry.md) (token-change protocol соблюдён: architect + ADR)
- Open question: OQ-09 ([OPEN-QUESTIONS.md](../OPEN-QUESTIONS.md)) — финальный бренд W2
- DS source: [ui/design-tokens.md](../ui/design-tokens.md) (v0.2.0 — Phase 00.8 deliverable)
