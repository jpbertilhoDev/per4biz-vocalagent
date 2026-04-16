"use client";

/**
 * Auth loading splash (Sprint 1 · E1).
 * Intermediário opcional entre OAuth callback e /inbox.
 * Ver specs/e1-auth-google-oauth/SPEC.md §6.
 *
 * Client component porque precisa de setTimeout + router.replace().
 * router.replace (não push) para não poluir histórico.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AuthLoadingPage() {
  const router = useRouter();

  useEffect(() => {
    const timer = setTimeout(() => {
      router.replace("/inbox");
    }, 2000);
    return () => clearTimeout(timer);
  }, [router]);

  return (
    <main
      role="status"
      aria-live="polite"
      aria-label="A preparar a tua caixa de email"
      className="flex min-h-screen flex-col items-center justify-center gap-6 px-6"
      style={{ paddingBottom: "max(3rem, env(safe-area-inset-bottom))" }}
    >
      <div
        aria-hidden
        className="h-16 w-16 rounded-2xl bg-[#0A84FF] shadow-lg"
      />
      <div className="flex flex-col items-center gap-3">
        <Spinner />
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          A preparar a tua caixa…
        </p>
      </div>
    </main>
  );
}

function Spinner() {
  return (
    <svg
      className="h-8 w-8 animate-spin text-[#0A84FF]"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
      />
    </svg>
  );
}
