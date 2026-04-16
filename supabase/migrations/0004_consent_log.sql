-- Per4Biz — Consent log (RGPD Art. 30 record of processing + policy versioning)
-- Versão: 0004
-- Data: 2026-04-15
--
-- Referenciado em:
--   - specs/e1-auth-google-oauth/SPEC.md §5.5 (GDPR)
--   - 06-addendum/PRIVACY-POLICY-PT.md §11 (versioning)
--
-- Append-only: NUNCA atualizar linhas existentes. Para revogar consentimento,
-- inserir nova linha com consent_given=false.

create table if not exists public.consent_log (
    id                  uuid primary key default uuid_generate_v4(),
    user_id             uuid not null references public.users(id) on delete cascade,
    policy_type         text not null check (policy_type in ('privacy', 'terms', 'transcripts_opt_in')),
    policy_version      text not null,       -- ex: "privacy-v1.0"
    consent_given       boolean not null,    -- true = aceitou, false = revogou
    ip_hash             text,                -- SHA-256(ip || CONSENT_IP_SALT); nunca plaintext
    user_agent_summary  text,                -- família do browser apenas (ex: "Safari 17 iOS")
    created_at          timestamptz not null default now()
);

comment on table public.consent_log is
    'Registo append-only de consentimentos RGPD. Cada aceitação/revogação = nova linha.';
comment on column public.consent_log.ip_hash is
    'SHA-256(ip || env.CONSENT_IP_SALT). Se salt for rotado, hashes antigos ficam sem matching possível (by design).';
comment on column public.consent_log.policy_type is
    'privacy = política privacidade · terms = termos serviço · transcripts_opt_in = consent voluntário 30d';

create index idx_consent_log_user        on public.consent_log(user_id, created_at desc);
create index idx_consent_log_policy      on public.consent_log(policy_type, policy_version);
create index idx_consent_log_latest      on public.consent_log(user_id, policy_type, created_at desc);

-- ============================================================================
-- Seed: consentimentos iniciais do JP (V1 single-tenant — uso implica aceitação)
-- ============================================================================
insert into public.consent_log (user_id, policy_type, policy_version, consent_given, created_at)
values
    ('00000000-0000-0000-0000-000000000001'::uuid, 'privacy', 'privacy-v1.0', true, now()),
    ('00000000-0000-0000-0000-000000000001'::uuid, 'terms',   'terms-v1.0',   true, now())
on conflict do nothing;

-- ============================================================================
-- Rollback (comentado; correr manualmente se preciso)
-- ============================================================================
-- drop index if exists public.idx_consent_log_latest;
-- drop index if exists public.idx_consent_log_policy;
-- drop index if exists public.idx_consent_log_user;
-- drop table if exists public.consent_log;
