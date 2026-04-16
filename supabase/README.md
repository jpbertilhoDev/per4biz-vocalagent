# supabase/ — Schema, RLS policies & migrations

## Estado

**Vazio.** Primeira migration a criar no **Sprint 0 — Dia 2**: `0001_initial_schema.sql`.

## Estrutura esperada

```
supabase/
├── config.toml                              ← gerado por `supabase init`
├── migrations/
│   ├── 0001_initial_schema.sql              ← users, google_accounts, email_cache,
│   │                                           draft_responses, voice_sessions,
│   │                                           app_settings + RLS policies
│   ├── 0002_indexes.sql
│   └── 0003_cron_cleanup_email_cache.sql    ← Edge Function trigger diário
├── functions/                               ← Edge Functions (Deno)
│   └── cleanup-email-cache/
└── seed.sql                                 ← dados de dev (opcional)
```

## Schema (resumo — detalhe em Ultraplan §3)

| Tabela | Propósito | RLS |
|---|---|---|
| `users` | Perfil + preferências (estende `auth.users`) | `auth.uid() = id` |
| `google_accounts` | N contas Google por user, tokens cifrados AES-GCM | `auth.uid() = user_id` |
| `email_cache` | Cache 24h de emails (metadados + body com TTL) | via `google_accounts.user_id` |
| `draft_responses` | Rascunhos gerados pelo LLM | `auth.uid() = user_id` |
| `voice_sessions` | Histórico curto de interações vocais | `auth.uid() = user_id` |
| `app_settings` | Preferências do user | `auth.uid() = user_id` |

## Comandos

```bash
supabase init                             # primeira vez
supabase start                            # local dev
supabase stop                             # para
supabase db reset                         # drop + apply migrations + seed
supabase migration new <name>             # nova migration
supabase migration list                   # ver migrations aplicadas
supabase db push                          # aplicar migrations no remoto (produção)
supabase gen types typescript --local     # gera types TS para frontend
```

## Região

**EU** (Paris `eu-west-3` ou Frankfurt `eu-central-1`).
**Nunca US** — GDPR / residência de dados obrigatória para utilizadores UE.

## Referências

- Schema SQL completo: [../02-ultraplan/ULTRAPLAN-tecnico.md §3](../02-ultraplan/ULTRAPLAN-tecnico.md)
- RLS policies exemplo: [../02-ultraplan/ULTRAPLAN-tecnico.md §6.3](../02-ultraplan/ULTRAPLAN-tecnico.md)
- GDPR & retenção: [../02-ultraplan/ULTRAPLAN-tecnico.md §6.4](../02-ultraplan/ULTRAPLAN-tecnico.md)
