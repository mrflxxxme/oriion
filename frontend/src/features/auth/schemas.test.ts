import { describe, it, expect } from "vitest";
import { loginSchema, registerSchema } from "./schemas";

const validRegister = {
  email: "user@example.com",
  password: "supersecret12",
  passwordConfirm: "supersecret12",
  consentPdn: true,
} as const;

describe("loginSchema", () => {
  it("accepts a valid email + password", () => {
    const result = loginSchema.safeParse({ email: "a@b.com", password: "x" });
    expect(result.success).toBe(true);
  });

  it("rejects an invalid email", () => {
    const result = loginSchema.safeParse({ email: "not-an-email", password: "x" });
    expect(result.success).toBe(false);
  });

  it("rejects an empty password", () => {
    const result = loginSchema.safeParse({ email: "a@b.com", password: "" });
    expect(result.success).toBe(false);
  });
});

describe("registerSchema", () => {
  it("accepts a fully valid payload", () => {
    expect(registerSchema.safeParse(validRegister).success).toBe(true);
  });

  it("rejects when consentPdn is not true (AC12 — ФЗ-152)", () => {
    const result = registerSchema.safeParse({ ...validRegister, consentPdn: false });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes("consentPdn"))).toBe(true);
    }
  });

  it("rejects a password shorter than 12 chars", () => {
    const result = registerSchema.safeParse({
      ...validRegister,
      password: "short1",
      passwordConfirm: "short1",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes("password"))).toBe(true);
    }
  });

  it("rejects a mismatched password confirmation", () => {
    const result = registerSchema.safeParse({
      ...validRegister,
      passwordConfirm: "differentpass12",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes("passwordConfirm"))).toBe(true);
    }
  });
});
