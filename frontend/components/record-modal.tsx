"use client";

import { useEffect, useRef } from "react";
import { Mic, MicOff, Square } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useMediaRecorder } from "@/lib/use-media-recorder";
import { VoiceTelemetry } from "@/lib/voice-telemetry";

export interface RecordModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRecorded: (blob: Blob, telemetry: VoiceTelemetry) => void;
}

export function RecordModal({ open, onOpenChange, onRecorded }: RecordModalProps) {
  const { state, audioBlob, duration, error, start, stop, reset } = useMediaRecorder();
  const telemetryRef = useRef<VoiceTelemetry>(new VoiceTelemetry());

  // Auto-start quando abre — a telemetria arranca com o modal e é flushed
  // quando o modal fecha (qualquer evento bufferizado segue para o backend).
  useEffect(() => {
    if (open && state === "idle") {
      telemetryRef.current.start();
      void start();
    }
    if (!open) {
      void telemetryRef.current.flush();
      reset();
    }
  }, [open, state, start, reset]);

  // Quando ready, marca vad_cut e propaga telemetria ao caller
  useEffect(() => {
    if (state === "ready" && audioBlob) {
      telemetryRef.current.mark("vad_cut");
      onRecorded(audioBlob, telemetryRef.current);
      onOpenChange(false);
    }
  }, [state, audioBlob, onRecorded, onOpenChange]);

  const mins = Math.floor(duration / 60);
  const secs = duration % 60;
  const timer = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>A gravar…</DialogTitle>
          <DialogDescription>
            Fala a tua resposta. Máximo 60 segundos. Toca em Parar quando acabares.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center gap-4 py-6">
          {state === "requesting" && (
            <div className="text-sm text-neutral-600">A pedir permissão do microfone…</div>
          )}

          {state === "recording" && (
            <>
              <div className="relative flex h-20 w-20 items-center justify-center">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-50" />
                <span className="relative inline-flex h-16 w-16 items-center justify-center rounded-full bg-red-600 text-white">
                  <Mic className="h-8 w-8" />
                </span>
              </div>
              <div
                className="font-mono text-3xl font-bold tabular-nums"
                aria-live="polite"
              >
                {timer}
              </div>
            </>
          )}

          {state === "stopping" && (
            <div className="text-sm text-neutral-600">A processar…</div>
          )}

          {state === "error" && (
            <div
              role="alert"
              className="flex flex-col items-center gap-2 rounded-lg bg-red-50 p-4 text-center text-sm text-red-700 dark:bg-red-950 dark:text-red-300"
            >
              <MicOff className="h-8 w-8" />
              <p>{error ?? "Não foi possível aceder ao microfone."}</p>
            </div>
          )}
        </div>

        <div className="flex gap-2">
          {state === "recording" && (
            <Button variant="destructive" size="lg" className="flex-1" onClick={stop}>
              <Square className="h-5 w-5" />
              Parar e processar
            </Button>
          )}
          {state === "error" && (
            <Button
              variant="ghost"
              className="flex-1"
              onClick={() => onOpenChange(false)}
            >
              Fechar
            </Button>
          )}
          {(state === "requesting" || state === "stopping") && (
            <Button variant="ghost" disabled className="flex-1">
              Aguarda…
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
