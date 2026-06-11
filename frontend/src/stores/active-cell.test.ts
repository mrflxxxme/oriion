import { describe, it, expect, beforeEach } from "vitest";
import { useActiveCellStore } from "./active-cell";

describe("useActiveCellStore", () => {
  beforeEach(() => {
    useActiveCellStore.setState({ activeCellId: null });
  });

  it("starts with no active cell", () => {
    expect(useActiveCellStore.getState().activeCellId).toBeNull();
  });

  it("sets the active cell id", () => {
    useActiveCellStore.getState().setActiveCell("c1");
    expect(useActiveCellStore.getState().activeCellId).toBe("c1");
  });

  it("clears the active cell id", () => {
    useActiveCellStore.getState().setActiveCell("c1");
    useActiveCellStore.getState().setActiveCell(null);
    expect(useActiveCellStore.getState().activeCellId).toBeNull();
  });
});
