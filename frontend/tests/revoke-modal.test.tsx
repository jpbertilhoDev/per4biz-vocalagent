/**
 * RED tests for the Revoke Account Modal.
 *
 * Covers Sprint 1 · E1 · SPEC §3 RF-1.4 (revoke) + §6 Definições/Conta screen.
 * The double-confirm typing "APAGAR" is a destructive-safety requirement (UX spec).
 *
 * UI copy in PT-PT; test descriptions in English per JS ecosystem convention.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RevokeAccountModal } from "@/components/revoke-account-modal";

describe("RevokeAccountModal", () => {
  const originalFetch = global.fetch;
  const originalLocation = window.location;

  beforeEach(() => {
    vi.restoreAllMocks();
    // Restore a clean fetch / location before each test; individual tests re-mock.
    global.fetch = originalFetch;
    Object.defineProperty(window, "location", {
      configurable: true,
      value: originalLocation,
    });
  });

  it("submit button is disabled until user types 'APAGAR' exactly", () => {
    const onOpenChange = vi.fn();
    render(<RevokeAccountModal open={true} onOpenChange={onOpenChange} />);

    const submit = screen.getByRole("button", {
      name: /desvincular e apagar/i,
    });
    const input = screen.getByLabelText(/confirma/i) as HTMLInputElement;

    // Initially disabled (empty input).
    expect(submit).toBeDisabled();

    // Lowercase must NOT enable the button — phrase is case-sensitive.
    fireEvent.change(input, { target: { value: "apagar" } });
    expect(submit).toBeDisabled();

    // Exact phrase enables the button.
    fireEvent.change(input, { target: { value: "APAGAR" } });
    expect(submit).toBeEnabled();
  });

  it("submit calls DELETE /me with credentials and redirects on success", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    global.fetch = fetchMock as unknown as typeof fetch;

    // Capture window.location.href assignments.
    const hrefSetter = vi.fn();
    Object.defineProperty(window, "location", {
      configurable: true,
      value: {
        ...originalLocation,
        assign: hrefSetter,
        replace: hrefSetter,
        set href(value: string) {
          hrefSetter(value);
        },
        get href() {
          return originalLocation.href;
        },
      },
    });

    try {
      const onOpenChange = vi.fn();
      render(<RevokeAccountModal open={true} onOpenChange={onOpenChange} />);

      const input = screen.getByLabelText(/confirma/i);
      fireEvent.change(input, { target: { value: "APAGAR" } });

      const submit = screen.getByRole("button", {
        name: /desvincular e apagar/i,
      });
      fireEvent.click(submit);

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledTimes(1);
      });

      const [calledUrl, calledInit] = fetchMock.mock.calls[0];
      expect(String(calledUrl)).toMatch(/\/me$/);
      expect(calledInit).toMatchObject({
        method: "DELETE",
        credentials: "include",
      });

      await waitFor(() => {
        const navigatedUrls = hrefSetter.mock.calls.map((c) => String(c[0] ?? ""));
        expect(
          navigatedUrls.some((url) => url === "/" || url.startsWith("/?")),
          `expected navigation to "/" after successful revoke, got: ${JSON.stringify(
            navigatedUrls,
          )}`,
        ).toBe(true);
      });
    } finally {
      Object.defineProperty(window, "location", {
        configurable: true,
        value: originalLocation,
      });
    }
  });

  it("shows error alert on failed revoke and keeps modal open", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 500 });
    global.fetch = fetchMock as unknown as typeof fetch;

    const onOpenChange = vi.fn();
    render(<RevokeAccountModal open={true} onOpenChange={onOpenChange} />);

    const input = screen.getByLabelText(/confirma/i);
    fireEvent.change(input, { target: { value: "APAGAR" } });

    const submit = screen.getByRole("button", {
      name: /desvincular e apagar/i,
    });
    fireEvent.click(submit);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    // PT-PT error copy surfaced via role=alert; modal stays open (onOpenChange not called with false).
    await waitFor(() => {
      const alert = screen.getByRole("alert");
      expect(alert).toBeInTheDocument();
      expect(alert.textContent ?? "").toMatch(/erro|tenta novamente/i);
    });

    // Modal was not programmatically closed.
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });

  it("cancel button closes modal without calling DELETE", () => {
    const fetchMock = vi.fn();
    global.fetch = fetchMock as unknown as typeof fetch;

    const onOpenChange = vi.fn();
    render(<RevokeAccountModal open={true} onOpenChange={onOpenChange} />);

    const cancel = screen.getByRole("button", { name: /cancelar/i });
    fireEvent.click(cancel);

    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
