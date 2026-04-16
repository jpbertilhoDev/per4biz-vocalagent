"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft, Mic, Volume2 } from "lucide-react";

import { emailsKeys, getEmail } from "@/lib/queries";
import { formatRelativeTime } from "@/lib/relative-time";
import { Button } from "@/components/ui/button";
import { RecordModal } from "@/components/record-modal";
import { fetchTTS, postPolish, postTranscribe } from "@/lib/voice-api";

type ProcessingState = "idle" | "tts" | "transcribe" | "polish";

export default function EmailDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id =
    typeof params?.id === "string"
      ? params.id
      : Array.isArray(params?.id)
        ? params.id[0]
        : "";

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: emailsKeys.detail(id),
    queryFn: () => getEmail(id),
    enabled: Boolean(id),
  });

  const [recordOpen, setRecordOpen] = useState(false);
  const [processing, setProcessing] = useState<ProcessingState>("idle");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  const revokeAudio = useCallback(() => {
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = "";
      }
      revokeAudio();
    };
  }, [revokeAudio]);

  const handleBack = () => {
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
    } else {
      router.push("/inbox");
    }
  };

  const handlePlay = async () => {
    if (!data || typeof window === "undefined") return;
    setVoiceError(null);
    setProcessing("tts");
    try {
      const text = `${data.subject}. ${data.body_text}`.slice(0, 4000);
      const audioBlob = await fetchTTS(text);
      revokeAudio();
      const url = URL.createObjectURL(audioBlob);
      audioUrlRef.current = url;
      if (audioRef.current) {
        audioRef.current.src = url;
        audioRef.current.onended = () => {
          revokeAudio();
        };
        await audioRef.current.play();
      } else {
        const audio = new Audio(url);
        audio.onended = () => {
          revokeAudio();
        };
        audioRef.current = audio;
        await audio.play();
      }
    } catch {
      setVoiceError("Não foi possível ouvir o email.");
    } finally {
      setProcessing("idle");
    }
  };

  const handleRecorded = async (blob: Blob) => {
    if (!data) return;
    setVoiceError(null);
    try {
      setProcessing("transcribe");
      const transcribed = await postTranscribe(blob);
      setProcessing("polish");
      const polished = await postPolish({
        transcript: transcribed.text,
        from_name: data.from_name ?? "",
        from_email: data.from_email,
        subject: data.subject,
        body: data.body_text,
      });
      const text = encodeURIComponent(polished.polished_text);
      const to = encodeURIComponent(data.from_email);
      const subject = encodeURIComponent(`Re: ${data.subject}`);
      const inReplyTo = encodeURIComponent(data.id);
      router.push(
        `/email/${data.id}/draft?text=${text}&to=${to}&subject=${subject}&in_reply_to=${inReplyTo}`
      );
    } catch {
      setVoiceError("Não foi possível processar a gravação.");
    } finally {
      setProcessing("idle");
    }
  };

  const isBusy = processing !== "idle";

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header
        className="glass-frost sticky top-0 z-10 border-b border-divider px-2 py-3"
        style={{ paddingTop: "max(0.75rem, env(safe-area-inset-top))" }}
      >
        <Button variant="ghost" size="default" onClick={handleBack} aria-label="Voltar">
          <ArrowLeft className="h-5 w-5" />
          <span>Voltar</span>
        </Button>
      </header>

      <section
        className="flex-1 px-4 py-6"
        style={{ paddingBottom: "max(2rem, env(safe-area-inset-bottom))" }}
      >
        {isLoading && <DetailSkeleton />}

        {isError && (
          <div
            role="alert"
            className="rounded-xl bg-error/10 p-4 text-sm text-error"
          >
            <p className="mb-3">Não foi possível carregar o email.</p>
            <Button variant="destructive" size="sm" onClick={() => refetch()}>
              Tentar novamente
            </Button>
          </div>
        )}

        {data && (
          <article className="space-y-4">
            <header className="space-y-1">
              <h1 className="text-xl font-bold tracking-tight text-text-primary">
                {data.subject || "(sem assunto)"}
              </h1>
              <p className="text-sm font-medium text-text-primary">
                {data.from_name ?? data.from_email}
              </p>
              {data.from_name && (
                <p className="text-xs text-text-tertiary">{data.from_email}</p>
              )}
              <p className="text-xs text-text-tertiary">
                {formatRelativeTime(data.received_at)}
              </p>
            </header>
            <div className="whitespace-pre-wrap break-words text-sm leading-relaxed text-text-secondary">
              {data.body_text || "(sem conteúdo)"}
            </div>
          </article>
        )}
      </section>

      {data && (
        <footer
          className="glass-frost sticky bottom-0 border-t border-divider p-3"
          style={{
            paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))",
          }}
        >
          {voiceError && (
            <div
              role="alert"
              className="mb-2 rounded-lg bg-error/10 p-2 text-xs text-error"
            >
              {voiceError}
            </div>
          )}
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="ghost"
              size="lg"
              onClick={handlePlay}
              disabled={isBusy}
              aria-label="Ouvir email"
            >
              <Volume2 className="h-5 w-5" />
              {processing === "tts" ? "A processar…" : "Ouvir"}
            </Button>
            <Button
              size="lg"
              onClick={() => setRecordOpen(true)}
              disabled={isBusy}
              aria-label="Responder por voz"
            >
              <Mic className="h-5 w-5" />
              {processing === "transcribe" || processing === "polish"
                ? "A processar…"
                : "Responder"}
            </Button>
          </div>
        </footer>
      )}

      <RecordModal
        open={recordOpen}
        onOpenChange={setRecordOpen}
        onRecorded={handleRecorded}
      />
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="space-y-4" aria-hidden>
      <div className="h-6 w-3/4 animate-pulse rounded bg-surface-elevated" />
      <div className="h-4 w-1/3 animate-pulse rounded bg-surface-elevated" />
      <div className="h-4 w-1/4 animate-pulse rounded bg-surface-elevated" />
      <div className="space-y-2 pt-2">
        <div className="h-3 w-full animate-pulse rounded bg-surface-elevated" />
        <div className="h-3 w-full animate-pulse rounded bg-surface-elevated" />
        <div className="h-3 w-11/12 animate-pulse rounded bg-surface-elevated" />
        <div className="h-3 w-4/5 animate-pulse rounded bg-surface-elevated" />
      </div>
    </div>
  );
}
