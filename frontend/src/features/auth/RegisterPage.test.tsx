import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { renderWithRouter } from "@/test/helpers/renderWithProviders";
import { useAuthStore } from "@/stores/auth";
import { RegisterPage } from "./RegisterPage";

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
    register: vi.fn(),
    login: vi.fn(),
    me: vi.fn(),
  },
}));

import { authApi } from "@/api/auth";

const mockRegister = vi.mocked(authApi.register);
const mockLogin = vi.mocked(authApi.login);
const mockMe = vi.mocked(authApi.me);

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.getState().clearSession();
});

describe("RegisterPage", () => {
  it("renders labelled fields", async () => {
    renderWithRouter(<RegisterPage />, { path: "/auth/register" });
    expect(await screen.findByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Пароль")).toBeInTheDocument();
    expect(screen.getByLabelText("Подтверждение пароля")).toBeInTheDocument();
    expect(
      screen.getByRole("checkbox", {
        name: "Согласен с обработкой персональных данных (ФЗ-152)",
      }),
    ).toBeInTheDocument();
  });

  it("shows field errors (aria-invalid) on empty submit", async () => {
    renderWithRouter(<RegisterPage />, { path: "/auth/register" });
    await userEvent.click(await screen.findByRole("button", { name: "Зарегистрироваться" }));

    await waitFor(() => {
      expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
    });
    expect(screen.getByLabelText("Пароль")).toHaveAttribute("aria-invalid", "true");
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("blocks submit when the ФЗ-152 consent is unchecked (AC12)", async () => {
    renderWithRouter(<RegisterPage />, { path: "/auth/register" });
    await userEvent.type(await screen.findByLabelText("Email"), "user@example.com");
    await userEvent.type(screen.getByLabelText("Пароль"), "supersecret12");
    await userEvent.type(screen.getByLabelText("Подтверждение пароля"), "supersecret12");
    // Leave consent unchecked.
    await userEvent.click(screen.getByRole("button", { name: "Зарегистрироваться" }));

    await waitFor(() => {
      expect(
        screen.getByText("Необходимо согласие на обработку персональных данных"),
      ).toBeInTheDocument();
    });
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("registers + auto-logs-in on a fully valid submit", async () => {
    mockRegister.mockResolvedValue({
      user_id: "u1",
      workspace_id: "w1",
      cell_id: "c1",
      email: "user@example.com",
    });
    mockLogin.mockResolvedValue({
      access_token: "acc",
      refresh_token: "ref",
      expires_in: 3600,
      token_type: "bearer",
    });
    mockMe.mockResolvedValue({ id: "u1", email: "user@example.com", display_name: null });

    renderWithRouter(<RegisterPage />, { path: "/auth/register" });
    await userEvent.type(await screen.findByLabelText("Email"), "user@example.com");
    await userEvent.type(screen.getByLabelText("Пароль"), "supersecret12");
    await userEvent.type(screen.getByLabelText("Подтверждение пароля"), "supersecret12");
    await userEvent.click(
      screen.getByRole("checkbox", {
        name: "Согласен с обработкой персональных данных (ФЗ-152)",
      }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Зарегистрироваться" }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledTimes(1);
    });
    expect(mockRegister).toHaveBeenCalledWith(
      expect.objectContaining({
        email: "user@example.com",
        password: "supersecret12",
        consent_pdn: true,
      }),
    );
    await waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
    });
  });

  it("has no axe violations", async () => {
    const { container } = renderWithRouter(<RegisterPage />, { path: "/auth/register" });
    await screen.findByLabelText("Email");
    expect(await axe(container)).toHaveNoViolations();
  });
});
