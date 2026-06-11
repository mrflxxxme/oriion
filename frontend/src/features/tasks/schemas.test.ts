import { describe, it, expect } from "vitest";
import { taskSubmitSchema, PROMPT_MAX_LENGTH } from "./schemas";

describe("taskSubmitSchema", () => {
  it("accepts a non-empty prompt", () => {
    const result = taskSubmitSchema.safeParse({ prompt: "Сделай market brief" });
    expect(result.success).toBe(true);
  });

  it("rejects an empty prompt", () => {
    const result = taskSubmitSchema.safeParse({ prompt: "" });
    expect(result.success).toBe(false);
  });

  it("rejects a prompt longer than the 4000-char ceiling", () => {
    const result = taskSubmitSchema.safeParse({ prompt: "a".repeat(PROMPT_MAX_LENGTH + 1) });
    expect(result.success).toBe(false);
  });

  it("accepts a prompt at exactly the 4000-char ceiling", () => {
    const result = taskSubmitSchema.safeParse({ prompt: "a".repeat(PROMPT_MAX_LENGTH) });
    expect(result.success).toBe(true);
  });
});
