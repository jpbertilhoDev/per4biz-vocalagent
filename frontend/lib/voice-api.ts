import { apiFetch } from "./api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export interface TranscribeResponse {
  text: string;
  language: string | null;
  duration_ms: number;
}

export async function postTranscribe(blob: Blob): Promise<TranscribeResponse> {
  const formData = new FormData();
  formData.append("audio", blob, "recording.webm");
  const res = await fetch(`${API_URL}/voice/transcribe`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  if (!res.ok) {
    if (res.status === 401 && typeof window !== "undefined") {
      window.location.href = "/";
    }
    throw new Error(`transcribe failed: ${res.status}`);
  }
  return res.json();
}

export interface PolishContext {
  transcript: string;
  from_name: string;
  from_email: string;
  subject: string;
  body: string;
}

export interface PolishResponse {
  polished_text: string;
  model_ms: number;
}

export async function postPolish(ctx: PolishContext): Promise<PolishResponse> {
  return apiFetch<PolishResponse>("/voice/polish", {
    method: "POST",
    body: JSON.stringify(ctx),
  });
}

export async function fetchTTS(text: string, voiceId?: string): Promise<Blob> {
  const res = await fetch(`${API_URL}/voice/tts`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, voice_id: voiceId ?? null }),
  });
  if (!res.ok) {
    if (res.status === 401 && typeof window !== "undefined") {
      window.location.href = "/";
    }
    throw new Error(`tts failed: ${res.status}`);
  }
  return res.blob();
}
