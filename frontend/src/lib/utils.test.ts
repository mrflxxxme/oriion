import { describe, expect, it } from "vitest";
import { cn } from "./utils";

describe("cn", () => {
  it("merges simple class names", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("filters out falsy values", () => {
    const isActive = false;
    expect(cn("a", isActive && "active", "b")).toBe("a b");
  });

  it("deduplicates conflicting tailwind utilities (later wins)", () => {
    expect(cn("px-4", "px-6")).toBe("px-6");
  });

  it("handles array input", () => {
    expect(cn(["a", "b"], "c")).toBe("a b c");
  });

  it("returns empty string for no input", () => {
    expect(cn()).toBe("");
  });
});
