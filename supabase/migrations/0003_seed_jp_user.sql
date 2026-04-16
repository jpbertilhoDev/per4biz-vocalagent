-- Per4Biz — Seed do único utilizador V1 (JP)
-- Versão: 0003
-- Data: 2026-04-15
--
-- Em V1 single-tenant, existe 1 linha em public.users com UUID fixo que bate
-- com o USER_ID do .env. Isto permite inserts e queries do backend sem Auth.
--
-- IMPORTANTE: este UUID deve corresponder EXATAMENTE ao valor de USER_ID no .env
-- Se mudares um, muda o outro.

insert into public.users (id, email, full_name, preferred_language, created_at, updated_at)
values (
    '00000000-0000-0000-0000-000000000001'::uuid,
    'jpbertilhopt@gmail.com',
    'JP Bertilho',
    'pt-PT',
    now(),
    now()
)
on conflict (id) do update set
    email               = excluded.email,
    full_name           = excluded.full_name,
    preferred_language  = excluded.preferred_language,
    updated_at          = now();

insert into public.app_settings (user_id, default_tone, unified_inbox, theme, created_at, updated_at)
values (
    '00000000-0000-0000-0000-000000000001'::uuid,
    'profissional_cordial',
    true,
    'system',
    now(),
    now()
)
on conflict (user_id) do nothing;
