import { expect, test } from "@playwright/test";

const BACKEND_ORIGIN = "http://localhost:8000";

const FAKE_EMAILS = {
  emails: [
    {
      id: "m1",
      from_name: "João Silva",
      from_email: "joao@example.com",
      subject: "Proposta nova",
      snippet: "Segue a proposta para a parceria...",
      received_at: "2026-04-15T10:00:00Z",
      is_unread: true,
    },
    {
      id: "m2",
      from_name: "Maria Pinto",
      from_email: "maria@example.com",
      subject: "Reunião amanhã",
      snippet: "Confirmar horário da reunião...",
      received_at: "2026-04-14T14:30:00Z",
      is_unread: false,
    },
    {
      id: "m3",
      from_name: null,
      from_email: "noreply@service.com",
      subject: "Newsletter semanal",
      snippet: "As 10 notícias mais relevantes...",
      received_at: "2026-04-14T08:00:00Z",
      is_unread: false,
    },
  ],
  next_page_token: null,
};

const FAKE_EMAIL_DETAIL = {
  id: "m1",
  from_name: "João Silva",
  from_email: "joao@example.com",
  to_emails: ["jp@per4biz.local"],
  cc_emails: [],
  subject: "Proposta nova",
  snippet: "Segue a proposta para a parceria...",
  body_text: "Bom dia JP,\n\nGostaria de propor uma parceria...\n\nCumprimentos,\nJoão",
  received_at: "2026-04-15T10:00:00Z",
  is_unread: true,
};

test("inbox list → click email → detail → back", async ({ page }) => {
  await page.route(`${BACKEND_ORIGIN}/emails/list*`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(FAKE_EMAILS),
    });
  });

  await page.route(`${BACKEND_ORIGIN}/emails/m1`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(FAKE_EMAIL_DETAIL),
    });
  });

  await page.goto("/inbox");

  // List rendered
  await expect(page.getByText("Caixa de entrada")).toBeVisible();
  await expect(page.getByText("João Silva")).toBeVisible();
  await expect(page.getByText("Maria Pinto")).toBeVisible();
  await expect(page.getByText("Proposta nova")).toBeVisible();

  // Unread count (1 of 3 is unread)
  await expect(page.getByText(/1 não lido/i)).toBeVisible();

  // Click first email
  await page.getByText("João Silva").click();
  await page.waitForURL(/\/email\/m1/);

  // Detail page
  await expect(
    page.getByRole("heading", { name: /proposta nova/i }),
  ).toBeVisible();
  await expect(page.getByText(/bom dia jp/i)).toBeVisible();

  // Back
  await page.getByRole("button", { name: /voltar/i }).click();
  await expect(page).toHaveURL(/\/inbox/);
});

test("inbox empty state shows 'Sem emails'", async ({ page }) => {
  await page.route(`${BACKEND_ORIGIN}/emails/list*`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ emails: [], next_page_token: null }),
    });
  });

  await page.goto("/inbox");
  await expect(page.getByText(/sem emails/i)).toBeVisible();
});
