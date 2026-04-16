import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export type VoxCardType =
  | "email-read"
  | "transcription"
  | "draft"
  | "confirmation"
  | "error"
  | "agenda-placeholder"
  | "calendar-event"
  | "calendar-create"
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
            { role: "vox", ...card, id: uid(), createdAt: Date.now() },
          ].slice(-MAX_PERSISTED_MESSAGES),
        })),

      addUserMessage: (text, isVoice) =>
        set((s) => ({
          messages: [
            ...s.messages,
            {
              role: "user",
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
