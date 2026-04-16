"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000, // 60s — evita refetch ao montar
            gcTime: 5 * 60_000, // 5min cache
            retry: (failureCount, error) => {
              // Não tenta de novo em 401
              if ((error as { status?: number })?.status === 401) return false;
              return failureCount < 2;
            },
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
