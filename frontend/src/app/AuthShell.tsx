/**
 * Auth-shell layout — centered card surface for login/register, no app chrome.
 * Includes the theme toggle so the auth screens honour dark/light too.
 */
import { Outlet } from "@tanstack/react-router";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui";
import { useThemeStore } from "@/stores/theme";
import { t } from "@/lib/i18n";

export function AuthShell() {
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggle);

  return (
    <div className="flex min-h-screen flex-col bg-page text-primary">
      <header className="flex h-14 items-center justify-end px-4">
        <Button
          variant="ghost"
          size="icon"
          aria-label={theme === "dark" ? "Включить светлую тему" : "Включить тёмную тему"}
          onClick={toggleTheme}
        >
          {theme === "dark" ? (
            <Sun className="size-5" aria-hidden="true" />
          ) : (
            <Moon className="size-5" aria-hidden="true" />
          )}
        </Button>
      </header>
      <main id="main-content" role="main" className="flex flex-1 items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-bold tracking-tight">{t("common.appName")}</h1>
            <p className="mt-2 text-sm text-secondary">{t("common.tagline")}</p>
          </div>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
