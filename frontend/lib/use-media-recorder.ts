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
  duration: number;
  error: string | null;
  isSilent: boolean;
  start: (autoSilenceMs?: number) => Promise<void>;
  stop: () => void;
  reset: () => void;
}

const MAX_DURATION_S = 60;
const PREFERRED_MIME = "audio/webm;codecs=opus";
const SILENCE_THRESHOLD = 0.015;
const SILENCE_CHECK_INTERVAL_MS = 100;

export function useMediaRecorder(): UseMediaRecorderResult {
  const [state, setState] = useState<RecorderState>("idle");
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isSilent, setIsSilent] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startTimeRef = useRef<number>(0);
  const intervalRef = useRef<number | null>(null);

  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const silenceStartRef = useRef<number | null>(null);
  const autoSilenceMsRef = useRef<number>(0);
  const silenceCheckRef = useRef<number | null>(null);

  const cleanup = useCallback(() => {
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (silenceCheckRef.current) {
      window.clearInterval(silenceCheckRef.current);
      silenceCheckRef.current = null;
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    mediaRecorderRef.current = null;
    analyserRef.current = null;
    if (audioCtxRef.current?.state !== "closed") {
      audioCtxRef.current?.close().catch(() => {});
    }
    audioCtxRef.current = null;
    chunksRef.current = [];
    silenceStartRef.current = null;
    setIsSilent(false);
  }, []);

  const start = useCallback(
    async (autoSilenceMs = 2000) => {
      setError(null);
      setAudioBlob(null);
      setDuration(0);
      setState("requesting");
      autoSilenceMsRef.current = autoSilenceMs;

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

        const audioCtx = new AudioContext();
        audioCtxRef.current = audioCtx;
        const source = audioCtx.createMediaStreamSource(stream);
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 512;
        source.connect(analyser);
        analyserRef.current = analyser;

        recorder.start(250);
        startTimeRef.current = Date.now();
        setState("recording");
        silenceStartRef.current = Date.now();

        const dataArray = new Float32Array(analyser.fftSize);

        silenceCheckRef.current = window.setInterval(() => {
          if (!analyserRef.current) return;
          analyserRef.current.getFloatTimeDomainData(dataArray);

          let rms = 0;
          for (let i = 0; i < dataArray.length; i++) {
            rms += dataArray[i] * dataArray[i];
          }
          rms = Math.sqrt(rms / dataArray.length);

          if (rms < SILENCE_THRESHOLD) {
            if (!silenceStartRef.current) {
              silenceStartRef.current = Date.now();
            }
            const silenceDuration = Date.now() - silenceStartRef.current;
            setIsSilent(silenceDuration > 500);

            if (
              autoSilenceMsRef.current > 0 &&
              silenceDuration >= autoSilenceMsRef.current &&
              mediaRecorderRef.current?.state === "recording"
            ) {
              setState("stopping");
              mediaRecorderRef.current.stop();
            }
          } else {
            silenceStartRef.current = Date.now();
            setIsSilent(false);
          }
        }, SILENCE_CHECK_INTERVAL_MS);

        intervalRef.current = window.setInterval(() => {
          const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
          setDuration(elapsed);
          if (elapsed >= MAX_DURATION_S && mediaRecorderRef.current?.state === "recording") {
            setState("stopping");
            mediaRecorderRef.current.stop();
          }
        }, 250);
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Falha ao aceder ao microfone";
        setError(msg);
        setState("error");
        cleanup();
      }
    },
    [cleanup],
  );

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

  return { state, audioBlob, duration, error, isSilent, start, stop, reset };
}
