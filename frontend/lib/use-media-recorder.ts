"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type RecorderState =
  | "idle"
  | "requesting"
  | "recording"
  | "stopping"
  | "ready"
  | "error";

export interface UseMediaRecorderResult {
  state: RecorderState;
  audioBlob: Blob | null;
  duration: number; // seconds
  error: string | null;
  start: () => Promise<void>;
  stop: () => void;
  reset: () => void;
}

const MAX_DURATION_S = 60;
const PREFERRED_MIME = "audio/webm;codecs=opus";

export function useMediaRecorder(): UseMediaRecorderResult {
  const [state, setState] = useState<RecorderState>("idle");
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startTimeRef = useRef<number>(0);
  const intervalRef = useRef<number | null>(null);

  const cleanup = useCallback(() => {
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    mediaRecorderRef.current = null;
    chunksRef.current = [];
  }, []);

  const start = useCallback(async () => {
    setError(null);
    setAudioBlob(null);
    setDuration(0);
    setState("requesting");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mime = MediaRecorder.isTypeSupported(PREFERRED_MIME)
        ? PREFERRED_MIME
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType: mime });
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mime });
        setAudioBlob(blob);
        setState("ready");
        cleanup();
      };

      recorder.onerror = () => {
        setError("Erro durante gravação");
        setState("error");
        cleanup();
      };

      recorder.start();
      startTimeRef.current = Date.now();
      setState("recording");

      intervalRef.current = window.setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
        setDuration(elapsed);
        if (elapsed >= MAX_DURATION_S) {
          recorder.stop();
        }
      }, 250);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Falha ao aceder ao microfone";
      setError(msg);
      setState("error");
      cleanup();
    }
  }, [cleanup]);

  const stop = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      setState("stopping");
      mediaRecorderRef.current.stop();
    }
  }, []);

  const reset = useCallback(() => {
    cleanup();
    setState("idle");
    setAudioBlob(null);
    setDuration(0);
    setError(null);
  }, [cleanup]);

  useEffect(() => {
    return () => cleanup();
  }, [cleanup]);

  return { state, audioBlob, duration, error, start, stop, reset };
}
