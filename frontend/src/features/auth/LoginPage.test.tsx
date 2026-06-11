import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { renderWithRouter } from "@/test/helpers/renderWithProviders";
import { useAuthStore } from "@/stores/auth";
import { LoginPage } from "./LoginPage";

// jsdom lacks ResizeObserver; Radix Checkbox's bubble input needs it. Without
// this stub the page crashes into the router CatchBoundary and renders nothing.
vi.stubGlobal(
  "ResizeObserver",
  class {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  },
);

vi.mock("@/api/auth", () => ({
  authApi: {
    login: vi.fn(),
    me: vi.fn(),
  },
}));

import { authApi } from "@/api/auth";

const mockLogin = vi.mocked(authApi.login);
const mockMe = vi.mocked(authApi.me);

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.getState().clearSession();
});

describe("LoginPage", () => {
  it("renders labelled email and password fields", async () => {
    renderWithRouter(<LoginPage />, { path: "/auth/login" });
    expect(await screen.findByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Пароль")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Войти" })).toBeInTheDocument();
  });

  it("shows validation errors (aria-invalid) when submitting an empty form", async () => {
    renderWithRouter(<LoginPage />, { path: "/auth/login" });
    await userEvent.click(await screen.findByRole("button", { name: "Войти" }));

    await waitFor(() => {
      expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
    });
    expect(screen.getByLabelText("Пароль")).toHaveAttribute("aria-invalid", "true");
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it("calls the API and persists a session on valid submit", async () => {
    mockLogin.mockResolvedValue({
      access_token: "acc",
      refresh_token: "ref",
      expires_in: 3600,
      token_type: "bearer",
    });
    mockMe.mockResolvedValue({ id: "u1", email: "user@example.com", display_name: "Ada" });

    renderWithRouter(<LoginPage />, { path: "/auth/login" });
    await userEvent.type(await screen.findByLabelText("Email"), "user@example.com");
    await userEvent.type(screen.getByLabelText("Пароль"), "supersecret12");
    await userEvent.click(screen.getByRole("button", { name: "Войти" }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("user@example.com", "supersecret12");
    });
    await waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
    });
    expect(useAuthStore.getState().user).toEqual({
      id: "u1",
      email: "user@example.com",
      displayName: "Ada",
    });
  });

  it("has no axe violations", async () => {
    const { container } = renderWithRouter(<LoginPage />, { path: "/auth/login" });
    await screen.findByLabelText("Email");
    expect(await axe(container)).toHaveNoViolations();
  });
});
