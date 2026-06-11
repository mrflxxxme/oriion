import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import "./styles/index.css";
import { router } from "@/app/router";
import { useAuthStore } from "@/stores/auth";
import { useThemeStore } from "@/stores/theme";
import { authApi } from "@/api/auth";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 5_000, retry: 1, refetchOnWindowFocus: false },
  },
});

/**
 * Best-effort silent session restore on boot. The access token is never
 * persisted, so on reload we only hold a refresh token — calling /users/me
 * triggers apiFetch's 401→refresh→retry path, recovering the session and the
 * user profile. Failure just leaves us logged out.
 */
async function bootstrap(): Promise<void> {
  useThemeStore.getState().setTheme(useThemeStore.getState().theme);
  if (useAuthStore.getState().refreshToken) {
    try {
      const me = await authApi.me();
      useAuthStore.getState().setUser({
        id: me.id,
        email: me.email,
        displayName: me.display_name ?? null,
      });
    } catch {
      useAuthStore.getState().clearSession();
    }
  }
}

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root not found in index.html");
}

void bootstrap().finally(() => {
  createRoot(rootElement).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </StrictMode>,
  );
});
