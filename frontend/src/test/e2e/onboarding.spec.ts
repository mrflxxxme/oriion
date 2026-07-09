import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * @live — full Phase 01.12 onboarding flow against the real docker backend with
 * real LLMs: register → 3-step wizard (welcome → pick preset → seed first task)
 * → live SSE progress → artifacts → Dashboard. Drives a genuine orchestration,
 * so the budget is generous (mirrors wave-0-demo.spec.ts).
 *
 * This is the AC evidence for "the full path is traversable e2e without manual
 * steps" + "the wizard routes the chosen preset" + "axe AA on the new surfaces".
 *
 * Run with: npx playwright test onboarding --grep @live
 * (DO NOT run in CI — needs a funded live stack; the runner executes it at
 * server-verify.)
 */

const PASSWORD = "Wave0Demo!Pass12";

async function expectNoAxeViolations(page: import("@playwright/test").Page) {
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter((v) =>
    ["serious", "critical"].includes(v.impact ?? ""),
  );
  expect(serious, JSON.stringify(serious.map((v) => v.id))).toHaveLength(0);
}

test.describe("@live onboarding", () => {
  test.setTimeout(260_000);

  test("register → wizard → first task → artifact → dashboard", async ({ page }) => {
    const email = `e2e-onboarding-${String(Date.now())}@oriion.dev`;

    // 1. Register (auto-login locally; REQUIRE_EMAIL_VERIFICATION=false). The
    //    register flow already auto-spawns a trial cell + grants Trial.
    await page.goto("/auth/register");
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel("Пароль", { exact: true }).fill(PASSWORD);
    await page.getByLabel(/подтверждение пароля/i).fill(PASSWORD);
    await page.getByText(/согласен с обработкой персональных данных/i).click();
    await page.getByRole("button", { name: /зарегистрироваться/i }).click();
    await expect(page).toHaveURL(/\/cells/, { timeout: 15_000 });

    // 2. Enter the onboarding wizard (a first-login surface — reachable via the
    //    /onboarding route). Step 1: welcome. axe the wizard (AC — axe AA).
    await page.goto("/onboarding");
    await expect(page.getByRole("heading", { name: /мастер настройки/i, level: 1 })).toBeVisible();
    await expect(page.getByText(/добро пожаловать/i)).toBeVisible();
    await expectNoAxeViolations(page);
    await page.getByRole("button", { name: /далее/i }).click();

    // 3. Step 2: choose a preset. Use the horizontal "Твои личные ассистенты"
    //    (productivity-core) demo scenario — cheapest live run. Провижн команды
    //    идёт через POST /cells/{cellId}/teams.
    await expect(page.getByText(/выберите команду агентов/i)).toBeVisible();
    await page.getByRole("radio", { name: /твои личные ассистенты/i }).click();
    await expectNoAxeViolations(page); // preset step a11y
    await page.getByRole("button", { name: /продолжить/i }).click();

    // 4. Step 3: the demo prompt is prefilled — submit it as-is.
    await expect(page.getByText(/поставьте первую задачу/i)).toBeVisible();
    await expect(page.getByLabel(/описание задачи/i)).not.toHaveValue("");
    await page.getByRole("button", { name: /запустить задачу/i }).click();

    // 5. Land on the live task-result route; the 3 agent cards render.
    await expect(page).toHaveURL(/\/cells\/[^/]+\/tasks\/[^/]+$/, { timeout: 15_000 });
    await expect(page.getByText("Исследователь")).toBeVisible();
    await expect(page.getByText("Аналитик")).toBeVisible();
    await expect(page.getByText("Райтер")).toBeVisible();

    // 6. Wait for the orchestration to finish — all three agents reach "Готово".
    await expect(page.getByText("Готово")).toHaveCount(3, { timeout: 240_000 });

    // 7. The Результат tab shows the markdown artifact(s).
    await page.getByRole("tab", { name: /результат/i }).click();
    await expect(page.getByRole("region", { name: /итоговый ответ/i })).toBeVisible();

    // 8. Navigate to the Dashboard via the app nav — the recent task + credit
    //    balance summarise the run.
    await page.getByRole("link", { name: /дашборд/i }).click();
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByRole("heading", { name: /дашборд/i, level: 1 })).toBeVisible();
    await expect(page.getByText(/баланс кредитов/i)).toBeVisible();
    // The task the wizard created is tracked in the recent-tasks summary.
    await expect(page.getByText(/недавние задачи/i)).toBeVisible();

    // 9. a11y — zero serious/critical violations on the dashboard.
    await expectNoAxeViolations(page);
  });
});
