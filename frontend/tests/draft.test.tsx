/**
 * RED tests for <DraftPage> (`app/email/[id]/draft/page.tsx`).
 *
 * Covers Sprint 2 · E5 · SPEC §5 UX review page + §3 RF-V.8 (draft review + send).
 * Task 10 redirects here with query params { text, to, subject, in_reply_to }.
 * The page currently returns null — Task 12 (GREEN) implements the real UI.
 *
 * UI copy in PT-PT; test descriptions in English per JS ecosystem convention.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// --- Mocks ------------------------------------------------------------------
const pushMock = vi.fn();
const backMock = vi.fn();
const paramsMock = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, back: backMock }),
  useSearchParams: () => paramsMock,
  useParams: () => ({ id: "m1" }),
}));

const apiFetchMock = vi.fn();
vi.mock("@/lib/api", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: class ApiError extends Error {
    status = 0;
    detail = "";
    constructor(status: number, detail: string) {
      super(detail);
      this.status = status;
      this.detail = detail;
    }
  },
}));

import DraftPage from "@/app/email/[id]/draft/page";

function setParams(obj: Record<string, string>) {
  for (const [k, v] of Object.entries(obj)) paramsMock.set(k, v);
}

describe("DraftPage", () => {
  beforeEach(() => {
    pushMock.mockClear();
    backMock.mockClear();
    apiFetchMock.mockReset();
    for (const key of Array.from(paramsMock.keys())) paramsMock.delete(key);
  });

  it("renders pre-populated polished text in textarea", () => {
    setParams({
      text: "Caro João,\n\nObrigado.",
      to: "joao@ex.com",
      subject: "Re: Teste",
      in_reply_to: "m1",
    });

    render(<DraftPage />);

    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    expect(textarea).toBeInTheDocument();
    expect(textarea.value).toBe("Caro João,\n\nObrigado.");

    // Para + Assunto rendered (read-only) in header.
    expect(screen.getByText(/joao@ex\.com/)).toBeInTheDocument();
    expect(screen.getByText(/Re: Teste/)).toBeInTheDocument();
  });

  it("user can edit textarea and value updates", () => {
    setParams({
      text: "Texto original",
      to: "joao@ex.com",
      subject: "Re: Teste",
      in_reply_to: "m1",
    });

    render(<DraftPage />);

    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "Novo texto" } });
    expect(textarea.value).toBe("Novo texto");
  });

  it("clicking Send calls /emails/send and redirects on success", async () => {
    setParams({
      text: "Caro João,\n\nObrigado.",
      to: "joao@ex.com",
      subject: "Re: Teste",
      in_reply_to: "m1",
    });

    apiFetchMock.mockResolvedValue({ message_id: "sent1", thread_id: "t1" });

    render(<DraftPage />);

    const sendBtn = screen.getByRole("button", { name: /enviar/i });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalled();
    });

    const [calledPath, calledInit] = apiFetchMock.mock.calls[0];
    expect(String(calledPath)).toBe("/emails/send");
    expect(calledInit).toMatchObject({ method: "POST" });

    const body = JSON.parse(String(calledInit.body));
    expect(body).toMatchObject({
      to: "joao@ex.com",
      subject: "Re: Teste",
    });
    expect(body.body).toMatch(/^Caro João,/);

    await waitFor(() => {
      const pushed = pushMock.mock.calls.map((c) => String(c[0] ?? ""));
      expect(
        pushed.some((url) => url === "/inbox" || url.startsWith("/inbox?")),
        `expected navigation to "/inbox" after send, got: ${JSON.stringify(
          pushed,
        )}`,
      ).toBe(true);
    });
  });

  it("clicking Send shows error toast on failure", async () => {
    setParams({
      text: "Texto qualquer",
      to: "joao@ex.com",
      subject: "Re: Teste",
      in_reply_to: "m1",
    });

    apiFetchMock.mockRejectedValue(new Error("network error"));

    render(<DraftPage />);

    const sendBtn = screen.getByRole("button", { name: /enviar/i });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      const alert = screen.getByRole("alert");
      expect(alert).toBeInTheDocument();
      expect(alert.textContent ?? "").toMatch(/não foi possível enviar|erro/i);
    });

    expect(pushMock).not.toHaveBeenCalled();
  });
});
