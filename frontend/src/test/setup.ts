/**
 * Vitest setup — extends ``expect`` с jest-dom matchers + cleanup hooks.
 * Подгружается автоматически перед каждым test-файлом per vitest.config.ts.
 */

import "@testing-library/jest-dom/vitest";
import { afterEach, expect } from "vitest";
import { cleanup } from "@testing-library/react";
import { toHaveNoViolations } from "jest-axe";

// jest-axe matcher for component-level a11y assertions (AC7 / REVIEW-CHECKLIST §C).
expect.extend(toHaveNoViolations);

// jsdom doesn't implement scrollTo — TanStack Router's scroll restoration calls
// it on navigation. Stub to keep test output clean.
if (typeof window !== "undefined") {
  window.scrollTo = () => {};
}

afterEach(() => {
  cleanup();
});
