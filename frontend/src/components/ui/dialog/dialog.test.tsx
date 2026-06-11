import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { Dialog } from "./index";

function ControlledDialog({ onOpenChange }: { onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open onOpenChange={onOpenChange}>
      <Dialog.Content>
        <Dialog.Header>
          <Dialog.Title>Удалить ячейку</Dialog.Title>
          <Dialog.Description>Это действие необратимо.</Dialog.Description>
        </Dialog.Header>
        <Dialog.Body>Содержимое будет удалено навсегда.</Dialog.Body>
      </Dialog.Content>
    </Dialog>
  );
}

describe("Dialog", () => {
  it("renders title + description inside role=dialog when open", () => {
    render(<ControlledDialog onOpenChange={vi.fn()} />);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(screen.getByText("Удалить ячейку")).toBeVisible();
    expect(screen.getByText("Это действие необратимо.")).toBeVisible();
  });

  it("wires aria-labelledby and aria-describedby (Radix)", () => {
    render(<ControlledDialog onOpenChange={vi.fn()} />);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-labelledby");
    expect(dialog).toHaveAttribute("aria-describedby");
  });

  it("close button requests close via onOpenChange", async () => {
    const onOpenChange = vi.fn();
    render(<ControlledDialog onOpenChange={onOpenChange} />);
    await userEvent.click(screen.getByRole("button", { name: "Закрыть" }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("Esc requests close via onOpenChange", async () => {
    const onOpenChange = vi.fn();
    render(<ControlledDialog onOpenChange={onOpenChange} />);
    await userEvent.keyboard("{Escape}");
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("has no axe violations", async () => {
    const { baseElement } = render(<ControlledDialog onOpenChange={vi.fn()} />);
    expect(await axe(baseElement)).toHaveNoViolations();
  });
});
