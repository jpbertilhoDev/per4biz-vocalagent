"use client";

/**
 * Welcome / Login screen (Sprint 1 · E1 · AC-1, AC-2).
 * V1 scope: single-tenant (JP). Ver specs/e1-auth-google-oauth/SPEC.md §6.
 *
 * PT-PT copy. Client component porque precisa de:
 *   - useSearchParams (?error=access_denied)
 *   - window.location.href para OAuth redirect (fora do Next router)
 */

import { useSearchParams } from "next/navigation";
import { useEffect, useState, Suspense } from "react";
import { Button } from "@/components/ui/button";
import { GoogleGLogo } from "@/components/google-g-logo";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

function WelcomeContent() {
  const params = useSearchParams();
  const error = params?.get("error") ?? null;
  const [alertMessage, setAlertMessage] = useState<string | null>(null);

  useEffect(() => {
    if (error === "access_denied") {
      setAlertMessage(
        "Login cancelado — tens de aceitar para usar o Per4Biz.",
      );
    } else {
      setAlertMessage(null);
    }
  }, [error]);

  const handleLogin = () => {
    // OAuth fluxo: redireciona para backend FastAPI (/auth/google/start)
    // fora do router Next (URL absoluto em prod, relativo em dev).
    const loginUrl = `${API_URL}/auth/google/start`;
    window.location.href = loginUrl;
  };

  return (
    <main
      className="flex min-h-screen flex-col items-center justify-center px-6 py-12"
      style={{
        paddingBottom: "max(3rem, env(safe-area-inset-bottom))",
      }}
    >
      <div className="flex w-full max-w-sm flex-col items-center gap-8">
        <div className="flex flex-col items-center gap-3 text-center">
          <div
            aria-hidden
            className="h-16 w-16 rounded-2xl bg-[#0A84FF] shadow-lg"
          />
          <h1 className="text-3xl font-bold tracking-tight">Per4Biz</h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Copiloto vocal de email. Responde falando.
          </p>
        </div>

        {alertMessage ? (
          <div
            role="alert"
            aria-live="assertive"
            className="w-full rounded-xl border border-[#FF3B30]/30 bg-[#FF3B30]/10 px-4 py-3 text-center text-sm font-medium text-[#FF3B30]"
          >
            {alertMessage}
          </div>
        ) : null}

        <Button
          type="button"
          size="lg"
          className="w-full"
          onClick={handleLogin}
          aria-label="Entrar com Google"
        >
          <GoogleGLogo className="h-5 w-5" />
          Entrar com Google
        </Button>

        <a
          href="/privacy"
          className="text-center text-xs text-neutral-500 underline underline-offset-2 hover:text-neutral-700 dark:hover:text-neutral-300"
        >
          Política de privacidade
        </a>
      </div>
    </main>
  );
}

export default function HomePage() {
  // Suspense boundary exigido por useSearchParams no App Router (Next 15+).
  return (
    <Suspense fallback={null}>
      <WelcomeContent />
    </Suspense>
  );
}
