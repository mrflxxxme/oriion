# ADR-031: Design direction — professional nordic base, pixel as optional skin

- **Status:** **Accepted** (2026-06-13) — accent = **Royal Blue `#2563eb`**; materialized in Phase 00.8.
- **Date:** 2026-06-11 (proposed) · 2026-06-13 (accepted)
- **Deciders:** Founder (grill-session 2026-06-11 + bake-off 2026-06-13), architect, designer

## Context

Phase 00.7 поставила Wave-0 UI на токенах Nordic Warm v0.1.0 (slate + amber-500, dark-first). Founder-ревизия 2026-06-11 после живого прогона зафиксировала два запроса:

1. Базовый внешний вид должен сместиться к **более профессиональной, приглушённой эстетике в духе Claude Code**: глубже тёмный фон, спокойный тёплый акцент вместо яркого «предупреждающего» amber-500, плотность/иерархия экранов по образцу teamly.to (просторный SaaS-layout, явные секции, числовая иерархия).
2. **Pixel Department (ADR-004) переосмысляется**: пиксельные герои и офис остаются фичей Wave 2, но как **опциональный «скин»/режим офиса (opt-in)** — базовый UI и брендинг строго профессиональные. Пиксели не определяют identity бренда.

Constraints: OQ-09 (финальный бренд/имя/домен) остаётся открытым до Wave 2 — это интерим-направление v0.2, не финальный ребрендинг. CI-гейты Phase 00.7 (no-inline-hex grep, no-arbitrary-values grep, 18-export barrel audit) должны остаться зелёными.

## Decision

Принять направление **«professional nordic»** как базовую визуальную идентичность продукта на W0–W2:

1. **Phase 00.8 (Design restyling)** вставляется в Wave 0 после 00.7: рестайлинг значений токенов (палитра/акцент) + полировка 6 существующих экранов по layout-паттернам teamly.to. Архитектура токенов, 18 компонентов, светлая тема и dark-default **не меняются**.
2. **Акцентный цвет выбран внутри Phase 00.8** через live bake-off. ⚠️ **Founder pivot (2026-06-13):** первоначальная рамка «тёплый приглушённый акцент» (терракота/amber) **отклонена** — founder выбрал **более холодную палитру** и **синий бренд-акцент** в духе teamly.to. После второго bake-off (4 cool-blue кандидата, все WCAG-AA проверены) зафиксирован **Royal Blue `#2563eb`**. Канва — углублённый **холодный** slate (не тёплый near-black). См. контраст-таблицу ниже + [UI-SPEC-00.8.md](../ui/UI-SPEC-00.8.md).
3. **Pixel-герои = опциональный скин** (поправка к ADR-004): off by default; пользователь включает «пиксельный офис» сознательно. Маркетинговое позиционирование пикселей понижается с «defensible visual brand» до «memorable opt-in feature». Скоуп ассетов Wave 2 не меняется.

## Resolution (2026-06-13) — accent + WCAG AA contrast table

Final accent: **Royal Blue `#2563eb`** (brand CTA, white text) on a deepened cold-slate canvas
(`bg-page` `#0f172a`→`#0b111e`). Because a saturated blue is dark, the accent splits into two roles
(CTA fill with white text; lighter link/text stop via `cta-hover`); `info` semantic moved blue→cyan
to keep brand-blue unique. Token names/structure unchanged — values only.

| Pairing | Ratio | Gate | Verdict |
|---|---|---|---|
| White on CTA `#2563eb` (dark) | 5.17:1 | ≥4.5 | ✓ AA |
| White on light-CTA `#1d4ed8` | 6.70:1 | ≥4.5 | ✓ AA (on-cta mode-invariant) |
| White on CTA-hover `#1e40af` | 9.7:1 | ≥4.5 | ✓ AA |
| Link `#60a5fa` (`cta-hover` dark) on `#0b111e` | 7.4:1 | ≥4.5 | ✓ AA |
| Link `#1e40af` (`cta-hover` light) on `#f8fafc` | ~9:1 | ≥4.5 | ✓ AA |
| Focus ring `rgba(37,99,235,.4)` | non-text | ≥3 | ✓ |
| Badge primary `#1e40af` on `#dbeafe` | 7.15:1 | ≥4.5 | ✓ |
| Badge info `#0e7490` on `#cffafe` | 4.79:1 | ≥4.5 | ✓ |

Verified live: `gsd-ui-checker` recomputation + axe-core 0 violations on auth routes (smoke spec) +
theme-toggle pass. Full 5-route axe runs on the staging stack (`e2e:live`).

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
