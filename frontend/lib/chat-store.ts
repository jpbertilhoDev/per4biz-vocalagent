import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

import type { ChatHistoryMessage } from "./voice-api";

export type VoxCardType =
  | "email-read"
  | "transcription"
  | "draft"
  | "confirmation"
  | "error"
  | "agenda-placeholder"
  | "calendar-event"
  | "calendar-create"
  | "calendar-confirm"
  | "contact-card";

export interface VoxCard {
  id: string;
  type: VoxCardType;
  title: string;
  content: string;
  meta?: Record<string, string>;
  actions?: { label: string; action: string }[];
  createdAt: number;
}

export interface UserMessage {
  id: string;
  text: string;
  isVoice: boolean;
  createdAt: number;
}

export type ChatMessage =
  | ({ role: "vox" } & VoxCard)
  | ({ role: "user" } & UserMessage);

export type MicState =
  | "idle"
  | "listening"
  | "silence-detected"
  | "processing"
  | "speaking"
  | "error";

interface ChatState {
  messages: ChatMessage[];
  micState: MicState;
  liveTranscript: string;
  hypothesisTranscript: string;
  activeAccountId: string | null;

  addVoxCard: (card: Omit<VoxCard, "id" | "createdAt">) => void;
  addUserMessage: (text: string, isVoice: boolean) => void;
  updateVoxCard: (id: string, updates: Partial<VoxCard>) => void;
  removeVoxCard: (id: string) => void;
  clearMessages: () => void;
  setMicState: (state: MicState) => void;
  setLiveTranscript: (confirmed: string, hypothesis?: string) => void;
  clearLiveTranscript: () => void;
  setActiveAccount: (id: string | null) => void;
}

let nextId = 1;
function uid(): string {
  return `msg-${Date.now()}-${nextId++}`;
}

// Cap persisted messages so localStorage doesn't blow up over time.
const MAX_PERSISTED_MESSAGES = 50;

/**
 * Build the LLM-facing conversation history from the last N chat-store messages.
 *
 * User turns pass through verbatim; Vox turns are serialized as "Title: content"
 * when a title exists, or just content otherwise. Messages without textual
 * content are dropped (e.g. loading placeholders) so the LLM never sees ghosts.
 *
 * @param messages — the full chat-store messages array
 * @param limit — how many trailing messages to consider (default 10)
 */
export function buildHistoryFromMessages(
  messages: ChatMessage[],
  limit = 10,
): ChatHistoryMessage[] {
  return messages.slice(-limit).reduce<ChatHistoryMessage[]>((acc, msg) => {
    if (msg.role === "user") {
      acc.push({ role: "user", content: msg.text });
    } else if (msg.role === "vox" && msg.content) {
      acc.push({
        role: "assistant",
        content: msg.title ? `${msg.title}: ${msg.content}` : msg.content,
      });
    }
    return acc;
  }, []);
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      messages: [],
      micState: "idle",
      liveTranscript: "",
      hypothesisTranscript: "",
      activeAccountId: null,

      addVoxCard: (card) =>
        set((s) => ({
          messages: [
            ...s.messages,
            { role: "vox" as const, ...card, id: uid(), createdAt: Date.now() },
          ].slice(-MAX_PERSISTED_MESSAGES),
        })),

      addUserMessage: (text, isVoice) =>
        set((s) => ({
          messages: [
            ...s.messages,
            {
              role: "user" as const,
              id: uid(),
              text,
              isVoice,
              createdAt: Date.now(),
            },
          ].slice(-MAX_PERSISTED_MESSAGES),
        })),

      updateVoxCard: (id, updates) =>
        set((s) => ({
          messages: s.messages.map((m) =>
            m.role === "vox" && m.id === id ? { ...m, ...updates } : m,
          ),
        })),

      removeVoxCard: (id) =>
        set((s) => ({
          messages: s.messages.filter((m) => !(m.role === "vox" && m.id === id)),
        })),

      clearMessages: () => set({ messages: [] }),

      setMicState: (micState) => set({ micState }),

      setLiveTranscript: (confirmed, hypothesis = "") =>
        set({ liveTranscript: confirmed, hypothesisTranscript: hypothesis }),

      clearLiveTranscript: () =>
        set({ liveTranscript: "", hypothesisTranscript: "" }),

      setActiveAccount: (activeAccountId) => set({ activeAccountId }),
    }),
    {
      name: "vox-chat-store",
      storage: createJSONStorage(() => localStorage),
      // Only persist the conversation, not transient UI state
      partialize: (state) => ({
        messages: state.messages,
        activeAccountId: state.activeAccountId,
      }),
    },
  ),
);
