"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";
const CONFIRM_PHRASE = "APAGAR";

export interface RevokeAccountModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

/**
 * Destructive modal for `DELETE /me` (SPEC §3 RF-1.4).
 * User must type "APAGAR" (case-sensitive) to enable the submit button.
 * On success: hard redirect to "/" (cookie cleared server-side).
 */
export function RevokeAccountModal({
  open,
  onOpenChange,
  onSuccess,
}: RevokeAccountModalProps) {
  const [typed, setTyped] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset local state whenever the modal is closed so reopening is clean.
  useEffect(() => {
    if (!open) {
      setTyped("");
      setSubmitting(false);
      setError(null);
    }
  }, [open]);

  const canSubmit = typed === CONFIRM_PHRASE && !submitting;

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/me`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      onSuccess?.();
      // Hard redirect — cookie foi limpa pelo backend, qualquer navegação cai em 401.
      window.location.href = "/";
    } catch {
      setError("Ocorreu um erro ao apagar a conta. Tenta novamente.");
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Apagar conta</DialogTitle>
          <DialogDescription>
            Esta ação é irreversível. Todos os teus dados (emails em cache,
            rascunhos, definições) serão apagados e o acesso ao Gmail será
            revogado. Para confirmar, escreve{" "}
            <strong className="font-semibold text-neutral-900 dark:text-neutral-100">
              {CONFIRM_PHRASE}
            </strong>{" "}
            abaixo.
          </DialogDescription>
        </DialogHeader>

        <input
          type="text"
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          placeholder={CONFIRM_PHRASE}
          aria-label="Confirmação"
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-base tracking-wide focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
          disabled={submitting}
        />

        {error && (
          <div
            role="alert"
            className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300"
          >
            {error}
          </div>
        )}

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            Cancelar
          </Button>
          <Button
            variant="destructive"
            onClick={handleSubmit}
            disabled={!canSubmit}
          >
            {submitting ? "A apagar…" : "Desvincular e apagar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
