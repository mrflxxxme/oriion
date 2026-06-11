import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { Tabs } from "./index";

function Fixture() {
  return (
    <Tabs defaultValue="overview">
      <Tabs.List aria-label="Разделы">
        <Tabs.Trigger value="overview">Обзор</Tabs.Trigger>
        <Tabs.Trigger value="settings">Настройки</Tabs.Trigger>
      </Tabs.List>
      <Tabs.Content value="overview">Содержимое обзора</Tabs.Content>
      <Tabs.Content value="settings">Содержимое настроек</Tabs.Content>
    </Tabs>
  );
}

describe("Tabs", () => {
  it("shows the default panel", () => {
    render(<Fixture />);
    expect(screen.getByText("Содержимое обзора")).toBeInTheDocument();
    expect(screen.queryByText("Содержимое настроек")).not.toBeInTheDocument();
  });

  it("switches panels on trigger click", async () => {
    render(<Fixture />);
    await userEvent.click(screen.getByRole("tab", { name: "Настройки" }));
    expect(screen.getByText("Содержимое настроек")).toBeInTheDocument();
    expect(screen.queryByText("Содержимое обзора")).not.toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    const { container } = render(<Fixture />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
