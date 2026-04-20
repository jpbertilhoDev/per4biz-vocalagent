export interface TelemetryEvent {
  phase: string;
  ms: number;
  status?: "ok" | "error" | "timeout";
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";
const TELEMETRY_ENDPOINT = `${API_URL}/voice/telemetry`;

export class VoiceTelemetry {
  private sessionId: string | null = null;
  private t0: number = 0;
  private buffer: TelemetryEvent[] = [];
  private now: () => number;

  constructor(now?: () => number) {
    this.now = now ?? (() => performance.now());
  }

  start(): string {
    this.sessionId = crypto.randomUUID();
    this.t0 = this.now();
    this.buffer = [];
    return this.sessionId;
  }

  mark(phase: string, status: "ok" | "error" | "timeout" = "ok"): void {
    if (!this.sessionId) return;
    const ms = Math.max(0, Math.round(this.now() - this.t0));
    this.buffer.push({ phase, ms, status });
  }

  events(): TelemetryEvent[] {
    return [...this.buffer];
  }

  async flush(): Promise<void> {
    if (!this.sessionId || this.buffer.length === 0) return;
    const payload = { events: this.buffer };
    const sessionId = this.sessionId;
    this.buffer = [];
    try {
      const { getAuthToken } = await import("./api");
      const token = getAuthToken();
      await fetch(TELEMETRY_ENDPOINT, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-Voice-Session-Id": sessionId,
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
        keepalive: true,
      });
    } catch {
      // Swallow — telemetry must never break UX.
    }
  }

  get id(): string | null {
    return this.sessionId;
  }
}
