"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Mic, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RecordModal } from "@/components/record-modal";
import { apiFetch } from "@/lib/api";
import { postTranscribe, postPolish } from "@/lib/voice-api";
import type { VoiceTelemetry } from "@/lib/voice-telemetry";

export default function DraftPage() {
  const router = useRouter();
  const params = useSearchParams();

  const initialText = params?.get("text") ?? "";
  const to = params?.get("to") ?? "";
  const subject = params?.get("subject") ?? "";
  const inReplyTo = params?.get("in_reply_to") ?? undefined;

  const [body, setBody] = useState(initialText);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recordOpen, setRecordOpen] = useState(false);
  const [reDictating, setReDictating] = useState(false);

  const handleSend = async () => {
    if (!body.trim() || sending) return;
    setError(null);
    setSending(true);
    try {
      await apiFetch("/emails/send", {
        method: "POST",
        body: JSON.stringify({
          to,
          subject,
          body,
          in_reply_to: inReplyTo ?? null,
        }),
      });
      router.push("/chat?sent=1");
    } catch {
      setError("Não foi possível enviar. Tenta de novo.");
      setSending(false);
    }
  };

  const handleReRecorded = async (blob: Blob, telemetry: VoiceTelemetry) => {
    setReDictating(true);
    setError(null);
    try {
      const transcribed = await postTranscribe(blob, telemetry);
      const polished = await postPolish({
        transcript: transcribed.text,
        from_name: "",
        from_email: to,
        subject,
        body: initialText,
      }, telemetry);
      setBody(polished.polished_text);
    } catch {
      setError("Não foi possível processar a gravação.");
    } finally {
      setReDictating(false);
      void telemetry.flush();
    }
  };

  const canSend = body.trim().length > 0 && !sending;

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

      <section className="flex-1 space-y-4 px-4 py-4">
        <div className="space-y-1 rounded-xl border border-divider bg-surface p-3 text-sm">
          <div>
            <span className="text-text-tertiary">Para:</span>{" "}
            <span className="font-medium text-text-primary">{to}</span>
          </div>
          <div>
            <span className="text-text-tertiary">Assunto:</span>{" "}
            <span className="font-medium text-text-primary">{subject}</span>
          </div>
        </div>

        <label htmlFor="body" className="sr-only">
          Corpo do email
        </label>
        <textarea
          id="body"
          role="textbox"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={12}
          disabled={sending || reDictating}
          className="w-full rounded-xl border border-divider bg-surface p-3 text-base leading-relaxed text-text-primary placeholder:text-text-tertiary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          placeholder="Escreve a tua resposta..."
        />

        {error && (
          <div
            role="alert"
            className="rounded-lg bg-error/10 p-3 text-sm text-error"
          >
            {error}
          </div>
        )}
      </section>

      <footer
        className="glass-frost sticky bottom-0 border-t border-divider p-3"
        style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
      >
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant="ghost"
            size="lg"
            onClick={() => setRecordOpen(true)}
            disabled={sending || reDictating}
          >
            <Mic className="h-5 w-5" />
            {reDictating ? "A processar…" : "Re-ditar"}
          </Button>
          <Button size="lg" onClick={handleSend} disabled={!canSend}>
            <Send className="h-5 w-5" />
            {sending ? "A enviar…" : "Enviar"}
          </Button>
        </div>
      </footer>

      <RecordModal
        open={recordOpen}
        onOpenChange={setRecordOpen}
        onRecorded={handleReRecorded}
      />
    </div>
  );
}
