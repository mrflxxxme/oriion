import type { ReactElement, ReactNode } from "react";
import { render, type RenderResult } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import {
  RouterProvider,
  createRootRoute,
  createRoute,
  createRouter,
  createMemoryHistory,
  Outlet,
} from "@tanstack/react-router";
import { createTestQueryClient } from "./createTestQueryClient";

/** Wrap children in a QueryClientProvider only (no router). */
export function renderWithQuery(ui: ReactElement): RenderResult {
  const client = createTestQueryClient();
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

/**
 * Mount a component at a route inside a real (memory-history) router + query
 * provider — use for components that call useNavigate / render <Link>.
 */
export function renderWithRouter(
  ui: ReactNode,
  options: { path?: string; initialEntry?: string } = {},
): RenderResult {
  const path = options.path ?? "/";
  const client = createTestQueryClient();
  const rootRoute = createRootRoute({ component: () => <Outlet /> });
  const route = createRoute({ getParentRoute: () => rootRoute, path, component: () => <>{ui}</> });
  const router = createRouter({
    routeTree: rootRoute.addChildren([route]),
    history: createMemoryHistory({ initialEntries: [options.initialEntry ?? path] }),
  });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router as never} />
    </QueryClientProvider>,
  );
}
