import "vitest";

// Augment vitest's expect with the jest-axe matcher wired in setup.ts.
declare module "vitest" {
  interface Assertion {
    toHaveNoViolations(): void;
  }
  interface AsymmetricMatchersContaining {
    toHaveNoViolations(): void;
  }
}
