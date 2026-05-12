# ADR-021: AI-generated pixel-asset pipeline + 5 vertical-героев hand-drawn

- **Status:** Accepted

## Decision

### AI-generated baseline (24 archetypes)

**Тех. стек:**
- **SDXL Base 1.0** или **Flux.1-dev** (выбор по качеству на тестах)
- **Pixel-Art-XL LoRA** (community model, MIT-friendly license)
- **ComfyUI** workflow (визуальный pipeline)
- **Aseprite** для post-processing (manual cleanup + animation frames)
- **Hardware:** local M-series Mac / RTX 4070+, либо Yandex DataSphere GPU (Tesla T4/A100)

**Workflow:**
```
1. Master prompt template (consistent across archetypes):
   "pixel art, 32x32 character sprite, [archetype] office worker, 
    front-facing, [details], retro 16-bit style, transparent background"
2. Iteration: ~10 prompts per archetype для best result
3. Aseprite cleanup: chromatic noise removal, edge sharpening
4. Animation: 4-frame idle loop (subtle head bob + blink)
5. Export: PNG sprite-sheet (32×32 per frame, 4 frames × 32px = 128×32 strip)
```

**24 archetypes:**

| ID | Archetype | Стиль |
|---|---|---|
| `creative01-08` | Casual creative | Хипстер, дизайнер, художник |
| `formal01-05` | Suit/professional | Бизнесмен, юрист, бухгалтер |
| `hoodie01-04` | Tech/casual | Разработчик, исследователь |
| `casual01-04` | Generic office | Менеджер, ассистент |
| `service01-03` | Service/support | Customer support, sales |

Generic naming (для reuse в разных team-presets), РФ-стилизация в окружении (см. ADR-004).

**Бюджет:** ~$200-500 compute + 20 часов работы dev/artist на pipeline. Total: ~$1K.

### 5 vertical-героев (hand-drawn)

| Vertical-герой | Привязка к template | Использование |
|---|---|---|
| **Селлер-Маркус** | WB-Селлер / Ozon-Селлер | Тематические Telegram-стикеры, маркетинг материалы |
| **SMM-Анастасия** | Маркетинг-агентство РФ | Лендинг агентств, content marketing |
| **Крейтор-Денис** | Telegram-крейтор / Курс-автор | Креатор-комьюнити маркетинг |
| **Бухгалтер-Анна** | ИП-Бухгалтерия | Партнёрство с Контур/Тинькофф |
| **Sales-Дмитрий** | СМБ-Sales | Партнёрство с Bitrix24/amoCRM |

**Specs per герой:**
- Pixel-art 64×64 (выше resolution чем generic, для signature look)
- 6 anim states (profile / idle / working / thinking / success / waving)
- Sprite-sheet: 64×64 × 6 states × 4 frames = 384×64 strip
- РФ-стилизация (Селлер-Маркус с кружкой «WB», Бухгалтер-Анна с пачкой 1С-документов, и т.д.)
- Лицензия: full ownership (work-for-hire contract)

**Подрядчик:** freelance artist через FL.ru / Хабр Карьера / Кворк.
- Бюджет: $400-1000 per герой × 5 = $2-5K total
- Срок: ~3 недели от concept до final
- Approach: тендер с 3-5 кандидатами → выбор best style fit → contract

### Asset pipeline (Wave 2 Phase 02.1)

```
1. Generate generic archetypes (AI) — 1 неделя
2. Подбор freelance artist для героев — 1 неделя (параллельно с 1)
3. Hand-drawn героев — 2-3 недели (параллельно с других phases)
4. Asset deployment в Yandex Object Storage:
   /assets/agents/<id>/profile.png
   /assets/agents/<id>/idle.png  
   /assets/agents/<id>/working.png
   ...
5. Canvas renderer (React component) — 3-5 дней
```

### Asset versioning

URL: `/api/assets/agents/<id>/<state>.png?v=<version>`
- Immutable (cache-control max-age=31536000, immutable)
- Version bump при изменении asset
- Old versions сохраняются (legacy clients продолжают работать)

### Storage

- **Yandex Object Storage** (S3-compat, рублёвая оплата)
- **CDN-fronting:** Yandex Cloud CDN с edge-cache (~50-100ms TTFB по РФ)
- Total storage: ~50-100 MB baseline + ~50 MB героев = ~200 MB

### License & legal

- AI-generated assets проходят через legal-review для каждого выпуска
  - Pixel-Art-XL LoRA — проверяем training data origin
  - Generated assets — наша собственность
  - Manual cleanup (Aseprite) добавляет creative-input → strengthens copyright position
- Hand-drawn vertical-герои: explicit work-for-hire contract (full IP transfer)
- Trademark консультация: проверка vertical-героев на conflict с existing brands (Роспатент search)

## Wave 3+ asset roadmap

- **Wave 3:** +5 vertical-героев (расширение к новым vertical-templates)
- **Wave 4:** Полный upgrade ключевых archetypes через профессионального pixel-artist (если revenue позволяет) — ~$10-15K
- **Wave 5+:** Open marketplace UGC sprites под лицензией (community-driven)

## Links

- Risks: [R-14](../risks/REGISTER.md), [R-23](../risks/REGISTER.md), [R-24](../risks/REGISTER.md)
- Phase: 02.1 (Pixel Department implementation)
- Related ADRs: ADR-004 (Pixel architecture), ADR-017 (vertical-героев привязка к templates)
