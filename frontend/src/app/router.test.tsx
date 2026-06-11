import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { RouterProvider, createRouter, createMemoryHistory } from "@tanstack/react-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { routeTree } from "./router";
import { useAuthStore } from "@/stores/auth";
import { createTestQueryClient } from "@/test/helpers/createTestQueryClient";

// Keep the cells query deterministic (no real fetch) when the guard lets us in.
vi.mock("@/api/cells", () => ({
  cellsApi: { listAllCells: vi.fn().mockResolvedValue([]) },
}));

function mountAt(initial: string) {
  const router = createRouter({
    routeTree,
    history: createMemoryHistory({ initialEntries: [initial] }),
  });
  render(
    <QueryClientProvider client={createTestQueryClient()}>
      <RouterProvider router={router as never} />
    </QueryClientProvider>,
  );
  return router;
}

describe("app router guard", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
    });
  });

  it("redirects unauthenticated access to /cells → /auth/login", async () => {
    const router = mountAt("/cells");
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/auth/login");
    });
    expect(screen.getByRole("button", { name: /войти/i })).toBeInTheDocument();
  });

  it("renders the cells page when authenticated", async () => {
    useAuthStore.setState({
      accessToken: "a",
      refreshToken: "r",
      isAuthenticated: true,
      user: { id: "1", email: "t@oriion.dev", displayName: null },
    });
    mountAt("/cells");
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /ячейки/i, level: 1 })).toBeInTheDocument();
    });
  });

  it("index redirects to /auth/login when logged out", async () => {
    const router = mountAt("/");
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/auth/login");
    });
  });
});
