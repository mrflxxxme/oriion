/**
 * Vitest setup — extends ``expect`` с jest-dom matchers + cleanup hooks.
 * Подгружается автоматически перед каждым test-файлом per vitest.config.ts.
 */

import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});
