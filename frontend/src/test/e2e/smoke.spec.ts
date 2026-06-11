import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * Fast smoke E2E — routes render, FZ-152 consent gate (AC12), dark/light
 * toggle (AC8), and axe has zero serious/critical violations on the public
 * routes (AC7). Needs the frontend + a reachable backend for register/login.
 */

const PASSWORD = "Wave0Demo!Pass12";
function uniqueEmail(): string {
  return `e2e-${String(Date.now())}-${String(Math.floor(performance.now()))}@oriion.dev`;
}

async function expectNoAxeViolations(page: import("@playwright/test").Page) {
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter((v) =>
    ["serious", "critical"].includes(v.impact ?? ""),
  );
  expect(serious, JSON.stringify(serious.map((v) => v.id))).toHaveLength(0);
}

test("login + register routes render with no axe violations", async ({ page }) => {
  await page.goto("/auth/login");
  await expect(page.getByRole("button", { name: /войти/i })).toBeVisible();
  await expectNoAxeViolations(page);

  await page.goto("/auth/register");
  await expect(page.getByRole("button", { name: /зарегистрироваться/i })).toBeVisible();
  await expectNoAxeViolations(page);
});

test("AC12 — register is blocked without the FZ-152 consent", async ({ page }) => {
  await page.goto("/auth/register");
  await page.getByLabel(/email/i).fill(uniqueEmail());
  await page.getByLabel("Пароль", { exact: true }).fill(PASSWORD);
  await page.getByLabel(/подтверждение пароля/i).fill(PASSWORD);
  // Deliberately do NOT check the consent box.
  await page.getByRole("button", { name: /зарегистрироваться/i }).click();
  // Stays on register; a consent validation error is surfaced.
  await expect(page).toHaveURL(/\/auth\/register/);
  await expect(page.getByText(/согласие на обработку персональных данных/i)).toBeVisible();
});

test("AC8 — dark/light theme toggle flips data-theme", async ({ page }) => {
  await page.goto("/auth/login");
  const html = page.locator("html");
  await expect(html).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: /тему/i }).click();
  await expect(html).toHaveAttribute("data-theme", "light");
});

// @backend — needs the live backend for register/login (excluded from CI).
test("@backend register → auto-login lands on the cells route", async ({ page }) => {
  const email = uniqueEmail();
  await page.goto("/auth/register");
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel("Пароль", { exact: true }).fill(PASSWORD);
  await page.getByLabel(/подтверждение пароля/i).fill(PASSWORD);
  // Radix Checkbox renders a role=checkbox button — toggle it via its <label>.
  await page.getByText(/согласен с обработкой персональных данных/i).click();
  await page.getByRole("button", { name: /зарегистрироваться/i }).click();

  await expect(page).toHaveURL(/\/cells/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: /ячейки/i, level: 1 })).toBeVisible();
  await expectNoAxeViolations(page);
});
