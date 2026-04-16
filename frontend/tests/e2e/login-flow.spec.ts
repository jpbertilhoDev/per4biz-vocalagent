import { expect, test } from "@playwright/test";

/**
 * RED E2E test — Sprint 1 · E1 Task 14.
 * Validates the login CTA is functional. The real OAuth flow is intercepted so
 * we never hit Google from CI — we only assert the button triggers navigation
 * towards `/auth/google/start`.
 *
 * Expected to FAIL in RED because the stub in `app/page.tsx` renders a
 * `disabled` button. Task 15 (GREEN) makes this pass.
 */
test("welcome page shows working login button", async ({ page }) => {
  // Intercept the backend start endpoint so the test stays hermetic.
  await page.route("**/auth/google/start**", (route) =>
    route.fulfill({
      status: 307,
      headers: { location: "/auth/loading" },
      body: "",
    }),
  );

  await page.goto("/");

  const button = page.getByRole("button", { name: /entrar com google/i });
  await expect(button).toBeVisible();
  await expect(button).toBeEnabled();

  await button.click();

  // After click we expect either (a) a navigation away from `/`
  // or (b) a network request to `/auth/google/start`. Either proves the CTA
  // is wired; in RED the button is disabled so we never reach here.
  await expect
    .poll(() => page.url(), { timeout: 5_000 })
    .not.toBe("http://localhost:3000/");
});
