"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { RevokeAccountModal } from "@/components/revoke-account-modal";

/**
 * Ecrã Definições → Conta (SPEC §6).
 * V1: o email real virá de `GET /me` numa task futura (Sprint 2 com TanStack Query).
 * Nesta iteração apresentamos o card estático; o fluxo destrutivo já liga ao backend.
 */
export default function SettingsAccountPage() {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <main
      className="mx-auto flex min-h-screen max-w-xl flex-col gap-6 px-6 py-12"
      style={{ paddingBottom: "max(3rem, env(safe-area-inset-bottom))" }}
    >
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-50">
          Conta
        </h1>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          Gere a ligação ao Google e apaga a tua conta do Per4Biz.
        </p>
      </header>

      <section
        aria-labelledby="account-google-heading"
        className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900"
      >
        <h2
          id="account-google-heading"
          className="text-base font-semibold text-neutral-900 dark:text-neutral-50"
        >
          Conta Google ligada
        </h2>
        <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
          O Per4Biz tem acesso de leitura e envio à tua caixa de Gmail para
          te ajudar a ler e responder por voz.
        </p>

        <dl className="mt-4 grid grid-cols-1 gap-2 text-sm">
          <div className="flex items-center justify-between rounded-lg bg-neutral-50 px-3 py-2 dark:bg-neutral-800/60">
            <dt className="text-neutral-500 dark:text-neutral-400">Email</dt>
            <dd className="font-medium text-neutral-900 dark:text-neutral-100">
              a carregar…
            </dd>
          </div>
          <div className="flex items-center justify-between rounded-lg bg-neutral-50 px-3 py-2 dark:bg-neutral-800/60">
            <dt className="text-neutral-500 dark:text-neutral-400">Estado</dt>
            <dd className="font-medium text-green-700 dark:text-green-400">
              Ligada
            </dd>
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
      </section>

      <p className="text-xs text-neutral-500 dark:text-neutral-500">
        Ao apagar a conta, revogamos o acesso junto da Google e eliminamos
        todos os dados associados. Esta ação é irreversível.
      </p>

      <RevokeAccountModal open={modalOpen} onOpenChange={setModalOpen} />
    </main>
  );
}
