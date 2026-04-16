import { describe, it, expect, vi, beforeEach } from "vitest";
import { postIntent } from "@/lib/voice-api";
import { useChatStore, buildHistoryFromMessages } from "@/lib/chat-store";

vi.mock("@/lib/api", () => ({
  apiFetch: vi.fn().mockResolvedValue({ intent: "general", params: {}, model_ms: 100 }),
  ApiError: class extends Error {
    status: number;
    detail: string;
    constructor(status: number, detail: string) {
      super(`${status}: ${detail}`);
      this.status = status;
      this.detail = detail;
    }
  },
}));

describe("ChatPage — history mapping do chat-store para postIntent", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useChatStore.getState().clearMessages();
  });

  it("mapeia mensagens do chat-store para ChatHistoryMessage[]", async () => {
    useChatStore.getState().addUserMessage("o que tenho hoje?", true);
    useChatStore.getState().addVoxCard({
      type: "calendar-event",
      title: "Reunião Maria",
      content: "15h",
    });

    const store = useChatStore.getState();
    const history = buildHistoryFromMessages(store.messages);

    expect(history).toHaveLength(2);
    expect(history[0]).toEqual({ role: "user", content: "o que tenho hoje?" });
    expect(history[1]).toEqual({ role: "assistant", content: "Reunião Maria: 15h" });

    await postIntent("cancela essa reunião", history);

    const { apiFetch } = await import("@/lib/api");
    expect(vi.mocked(apiFetch)).toHaveBeenCalledWith(
      "/voice/intent",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"history"'),
      }),
    );

    const callArgs = vi.mocked(apiFetch).mock.calls[0]!;
    const body = JSON.parse(callArgs[1]!.body as string);
    expect(body.transcript).toBe("cancela essa reunião");
    expect(body.history).toHaveLength(2);
    expect(body.history[0]).toEqual({ role: "user", content: "o que tenho hoje?" });
  });

  it("passa array vazio se chat-store está vazio", async () => {
    const history: Array<{ role: "user" | "assistant"; content: string }> = [];
    await postIntent("olá", history);

    const { apiFetch } = await import("@/lib/api");
    const callArgs = vi.mocked(apiFetch).mock.calls[0]!;
    const body = JSON.parse(callArgs[1]!.body as string);
    expect(body.history).toEqual([]);
  });
});
