import type { Config } from "tailwindcss";

/**
 * Tailwind v4 предпочитает CSS-first config (см. ``src/styles/index.css``
 * с ``@theme`` блоком). Этот файл — minimal compatibility shim для
 * IDE-плагинов (Tailwind IntelliSense) и backwards-compat с tools которые
 * всё ещё читают ``tailwind.config.ts``. Все design tokens живут в CSS
 * starting с Phase 00.7 (`src/styles/tokens.css`).
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
} satisfies Config;
