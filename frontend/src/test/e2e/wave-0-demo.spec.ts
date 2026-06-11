import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * @live — full Wave-0 demo flow against the real docker backend with real LLMs.
 * Drives a genuine ~90-170s orchestration, so the test budget is generous.
 * This is the AC3 (end-to-end) + AC7 (a11y across visited routes) evidence.
 *
 * Run with: npx playwright test wave-0-demo --grep @live
 */

const PASSWORD = "Wave0Demo!Pass12";

async function expectNoAxeViolations(page: import("@playwright/test").Page) {
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter((v) =>
    ["serious", "critical"].includes(v.impact ?? ""),
  );
  expect(serious, JSON.stringify(serious.map((v) => v.id))).toHaveLength(0);
}

test.describe("@live Wave-0 demo", () => {
  test.setTimeout(260_000);

  test("register → cell → submit Market-brief → SSE progress → 3 artifacts", async ({ page }) => {
    const email = `e2e-live-${String(Date.now())}@oriion.dev`;

    // 1. Register (auto-login locally; REQUIRE_EMAIL_VERIFICATION=false).
    await page.goto("/auth/register");
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel("Пароль", { exact: true }).fill(PASSWORD);
    await page.getByLabel(/подтверждение пароля/i).fill(PASSWORD);
    await page.getByText(/согласен с обработкой персональных данных/i).click();
    await page.getByRole("button", { name: /зарегистрироваться/i }).click();

    // 2. Land on the cells list — the user has exactly one auto-provisioned cell.
    await expect(page).toHaveURL(/\/cells/, { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: /ячейки/i, level: 1 })).toBeVisible();

    // 3. Open the cell, then go to the new-task form (axe both routes — AC7).
    await page.locator("table tbody tr").first().getByRole("link").first().click();
    await expect(page).toHaveURL(/\/cells\/[^/]+$/);
    await expectNoAxeViolations(page); // cell detail route
    await page.getByRole("link", { name: /новая задача/i }).click();
    await expect(page).toHaveURL(/\/tasks\/new$/);
    await expectNoAxeViolations(page); // task submit route

    // 4. Use the «Маркет-бриф» preset, then submit.
    await page.getByRole("button", { name: /маркет-бриф/i }).click();
    await expect(page.getByRole("textbox")).not.toHaveValue("");
    await page.getByRole("button", { name: /создать задачу/i }).click();

    // 5. Land on the result route; the 3 agent cards render.
    await expect(page).toHaveURL(/\/cells\/[^/]+\/tasks\/[^/]+$/, { timeout: 15_000 });
    await expect(page.getByText("Исследователь")).toBeVisible();
    await expect(page.getByText("Аналитик")).toBeVisible();
    await expect(page.getByText("Райтер")).toBeVisible();

    // 6. Wait for the orchestration to finish — all three agents reach "Готово".
    await expect(page.getByText("Готово")).toHaveCount(3, { timeout: 240_000 });

    // 7. The Результат tab shows the three markdown artifacts.
    await page.getByRole("tab", { name: /результат/i }).click();
    const region = page.getByRole("region", { name: /итоговый ответ/i });
    await expect(region).toBeVisible();
    await expect(page.getByRole("heading", { name: /матрица исследования/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /бриф и контент-план/i })).toBeVisible();

    // 8. a11y — zero serious/critical violations on the result page.
    const results = await new AxeBuilder({ page }).analyze();
    const serious = results.violations.filter((v) =>
      ["serious", "critical"].includes(v.impact ?? ""),
    );
    expect(serious, JSON.stringify(serious.map((v) => v.id))).toHaveLength(0);
  });
});
