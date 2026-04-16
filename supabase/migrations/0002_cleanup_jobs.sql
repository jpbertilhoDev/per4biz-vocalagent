-- Per4Biz — Cleanup jobs para minimização de dados (GDPR / CON-009)
-- Versão: 0002
-- Data: 2026-04-15
--
-- Requer pg_cron (habilitar em Supabase Dashboard → Database → Extensions).
-- Se pg_cron não estiver disponível, substituir por Supabase Edge Function diária.

create extension if not exists "pg_cron";

-- ============================================================================
-- Função: limpar body_cached de emails > 24h
-- ============================================================================
create or replace function public.cleanup_expired_email_bodies()
returns int
language plpgsql
as $$
declare
  affected_count int;
begin
  update public.email_cache
     set body_cached = null
   where cache_expires_at < now()
     and body_cached is not null;

  get diagnostics affected_count = row_count;
  return affected_count;
end;
$$;

comment on function public.cleanup_expired_email_bodies is
    'Apaga email_cache.body_cached quando TTL 24h expira (ADR-005 + CON-009).';

-- ============================================================================
-- Função: apagar voice_sessions audio > 7d
-- ============================================================================
create or replace function public.cleanup_expired_voice_audio()
returns int
language plpgsql
as $$
declare
  affected_count int;
begin
  -- NB: o file em Supabase Storage tem de ser apagado separadamente via Edge Function ou app.
  -- Aqui apenas limpamos a referência.
  update public.voice_sessions
     set audio_url = null
   where audio_expires_at < now()
     and audio_url is not null;

  get diagnostics affected_count = row_count;
  return affected_count;
end;
$$;

-- ============================================================================
-- Schedule: cron diário 03:00 UTC
-- ============================================================================
select cron.schedule(
    'per4biz-cleanup-email-bodies',
    '0 3 * * *',
    $$ select public.cleanup_expired_email_bodies(); $$
);

select cron.schedule(
    'per4biz-cleanup-voice-audio',
    '15 3 * * *',
    $$ select public.cleanup_expired_voice_audio(); $$
);
