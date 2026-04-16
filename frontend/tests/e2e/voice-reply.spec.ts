import { expect, test } from "@playwright/test";

const BACKEND_ORIGIN = "http://localhost:8000";

const FAKE_EMAIL_DETAIL = {
  id: "m1",
  from_name: "João Silva",
  from_email: "joao@example.com",
  to_emails: ["jp@per4biz.local"],
  cc_emails: [],
  subject: "Reunião amanhã",
  snippet: "Confirmar horário...",
  body_text: "Olá JP, podemos confirmar a reunião de amanhã às 15h?",
  received_at: "2026-04-15T10:00:00Z",
  is_unread: true,
};

test("voice reply full flow: record → polish → edit → send", async ({ page }) => {
  await page.route(`${BACKEND_ORIGIN}/emails/m1`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(FAKE_EMAIL_DETAIL),
    });
  });

  await page.route(`${BACKEND_ORIGIN}/voice/transcribe`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        text: "confirma reunião 15h amanhã",
        language: "pt",
        duration_ms: 3200,
      }),
    });
  });

  await page.route(`${BACKEND_ORIGIN}/voice/polish`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        polished_text:
          "Olá João,\n\nConfirmo a reunião de amanhã às 15h.\n\nCumprimentos",
        model_ms: 920,
      }),
    });
  });

  await page.route(`${BACKEND_ORIGIN}/emails/send`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ message_id: "sent1", thread_id: "t1" }),
    });
  });

  // Stub MediaRecorder before page loads
  await page.addInitScript(() => {
    class FakeMediaRecorder {
      state = "inactive";
      ondataavailable: ((e: { data: Blob }) => void) | null = null;
      onstop: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(public stream: MediaStream, public options?: { mimeType: string }) {}
      start() {
        this.state = "recording";
      }
      stop() {
        this.state = "inactive";
        const blob = new Blob([new Uint8Array([1, 2, 3])], { type: "audio/webm" });
        setTimeout(() => {
          this.ondataavailable?.({ data: blob });
          this.onstop?.();
        }, 50);
      }
      static isTypeSupported() {
        return true;
      }
    }
    // @ts-expect-error stub
    window.MediaRecorder = FakeMediaRecorder;
    Object.defineProperty(navigator, "mediaDevices", {
      value: {
        getUserMedia: async () => ({
          getTracks: () => [{ stop: () => undefined }],
        }),
      },
      configurable: true,
    });
  });

  await page.goto("/email/m1");
  await expect(
    page.getByRole("heading", { name: /reunião amanhã/i }),
  ).toBeVisible();

  // Click "Responder" → opens record modal → auto-stops via mock
  await page.getByRole("button", { name: /responder/i }).click();
  await page.getByRole("button", { name: /parar/i }).click();

  // After transcribe + polish, navigates to /draft with polished text
  await page.waitForURL(/\/email\/m1\/draft/);
  const textarea = page.getByRole("textbox");
  await expect(textarea).toHaveValue(/confirmo a reunião/i);

  // Edit
  await textarea.fill("Olá João,\n\nConfirmo a reunião. Até amanhã!\n\nJP");

  // Send
  await page.getByRole("button", { name: /^enviar/i }).click();
  await page.waitForURL(/\/inbox/);
  expect(page.url()).toContain("sent=1");
});
