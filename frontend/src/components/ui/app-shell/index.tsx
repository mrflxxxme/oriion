/**
 * AppShell — top-level application chrome (component-inventory.md #1).
 * Skip-link → header (with theme toggle) → sidebar nav → main → footer.
 */
import { forwardRef, useState } from "react";
import type { ReactNode } from "react";
import { Menu, Moon, Sun } from "lucide-react";
import { useThemeStore } from "@/stores/theme";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface AppShellProps {
  children: ReactNode;
  header?: ReactNode;
  sidebar?: ReactNode;
  footer?: ReactNode;
  sidebarCollapsed?: boolean;
  onSidebarToggle?: () => void;
  density?: "comfortable" | "compact";
  className?: string;
}

export const AppShell = forwardRef<HTMLDivElement, AppShellProps>(function AppShell(
  {
    children,
    header,
    sidebar,
    footer,
    sidebarCollapsed = false,
    onSidebarToggle,
    density = "comfortable",
    className,
  },
  ref,
) {
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggle);
  const mainPadding = density === "compact" ? "p-4" : "p-6";

  // Mobile nav state: controlled via onSidebarToggle if provided, else internal.
  const [mobileOpenInternal, setMobileOpenInternal] = useState(false);
  const isControlled = onSidebarToggle !== undefined;
  const mobileOpen = isControlled ? !sidebarCollapsed : mobileOpenInternal;
  const toggleMobile = () => {
    if (isControlled) onSidebarToggle();
    else setMobileOpenInternal((open) => !open);
  };

  return (
    <div ref={ref} className={cn("flex min-h-screen flex-col bg-page text-primary", className)}>
      {/* First focusable element — skip directly to the main content region. */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-toast focus:rounded-md focus:bg-surface focus:px-4 focus:py-2 focus:text-primary focus:shadow-focus-ring"
      >
        Перейти к содержимому
      </a>

      <header className="flex h-14 items-center justify-between gap-2 border-b border-default bg-surface px-4">
        <div className="flex items-center gap-2">
          {sidebar ? (
            <Button
              variant="ghost"
              size="icon"
              aria-label={mobileOpen ? "Свернуть меню" : "Развернуть меню"}
              aria-expanded={mobileOpen}
              aria-controls="app-mobile-nav"
              onClick={toggleMobile}
              className="md:hidden"
            >
              <Menu className="size-5" aria-hidden="true" />
            </Button>
          ) : null}
          {header}
        </div>
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

      {/* Mobile nav — disclosed by the hamburger below md. Rendered only when
          open so the (display:none) desktop nav isn't a duplicate landmark. */}
      {sidebar && mobileOpen ? (
        <nav
          id="app-mobile-nav"
          aria-label="Основная навигация"
          className="border-b border-default bg-surface md:hidden"
        >
          {sidebar}
        </nav>
      ) : null}

      <div className="flex flex-1">
        {sidebar ? (
          <nav
            aria-label="Основная навигация"
            className="hidden shrink-0 border-r border-default bg-surface md:flex md:flex-col md:w-64"
          >
            {sidebar}
          </nav>
        ) : null}

        <main id="main-content" role="main" className={cn("flex-1", mainPadding)}>
          {children}
        </main>
      </div>

      {footer ? (
        <footer className="border-t border-default bg-surface px-4 py-3 text-sm text-secondary">
          {footer}
        </footer>
      ) : null}
    </div>
  );
});
