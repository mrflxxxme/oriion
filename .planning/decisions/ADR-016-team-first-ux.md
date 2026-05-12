# ADR-016: Team-first UX — продуктовая абстракция «нанять команду»

- **Status:** Accepted

## Decision

### Product abstraction

Главные external units (что видит пользователь):
- **Team-preset** (e.g. «WB-Селлер команда», «Маркетинг-агентство РФ»)
- **Cell** (= active team workspace после hire)
- **Agent** (sprite + name + role внутри cell)
- **Task** (задача, поставленная команде через Coordinator)

**11 ролей** — внутренняя метадата агентов, НЕ user-facing units.

### Onboarding flow

1. Landing page: Coordinator wizard (3 шага → recommended team-preset)
2. Registration с consent → auto-spawn trial-cell с pre-selected preset
3. Cell содержит N pre-bundled агентов (фиксированные роли + sprites + workflow DAG)
4. Пользователь сразу видит «свою команду» и может ставить задачи

### Pricing units

- **Workspace** = 1 user account, может иметь N cells
- **Cell** = 1 hired team (включает M agents)
- **Agent** = 1 «AI employee» = слот в тарифе

### Role-swap (Wave 3+)

После Wave 3 пользователь сможет:
- Заменить generic Designer на «Senior Designer» (другой sprite + prompt + tools)
- Добавить дополнительного агента в cell (если тариф позволяет)
- Создать custom team-preset (Save current cell as template)

В Wave 0-2: role-swap НЕ доступен. Cell содержит fixed-bundle согласно preset.

### Internal data model

```sql
agents.roles
  role_key (PK)  -- 'researcher', 'writer', 'analyst', ...
  default_system_prompt
  default_tools[]
  recommended_model_tier
  risk_level
  ui_sprite_archetype  -- 'creative01', 'formal05', ...

agents.team_presets
  preset_key (PK)  -- 'wb_seller', 'marketing_agency_ru', ...
  name (i18n keys)
  description (i18n)
  icon_emoji  -- 🛒, 📈, ...
  vertical_tag  -- 'wb_seller', 'agency', 'creator', 'accounting', 'sales'
  agent_bundle[]  -- список {role_key, custom_name, custom_sprite, override_prompt?}
  workflow_dag  -- jsonb workflow definition
  recommended_plan  -- 'team_5' / 'team_15' / 'team_30'
  visibility  -- 'public' / 'beta' / 'archived'

agents.cell_agents  -- Wave 3+ role-swap
  cell_id (FK)
  agent_id (PK)
  name (override от preset default)
  role_key (FK, может быть свапнут в Wave 3+)
  sprite_id (override)
  system_prompt_override (Wave 3+)
  tools_override[] (Wave 3+)
```

## Marketing copy

- Primary: «Наймите AI-команду одним кликом»
- Sub: «Готовые команды для WB-селлеров, маркетинг-агентств, бухгалтерии, sales — выберите и начинайте работать через 3 минуты»

## Consequences

- Wave 0-1 scope проще: нет role-builder UI, нет catalog-of-roles UX
- Mental model для не-технического СМБ: «нанять команду» понятнее чем «собрать команду из ролей»
- Team-presets становятся главным IP-asset продукта (vertical-knowledge encoded в preset)

## Links

- Risk: [R-11](../risks/REGISTER.md) (TTFV/retention)
- Phase: 00.5 (first WB-Селлер team), 01.x (3 vertical-templates), 02.x (5 vertical-templates), 03.x (role-swap)
- Related ADRs: ADR-017 (5 vertical-templates), ADR-022 (Coordinator wizard)
