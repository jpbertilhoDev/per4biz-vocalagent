/**
 * RED tests for <InboxPage> (`app/inbox/page.tsx`).
 *
 * Covers Sprint 1.x · E3 · SPEC §5 UX + §6 AC 2.1, 2.5 (loading / empty / error).
 * The page currently returns null — assertions must fail on missing DOM,
 * not on missing module, until Task 7 GREEN.
 *
 * UI copy in PT-PT; test descriptions in English.
 */
import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQuery } from "./utils/render-with-query";
import { ApiError } from "@/lib/api";
import type { EmailListItem, EmailListResponse } from "@/lib/queries";

// --- Mock next/navigation (EmailItem children call useRouter) --------------
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

// --- Mock listEmails --------------------------------------------------------
vi.mock("@/lib/queries", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/queries")>();
  return { ...actual, listEmails: vi.fn() };
});
import { listEmails } from "@/lib/queries";
import InboxPage from "@/app/(app)/inbox/page";

const listEmailsMock = vi.mocked(listEmails);

function makeEmail(id: string, overrides: Partial<EmailListItem> = {}): EmailListItem {
  return {
    id,
    from_name: `Sender ${id}`,
    from_email: `${id}@example.com`,
    subject: `Subject ${id}`,
    snippet: `Snippet ${id}`,
    received_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    is_unread: false,
    ...overrides,
  };
}

describe("InboxPage", () => {
  beforeEach(() => {
    listEmailsMock.mockReset();
  });

  it("renders loading skeleton while fetching", () => {
    // Never-resolving promise keeps the query in pending state.
    listEmailsMock.mockImplementation(() => new Promise(() => {}));

    renderWithQuery(<InboxPage />);

    const skeletons = screen.getAllByTestId("email-skeleton");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders 3 email items after successful fetch", async () => {
    const response: EmailListResponse = {
      emails: [makeEmail("m1"), makeEmail("m2"), makeEmail("m3")],
      next_page_token: null,
    };
    listEmailsMock.mockResolvedValue(response);

    renderWithQuery(<InboxPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId("email-item")).toHaveLength(3);
    });
  });

  it("renders empty state when no emails", async () => {
    listEmailsMock.mockResolvedValue({ emails: [], next_page_token: null });

    renderWithQuery(<InboxPage />);

    await waitFor(() => {
      expect(screen.getByText(/sem emails/i)).toBeInTheDocument();
    });
  });

  it("renders error state with retry on fetch fail", async () => {
    listEmailsMock.mockRejectedValue(new ApiError(500, "oops"));

    renderWithQuery(<InboxPage />);

    await waitFor(() => {
      // Error surfaced via role=alert OR PT-PT copy.
      const alertByRole = screen.queryByRole("alert");
      const alertByText = screen.queryByText(/não foi possível|erro/i);
      expect(alertByRole ?? alertByText).not.toBeNull();
    });

    // Retry button (PT-PT copy — accept "tentar novamente" or "repetir").
    const retry = screen.queryByRole("button", { name: /tentar novamente|repetir/i });
    expect(retry, "expected a retry button after fetch failure").not.toBeNull();
  });
});
