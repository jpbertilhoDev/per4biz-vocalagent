-- Per4Biz — Initial Schema (V1 single-tenant)
-- Versão: 0001
-- Data: 2026-04-15
--
-- Arquitetura target (ver 02-ultraplan/ULTRAPLAN-tecnico.md §3) prevê multi-tenant com RLS.
-- Em V1 (ver 07-v1-scope/EXECUTION-NOTES.md) executamos SEM RLS e com user_id hardcoded
-- para o UUID do JP. A coluna user_id fica preparada para migração multi-tenant futura.

-- ============================================================================
-- Extensions
-- ============================================================================
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- ============================================================================
-- 1. users  (perfil + preferências do único utilizador em V1)
-- ============================================================================
create table public.users (
    id                  uuid primary key default uuid_generate_v4(),
    email               text unique not null,
    full_name           text,
    preferred_language  text not null default 'pt-PT',
    voice_id            text,                         -- ElevenLabs voice_id
    active_account_id   uuid,                         -- FK soft; set later
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

comment on table public.users is
    'Utilizadores. V1 = apenas 1 linha (JP). Multi-tenant ready.';

-- ============================================================================
-- 2. google_accounts  (N contas Google do mesmo user)
-- ============================================================================
create table public.google_accounts (
    id                          uuid primary key default uuid_generate_v4(),
    user_id                     uuid not null references public.users(id) on delete cascade,
    google_email                text not null,
    display_name                text,
    color_hex                   text not null default '#0A84FF',
    refresh_token_encrypted     bytea not null,       -- AES-256-GCM (nonce || ct || tag)
    access_token_encrypted      bytea,
    access_token_expires_at     timestamptz,
    scopes                      text[] not null default '{}',
    key_version                 int not null default 1,
    last_sync_at                timestamptz,
    pubsub_watch_expiration     timestamptz,
    is_primary                  boolean not null default false,
    is_active                   boolean not null default true,
    created_at                  timestamptz not null default now(),
    updated_at                  timestamptz not null default now(),
    unique (user_id, google_email)
);

comment on column public.google_accounts.refresh_token_encrypted is
    'AES-256-GCM: nonce(12) || ciphertext || tag(16). Chave em ENCRYPTION_KEY env.';

create index idx_google_accounts_user on public.google_accounts(user_id) where is_active;

-- FK soft (circular): users.active_account_id → google_accounts
alter table public.users
    add constraint users_active_account_fk
    foreign key (active_account_id) references public.google_accounts(id) on delete set null;

-- ============================================================================
-- 3. email_cache  (cache de metadados; body com TTL 24h)
-- ============================================================================
create table public.email_cache (
    id                  uuid primary key default uuid_generate_v4(),
    google_account_id   uuid not null references public.google_accounts(id) on delete cascade,
    gmail_message_id    text not null,
    thread_id           text,
    from_email          text,
    from_name           text,
    to_emails           text[] not null default '{}',
    cc_emails           text[] not null default '{}',
    subject             text,
    snippet             text,                         -- <= 200 chars preview
    body_cached         text,                         -- full body, APAGAR em 24h via cron
    received_at         timestamptz not null,
    is_read             boolean not null default false,
    is_starred          boolean not null default false,
    labels              text[] not null default '{}',
    cache_expires_at    timestamptz not null default (now() + interval '24 hours'),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    unique (google_account_id, gmail_message_id)
);

comment on column public.email_cache.body_cached is
    'Corpo completo do email. TTL 24h (ADR-005 + CON-009). Cron apaga daily.';

create index idx_email_cache_account_received
    on public.email_cache(google_account_id, received_at desc);
create index idx_email_cache_expiry
    on public.email_cache(cache_expires_at);
create index idx_email_cache_unread
    on public.email_cache(google_account_id, is_read) where is_read = false;

-- ============================================================================
-- 4. draft_responses  (rascunhos gerados pelo LLM + aprovados pelo user)
-- ============================================================================
create type draft_status as enum ('draft', 'approved', 'sent', 'discarded');
create type draft_tone   as enum ('formal', 'casual', 'concise', 'profissional_cordial');

create table public.draft_responses (
    id                      uuid primary key default uuid_generate_v4(),
    user_id                 uuid not null references public.users(id) on delete cascade,
    google_account_id       uuid not null references public.google_accounts(id) on delete cascade,
    reply_to_message_id     text,                     -- gmail_message_id se reply
    parent_draft_id         uuid references public.draft_responses(id) on delete set null,
    to_emails               text[] not null default '{}',
    cc_emails               text[] not null default '{}',
    subject                 text,
    body_text               text not null,
    tone                    draft_tone not null default 'profissional_cordial',
    llm_model               text not null,            -- e.g. "llama-3.3-70b-versatile"
    status                  draft_status not null default 'draft',
    voice_session_id        uuid,                     -- FK soft; set later
    gmail_message_id_sent   text,                     -- populated after send
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now(),
    sent_at                 timestamptz
);

create index idx_drafts_user_status on public.draft_responses(user_id, status);
create index idx_drafts_account on public.draft_responses(google_account_id);

-- ============================================================================
-- 5. voice_sessions  (histórico de interações vocais — áudio apaga em 7d)
-- ============================================================================
create type voice_intent as enum (
    'read_inbox',
    'reply_email',
    'compose_email',
    'check_calendar',      -- V2
    'create_event',        -- V2
    'search_contact',      -- V2
    'switch_account',
    'unknown'
);

create table public.voice_sessions (
    id                  uuid primary key default uuid_generate_v4(),
    user_id             uuid not null references public.users(id) on delete cascade,
    google_account_id   uuid references public.google_accounts(id) on delete set null,
    audio_url           text,                         -- Supabase Storage path; apaga 7d
    audio_expires_at    timestamptz not null default (now() + interval '7 days'),
    transcript          text,                         -- retenção 30d opt-in (ou session-only)
    intent              voice_intent not null default 'unknown',
    llm_response        text,
    tts_audio_url       text,
    stt_ms              int,
    intent_ms           int,
    llm_ms              int,
    tts_ms              int,
    total_ms            int,
    created_at          timestamptz not null default now()
);

-- Add soft FK back from draft_responses to voice_sessions
alter table public.draft_responses
    add constraint drafts_voice_session_fk
    foreign key (voice_session_id) references public.voice_sessions(id) on delete set null;

create index idx_voice_sessions_user on public.voice_sessions(user_id, created_at desc);
create index idx_voice_sessions_audio_expiry on public.voice_sessions(audio_expires_at);

-- ============================================================================
-- 6. app_settings  (preferências por utilizador)
-- ============================================================================
create table public.app_settings (
    user_id                             uuid primary key references public.users(id) on delete cascade,
    default_tone                        draft_tone not null default 'profissional_cordial',
    signature_text                      text,
    push_notifications_enabled          boolean not null default false,
    wake_word_enabled                   boolean not null default false,
    voice_speed                         float not null default 1.0 check (voice_speed between 0.5 and 2.0),
    auto_sync_interval_sec              int not null default 120 check (auto_sync_interval_sec between 30 and 3600),
    unified_inbox                       boolean not null default true,
    transcript_retention_enabled        boolean not null default false,  -- opt-in
    theme                               text not null default 'system' check (theme in ('light','dark','system')),
    created_at                          timestamptz not null default now(),
    updated_at                          timestamptz not null default now()
);

-- ============================================================================
-- Updated_at triggers
-- ============================================================================
create or replace function public.trigger_set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger users_updated_at          before update on public.users          for each row execute function public.trigger_set_updated_at();
create trigger google_accounts_updated   before update on public.google_accounts for each row execute function public.trigger_set_updated_at();
create trigger email_cache_updated       before update on public.email_cache    for each row execute function public.trigger_set_updated_at();
create trigger draft_responses_updated   before update on public.draft_responses for each row execute function public.trigger_set_updated_at();
create trigger app_settings_updated      before update on public.app_settings   for each row execute function public.trigger_set_updated_at();

-- ============================================================================
-- NOTE: RLS DELIBERADAMENTE OMITIDO EM V1
-- ============================================================================
-- Em V1 single-tenant (JP), RLS não é aplicado.
-- FastAPI valida ALLOWED_USER_EMAIL no middleware e confia daí em diante.
-- Ao migrar para multi-tenant:
--   alter table public.users          enable row level security;
--   alter table public.google_accounts enable row level security;
--   alter table public.email_cache    enable row level security;
--   alter table public.draft_responses enable row level security;
--   alter table public.voice_sessions enable row level security;
--   alter table public.app_settings   enable row level security;
--   + policies "tenant_isolation" on each table where user_id = auth.uid()
-- Ver 06-addendum/CONSTRAINTS-ASSUMPTIONS-OOS.md §CON-008.
