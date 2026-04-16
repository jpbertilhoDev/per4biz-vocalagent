/**
 * RED tests for `lib/relative-time.ts::formatRelativeTime`.
 *
 * Covers Sprint 1.x · E3 · SPEC §5 UX (relative time labels in inbox rows).
 * The helper currently returns "" — these regex assertions fail on that empty
 * output (not on missing export) until Task 7 GREEN.
 *
 * PT-PT output; test descriptions in English.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { formatRelativeTime } from "@/lib/relative-time";

describe("formatRelativeTime (pt-PT)", () => {
  const NOW = new Date("2026-04-15T12:00:00Z");

  beforeEach(() => {
    vi.useFakeTimers().setSystemTime(NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows 'há Nm' for under 1 hour", () => {
    expect(formatRelativeTime("2026-04-15T11:30:00Z")).toMatch(/há\s?30\s?m/);
  });

  it("shows 'há Nh' for 1-23 hours ago", () => {
    expect(formatRelativeTime("2026-04-15T10:00:00Z")).toMatch(/há\s?2\s?h/);
  });

  it("shows 'ontem' for yesterday", () => {
    expect(formatRelativeTime("2026-04-14T11:00:00Z")).toMatch(/ontem/i);
  });

  it("shows 'dd MMM' for older dates", () => {
    expect(formatRelativeTime("2026-04-10T11:00:00Z")).toMatch(/10\s?abr/i);
  });
});
