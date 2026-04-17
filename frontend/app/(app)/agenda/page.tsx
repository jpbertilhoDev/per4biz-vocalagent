"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Calendar, Clock, MapPin, Users, LogIn, AlertTriangle } from "lucide-react";
import { ApiError } from "@/lib/api";
import {
  listCalendarEvents,
  calendarKeys,
  type CalendarEvent,
} from "@/lib/queries";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

function formatEventTime(start: string, end: string, isAllDay: boolean): string {
  if (isAllDay) {
    const d = new Date(start);
    return d.toLocaleDateString("pt-PT", { weekday: "short", day: "numeric", month: "short" });
  }
  const s = new Date(start);
  const e = new Date(end);
  const dateStr = s.toLocaleDateString("pt-PT", { weekday: "short", day: "numeric", month: "short" });
  const timeStr = `${s.toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}–${e.toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}`;
  return `${dateStr}, ${timeStr}`;
}

function EventCard({ event, index = 0 }: { event: CalendarEvent; index?: number }) {
  return (
    <div
      className="glass-card animate-fade-in-up rounded-2xl p-4 transition-colors hover:bg-[color:var(--surface-elevated)]/80"
      style={{ animationDelay: `${Math.min(index, 10) * 40}ms` }}
    >
      <div className="mb-2 flex items-start justify-between gap-3">
        <h3 className="text-[15px] font-semibold leading-snug text-[color:var(--text-primary)]">
          {event.summary || "(sem título)"}
        </h3>
        {!event.is_all_day && (
          <span className="shrink-0 rounded-full bg-[color:var(--primary)]/15 px-2.5 py-0.5 text-[10px] font-medium tabular-nums tracking-[0.04em] text-[color:var(--primary)]">
            {new Date(event.start).toLocaleTimeString("pt-PT", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3 text-xs text-[color:var(--text-secondary)]">
        <span className="flex items-center gap-1.5">
          <Clock className="h-3 w-3 text-[color:var(--text-tertiary)]" />
          {formatEventTime(event.start, event.end, event.is_all_day)}
        </span>
        {event.location && (
          <span className="flex items-center gap-1.5">
            <MapPin className="h-3 w-3 text-[color:var(--text-tertiary)]" />
            {event.location}
          </span>
        )}
        {event.attendees.length > 0 && (
          <span className="flex items-center gap-1.5">
            <Users className="h-3 w-3 text-[color:var(--text-tertiary)]" />
            {event.attendees.length}
          </span>
        )}
      </div>

      {event.description && (
        <p className="mt-2 line-clamp-2 text-xs text-[color:var(--text-tertiary)]">
          {event.description}
        </p>
      )}
    </div>
  );
}

function groupByDate(events: CalendarEvent[]): Record<string, CalendarEvent[]> {
  const groups: Record<string, CalendarEvent[]> = {};
  for (const e of events) {
    const dateKey = new Date(e.start).toLocaleDateString("pt-PT", {
      weekday: "long",
      day: "numeric",
      month: "long",
    });
    if (!groups[dateKey]) groups[dateKey] = [];
    groups[dateKey].push(e);
  }
  return groups;
}

function isScopeMissing(error: unknown): boolean {
  if (error instanceof ApiError) {
    return error.status === 403 && error.detail === "calendar_scope_missing";
  }
  return false;
}

function isApiNotEnabled(error: unknown): boolean {
  if (error instanceof ApiError) {
    return error.detail === "calendar_api_not_enabled";
  }
  return false;
}

function handleReAuth() {
  // Redirect to Google OAuth to re-authorize with new Calendar scopes
  window.location.href = `${API_URL}/auth/google/start`;
}

export default function AgendaPage() {
  // Stable range anchored at mount — re-computing on every render flipped the
  // queryKey each time and put React Query in a perpetual loading loop.
  const { now, weekLater } = useMemo(() => {
    const nowDate = new Date();
    return {
      now: nowDate.toISOString(),
      weekLater: new Date(nowDate.getTime() + 7 * 86400000).toISOString(),
    };
  }, []);

  const { data, isLoading, error } = useQuery({
    queryKey: calendarKeys.events(now, weekLater),
    queryFn: () => listCalendarEvents(now, weekLater),
    staleTime: 60_000,
    retry: (failureCount, err) => {
      // Don't retry 403 scope-missing — user needs to re-auth
      if (isScopeMissing(err)) return false;
      if (isApiNotEnabled(err)) return false;
      return failureCount < 2;
    },
  });

  const events = data?.events ?? [];
  const grouped = groupByDate(events);
  const scopeMissing = isScopeMissing(error);
  const apiNotEnabled = isApiNotEnabled(error);

  return (
    <div className="relative flex min-h-screen flex-col">
      <header
        className="glass-frost sticky top-0 z-10 px-5 pb-4"
        style={{ paddingTop: "max(2rem, calc(env(safe-area-inset-top) + 2rem))" }}
      >
        <div className="flex items-end justify-between">
          <div className="flex items-baseline gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[color:var(--primary)]/15 ring-1 ring-[color:var(--primary)]/25">
              <Calendar
                className="h-5 w-5 text-[color:var(--primary)]"
                strokeWidth={1.8}
              />
            </div>
            <div className="flex flex-col">
              <h1 className="font-[family-name:var(--font-display)] text-[30px] italic leading-none tracking-[-0.01em] text-[color:var(--text-primary)]">
                Agenda
              </h1>
              <span className="mt-1.5 text-[10px] uppercase tracking-[0.22em] text-[color:var(--text-tertiary)]">
                Próximos 7 dias
              </span>
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1 px-5 py-4" style={{ paddingBottom: "6rem" }}>
        {isLoading && (
          <div className="flex flex-col items-center gap-3 py-16">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <p className="text-sm text-text-tertiary">A carregar agenda...</p>
          </div>
        )}

        {/* Scope missing — user needs to re-authorize with Calendar access */}
        {scopeMissing && (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="mb-2 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 ring-1 ring-primary/20">
              <LogIn className="h-8 w-8 text-primary" strokeWidth={1.5} />
            </div>
            <h2 className="text-base font-semibold text-text-primary">
              Autoriza acesso a agenda
            </h2>
            <p className="max-w-xs text-sm text-text-secondary">
              O Vox precisa de permissao para aceder ao teu Google Calendar.
              Clica em baixo para autorizar.
            </p>
            <button
              type="button"
              onClick={handleReAuth}
              className="inline-flex items-center gap-2 rounded-2xl bg-primary px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-primary/90"
            >
              <LogIn className="h-4 w-4" />
              Autorizar Calendar
            </button>
          </div>
        )}

        {/* Calendar API not enabled in Google Cloud */}
        {apiNotEnabled && (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="mb-2 flex h-16 w-16 items-center justify-center rounded-full bg-error/10 ring-1 ring-error/20">
              <AlertTriangle className="h-8 w-8 text-error" strokeWidth={1.5} />
            </div>
            <h2 className="text-base font-semibold text-text-primary">
              Calendar API nao ativa
            </h2>
            <p className="max-w-xs text-sm text-text-secondary">
              O Google Calendar API precisa de ser ativado no Google Cloud Console do projeto.
            </p>
          </div>
        )}

        {/* Generic error (not scope-related) */}
        {error && !scopeMissing && !apiNotEnabled && (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <div className="mb-2 flex h-14 w-14 items-center justify-center rounded-full bg-error/10">
              <Calendar className="h-7 w-7 text-error" strokeWidth={1.5} />
            </div>
            <p className="text-sm font-medium text-text-primary">Erro ao carregar agenda</p>
            <p className="text-xs text-text-tertiary">
              {error instanceof ApiError
                ? `Erro ${error.status}: ${error.detail}`
                : "Verifica a tua ligacao e tenta de novo."}
            </p>
          </div>
        )}

        {!isLoading && !error && events.length === 0 && (
          <div className="flex flex-col items-center gap-3 py-20 text-center">
            <p className="max-w-[280px] font-[family-name:var(--font-display)] text-[30px] italic leading-[1.15] text-[color:var(--text-primary)]">
              Nada marcado. A semana é tua.
            </p>
            <p className="mt-2 max-w-[260px] text-sm leading-relaxed text-[color:var(--text-secondary)]">
              Sem eventos nos próximos 7 dias. Diz &quot;agenda&quot; ao Vox para criares um.
            </p>
          </div>
        )}

        {!isLoading && !error && events.length > 0 && (
          <div className="space-y-7">
            {Object.entries(grouped).map(([dateLabel, dateEvents], groupIdx) => (
              <div key={dateLabel}>
                <h2 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.22em] text-[color:var(--text-tertiary)]">
                  {dateLabel}
                </h2>
                <div className="space-y-2.5">
                  {dateEvents.map((event, i) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      index={groupIdx * 3 + i}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
