/**
 * RED tests for the Welcome / Login screen.
 *
 * Covers Sprint 1 · E1 · SPEC §6 (UX) + §7 (AC-1, AC-2).
 * Current `app/page.tsx` is a disabled stub — these tests must fail authentically
 * (`.toBeEnabled()` fails + navigation/toast assertions fail) until Task 15 GREEN.
 *
 * UI copy in PT-PT; test descriptions in English per JS ecosystem convention.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// --- Mock next/navigation ---------------------------------------------------
// We expose `pushMock` and a mutable `searchParamsValue` so each test can
// configure the URL query string seen by the component.
const pushMock = vi.fn();
let searchParamsValue = new URLSearchParams("");

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    replace: pushMock,
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  useSearchParams: () => searchParamsValue,
  usePathname: () => "/",
}));

// Import after mocks are registered.
import HomePage from "@/app/page";

describe("Welcome page", () => {
  beforeEach(() => {
    pushMock.mockReset();
    searchParamsValue = new URLSearchParams("");
    // Reset any location.href assignments done in previous tests.
    // jsdom permits overriding `window.location.href` via a setter spy.
    window.history.replaceState({}, "", "/");
  });

  it("renders 'Entrar com Google' button with Google G logo", () => {
    render(<HomePage />);

    const button = screen.getByRole("button", { name: /entrar com google/i });
    expect(button).toBeInTheDocument();
    expect(button).toBeEnabled();

    // The button must contain the Google "G" mark. We accept either a
    // dedicated test id or an svg with the Google-specific aria-label.
    const logo =
      screen.queryByTestId("google-g-logo") ??
      button.querySelector('[aria-label*="Google" i]');
    expect(logo).not.toBeNull();
  });

  it("clicking button navigates to /auth/google/start", () => {
    // Capture both router.push(...) calls AND window.location.href = "..."
    // assignments — the Task 15 impl may use either approach.
    const hrefSetter = vi.fn();
    const originalLocation = window.location;
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
      render(<HomePage />);
      const button = screen.getByRole("button", { name: /entrar com google/i });
      fireEvent.click(button);

      const navigatedUrls = [
        ...pushMock.mock.calls.map((c) => String(c[0] ?? "")),
        ...hrefSetter.mock.calls.map((c) => String(c[0] ?? "")),
      ];

      const didNavigate = navigatedUrls.some((url) =>
        /\/auth\/google\/start/.test(url),
      );

      expect(
        didNavigate,
        `expected a navigation to /auth/google/start, got: ${JSON.stringify(
          navigatedUrls,
        )}`,
      ).toBe(true);
    } finally {
      Object.defineProperty(window, "location", {
        configurable: true,
        value: originalLocation,
      });
    }
  });

  it("shows error toast if URL has ?error=access_denied (AC-2)", () => {
    searchParamsValue = new URLSearchParams("error=access_denied");

    render(<HomePage />);

    // AC-2: "Login cancelado — tens de aceitar para usar o Per4Biz"
    // Accept any element with role=alert OR matching text (PT-PT).
    const alertByRole = screen.queryByRole("alert");
    const alertByText = screen.queryByText(/login cancelado/i);

    expect(
      alertByRole ?? alertByText,
      "expected a role=alert or 'Login cancelado' copy to be rendered when ?error=access_denied",
    ).not.toBeNull();
  });
});
