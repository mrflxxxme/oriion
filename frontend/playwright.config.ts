import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E config (Phase 00.7).
 *
 * Runs against the Vite dev server (which proxies /api → the local docker
 * backend on :8000). The full Wave-0 demo spec is tagged @live and drives a
 * real ~90-170s LLM orchestration — keep it out of fast/unit CI lanes.
 *
 * Smoke specs (routes render, FZ-152 consent, dark/light) need only the
 * frontend + a reachable backend for auth, and run quickly.
 */
export default defineConfig({
  testDir: "./src/test/e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
