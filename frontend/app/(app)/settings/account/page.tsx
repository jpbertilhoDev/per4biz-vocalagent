"use client";

import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { RevokeAccountModal } from "@/components/revoke-account-modal";

/**
 * Definições → Conta — dark-first redesign.
 */
export default function SettingsAccountPage() {
  const router = useRouter();
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header
        className="glass-frost sticky top-0 z-10 border-b border-divider px-2 py-3"
        style={{ paddingTop: "max(0.75rem, env(safe-area-inset-top))" }}
      >
        <Button variant="ghost" onClick={() => router.back()} aria-label="Voltar">
          <ArrowLeft className="h-5 w-5" />
          <span>Voltar</span>
        </Button>
      </header>

      <section className="flex-1 space-y-6 px-6 py-6">
        <header>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">
            Conta
          </h1>
          <p className="text-sm text-text-secondary">
            Gere a ligação ao Google e apaga a tua conta do Per4Biz.
          </p>
        </header>

        <div
          aria-labelledby="account-google-heading"
          className="rounded-2xl border border-divider bg-surface-elevated p-6"
        >
          <h2
            id="account-google-heading"
            className="text-base font-semibold text-text-primary"
          >
            Conta Google ligada
          </h2>
          <p className="mt-1 text-sm text-text-secondary">
            O Per4Biz tem acesso de leitura e envio à tua caixa de Gmail.
          </p>

          <dl className="mt-4 grid grid-cols-1 gap-2 text-sm">
            <div className="flex items-center justify-between rounded-lg bg-surface px-3 py-2">
              <dt className="text-text-tertiary">Email</dt>
              <dd className="font-medium text-text-primary">a carregar…</dd>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-surface px-3 py-2">
              <dt className="text-text-tertiary">Estado</dt>
              <dd className="font-medium text-success">Ligada</dd>
            </div>
          </dl>

          <div className="mt-6 flex justify-end">
            <Button
              variant="destructive"
              onClick={() => setModalOpen(true)}
            >
              Desvincular e apagar conta
            </Button>
          </div>
        </div>

        <p className="text-xs text-text-tertiary">
          Ao apagar a conta, revogamos o acesso junto da Google e eliminamos
          todos os dados associados. Esta ação é irreversível.
        </p>
      </section>

      <RevokeAccountModal open={modalOpen} onOpenChange={setModalOpen} />
    </div>
  );
}
