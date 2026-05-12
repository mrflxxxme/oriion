# 04 — Pixel Department: deep-dive

## Краткий вердикт

**Pixel Department у teamly.to реализован максимально просто:**
- НЕ PixiJS, НЕ Phaser, НЕ Three.js, НЕ WebGL.
- Native HTML `<canvas>` 2D Context.
- PNG sprite-sheet per agent per animation-state.
- CSS `@keyframes pixelBob` для idle bounce.
- Никакой game engine — это просто красиво нарисованные PNG в canvas-обёртке.

Это **важный insight** для нашего roadmap: можно достичь похожего wow-эффекта без heavy frontend stack.

## Tech ingredients

| Слой | Implementation | Источник |
|---|---|---|
| Sprite source | PNG sheets per agent + state | `/api/assets/agents/<id>/<state>.png?v=<ver>` |
| Canvas | Native `<canvas>` 2D, retina (2× internal resolution) | `canvas.width=320, style.width=160` |
| Smoothing | `imageSmoothingEnabled: true, imageSmoothingQuality: 'low'` | naked canvas defaults overridden |
| CSS image-rendering | `auto` (default) | not `pixelated` — they want slight smoothing |
| Animation tween | CSS `@keyframes pixelBob` (translateY -2px on 50%) | global stylesheet |
| Interactivity | `pointer-events-none select-none` on canvas | parent button handles clicks |
| Font | Press Start 2P (Google Fonts) | retro labels everywhere |

## Sprite asset model

URL pattern: `/api/assets/agents/<agent_id>/<state>.png?v=<version>`

- `<agent_id>` — текстовый ID (e.g. `creative01`, `formal01`, `hoodie07`, `oliver-goals`)
- `<state>` — `profile`, `idle`, `writing`, и т.д.
- `<version>` — для cache-busting (e.g. `v=1`, `v=2`)
- Content-Type: `image/png`
- Size: до **13.5 MB** (наблюдали `formal01-writing/idle.png`)
- Cache-Control: `public, max-age=31536000, immutable` (год кеширование)

Такой размер PNG указывает на **многокадровый sprite-sheet** или **высокое разрешение per frame**:
- Если 24 frames × 256×256 каждый = ~24 МБ декомпрессированных пикселей, ~3-5 МБ PNG ≠ совпадает.
- Если 64 frames × 320×320 = ~80 MB декомпрессированных, ~10-15 МБ PNG ≈ совпадает. **Скорее всего: ~32-64 кадра анимации.**

## Agent identifier conventions

Наблюдаемые ID:
- `creative01` … `creative11` (12 шт., generic "creative" archetype — для Marketing/Content roles)
- `hoodie07` (developer/casual look)
- `formal01` … `formal05` (suit/professional — для Coordinator, Sales)
- `<name>-<role>`: `oliver-goals`, `josh-morning`, `maksim-calendar`, `zoya-journal`, `hana-recruiter`, `kai-screener`, `emma-onboarding`, `finn-peopleops`, `oscar-voice`, `marta-factcheck`, `eugene-stylist`, `ivan-designer`, `orchestra-health`, `pulse-health`, `nutra-health`, `labreader-health`

Notable: некоторые ID не numeric, а semantic — указывает на ручную дизайн-курацию каждого «именного» персонажа.

## Canvas count breakdown (landing page)

После загрузки `/` (unauthenticated landing с How-it-works + Pricing sections):
- **41 canvases** одновременно
- Группировка по размеру:
  - 320×320: 3 (hero-sized agents, e.g. main Coordinator)
  - 180×180: 2
  - 160×160: 3
  - 140×140: 12
  - 90×90: 3
  - 70×70: 18 (thumbnail-sized)

Очевидно: каждый pixel-art аватар на странице рендерится в свой canvas. Это лёгкий tradeoff — DOM становится «тяжёлым», но позволяет per-element CSS-animation (pixelBob), который не работал бы для single full-page canvas.

## Animation states (sprite naming convention)

