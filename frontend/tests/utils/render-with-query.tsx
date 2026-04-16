/**
 * Test helper — wraps `render` with a fresh QueryClient per call so TanStack
 * Query hooks work in isolation without state leaking between tests.
 *
 * Retries are disabled to make error-state assertions deterministic; gcTime and
 * staleTime are zero so re-renders always re-fetch.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions, type RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";

export function renderWithQuery(
  ui: ReactElement,
  options?: RenderOptions,
): RenderResult & { queryClient: QueryClient } {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
    },
  });

  const result = render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
    options,
  );

  return { ...result, queryClient };
}
