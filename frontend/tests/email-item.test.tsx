/**
 * RED tests for <EmailItem>.
 *
 * Covers Sprint 1.x · E3 · SPEC §5 UX (email row) + §6 AC 2.1, 2.3.
 * The component is currently a stub returning null — these tests must fail
 * on assertions (not on import / module resolution) until Task 7 GREEN.
 *
 * UI copy in PT-PT; test descriptions in English per JS ecosystem convention.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { EmailListItem } from "@/lib/queries";

// --- Mock next/navigation ---------------------------------------------------
const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    replace: pushMock,
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

// Import after mocks are registered.
import { EmailItem } from "@/components/email-item";

function makeEmail(overrides: Partial<EmailListItem> = {}): EmailListItem {
  // 2 hours before "now" — formatRelativeTime should render "há 2h".
  const twoHoursAgoIso = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
  return {
    id: "m1",
    from_name: "João Silva",
    from_email: "joao@example.com",
    subject: "Proposta comercial",
    snippet: "Segue a proposta em anexo...",
    received_at: twoHoursAgoIso,
    is_unread: false,
    ...overrides,
  };
}

describe("EmailItem", () => {
  beforeEach(() => {
    pushMock.mockReset();
  });

  it("renders from_name, subject, snippet and formatted time", () => {
    const email = makeEmail();
    render(<EmailItem email={email} />);

    expect(screen.getByText(/João Silva/)).toBeInTheDocument();
    expect(screen.getByText(/Proposta comercial/)).toBeInTheDocument();
    expect(screen.getByText(/Segue a proposta em anexo/)).toBeInTheDocument();
    // Accept "há 2h", "há 2 h" — both valid PT-PT formats.
    expect(screen.getByText(/há\s?\d+\s?h/i)).toBeInTheDocument();
  });

  it("shows unread indicator only when is_unread=true", () => {
    const { unmount } = render(<EmailItem email={makeEmail({ is_unread: true })} />);
    expect(screen.getByTestId("unread-dot")).toBeInTheDocument();
    unmount();

    render(<EmailItem email={makeEmail({ is_unread: false })} />);
    expect(screen.queryByTestId("unread-dot")).toBeNull();
  });

  it("clicking item navigates to /email/:id", () => {
    render(<EmailItem email={makeEmail({ id: "abc123" })} />);

    // Root may be a <button> or an element with role="button" / data-testid.
    const target =
      screen.queryByRole("button") ??
      screen.queryByTestId("email-item");
    expect(
      target,
      "expected EmailItem root to be a button or have data-testid='email-item'",
    ).not.toBeNull();

    fireEvent.click(target as HTMLElement);

    expect(pushMock).toHaveBeenCalledWith("/email/abc123");
  });
});