Из observed URLs:
- `profile` — статичный портрет (для каталога, settings, sidebar avatar)
- `idle` — base loop animation (medium energy)
- `writing` — задача-specific (e.g. Writer agent typing)

Гипотеза, что в полном production-каталоге существуют состояния:
- `idle`, `walking`, `talking`, `thinking`, `writing`, `working`, `coffee`, `waving`, `success`, `error`
- Каждое — отдельный PNG sprite-sheet
- Switching между состояниями — JavaScript меняет `image src` или `canvas.drawImage` от нового источника

## CSS animation: pixelBob

```css
@keyframes pixelBob {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-2px); }
}
```

- Длительность не извлечена (likely ~1s ease-in-out infinite)
- Применяется на canvas-wrapper (не на canvas — иначе бы redraw блокировал animation)
- Это даёт «дышащий» эффект, без переписывания pixel-data — чисто CSS transform

## Canvas drawing loop (reconstructed)

Не имея исходников, гипотеза:

```js
// Pseudocode
const canvas = ref.current;
const ctx = canvas.getContext('2d');
const sprite = new Image();
sprite.src = `/api/assets/agents/${agentId}/${state}.png`;

sprite.onload = () => {
  const fps = 12;
  const frames = totalFrames; // depends on sheet
  const frameW = sprite.width / framesX;
  const frameH = sprite.height / framesY;
  
  let frame = 0;
  const draw = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const sx = (frame % framesX) * frameW;
    const sy = Math.floor(frame / framesX) * frameH;
    ctx.drawImage(sprite, sx, sy, frameW, frameH, 0, 0, canvas.width, canvas.height);
    frame = (frame + 1) % frames;
  };
  
  setInterval(draw, 1000 / fps);
};
```

Возможно используется `requestAnimationFrame` для лучшего фрейм-рейта.

## Office view (Pixel Department полностью)

Office view не показывался (требует активной cell). Из общего смысла: вероятно, при активной cell `/office` показывает 2D-сцену с агентами на «рабочих местах» — но никаких следов sprite-движения по позициям мы не видели. Возможно:
- Простая grid с per-agent canvas (как на landing)
- Все агенты «работают на своих местах», без обхода офиса
- Status indicators (online/working/thinking) меняют sprite state

## Wow-factor delta vs effort

Pixel Department в реализации teamly.to — **medium effort, high impact**:

| Effort | Что нужно |
|---|---|
| Low | CSS keyframes (pixelBob) |
| Low | Native canvas 2D API |
| Low | PNG sprite-sheets (статичные ассеты) |
| **HIGH** | **Pixel-art design** — ручное рисование 24+ frame анимаций per agent per state |
| **HIGH** | **Asset pipeline** — преобразование, optimization, deployment |

Самая дорогая часть — **художник пиксель-арт + animator**. Технология тривиальная.

## Hi-DPI / Retina handling

`<canvas width=2× style.width=1×>` — стандартный паттерн для retina-screen рендеринга. Канвас отрисовывается в 2× плотности, CSS показывает в 1×.

Smoothing `imageSmoothingQuality: 'low'` — компромисс: пиксели не quite crisp (как в `image-rendering: pixelated`), но и не чрезмерно blurred. Эстетически удачный middle ground для retro+modern fusion.

## Reusable findings для нашего roadmap

1. **Можно начать с native canvas — не обязательно PixiJS на Wave 2.** Это упрощает frontend stack и снижает требования к найму PixiJS-эксперта (R-09 из risks).
2. **Sprite-asset pipeline = главный bottleneck.** Нужен либо штатный pixel-art artist, либо подрядчик. Это операционная подготовка задолго до Wave 2.
3. **CSS-only анимации могут заместить heavy game engine** для простых эффектов (bob, fade, slide).
4. **Bundle size economy** — отказ от PixiJS экономит ~500KB JS. Pure canvas + PNG = optimal.

См. также: `RECONSTRUCTION-NOTES.md` для финальной рекомендации по нашему ADR-004.
