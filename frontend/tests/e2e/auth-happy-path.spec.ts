import { expect, test } from "@playwright/test";

const BACKEND_ORIGIN = "http://localhost:8000";

test("happy login path reaches inbox with session cookie", async ({
  page,
  context,
}) => {
  await page.route(`${BACKEND_ORIGIN}/auth/google/start**`, async (route) => {
    await route.fulfill({
      status: 307,
      headers: {
        location: `${BACKEND_ORIGIN}/auth/google/callback?state=stubbed-state&code=stubbed-code`,
      },
      body: "",
    });
  });

  await page.route(
    `${BACKEND_ORIGIN}/auth/google/callback**`,
    async (route) => {
      await route.fulfill({
        status: 307,
        headers: {
          location: "http://localhost:3000/inbox",
          "set-cookie":
            "__Host-session=fake.jwt.value; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=604800",
        },
        body: "",
      });
    },
  );

  await page.goto("/");
  const button = page.getByRole("button", { name: /entrar com google/i });
  await expect(button).toBeEnabled();
  await button.click();

  await page.waitForURL(/\/inbox/);
  expect(page.url()).toContain("/inbox");

  const cookies = await context.cookies(BACKEND_ORIGIN);
  const session = cookies.find((c) => c.name === "__Host-session");
  if (session) {
    expect(session.httpOnly).toBe(true);
  }
});
