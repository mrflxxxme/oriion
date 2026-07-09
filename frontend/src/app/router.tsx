/**
 * Code-based TanStack Router tree (phase-spec amendment: code-based instead of
 * the file-based codegen toolchain — avoids the router vite-plugin while
 * satisfying every AC; the 5 demo routes + index redirect + cell detail).
 *
 * Tree:
 *   /                              → redirect (auth ? /cells : /auth/login)
 *   /auth/login, /auth/register    → AuthShell (no app chrome)
 *   [app guard] AppLayout
 *     /cells
 *     /cells/$cellId
 *     /cells/$cellId/tasks/new
 *     /cells/$cellId/tasks/$taskId
 */
import {
  createRootRoute,
  createRoute,
  createRouter,
  redirect,
  Outlet,
} from "@tanstack/react-router";
import { Toaster } from "@/components/ui";
import { useAuthStore } from "@/stores/auth";
import { AppLayout } from "./AppLayout";
import { AuthShell } from "./AuthShell";
import { LoginPage } from "@/features/auth/LoginPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { CellsListPage } from "@/features/cells/CellsListPage";
import { CellDetailPage } from "@/features/cells/CellDetailPage";
import { TaskSubmitPage } from "@/features/tasks/TaskSubmitPage";
import { TaskResultPage } from "@/features/tasks/TaskResultPage";
import { MemoryPanelPage } from "@/features/memory/MemoryPanelPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { OnboardingPage } from "@/features/onboarding/OnboardingPage";

const rootRoute = createRootRoute({
  component: () => (
    <>
      <Outlet />
      <Toaster />
    </>
  ),
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  beforeLoad: () => {
    // TanStack Router signals navigation by throwing a redirect (not an Error).
    // eslint-disable-next-line @typescript-eslint/only-throw-error
    throw redirect({ to: useAuthStore.getState().isAuthenticated ? "/cells" : "/auth/login" });
  },
});

// --- Auth area (no app chrome) ---
const authLayoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "auth",
  component: AuthShell,
});
const loginRoute = createRoute({
  getParentRoute: () => authLayoutRoute,
  path: "/auth/login",
  component: LoginPage,
});
const registerRoute = createRoute({
  getParentRoute: () => authLayoutRoute,
  path: "/auth/register",
  component: RegisterPage,
});

// --- Authenticated app area ---
const appLayoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "app",
  component: AppLayout,
  beforeLoad: () => {
    if (!useAuthStore.getState().isAuthenticated) {
      // eslint-disable-next-line @typescript-eslint/only-throw-error
      throw redirect({ to: "/auth/login" });
    }
  },
});
const cellsRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/cells",
  component: CellsListPage,
});
const cellDetailRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/cells/$cellId",
  component: CellDetailPage,
});
const taskNewRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/cells/$cellId/tasks/new",
  component: TaskSubmitPage,
});
const taskResultRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/cells/$cellId/tasks/$taskId",
  component: TaskResultPage,
});
const memoryRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/memory",
  component: MemoryPanelPage,
});
const dashboardRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/dashboard",
  component: DashboardPage,
});
const onboardingRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/onboarding",
  component: OnboardingPage,
});

export const routeTree = rootRoute.addChildren([
  indexRoute,
  authLayoutRoute.addChildren([loginRoute, registerRoute]),
  appLayoutRoute.addChildren([
    cellsRoute,
    cellDetailRoute,
    taskNewRoute,
    taskResultRoute,
    memoryRoute,
    dashboardRoute,
    onboardingRoute,
  ]),
]);

export const router = createRouter({
  routeTree,
  defaultPreload: "intent",
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
