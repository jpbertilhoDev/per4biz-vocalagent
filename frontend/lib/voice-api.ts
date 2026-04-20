import { apiFetch, getAuthToken } from "./api";
import type { VoiceTelemetry } from "./voice-telemetry";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

function authHeaders(): HeadersInit {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function telemetryHeaders(telemetry?: VoiceTelemetry): HeadersInit {
  const id = telemetry?.id;
  return id ? { "X-Voice-Session-Id": id } : {};
}

export interface TranscribeResponse {
  text: string;
  language: string | null;
  duration_ms: number;
}

export async function postTranscribe(
  blob: Blob,
  telemetry?: VoiceTelemetry,
): Promise<TranscribeResponse> {
  const formData = new FormData();
  formData.append("audio", blob, "recording.webm");
  telemetry?.mark("upload_start");
  const res = await fetch(`${API_URL}/voice/transcribe`, {
    method: "POST",
    credentials: "include",
    headers: { ...authHeaders(), ...telemetryHeaders(telemetry) },
    body: formData,
  });
  telemetry?.mark("upload_done");
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

export async function postPolish(
  ctx: PolishContext,
  telemetry?: VoiceTelemetry,
): Promise<PolishResponse> {
  const result = await apiFetch<PolishResponse>("/voice/polish", {
    method: "POST",
    body: JSON.stringify(ctx),
    headers: { ...telemetryHeaders(telemetry) },
  });
  telemetry?.mark("polish_done");
  return result;
}

export async function fetchTTS(
  text: string,
  voiceId?: string,
  telemetry?: VoiceTelemetry,
): Promise<Blob> {
  const res = await fetch(`${API_URL}/voice/tts`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...telemetryHeaders(telemetry),
    },
    body: JSON.stringify({ text, voice_id: voiceId ?? null }),
  });
  telemetry?.mark("tts_done");
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
 * Web Speech API removed — Vox uses ElevenLabs exclusively.
 * If ElevenLabs fails, the UI surfaces a visible error card; no robotic
 * fallback voice is ever played to keep voice identity consistent.
 */

export interface IntentResponse {
  intent: string;
  params: Record<string, unknown>;
  model_ms: number;
}

export async function postIntent(
  transcript: string,
  history: ChatHistoryMessage[] = [],
  telemetry?: VoiceTelemetry,
): Promise<IntentResponse> {
  const result = await apiFetch<IntentResponse>("/voice/intent", {
    method: "POST",
    body: JSON.stringify({ transcript, history }),
    headers: { ...telemetryHeaders(telemetry) },
  });
  telemetry?.mark("intent_done");
  return result;
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
  telemetry?: VoiceTelemetry,
): Promise<ChatResponse> {
  const result = await apiFetch<ChatResponse>("/voice/chat", {
    method: "POST",
    body: JSON.stringify({ transcript, history }),
    headers: { ...telemetryHeaders(telemetry) },
  });
  telemetry?.mark("chat_done");
  return result;
}
