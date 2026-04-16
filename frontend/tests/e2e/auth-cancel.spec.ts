import { expect, test } from "@playwright/test";

const BACKEND_ORIGIN = "http://localhost:8000";

test("cancel at consent redirects home with PT-PT alert", async ({ page }) => {
  await page.route(`${BACKEND_ORIGIN}/auth/google/start**`, async (route) => {
    await route.fulfill({
      status: 307,
      headers: {
        location: "http://localhost:3000/?error=access_denied",
      },
      body: "",
    });
  });

  await page.goto("/");
  const button = page.getByRole("button", { name: /entrar com google/i });
  await button.click();

  await page.waitForURL(/error=access_denied/);
  const alert = page.getByRole("alert");
  await expect(alert).toBeVisible();
  await expect(alert).toContainText(/login cancelado/i);
});
