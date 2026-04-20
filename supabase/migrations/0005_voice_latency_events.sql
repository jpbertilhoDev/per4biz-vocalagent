-- Per4Biz — Voice latency telemetry (E10 Phase 1)
-- Versão: 0005
-- Data: 2026-04-20
--
-- Tabela de eventos de latência por fase do pipeline vocal.
-- Zero PII (CLAUDE.md §3.3, LOGGING-POLICY §4). Retenção 30 dias.

create table if not exists public.voice_latency_events (
  id uuid primary key default gen_random_uuid(),
  voice_session_id uuid not null,
  user_id uuid not null,
  phase text not null,
  ms integer not null check (ms >= 0),
  status text not null check (status in ('ok', 'error', 'timeout')),
  created_at timestamptz not null default now()
);

create index if not exists voice_latency_events_session_idx
  on public.voice_latency_events(voice_session_id);

create index if not exists voice_latency_events_created_idx
  on public.voice_latency_events(created_at desc);

create index if not exists voice_latency_events_phase_created_idx
  on public.voice_latency_events(phase, created_at desc);

comment on table public.voice_latency_events is
  'E10 — telemetria de latência por fase do pipeline vocal Vox. TTL 30d.';

-- Cleanup: eventos > 30 dias
create or replace function public.cleanup_expired_voice_latency_events()
returns int
language plpgsql
as $$
declare
  affected_count int;
begin
  delete from public.voice_latency_events
   where created_at < now() - interval '30 days';

  get diagnostics affected_count = row_count;
  return affected_count;
end;
$$;

comment on function public.cleanup_expired_voice_latency_events is
  'E10 — apaga eventos de latência > 30 dias. Corre diariamente via pg_cron.';

-- Agendar cleanup diário às 03:00 UTC
select cron.schedule(
  'cleanup_voice_latency_events',
  '0 3 * * *',
  $$ select public.cleanup_expired_voice_latency_events(); $$
);
