"use client";

/**
 * Auth loading splash — redirects to /chat (chat-first home).
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AuthLoadingPage() {
  const router = useRouter();

  useEffect(() => {
    const timer = setTimeout(() => {
      router.replace("/chat");
    }, 2000);
    return () => clearTimeout(timer);
  }, [router]);

  return (
    <main
      role="status"
      aria-live="polite"
      aria-label="A preparar o Vox"
      className="flex min-h-screen flex-col items-center justify-center gap-6 px-6"
      style={{ paddingBottom: "max(3rem, env(safe-area-inset-bottom))" }}
    >
      <div
        aria-hidden
        className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/15 shadow-lg shadow-primary/20"
      >
        <span className="hero-gradient-text text-2xl font-bold">V</span>
      </div>
      <div className="flex flex-col items-center gap-3">
        <Spinner />
        <p className="text-sm text-text-secondary">
          A preparar o Vox…
        </p>
      </div>
    </main>
  );
}

function Spinner() {
  return (
    <svg
      className="h-8 w-8 animate-spin text-primary"
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
