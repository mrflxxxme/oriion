import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { Textarea } from "./index";

describe("Textarea", () => {
  it("fires onChange while typing", async () => {
    const onChange = vi.fn();
    render(
      <>
        <label htmlFor="bio">Описание</label>
        <Textarea id="bio" onChange={onChange} />
      </>,
    );
    await userEvent.type(screen.getByLabelText("Описание"), "abc");
    expect(onChange).toHaveBeenCalled();
  });

  it("renders a live counter when maxLength is set", () => {
    render(
      <>
        <label htmlFor="note">Заметка</label>
        <Textarea id="note" maxLength={100} value="привет" onChange={() => {}} />
      </>,
    );
    expect(screen.getByText("6/100")).toBeInTheDocument();
  });

  it("invalid sets aria-invalid", () => {
    render(
      <>
        <label htmlFor="msg">Сообщение</label>
        <Textarea id="msg" invalid />
      </>,
    );
    expect(screen.getByLabelText("Сообщение")).toHaveAttribute("aria-invalid", "true");
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <>
        <label htmlFor="comment">Комментарий</label>
        <Textarea id="comment" maxLength={50} value="" onChange={() => {}} />
      </>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
