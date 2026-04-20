import { describe, expect, it, vi } from "vitest";
import { VoiceTelemetry } from "@/lib/voice-telemetry";

describe("VoiceTelemetry", () => {
  it("mints a session id on start()", () => {
    const t = new VoiceTelemetry();
    const id = t.start();
    expect(id).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("mark() records ms offsets from start()", () => {
    let clock = 1000;
    const t = new VoiceTelemetry(() => clock);
    t.start();
    clock += 150;
    t.mark("vad_cut");
    clock += 400;
    t.mark("audio_first_play");
    const events = t.events();
    expect(events).toHaveLength(2);
    expect(events[0].phase).toBe("vad_cut");
    expect(events[0].ms).toBeGreaterThanOrEqual(150);
    expect(events[1].ms).toBeGreaterThanOrEqual(550);
  });

  it("flush() posts batch and resets", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    global.fetch = fetchSpy as unknown as typeof fetch;
    const t = new VoiceTelemetry();
    const id = t.start();
    t.mark("vad_cut");
    await t.flush();
    expect(fetchSpy).toHaveBeenCalledOnce();
    const [, init] = fetchSpy.mock.calls[0];
    const headers = new Headers(init.headers);
    expect(headers.get("X-Voice-Session-Id")).toBe(id);
    expect(t.events()).toHaveLength(0);
  });

  it("flush() swallows network errors", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("offline")) as unknown as typeof fetch;
    const t = new VoiceTelemetry();
    t.start();
    t.mark("vad_cut");
    await expect(t.flush()).resolves.toBeUndefined();
  });
});
