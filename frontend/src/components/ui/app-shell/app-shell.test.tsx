import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { AppShell } from "./index";
import { useThemeStore } from "@/stores/theme";

beforeEach(() => {
  useThemeStore.setState({ theme: "dark" });
});

describe("AppShell", () => {
  it("renders skip-link as first focusable element and main region", () => {
    render(
      <AppShell sidebar={<span>Меню</span>}>
        <p>Контент</p>
      </AppShell>,
    );
    const skip = screen.getByRole("link", { name: "Перейти к содержимому" });
    expect(skip).toHaveAttribute("href", "#main-content");
    expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
    expect(screen.getByRole("navigation", { name: "Основная навигация" })).toBeInTheDocument();
  });

  it("theme toggle flips the theme store", async () => {
    render(<AppShell>контент</AppShell>);
    const toggle = screen.getByRole("button", { name: "Включить светлую тему" });
    await userEvent.click(toggle);
    expect(useThemeStore.getState().theme).toBe("light");
  });

  it("sidebar toggle button fires onSidebarToggle", async () => {
    const onSidebarToggle = vi.fn();
    render(
      <AppShell sidebar={<span>Меню</span>} onSidebarToggle={onSidebarToggle}>
        контент
      </AppShell>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Свернуть меню" }));
    expect(onSidebarToggle).toHaveBeenCalledOnce();
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <AppShell sidebar={<span>Меню</span>} footer={<span>Подвал</span>}>
        <p>Контент</p>
      </AppShell>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
