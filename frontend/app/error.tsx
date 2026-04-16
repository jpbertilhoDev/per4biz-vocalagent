"use client";

import { useEffect } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log to console in dev; in production this would go to Sentry/Axiom
    console.error("[Per4Biz] Unhandled error:", error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-6 text-center">
      <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-error/10 ring-1 ring-error/20">
        <AlertCircle className="h-8 w-8 text-error" strokeWidth={1.5} />
      </div>
      <h1 className="mb-2 text-lg font-semibold text-text-primary">
        Algo correu mal
      </h1>
      <p className="mb-6 max-w-xs text-sm text-text-secondary">
        O Vox encontrou um erro inesperado. Tenta de novo ou recarrega a
        página.
      </p>
      <button
        type="button"
        onClick={reset}
        className="inline-flex items-center gap-2 rounded-2xl bg-primary px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary/90"
      >
        <RefreshCw className="h-4 w-4" />
        Tentar de novo
      </button>
    </div>
  );
}
