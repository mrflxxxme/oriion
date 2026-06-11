/**
 * Theme store — dark/light mode toggle (Nordic Warm, dark-first).
 *
 * Persists the choice to localStorage and reflects it as a `data-theme`
 * attribute on `<html>` so themes.css can flip every semantic surface.
 * Per design-tokens.md §2.4 + §10.3 (dark default for night-shift operators).
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "dark" | "light";

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggle: () => void;
}

/** Apply the theme to the document root (no-op in non-DOM environments). */
export function applyTheme(theme: Theme): void {
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-theme", theme);
  }
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "dark",
      setTheme: (theme) => {
        applyTheme(theme);
        set({ theme });
      },
      toggle: () => {
        const next: Theme = get().theme === "dark" ? "light" : "dark";
        applyTheme(next);
        set({ theme: next });
      },
    }),
    {
      name: "oriion-theme",
      onRehydrateStorage: () => (state) => {
        // Reflect the persisted choice onto <html> once hydrated.
        if (state) applyTheme(state.theme);
      },
    },
  ),
);
