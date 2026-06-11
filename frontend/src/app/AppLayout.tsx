/**
 * Authenticated app chrome — wraps the cells/tasks subtree in the AppShell
 * with a sidebar nav + logout. Auth pages render outside this layout.
 */
import { Outlet, useNavigate, Link } from "@tanstack/react-router";
import { LayoutGrid } from "lucide-react";
import { AppShell, Button } from "@/components/ui";
import { useAuthStore } from "@/stores/auth";
import { authApi } from "@/api/auth";
import { t } from "@/lib/i18n";

export function AppLayout() {
  const navigate = useNavigate();
  const refreshToken = useAuthStore((s) => s.refreshToken);
  const clearSession = useAuthStore((s) => s.clearSession);

  async function handleLogout() {
    try {
      if (refreshToken) await authApi.logout(refreshToken);
    } catch {
      // best-effort revoke; clear locally regardless
    }
    clearSession();
    void navigate({ to: "/auth/login" });
  }

  return (
    <AppShell
      header={
        <Button variant="ghost" size="sm" onClick={() => void handleLogout()}>
          {t("common.logout")}
        </Button>
      }
      sidebar={
        // AppShell already provides the <nav> landmark — just the links here.
        <div className="flex flex-col gap-1 p-4">
          <Link
            to="/cells"
            className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-secondary hover:bg-page hover:text-primary [&.active]:bg-page [&.active]:text-primary"
          >
            <LayoutGrid className="size-4" aria-hidden="true" />
            {t("cells.title")}
          </Link>
        </div>
      }
    >
      <Outlet />
    </AppShell>
  );
}
