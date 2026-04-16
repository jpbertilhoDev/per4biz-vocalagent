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
    let detail = `transcribe failed: ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // body não é JSON
    }
    throw new Error(detail);
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
    let detail = `tts failed: ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // body não é JSON
    }
    throw new Error(detail);
  }
  return res.blob();
}

/**
 * Browser-native TTS fallback via Web Speech Synthesis API.
 * Used when ElevenLabs is unavailable (502/timeout).
 * Returns a promise that resolves when speech ends.
 */
export function speakFallback(text: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      reject(new Error("Web Speech API not available"));
      return;
    }

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text.slice(0, 4000));
    utterance.lang = "pt-PT";
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Try to find a PT-PT voice
    const voices = window.speechSynthesis.getVoices();
    const ptVoice = voices.find((v) => v.lang.startsWith("pt"));
    if (ptVoice) {
      utterance.voice = ptVoice;
    }

    utterance.onend = () => resolve();
    utterance.onerror = (event) => reject(new Error(`speech synthesis failed: ${event.error}`));

    window.speechSynthesis.speak(utterance);
  });
}

export interface IntentResponse {
  intent: string;
  params: Record<string, unknown>;
  model_ms: number;
}

export async function postIntent(transcript: string): Promise<IntentResponse> {
  return apiFetch<IntentResponse>("/voice/intent", {
    method: "POST",
    body: JSON.stringify({ transcript }),
  });
}

export interface ChatResponse {
  response_text: string;
  model_ms: number;
}

export interface ChatHistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export async function postChat(
  transcript: string,
  history: ChatHistoryMessage[] = [],
): Promise<ChatResponse> {
  return apiFetch<ChatResponse>("/voice/chat", {
    method: "POST",
    body: JSON.stringify({ transcript, history }),
  });
}
