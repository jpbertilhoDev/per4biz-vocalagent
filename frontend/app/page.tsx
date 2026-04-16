"use client";

/**
 * Welcome / Login screen — dark-first + Vox branding.
 * V1 scope: single-tenant (JP). Ver specs/e1-auth-google-oauth/SPEC.md §6.
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
        <div className="flex flex-col items-center gap-4 text-center">
          <div
            aria-hidden
            className="flex h-20 w-20 items-center justify-center rounded-2xl bg-primary/15 shadow-lg shadow-primary/20"
          >
            <span className="hero-gradient-text text-3xl font-bold">V</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-text-primary">
            Per4Biz
          </h1>
          <p className="text-sm text-text-secondary">
            O teu agente vocal de email. Fala com o Vox.
          </p>
        </div>

        {alertMessage ? (
          <div
            role="alert"
            aria-live="assertive"
            className="w-full rounded-xl border border-error/30 bg-error/10 px-4 py-3 text-center text-sm font-medium text-error"
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
          className="text-center text-xs text-text-tertiary underline underline-offset-2 hover:text-text-secondary"
        >
          Política de privacidade
        </a>
      </div>
    </main>
  );
}

export default function HomePage() {
  return (
    <Suspense fallback={null}>
      <WelcomeContent />
    </Suspense>
  );
}
